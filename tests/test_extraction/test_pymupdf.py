"""Tests for PyMuPDF extraction."""

from pathlib import Path

from reflens.extraction.pymupdf import PyMuPDFExtractor


class TestPyMuPDFExtractor:
    def setup_method(self):
        self.extractor = PyMuPDFExtractor()

    def test_extract_text(self, sample_pdf: Path):
        paper = self.extractor.extract_text(sample_pdf)
        assert paper.title != ""
        assert len(paper.full_text) > 0

    def test_extract_text_contains_content(self, sample_pdf: Path):
        paper = self.extractor.extract_text(sample_pdf)
        assert "Deep Learning" in paper.full_text or "deep learning" in paper.full_text.lower()

    def test_extract_figures_from_text_pdf(self, sample_pdf: Path):
        figures = self.extractor.extract_figures(sample_pdf)
        # Our test PDF has no embedded images
        assert isinstance(figures, list)

    def test_guess_title(self, sample_pdf: Path):
        paper = self.extractor.extract_text(sample_pdf)
        # Title should be the largest text, which we set as the first line
        assert len(paper.title) > 0
