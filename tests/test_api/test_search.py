"""Tests for search and reference finder API endpoints."""


class TestSearch:
    def test_search_with_query(self, client, mock_engine):
        resp = client.get("/api/v1/search?q=deep+learning")
        assert resp.status_code == 200
        data = resp.json()
        assert data["query"] == "deep learning"
        assert len(data["results"]) == 1
        item = data["results"][0]
        assert "paper" in item
        assert item["score"] == 0.85
        assert item["paper"]["title"] == "Test Paper"
        mock_engine.search_papers.assert_called_with(
            "deep learning", user_id="local", limit=20
        )

    def test_search_with_custom_limit(self, client, mock_engine):
        resp = client.get("/api/v1/search?q=test&limit=5")
        assert resp.status_code == 200
        mock_engine.search_papers.assert_called_with("test", user_id="local", limit=5)

    def test_search_empty_query(self, client, mock_engine):
        resp = client.get("/api/v1/search?q=")
        assert resp.status_code == 200
        data = resp.json()
        assert data["results"] == []
        mock_engine.search_papers.assert_not_called()

    def test_search_no_results(self, client, mock_engine):
        mock_engine.search_papers.return_value = []
        resp = client.get("/api/v1/search?q=nonexistent")
        assert resp.status_code == 200
        assert resp.json()["results"] == []

    def test_search_null_score(self, client, mock_engine):
        from tests.test_api.conftest import _make_paper

        mock_engine.search_papers.return_value = [
            {"paper": _make_paper(), "score": None}
        ]
        resp = client.get("/api/v1/search?q=fallback")
        assert resp.status_code == 200
        item = resp.json()["results"][0]
        assert item["score"] is None


class TestReferenceFinder:
    def test_find_references(self, client, mock_engine):
        resp = client.post(
            "/api/v1/search/references",
            json={"text": "Deep learning improves NLP tasks", "limit": 3},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["text"] == "Deep learning improves NLP tasks"
        assert len(data["results"]) == 1
        assert data["results"][0]["score"] == 0.92
        assert data["results"][0]["paper"]["title"] == "Test Paper"
        mock_engine.find_references.assert_called_once()

    def test_find_references_with_explain(self, client, mock_engine):
        resp = client.post(
            "/api/v1/search/references",
            json={"text": "some claim", "explain": True},
        )
        assert resp.status_code == 200
        call_kwargs = mock_engine.find_references.call_args
        assert call_kwargs.kwargs["explain"] is True

    def test_find_references_empty_text(self, client, mock_engine):
        mock_engine.find_references.return_value = []
        resp = client.post(
            "/api/v1/search/references",
            json={"text": ""},
        )
        assert resp.status_code == 200
        assert resp.json()["results"] == []

    def test_find_references_defaults(self, client, mock_engine):
        resp = client.post(
            "/api/v1/search/references",
            json={"text": "test"},
        )
        assert resp.status_code == 200
        call_kwargs = mock_engine.find_references.call_args
        assert call_kwargs.kwargs["limit"] == 5
        assert call_kwargs.kwargs["explain"] is False
