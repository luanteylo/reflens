"""SQLAlchemy models for RefLens.

All models include user_id for SaaS-readiness. In local mode a default user is used.
"""

import uuid
from datetime import UTC, datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

DEFAULT_USER_ID = "local"


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Future: paid plans
    plan: Mapped[str] = mapped_column(String(50), default="free")

    # Future: OAuth
    oauth_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    oauth_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class AISummary(Base):
    __tablename__ = "ai_summaries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    paper_id: Mapped[str] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(String(255), default=DEFAULT_USER_ID)
    model_id: Mapped[str] = mapped_column(String(100))  # e.g. "ollama/mistral"
    model_name: Mapped[str] = mapped_column(String(100))  # e.g. "mistral"
    user_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)

    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_contributions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    methodology: Mapped[str | None] = mapped_column(Text, nullable=True)
    findings: Mapped[str | None] = mapped_column(Text, nullable=True)
    limitations: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    paper: Mapped["Paper"] = relationship(back_populates="summaries")


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(255), default=DEFAULT_USER_ID, index=True)
    provider: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(100))
    operation: Mapped[str] = mapped_column(String(50))  # summarize, tag, relevance, etc.
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class UserApiKey(Base):
    __tablename__ = "user_api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    provider: Mapped[str] = mapped_column(String(50))  # claude, openai
    encrypted_key: Mapped[str] = mapped_column(Text)
    label: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    default_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    search_limit: Mapped[int] = mapped_column(Integer, default=10)
    explain_by_default: Mapped[bool] = mapped_column(Boolean, default=True)
    context_length: Mapped[int] = mapped_column(Integer, default=6000)
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class SearchHistory(Base):
    __tablename__ = "search_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(255), default=DEFAULT_USER_ID, index=True)
    query: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ReadingStatus(PyEnum):
    UNREAD = "unread"
    PARTIAL = "partial"
    READ = "read"


# -- Association tables --

class PaperAuthor(Base):
    __tablename__ = "paper_authors"

    paper_id: Mapped[str] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True
    )
    author_id: Mapped[str] = mapped_column(
        ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, default=0)


class PaperCollectionMembership(Base):
    __tablename__ = "paper_collection_members"

    paper_id: Mapped[str] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True
    )
    collection_id: Mapped[str] = mapped_column(
        ForeignKey("paper_collections.id", ondelete="CASCADE"), primary_key=True
    )


class PaperTag(Base):
    __tablename__ = "paper_tags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.id"))
    tag_id: Mapped[str] = mapped_column(ForeignKey("tags.id"))
    section: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    source: Mapped[str] = mapped_column(String(10), default="ai")  # "ai" or "user"
    user_id: Mapped[str] = mapped_column(String(255), default=DEFAULT_USER_ID)

    tag: Mapped["Tag"] = relationship(lazy="joined")


# -- Main models --

class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(255), default=DEFAULT_USER_ID, index=True)

    title: Mapped[str] = mapped_column(String(1000))
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    sections: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    doi: Mapped[str | None] = mapped_column(String(255), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_file: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # AI-generated fields
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_key_contributions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ai_methodology: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_findings: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_limitations: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    # Relationships
    authors: Mapped[list["Author"]] = relationship(
        secondary="paper_authors",
        back_populates="papers",
        passive_deletes=True,
    )
    citing_refs: Mapped[list["Citation"]] = relationship(
        back_populates="citing_paper",
        foreign_keys="Citation.citing_paper_id",
        cascade="all, delete-orphan",
    )
    tags: Mapped[list["PaperTag"]] = relationship(cascade="all, delete-orphan")
    summaries: Mapped[list["AISummary"]] = relationship(
        back_populates="paper", cascade="all, delete-orphan"
    )
    notes: Mapped[list["UserNote"]] = relationship(
        back_populates="paper", cascade="all, delete-orphan"
    )


class Author(Base):
    __tablename__ = "authors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(500))
    affiliations: Mapped[list | None] = mapped_column(JSON, nullable=True)

    papers: Mapped[list["Paper"]] = relationship(
        secondary="paper_authors", back_populates="authors"
    )


class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(255), default=DEFAULT_USER_ID, index=True)

    citing_paper_id: Mapped[str] = mapped_column(ForeignKey("papers.id"))
    cited_paper_id: Mapped[str | None] = mapped_column(
        ForeignKey("papers.id"), nullable=True
    )

    cited_title: Mapped[str] = mapped_column(String(1000))
    cited_authors: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    cited_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cited_doi: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_reference: Mapped[str | None] = mapped_column(Text, nullable=True)

    citing_paper: Mapped["Paper"] = relationship(
        back_populates="citing_refs", foreign_keys=[citing_paper_id]
    )
    cited_paper: Mapped["Paper | None"] = relationship(
        foreign_keys=[cited_paper_id], passive_deletes=True
    )


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("tags.id"), nullable=True
    )

    children: Mapped[list["Tag"]] = relationship(back_populates="parent")
    parent: Mapped["Tag | None"] = relationship(
        back_populates="children", remote_side=[id]
    )


class UserNote(Base):
    __tablename__ = "user_notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(255), default=DEFAULT_USER_ID, index=True)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.id"))

    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    reading_status: Mapped[ReadingStatus] = mapped_column(
        Enum(ReadingStatus), default=ReadingStatus.UNREAD
    )
    relevance_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    paper: Mapped["Paper"] = relationship(back_populates="notes")


class PaperCollection(Base):
    __tablename__ = "paper_collections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(255), default=DEFAULT_USER_ID, index=True)
    name: Mapped[str] = mapped_column(String(255))
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("paper_collections.id", ondelete="CASCADE"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    papers: Mapped[list["Paper"]] = relationship(
        secondary="paper_collection_members",
        passive_deletes=True,
    )
    children: Mapped[list["PaperCollection"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )
    parent: Mapped["PaperCollection | None"] = relationship(
        back_populates="children", remote_side=[id]
    )


class SavedSearch(Base):
    __tablename__ = "saved_searches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(255), default=DEFAULT_USER_ID, index=True)
    text: Mapped[str] = mapped_column(Text)
    collection_id: Mapped[str | None] = mapped_column(
        ForeignKey("paper_collections.id", ondelete="SET NULL"), nullable=True
    )
    results: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    collection: Mapped["PaperCollection | None"] = relationship(lazy="joined")
