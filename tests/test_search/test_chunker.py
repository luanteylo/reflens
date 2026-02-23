"""Tests for paper text chunking."""

from reflens.search.chunker import chunk_paper


class TestChunkPaper:
    def test_abstract_only(self):
        chunks = chunk_paper("p1", "My Paper", abstract="This is the abstract.")
        assert len(chunks) == 1
        assert chunks[0].chunk_type == "abstract"
        assert chunks[0].text == "My Paper\n\nThis is the abstract."
        assert chunks[0].chunk_id == "p1::abstract::0"
        assert chunks[0].paper_id == "p1"

    def test_title_only_fallback(self):
        chunks = chunk_paper("p1", "My Paper")
        assert len(chunks) == 1
        assert chunks[0].chunk_type == "title"
        assert chunks[0].text == "My Paper"

    def test_sections_produce_section_chunks(self):
        sections = {"Intro": "Some intro text.", "Methods": "Methodology details."}
        chunks = chunk_paper("p1", "Paper", sections=sections)
        section_chunks = [c for c in chunks if c.chunk_type == "section"]
        assert len(section_chunks) == 2
        assert "Paper - Intro" in section_chunks[0].text
        assert "Some intro text." in section_chunks[0].text

    def test_abstract_plus_sections(self):
        chunks = chunk_paper(
            "p1",
            "Paper",
            abstract="Abstract text.",
            sections={"Intro": "Intro text."},
        )
        types = [c.chunk_type for c in chunks]
        assert "abstract" in types
        assert "section" in types

    def test_long_section_gets_split(self):
        long_text = "x" * 3000
        sections = {"LongSection": long_text}
        chunks = chunk_paper("p1", "Paper", sections=sections)
        section_chunks = [c for c in chunks if c.chunk_type == "section"]
        assert len(section_chunks) > 1
        # Each chunk should have the section prefix
        for c in section_chunks:
            assert "Paper - LongSection" in c.text

    def test_fulltext_fallback_when_no_sections(self):
        chunks = chunk_paper("p1", "Paper", full_text="Some body text here.")
        fulltext_chunks = [c for c in chunks if c.chunk_type == "fulltext"]
        assert len(fulltext_chunks) == 1
        assert "Paper\n\n" in fulltext_chunks[0].text

    def test_fulltext_not_used_when_sections_exist(self):
        chunks = chunk_paper(
            "p1",
            "Paper",
            sections={"Intro": "text"},
            full_text="Full text here.",
        )
        fulltext_chunks = [c for c in chunks if c.chunk_type == "fulltext"]
        assert len(fulltext_chunks) == 0

    def test_long_fulltext_gets_split(self):
        long_text = "word " * 1000  # ~5000 chars
        chunks = chunk_paper("p1", "Paper", full_text=long_text)
        fulltext_chunks = [c for c in chunks if c.chunk_type == "fulltext"]
        assert len(fulltext_chunks) > 1
        # Title prepended only to first chunk
        assert fulltext_chunks[0].text.startswith("Paper\n\n")
        assert not fulltext_chunks[1].text.startswith("Paper\n\n")

    def test_empty_abstract_ignored(self):
        chunks = chunk_paper("p1", "Paper", abstract="   ")
        assert all(c.chunk_type != "abstract" for c in chunks)

    def test_empty_section_ignored(self):
        sections = {"Intro": "", "Methods": "Real content."}
        chunks = chunk_paper("p1", "Paper", sections=sections)
        section_chunks = [c for c in chunks if c.chunk_type == "section"]
        assert len(section_chunks) == 1
        assert "Methods" in section_chunks[0].text

    def test_chunk_ids_are_unique(self):
        chunks = chunk_paper(
            "p1",
            "Paper",
            abstract="Abstract",
            sections={"A": "text a", "B": "text b"},
        )
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_chunk_ids_format(self):
        chunks = chunk_paper("paper-uuid", "Title", abstract="Abstract")
        assert chunks[0].chunk_id == "paper-uuid::abstract::0"
