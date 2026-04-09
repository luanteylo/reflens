"""Core engine -- the central orchestrator.

This is the shared business logic layer called by both the CLI and
(in the future) the REST API and MCP server.
"""

import logging
import shutil
from pathlib import Path

from sqlalchemy.orm import Session

from reflens.ai.factory import create_ai_provider
from reflens.ai.provider import AIProvider
from reflens.config import Settings
from reflens.db.models import Citation, Paper, ReadingStatus, UserNote
from reflens.db.repositories import (
    AuthorRepository,
    CitationRepository,
    CollectionRepository,
    PaperRepository,
    SavedSearchRepository,
    TagRepository,
    UserNoteRepository,
)
from reflens.db.session import get_session, init_db
from reflens.extraction.models import ExtractedPaper
from reflens.extraction.pipeline import ExtractionPipeline
from reflens.search.embedder import EmbeddingStore

logger = logging.getLogger(__name__)


class RefLensEngine:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        init_db(self.settings)
        self.extraction = ExtractionPipeline(self.settings)
        self._ai: AIProvider | None = None
        self._embedding_store: EmbeddingStore | None = None

    @property
    def ai(self) -> AIProvider:
        if self._ai is None:
            self._ai = create_ai_provider(self.settings)
        return self._ai

    def get_ai(self, model_id: str | None = None) -> AIProvider:
        """Get an AI provider for a specific model, or the default."""
        if not model_id:
            return self.ai
        return create_ai_provider(self.settings, model_id)

    @property
    def embedding_store(self) -> EmbeddingStore:
        if self._embedding_store is None:
            self._embedding_store = EmbeddingStore(
                chroma_path=self.settings.chroma_path,
                model_name=self.settings.embedding_model,
            )
        return self._embedding_store

    def _get_session(self) -> Session:
        return get_session()

    def ingest_paper(
        self,
        pdf_path: Path,
        user_id: str = "local",
        notes: str | None = None,
        reading_status: str = "unread",
    ) -> dict:
        """Ingest a PDF: extract, store in DB, and copy the file to storage.

        Returns a dict with paper details (detached from session).
        """
        pdf_path = Path(pdf_path)

        # Extract
        extracted = self.extraction.extract(pdf_path)

        # Store the PDF file
        stored_path = self._store_pdf(pdf_path, user_id)

        session = self._get_session()
        try:
            paper = self._save_paper(session, extracted, stored_path, user_id)
            self._save_authors(session, extracted, paper)
            self._save_citations(session, extracted, paper, user_id)

            if notes:
                note_repo = UserNoteRepository(session)
                note_repo.create_or_update(
                    UserNote(
                        paper_id=paper.id,
                        user_id=user_id,
                        content=notes,
                        reading_status=ReadingStatus(reading_status),
                    )
                )

            session.commit()
            session.refresh(paper)
            logger.info("Ingested paper: %s (id=%s)", paper.title, paper.id)

            # Index embeddings (non-fatal on error)
            indexed = False
            try:
                self.embedding_store.index_paper(
                    paper_id=paper.id,
                    title=paper.title,
                    abstract=paper.abstract,
                    sections=paper.sections,
                    full_text=paper.full_text,
                )
                indexed = True
            except Exception:
                logger.warning("Failed to index embeddings for %s", paper.id, exc_info=True)

            # Return a detached dict to avoid lazy-load issues
            result = {
                "id": paper.id,
                "title": paper.title,
                "abstract": paper.abstract,
                "year": paper.year,
                "doi": paper.doi,
                "source_file": paper.source_file,
                "authors": [a.name for a in paper.authors],
                "citations_count": len(paper.citing_refs),
                "indexed": indexed,
            }
            return result
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    async def summarize_paper(self, paper_id: str, user_id: str = "local") -> Paper:
        """Generate AI summary for a paper."""
        session = self._get_session()
        try:
            repo = PaperRepository(session)
            paper = repo.get_by_id(paper_id, user_id)
            if paper is None:
                raise ValueError(f"Paper not found: {paper_id}")

            summary = await self.ai.summarize(
                title=paper.title,
                abstract=paper.abstract or "",
                full_text=paper.full_text or "",
            )

            paper.ai_summary = summary.overview
            paper.ai_key_contributions = summary.key_contributions
            paper.ai_methodology = summary.methodology
            paper.ai_findings = summary.findings
            paper.ai_limitations = summary.limitations

            session.commit()
            session.refresh(paper)
            return paper
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    async def tag_paper(self, paper_id: str, user_id: str = "local") -> list[str]:
        """Generate AI tags for a paper."""
        session = self._get_session()
        try:
            repo = PaperRepository(session)
            paper = repo.get_by_id(paper_id, user_id)
            if paper is None:
                raise ValueError(f"Paper not found: {paper_id}")

            generated = await self.ai.generate_tags(
                title=paper.title,
                abstract=paper.abstract or "",
                sections=paper.sections or {},
            )

            tag_repo = TagRepository(session)
            tag_names = []
            for gt in generated:
                tag = tag_repo.get_or_create(gt.name)
                tag_repo.tag_paper(
                    paper_id=paper.id,
                    tag_id=tag.id,
                    section=gt.section,
                    confidence=gt.confidence,
                    user_id=user_id,
                )
                tag_names.append(gt.name)

            session.commit()
            return tag_names
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    async def summarize_all(
        self, user_id: str = "local"
    ) -> dict[str, list[str]]:
        """Generate AI summaries for all papers that don't have one yet.

        Returns dict with 'done' and 'failed' lists of paper titles.
        """
        papers = self.list_papers(user_id=user_id, limit=10000)
        pending = [p for p in papers if not p.ai_summary]
        done = []
        failed = []

        for paper in pending:
            try:
                await self.summarize_paper(paper.id, user_id)
                done.append(paper.title)
            except Exception:
                logger.warning("Failed to summarize %s", paper.title, exc_info=True)
                failed.append(paper.title)

        return {"done": done, "failed": failed}

    async def tag_all(
        self, user_id: str = "local"
    ) -> dict[str, list[str]]:
        """Generate AI tags for all papers that don't have any yet.

        Returns dict with 'done' and 'failed' lists of paper titles.
        """
        papers = self.list_papers(user_id=user_id, limit=10000)
        pending = [p for p in papers if not p.tags]
        done = []
        failed = []

        for paper in pending:
            try:
                await self.tag_paper(paper.id, user_id)
                done.append(paper.title)
            except Exception:
                logger.warning("Failed to tag %s", paper.title, exc_info=True)
                failed.append(paper.title)

        return {"done": done, "failed": failed}

    def get_paper(self, paper_id: str, user_id: str = "local") -> Paper | None:
        session = self._get_session()
        try:
            repo = PaperRepository(session)
            return repo.get_with_relations(paper_id, user_id)
        finally:
            session.close()

    def list_papers(
        self, user_id: str = "local", limit: int = 50, offset: int = 0
    ) -> list[Paper]:
        session = self._get_session()
        try:
            repo = PaperRepository(session)
            return repo.list_all(user_id, limit, offset)
        finally:
            session.close()

    def _resolve_collection_paper_ids(
        self, collection_ids: list[str]
    ) -> set[str]:
        """Get all paper IDs from one or more collections (recursive)."""
        session = self._get_session()
        try:
            col_repo = CollectionRepository(session)
            ids: set[str] = set()
            for cid in collection_ids:
                ids |= col_repo.get_paper_ids_recursive(cid)
            return ids
        finally:
            session.close()

    def search_papers(
        self,
        query: str,
        user_id: str = "local",
        limit: int = 20,
        collection_ids: list[str] | None = None,
    ) -> list[dict]:
        """Semantic search with SQL ILIKE fallback.

        Returns list of dicts with keys {"paper": Paper, "score": float | None}.
        """
        allowed_ids: set[str] | None = None
        if collection_ids:
            allowed_ids = self._resolve_collection_paper_ids(collection_ids)
            if not allowed_ids:
                return []

        # Try semantic search first
        try:
            if self.embedding_store.is_available() and self.embedding_store.count() > 0:
                hits = self.embedding_store.search(query, n_results=limit * 3)
                if hits:
                    # Deduplicate by paper_id, keep best (lowest) distance
                    best: dict[str, float] = {}
                    for h in hits:
                        if h.paper_id not in best or h.distance < best[h.paper_id]:
                            best[h.paper_id] = h.distance
                    # Convert distance to similarity score (0-1)
                    scored = {
                        pid: 1.0 - (dist / 2.0) for pid, dist in best.items()
                    }
                    if allowed_ids is not None:
                        scored = {pid: s for pid, s in scored.items() if pid in allowed_ids}
                    # Load papers from DB and filter by user_id
                    session = self._get_session()
                    try:
                        repo = PaperRepository(session)
                        results = []
                        for pid in sorted(scored, key=scored.get, reverse=True):
                            paper = repo.get_with_relations(pid, user_id)
                            if paper:
                                results.append({"paper": paper, "score": scored[pid]})
                            if len(results) >= limit:
                                break
                        if results:
                            return results
                    finally:
                        session.close()
        except Exception:
            logger.warning("Semantic search failed, falling back to SQL", exc_info=True)

        # Fallback to SQL ILIKE
        session = self._get_session()
        try:
            repo = PaperRepository(session)
            papers = repo.search_by_title(query, user_id)
            if allowed_ids is not None:
                papers = [p for p in papers if p.id in allowed_ids]
            return [{"paper": p, "score": None} for p in papers[:limit]]
        finally:
            session.close()

    def count_papers(self, user_id: str = "local") -> int:
        session = self._get_session()
        try:
            repo = PaperRepository(session)
            return repo.count(user_id)
        finally:
            session.close()

    def list_papers_by_tags(
        self,
        tag_ids: list[str],
        user_id: str = "local",
        limit: int = 50,
        offset: int = 0,
    ) -> list[Paper]:
        session = self._get_session()
        try:
            repo = PaperRepository(session)
            return repo.list_by_tags(tag_ids, user_id, limit, offset)
        finally:
            session.close()

    def count_papers_by_tags(self, tag_ids: list[str], user_id: str = "local") -> int:
        session = self._get_session()
        try:
            repo = PaperRepository(session)
            return repo.count_by_tags(tag_ids, user_id)
        finally:
            session.close()

    def get_citations(self, paper_id: str, user_id: str = "local") -> list[Citation]:
        session = self._get_session()
        try:
            repo = PaperRepository(session)
            paper = repo.get_by_id(paper_id, user_id)
            if paper is None:
                raise ValueError(f"Paper not found: {paper_id}")
            cite_repo = CitationRepository(session)
            return cite_repo.get_by_paper(paper_id)
        finally:
            session.close()

    def update_notes(
        self,
        paper_id: str,
        user_id: str = "local",
        content: str | None = None,
        reading_status: str = "unread",
        relevance_score: int | None = None,
        is_favorite: bool = False,
    ) -> UserNote:
        session = self._get_session()
        try:
            repo = PaperRepository(session)
            paper = repo.get_by_id(paper_id, user_id)
            if paper is None:
                raise ValueError(f"Paper not found: {paper_id}")
            note_repo = UserNoteRepository(session)
            note = note_repo.create_or_update(
                UserNote(
                    paper_id=paper_id,
                    user_id=user_id,
                    content=content,
                    reading_status=ReadingStatus(reading_status),
                    relevance_score=relevance_score,
                    is_favorite=is_favorite,
                )
            )
            session.commit()
            session.refresh(note)
            return note
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def list_tags(self) -> list:
        session = self._get_session()
        try:
            repo = TagRepository(session)
            return repo.list_all()
        finally:
            session.close()

    def get_tag(self, tag_id: str):
        session = self._get_session()
        try:
            repo = TagRepository(session)
            return repo.get_by_id(tag_id)
        finally:
            session.close()

    def list_papers_by_tag(self, tag_id: str, user_id: str = "local") -> list[Paper]:
        session = self._get_session()
        try:
            repo = PaperRepository(session)
            return repo.list_by_tag(tag_id, user_id)
        finally:
            session.close()

    def list_authors(self, limit: int = 50, offset: int = 0) -> list:
        session = self._get_session()
        try:
            repo = AuthorRepository(session)
            return repo.list_all(limit, offset)
        finally:
            session.close()

    def count_authors(self) -> int:
        session = self._get_session()
        try:
            repo = AuthorRepository(session)
            return repo.count()
        finally:
            session.close()

    def get_author(self, author_id: str):
        session = self._get_session()
        try:
            repo = AuthorRepository(session)
            return repo.get_by_id(author_id)
        finally:
            session.close()

    def list_papers_by_author(self, author_id: str, user_id: str = "local") -> list[Paper]:
        session = self._get_session()
        try:
            repo = PaperRepository(session)
            return repo.list_by_author(author_id, user_id)
        finally:
            session.close()

    def update_paper(self, paper: Paper) -> Paper:
        session = self._get_session()
        try:
            repo = PaperRepository(session)
            merged = session.merge(paper)
            return repo.update(merged)
        finally:
            session.close()

    def delete_paper(self, paper_id: str, user_id: str = "local") -> bool:
        session = self._get_session()
        try:
            repo = PaperRepository(session)
            result = repo.delete(paper_id, user_id)
            if result:
                try:
                    self.embedding_store.remove_paper(paper_id)
                except Exception:
                    logger.warning("Failed to remove embeddings for %s", paper_id, exc_info=True)
            return result
        finally:
            session.close()

    async def find_references(
        self,
        text: str,
        user_id: str = "local",
        limit: int = 5,
        explain: bool = False,
        tag_ids: list[str] | None = None,
        collection_ids: list[str] | None = None,
        model_id: str | None = None,
    ) -> list[dict]:
        """Find papers that could serve as references for the given text.

        Returns list of dicts with keys:
        {"paper": Paper, "score": float, "explanation": str | None}
        """
        hits = self.embedding_store.search(text, n_results=limit * 3)
        if not hits:
            return []

        # Deduplicate by paper_id, keep best distance
        best: dict[str, float] = {}
        for h in hits:
            if h.paper_id not in best or h.distance < best[h.paper_id]:
                best[h.paper_id] = h.distance

        scored = {pid: 1.0 - (dist / 2.0) for pid, dist in best.items()}

        session = self._get_session()
        try:
            repo = PaperRepository(session)

            if collection_ids:
                allowed = self._resolve_collection_paper_ids(collection_ids)
                scored = {pid: s for pid, s in scored.items() if pid in allowed}

            if tag_ids:
                allowed = repo.get_paper_ids_by_tags(tag_ids, user_id)
                scored = {pid: s for pid, s in scored.items() if pid in allowed}

            # Load top papers
            papers = []
            for pid in sorted(scored, key=scored.get, reverse=True):
                paper = repo.get_with_relations(pid, user_id)
                if paper:
                    papers.append(paper)
                if len(papers) >= limit:
                    break

            # Batch explain if requested
            ai_warning = None
            assessments = [None] * len(papers)
            if explain and papers:
                try:
                    paper_inputs = [
                        {
                            "title": p.title,
                            "abstract": p.abstract or "",
                            "text": p.full_text or "",
                        }
                        for p in papers
                    ]
                    ai = self.get_ai(model_id)
                    assessments = await ai.explain_relevance_batch(
                        text, paper_inputs
                    )
                except Exception as exc:
                    logger.warning("Failed to explain relevance", exc_info=True)
                    ai_warning = str(exc)

            return {
                "results": [
                    {
                        "paper": paper,
                        "score": scored[paper.id],
                        "explanation": a["explanation"] if a else None,
                        "stance": a["stance"] if a else None,
                    }
                    for paper, a in zip(papers, assessments)
                ],
                "warning": ai_warning,
            }
        finally:
            session.close()

    # -- Collections --

    def create_collection(
        self, name: str, parent_id: str | None = None, user_id: str = "local"
    ) -> dict:
        session = self._get_session()
        try:
            repo = CollectionRepository(session)
            col = repo.create(name, parent_id, user_id)
            return {
                "id": col.id,
                "name": col.name,
                "parent_id": col.parent_id,
                "paper_count": 0,
                "children": [],
                "created_at": col.created_at,
            }
        finally:
            session.close()

    def get_or_create_collection(
        self, name: str, parent_id: str | None = None, user_id: str = "local"
    ) -> dict:
        session = self._get_session()
        try:
            repo = CollectionRepository(session)
            col = repo.get_or_create(name, parent_id, user_id)
            return {
                "id": col.id,
                "name": col.name,
                "parent_id": col.parent_id,
                "paper_count": len(col.papers) if col.papers else 0,
                "created_at": col.created_at,
            }
        finally:
            session.close()

    def _collection_to_dict(self, col, all_paper_ids: set | None = None) -> dict:
        if all_paper_ids is None:
            all_paper_ids = set()
        # Add this collection's own papers
        own_ids = {p.id for p in col.papers} if col.papers else set()
        all_paper_ids |= own_ids
        # Process children, collecting their paper IDs into the same set
        children = []
        for c in (col.children or []):
            child_ids: set = set()
            children.append(self._collection_to_dict(c, child_ids))
            all_paper_ids |= child_ids
        return {
            "id": col.id,
            "name": col.name,
            "parent_id": col.parent_id,
            "paper_count": len(all_paper_ids),
            "children": children,
            "created_at": col.created_at,
        }

    def list_collections(self, user_id: str = "local") -> list[dict]:
        session = self._get_session()
        try:
            repo = CollectionRepository(session)
            cols = repo.list_all(user_id)
            # Return only root collections (children are nested)
            roots = [c for c in cols if c.parent_id is None]
            return [self._collection_to_dict(c) for c in roots]
        finally:
            session.close()

    def get_collection(self, col_id: str, user_id: str = "local") -> dict | None:
        session = self._get_session()
        try:
            repo = CollectionRepository(session)
            col = repo.get_by_id(col_id, user_id)
            if col is None:
                return None
            # Get all paper IDs recursively and load them
            all_ids = repo.get_paper_ids_recursive(col_id)
            papers = []
            if all_ids:
                paper_repo = PaperRepository(session)
                for pid in all_ids:
                    p = paper_repo.get_with_relations(pid, user_id)
                    if p:
                        papers.append(p)
            return {
                **self._collection_to_dict(col),
                "papers": papers,
            }
        finally:
            session.close()

    def delete_collection(self, col_id: str, user_id: str = "local") -> bool:
        session = self._get_session()
        try:
            repo = CollectionRepository(session)
            return repo.delete(col_id, user_id)
        finally:
            session.close()

    def add_papers_to_collection(
        self, col_id: str, paper_ids: list[str], user_id: str = "local"
    ) -> None:
        session = self._get_session()
        try:
            repo = CollectionRepository(session)
            repo.add_papers(col_id, paper_ids)
        finally:
            session.close()

    def remove_papers_from_collection(
        self, col_id: str, paper_ids: list[str], user_id: str = "local"
    ) -> None:
        session = self._get_session()
        try:
            repo = CollectionRepository(session)
            repo.remove_papers(col_id, paper_ids)
        finally:
            session.close()

    # -- Saved Searches --

    def save_search(
        self,
        text: str,
        collection_id: str | None = None,
        results: list | None = None,
        user_id: str = "local",
    ) -> dict:
        session = self._get_session()
        try:
            repo = SavedSearchRepository(session)
            saved = repo.create(text, collection_id, results, user_id)
            return {
                "id": saved.id,
                "text": saved.text,
                "collection_id": saved.collection_id,
                "collection_name": saved.collection.name if saved.collection else None,
                "results": saved.results,
                "created_at": saved.created_at,
            }
        finally:
            session.close()

    def list_saved_searches(self, user_id: str = "local") -> list[dict]:
        session = self._get_session()
        try:
            repo = SavedSearchRepository(session)
            searches = repo.list_all(user_id)
            return [
                {
                    "id": s.id,
                    "text": s.text,
                    "collection_id": s.collection_id,
                    "collection_name": s.collection.name if s.collection else None,
                    "results": s.results,
                    "created_at": s.created_at,
                }
                for s in searches
            ]
        finally:
            session.close()

    def delete_saved_search(self, search_id: str, user_id: str = "local") -> bool:
        session = self._get_session()
        try:
            repo = SavedSearchRepository(session)
            return repo.delete(search_id, user_id)
        finally:
            session.close()

    def embedding_status(self, user_id: str = "local") -> dict:
        """Return embedding index stats vs paper count."""
        total_papers = self.count_papers(user_id)
        try:
            total_chunks = self.embedding_store.count()
        except Exception:
            total_chunks = 0
        return {"total_papers": total_papers, "indexed_chunks": total_chunks}

    def backfill_embeddings(self, user_id: str = "local") -> dict[str, int]:
        """Index embeddings for all existing papers. Returns counts."""
        session = self._get_session()
        try:
            repo = PaperRepository(session)
            papers = repo.list_all(user_id, limit=10000)
            indexed = 0
            failed = 0
            for paper in papers:
                try:
                    self.embedding_store.index_paper(
                        paper_id=paper.id,
                        title=paper.title,
                        abstract=paper.abstract,
                        sections=paper.sections,
                        full_text=paper.full_text,
                    )
                    indexed += 1
                except Exception:
                    logger.warning("Failed to index %s", paper.id, exc_info=True)
                    failed += 1
            return {"indexed": indexed, "failed": failed}
        finally:
            session.close()

    def _store_pdf(self, pdf_path: Path, user_id: str) -> str:
        """Copy PDF to storage directory."""
        storage_dir = self.settings.storage_path / user_id
        storage_dir.mkdir(parents=True, exist_ok=True)
        dest = storage_dir / pdf_path.name
        shutil.copy2(pdf_path, dest)
        return str(dest)

    def _save_paper(
        self,
        session: Session,
        extracted: ExtractedPaper,
        stored_path: str,
        user_id: str,
    ) -> Paper:
        repo = PaperRepository(session)
        paper = Paper(
            user_id=user_id,
            title=extracted.title or "Untitled",
            abstract=extracted.abstract,
            full_text=extracted.full_text,
            sections=extracted.sections or None,
            doi=extracted.doi,
            year=extracted.year,
            source_file=stored_path,
        )
        return repo.create(paper)

    def _save_authors(
        self, session: Session, extracted: ExtractedPaper, paper: Paper
    ) -> None:
        author_repo = AuthorRepository(session)
        for i, ea in enumerate(extracted.authors):
            author = author_repo.get_or_create(ea.name)
            if ea.affiliations:
                author.affiliations = ea.affiliations
            author_repo.link_to_paper(author, paper, position=i)

    def _save_citations(
        self,
        session: Session,
        extracted: ExtractedPaper,
        paper: Paper,
        user_id: str,
    ) -> None:
        cite_repo = CitationRepository(session)
        for ref in extracted.references:
            # Try to match citation to an existing paper in DB
            matched = cite_repo.find_matching_paper(ref.title, user_id)
            citation = Citation(
                user_id=user_id,
                citing_paper_id=paper.id,
                cited_paper_id=matched.id if matched else None,
                cited_title=ref.title,
                cited_authors=ref.authors,
                cited_year=ref.year,
                cited_doi=ref.doi,
                raw_reference=ref.raw,
            )
            cite_repo.create(citation)
