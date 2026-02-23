"""Integration tests for the core engine."""

from pathlib import Path
from unittest.mock import patch

import pytest

from reflens.config import Settings
from reflens.core.engine import RefLensEngine
from reflens.extraction.models import ExtractedAuthor, ExtractedPaper, ExtractedReference


@pytest.fixture
def engine(settings: Settings) -> RefLensEngine:
    return RefLensEngine(settings)


@pytest.fixture
def mock_extracted_paper() -> ExtractedPaper:
    return ExtractedPaper(
        title="Test Paper on AI",
        abstract="A test abstract about artificial intelligence.",
        full_text="This is the full text of the paper about AI research.",
        sections={"Introduction": "AI is important.", "Methods": "We used transformers."},
        authors=[
            ExtractedAuthor(name="Alice Smith", affiliations=["MIT"]),
            ExtractedAuthor(name="Bob Jones", affiliations=["Stanford"]),
        ],
        references=[
            ExtractedReference(
                title="Attention Is All You Need",
                authors="Vaswani et al.",
                year=2017,
            ),
        ],
        doi="10.1234/test",
        year=2024,
    )


class TestEngineIngest:
    def test_ingest_paper(
        self, engine: RefLensEngine, sample_pdf: Path, mock_extracted_paper: ExtractedPaper
    ):
        with patch.object(
            engine.extraction, "extract", return_value=mock_extracted_paper
        ):
            result = engine.ingest_paper(sample_pdf)

        assert result["id"] is not None
        assert result["title"] == "Test Paper on AI"
        assert result["year"] == 2024
        assert result["doi"] == "10.1234/test"

    def test_ingest_stores_pdf(
        self, engine: RefLensEngine, sample_pdf: Path, mock_extracted_paper: ExtractedPaper
    ):
        with patch.object(
            engine.extraction, "extract", return_value=mock_extracted_paper
        ):
            result = engine.ingest_paper(sample_pdf)

        assert result["source_file"] is not None
        assert Path(result["source_file"]).exists()

    def test_ingest_saves_authors(
        self, engine: RefLensEngine, sample_pdf: Path, mock_extracted_paper: ExtractedPaper
    ):
        with patch.object(
            engine.extraction, "extract", return_value=mock_extracted_paper
        ):
            result = engine.ingest_paper(sample_pdf)

        assert len(result["authors"]) == 2
        assert "Alice Smith" in result["authors"]
        assert "Bob Jones" in result["authors"]

    def test_ingest_saves_citations(
        self, engine: RefLensEngine, sample_pdf: Path, mock_extracted_paper: ExtractedPaper
    ):
        with patch.object(
            engine.extraction, "extract", return_value=mock_extracted_paper
        ):
            result = engine.ingest_paper(sample_pdf)

        assert result["citations_count"] == 1

        # Verify via get_paper
        full_paper = engine.get_paper(result["id"])
        assert full_paper is not None
        assert len(full_paper.citing_refs) == 1
        assert full_paper.citing_refs[0].cited_title == "Attention Is All You Need"

    def test_ingest_with_notes(
        self, engine: RefLensEngine, sample_pdf: Path, mock_extracted_paper: ExtractedPaper
    ):
        with patch.object(
            engine.extraction, "extract", return_value=mock_extracted_paper
        ):
            result = engine.ingest_paper(
                sample_pdf, notes="Very interesting paper", reading_status="read"
            )

        full_paper = engine.get_paper(result["id"])
        assert full_paper is not None
        assert len(full_paper.notes) == 1
        assert full_paper.notes[0].content == "Very interesting paper"


class TestEngineList:
    def test_list_papers(
        self, engine: RefLensEngine, sample_pdf: Path, mock_extracted_paper: ExtractedPaper
    ):
        with patch.object(
            engine.extraction, "extract", return_value=mock_extracted_paper
        ):
            engine.ingest_paper(sample_pdf)

        papers = engine.list_papers()
        assert len(papers) == 1

    def test_search_papers(
        self, engine: RefLensEngine, sample_pdf: Path, mock_extracted_paper: ExtractedPaper
    ):
        with patch.object(
            engine.extraction, "extract", return_value=mock_extracted_paper
        ):
            engine.ingest_paper(sample_pdf)

        results = engine.search_papers("AI")
        assert len(results) == 1
        assert results[0]["paper"].title == "Test Paper on AI"

    def test_search_no_results(self, engine: RefLensEngine):
        results = engine.search_papers("nonexistent")
        assert len(results) == 0


class TestEngineDelete:
    def test_delete_paper(
        self, engine: RefLensEngine, sample_pdf: Path, mock_extracted_paper: ExtractedPaper
    ):
        with patch.object(
            engine.extraction, "extract", return_value=mock_extracted_paper
        ):
            result = engine.ingest_paper(sample_pdf)

        assert engine.delete_paper(result["id"]) is True
        assert engine.get_paper(result["id"]) is None
