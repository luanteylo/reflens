"""Shared test fixtures."""

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from reflens.config import Settings
from reflens.db.models import Base
from reflens.extraction.models import (
    ExtractedAuthor,
    ExtractedPaper,
    ExtractedReference,
)


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def settings(tmp_dir: Path) -> Settings:
    return Settings(
        database_url="sqlite:///:memory:",
        grobid_url="http://localhost:8070",
        storage_path=tmp_dir / "storage",
        chroma_path=tmp_dir / "chroma",
        anthropic_api_key="test-key",
        openai_api_key="test-key",
    )


@pytest.fixture
def db_session(settings: Settings) -> Session:
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()
    yield session
    session.close()


@pytest.fixture
def sample_extracted_paper() -> ExtractedPaper:
    return ExtractedPaper(
        title="Deep Learning for Scientific Discovery",
        abstract="We present a novel approach to applying deep learning in scientific research.",
        full_text="Introduction\nDeep learning has revolutionized many fields...",
        sections={
            "Introduction": "Deep learning has revolutionized many fields of science.",
            "Methods": "We used a transformer-based architecture with attention mechanisms.",
            "Results": "Our model achieved state-of-the-art performance on 5 benchmarks.",
            "Conclusion": "Deep learning shows great promise for scientific discovery.",
        },
        authors=[
            ExtractedAuthor(name="Alice Smith", affiliations=["MIT"]),
            ExtractedAuthor(name="Bob Jones", affiliations=["Stanford"]),
        ],
        references=[
            ExtractedReference(
                title="Attention Is All You Need",
                authors="Vaswani et al.",
                year=2017,
                doi="10.xxxxx",
                raw="Vaswani et al., Attention Is All You Need, NeurIPS 2017",
            ),
            ExtractedReference(
                title="BERT: Pre-training of Deep Bidirectional Transformers",
                authors="Devlin et al.",
                year=2019,
                raw="Devlin et al., BERT, 2019",
            ),
        ],
        doi="10.1234/test",
        year=2024,
    )


@pytest.fixture
def sample_pdf(tmp_dir: Path) -> Path:
    """Create a minimal valid PDF for testing."""
    try:
        import fitz

        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Deep Learning for Scientific Discovery", fontsize=18)
        page.insert_text((72, 120), "Alice Smith, Bob Jones")
        page.insert_text((72, 160), "Abstract: We present a novel approach to applying "
                         "deep learning in scientific research.")
        page.insert_text((72, 200), "Introduction")
        page.insert_text((72, 230), "Deep learning has revolutionized many fields of science. "
                         "This paper explores new applications.")

        pdf_path = tmp_dir / "test_paper.pdf"
        doc.save(str(pdf_path))
        doc.close()
        return pdf_path
    except ImportError:
        pytest.skip("PyMuPDF not installed")
