"""Tag endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from reflens.api.deps import get_engine, get_user_id
from reflens.api.routes.papers import _paper_to_summary
from reflens.api.schemas import TagListResponse, TagPapersResponse, TagResponse
from reflens.core.engine import RefLensEngine

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=TagListResponse)
def list_tags(engine: RefLensEngine = Depends(get_engine)):
    tags = engine.list_tags()
    return TagListResponse(
        tags=[
            TagResponse(id=t.id, name=t.name, parent_id=t.parent_id)
            for t in tags
        ]
    )


@router.get("/{tag_id}/papers", response_model=TagPapersResponse)
def papers_by_tag(
    tag_id: str,
    engine: RefLensEngine = Depends(get_engine),
    user_id: str = Depends(get_user_id),
):
    tag = engine.get_tag(tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    papers = engine.list_papers_by_tag(tag_id, user_id=user_id)
    return TagPapersResponse(
        tag=TagResponse(id=tag.id, name=tag.name, parent_id=tag.parent_id),
        papers=[_paper_to_summary(p) for p in papers],
    )
