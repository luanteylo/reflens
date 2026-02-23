"""Integration tests for EmbeddingStore (uses real ChromaDB with ephemeral client)."""

import pytest

from reflens.search.embedder import EmbeddingStore, SearchHit


@pytest.fixture
def store(tmp_path):
    return EmbeddingStore(chroma_path=tmp_path / "chroma")


class TestEmbeddingStore:
    def test_index_and_count(self, store):
        n = store.index_paper(
            paper_id="p1",
            title="Deep Learning for NLP",
            abstract="We propose a transformer-based approach.",
        )
        assert n >= 1
        assert store.count() >= 1

    def test_search_returns_hits(self, store):
        store.index_paper(
            paper_id="p1",
            title="Deep Learning for NLP",
            abstract="Neural networks for text classification.",
        )
        store.index_paper(
            paper_id="p2",
            title="Quantum Computing Basics",
            abstract="Introduction to qubits and quantum gates.",
        )
        hits = store.search("neural networks text", n_results=5)
        assert len(hits) > 0
        assert all(isinstance(h, SearchHit) for h in hits)
        # The NLP paper should rank higher for this query
        paper_ids = [h.paper_id for h in hits]
        assert "p1" in paper_ids

    def test_search_empty_store(self, store):
        hits = store.search("anything")
        assert hits == []

    def test_remove_paper(self, store):
        store.index_paper("p1", "Paper One", abstract="Content about A.")
        store.index_paper("p2", "Paper Two", abstract="Content about B.")
        before = store.count()
        store.remove_paper("p1")
        after = store.count()
        assert after < before
        # Only p2 should remain in search results
        hits = store.search("content", n_results=10)
        remaining_ids = {h.paper_id for h in hits}
        assert "p1" not in remaining_ids
        assert "p2" in remaining_ids

    def test_upsert_is_idempotent(self, store):
        store.index_paper("p1", "Paper", abstract="Abstract v1.")
        count1 = store.count()
        store.index_paper("p1", "Paper", abstract="Abstract v2.")
        count2 = store.count()
        assert count1 == count2

    def test_is_available(self, store):
        assert store.is_available()

    def test_search_hit_fields(self, store):
        store.index_paper("p1", "Test", abstract="Some abstract text.")
        hits = store.search("abstract text")
        assert len(hits) > 0
        hit = hits[0]
        assert hit.paper_id == "p1"
        assert isinstance(hit.distance, float)
        assert len(hit.chunk_text) > 0
