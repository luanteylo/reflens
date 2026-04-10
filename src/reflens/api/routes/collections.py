"""Collection endpoints: CRUD and membership management."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from reflens.api.deps import get_engine, get_user_id
from reflens.api.routes.papers import _paper_to_summary
from reflens.core.engine import RefLensEngine

router = APIRouter(prefix="/collections", tags=["collections"])


class CollectionCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    parent_id: str | None = None


class CollectionPapersRequest(BaseModel):
    paper_ids: list[str]


class CollectionResponse(BaseModel):
    id: str
    name: str
    parent_id: str | None = None
    paper_count: int
    children: list["CollectionResponse"] = []
    created_at: datetime | None = None


class CollectionDetailResponse(CollectionResponse):
    papers: list = []


class CollectionListResponse(BaseModel):
    collections: list[CollectionResponse]


@router.get("", response_model=CollectionListResponse)
def list_collections(
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    cols = engine.list_collections(user_id=user_id)
    return CollectionListResponse(
        collections=[CollectionResponse(**c) for c in cols]
    )


@router.post("", response_model=CollectionResponse, status_code=201)
def create_collection(
    body: CollectionCreateRequest,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    return CollectionResponse(
        **engine.create_collection(body.name, parent_id=body.parent_id, user_id=user_id)
    )


@router.post("/get-or-create", response_model=CollectionResponse)
def get_or_create_collection(
    body: CollectionCreateRequest,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    return CollectionResponse(
        **engine.get_or_create_collection(body.name, parent_id=body.parent_id, user_id=user_id)
    )


@router.get("/{col_id}", response_model=CollectionDetailResponse)
def get_collection(
    col_id: str,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    col = engine.get_collection(col_id, user_id=user_id)
    if col is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    papers = col.pop("papers", [])
    return CollectionDetailResponse(
        **col,
        papers=[_paper_to_summary(p) for p in papers],
    )


class CollectionUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


@router.patch("/{col_id}", response_model=CollectionResponse)
def update_collection(
    col_id: str,
    body: CollectionUpdateRequest,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    col = engine.rename_collection(col_id, body.name, user_id=user_id)
    if col is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return CollectionResponse(**col)


@router.delete("/{col_id}", status_code=204)
def delete_collection(
    col_id: str,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    if not engine.delete_collection(col_id, user_id=user_id):
        raise HTTPException(status_code=404, detail="Collection not found")


@router.post("/{col_id}/papers", status_code=204)
def add_papers_to_collection(
    col_id: str,
    body: CollectionPapersRequest,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    col = engine.get_collection(col_id, user_id=user_id)
    if col is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    engine.add_papers_to_collection(col_id, body.paper_ids, user_id=user_id)


@router.delete("/{col_id}/papers", status_code=204)
def remove_papers_from_collection(
    col_id: str,
    body: CollectionPapersRequest,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    engine.remove_papers_from_collection(col_id, body.paper_ids, user_id=user_id)
