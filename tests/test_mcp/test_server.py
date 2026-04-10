"""Tests for the MCP server tools."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from reflens.mcp.server import (
    mcp,
    reflens_find_references,
    reflens_get_paper,
    reflens_list_collections,
    reflens_list_papers,
    reflens_list_tags,
    reflens_search,
)


def _make_paper(**overrides):
    paper = MagicMock()
    paper.id = overrides.get("id", "paper-1")
    paper.title = overrides.get("title", "Test Paper")
    paper.abstract = overrides.get("abstract", "An abstract")
    paper.year = overrides.get("year", 2024)
    paper.doi = overrides.get("doi", "10.1234/test")
    paper.ai_summary = overrides.get("ai_summary", None)
    paper.full_text = overrides.get("full_text", "Full text here")

    author = MagicMock()
    author.name = "Alice Smith"
    paper.authors = overrides.get("authors", [author])
    paper.tags = overrides.get("tags", [])
    return paper


def _make_tag(**overrides):
    tag = MagicMock()
    tag.id = overrides.get("id", "tag-1")
    tag.name = overrides.get("name", "machine-learning")
    return tag


def _make_ctx(engine, user_id: str = "user-123"):
    """Build a mock Context whose lifespan_context holds engine and user_id."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {"engine": engine, "user_id": user_id}
    return ctx


@pytest.fixture
def engine():
    e = MagicMock()
    e.find_references = AsyncMock(return_value={
        "results": [
            {"paper": _make_paper(), "score": 0.92, "explanation": None, "stance": None},
        ],
        "warning": None,
    })
    e.search_papers.return_value = [{"paper": _make_paper(), "score": 0.85}]
    e.list_tags.return_value = [_make_tag()]
    e.get_paper.return_value = _make_paper()
    e.list_papers.return_value = [_make_paper()]
    e.count_papers.return_value = 1
    e.list_collections.return_value = []
    return e


# -- Tool registration --

async def test_server_registers_all_tools():
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    # Spot-check that core tools across every category are registered.
    expected_subset = {
        "reflens_find_references",
        "reflens_search",
        "reflens_explain_relevance",
        "reflens_list_papers",
        "reflens_get_paper",
        "reflens_upload_paper",
        "reflens_delete_paper",
        "reflens_summarize_paper",
        "reflens_list_paper_summaries",
        "reflens_tag_paper",
        "reflens_get_paper_bibtex",
        "reflens_get_paper_cite",
        "reflens_get_paper_references",
        "reflens_update_paper_notes",
        "reflens_list_tags",
        "reflens_list_papers_by_tag",
        "reflens_list_collections",
        "reflens_get_collection",
        "reflens_create_collection",
        "reflens_delete_collection",
        "reflens_add_papers_to_collection",
        "reflens_remove_papers_from_collection",
        "reflens_list_authors",
        "reflens_list_papers_by_author",
        "reflens_list_saved_searches",
        "reflens_save_search",
        "reflens_delete_saved_search",
        "reflens_library_stats",
    }
    assert expected_subset <= names


# -- reflens_find_references --

async def test_find_references(engine):
    ctx = _make_ctx(engine)
    result = await reflens_find_references(ctx, text="Transformers improve NLP tasks")
    engine.find_references.assert_awaited_once_with(
        "Transformers improve NLP tasks",
        user_id="user-123",
        limit=5,
        explain=True,
        tag_ids=None,
        collection_ids=None,
    )
    assert "Test Paper" in result
    assert "92%" in result


async def test_find_references_no_results(engine):
    engine.find_references = AsyncMock(return_value={"results": [], "warning": None})
    ctx = _make_ctx(engine)
    result = await reflens_find_references(
        ctx, text="claim", limit=3, tag_ids=["tag-1"], explain=False,
    )
    engine.find_references.assert_awaited_once_with(
        "claim",
        user_id="user-123",
        limit=3,
        explain=False,
        tag_ids=["tag-1"],
        collection_ids=None,
    )
    assert "No matching references" in result


# -- reflens_search --

async def test_search(engine):
    ctx = _make_ctx(engine)
    result = await reflens_search(ctx, query="attention mechanism")
    engine.search_papers.assert_called_once_with(
        "attention mechanism", user_id="user-123", limit=10, collection_ids=None
    )
    assert "Test Paper" in result
    assert "85%" in result


async def test_search_no_results(engine):
    engine.search_papers.return_value = []
    ctx = _make_ctx(engine)
    result = await reflens_search(ctx, query="nonexistent")
    assert "No papers found" in result


# -- reflens_list_tags --

async def test_list_tags(engine):
    ctx = _make_ctx(engine)
    result = await reflens_list_tags(ctx)
    engine.list_tags.assert_called_once()
    assert "machine-learning" in result
    assert "tag-1" in result


async def test_list_tags_empty(engine):
    engine.list_tags.return_value = []
    ctx = _make_ctx(engine)
    result = await reflens_list_tags(ctx)
    assert "No tags found" in result


# -- reflens_get_paper --

async def test_get_paper(engine):
    ctx = _make_ctx(engine)
    result = await reflens_get_paper(ctx, paper_id="paper-1")
    engine.get_paper.assert_called_once_with("paper-1", user_id="user-123")
    assert "Test Paper" in result
    assert "Alice Smith" in result
    assert "2024" in result
    assert "10.1234/test" in result


async def test_get_paper_not_found(engine):
    engine.get_paper.return_value = None
    ctx = _make_ctx(engine)
    result = await reflens_get_paper(ctx, paper_id="missing")
    assert "not found" in result


async def test_get_paper_with_summary(engine):
    paper = _make_paper(ai_summary="A great paper about transformers")
    engine.get_paper.return_value = paper
    ctx = _make_ctx(engine)
    result = await reflens_get_paper(ctx, paper_id="paper-1")
    assert "A great paper about transformers" in result


async def test_get_paper_with_tags(engine):
    pt = MagicMock()
    pt.tag.name = "deep-learning"
    paper = _make_paper(tags=[pt])
    engine.get_paper.return_value = paper
    ctx = _make_ctx(engine)
    result = await reflens_get_paper(ctx, paper_id="paper-1")
    assert "deep-learning" in result


# -- reflens_list_papers --

async def test_list_papers(engine):
    ctx = _make_ctx(engine)
    result = await reflens_list_papers(ctx, limit=10)
    engine.list_papers.assert_called_once_with(user_id="user-123", limit=10, offset=0)
    assert "Test Paper" in result


async def test_list_papers_empty(engine):
    engine.list_papers.return_value = []
    engine.count_papers.return_value = 0
    ctx = _make_ctx(engine)
    result = await reflens_list_papers(ctx)
    assert "No papers found" in result


# -- reflens_list_collections --

async def test_list_collections_empty(engine):
    ctx = _make_ctx(engine)
    result = await reflens_list_collections(ctx)
    assert "No collections found" in result
