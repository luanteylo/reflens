"""OpenAI AI provider implementation. Also used for Ollama via base_url."""

import json
import logging

import openai

from reflens.ai.claude import (
    BATCH_RELEVANCE_PROMPT,
    CLAIM_CHECK_PROMPT,
    RELEVANCE_PROMPT,
    RELEVANCE_PROMPT_COMPACT,
    SUMMARIZE_PROMPT,
    SUMMARIZE_PROMPT_COMPACT,
    TAGS_PROMPT,
    TAGS_PROMPT_COMPACT,
    _extract_json,
)
from reflens.ai.provider import AIProvider, GeneratedTag, PaperSummary, ProviderProfile

logger = logging.getLogger(__name__)


class OpenAIProvider(AIProvider):
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: str | None = None,
        profile: ProviderProfile | None = None,
    ):
        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = openai.OpenAI(**kwargs)
        self.model = model
        self.profile = profile or ProviderProfile()

    def _chat(self, prompt: str, max_tokens: int) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""

    async def summarize(self, title: str, abstract: str, full_text: str) -> PaperSummary:
        if self.profile.use_compact_prompts:
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

        text = self._chat(prompt, max_tokens)
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

        text = self._chat(prompt, max_tokens)
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

        raw = self._chat(prompt, max_tokens)
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
        return self._chat(
            CLAIM_CHECK_PROMPT.format(claim=claim, evidence=evidence),
            self.profile.max_output_tokens,
        )

    async def explain_relevance_batch(
        self, query: str, papers: list[dict]
    ) -> list[dict]:
        """Batch relevance: one call for all papers (cloud), sequential (local)."""
        if len(papers) <= 1 or self.profile.use_compact_prompts:
            return await super().explain_relevance_batch(query, papers)

        papers_block = "\n\n".join(
            f"Paper {i}: {p['title']}\nAbstract: {p['abstract'][:1000]}"
            for i, p in enumerate(papers)
        )
        prompt = BATCH_RELEVANCE_PROMPT.format(query=query, papers_block=papers_block)

        raw = self._chat(prompt, 200 * len(papers))
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
