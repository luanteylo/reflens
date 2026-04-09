"""MCP server exposing RefLens tools for AI clients."""

import os
from contextlib import asynccontextmanager

from mcp.server.fastmcp import Context, FastMCP

from reflens.config import get_settings
from reflens.core.engine import RefLensEngine


@asynccontextmanager
async def lifespan(server: FastMCP):
    engine = RefLensEngine(get_settings())
    user_id = os.environ.get("REFLENS_MCP_USER_ID", "local")
    yield {"engine": engine, "user_id": user_id}


mcp = FastMCP(
    "reflens",
    instructions=(
        "RefLens: a scientific paper library. "
        "Use reflens_find_references to find papers that support a claim or sentence."
    ),
    lifespan=lifespan,
)


def _get_engine(ctx: Context) -> RefLensEngine:
    return ctx.request_context.lifespan_context["engine"]


def _get_user_id(ctx: Context) -> str:
    return ctx.request_context.lifespan_context["user_id"]


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


@mcp.tool()
async def reflens_find_references(
    ctx: Context,
    text: str,
    limit: int = 5,
    tag_ids: list[str] | None = None,
) -> str:
    """Find papers from the library that could serve as references for a claim or sentence.

    Args:
        text: The claim or sentence to find references for.
        limit: Maximum number of results (default 5).
        tag_ids: Optional list of tag IDs to filter by.
    """
    engine = _get_engine(ctx)
    user_id = _get_user_id(ctx)
    data = await engine.find_references(text, user_id=user_id, limit=limit, tag_ids=tag_ids)
    results = data.get("results", []) if isinstance(data, dict) else data
    if not results:
        return "No matching references found."
    lines = [f"Found {len(results)} reference(s):\n"]
    for r in results:
        lines.append(_format_paper_short(r["paper"], r["score"]))
        if r.get("explanation"):
            lines.append(f"  Relevance: {r['explanation']}")
        if r.get("stance"):
            lines.append(f"  Stance: {r['stance']}")
    return "\n".join(lines)


@mcp.tool()
async def reflens_search(
    ctx: Context,
    query: str,
    limit: int = 10,
) -> str:
    """Search the paper library by semantic similarity or keyword.

    Args:
        query: Search query (natural language or keywords).
        limit: Maximum number of results (default 10).
    """
    engine = _get_engine(ctx)
    user_id = _get_user_id(ctx)
    results = engine.search_papers(query, user_id=user_id, limit=limit)
    if not results:
        return "No papers found."
    lines = [f"Found {len(results)} paper(s):\n"]
    for r in results:
        lines.append(_format_paper_short(r["paper"], r["score"]))
    return "\n".join(lines)


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
async def reflens_get_paper(ctx: Context, paper_id: str) -> str:
    """Get full details of a paper by its ID. Use for citation formatting.

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


def main():
    mcp.run(transport="stdio")
