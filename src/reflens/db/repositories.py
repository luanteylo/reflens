"""Data access layer for RefLens entities."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from reflens.db.models import (
    Author,
    Citation,
    Paper,
    PaperAuthor,
    PaperTag,
    Tag,
    UserNote,
)


class PaperRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, paper: Paper) -> Paper:
        self.session.add(paper)
        self.session.commit()
        self.session.refresh(paper)
        return paper

    def get_by_id(self, paper_id: str, user_id: str = "local") -> Paper | None:
        stmt = select(Paper).where(Paper.id == paper_id, Paper.user_id == user_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def count(self, user_id: str = "local") -> int:
        stmt = select(func.count()).select_from(Paper).where(Paper.user_id == user_id)
        return self.session.execute(stmt).scalar_one()

    def list_all(self, user_id: str = "local", limit: int = 50, offset: int = 0) -> list[Paper]:
        stmt = (
            select(Paper)
            .where(Paper.user_id == user_id)
            .options(
                selectinload(Paper.authors),
                selectinload(Paper.tags),
                selectinload(Paper.notes),
            )
            .order_by(Paper.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.execute(stmt).scalars().all())

    def list_by_tag(self, tag_id: str, user_id: str = "local") -> list[Paper]:
        stmt = (
            select(Paper)
            .join(PaperTag, Paper.id == PaperTag.paper_id)
            .where(PaperTag.tag_id == tag_id, Paper.user_id == user_id)
            .options(selectinload(Paper.authors), selectinload(Paper.tags))
            .order_by(Paper.created_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def list_by_author(self, author_id: str, user_id: str = "local") -> list[Paper]:
        stmt = (
            select(Paper)
            .join(PaperAuthor, Paper.id == PaperAuthor.paper_id)
            .where(PaperAuthor.author_id == author_id, Paper.user_id == user_id)
            .options(selectinload(Paper.authors), selectinload(Paper.tags))
            .order_by(Paper.created_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def search_by_title(self, query: str, user_id: str = "local") -> list[Paper]:
        stmt = (
            select(Paper)
            .where(Paper.user_id == user_id, Paper.title.ilike(f"%{query}%"))
            .options(selectinload(Paper.authors), selectinload(Paper.tags))
            .order_by(Paper.created_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_with_relations(self, paper_id: str, user_id: str = "local") -> Paper | None:
        stmt = (
            select(Paper)
            .where(Paper.id == paper_id, Paper.user_id == user_id)
            .options(
                selectinload(Paper.authors),
                selectinload(Paper.citing_refs),
                selectinload(Paper.tags),
                selectinload(Paper.notes),
            )
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def delete(self, paper_id: str, user_id: str = "local") -> bool:
        paper = self.get_by_id(paper_id, user_id)
        if paper is None:
            return False
        self.session.delete(paper)
        self.session.commit()
        return True

    def update(self, paper: Paper) -> Paper:
        self.session.commit()
        self.session.refresh(paper)
        return paper


class AuthorRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, author_id: str) -> Author | None:
        stmt = select(Author).where(Author.id == author_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_or_create(self, name: str) -> Author:
        stmt = select(Author).where(Author.name == name)
        author = self.session.execute(stmt).scalar_one_or_none()
        if author is None:
            author = Author(name=name)
            self.session.add(author)
            self.session.flush()
        return author

    def count(self) -> int:
        stmt = select(func.count()).select_from(Author)
        return self.session.execute(stmt).scalar_one()

    def list_all(self, limit: int = 50, offset: int = 0) -> list[Author]:
        stmt = select(Author).order_by(Author.name).limit(limit).offset(offset)
        return list(self.session.execute(stmt).scalars().all())

    def link_to_paper(self, author: Author, paper: Paper, position: int = 0) -> None:
        assoc = PaperAuthor(
            paper_id=paper.id, author_id=author.id, position=position
        )
        self.session.add(assoc)
        self.session.flush()


class CitationRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, citation: Citation) -> Citation:
        self.session.add(citation)
        self.session.flush()
        return citation

    def get_by_paper(self, paper_id: str) -> list[Citation]:
        stmt = (
            select(Citation)
            .where(Citation.citing_paper_id == paper_id)
            .order_by(Citation.cited_year.desc().nullslast())
        )
        return list(self.session.execute(stmt).scalars().all())

    def find_matching_paper(self, title: str, user_id: str = "local") -> Paper | None:
        """Try to find an existing paper that matches a citation."""
        stmt = (
            select(Paper)
            .where(Paper.user_id == user_id, Paper.title.ilike(f"%{title}%"))
            .limit(1)
        )
        return self.session.execute(stmt).scalar_one_or_none()


class TagRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, tag_id: str) -> Tag | None:
        stmt = select(Tag).where(Tag.id == tag_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_or_create(self, name: str, parent_id: str | None = None) -> Tag:
        stmt = select(Tag).where(Tag.name == name)
        tag = self.session.execute(stmt).scalar_one_or_none()
        if tag is None:
            tag = Tag(name=name, parent_id=parent_id)
            self.session.add(tag)
            self.session.flush()
        return tag

    def list_all(self) -> list[Tag]:
        stmt = select(Tag).order_by(Tag.name)
        return list(self.session.execute(stmt).scalars().all())

    def tag_paper(
        self,
        paper_id: str,
        tag_id: str,
        section: str | None = None,
        confidence: float = 1.0,
        source: str = "ai",
        user_id: str = "local",
    ) -> PaperTag:
        pt = PaperTag(
            paper_id=paper_id,
            tag_id=tag_id,
            section=section,
            confidence=confidence,
            source=source,
            user_id=user_id,
        )
        self.session.add(pt)
        self.session.flush()
        return pt


class UserNoteRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_or_update(self, note: UserNote) -> UserNote:
        existing = (
            self.session.execute(
                select(UserNote).where(
                    UserNote.paper_id == note.paper_id,
                    UserNote.user_id == note.user_id,
                )
            )
            .scalar_one_or_none()
        )
        if existing:
            existing.content = note.content
            existing.reading_status = note.reading_status
            existing.relevance_score = note.relevance_score
            existing.is_favorite = note.is_favorite
            self.session.flush()
            return existing

        self.session.add(note)
        self.session.flush()
        return note
