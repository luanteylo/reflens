"""Paper endpoints: CRUD, upload, summarize, tag, notes."""

import asyncio
import re
import tempfile
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

from reflens.api.deps import get_engine, get_user_id
from reflens.api.schemas import (
    CitationResponse,
    NoteUpdateRequest,
    PaperDetail,
    PaperListResponse,
    PaperSummary,
    PaperTagResponse,
    PaperUploadResponse,
    SummarizeResponse,
    TagGenerateResponse,
    TaskCreatedResponse,
    UserNoteResponse,
)
from reflens.api.tasks import get_task_registry, run_bulk_task
from reflens.core.engine import RefLensEngine

router = APIRouter(prefix="/papers", tags=["papers"])


def _paper_to_summary(paper) -> PaperSummary:
    return PaperSummary(
        id=paper.id,
        title=paper.title,
        abstract=paper.abstract,
        year=paper.year,
        doi=paper.doi,
        ai_summary=paper.ai_summary,
        created_at=paper.created_at,
        authors=[
            {"id": a.id, "name": a.name, "affiliations": a.affiliations}
            for a in paper.authors
        ],
        tags=[
            PaperTagResponse(
                id=pt.id,
                tag_id=pt.tag_id,
                tag_name=pt.tag.name if hasattr(pt, "tag") and pt.tag else "",
                section=pt.section,
                confidence=pt.confidence,
                source=pt.source,
            )
            for pt in paper.tags
        ],
    )


def _paper_to_detail(paper) -> PaperDetail:
    return PaperDetail(
        id=paper.id,
        title=paper.title,
        abstract=paper.abstract,
        year=paper.year,
        doi=paper.doi,
        ai_summary=paper.ai_summary,
        created_at=paper.created_at,
        full_text=paper.full_text,
        sections=paper.sections,
        source_file=paper.source_file,
        ai_key_contributions=paper.ai_key_contributions,
        ai_methodology=paper.ai_methodology,
        ai_findings=paper.ai_findings,
        ai_limitations=paper.ai_limitations,
        updated_at=paper.updated_at,
        authors=[
            {"id": a.id, "name": a.name, "affiliations": a.affiliations}
            for a in paper.authors
        ],
        tags=[
            PaperTagResponse(
                id=pt.id,
                tag_id=pt.tag_id,
                tag_name=pt.tag.name if hasattr(pt, "tag") and pt.tag else "",
                section=pt.section,
                confidence=pt.confidence,
                source=pt.source,
            )
            for pt in paper.tags
        ],
        citations=[
            CitationResponse(
                id=c.id,
                cited_title=c.cited_title,
                cited_authors=c.cited_authors,
                cited_year=c.cited_year,
                cited_doi=c.cited_doi,
                cited_paper_id=c.cited_paper_id,
                raw_reference=c.raw_reference,
            )
            for c in paper.citing_refs
        ],
        notes=[
            UserNoteResponse(
                id=n.id,
                content=n.content,
                reading_status=n.reading_status.value,
                relevance_score=n.relevance_score,
                is_favorite=n.is_favorite,
                created_at=n.created_at,
                updated_at=n.updated_at,
            )
            for n in paper.notes
        ],
    )


@router.post("/upload", response_model=PaperUploadResponse)
async def upload_paper(
    file: UploadFile,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        result = engine.ingest_paper(tmp_path, user_id=user_id)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        tmp_path.unlink(missing_ok=True)

    return PaperUploadResponse(**result)


class BulkRequest(BaseModel):
    model_id: str | None = None
    paper_ids: list[str] | None = None
    user_prompt: str | None = None


@router.post("/summarize-all", response_model=TaskCreatedResponse)
async def summarize_all(
    body: BulkRequest | None = None,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    registry = get_task_registry()
    task = registry.create("summarize-all")
    if task.status.value == "pending":
        asyncio.create_task(
            run_bulk_task(
                task.id, registry, engine, "summarize-all", user_id,
                body.model_id if body else None,
                body.paper_ids if body else None,
                body.user_prompt if body else None,
            )
        )
    return TaskCreatedResponse(task_id=task.id)


@router.post("/tag-all", response_model=TaskCreatedResponse)
async def tag_all(
    body: BulkRequest | None = None,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    registry = get_task_registry()
    task = registry.create("tag-all")
    if task.status.value == "pending":
        asyncio.create_task(
            run_bulk_task(
                task.id, registry, engine, "tag-all", user_id,
                body.model_id if body else None,
                body.paper_ids if body else None,
            )
        )
    return TaskCreatedResponse(task_id=task.id)


@router.get("", response_model=PaperListResponse)
def list_papers(
    limit: int = 50,
    offset: int = 0,
    tag_ids: list[str] | None = Query(None),
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    if tag_ids:
        papers = engine.list_papers_by_tags(tag_ids, user_id=user_id, limit=limit, offset=offset)
        total = engine.count_papers_by_tags(tag_ids, user_id=user_id)
    else:
        papers = engine.list_papers(user_id=user_id, limit=limit, offset=offset)
        total = engine.count_papers(user_id=user_id)
    return PaperListResponse(
        papers=[_paper_to_summary(p) for p in papers],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{paper_id}", response_model=PaperDetail)
def get_paper(
    paper_id: str,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    paper = engine.get_paper(paper_id, user_id=user_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    return _paper_to_detail(paper)


def _make_bibtex_key(authors: list, year: int | None, title: str) -> str:
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


def _build_bibtex_from_metadata(paper) -> str:
    """Build a basic BibTeX entry from paper metadata."""
    key = _make_bibtex_key(paper.authors, paper.year, paper.title)
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


@router.get("/{paper_id}/bibtex", response_class=PlainTextResponse)
async def get_bibtex(
    paper_id: str,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    paper = engine.get_paper(paper_id, user_id=user_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    # Try fetching from doi.org if DOI is available
    if paper.doi:
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                resp = await client.get(
                    f"https://doi.org/{paper.doi}",
                    headers={"Accept": "application/x-bibtex"},
                )
                if resp.status_code == 200 and "@" in resp.text:
                    return PlainTextResponse(resp.text.strip())
        except httpx.HTTPError:
            pass

    # Fallback: build from metadata
    return PlainTextResponse(_build_bibtex_from_metadata(paper))


def _build_short_ref(paper) -> str:
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


def _build_full_ref(paper) -> str:
    """Build a full text reference from metadata."""
    parts = []
    # Authors
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
    # Year
    if paper.year:
        parts.append(f"({paper.year})")
    # Title
    parts.append(paper.title)
    # DOI
    if paper.doi:
        parts.append(f"https://doi.org/{paper.doi}")
    return "\n".join(parts)


@router.get("/{paper_id}/cite")
async def get_citation_formats(
    paper_id: str,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    paper = engine.get_paper(paper_id, user_id=user_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")

    short_ref = _build_short_ref(paper)
    bibtex = _build_bibtex_from_metadata(paper)
    full_ref = _build_full_ref(paper)
    apa = None

    if paper.doi:
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                # Fetch BibTeX
                resp = await client.get(
                    f"https://doi.org/{paper.doi}",
                    headers={"Accept": "application/x-bibtex"},
                )
                if resp.status_code == 200 and "@" in resp.text:
                    bibtex = resp.text.strip()

                # Fetch APA
                resp = await client.get(
                    f"https://doi.org/{paper.doi}",
                    headers={"Accept": "text/x-bibliography; style=apa"},
                )
                if resp.status_code == 200 and resp.text.strip():
                    apa = resp.text.strip()
        except httpx.HTTPError:
            pass

    result = {
        "short": short_ref,
        "full": apa or full_ref,
        "bibtex": bibtex,
    }
    return result


@router.get("/{paper_id}/pdf")
def get_pdf(
    paper_id: str,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    paper = engine.get_paper(paper_id, user_id=user_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    if not paper.source_file:
        raise HTTPException(status_code=404, detail="No PDF stored for this paper")
    pdf_path = Path(paper.source_file)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found on disk")
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"},
    )


class PaperUpdateRequest(BaseModel):
    doi: str | None = None
    year: int | None = None
    title: str | None = None


@router.patch("/{paper_id}", response_model=PaperSummary)
def update_paper(
    paper_id: str,
    body: PaperUpdateRequest,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    paper = engine.get_paper(paper_id, user_id=user_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    if body.doi is not None:
        paper.doi = body.doi
    if body.year is not None:
        paper.year = body.year
    if body.title is not None:
        paper.title = body.title
    engine.update_paper(paper)
    return _paper_to_summary(paper)


@router.delete("/{paper_id}", status_code=204)
def delete_paper(
    paper_id: str,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    deleted = engine.delete_paper(paper_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Paper not found")


class SummarizeRequest(BaseModel):
    model_id: str | None = None
    user_prompt: str | None = None


@router.post("/{paper_id}/summarize")
async def summarize_paper(
    paper_id: str,
    body: SummarizeRequest | None = None,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    try:
        result = await engine.summarize_paper(
            paper_id,
            user_id=user_id,
            model_id=body.model_id if body else None,
            user_prompt=body.user_prompt if body else None,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Paper not found")
    return result


@router.get("/{paper_id}/summaries")
def get_paper_summaries(
    paper_id: str,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    return engine.get_paper_summaries(paper_id, user_id=user_id)


@router.delete("/{paper_id}/summaries/{summary_id}", status_code=204)
def delete_summary(
    paper_id: str,
    summary_id: str,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    from sqlalchemy import select
    from reflens.db.models import AISummary
    session = engine._get_session()
    try:
        s = session.execute(
            select(AISummary).where(
                AISummary.id == summary_id,
                AISummary.paper_id == paper_id,
                AISummary.user_id == user_id,
            )
        ).scalar_one_or_none()
        if s is None:
            raise HTTPException(status_code=404, detail="Summary not found")
        session.delete(s)
        session.commit()
    finally:
        session.close()


@router.post("/{paper_id}/tag", response_model=TagGenerateResponse)
async def tag_paper(
    paper_id: str,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    try:
        tags = await engine.tag_paper(paper_id, user_id=user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Paper not found")
    return TagGenerateResponse(id=paper_id, tags=tags)


@router.get("/{paper_id}/citations", response_model=list[CitationResponse])
def get_citations(
    paper_id: str,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    try:
        citations = engine.get_citations(paper_id, user_id=user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Paper not found")
    return [
        CitationResponse(
            id=c.id,
            cited_title=c.cited_title,
            cited_authors=c.cited_authors,
            cited_year=c.cited_year,
            cited_doi=c.cited_doi,
            cited_paper_id=c.cited_paper_id,
            raw_reference=c.raw_reference,
        )
        for c in citations
    ]


@router.put("/{paper_id}/notes", response_model=UserNoteResponse)
def update_notes(
    paper_id: str,
    body: NoteUpdateRequest,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    try:
        note = engine.update_notes(
            paper_id=paper_id,
            user_id=user_id,
            content=body.content,
            reading_status=body.reading_status,
            relevance_score=body.relevance_score,
            is_favorite=body.is_favorite,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Paper not found")
    return UserNoteResponse(
        id=note.id,
        content=note.content,
        reading_status=note.reading_status.value,
        relevance_score=note.relevance_score,
        is_favorite=note.is_favorite,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )
