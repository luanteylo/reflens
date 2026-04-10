"""MCP server exposing RefLens tools for AI clients."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from mcp.server.fastmcp import Context, FastMCP

from reflens.config import get_settings
from reflens.core.citations import get_bibtex, get_citation_formats
from reflens.core.engine import DuplicatePaperError, RefLensEngine


@asynccontextmanager
async def lifespan(server: FastMCP):
    engine = RefLensEngine(get_settings())
    user_id = os.environ.get("REFLENS_MCP_USER_ID", "local")
    yield {"engine": engine, "user_id": user_id}


mcp = FastMCP(
    "reflens",
    instructions=(
        "RefLens: a scientific paper library. Find references for a claim, search papers, "
        "summarize, tag, manage collections, and export citations in BibTeX/APA."
    ),
    lifespan=lifespan,
)


def _get_engine(ctx: Context) -> RefLensEngine:
    return ctx.request_context.lifespan_context["engine"]


def _get_user_id(ctx: Context) -> str:
    return ctx.request_context.lifespan_context["user_id"]


# -- Formatting helpers --

def _format_paper_short(paper, score: float | None = None) -> str:
    authors = ", ".join(a.name for a in paper.authors) if paper.authors else "Unknown"
    parts = [f"- {paper.title}"]
    parts.append(f"  Authors: {authors}")
    if paper.year:
        parts.append(f"  Year: {paper.year}")
    if paper.doi:
        parts.append(f"  DOI: {paper.doi}")
    if score is not None:
        parts.append(f"  Relevance: {score:.0%}")
    parts.append(f"  ID: {paper.id}")
    return "\n".join(parts)


def _format_paper_list(papers, title: str) -> str:
    if not papers:
        return "No papers found."
    lines = [f"{title} ({len(papers)}):\n"]
    for p in papers:
        lines.append(_format_paper_short(p))
    return "\n".join(lines)


def _format_summary_dict(s: dict) -> str:
    lines = [f"[{s.get('model_name', 'unknown')}]"]
    if s.get("user_prompt"):
        lines.append(f"  Prompt: {s['user_prompt']}")
    if s.get("overview"):
        lines.append(f"  Overview: {s['overview']}")
    if s.get("key_contributions"):
        lines.append("  Key contributions:")
        for kc in s["key_contributions"]:
            lines.append(f"    - {kc}")
    if s.get("methodology"):
        lines.append(f"  Methodology: {s['methodology']}")
    if s.get("findings"):
        lines.append(f"  Findings: {s['findings']}")
    if s.get("limitations"):
        lines.append(f"  Limitations: {s['limitations']}")
    return "\n".join(lines)


# -- Search & Discovery --

@mcp.tool()
async def reflens_find_references(
    ctx: Context,
    text: str,
    limit: int = 5,
    explain: bool = True,
    tag_ids: list[str] | None = None,
    collection_ids: list[str] | None = None,
) -> str:
    """Find papers from the library that could serve as references for a claim or sentence.

    Uses hybrid search + AI re-ranking + stance analysis (supports/contradicts/neutral)
    when explain=True.

    Args:
        text: The claim or sentence to find references for.
        limit: Maximum number of results (default 5).
        explain: Whether to run AI re-ranking and stance analysis (default True).
        tag_ids: Optional list of tag IDs to filter by.
        collection_ids: Optional list of collection IDs to restrict the search to.
    """
    engine = _get_engine(ctx)
    user_id = _get_user_id(ctx)
    data = await engine.find_references(
        text,
        user_id=user_id,
        limit=limit,
        explain=explain,
        tag_ids=tag_ids,
        collection_ids=collection_ids,
    )
    results = data.get("results", []) if isinstance(data, dict) else data
    if not results:
        return "No matching references found."
    lines = [f"Found {len(results)} reference(s):\n"]
    for r in results:
        lines.append(_format_paper_short(r["paper"], r["score"]))
        if r.get("stance"):
            lines.append(f"  Stance: {r['stance']}")
        if r.get("explanation"):
            lines.append(f"  Explanation: {r['explanation']}")
    if isinstance(data, dict) and data.get("warning"):
        lines.append(f"\nWarning: {data['warning']}")
    return "\n".join(lines)


@mcp.tool()
async def reflens_search(ctx: Context, query: str, limit: int = 10,
                         collection_ids: list[str] | None = None) -> str:
    """Search the paper library by semantic similarity + keyword.

    Args:
        query: Search query (natural language or keywords).
        limit: Maximum number of results (default 10).
        collection_ids: Optional list of collection IDs to restrict the search to.
    """
    engine = _get_engine(ctx)
    user_id = _get_user_id(ctx)
    results = engine.search_papers(query, user_id=user_id, limit=limit,
                                   collection_ids=collection_ids)
    if not results:
        return "No papers found."
    lines = [f"Found {len(results)} paper(s):\n"]
    for r in results:
        lines.append(_format_paper_short(r["paper"], r["score"]))
    return "\n".join(lines)


@mcp.tool()
async def reflens_explain_relevance(ctx: Context, query: str, paper_id: str) -> str:
    """Assess whether a specific paper supports, contradicts, or is neutral to a claim.

    Args:
        query: The claim or question to assess.
        paper_id: The UUID of the paper.
    """
    engine = _get_engine(ctx)
    user_id = _get_user_id(ctx)
    try:
        result = await engine.explain_single(query, paper_id, user_id=user_id)
    except ValueError as e:
        return f"Error: {e}"
    stance = result.get("stance", "neutral")
    explanation = result.get("explanation", "")
    return f"Stance: {stance}\nExplanation: {explanation}"


# -- Papers --

@mcp.tool()
async def reflens_list_papers(ctx: Context, limit: int = 50, offset: int = 0,
                              tag_ids: list[str] | None = None) -> str:
    """List papers in the library with pagination.

    Args:
        limit: Maximum number of results (default 50).
        offset: Pagination offset (default 0).
        tag_ids: Optional list of tag IDs to filter by.
    """
    engine = _get_engine(ctx)
    user_id = _get_user_id(ctx)
    if tag_ids:
        papers = engine.list_papers_by_tags(tag_ids, user_id=user_id, limit=limit, offset=offset)
        total = engine.count_papers_by_tags(tag_ids, user_id=user_id)
    else:
        papers = engine.list_papers(user_id=user_id, limit=limit, offset=offset)
        total = engine.count_papers(user_id=user_id)
    if not papers:
        return "No papers found."
    header = f"Showing {len(papers)} of {total} paper(s) (offset {offset}):\n"
    return header + "\n".join(_format_paper_short(p) for p in papers)


@mcp.tool()
async def reflens_get_paper(ctx: Context, paper_id: str) -> str:
    """Get full details of a paper by its ID.

    Args:
        paper_id: The UUID of the paper.
    """
    engine = _get_engine(ctx)
    user_id = _get_user_id(ctx)
    paper = engine.get_paper(paper_id, user_id=user_id)
    if paper is None:
        return f"Paper not found: {paper_id}"
    authors = ", ".join(a.name for a in paper.authors) if paper.authors else "Unknown"
    lines = [
        f"Title: {paper.title}",
        f"Authors: {authors}",
        f"Year: {paper.year or 'Unknown'}",
        f"DOI: {paper.doi or 'N/A'}",
    ]
    if paper.abstract:
        lines.append(f"Abstract: {paper.abstract}")
    if paper.ai_summary:
        lines.append(f"Summary: {paper.ai_summary}")
    if paper.tags:
        tag_names = ", ".join(pt.tag.name for pt in paper.tags)
        lines.append(f"Tags: {tag_names}")
    lines.append(f"ID: {paper.id}")
    return "\n".join(lines)


@mcp.tool()
async def reflens_upload_paper(ctx: Context, pdf_path: str, force: bool = False) -> str:
    """Ingest a PDF file into the library: extracts text, metadata, references.

    If a paper with the same DOI or title already exists, this tool aborts and
    returns the duplicate info so the caller can decide. Pass force=True to
    ingest anyway.

    Args:
        pdf_path: Absolute path to a local PDF file.
        force: Ingest even if a duplicate is detected (default False).
    """
    engine = _get_engine(ctx)
    user_id = _get_user_id(ctx)
    path = Path(pdf_path)
    if not path.exists():
        return f"Error: file not found: {pdf_path}"
    try:
        result = engine.ingest_paper(path, user_id=user_id, force=force)
    except DuplicatePaperError as e:
        return (
            "Duplicate paper detected. Existing entry:\n"
            f"  Title: {e.existing.get('title')}\n"
            f"  Year: {e.existing.get('year') or 'Unknown'}\n"
            f"  DOI: {e.existing.get('doi') or 'N/A'}\n"
            f"  ID: {e.existing.get('id')}\n\n"
            "Call again with force=True to ingest anyway."
        )
    except Exception as e:
        return f"Error ingesting paper: {e}"
    return (
        f"Ingested: {result['title']}\n"
        f"ID: {result['id']}\n"
        f"Authors: {', '.join(result.get('authors') or []) or 'Unknown'}\n"
        f"Year: {result.get('year') or 'Unknown'}\n"
        f"DOI: {result.get('doi') or 'N/A'}\n"
        f"Citations extracted: {result.get('citations_count', 0)}\n"
        f"Indexed: {result.get('indexed', False)}"
    )


@mcp.tool()
async def reflens_delete_paper(ctx: Context, paper_id: str) -> str:
    """Delete a paper from the library.

    Args:
        paper_id: The UUID of the paper.
    """
    engine = _get_engine(ctx)
    user_id = _get_user_id(ctx)
    ok = engine.delete_paper(paper_id, user_id=user_id)
    return "Deleted." if ok else f"Paper not found: {paper_id}"


@mcp.tool()
async def reflens_summarize_paper(
    ctx: Context,
    paper_id: str,
    model_id: str | None = None,
    user_prompt: str | None = None,
) -> str:
    """Generate an AI summary for a paper.

    Args:
        paper_id: The UUID of the paper.
        model_id: Optional model ID (e.g. "claude/claude-sonnet-4-6", "openai/gpt-4o-mini").
        user_prompt: Optional extra instructions for the summarizer.
    """
    engine = _get_engine(ctx)
    user_id = _get_user_id(ctx)
    try:
        summary = await engine.summarize_paper(
            paper_id, user_id=user_id, model_id=model_id, user_prompt=user_prompt
        )
    except ValueError as e:
        return f"Error: {e}"
    return _format_summary_dict(summary)


@mcp.tool()
async def reflens_list_paper_summaries(ctx: Context, paper_id: str) -> str:
    """List all AI summaries for a paper (possibly from different models or prompts).

    Args:
        paper_id: The UUID of the paper.
    """
    engine = _get_engine(ctx)
    user_id = _get_user_id(ctx)
    summaries = engine.get_paper_summaries(paper_id, user_id=user_id)
    if not summaries:
        return "No summaries found for this paper."
    lines = [f"Found {len(summaries)} summary(ies):\n"]
    for s in summaries:
        lines.append(_format_summary_dict(s))
        lines.append("")
    return "\n".join(lines).strip()


@mcp.tool()
async def reflens_tag_paper(ctx: Context, paper_id: str, model_id: str | None = None) -> str:
    """Generate AI topic tags for a paper.

    Args:
        paper_id: The UUID of the paper.
        model_id: Optional model ID override.
    """
    engine = _get_engine(ctx)
    user_id = _get_user_id(ctx)
    try:
        tags = await engine.tag_paper(paper_id, user_id=user_id, model_id=model_id)
    except ValueError as e:
        return f"Error: {e}"
    return "Tags: " + ", ".join(tags) if tags else "No tags generated."


@mcp.tool()
async def reflens_get_paper_bibtex(ctx: Context, paper_id: str) -> str:
    """Get the BibTeX entry for a paper (fetched from doi.org when possible).

    Args:
        paper_id: The UUID of the paper.
    """
    engine = _get_engine(ctx)
    user_id = _get_user_id(ctx)
    paper = engine.get_paper(paper_id, user_id=user_id)
    if paper is None:
        return f"Paper not found: {paper_id}"
    return await get_bibtex(paper)


@mcp.tool()
async def reflens_get_paper_cite(ctx: Context, paper_id: str) -> str:
    """Get multiple citation formats (short ref, APA, BibTeX) for a paper.

    Args:
        paper_id: The UUID of the paper.
    """
    engine = _get_engine(ctx)
    user_id = _get_user_id(ctx)
    paper = engine.get_paper(paper_id, user_id=user_id)
    if paper is None:
        return f"Paper not found: {paper_id}"
    fmts = await get_citation_formats(paper)
    return (
        f"Short: {fmts['short']}\n\n"
        f"Full:\n{fmts['full']}\n\n"
        f"BibTeX:\n{fmts['bibtex']}"
    )


@mcp.tool()
async def reflens_get_paper_references(ctx: Context, paper_id: str) -> str:
    """List all references (outgoing citations) extracted from a paper.

    Args:
        paper_id: The UUID of the paper.
    """
    engine = _get_engine(ctx)
    user_id = _get_user_id(ctx)
    try:
        citations = engine.get_citations(paper_id, user_id=user_id)
    except ValueError as e:
        return f"Error: {e}"
    if not citations:
        return "No references extracted."
    lines = [f"Found {len(citations)} reference(s):\n"]
    for c in citations:
        line = f"- {c.cited_title or 'Unknown title'}"
        if c.cited_authors:
            line += f" ({c.cited_authors})"
        if c.cited_year:
            line += f" {c.cited_year}"
        if c.cited_doi:
            line += f" [DOI: {c.cited_doi}]"
        if c.cited_paper_id:
            line += f" [in library: {c.cited_paper_id}]"
        lines.append(line)
    return "\n".join(lines)


@mcp.tool()
async def reflens_update_paper_notes(
    ctx: Context,
    paper_id: str,
    content: str | None = None,
    reading_status: str = "unread",
    relevance_score: int | None = None,
    is_favorite: bool = False,
) -> str:
    """Update user notes for a paper.

    Args:
        paper_id: The UUID of the paper.
        content: Note content text.
        reading_status: One of "unread", "reading", "read".
        relevance_score: Optional 1-5 score.
        is_favorite: Whether to mark as favorite.
    """
    engine = _get_engine(ctx)
    user_id = _get_user_id(ctx)
    try:
        note = engine.update_notes(
            paper_id,
            user_id=user_id,
            content=content,
            reading_status=reading_status,
            relevance_score=relevance_score,
            is_favorite=is_favorite,
        )
    except ValueError as e:
        return f"Error: {e}"
    rs = note.reading_status
    status = rs.value if hasattr(rs, "value") else rs
    return (
        f"Notes updated.\n"
        f"Status: {status}\n"
        f"Favorite: {note.is_favorite}\n"
        f"Score: {note.relevance_score or 'N/A'}"
    )


# -- Tags --

@mcp.tool()
async def reflens_list_tags(ctx: Context) -> str:
    """List all available tags in the library. Useful for filtering searches."""
    engine = _get_engine(ctx)
    tags = engine.list_tags()
    if not tags:
        return "No tags found."
    lines = [f"Found {len(tags)} tag(s):\n"]
    for tag in tags:
        lines.append(f"- {tag.name} (ID: {tag.id})")
    return "\n".join(lines)


@mcp.tool()
async def reflens_list_papers_by_tag(ctx: Context, tag_id: str) -> str:
    """List all papers with a given tag.

    Args:
        tag_id: The UUID of the tag.
    """
    engine = _get_engine(ctx)
    user_id = _get_user_id(ctx)
    papers = engine.list_papers_by_tag(tag_id, user_id=user_id)
    return _format_paper_list(papers, "Papers with tag")


# -- Collections --

def _format_collection(col: dict, indent: int = 0) -> list[str]:
    prefix = "  " * indent
    lines = [f"{prefix}- {col['name']} ({col['paper_count']} papers) [ID: {col['id']}]"]
    for child in col.get("children") or []:
        lines.extend(_format_collection(child, indent + 1))
    return lines


@mcp.tool()
async def reflens_list_collections(ctx: Context) -> str:
    """List all collections (hierarchical folders) in the library."""
    engine = _get_engine(ctx)
    user_id = _get_user_id(ctx)
    cols = engine.list_collections(user_id=user_id)
    if not cols:
        return "No collections found."
    lines = [f"Found {len(cols)} root collection(s):\n"]
    for c in cols:
        lines.extend(_format_collection(c))
    return "\n".join(lines)


@mcp.tool()
async def reflens_get_collection(ctx: Context, collection_id: str) -> str:
    """Get a collection's details and its papers (recursive).

    Args:
        collection_id: The UUID of the collection.
    """
    engine = _get_engine(ctx)
    user_id = _get_user_id(ctx)
    col = engine.get_collection(collection_id, user_id=user_id)
    if col is None:
        return f"Collection not found: {collection_id}"
    lines = [f"Collection: {col['name']}", f"ID: {col['id']}", f"Papers: {col['paper_count']}"]
    if col.get("papers"):
        lines.append("")
        for p in col["papers"]:
            lines.append(_format_paper_short(p))
    return "\n".join(lines)


@mcp.tool()
async def reflens_create_collection(
    ctx: Context, name: str, parent_id: str | None = None
) -> str:
    """Create a new collection (optionally as a child of another).

    Args:
        name: The name of the collection.
        parent_id: Optional parent collection UUID for nesting.
    """
    engine = _get_engine(ctx)
    user_id = _get_user_id(ctx)
    col = engine.create_collection(name, parent_id=parent_id, user_id=user_id)
    return f"Created collection '{col['name']}' (ID: {col['id']})"


@mcp.tool()
async def reflens_rename_collection(
    ctx: Context, collection_id: str, name: str
) -> str:
    """Rename a collection.

    Args:
        collection_id: The UUID of the collection.
        name: The new name.
    """
    engine = _get_engine(ctx)
    user_id = _get_user_id(ctx)
    col = engine.rename_collection(collection_id, name, user_id=user_id)
    if col is None:
        return f"Collection not found: {collection_id}"
    return f"Renamed to '{col['name']}'"


@mcp.tool()
async def reflens_delete_collection(ctx: Context, collection_id: str) -> str:
    """Delete a collection (papers themselves are not deleted).

    Args:
        collection_id: The UUID of the collection.
    """
    engine = _get_engine(ctx)
    user_id = _get_user_id(ctx)
    ok = engine.delete_collection(collection_id, user_id=user_id)
    return "Deleted." if ok else f"Collection not found: {collection_id}"


@mcp.tool()
async def reflens_add_papers_to_collection(
    ctx: Context, collection_id: str, paper_ids: list[str]
) -> str:
    """Add one or more papers to a collection.

    Args:
        collection_id: The UUID of the collection.
        paper_ids: List of paper UUIDs to add.
    """
    engine = _get_engine(ctx)
    user_id = _get_user_id(ctx)
    engine.add_papers_to_collection(collection_id, paper_ids, user_id=user_id)
    return f"Added {len(paper_ids)} paper(s) to collection."


@mcp.tool()
async def reflens_remove_papers_from_collection(
    ctx: Context, collection_id: str, paper_ids: list[str]
) -> str:
    """Remove papers from a collection.

    Args:
        collection_id: The UUID of the collection.
        paper_ids: List of paper UUIDs to remove.
    """
    engine = _get_engine(ctx)
    user_id = _get_user_id(ctx)
    engine.remove_papers_from_collection(collection_id, paper_ids, user_id=user_id)
    return f"Removed {len(paper_ids)} paper(s) from collection."


# -- Authors --

@mcp.tool()
async def reflens_list_authors(ctx: Context, limit: int = 50, offset: int = 0) -> str:
    """List authors in the library with pagination.

    Args:
        limit: Maximum results (default 50).
        offset: Pagination offset (default 0).
    """
    engine = _get_engine(ctx)
    authors = engine.list_authors(limit=limit, offset=offset)
    total = engine.count_authors()
    if not authors:
        return "No authors found."
    lines = [f"Showing {len(authors)} of {total} author(s) (offset {offset}):\n"]
    for a in authors:
        lines.append(f"- {a.name} (ID: {a.id})")
    return "\n".join(lines)


@mcp.tool()
async def reflens_list_papers_by_author(ctx: Context, author_id: str) -> str:
    """List all papers by a specific author.

    Args:
        author_id: The UUID of the author.
    """
    engine = _get_engine(ctx)
    user_id = _get_user_id(ctx)
    papers = engine.list_papers_by_author(author_id, user_id=user_id)
    return _format_paper_list(papers, "Papers by author")


# -- Saved searches --

@mcp.tool()
async def reflens_list_saved_searches(ctx: Context) -> str:
    """List saved searches."""
    engine = _get_engine(ctx)
    user_id = _get_user_id(ctx)
    searches = engine.list_saved_searches(user_id=user_id)
    if not searches:
        return "No saved searches."
    lines = [f"Found {len(searches)} saved search(es):\n"]
    for s in searches:
        col = f" [collection: {s['collection_name']}]" if s.get("collection_name") else ""
        lines.append(f"- {s['text']}{col} (ID: {s['id']})")
    return "\n".join(lines)


@mcp.tool()
async def reflens_save_search(
    ctx: Context, text: str, collection_id: str | None = None
) -> str:
    """Save a search query for later.

    Args:
        text: The search text to save.
        collection_id: Optional collection UUID the search was scoped to.
    """
    engine = _get_engine(ctx)
    user_id = _get_user_id(ctx)
    saved = engine.save_search(text, collection_id=collection_id, user_id=user_id)
    return f"Saved search (ID: {saved['id']})"


@mcp.tool()
async def reflens_delete_saved_search(ctx: Context, search_id: str) -> str:
    """Delete a saved search.

    Args:
        search_id: The UUID of the saved search.
    """
    engine = _get_engine(ctx)
    user_id = _get_user_id(ctx)
    ok = engine.delete_saved_search(search_id, user_id=user_id)
    return "Deleted." if ok else f"Saved search not found: {search_id}"


# -- Library stats --

@mcp.tool()
async def reflens_library_stats(ctx: Context) -> str:
    """Get library statistics: paper count, embedding index status."""
    engine = _get_engine(ctx)
    user_id = _get_user_id(ctx)
    status = engine.embedding_status(user_id=user_id)
    return (
        f"Papers: {status['total_papers']}\n"
        f"Indexed chunks: {status['indexed_chunks']}"
    )


def main():
    mcp.run(transport="stdio")
