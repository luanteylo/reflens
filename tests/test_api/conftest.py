"""Shared fixtures for API tests."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from reflens.api.app import create_app
from reflens.api.deps import set_engine
from reflens.db.models import ReadingStatus


def _make_paper(**overrides):
    """Create a mock paper object with sensible defaults."""
    paper = MagicMock()
    paper.id = overrides.get("id", "paper-1")
    paper.title = overrides.get("title", "Test Paper")
    paper.abstract = overrides.get("abstract", "An abstract")
    paper.year = overrides.get("year", 2024)
    paper.doi = overrides.get("doi", "10.1234/test")
    paper.ai_summary = overrides.get("ai_summary", None)
    paper.created_at = overrides.get("created_at", "2024-01-01T00:00:00Z")
    paper.updated_at = overrides.get("updated_at", "2024-01-01T00:00:00Z")
    paper.full_text = overrides.get("full_text", "Full text here")
    paper.sections = overrides.get("sections", {"Intro": "text"})
    paper.source_file = overrides.get("source_file", "/path/to/file.pdf")
    paper.ai_key_contributions = overrides.get("ai_key_contributions", None)
    paper.ai_methodology = overrides.get("ai_methodology", None)
    paper.ai_findings = overrides.get("ai_findings", None)
    paper.ai_limitations = overrides.get("ai_limitations", None)

    # Relations
    author = MagicMock()
    author.id = "author-1"
    author.name = "Alice Smith"
    author.affiliations = ["MIT"]
    paper.authors = overrides.get("authors", [author])
    paper.tags = overrides.get("tags", [])
    paper.citing_refs = overrides.get("citing_refs", [])
    paper.notes = overrides.get("notes", [])
    return paper


def _make_note(**overrides):
    note = MagicMock()
    note.id = overrides.get("id", "note-1")
    note.content = overrides.get("content", "My notes")
    note.reading_status = overrides.get("reading_status", ReadingStatus.UNREAD)
    note.relevance_score = overrides.get("relevance_score", None)
    note.is_favorite = overrides.get("is_favorite", False)
    note.created_at = overrides.get("created_at", "2024-01-01T00:00:00Z")
    note.updated_at = overrides.get("updated_at", "2024-01-01T00:00:00Z")
    return note


def _make_citation(**overrides):
    c = MagicMock()
    c.id = overrides.get("id", "cite-1")
    c.cited_title = overrides.get("cited_title", "Cited Paper")
    c.cited_authors = overrides.get("cited_authors", "Doe et al.")
    c.cited_year = overrides.get("cited_year", 2020)
    c.cited_doi = overrides.get("cited_doi", None)
    c.cited_paper_id = overrides.get("cited_paper_id", None)
    c.raw_reference = overrides.get("raw_reference", "Doe et al., 2020")
    return c


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    engine.list_papers.return_value = [_make_paper()]
    engine.count_papers.return_value = 1
    engine.get_paper.return_value = _make_paper()
    engine.search_papers.return_value = [{"paper": _make_paper(), "score": 0.85}]
    engine.delete_paper.return_value = True
    engine.get_citations.return_value = [_make_citation()]
    engine.update_notes.return_value = _make_note()
    engine.list_tags.return_value = []
    engine.get_tag.return_value = None
    engine.list_papers_by_tag.return_value = []
    engine.list_authors.return_value = []
    engine.count_authors.return_value = 0
    engine.get_author.return_value = None
    engine.list_papers_by_author.return_value = []
    engine.ingest_paper.return_value = {
        "id": "paper-1",
        "title": "Uploaded Paper",
        "authors": ["Alice"],
        "year": 2024,
        "doi": None,
        "citations_count": 0,
    }
    engine.summarize_paper = AsyncMock(return_value=_make_paper(
        ai_summary="Summary text",
        ai_key_contributions=["contrib1"],
        ai_methodology="Methods",
        ai_findings="Findings",
        ai_limitations="Limits",
    ))
    engine.tag_paper = AsyncMock(return_value=["ml", "nlp"])
    engine.find_references = AsyncMock(return_value=[
        {"paper": _make_paper(), "score": 0.92, "explanation": None},
    ])
    return engine


@pytest.fixture
def client(mock_engine):
    set_engine(mock_engine)
    app = create_app()
    with TestClient(app) as c:
        yield c
    set_engine(None)
