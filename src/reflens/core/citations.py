"""Citation format helpers shared by API and MCP."""

import re

import httpx


def make_bibtex_key(authors: list, year: int | None, title: str) -> str:
    """Generate a BibTeX citation key like 'smith2024transformers'."""
    first_author = ""
    if authors:
        name = authors[0].name if hasattr(authors[0], "name") else str(authors[0])
        first_author = re.sub(r"[^a-zA-Z]", "", name.split()[-1]).lower()
    yr = str(year) if year else ""
    title_word = ""
    for word in title.split():
        cleaned = re.sub(r"[^a-zA-Z]", "", word).lower()
        if len(cleaned) > 3:
            title_word = cleaned
            break
    return f"{first_author}{yr}{title_word}" or "unknown"


def build_bibtex_from_metadata(paper) -> str:
    """Build a basic BibTeX entry from paper metadata."""
    key = make_bibtex_key(paper.authors, paper.year, paper.title)
    authors_str = " and ".join(a.name for a in paper.authors) if paper.authors else ""

    lines = [f"@article{{{key},"]
    lines.append(f"  title = {{{paper.title}}},")
    if authors_str:
        lines.append(f"  author = {{{authors_str}}},")
    if paper.year:
        lines.append(f"  year = {{{paper.year}}},")
    if paper.doi:
        lines.append(f"  doi = {{{paper.doi}}},")
    lines.append("}")
    return "\n".join(lines)


def build_short_ref(paper) -> str:
    """Build 'Adams et al., 2004' style short reference."""
    if not paper.authors:
        first = "Unknown"
    elif len(paper.authors) == 1:
        first = paper.authors[0].name.split()[-1]
    elif len(paper.authors) == 2:
        first = (
            paper.authors[0].name.split()[-1]
            + " and "
            + paper.authors[1].name.split()[-1]
        )
    else:
        first = paper.authors[0].name.split()[-1] + " et al."
    year = str(paper.year) if paper.year else "n.d."
    return f"{first}, {year}"


def build_full_ref(paper) -> str:
    """Build a full text reference from metadata."""
    parts = []
    if paper.authors:
        names = []
        for a in paper.authors:
            name_parts = a.name.split()
            if len(name_parts) >= 2:
                initials = ".".join(p[0].upper() for p in name_parts[:-1]) + "."
                names.append(f"{name_parts[-1]}, {initials}")
            else:
                names.append(a.name)
        parts.append(", ".join(names))
    if paper.year:
        parts.append(f"({paper.year})")
    parts.append(paper.title)
    if paper.doi:
        parts.append(f"https://doi.org/{paper.doi}")
    return "\n".join(parts)


async def fetch_bibtex_from_doi(doi: str) -> str | None:
    """Fetch BibTeX from doi.org. Returns None on failure."""
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(
                f"https://doi.org/{doi}",
                headers={"Accept": "application/x-bibtex"},
            )
            if resp.status_code == 200 and "@" in resp.text:
                return resp.text.strip()
    except httpx.HTTPError:
        pass
    return None


async def fetch_apa_from_doi(doi: str) -> str | None:
    """Fetch APA-formatted citation from doi.org. Returns None on failure."""
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(
                f"https://doi.org/{doi}",
                headers={"Accept": "text/x-bibliography; style=apa"},
            )
            if resp.status_code == 200 and resp.text.strip():
                return resp.text.strip()
    except httpx.HTTPError:
        pass
    return None


async def get_citation_formats(paper) -> dict:
    """Return {short, full, bibtex} for a paper, using doi.org when possible."""
    short_ref = build_short_ref(paper)
    bibtex = build_bibtex_from_metadata(paper)
    full_ref = build_full_ref(paper)
    apa = None

    if paper.doi:
        fetched_bibtex = await fetch_bibtex_from_doi(paper.doi)
        if fetched_bibtex:
            bibtex = fetched_bibtex
        apa = await fetch_apa_from_doi(paper.doi)

    return {
        "short": short_ref,
        "full": apa or full_ref,
        "bibtex": bibtex,
    }


async def get_bibtex(paper) -> str:
    """Get BibTeX for a paper, preferring doi.org when available."""
    if paper.doi:
        fetched = await fetch_bibtex_from_doi(paper.doi)
        if fetched:
            return fetched
    return build_bibtex_from_metadata(paper)
