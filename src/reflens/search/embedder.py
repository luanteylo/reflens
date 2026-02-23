"""ChromaDB wrapper for paper embedding storage and semantic search."""

import logging
from dataclasses import dataclass
from pathlib import Path

from reflens.search.chunker import chunk_paper

logger = logging.getLogger(__name__)


@dataclass
class SearchHit:
    paper_id: str
    distance: float
    chunk_text: str


class EmbeddingStore:
    """Manages paper embeddings in ChromaDB with sentence-transformers.

    Lazily initializes the ChromaDB client and embedding model to avoid
    heavy imports at module load time.
    """

    def __init__(self, chroma_path: Path, model_name: str = "all-MiniLM-L6-v2"):
        self._chroma_path = chroma_path
        self._model_name = model_name
        self._client = None
        self._collection = None

    def _ensure_initialized(self):
        if self._collection is not None:
            return
        import chromadb
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

        self._chroma_path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(self._chroma_path))
        ef = SentenceTransformerEmbeddingFunction(model_name=self._model_name)
        self._collection = self._client.get_or_create_collection(
            name="papers",
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )

    def index_paper(
        self,
        paper_id: str,
        title: str,
        abstract: str | None = None,
        sections: dict[str, str] | None = None,
        full_text: str | None = None,
    ) -> int:
        """Chunk and upsert a paper's embeddings. Returns number of chunks indexed."""
        self._ensure_initialized()
        chunks = chunk_paper(paper_id, title, abstract, sections, full_text)
        if not chunks:
            return 0

        self._collection.upsert(
            ids=[c.chunk_id for c in chunks],
            documents=[c.text for c in chunks],
            metadatas=[
                {"paper_id": c.paper_id, "chunk_type": c.chunk_type, "index": c.index}
                for c in chunks
            ],
        )
        logger.debug("Indexed %d chunks for paper %s", len(chunks), paper_id)
        return len(chunks)

    def remove_paper(self, paper_id: str) -> None:
        """Delete all chunks for a paper."""
        self._ensure_initialized()
        self._collection.delete(where={"paper_id": paper_id})
        logger.debug("Removed embeddings for paper %s", paper_id)

    def search(self, query: str, n_results: int = 10) -> list[SearchHit]:
        """Semantic search across all paper chunks."""
        self._ensure_initialized()
        if self._collection.count() == 0:
            return []

        results = self._collection.query(
            query_texts=[query],
            n_results=min(n_results, self._collection.count()),
        )

        hits = []
        if results["ids"] and results["ids"][0]:
            for i, _id in enumerate(results["ids"][0]):
                hits.append(SearchHit(
                    paper_id=results["metadatas"][0][i]["paper_id"],
                    distance=results["distances"][0][i],
                    chunk_text=results["documents"][0][i],
                ))
        return hits

    def count(self) -> int:
        """Total number of chunks in the store."""
        self._ensure_initialized()
        return self._collection.count()

    def is_available(self) -> bool:
        """Check if the embedding store can be initialized."""
        try:
            self._ensure_initialized()
            return True
        except Exception:
            logger.warning("Embedding store not available", exc_info=True)
            return False
