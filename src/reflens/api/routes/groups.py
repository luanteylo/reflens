"""Group endpoints: CRUD and membership management."""

from fastapi import APIRouter, Depends, HTTPException

from reflens.api.deps import get_engine, get_user_id
from reflens.api.routes.papers import _paper_to_summary
from reflens.api.schemas import (
    GroupCreateRequest,
    GroupDetailResponse,
    GroupListResponse,
    GroupPapersRequest,
    GroupResponse,
)
from reflens.core.engine import RefLensEngine

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("", response_model=GroupListResponse)
def list_groups(
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    groups = engine.list_groups(user_id=user_id)
    return GroupListResponse(
        groups=[
            GroupResponse(
                id=g.id,
                name=g.name,
                paper_count=len(g.papers) if hasattr(g, "papers") and g.papers else 0,
                created_at=g.created_at,
            )
            for g in groups
        ]
    )


@router.post("", response_model=GroupResponse, status_code=201)
def create_group(
    body: GroupCreateRequest,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    group = engine.create_group(body.name, user_id=user_id)
    return GroupResponse(
        id=group.id,
        name=group.name,
        paper_count=0,
        created_at=group.created_at,
    )


@router.get("/{group_id}", response_model=GroupDetailResponse)
def get_group(
    group_id: str,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    group = engine.get_group(group_id, user_id=user_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    return GroupDetailResponse(
        id=group.id,
        name=group.name,
        paper_count=len(group.papers),
        created_at=group.created_at,
        papers=[_paper_to_summary(p) for p in group.papers],
    )


@router.delete("/{group_id}", status_code=204)
def delete_group(
    group_id: str,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    if not engine.delete_group(group_id, user_id=user_id):
        raise HTTPException(status_code=404, detail="Group not found")


@router.post("/{group_id}/papers", status_code=204)
def add_papers_to_group(
    group_id: str,
    body: GroupPapersRequest,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    group = engine.get_group(group_id, user_id=user_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    engine.add_papers_to_group(group_id, body.paper_ids, user_id=user_id)


@router.delete("/{group_id}/papers", status_code=204)
def remove_papers_from_group(
    group_id: str,
    body: GroupPapersRequest,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    engine.remove_papers_from_group(group_id, body.paper_ids, user_id=user_id)
