"""Claude (Anthropic) AI provider implementation."""

import json
import logging
import re

import anthropic

from reflens.ai.provider import AIProvider, GeneratedTag, PaperSummary, ProviderProfile

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
Summarize this paper as JSON with keys: overview, key_contributions (list), methodology, findings, limitations.

Title: {title}
Abstract: {abstract}
{full_text}
JSON only:"""

TAGS_PROMPT_COMPACT = """\
Generate 5-8 topic tags for this paper. JSON list of {{"name": "tag-name", "confidence": 0.0-1.0}}.
Use lowercase-hyphenated format.

Title: {title}
Abstract: {abstract}
{sections_text}
JSON only:"""

RELEVANCE_PROMPT_COMPACT = """\
Does this paper support, contradict, or is neutral to the claim?

Claim: {query}
Paper: {paper_title}
Abstract: {paper_abstract}
{paper_text}
JSON: {{"stance": "supports|contradicts|neutral", "explanation": "1 sentence"}}"""

BATCH_RELEVANCE_PROMPT = """\
Assess each paper against the claim. For each, give stance and explanation.

Claim: {query}

{papers_block}

Respond as JSON array: [{{"paper_index": 0, "stance": "supports|contradicts|neutral", "explanation": "1-2 sentences"}}]"""


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
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.profile = profile or ProviderProfile()

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

        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
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

        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
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

        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text
        try:
            data = json.loads(_extract_json(raw))
            return {"stance": data["stance"], "explanation": data["explanation"]}
        except (json.JSONDecodeError, KeyError):
            return {"stance": "neutral", "explanation": raw}

    async def check_claim(
        self, claim: str, supporting_texts: list[dict[str, str]]
    ) -> str:
        limit = self.profile.max_context_chars if self.profile.use_compact_prompts else 3000
        evidence = "\n\n".join(
            f"**{item['title']}**:\n{item['text'][:limit]}" for item in supporting_texts
        )
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.profile.max_output_tokens,
            messages=[
                {
                    "role": "user",
                    "content": CLAIM_CHECK_PROMPT.format(claim=claim, evidence=evidence),
                }
            ],
        )
        return response.content[0].text

    async def explain_relevance_batch(
        self, query: str, papers: list[dict]
    ) -> list[dict]:
        """Batch relevance for cloud models: one call for all papers."""
        if len(papers) <= 1 or self.profile.use_compact_prompts:
            return await super().explain_relevance_batch(query, papers)

        papers_block = "\n\n".join(
            f"Paper {i}: {p['title']}\nAbstract: {p['abstract'][:1000]}"
            for i, p in enumerate(papers)
        )
        prompt = BATCH_RELEVANCE_PROMPT.format(query=query, papers_block=papers_block)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=200 * len(papers),
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text
        try:
            data = json.loads(_extract_json(raw))
            results = [{"stance": "neutral", "explanation": ""}] * len(papers)
            for item in data:
                idx = item.get("paper_index", 0)
                if 0 <= idx < len(papers):
                    results[idx] = {
                        "stance": item.get("stance", "neutral"),
                        "explanation": item.get("explanation", ""),
                    }
            return results
        except (json.JSONDecodeError, KeyError):
            return await super().explain_relevance_batch(query, papers)
