"""Pydantic request/response models for the REST API."""

from datetime import datetime

from pydantic import BaseModel, Field

# -- Papers --


class AuthorResponse(BaseModel):
    id: str
    name: str
    affiliations: list[str] | None = None


class TagResponse(BaseModel):
    id: str
    name: str
    parent_id: str | None = None


class PaperTagResponse(BaseModel):
    id: str
    tag_id: str
    tag_name: str
    section: str | None = None
    confidence: float
    source: str


class CitationResponse(BaseModel):
    id: str
    cited_title: str
    cited_authors: str | None = None
    cited_year: int | None = None
    cited_doi: str | None = None
    cited_paper_id: str | None = None
    raw_reference: str | None = None


class UserNoteResponse(BaseModel):
    id: str
    content: str | None = None
    reading_status: str
    relevance_score: int | None = None
    is_favorite: bool
    created_at: datetime
    updated_at: datetime


class PaperSummary(BaseModel):
    """Lightweight paper representation for list views."""

    id: str
    title: str
    abstract: str | None = None
    year: int | None = None
    doi: str | None = None
    ai_summary: str | None = None
    created_at: datetime
    authors: list[AuthorResponse] = []
    tags: list[PaperTagResponse] = []


class PaperDetail(PaperSummary):
    """Full paper representation with all relations."""

    full_text: str | None = None
    sections: dict | None = None
    source_file: str | None = None
    ai_key_contributions: list[str] | None = None
    ai_methodology: str | None = None
    ai_findings: str | None = None
    ai_limitations: str | None = None
    updated_at: datetime
    citations: list[CitationResponse] = []
    notes: list[UserNoteResponse] = []


class PaperListResponse(BaseModel):
    papers: list[PaperSummary]
    total: int
    limit: int
    offset: int


class PaperUploadResponse(BaseModel):
    id: str
    title: str
    authors: list[str]
    year: int | None = None
    doi: str | None = None
    citations_count: int
    indexed: bool = False


class SummarizeResponse(BaseModel):
    id: str
    ai_summary: str | None = None
    ai_key_contributions: list[str] | None = None
    ai_methodology: str | None = None
    ai_findings: str | None = None
    ai_limitations: str | None = None


class TagGenerateResponse(BaseModel):
    id: str
    tags: list[str]


class NoteUpdateRequest(BaseModel):
    content: str | None = None
    reading_status: str = "unread"
    relevance_score: int | None = Field(default=None, ge=1, le=5)
    is_favorite: bool = False


class BulkActionResponse(BaseModel):
    done: list[str]
    failed: list[str]


class TaskCreatedResponse(BaseModel):
    task_id: str


class TaskStatusResponse(BaseModel):
    id: str
    kind: str
    status: str
    total: int
    completed: int
    failed: int
    done_titles: list[str]
    failed_titles: list[str]
    error: str | None = None


# -- Search --


class SearchResultItem(BaseModel):
    paper: PaperSummary
    score: float | None = None


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    query: str


class ReferencesRequest(BaseModel):
    text: str
    limit: int = Field(default=5, ge=1, le=50)
    explain: bool = False
    tag_ids: list[str] | None = None
    collection_id: str | None = None


class ReferenceResult(BaseModel):
    paper: PaperSummary
    score: float
    explanation: str | None = None
    stance: str | None = None


class ReferencesResponse(BaseModel):
    results: list[ReferenceResult]
    text: str


# -- Authors --


class AuthorListResponse(BaseModel):
    authors: list[AuthorResponse]
    total: int
    limit: int
    offset: int


# -- Tags --


class TagListResponse(BaseModel):
    tags: list[TagResponse]


class TagPapersResponse(BaseModel):
    tag: TagResponse
    papers: list[PaperSummary]


# -- Health --


class EmbeddingStatusResponse(BaseModel):
    total_papers: int
    indexed_chunks: int


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str


# -- Saved Searches --


class SaveSearchRequest(BaseModel):
    text: str
    collection_id: str | None = None
    results: list[ReferenceResult] | None = None


class SavedSearchResponse(BaseModel):
    id: str
    text: str
    collection_id: str | None = None
    collection_name: str | None = None
    results: list[ReferenceResult] | None = None
    created_at: datetime


class SavedSearchListResponse(BaseModel):
    searches: list[SavedSearchResponse]
