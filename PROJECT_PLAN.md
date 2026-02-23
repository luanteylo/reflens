# RefLens -- Scientific Paper Database with AI

---

## 1. Vision

A local-first intelligent paper management system that goes beyond simple storage.
The user uploads scientific papers (PDF), and the system extracts structured
information, builds a knowledge graph of citations and topics, and provides
AI-powered search that understands context, not just keywords.<!--  -->

The killer feature: "Give me a sentence, and I will find papers in your library
that can support it as references, and explain why."

---

## 2. Core Features

### 2.1 Paper Ingestion
- Upload a single PDF or a batch (folder)
- Extract from each paper:
  - Title, authors, affiliations
  - Abstract
  - Full text (section-by-section)
  - References/citations (parsed into structured data)
  - Figures and captions
  - Tables
- User can attach notes during upload
- Optional form: reading status, relevance score, personal tags, comments

### 2.2 AI Summarization Pipeline
- Generate a structured summary for each paper:
  - One-paragraph overview
  - Key contributions (bullet points)
  - Methodology summary
  - Main findings/results
  - Limitations mentioned by authors
- Multi-provider support: Claude (primary), OpenAI (secondary), extensible to others

### 2.3 Tagging and Classification
- AI-generated tags based on paper content
- Tags mapped to specific sections/paragraphs (not just the whole paper)
- Hierarchical tag system (e.g., `machine-learning > reinforcement-learning > Q-learning`)
- User can add/edit/remove tags manually

### 2.4 Citation Network
- Cross-reference citations between papers in the database
- Build a citation graph: who cites whom
- Detect shared references between papers (co-citation analysis)
- Visualize the citation network

### 2.5 Semantic Search
- Context-based search using vector embeddings
- Search by meaning, not just keywords
- Filter by tags, authors, date range, reading status
- Search within specific sections (e.g., "search only in methodology sections")

### 2.6 Reference Finder
- User inputs a sentence or paragraph
- System returns a ranked list of papers from the database that could serve as references
- Each suggestion includes an explanation: "This paper is relevant because..."
- Confidence score for each suggestion

### 2.7 AI-Accessible Database (MCP + RAG)

The database must be a first-class tool that AI can use, not just a backend
the user queries through a UI. Two mechanisms enable this:

**MCP Server (Model Context Protocol)**
- RefLens exposes itself as an MCP server
- Any MCP-compatible AI client (Claude Code, future IDE extensions) can call
  RefLens tools directly during a conversation
- Exposed tools:
  - `reflens_search(query)` -- semantic search across all papers
  - `reflens_find_references(text)` -- find papers that support a statement
  - `reflens_get_paper(id)` -- retrieve full paper details and summary
  - `reflens_list_by_tag(tag)` -- browse papers by topic
  - `reflens_cite(text)` -- return formatted citations for matching papers
  - `reflens_check(text)` -- verify claims against the database
- This means from Claude Code you can naturally say:
  - "Check my RefLens database, does this paragraph have supporting references?"
  - "Based on my RefLens papers, does this claim make sense?"
  - "Find me papers about X from my collection"

**RAG Pipeline (Retrieval Augmented Generation)**
- When the AI receives a query, it:
  1. Embeds the query
  2. Searches ChromaDB for relevant paper chunks
  3. Retrieves full context (summaries, metadata, user notes)
  4. Passes relevant context to the LLM
  5. LLM generates a response grounded in your actual papers
- Every AI response includes source attribution (which papers, which sections)
- The AI never fabricates references -- it only cites what exists in your DB

**Usage Scenarios**
- Writing a paper in VS Code: select a paragraph, ask "find references for this"
- Reviewing a draft: "does my database support this claim?"
- Literature exploration: "what do my papers say about topic X?"
- Browser: select text on a webpage, right-click "find references in RefLens"

### 2.8 User Interaction
- Upload form with optional fields:
  - Have you read this paper? (yes/partially/no)
  - Relevance to your work (1-5)
  - Personal notes (free text)
  - Custom tags
  - Project/collection assignment
- Edit metadata and notes at any time
- Mark papers as favorites, archive, or trash

---

## 3. Architecture

```
+-------------------+  +-------------------+  +-------------------+
|    Web UI         |  | Claude Code /     |  | Browser / VS Code |
|    (Frontend)     |  | AI Clients        |  | Extensions        |
+-------------------+  +-------------------+  +-------------------+
         |                      |                      |
         v                      v                      v
+------------------+   +------------------+
|    REST API      |   |   MCP Server     |
|    (FastAPI)     |   |   (stdio/SSE)    |
+------------------+   +------------------+
         |                      |
         +-----------+----------+
                     |
                     v
        +------------------------+
        |      Core Engine       |
        |  (shared Python lib)   |
        +------------------------+
         |       |        |       |
         v       v        v       v
     +------+ +------+ +------+ +------+
     | PDF  | | AI   | | RAG  | | DB   |
     | Ext. | | Pipe | | Eng. | | Layer|
     +------+ +------+ +------+ +------+
         |       |        |       |
         v       v        v       v
      GROBID  Claude/  ChromaDB  SQLite/
      PyMuPDF OpenAI             PostgreSQL
```

### Layers

1. **MCP Server Layer** -- AI-accessible interface
   - Exposes RefLens as tools that any MCP client can call
   - Claude Code, VS Code extensions, browser extensions connect here
   - Handles tool calls: search, find_references, check, cite
   - Runs via stdio (for Claude Code) or SSE (for remote clients)

2. **REST API Layer** -- Human-facing interface
   - FastAPI for the web UI and programmatic access
   - Shares the same core engine as the MCP server

3. **Core Engine** -- Shared business logic
   - Both the REST API and MCP server call into this layer
   - No duplication: one implementation, two interfaces

4. **PDF Extraction Layer** -- GROBID + PyMuPDF
   - GROBID handles structured extraction (metadata, refs, sections)
   - PyMuPDF handles images/figures and fallback text extraction

5. **AI Pipeline Layer** -- Provider-agnostic
   - Abstract interface for LLM calls
   - Implementations: Claude (Anthropic SDK), OpenAI SDK
   - Tasks: summarization, tagging, reference matching, explanation generation

6. **RAG Engine** -- Retrieval Augmented Generation
   - Embeds queries, retrieves relevant paper chunks from ChromaDB
   - Assembles context for the LLM (paper summaries, sections, user notes)
   - Ensures every AI response is grounded in actual database content
   - Hybrid search: vector similarity + metadata filters

7. **Database Layer** -- Structured storage
   - SQLite for development and single-user (simple, no server)
   - PostgreSQL option for multi-user / production
   - Store: papers, authors, tags, citations, user notes, relationships

---

## 4. Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Language | Python 3.11+ | ML/AI ecosystem, PDF libraries |
| API Framework | FastAPI | Async, auto-docs, type-safe |
| PDF Extraction | GROBID + PyMuPDF | Best combo for scientific papers |
| AI (primary) | Anthropic SDK (Claude) | Strong reasoning, long context |
| AI (secondary) | OpenAI SDK | Wide adoption, good embeddings |
| Embeddings | sentence-transformers or OpenAI | For semantic search |
| Vector DB | ChromaDB | Local-first, easy setup |
| Database | SQLite (dev) / PostgreSQL (prod) | Simple to start, scalable later |
| ORM | SQLAlchemy or SQLModel | Type-safe DB access |
| MCP Server | mcp Python SDK | Expose DB as tools to AI clients |
| Frontend | Next.js + Tailwind + TanStack Query | React App Router, drag-and-drop upload |
| Testing | pytest + pytest-cov | Standard Python testing |

---

## 5. Development Environment

### Python Virtual Environment
- All virtual environments live in `~/.venvs/`
- RefLens venv: `~/.venvs/reflens/`
- Create: `python -m venv ~/.venvs/reflens`
- Activate: `source ~/.venvs/reflens/bin/activate`

### Testing
- **Framework**: pytest
- **Coverage**: pytest-cov with minimum threshold
- Tests are mandatory -- every module and feature must have tests
- Test structure mirrors `src/`: `tests/test_<module>.py`
- Run all tests: `pytest tests/`
- Run with coverage: `pytest --cov=reflens tests/`
- Types of tests:
  - **Unit tests**: individual functions and classes (extraction, DB operations, etc.)
  - **Integration tests**: pipeline end-to-end (PDF in -> data in DB)
  - **API tests**: endpoint testing with FastAPI TestClient
- Tests must pass before any merge or release
- Use fixtures for common test data (sample PDFs, mock AI responses)

---

## 6. Data Model

### Papers
```
Paper
  - id: UUID
  - title: str
  - abstract: str
  - full_text: str (raw extracted)
  - sections: JSON (structured by section name)
  - doi: str (optional)
  - year: int
  - source_file: str (path to original PDF)
  - ai_summary: str
  - ai_key_contributions: JSON (list of strings)
  - created_at: datetime
  - updated_at: datetime
```

### Authors
```
Author
  - id: UUID
  - name: str
  - affiliations: JSON
  - papers: [Paper] (many-to-many)
```

### Citations
```
Citation
  - id: UUID
  - citing_paper_id: FK -> Paper
  - cited_paper_id: FK -> Paper (nullable, only if paper is in DB)
  - cited_title: str
  - cited_authors: str
  - cited_year: int
  - cited_doi: str (optional)
  - raw_reference: str (original reference string)
```

### Tags
```
Tag
  - id: UUID
  - name: str
  - parent_id: FK -> Tag (for hierarchy)

PaperTag
  - paper_id: FK -> Paper
  - tag_id: FK -> Tag
  - section: str (which section the tag applies to)
  - confidence: float (AI confidence)
  - source: str ("ai" or "user")
```

### User Notes
```
UserNote
  - id: UUID
  - paper_id: FK -> Paper
  - content: str
  - reading_status: enum (unread, partial, read)
  - relevance_score: int (1-5)
  - is_favorite: bool
  - created_at: datetime
```

### Embeddings (in ChromaDB)
```
Embedding
  - id: str (paper_id + section_index)
  - vector: float[]
  - metadata: {paper_id, section_name, tags}
  - document: str (the text chunk)
```

---

## 6. AI Pipeline Design

### Provider Abstraction
```
AIProvider (interface)
  - summarize(text) -> Summary
  - generate_tags(text) -> list[Tag]
  - find_references(query, candidates) -> list[RankedReference]
  - explain_relevance(query, paper) -> str
  - embed(text) -> list[float]  (optional, can use dedicated model)
```

### Processing Pipeline (per paper)

```
PDF Upload
  |
  v
[1] Extract (GROBID + PyMuPDF)
  |  -> structured text, metadata, figures
  v
[2] Parse References
  |  -> list of cited works
  |  -> match against existing DB entries
  v
[3] Generate Embeddings
  |  -> chunk text into sections/paragraphs
  |  -> embed each chunk
  |  -> store in ChromaDB
  v
[4] AI Summarize
  |  -> structured summary
  |  -> key contributions
  v
[5] AI Tag
  |  -> generate tags per section
  |  -> map to existing tag hierarchy
  v
[6] Link Discovery
  |  -> find related papers in DB by embedding similarity
  |  -> find shared citations
  |  -> suggest connections
  v
[7] Store Everything
     -> SQLite/PostgreSQL + ChromaDB
```

---

## 7. API Endpoints (Draft)

```
POST   /papers/upload          Upload PDF(s)
GET    /papers                 List papers (with filters)
GET    /papers/{id}            Get paper details
PATCH  /papers/{id}            Update paper metadata/notes
DELETE /papers/{id}            Remove paper

GET    /papers/{id}/summary    Get AI summary
GET    /papers/{id}/citations  Get citation list
GET    /papers/{id}/tags       Get tags
GET    /papers/{id}/related    Get related papers

POST   /search                 Semantic search
POST   /search/references      "Find references for this sentence"

GET    /tags                   List all tags
GET    /tags/{id}/papers       Papers with this tag

GET    /authors                List authors
GET    /authors/{id}/papers    Papers by author

GET    /graph/citations        Citation network data
GET    /graph/topics           Topic cluster data
```

---

## 8. Development Phases

### Phase 1: Foundation
- Project setup (Python package, dependencies, config)
- PDF extraction pipeline (GROBID + PyMuPDF)
- Database models and migrations (SQLite + SQLAlchemy)
- Basic CLI to ingest a paper and see extracted data

### Phase 2: AI Integration
- AI provider abstraction layer
- Claude integration for summarization
- OpenAI integration as alternative
- Tag generation pipeline
- Embedding generation and ChromaDB storage

### Phase 3: Search and Links
- Semantic search endpoint (embedding + ChromaDB lookup, fully local, no API cost)
- Reference finder ("cite this sentence")
- Citation cross-referencing within DB
- Related paper discovery
- RAG pipeline: query -> retrieve -> augment -> generate
- **Cost control**: LLM-powered features (explain_relevance, check_claim) must be opt-in, never triggered automatically by search. The default search path should be: embed query locally -> ChromaDB vector lookup -> return ranked results. LLM explanation only when the user explicitly asks for it.

### Phase 4: MCP Server
- MCP server exposing core tools (search, find_references, check, cite)
- stdio transport for Claude Code integration
- Test end-to-end: upload a paper, then query it from Claude Code
- SSE transport for remote/browser clients
- MCP tools for AI-delegated processing (zero API cost with Max plan):
  - `reflens_get_paper_text` -- expose full paper text so Claude can summarize/tag it
  - `reflens_save_summary` -- save a summary generated by the client-side LLM
  - `reflens_save_tags` -- save tags generated by the client-side LLM
  - This lets users run summarization/tagging through Claude Desktop (covered by Max plan) instead of paying for API calls

### Phase 5: Web Client (DONE)
- FastAPI REST API layer on top of core engine
  - Paper CRUD, upload, summarize, tag, citations, notes endpoints
  - Search, tags, and authors endpoints
  - Health check, CORS, Pydantic schemas
  - 23 API tests with mocked engine
- Next.js + Tailwind frontend
  - Dashboard with paper count, recent papers, quick actions
  - Papers list with pagination, paper detail with tabbed view
  - PDF upload with drag-and-drop (multi-file support)
  - Debounced search, tag browser, author browser
  - TanStack Query for data fetching and cache management

### Phase 6: Polish and Extend
- Citation graph visualization
- Batch import improvements
- Export features (BibTeX, citation lists)
- Reading list / collection management
- Token optimization: configurable tag context level (abstract-only vs abstract+intro+conclusion vs all sections) to let users trade cost for accuracy

### Phase 7: Integrations (Future)
- Browser extension: select text on any page, right-click "Find references in RefLens"
- VS Code extension: select text in editor, ask for references from your DB
- Both connect via MCP or REST API running locally

---

## 9. Business Model

### Strategy: Local-First, SaaS-Ready

Build the local product first to validate the core value. Architect everything
so the SaaS transition is a deployment change, not a rewrite.

### Phase A: Local Product (validate + early revenue)
- Docker-based install (one command to run)
- User provides their own API keys (Claude, OpenAI)
- Annual license: $49-99/year
- Target: researchers, PhD students, academics
- Landing page with early access waitlist from day one

### Phase B: SaaS (scale)
- Hosted version, nothing to install
- Monthly subscription: $9-19/month, 30-day free trial
- Tiered pricing:
  - **Free tier**: limited papers (e.g., 20), basic search, BYOK (bring your own keys)
  - **Pro tier**: unlimited papers, AI credits included, priority processing
  - **Team tier**: shared database, collaboration features
- Stripe for all payment processing (PCI compliance handled by Stripe)
- Valid credit card required for trial (Stripe handles this natively)

### Phase C: Integrations (expansion)
- Browser extension and VS Code extension
- Free extensions that drive users to the paid service
- API access tier for power users and integrations

### SaaS-Ready Architecture Decisions (from day one)
- `user_id` field on all database models (even in local mode, use a default user)
- Config-driven: API keys, DB connection, storage paths via environment variables
- Docker Compose for local, Kubernetes-ready for cloud
- File storage abstraction: local disk now, S3-compatible later
- PostgreSQL as the production database (SQLite only for dev/testing)
- All secrets via environment variables, never in code or config files
- HTTPS everywhere, API key encryption at rest

### Payment and Security
- **Stripe** handles: credit cards, subscriptions, trials, invoices, tax
- We never store or touch card numbers
- Auth: OAuth2 (Google, GitHub, ORCID) + email/password option
- API keys stored encrypted (Fernet or similar), decrypted only at runtime
- Rate limiting on all endpoints
- Audit logging for data access

---

## 10. Future Ideas
- Local LLM provider via Ollama (zero API cost for summarization, tagging, and search)
- OCR fallback for scanned papers (tesseract)
- arXiv / Semantic Scholar API integration (auto-fetch metadata)
- Collaborative mode (shared database, multiple users)
- Paper recommendation ("based on what you read, you might like...")
- Auto-download cited papers that are open access
- Integration with reference managers (Zotero, Mendeley)
- Chat with your paper collection ("What do my papers say about X?")
