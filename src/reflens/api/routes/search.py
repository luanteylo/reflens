"""Search and reference finder endpoints."""

from fastapi import APIRouter, Depends

from reflens.api.deps import get_engine, get_user_id
from reflens.api.routes.papers import _paper_to_summary
from reflens.api.schemas import (
    EmbeddingStatusResponse,
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
    group_id: str | None = None,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    if not q.strip():
        return SearchResponse(results=[], query=q)
    results = engine.search_papers(q, user_id=user_id, limit=limit, group_id=group_id)
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


@router.get("/embedding-status", response_model=EmbeddingStatusResponse)
def embedding_status(
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    return EmbeddingStatusResponse(**engine.embedding_status(user_id))


@router.post("/backfill-embeddings")
def backfill_embeddings(
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    counts = engine.backfill_embeddings(user_id)
    return counts


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
        tag_ids=body.tag_ids,
        group_id=body.group_id,
    )
    return ReferencesResponse(
        results=[
            ReferenceResult(
                paper=_paper_to_summary(r["paper"]),
                score=r["score"],
                explanation=r.get("explanation"),
                stance=r.get("stance"),
            )
            for r in results
        ],
        text=body.text,
    )
