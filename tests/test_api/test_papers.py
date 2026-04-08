"""Tests for paper API endpoints."""

import io

import pytest


class TestListPapers:
    def test_list_returns_papers(self, client, mock_engine):
        resp = client.get("/api/v1/papers")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["papers"]) == 1
        assert data["papers"][0]["title"] == "Test Paper"

    def test_list_pagination(self, client, mock_engine):
        resp = client.get("/api/v1/papers?limit=10&offset=5")
        assert resp.status_code == 200
        mock_engine.list_papers.assert_called_with(user_id="local", limit=10, offset=5)

    def test_list_empty(self, client, mock_engine):
        mock_engine.list_papers.return_value = []
        mock_engine.count_papers.return_value = 0
        resp = client.get("/api/v1/papers")
        assert resp.status_code == 200
        assert resp.json()["papers"] == []


class TestGetPaper:
    def test_get_existing(self, client):
        resp = client.get("/api/v1/papers/paper-1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "paper-1"
        assert data["title"] == "Test Paper"
        assert "citations" in data
        assert "notes" in data

    def test_get_not_found(self, client, mock_engine):
        mock_engine.get_paper.return_value = None
        resp = client.get("/api/v1/papers/nonexistent")
        assert resp.status_code == 404


class TestDeletePaper:
    def test_delete_existing(self, client):
        resp = client.delete("/api/v1/papers/paper-1")
        assert resp.status_code == 204

    def test_delete_not_found(self, client, mock_engine):
        mock_engine.delete_paper.return_value = False
        resp = client.delete("/api/v1/papers/nonexistent")
        assert resp.status_code == 404


class TestUploadPaper:
    def test_upload_pdf(self, client):
        pdf_content = b"%PDF-1.4 fake content"
        resp = client.post(
            "/api/v1/papers/upload",
            files={"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "paper-1"
        assert data["title"] == "Uploaded Paper"

    def test_upload_non_pdf_rejected(self, client):
        resp = client.post(
            "/api/v1/papers/upload",
            files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        assert resp.status_code == 400


class TestSummarizePaper:
    def test_summarize(self, client):
        resp = client.post("/api/v1/papers/paper-1/summarize")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ai_summary"] == "Summary text"
        assert data["ai_key_contributions"] == ["contrib1"]

    def test_summarize_not_found(self, client, mock_engine):
        mock_engine.summarize_paper = pytest.importorskip("unittest.mock").AsyncMock(
            side_effect=ValueError("Paper not found")
        )
        resp = client.post("/api/v1/papers/nonexistent/summarize")
        assert resp.status_code == 404


class TestTagPaper:
    def test_tag(self, client):
        resp = client.post("/api/v1/papers/paper-1/tag")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tags"] == ["ml", "nlp"]


class TestGetCitations:
    def test_get_citations(self, client):
        resp = client.get("/api/v1/papers/paper-1/citations")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["cited_title"] == "Cited Paper"

    def test_citations_not_found(self, client, mock_engine):
        mock_engine.get_citations.side_effect = ValueError("Paper not found")
        resp = client.get("/api/v1/papers/nonexistent/citations")
        assert resp.status_code == 404


class TestUpdateNotes:
    def test_update_notes(self, client):
        resp = client.put(
            "/api/v1/papers/paper-1/notes",
            json={"content": "My notes", "reading_status": "read"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"] == "My notes"

    def test_notes_not_found(self, client, mock_engine):
        mock_engine.update_notes.side_effect = ValueError("Paper not found")
        resp = client.put(
            "/api/v1/papers/nonexistent/notes",
            json={"content": "notes"},
        )
        assert resp.status_code == 404


class TestSummarizeAll:
    def test_summarize_all_returns_task_id(self, client):
        resp = client.post("/api/v1/papers/summarize-all")
        assert resp.status_code == 200
        data = resp.json()
        assert "task_id" in data
        assert len(data["task_id"]) > 0

    def test_summarize_all_duplicate_returns_same_task(self, client):
        from reflens.api.tasks import TaskStatus, get_task_registry

        registry = get_task_registry()
        task = registry.create("summarize-all")
        task.status = TaskStatus.RUNNING

        resp = client.post("/api/v1/papers/summarize-all")
        assert resp.json()["task_id"] == task.id


class TestTagAll:
    def test_tag_all_returns_task_id(self, client):
        resp = client.post("/api/v1/papers/tag-all")
        assert resp.status_code == 200
        data = resp.json()
        assert "task_id" in data
        assert len(data["task_id"]) > 0
