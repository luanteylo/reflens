"""Author endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from reflens.api.deps import get_engine, get_user_id
from reflens.api.routes.papers import _paper_to_summary
from reflens.api.schemas import AuthorListResponse, AuthorResponse, PaperSummary
from reflens.core.engine import RefLensEngine

router = APIRouter(prefix="/authors", tags=["authors"])


@router.get("", response_model=AuthorListResponse)
def list_authors(
    limit: int = 50,
    offset: int = 0,
    engine: RefLensEngine = Depends(get_engine),
):
    authors = engine.list_authors(limit=limit, offset=offset)
    total = engine.count_authors()
    return AuthorListResponse(
        authors=[
            AuthorResponse(id=a.id, name=a.name, affiliations=a.affiliations)
            for a in authors
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{author_id}/papers", response_model=list[PaperSummary])
def papers_by_author(
    author_id: str,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    author = engine.get_author(author_id)
    if author is None:
        raise HTTPException(status_code=404, detail="Author not found")
    papers = engine.list_papers_by_author(author_id, user_id=user_id)
    return [_paper_to_summary(p) for p in papers]
