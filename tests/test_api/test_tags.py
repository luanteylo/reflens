"""Tests for tags API endpoint."""

from unittest.mock import MagicMock


class TestListTags:
    def test_list_tags(self, client, mock_engine):
        tag = MagicMock()
        tag.id = "tag-1"
        tag.name = "machine-learning"
        tag.parent_id = None
        mock_engine.list_tags.return_value = [tag]

        resp = client.get("/api/v1/tags")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["tags"]) == 1
        assert data["tags"][0]["name"] == "machine-learning"

    def test_list_tags_empty(self, client):
        resp = client.get("/api/v1/tags")
        assert resp.status_code == 200
        assert resp.json()["tags"] == []


class TestPapersByTag:
    def test_tag_not_found(self, client):
        resp = client.get("/api/v1/tags/nonexistent/papers")
        assert resp.status_code == 404

    def test_papers_by_tag(self, client, mock_engine):
        tag = MagicMock()
        tag.id = "tag-1"
        tag.name = "ml"
        tag.parent_id = None
        mock_engine.get_tag.return_value = tag

        paper = MagicMock()
        paper.id = "p1"
        paper.title = "ML Paper"
        paper.abstract = "Abstract"
        paper.year = 2024
        paper.doi = None
        paper.ai_summary = None
        paper.created_at = "2024-01-01T00:00:00Z"
        paper.authors = []
        paper.tags = []
        mock_engine.list_papers_by_tag.return_value = [paper]

        resp = client.get("/api/v1/tags/tag-1/papers")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tag"]["name"] == "ml"
        assert len(data["papers"]) == 1
