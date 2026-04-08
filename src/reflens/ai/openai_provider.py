"""OpenAI AI provider implementation."""

import json
import logging

import openai

from reflens.ai.claude import (
    CLAIM_CHECK_PROMPT,
    RELEVANCE_PROMPT,
    SUMMARIZE_PROMPT,
    TAGS_PROMPT,
    _extract_json,
)
from reflens.ai.provider import AIProvider, GeneratedTag, PaperSummary

logger = logging.getLogger(__name__)


class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

    async def summarize(self, title: str, abstract: str, full_text: str) -> PaperSummary:
        truncated = full_text[:80_000] if len(full_text) > 80_000 else full_text

        response = self.client.chat.completions.create(
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
        text = response.choices[0].message.content or ""
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

        response = self.client.chat.completions.create(
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
        text = response.choices[0].message.content or ""
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
        response = self.client.chat.completions.create(
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
        raw = response.choices[0].message.content or ""
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
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": CLAIM_CHECK_PROMPT.format(claim=claim, evidence=evidence),
                }
            ],
        )
        return response.choices[0].message.content or ""
