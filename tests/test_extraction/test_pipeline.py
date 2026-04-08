"""Tests for the extraction pipeline."""

from pathlib import Path
from unittest.mock import patch

import pytest

from reflens.config import Settings
from reflens.extraction.models import ExtractedPaper
from reflens.extraction.pipeline import ExtractionPipeline


class TestExtractionPipeline:
    def test_falls_back_to_pymupdf_when_grobid_unavailable(
        self, settings: Settings, sample_pdf: Path
    ):
        pipeline = ExtractionPipeline(settings)

        # GROBID is not running in tests, so it should fall back to PyMuPDF
        paper = pipeline.extract(sample_pdf)
        assert paper.title != ""
        assert len(paper.full_text) > 0

    def test_raises_on_missing_file(self, settings: Settings):
        pipeline = ExtractionPipeline(settings)
        with pytest.raises(FileNotFoundError):
            pipeline.extract(Path("/nonexistent/paper.pdf"))

    def test_uses_grobid_when_available(self, settings: Settings, sample_pdf: Path):
        pipeline = ExtractionPipeline(settings)

        mock_paper = ExtractedPaper(
            title="GROBID Title",
            abstract="GROBID abstract",
            full_text="GROBID full text",
        )

        with patch.object(pipeline.grobid, "is_available", return_value=True), \
             patch.object(pipeline.grobid, "extract", return_value=mock_paper):
            paper = pipeline.extract(sample_pdf)

        assert paper.title == "GROBID Title"

    def test_always_extracts_figures_with_pymupdf(
        self, settings: Settings, sample_pdf: Path
    ):
        pipeline = ExtractionPipeline(settings)

        mock_paper = ExtractedPaper(title="GROBID Title")

        with patch.object(pipeline.grobid, "is_available", return_value=True), \
             patch.object(pipeline.grobid, "extract", return_value=mock_paper), \
             patch.object(
                 pipeline.pymupdf, "extract_figures", return_value=[]
             ) as mock_figs:
            pipeline.extract(sample_pdf)
            mock_figs.assert_called_once()
