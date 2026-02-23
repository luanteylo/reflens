"""Tests for database models and repositories."""

from sqlalchemy.orm import Session

from reflens.db.models import (
    Author,
    Citation,
    Paper,
    PaperAuthor,
    ReadingStatus,
    Tag,
    UserNote,
)
from reflens.db.repositories import (
    AuthorRepository,
    CitationRepository,
    PaperRepository,
    TagRepository,
    UserNoteRepository,
)


class TestPaperRepository:
    def test_create_paper(self, db_session: Session):
        repo = PaperRepository(db_session)
        paper = Paper(
            title="Test Paper",
            abstract="An abstract",
            full_text="Full text here",
            year=2024,
        )
        created = repo.create(paper)
        assert created.id is not None
        assert created.title == "Test Paper"
        assert created.user_id == "local"

    def test_get_by_id(self, db_session: Session):
        repo = PaperRepository(db_session)
        paper = repo.create(Paper(title="Findable Paper"))

        found = repo.get_by_id(paper.id)
        assert found is not None
        assert found.title == "Findable Paper"

    def test_get_by_id_wrong_user(self, db_session: Session):
        repo = PaperRepository(db_session)
        paper = repo.create(Paper(title="My Paper", user_id="user-1"))

        assert repo.get_by_id(paper.id, user_id="user-2") is None

    def test_list_all(self, db_session: Session):
        repo = PaperRepository(db_session)
        repo.create(Paper(title="Paper A"))
        repo.create(Paper(title="Paper B"))
        repo.create(Paper(title="Paper C"))

        papers = repo.list_all()
        assert len(papers) == 3

    def test_list_all_respects_user_id(self, db_session: Session):
        repo = PaperRepository(db_session)
        repo.create(Paper(title="User 1 Paper", user_id="u1"))
        repo.create(Paper(title="User 2 Paper", user_id="u2"))

        assert len(repo.list_all(user_id="u1")) == 1
        assert len(repo.list_all(user_id="u2")) == 1

    def test_search_by_title(self, db_session: Session):
        repo = PaperRepository(db_session)
        repo.create(Paper(title="Machine Learning in Healthcare"))
        repo.create(Paper(title="Deep Learning for NLP"))
        repo.create(Paper(title="Quantum Computing Basics"))

        results = repo.search_by_title("learning")
        assert len(results) == 2

    def test_delete(self, db_session: Session):
        repo = PaperRepository(db_session)
        paper = repo.create(Paper(title="To Delete"))

        assert repo.delete(paper.id) is True
        assert repo.get_by_id(paper.id) is None

    def test_delete_nonexistent(self, db_session: Session):
        repo = PaperRepository(db_session)
        assert repo.delete("nonexistent-id") is False


class TestAuthorRepository:
    def test_get_or_create_new(self, db_session: Session):
        repo = AuthorRepository(db_session)
        author = repo.get_or_create("Alice Smith")
        assert author.id is not None
        assert author.name == "Alice Smith"

    def test_get_or_create_existing(self, db_session: Session):
        repo = AuthorRepository(db_session)
        a1 = repo.get_or_create("Alice Smith")
        a2 = repo.get_or_create("Alice Smith")
        assert a1.id == a2.id

    def test_link_to_paper(self, db_session: Session):
        paper_repo = PaperRepository(db_session)
        author_repo = AuthorRepository(db_session)

        paper = paper_repo.create(Paper(title="Authored Paper"))
        author = author_repo.get_or_create("Bob Jones")
        author_repo.link_to_paper(author, paper, position=0)
        db_session.commit()

        # Verify the association exists
        found = paper_repo.get_with_relations(paper.id)
        assert found is not None
        assert len(found.authors) == 1
        assert found.authors[0].name == "Bob Jones"


class TestCitationRepository:
    def test_create_citation(self, db_session: Session):
        paper_repo = PaperRepository(db_session)
        cite_repo = CitationRepository(db_session)

        paper = paper_repo.create(Paper(title="Citing Paper"))
        citation = cite_repo.create(
            Citation(
                citing_paper_id=paper.id,
                cited_title="Some Referenced Paper",
                cited_authors="Doe et al.",
                cited_year=2020,
            )
        )
        assert citation.id is not None

    def test_get_by_paper(self, db_session: Session):
        paper_repo = PaperRepository(db_session)
        cite_repo = CitationRepository(db_session)

        paper = paper_repo.create(Paper(title="Paper With Refs"))
        cite_repo.create(
            Citation(citing_paper_id=paper.id, cited_title="Ref 1", cited_year=2020)
        )
        cite_repo.create(
            Citation(citing_paper_id=paper.id, cited_title="Ref 2", cited_year=2021)
        )
        db_session.commit()

        refs = cite_repo.get_by_paper(paper.id)
        assert len(refs) == 2

    def test_find_matching_paper(self, db_session: Session):
        paper_repo = PaperRepository(db_session)
        cite_repo = CitationRepository(db_session)

        paper_repo.create(Paper(title="Attention Is All You Need", year=2017))

        match = cite_repo.find_matching_paper("Attention Is All You Need")
        assert match is not None
        assert match.year == 2017


class TestTagRepository:
    def test_get_or_create(self, db_session: Session):
        repo = TagRepository(db_session)
        tag = repo.get_or_create("machine-learning")
        assert tag.name == "machine-learning"

    def test_hierarchical_tags(self, db_session: Session):
        repo = TagRepository(db_session)
        parent = repo.get_or_create("machine-learning")
        child = repo.get_or_create("deep-learning", parent_id=parent.id)
        db_session.commit()

        assert child.parent_id == parent.id

    def test_tag_paper(self, db_session: Session):
        paper_repo = PaperRepository(db_session)
        tag_repo = TagRepository(db_session)

        paper = paper_repo.create(Paper(title="Tagged Paper"))
        tag = tag_repo.get_or_create("nlp")
        pt = tag_repo.tag_paper(
            paper_id=paper.id,
            tag_id=tag.id,
            section="Methods",
            confidence=0.95,
            source="ai",
        )
        db_session.commit()

        assert pt.section == "Methods"
        assert pt.confidence == 0.95


class TestUserNoteRepository:
    def test_create_note(self, db_session: Session):
        paper_repo = PaperRepository(db_session)
        note_repo = UserNoteRepository(db_session)

        paper = paper_repo.create(Paper(title="Noted Paper"))
        note = note_repo.create_or_update(
            UserNote(
                paper_id=paper.id,
                content="Great paper!",
                reading_status=ReadingStatus.READ,
                relevance_score=5,
            )
        )
        db_session.commit()

        assert note.content == "Great paper!"
        assert note.reading_status == ReadingStatus.READ

    def test_update_existing_note(self, db_session: Session):
        paper_repo = PaperRepository(db_session)
        note_repo = UserNoteRepository(db_session)

        paper = paper_repo.create(Paper(title="Updated Note Paper"))
        note_repo.create_or_update(
            UserNote(paper_id=paper.id, content="First draft")
        )
        db_session.commit()

        updated = note_repo.create_or_update(
            UserNote(paper_id=paper.id, content="Updated note")
        )
        db_session.commit()

        assert updated.content == "Updated note"
