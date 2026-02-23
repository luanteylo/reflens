"""GROBID client for structured extraction from scientific PDFs.

GROBID parses PDFs into TEI XML, giving us structured access to title,
authors, abstract, sections, and references.
"""

import logging
import re
from pathlib import Path

import httpx
from lxml import etree

from reflens.extraction.models import ExtractedAuthor, ExtractedPaper, ExtractedReference

logger = logging.getLogger(__name__)

TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}


class GrobidClient:
    def __init__(self, base_url: str = "http://localhost:8070"):
        self.base_url = base_url.rstrip("/")

    def is_available(self) -> bool:
        try:
            resp = httpx.get(f"{self.base_url}/api/isalive", timeout=5)
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    def extract(self, pdf_path: Path) -> ExtractedPaper:
        """Send a PDF to GROBID and parse the TEI XML response."""
        with open(pdf_path, "rb") as f:
            resp = httpx.post(
                f"{self.base_url}/api/processFulltextDocument",
                files={"input": (pdf_path.name, f, "application/pdf")},
                timeout=120,
            )
        resp.raise_for_status()
        return self._parse_tei(resp.text)

    def _parse_tei(self, xml_text: str) -> ExtractedPaper:
        root = etree.fromstring(xml_text.encode("utf-8"))
        paper = ExtractedPaper()

        paper.title = self._extract_title(root)
        paper.authors = self._extract_authors(root)
        paper.abstract = self._extract_abstract(root)
        paper.doi = self._extract_doi(root)
        paper.year = self._extract_year(root)
        paper.sections = self._extract_sections(root)
        paper.full_text = "\n\n".join(paper.sections.values())
        paper.references = self._extract_references(root)

        return paper

    def _text(self, element: etree._Element | None) -> str:
        if element is None:
            return ""
        return " ".join(element.itertext()).strip()

    def _extract_title(self, root: etree._Element) -> str:
        el = root.find(".//tei:titleStmt/tei:title", TEI_NS)
        return self._text(el)

    def _extract_authors(self, root: etree._Element) -> list[ExtractedAuthor]:
        authors = []
        for author_el in root.findall(
            ".//tei:fileDesc/tei:sourceDesc//tei:author", TEI_NS
        ):
            persname = author_el.find("tei:persName", TEI_NS)
            if persname is None:
                continue

            forename = self._text(persname.find("tei:forename", TEI_NS))
            surname = self._text(persname.find("tei:surname", TEI_NS))
            name = f"{forename} {surname}".strip()
            if not name:
                continue

            affiliations = []
            for aff in author_el.findall("tei:affiliation", TEI_NS):
                org = aff.find("tei:orgName", TEI_NS)
                if org is not None:
                    affiliations.append(self._text(org))

            authors.append(ExtractedAuthor(name=name, affiliations=affiliations))
        return authors

    def _extract_abstract(self, root: etree._Element) -> str:
        el = root.find(".//tei:profileDesc/tei:abstract", TEI_NS)
        return self._text(el)

    def _extract_doi(self, root: etree._Element) -> str | None:
        for idno in root.findall(".//tei:fileDesc//tei:idno", TEI_NS):
            if idno.get("type") == "DOI":
                return self._text(idno) or None
        return None

    def _extract_year(self, root: etree._Element) -> int | None:
        date_el = root.find(".//tei:fileDesc//tei:date", TEI_NS)
        if date_el is not None:
            when = date_el.get("when", "")
            match = re.match(r"(\d{4})", when)
            if match:
                return int(match.group(1))
        return None

    def _extract_sections(self, root: etree._Element) -> dict[str, str]:
        sections: dict[str, str] = {}
        body = root.find(".//tei:body", TEI_NS)
        if body is None:
            return sections

        for i, div in enumerate(body.findall("tei:div", TEI_NS)):
            head = div.find("tei:head", TEI_NS)
            section_name = self._text(head) if head is not None else f"Section {i + 1}"
            section_text = self._text(div)
            if section_text:
                sections[section_name] = section_text

        return sections

    def _extract_references(self, root: etree._Element) -> list[ExtractedReference]:
        refs = []
        for bib in root.findall(".//tei:listBibl/tei:biblStruct", TEI_NS):
            title_el = bib.find(".//tei:title", TEI_NS)
            title = self._text(title_el)
            if not title:
                continue

            # Authors
            author_names = []
            for author in bib.findall(".//tei:author/tei:persName", TEI_NS):
                forename = self._text(author.find("tei:forename", TEI_NS))
                surname = self._text(author.find("tei:surname", TEI_NS))
                author_names.append(f"{forename} {surname}".strip())

            # Year
            year = None
            date_el = bib.find(".//tei:date", TEI_NS)
            if date_el is not None:
                match = re.match(r"(\d{4})", date_el.get("when", ""))
                if match:
                    year = int(match.group(1))

            # DOI
            doi = None
            for idno in bib.findall(".//tei:idno", TEI_NS):
                if idno.get("type") == "DOI":
                    doi = self._text(idno) or None

            raw = etree.tostring(bib, encoding="unicode", method="text").strip()

            refs.append(
                ExtractedReference(
                    title=title,
                    authors=", ".join(author_names),
                    year=year,
                    doi=doi,
                    raw=raw,
                )
            )
        return refs
