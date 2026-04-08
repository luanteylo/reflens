"""Claude (Anthropic) AI provider implementation."""

import json
import logging
import re

import anthropic

from reflens.ai.provider import AIProvider, GeneratedTag, PaperSummary

logger = logging.getLogger(__name__)

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
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    async def summarize(self, title: str, abstract: str, full_text: str) -> PaperSummary:
        # Truncate to stay within context limits
        truncated = full_text[:80_000] if len(full_text) > 80_000 else full_text

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": SUMMARIZE_PROMPT.format(
                        title=title, abstract=abstract, full_text=truncated
                    ),
                }
            ],
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
        sections_text = "\n\n".join(
            f"## {name}\n{text[:2000]}" for name, text in sections.items()
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": TAGS_PROMPT.format(
                        title=title, abstract=abstract, sections_text=sections_text
                    ),
                }
            ],
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
        truncated = paper_text[:10_000]
        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            messages=[
                {
                    "role": "user",
                    "content": RELEVANCE_PROMPT.format(
                        query=query,
                        paper_title=paper_title,
                        paper_abstract=paper_abstract,
                        paper_text=truncated,
                    ),
                }
            ],
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
        evidence = "\n\n".join(
            f"**{item['title']}**:\n{item['text'][:3000]}" for item in supporting_texts
        )
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": CLAIM_CHECK_PROMPT.format(claim=claim, evidence=evidence),
                }
            ],
        )
        return response.content[0].text
