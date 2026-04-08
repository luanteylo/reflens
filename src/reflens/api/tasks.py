"""In-memory background task registry for bulk operations."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

from reflens.core.engine import RefLensEngine

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


MAX_CONSECUTIVE_FAILURES = 3


@dataclass
class TaskInfo:
    id: str
    kind: str
    status: TaskStatus = TaskStatus.PENDING
    total: int = 0
    completed: int = 0
    failed: int = 0
    done_titles: list[str] = field(default_factory=list)
    failed_titles: list[str] = field(default_factory=list)
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None


class TaskRegistry:
    def __init__(self):
        self._tasks: dict[str, TaskInfo] = {}

    def create(self, kind: str) -> TaskInfo:
        active = self.get_active(kind)
        if active is not None:
            return active
        task = TaskInfo(id=str(uuid.uuid4()), kind=kind)
        self._tasks[task.id] = task
        return task

    def get(self, task_id: str) -> TaskInfo | None:
        return self._tasks.get(task_id)

    def get_active(self, kind: str) -> TaskInfo | None:
        for task in self._tasks.values():
            if task.kind == kind and task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                return task
        return None

    def clear(self):
        self._tasks.clear()


# Module-level singleton
_registry = TaskRegistry()


def get_task_registry() -> TaskRegistry:
    return _registry


async def run_bulk_task(
    task_id: str,
    registry: TaskRegistry,
    engine: RefLensEngine,
    kind: str,
    user_id: str,
):
    task = registry.get(task_id)
    if task is None:
        return

    try:
        papers = engine.list_papers(user_id=user_id, limit=10000)
        if kind == "summarize-all":
            pending = [p for p in papers if not p.ai_summary]
        else:
            pending = [p for p in papers if not p.tags]

        task.total = len(pending)
        task.status = TaskStatus.RUNNING

        consecutive_failures = 0
        for paper in pending:
            try:
                if kind == "summarize-all":
                    await engine.summarize_paper(paper.id, user_id)
                else:
                    await engine.tag_paper(paper.id, user_id)
                task.completed += 1
                task.done_titles.append(paper.title)
                consecutive_failures = 0
            except Exception as exc:
                logger.warning("Task %s: failed on %s", kind, paper.title, exc_info=True)
                task.failed += 1
                task.failed_titles.append(paper.title)
                task.error = str(exc)
                consecutive_failures += 1
                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    task.error = (
                        f"Aborted after {MAX_CONSECUTIVE_FAILURES}"
                        f" consecutive failures: {exc}"
                    )
                    task.status = TaskStatus.FAILED
                    task.finished_at = datetime.now(UTC)
                    return

        task.status = TaskStatus.COMPLETED
    except Exception as exc:
        logger.error("Task %s failed unexpectedly", task_id, exc_info=True)
        task.status = TaskStatus.FAILED
        task.error = str(exc)
    finally:
        task.finished_at = datetime.now(UTC)
