"""Abstract AI provider interface.

All AI operations go through this interface so we can swap between
Claude, OpenAI, or any other provider.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


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


class AIProvider(ABC):
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
    ) -> str:
        """Explain why a paper is relevant to a query."""

    @abstractmethod
    async def check_claim(
        self, claim: str, supporting_texts: list[dict[str, str]]
    ) -> str:
        """Check whether a claim is supported by the given paper excerpts."""
