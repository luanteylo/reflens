"""Claude (Anthropic) AI provider implementation."""

import json
import logging
import re

import anthropic

from reflens.ai.provider import AIProvider, GeneratedTag, PaperSummary, ProviderProfile, UsageInfo

logger = logging.getLogger(__name__)

# -- Verbose prompts (for large cloud models) --

SUMMARIZE_PROMPT = """\
You are an expert scientific paper analyst. Given the following paper, produce a structured summary.

Title: {title}
Abstract: {abstract}

Full text:
{full_text}

Respond in JSON with these exact keys:
- "overview": A clear one-paragraph summary of the paper
- "key_contributions": A list of 3-5 bullet points of the main contributions
- "methodology": A summary of the methods used
- "findings": The main results and findings
- "limitations": Limitations mentioned or implied

Respond ONLY with valid JSON, no markdown fences."""

TAGS_PROMPT = """\
You are an expert at classifying scientific papers. Given the following paper, \
generate a curated set of topic tags that best describe it.

Title: {title}
Abstract: {abstract}

Sections:
{sections_text}

Rules:
- Generate between 5 and 8 tags total, no more.
- Mix broad research areas (e.g. "high-performance-computing") with key specific \
concepts or techniques (e.g. "burst-buffers", "io-scheduling").
- Tags should help a researcher find this paper later when browsing by topic.
- Use lowercase, hyphenated format (e.g. "machine-learning", not "Machine Learning").
- Do NOT generate a tag per section. Think about the paper as a whole.

Respond in JSON as a list of objects with keys:
- "name": the tag
- "confidence": float 0-1

Respond ONLY with valid JSON, no markdown fences."""

RELEVANCE_PROMPT = """\
A researcher wants to verify the following claim against a paper in their database.

Claim: {query}

Paper title: {paper_title}
Paper abstract: {paper_abstract}
Paper excerpt: {paper_text}

Assess whether this paper supports, contradicts, or is neutral to the claim.

Respond ONLY with valid JSON:
{{"stance": "supports" | "contradicts" | "neutral", "explanation": "2-3 sentence explanation"}}"""

CLAIM_CHECK_PROMPT = """\
A researcher wants to verify the following claim against their paper database.

Claim: "{claim}"

Supporting evidence from papers in the database:
{evidence}

Based on the evidence provided:
1. Is the claim supported, partially supported, or not supported?
2. Which papers provide the strongest support and why?
3. Are there any nuances or contradictions?

Be specific and cite paper titles."""

# -- Compact prompts (for small local models) --

SUMMARIZE_PROMPT_COMPACT = """\
You are a scientific paper summarizer. Read the paper below and produce a JSON summary.

Title: {title}
Abstract: {abstract}
{full_text}

Respond with ONLY valid JSON, no other text:
{{
  "overview": "A one-paragraph summary of what the paper does and its main contribution",
  "key_contributions": ["contribution 1", "contribution 2", "contribution 3"],
  "methodology": "Brief description of methods used",
  "findings": "Main results",
  "limitations": "Key limitations"
}}"""

TAGS_PROMPT_COMPACT = """\
You are a scientific paper classifier. Generate 5 topic tags for this paper.

Title: {title}
Abstract: {abstract}
{sections_text}

Respond with ONLY a JSON array, no other text:
[{{"name": "example-tag", "confidence": 0.9}}, {{"name": "another-tag", "confidence": 0.8}}]

Use lowercase-hyphenated format for tag names. Generate exactly 5 tags."""

RELEVANCE_PROMPT_COMPACT = """\
You are a research assistant. Determine if the paper below is relevant to the claim.

Claim: "{query}"

Paper title: {paper_title}
Paper abstract: {paper_abstract}
{paper_text}

Respond with ONLY valid JSON, no other text:
{{"stance": "supports", "explanation": "One sentence explaining why this paper supports or contradicts the claim."}}

The stance must be exactly one of: "supports", "contradicts", or "neutral"."""

RERANK_PROMPT = """\
You are a scientific literature expert. A researcher is looking for papers relevant to their query.

Query: "{query}"

Here are candidate papers found by keyword search. Rank them by relevance to the query.
For each paper, assess how well it addresses the query topic.

{papers_block}

Respond with ONLY a JSON array of paper indices ordered from most to least relevant.
Include a brief reason for each. Example:
[{{"index": 2, "reason": "Directly addresses the query topic"}}, {{"index": 0, "reason": "Related but tangential"}}]

Only include papers that are at least somewhat relevant. Exclude completely irrelevant papers."""

RERANK_PROMPT_COMPACT = """\
Rank these papers by relevance to the query. Return JSON array of indices, most relevant first.

Query: "{query}"

{papers_block}

JSON array only: [{{"index": 0, "reason": "why relevant"}}]
Exclude irrelevant papers."""

BATCH_RELEVANCE_PROMPT = """\
You are a research assistant. For each paper below, determine if it is relevant to the claim.

Claim: "{query}"

{papers_block}

Respond with ONLY a JSON array, no other text. One entry per paper:
[{{"paper_index": 0, "stance": "supports", "explanation": "Why this paper is relevant."}}]

The stance must be exactly one of: "supports", "contradicts", or "neutral"."""


def _extract_json(text: str) -> str:
    """Extract valid JSON from LLM output.

    Handles markdown fences, trailing commas, and truncated responses.
    """
    # Strip markdown fences
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    text = m.group(1).strip() if m else text.strip()

    # Remove trailing commas before } or ] (common LLM mistake)
    text = re.sub(r",\s*([}\]])", r"\1", text)

    # If JSON is truncated (incomplete array/object), try to salvage it
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    # Try closing an incomplete JSON array: find last complete element
    # Look for the last complete object in an array
    last_brace = text.rfind("}")
    if last_brace != -1:
        candidate = text[: last_brace + 1] + "]"
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass

    return text


class ClaudeProvider(AIProvider):
    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-6",
        profile: ProviderProfile | None = None,
    ):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model
        self.profile = profile or ProviderProfile()

    def _track_usage(self, response, operation: str) -> None:
        if hasattr(response, "usage") and response.usage:
            usage = UsageInfo(
                provider="claude",
                model=self.model,
                operation=operation,
                prompt_tokens=response.usage.input_tokens or 0,
                completion_tokens=response.usage.output_tokens or 0,
                total_tokens=(response.usage.input_tokens or 0) + (response.usage.output_tokens or 0),
            )
            usage.compute_cost()
            self.last_usage = usage

    async def summarize(self, title: str, abstract: str, full_text: str) -> PaperSummary:
        if self.profile.use_compact_prompts:
            # For local models: use abstract only, compact prompt
            text_to_send = full_text[:self.profile.max_context_chars] if full_text else ""
            prompt = SUMMARIZE_PROMPT_COMPACT.format(
                title=title, abstract=abstract, full_text=text_to_send
            )
            max_tokens = min(self.profile.max_output_tokens, 1000)
        else:
            truncated = full_text[:80_000] if len(full_text) > 80_000 else full_text
            prompt = SUMMARIZE_PROMPT.format(
                title=title, abstract=abstract, full_text=truncated
            )
            max_tokens = 2000

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        self._track_usage(response, "summarize")
        text = response.content[0].text
        data = json.loads(_extract_json(text))

        def _as_str(value: str | list, sep: str = "\n") -> str:
            if isinstance(value, list):
                return sep.join(value)
            return value

        return PaperSummary(
            overview=_as_str(data.get("overview", "")),
            key_contributions=data.get("key_contributions", []),
            methodology=_as_str(data.get("methodology", "")),
            findings=_as_str(data.get("findings", "")),
            limitations=_as_str(data.get("limitations", "")),
        )

    async def generate_tags(
        self, title: str, abstract: str, sections: dict[str, str]
    ) -> list[GeneratedTag]:
        if self.profile.use_compact_prompts:
            # Limit sections for small models
            section_limit = 500
            max_sections = 3
            items = list(sections.items())[:max_sections]
            sections_text = "\n".join(
                f"{name}: {text[:section_limit]}" for name, text in items
            )
            prompt = TAGS_PROMPT_COMPACT.format(
                title=title, abstract=abstract, sections_text=sections_text
            )
            max_tokens = 500
        else:
            sections_text = "\n\n".join(
                f"## {name}\n{text[:2000]}" for name, text in sections.items()
            )
            prompt = TAGS_PROMPT.format(
                title=title, abstract=abstract, sections_text=sections_text
            )
            max_tokens = 1000

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        self._track_usage(response, "tag")
        data = json.loads(_extract_json(text))
        return [
            GeneratedTag(
                name=t["name"],
                section=t.get("section"),
                confidence=t.get("confidence", 0.8),
            )
            for t in data
        ]

    async def explain_relevance(
        self, query: str, paper_title: str, paper_abstract: str, paper_text: str
    ) -> dict:
        if self.profile.abstract_only_relevance:
            text_to_send = ""
        else:
            text_to_send = paper_text[:self.profile.max_context_chars]

        if self.profile.use_compact_prompts:
            prompt = RELEVANCE_PROMPT_COMPACT.format(
                query=query,
                paper_title=paper_title,
                paper_abstract=paper_abstract,
                paper_text=text_to_send,
            )
            max_tokens = 200
        else:
            if not text_to_send:
                text_to_send = paper_text[:10_000]
            prompt = RELEVANCE_PROMPT.format(
                query=query,
                paper_title=paper_title,
                paper_abstract=paper_abstract,
                paper_text=text_to_send,
            )
            max_tokens = 500

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text
        self._track_usage(response, "relevance")
        for attempt in [raw, _extract_json(raw)]:
            try:
                data = json.loads(attempt)
                if "stance" in data and "explanation" in data:
                    return {"stance": data["stance"], "explanation": data["explanation"]}
            except (json.JSONDecodeError, TypeError):
                continue
        m = re.search(r'\{[^{}]*"stance"[^{}]*"explanation"[^{}]*\}', raw)
        if m:
            try:
                data = json.loads(m.group())
                return {"stance": data["stance"], "explanation": data["explanation"]}
            except (json.JSONDecodeError, KeyError):
                pass
        return {"stance": "neutral", "explanation": raw.strip()}

    async def rerank(self, query: str, papers: list[dict]) -> list[dict]:
        """Re-rank papers by relevance using AI."""
        if not papers:
            return []

        papers_block = "\n\n".join(
            f"Paper {i}: {p['title']}\nAbstract: {(p.get('abstract') or '')[:800]}"
            for i, p in enumerate(papers)
        )

        if self.profile.use_compact_prompts:
            prompt = RERANK_PROMPT_COMPACT.format(query=query, papers_block=papers_block)
            max_tokens = min(100 * len(papers), 1500)
        else:
            prompt = RERANK_PROMPT.format(query=query, papers_block=papers_block)
            max_tokens = min(150 * len(papers), 3000)

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        self._track_usage(response, "rerank")
        raw = response.content[0].text
        try:
            data = json.loads(_extract_json(raw))
            if isinstance(data, list):
                return [
                    {"index": item.get("index", 0), "reason": item.get("reason", "")}
                    for item in data
                    if isinstance(item, dict) and "index" in item
                ]
        except (json.JSONDecodeError, KeyError):
            pass
        return await super().rerank(query, papers)

    async def check_claim(
        self, claim: str, supporting_texts: list[dict[str, str]]
    ) -> str:
        limit = self.profile.max_context_chars if self.profile.use_compact_prompts else 3000
        evidence = "\n\n".join(
            f"**{item['title']}**:\n{item['text'][:limit]}" for item in supporting_texts
        )
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=self.profile.max_output_tokens,
            messages=[
                {
                    "role": "user",
                    "content": CLAIM_CHECK_PROMPT.format(claim=claim, evidence=evidence),
                }
            ],
        )
        self._track_usage(response, "claim_check")
        return response.content[0].text

    async def explain_relevance_batch(
        self, query: str, papers: list[dict]
    ) -> list[dict]:
        """Per-paper relevance with full text for best quality."""
        return await super().explain_relevance_batch(query, papers)
