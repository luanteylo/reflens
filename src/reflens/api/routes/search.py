"""Search and reference finder endpoints."""

from fastapi import APIRouter, Depends

from reflens.api.deps import get_engine, get_user_id
from reflens.api.routes.papers import _paper_to_summary
from reflens.api.schemas import (
    ReferenceResult,
    ReferencesRequest,
    ReferencesResponse,
    SearchResponse,
    SearchResultItem,
)
from reflens.core.engine import RefLensEngine

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
def search_papers(
    q: str = "",
    limit: int = 20,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    if not q.strip():
        return SearchResponse(results=[], query=q)
    results = engine.search_papers(q, user_id=user_id, limit=limit)
    return SearchResponse(
        results=[
            SearchResultItem(
                paper=_paper_to_summary(r["paper"]),
                score=r["score"],
            )
            for r in results
        ],
        query=q,
    )


@router.post("/references", response_model=ReferencesResponse)
async def find_references(
    body: ReferencesRequest,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    results = await engine.find_references(
        text=body.text,
        user_id=user_id,
        limit=body.limit,
        explain=body.explain,
    )
    return ReferencesResponse(
        results=[
            ReferenceResult(
                paper=_paper_to_summary(r["paper"]),
                score=r["score"],
                explanation=r.get("explanation"),
            )
            for r in results
        ],
        text=body.text,
    )
