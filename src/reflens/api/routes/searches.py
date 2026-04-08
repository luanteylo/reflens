"""Saved search endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from reflens.api.deps import get_engine, get_user_id
from reflens.api.schemas import (
    SavedSearchListResponse,
    SavedSearchResponse,
    SaveSearchRequest,
)
from reflens.core.engine import RefLensEngine

router = APIRouter(prefix="/saved-searches", tags=["saved-searches"])


@router.get("", response_model=SavedSearchListResponse)
def list_saved_searches(
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    searches = engine.list_saved_searches(user_id=user_id)
    return SavedSearchListResponse(
        searches=[SavedSearchResponse(**s) for s in searches]
    )


@router.post("", response_model=SavedSearchResponse, status_code=201)
def save_search(
    body: SaveSearchRequest,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    results_data = None
    if body.results:
        results_data = [r.model_dump(mode="json") for r in body.results]
    saved = engine.save_search(
        body.text, group_id=body.group_id, results=results_data, user_id=user_id
    )
    return SavedSearchResponse(**saved)


@router.delete("/{search_id}", status_code=204)
def delete_saved_search(
    search_id: str,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    if not engine.delete_saved_search(search_id, user_id=user_id):
        raise HTTPException(status_code=404, detail="Saved search not found")
