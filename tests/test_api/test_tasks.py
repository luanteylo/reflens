"""Tests for task status endpoint."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from reflens.api.tasks import (
    MAX_CONSECUTIVE_FAILURES,
    TaskRegistry,
    TaskStatus,
    get_task_registry,
    run_bulk_task,
)


class TestGetTaskStatus:
    def test_get_existing_task(self, client):
        registry = get_task_registry()
        task = registry.create("summarize-all")
        task.status = TaskStatus.RUNNING
        task.total = 10
        task.completed = 3
        task.failed = 1
        task.done_titles = ["Paper A", "Paper B", "Paper C"]
        task.failed_titles = ["Paper D"]
        task.error = None

        resp = client.get(f"/api/v1/tasks/{task.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == task.id
        assert data["kind"] == "summarize-all"
        assert data["status"] == "running"
        assert data["total"] == 10
        assert data["completed"] == 3
        assert data["failed"] == 1
        assert data["done_titles"] == ["Paper A", "Paper B", "Paper C"]
        assert data["failed_titles"] == ["Paper D"]
        assert data["error"] is None

    def test_get_failed_task_shows_error(self, client):
        registry = get_task_registry()
        task = registry.create("summarize-all")
        task.status = TaskStatus.FAILED
        task.total = 5
        task.failed = 3
        task.error = "Aborted after 3 consecutive failures: Invalid API key"

        resp = client.get(f"/api/v1/tasks/{task.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "failed"
        assert "Invalid API key" in data["error"]

    def test_get_completed_task(self, client):
        registry = get_task_registry()
        task = registry.create("tag-all")
        task.status = TaskStatus.COMPLETED
        task.total = 5
        task.completed = 4
        task.failed = 1

        resp = client.get(f"/api/v1/tasks/{task.id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    def test_get_nonexistent_task(self, client):
        resp = client.get("/api/v1/tasks/nonexistent-id")
        assert resp.status_code == 404


class TestTaskRegistry:
    def test_create_and_get(self):
        registry = TaskRegistry()
        task = registry.create("summarize-all")
        assert task.kind == "summarize-all"
        assert task.status == TaskStatus.PENDING
        assert registry.get(task.id) is task

    def test_duplicate_prevention(self):
        registry = TaskRegistry()
        task1 = registry.create("summarize-all")
        task2 = registry.create("summarize-all")
        assert task1.id == task2.id

    def test_different_kinds_allowed(self):
        registry = TaskRegistry()
        task1 = registry.create("summarize-all")
        task2 = registry.create("tag-all")
        assert task1.id != task2.id

    def test_completed_allows_new_task(self):
        registry = TaskRegistry()
        task1 = registry.create("summarize-all")
        task1.status = TaskStatus.COMPLETED
        task2 = registry.create("summarize-all")
        assert task1.id != task2.id

    def test_get_active(self):
        registry = TaskRegistry()
        task = registry.create("summarize-all")
        task.status = TaskStatus.RUNNING
        assert registry.get_active("summarize-all") is task
        assert registry.get_active("tag-all") is None

    def test_clear(self):
        registry = TaskRegistry()
        registry.create("summarize-all")
        registry.clear()
        assert registry.get_active("summarize-all") is None


def _make_mock_paper(paper_id, title, ai_summary=None, tags=None):
    p = MagicMock()
    p.id = paper_id
    p.title = title
    p.ai_summary = ai_summary
    p.tags = tags or []
    return p


class TestRunBulkTask:
    def test_fail_fast_after_consecutive_failures(self):
        registry = TaskRegistry()
        task = registry.create("summarize-all")

        papers = [_make_mock_paper(f"p{i}", f"Paper {i}") for i in range(10)]
        engine = MagicMock()
        engine.list_papers.return_value = papers
        engine.summarize_paper = AsyncMock(side_effect=RuntimeError("Invalid API key"))

        asyncio.run(
            run_bulk_task(task.id, registry, engine, "summarize-all", "local")
        )

        assert task.status == TaskStatus.FAILED
        assert task.failed == MAX_CONSECUTIVE_FAILURES
        assert task.completed == 0
        assert "Invalid API key" in task.error
        assert engine.summarize_paper.call_count == MAX_CONSECUTIVE_FAILURES

    def test_consecutive_counter_resets_on_success(self):
        registry = TaskRegistry()
        task = registry.create("summarize-all")

        papers = [_make_mock_paper(f"p{i}", f"Paper {i}") for i in range(5)]
        engine = MagicMock()
        engine.list_papers.return_value = papers

        call_count = 0

        async def alternate_fail(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                raise RuntimeError("Transient error")

        engine.summarize_paper = AsyncMock(side_effect=alternate_fail)

        asyncio.run(
            run_bulk_task(task.id, registry, engine, "summarize-all", "local")
        )

        assert task.status == TaskStatus.COMPLETED
        assert task.completed == 3
        assert task.failed == 2

    def test_error_message_captured(self):
        registry = TaskRegistry()
        task = registry.create("tag-all")

        papers = [_make_mock_paper("p1", "Paper 1")]
        engine = MagicMock()
        engine.list_papers.return_value = papers
        engine.tag_paper = AsyncMock(side_effect=RuntimeError("Rate limit exceeded"))

        asyncio.run(
            run_bulk_task(task.id, registry, engine, "tag-all", "local")
        )

        assert task.failed == 1
        assert "Rate limit exceeded" in task.error
