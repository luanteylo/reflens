"""Abstract AI provider interface.

All AI operations go through this interface so we can swap between
Claude, OpenAI, or any other provider.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ProviderProfile:
    """Declares a provider's capabilities and limits."""

    max_context_chars: int = 300_000  # conservative default for cloud models
    max_output_tokens: int = 2000
    use_compact_prompts: bool = False
    abstract_only_relevance: bool = False  # skip full_text for relevance


@dataclass
class PaperSummary:
    overview: str = ""
    key_contributions: list[str] = field(default_factory=list)
    methodology: str = ""
    findings: str = ""
    limitations: str = ""


@dataclass
class GeneratedTag:
    name: str
    section: str | None = None
    confidence: float = 1.0


@dataclass
class RankedReference:
    paper_id: str
    title: str
    relevance_score: float
    explanation: str


# Approximate cost per 1M tokens (input/output) for known models
MODEL_COSTS: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-sonnet-4-20250514": (3.0, 15.0),
    "gpt-4o": (2.5, 10.0),
    "gpt-4o-mini": (0.15, 0.6),
    "gpt-4-turbo": (10.0, 30.0),
}


@dataclass
class UsageInfo:
    provider: str = ""
    model: str = ""
    operation: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0

    def compute_cost(self) -> None:
        costs = MODEL_COSTS.get(self.model)
        if costs:
            input_cost, output_cost = costs
            self.cost_usd = (
                self.prompt_tokens * input_cost / 1_000_000
                + self.completion_tokens * output_cost / 1_000_000
            )


class AIProvider(ABC):
    profile: ProviderProfile = ProviderProfile()
    last_usage: UsageInfo | None = None

    @abstractmethod
    async def summarize(self, title: str, abstract: str, full_text: str) -> PaperSummary:
        """Generate a structured summary of a paper."""

    @abstractmethod
    async def generate_tags(
        self, title: str, abstract: str, sections: dict[str, str]
    ) -> list[GeneratedTag]:
        """Generate topic tags for a paper, mapped to sections."""

    @abstractmethod
    async def explain_relevance(
        self, query: str, paper_title: str, paper_abstract: str, paper_text: str
    ) -> dict:
        """Assess whether a paper supports, contradicts, or is neutral to a claim.

        Returns {"stance": str, "explanation": str}.
        """

    @abstractmethod
    async def check_claim(
        self, claim: str, supporting_texts: list[dict[str, str]]
    ) -> str:
        """Check whether a claim is supported by the given paper excerpts."""

    async def explain_relevance_batch(
        self, query: str, papers: list[dict]
    ) -> list[dict]:
        """Assess multiple papers. Default: sequential calls."""
        results = []
        for p in papers:
            r = await self.explain_relevance(
                query, p["title"], p["abstract"], p["text"]
            )
            results.append(r)
        return results
