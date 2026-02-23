"""PyMuPDF-based extraction for text and images.

Used as a fallback when GROBID is unavailable, and always used for figure
extraction since GROBID doesn't extract images.
"""

import logging
from pathlib import Path

import fitz  # PyMuPDF

from reflens.extraction.models import ExtractedFigure, ExtractedPaper

logger = logging.getLogger(__name__)


class PyMuPDFExtractor:
    def extract_text(self, pdf_path: Path) -> ExtractedPaper:
        """Extract text from PDF using PyMuPDF. Basic extraction without
        structured metadata -- use GROBID when available."""
        doc = fitz.open(str(pdf_path))
        pages_text = []

        for page in doc:
            pages_text.append(page.get_text())

        full_text = "\n\n".join(pages_text)

        # Try to extract title from first page (usually the largest font)
        title = self._guess_title(doc)

        paper = ExtractedPaper(
            title=title,
            full_text=full_text,
        )
        doc.close()
        return paper

    def extract_figures(self, pdf_path: Path) -> list[ExtractedFigure]:
        """Extract embedded images from PDF."""
        doc = fitz.open(str(pdf_path))
        figures = []
        fig_index = 0

        for page_num, page in enumerate(doc):
            for img_info in page.get_images():
                xref = img_info[0]
                try:
                    pix = fitz.Pixmap(doc, xref)
                    # Skip tiny images (likely icons/logos)
                    if pix.width < 100 or pix.height < 100:
                        if pix.alpha:
                            pix = fitz.Pixmap(fitz.csRGB, pix)
                        continue

                    # Convert CMYK to RGB if needed
                    if pix.n > 4:
                        pix = fitz.Pixmap(fitz.csRGB, pix)

                    figures.append(
                        ExtractedFigure(
                            index=fig_index,
                            image_bytes=pix.tobytes("png"),
                            page=page_num,
                        )
                    )
                    fig_index += 1
                except Exception:
                    logger.warning("Failed to extract image xref=%d on page %d", xref, page_num)

        doc.close()
        return figures

    def _guess_title(self, doc: fitz.Document) -> str:
        """Heuristic: the largest text block on the first page is likely the title."""
        if len(doc) == 0:
            return ""

        page = doc[0]
        blocks = page.get_text("dict")["blocks"]

        best_text = ""
        best_size = 0.0

        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    if span["size"] > best_size and len(span["text"].strip()) > 5:
                        best_size = span["size"]
                        best_text = span["text"].strip()

        return best_text
