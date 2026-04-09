"""Split paper text into embeddable chunks.

BGE models handle ~512 tokens (~2000 chars). We create specialized chunks
with different weights: abstract chunks get boosted in search scoring.
"""

from dataclasses import dataclass

CHUNK_SIZE = 2000
CHUNK_OVERLAP = 300


@dataclass
class PaperChunk:
    chunk_id: str
    paper_id: str
    text: str
    chunk_type: str  # "abstract", "section", "fulltext", "title"
    index: int


def _sliding_window(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping windows."""
    if len(text) <= size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def chunk_paper(
    paper_id: str,
    title: str,
    abstract: str | None = None,
    sections: dict[str, str] | None = None,
    full_text: str | None = None,
) -> list[PaperChunk]:
    """Split a paper into embeddable chunks.

    Strategy:
    1. Title + abstract combined (highest value for search)
    2. Abstract alone (for matching claims against abstracts)
    3. Key sections: introduction, conclusion, results (high signal)
    4. Other sections
    5. Full text fallback
    """
    chunks: list[PaperChunk] = []

    # 1. Title + Abstract combined chunk (best for topic matching)
    if abstract and abstract.strip():
        combined = f"{title}\n\nAbstract: {abstract.strip()}"
        chunks.append(PaperChunk(
            chunk_id=f"{paper_id}::abstract::0",
            paper_id=paper_id,
            text=combined,
            chunk_type="abstract",
            index=0,
        ))

    # 2. Section chunks with title context
    if sections:
        # Prioritize high-signal sections first
        priority_keys = ["introduction", "conclusion", "results", "discussion", "abstract"]
        ordered = []
        for key in priority_keys:
            for name, text in sections.items():
                if key in name.lower() and (name, text) not in ordered:
                    ordered.append((name, text))
        for name, text in sections.items():
            if (name, text) not in ordered:
                ordered.append((name, text))

        idx = 0
        for section_name, section_text in ordered:
            if not section_text or not section_text.strip():
                continue
            prefix = f"{title} - {section_name}\n\n"
            text = section_text.strip()
            if len(prefix + text) > CHUNK_SIZE * 1.25:
                windows = _sliding_window(text)
                for window in windows:
                    chunks.append(PaperChunk(
                        chunk_id=f"{paper_id}::section::{idx}",
                        paper_id=paper_id,
                        text=f"{prefix}{window}",
                        chunk_type="section",
                        index=idx,
                    ))
                    idx += 1
            else:
                chunks.append(PaperChunk(
                    chunk_id=f"{paper_id}::section::{idx}",
                    paper_id=paper_id,
                    text=f"{prefix}{text}",
                    chunk_type="section",
                    index=idx,
                ))
                idx += 1

    # 3. Full text fallback (only if no sections)
    section_chunks = [c for c in chunks if c.chunk_type == "section"]
    if not section_chunks and full_text and full_text.strip():
        windows = _sliding_window(full_text.strip())
        for idx, window in enumerate(windows):
            text = f"{title}\n\n{window}" if idx == 0 else window
            chunks.append(PaperChunk(
                chunk_id=f"{paper_id}::fulltext::{idx}",
                paper_id=paper_id,
                text=text,
                chunk_type="fulltext",
                index=idx,
            ))

    # 4. Title-only fallback
    if not chunks:
        chunks.append(PaperChunk(
            chunk_id=f"{paper_id}::title::0",
            paper_id=paper_id,
            text=title,
            chunk_type="title",
            index=0,
        ))

    return chunks
