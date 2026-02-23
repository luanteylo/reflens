"""Data models for extraction results (decoupled from DB models)."""

from dataclasses import dataclass, field


@dataclass
class ExtractedAuthor:
    name: str
    affiliations: list[str] = field(default_factory=list)


@dataclass
class ExtractedReference:
    title: str
    authors: str = ""
    year: int | None = None
    doi: str | None = None
    raw: str = ""


@dataclass
class ExtractedFigure:
    index: int
    image_bytes: bytes
    caption: str = ""
    page: int = 0


@dataclass
class ExtractedPaper:
    title: str = ""
    abstract: str = ""
    full_text: str = ""
    sections: dict[str, str] = field(default_factory=dict)
    authors: list[ExtractedAuthor] = field(default_factory=list)
    references: list[ExtractedReference] = field(default_factory=list)
    figures: list[ExtractedFigure] = field(default_factory=list)
    doi: str | None = None
    year: int | None = None
