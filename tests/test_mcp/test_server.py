"""Tests for the MCP server tools."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from reflens.mcp.server import (
    mcp,
    reflens_find_references,
    reflens_get_paper,
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


def _make_ctx(engine):
    """Build a mock Context whose lifespan_context holds the engine."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {"engine": engine}
    return ctx


@pytest.fixture
def engine():
    e = MagicMock()
    e.find_references = AsyncMock(return_value=[
        {"paper": _make_paper(), "score": 0.92, "explanation": None, "stance": None},
    ])
    e.search_papers.return_value = [{"paper": _make_paper(), "score": 0.85}]
    e.list_tags.return_value = [_make_tag()]
    e.get_paper.return_value = _make_paper()
    return e


# -- Tool registration --

async def test_server_registers_all_tools():
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert names == {
        "reflens_find_references",
        "reflens_search",
        "reflens_list_tags",
        "reflens_get_paper",
    }


# -- reflens_find_references --

async def test_find_references(engine):
    ctx = _make_ctx(engine)
    result = await reflens_find_references(ctx, text="Transformers improve NLP tasks")
    engine.find_references.assert_awaited_once_with(
        "Transformers improve NLP tasks", limit=5, tag_ids=None,
    )
    assert "Test Paper" in result
    assert "92%" in result


async def test_find_references_with_options(engine):
    engine.find_references = AsyncMock(return_value=[])
    ctx = _make_ctx(engine)
    result = await reflens_find_references(
        ctx, text="claim", limit=3, tag_ids=["tag-1"],
    )
    engine.find_references.assert_awaited_once_with("claim", limit=3, tag_ids=["tag-1"])
    assert "No matching references" in result


# -- reflens_search --

async def test_search(engine):
    ctx = _make_ctx(engine)
    result = await reflens_search(ctx, query="attention mechanism")
    engine.search_papers.assert_called_once_with("attention mechanism", limit=10)
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
    engine.get_paper.assert_called_once_with("paper-1")
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
