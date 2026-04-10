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

    def _log_usage(self, ai: AIProvider, user_id: str = "local") -> None:
        """Save AI usage to database if available."""
        if ai.last_usage is None:
            return
        try:
            from reflens.db.models import UsageLog
            session = self._get_session()
            try:
                log = UsageLog(
                    user_id=user_id,
                    provider=ai.last_usage.provider,
                    model=ai.last_usage.model,
                    operation=ai.last_usage.operation,
                    prompt_tokens=ai.last_usage.prompt_tokens,
                    completion_tokens=ai.last_usage.completion_tokens,
                    total_tokens=ai.last_usage.total_tokens,
                    cost_usd=ai.last_usage.cost_usd,
                )
                session.add(log)
                session.commit()
            finally:
                session.close()
            ai.last_usage = None
        except Exception:
            pass  # Don't fail operations on usage logging errors

    def get_ai(self, model_id: str | None = None, user_id: str | None = None) -> AIProvider:
        """Get an AI provider for a specific model, using user's key if available."""
        if not model_id and not user_id:
            return self.ai

        # Check if user has their own key for this provider
        effective_settings = self.settings
        if user_id and user_id != "local":
            try:
                from reflens.ai.factory import parse_model_spec
                from reflens.auth.crypto import decrypt_key
                from reflens.db.models import UserApiKey
                from sqlalchemy import select

                provider, _ = parse_model_spec(model_id or f"{self.settings.ai_provider}/{self.settings.ai_model}")
                session = self._get_session()
                try:
                    key_row = session.execute(
                        select(UserApiKey).where(
                            UserApiKey.user_id == user_id,
                            UserApiKey.provider == provider,
                        )
                    ).scalar_one_or_none()
                    if key_row:
                        from copy import copy
                        effective_settings = copy(self.settings)
                        decrypted = decrypt_key(key_row.encrypted_key, self.settings)
                        if provider == "claude":
                            effective_settings.anthropic_api_key = decrypted
                        elif provider == "openai":
                            effective_settings.openai_api_key = decrypted
                finally:
                    session.close()
            except Exception:
                pass  # Fall back to server keys

        return create_ai_provider(effective_settings, model_id)

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

    async def summarize_paper(
        self,
        paper_id: str,
        user_id: str = "local",
        model_id: str | None = None,
        user_prompt: str | None = None,
    ) -> dict:
        """Generate AI summary for a paper. Returns the AISummary as a dict."""
        from reflens.ai.factory import parse_model_spec
        from reflens.db.models import AISummary

        session = self._get_session()
        try:
            repo = PaperRepository(session)
            paper = repo.get_by_id(paper_id, user_id)
            if paper is None:
                raise ValueError(f"Paper not found: {paper_id}")

            ai = self.get_ai(model_id, user_id)
            resolved_id = model_id or f"{self.settings.ai_provider}/{self.settings.ai_model}"
            _, model_name = parse_model_spec(resolved_id)

            abstract = paper.abstract or ""
            title = paper.title
            if user_prompt:
                title = f"{paper.title}\n\nIMPORTANT - Additional instructions from the user: {user_prompt}"

            summary = await ai.summarize(
                title=title,
                abstract=abstract,
                full_text=paper.full_text or "",
            )
            self._log_usage(ai, user_id)

            # Also update the paper's flat fields (backward compat)
            paper.ai_summary = summary.overview
            paper.ai_key_contributions = summary.key_contributions
            paper.ai_methodology = summary.methodology
            paper.ai_findings = summary.findings
            paper.ai_limitations = summary.limitations

            # Create AISummary record
            ai_summary = AISummary(
                paper_id=paper_id,
                user_id=user_id,
                model_id=resolved_id,
                model_name=model_name,
                user_prompt=user_prompt,
                overview=summary.overview,
                key_contributions=summary.key_contributions,
                methodology=summary.methodology,
                findings=summary.findings,
                limitations=summary.limitations,
            )
            session.add(ai_summary)
            session.commit()

            return {
                "id": ai_summary.id,
                "model_id": ai_summary.model_id,
                "model_name": ai_summary.model_name,
                "user_prompt": ai_summary.user_prompt,
                "overview": ai_summary.overview,
                "key_contributions": ai_summary.key_contributions,
                "methodology": ai_summary.methodology,
                "findings": ai_summary.findings,
                "limitations": ai_summary.limitations,
                "created_at": ai_summary.created_at.isoformat(),
            }
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_paper_summaries(self, paper_id: str, user_id: str = "local") -> list[dict]:
        """Get all AI summaries for a paper."""
        from sqlalchemy import select
        from reflens.db.models import AISummary

        session = self._get_session()
        try:
            stmt = (
                select(AISummary)
                .where(AISummary.paper_id == paper_id, AISummary.user_id == user_id)
                .order_by(AISummary.created_at.desc())
            )
            summaries = list(session.execute(stmt).scalars().all())
            return [
                {
                    "id": s.id,
                    "model_id": s.model_id,
                    "model_name": s.model_name,
                    "user_prompt": s.user_prompt,
                    "overview": s.overview,
                    "key_contributions": s.key_contributions,
                    "methodology": s.methodology,
                    "findings": s.findings,
                    "limitations": s.limitations,
                    "created_at": s.created_at.isoformat(),
                }
                for s in summaries
            ]
        finally:
            session.close()

    async def tag_paper(self, paper_id: str, user_id: str = "local", model_id: str | None = None) -> list[str]:
        """Generate AI tags for a paper."""
        session = self._get_session()
        try:
            repo = PaperRepository(session)
            paper = repo.get_by_id(paper_id, user_id)
            if paper is None:
                raise ValueError(f"Paper not found: {paper_id}")

            ai = self.get_ai(model_id, user_id)
            generated = await ai.generate_tags(
                title=paper.title,
                abstract=paper.abstract or "",
                sections=paper.sections or {},
            )
            self._log_usage(ai, user_id)

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

    def _keyword_score(self, query: str, paper) -> float:
        """Simple keyword matching score based on query terms in title/abstract."""
        terms = [t.lower() for t in query.split() if len(t) > 2]
        if not terms:
            return 0.0

        text = f"{paper.title} {paper.abstract or ''}".lower()
        matches = sum(1 for t in terms if t in text)
        return matches / len(terms) if terms else 0.0

    def search_papers(
        self,
        query: str,
        user_id: str = "local",
        limit: int = 20,
        collection_ids: list[str] | None = None,
    ) -> list[dict]:
        """Hybrid search: semantic embeddings + keyword matching + abstract boost.

        Returns list of dicts with keys {"paper": Paper, "score": float | None}.
        """
        from reflens.search.embedder import CHUNK_BOOST

        allowed_ids: set[str] | None = None
        if collection_ids:
            allowed_ids = self._resolve_collection_paper_ids(collection_ids)
            if not allowed_ids:
                return []

        semantic_scores: dict[str, float] = {}
        keyword_scores: dict[str, float] = {}

        # 1. Semantic search with chunk-type boosting
        try:
            if self.embedding_store.is_available() and self.embedding_store.count() > 0:
                hits = self.embedding_store.search(query, n_results=limit * 5)
                if hits:
                    # Aggregate scores per paper with chunk-type boost
                    paper_hits: dict[str, list[tuple[float, str]]] = {}
                    for h in hits:
                        if h.paper_id not in paper_hits:
                            paper_hits[h.paper_id] = []
                        paper_hits[h.paper_id].append((h.distance, h.chunk_type))

                    for pid, ph in paper_hits.items():
                        # Best hit with boost
                        best_score = 0.0
                        for dist, ctype in ph:
                            similarity = 1.0 - (dist / 2.0)
                            boost = CHUNK_BOOST.get(ctype, 1.0)
                            boosted = min(1.0, similarity * boost)
                            best_score = max(best_score, boosted)
                        # Bonus for multiple chunk matches (paper covers topic broadly)
                        multi_match_bonus = min(0.1, len(ph) * 0.02)
                        semantic_scores[pid] = min(1.0, best_score + multi_match_bonus)
        except Exception:
            logger.warning("Semantic search failed", exc_info=True)

        # 2. Keyword search (SQL ILIKE)
        session = self._get_session()
        try:
            repo = PaperRepository(session)
            kw_papers = repo.search_by_title(query, user_id)
            for p in kw_papers:
                keyword_scores[p.id] = self._keyword_score(query, p)
        finally:
            session.close()

        # 3. Combine scores: 70% semantic + 30% keyword
        all_pids = set(semantic_scores.keys()) | set(keyword_scores.keys())
        if allowed_ids is not None:
            all_pids &= allowed_ids

        combined: dict[str, float] = {}
        for pid in all_pids:
            sem = semantic_scores.get(pid, 0.0)
            kw = keyword_scores.get(pid, 0.0)
            combined[pid] = sem * 0.7 + kw * 0.3

        # 4. Load papers sorted by combined score
        session = self._get_session()
        try:
            repo = PaperRepository(session)
            results = []
            for pid in sorted(combined, key=combined.get, reverse=True):
                paper = repo.get_with_relations(pid, user_id)
                if paper:
                    results.append({"paper": paper, "score": combined[pid]})
                if len(results) >= limit:
                    break
            return results
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
        from sqlalchemy import update

        from reflens.db.models import Citation

        session = self._get_session()
        try:
            # Null out incoming citation references from other papers so the
            # FK constraint on citations.cited_paper_id doesn't block the delete.
            session.execute(
                update(Citation)
                .where(Citation.cited_paper_id == paper_id)
                .values(cited_paper_id=None)
            )
            session.commit()

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
    ) -> dict:
        """Find papers that could serve as references for the given text.

        Uses hybrid search + AI re-ranking for best results.
        """
        # 1. Get more candidates than needed for AI re-ranking
        candidate_limit = limit * 3 if explain else limit
        results = self.search_papers(
            query=text,
            user_id=user_id,
            limit=candidate_limit,
            collection_ids=collection_ids,
        )

        # Filter by tags if provided
        if tag_ids:
            session = self._get_session()
            try:
                repo = PaperRepository(session)
                allowed = repo.get_paper_ids_by_tags(tag_ids, user_id)
                results = [r for r in results if r["paper"].id in allowed]
            finally:
                session.close()

        ai_warning = None
        assessments = [None] * len(results)

        if explain and results:
            ai = self.get_ai(model_id, user_id)

            # 2. AI re-ranking: send candidates, get AI-informed ordering
            try:
                paper_inputs = [
                    {
                        "title": r["paper"].title,
                        "abstract": r["paper"].abstract or "",
                    }
                    for r in results
                ]
                ranking = await ai.rerank(text, paper_inputs)
                self._log_usage(ai, user_id)

                # Reorder results based on AI ranking
                if ranking:
                    reordered = []
                    reasons = {}
                    for item in ranking:
                        idx = item.get("index", -1)
                        if 0 <= idx < len(results):
                            reordered.append(results[idx])
                            reasons[idx] = item.get("reason", "")
                    # Add any papers the AI didn't include at the end
                    included = {item["index"] for item in ranking if 0 <= item.get("index", -1) < len(results)}
                    for i, r in enumerate(results):
                        if i not in included:
                            reordered.append(r)
                    results = reordered
                    # Store reasons as explanations
                    assessments = [
                        {"stance": "relevant", "explanation": reasons.get(ranking[i]["index"], "")}
                        if i < len(ranking) else None
                        for i in range(len(results))
                    ]
            except Exception as exc:
                logger.warning("AI re-ranking failed", exc_info=True)
                ai_warning = str(exc)

        # Trim to requested limit
        results = results[:limit]

        # 3. Per-result stance analysis on the final set
        if explain and results and not ai_warning:
            try:
                paper_inputs = [
                    {
                        "title": r["paper"].title,
                        "abstract": r["paper"].abstract or "",
                        "text": r["paper"].full_text or "",
                    }
                    for r in results
                ]
                ai = self.get_ai(model_id, user_id)
                stance_results = await ai.explain_relevance_batch(text, paper_inputs)
                self._log_usage(ai, user_id)
                # Merge: keep rerank reason + add stance
                for i, stance in enumerate(stance_results):
                    if stance and i < len(assessments):
                        prev_reason = assessments[i]["explanation"] if assessments[i] else ""
                        assessments[i] = {
                            "stance": stance.get("stance", "neutral"),
                            "explanation": stance.get("explanation", prev_reason),
                        }
            except Exception as exc:
                logger.warning("Stance analysis failed", exc_info=True)
                if not ai_warning:
                    ai_warning = str(exc)
        assessments = assessments[:limit]

        return {
            "results": [
                {
                    "paper": r["paper"],
                    "score": r["score"],
                    "explanation": a["explanation"] if a else None,
                    "stance": a["stance"] if a else None,
                }
                for r, a in zip(results, assessments)
            ],
            "warning": ai_warning,
        }

    async def explain_single(
        self,
        query: str,
        paper_id: str,
        user_id: str = "local",
        model_id: str | None = None,
    ) -> dict:
        """Explain relevance for a single paper. Returns {stance, explanation}."""
        session = self._get_session()
        try:
            repo = PaperRepository(session)
            paper = repo.get_with_relations(paper_id, user_id)
            if paper is None:
                raise ValueError("Paper not found")
            ai = self.get_ai(model_id, user_id)
            result = await ai.explain_relevance(
                query=query,
                paper_title=paper.title,
                paper_abstract=paper.abstract or "",
                paper_text=paper.full_text or "",
            )
            self._log_usage(ai, user_id)
            return result
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

    def rename_collection(
        self, col_id: str, name: str, user_id: str = "local"
    ) -> dict | None:
        session = self._get_session()
        try:
            repo = CollectionRepository(session)
            col = repo.rename(col_id, name, user_id)
            if col is None:
                return None
            return {
                "id": col.id,
                "name": col.name,
                "parent_id": col.parent_id,
                "paper_count": len(col.papers) if col.papers else 0,
                "children": [],
                "created_at": col.created_at,
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
