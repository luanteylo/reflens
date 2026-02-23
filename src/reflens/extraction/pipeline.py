"""Extraction pipeline: orchestrates GROBID and PyMuPDF."""

import logging
from pathlib import Path

from reflens.config import Settings
from reflens.extraction.grobid import GrobidClient
from reflens.extraction.models import ExtractedPaper
from reflens.extraction.pymupdf import PyMuPDFExtractor

logger = logging.getLogger(__name__)


class ExtractionPipeline:
    def __init__(self, settings: Settings):
        self.grobid = GrobidClient(settings.grobid_url)
        self.pymupdf = PyMuPDFExtractor()

    def extract(self, pdf_path: Path) -> ExtractedPaper:
        """Extract structured data from a PDF.

        Tries GROBID first for structured extraction (metadata, references,
        sections). Falls back to PyMuPDF for basic text extraction.
        Always uses PyMuPDF for figure extraction.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Try GROBID for structured extraction
        paper = self._try_grobid(pdf_path)
        if paper is None:
            logger.info("GROBID unavailable, falling back to PyMuPDF for text extraction")
            paper = self.pymupdf.extract_text(pdf_path)

        # Always use PyMuPDF for figures (GROBID doesn't extract images)
        paper.figures = self.pymupdf.extract_figures(pdf_path)

        return paper

    def _try_grobid(self, pdf_path: Path) -> ExtractedPaper | None:
        if not self.grobid.is_available():
            return None
        try:
            return self.grobid.extract(pdf_path)
        except Exception:
            logger.exception("GROBID extraction failed for %s", pdf_path)
            return None
