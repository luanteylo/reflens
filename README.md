# RefLens

AI-powered scientific paper database with semantic search and citation management.

Upload PDFs, extract structured data, build citation networks, and search by meaning.
The killer feature: *"Give me a sentence, and I'll find papers in your library that support it as references."*

## Quick Start

```bash
# Setup
python -m venv ~/.venvs/reflens
source ~/.venvs/reflens/bin/activate
pip install -e ".[dev]"

# Start GROBID (required for PDF extraction)
docker compose up -d grobid

# Ingest a paper
reflens ingest paper.pdf --notes "Interesting approach to X" --status partial

# Ingest a whole folder
reflens ingest-folder ~/papers/

# Browse your library
reflens list
reflens show e1a20675
reflens search "reinforcement learning"

# AI-powered features
reflens summarize e1a20675
reflens tag e1a20675
reflens summarize-all
reflens tag-all

# Embeddings and semantic search
reflens embed-all
reflens find-refs "temporal I/O behavior improves with burst buffers"
reflens find-refs "temporal I/O behavior" --explain  # includes AI explanation (API cost)
```

## What It Does

- **PDF Extraction** -- Pulls title, authors, abstract, full text, references, and sections from scientific PDFs using GROBID + PyMuPDF
- **AI Summarization** -- Generates structured summaries: overview, key contributions, methodology, findings, and limitations
- **Smart Tagging** -- Curated topic tags (broad areas + specific concepts) for easy browsing
- **Citation Network** -- Cross-references citations between papers in your database
- **Semantic Search** -- Find papers by meaning, not just keywords (via ChromaDB + sentence-transformers)
- **Reference Finder** -- Input a sentence, get back papers from your library that support it
- **MCP Server** -- Expose your library as tools for AI clients (e.g. query your papers from Claude Code)

## Architecture

```
   REST API (FastAPI)     MCP Server
         \                  /
          \                /
           Core Engine
          / |    |     \
    PDF    AI    RAG    DB
    Ext.  Pipe  Eng.   Layer
     |      |     |      |
  GROBID  Claude ChromaDB SQLite
  PyMuPDF OpenAI
```

Two interfaces, one shared engine. No logic duplication.

## Configuration

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

Key settings:

| Variable | Description |
|----------|-------------|
| `REFLENS_ANTHROPIC_API_KEY` | Your Anthropic API key |
| `REFLENS_OPENAI_API_KEY` | Your OpenAI API key (optional) |
| `REFLENS_AI_PROVIDER` | `claude` or `openai` |
| `REFLENS_GROBID_URL` | GROBID server URL (default: `http://localhost:8070`) |
| `REFLENS_DATABASE_URL` | SQLite or PostgreSQL connection string |

## Development

```bash
# Run tests
pytest tests/

# Lint and format
ruff check src/ tests/
ruff format src/ tests/

# Run API server
uvicorn reflens.api.app:create_app --factory

# Web frontend
cd web && npm install && npm run dev

# Run everything with Docker
docker compose up
```

## Tech Stack

Python 3.11+ / FastAPI / SQLAlchemy / ChromaDB / PyMuPDF / GROBID / Anthropic SDK / OpenAI SDK

## License

Proprietary
