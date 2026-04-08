"""Task status endpoint for background bulk operations."""

from fastapi import APIRouter, HTTPException

from reflens.api.schemas import TaskStatusResponse
from reflens.api.tasks import get_task_registry

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: str):
    registry = get_task_registry()
    task = registry.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskStatusResponse(
        id=task.id,
        kind=task.kind,
        status=task.status.value,
        total=task.total,
        completed=task.completed,
        failed=task.failed,
        done_titles=task.done_titles,
        failed_titles=task.failed_titles,
        error=task.error,
    )
