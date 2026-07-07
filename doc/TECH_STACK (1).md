# Tech Stack & Rationale

Each choice below favors things that are (a) explicitly asked for or recommended in the
assignment, (b) fast to stand up correctly in 48 hours, and (c) demonstrate real engineering
judgement rather than novelty for its own sake.

## Frontend

| Choice | Why |
|---|---|
| **Next.js 14 (App Router) + TypeScript** | Assignment explicitly allows React or Next.js; Next.js gives file-based routing for the three-screen flow (upload → interview → summary) with zero extra routing setup, plus built-in API proxying if needed. TypeScript catches shape mismatches between frontend and the FastAPI schemas early. |
| **Tailwind CSS** | Fast to build a clean, consistent UI without a component library dependency; keeps the "smooth user interaction flow" requirement achievable without design debt. |
| **Zustand** (over Redux/Context) | Interview state (current question, answers-so-far, progress) is small and local to one flow — Zustand avoids Redux boilerplate while still giving predictable state outside component tree, useful for handling refresh/resume behavior. |

## Backend

| Choice | Why |
|---|---|
| **Python 3.11 + FastAPI** | Explicitly recommended in the assignment. FastAPI gives async I/O (important since LLM/embedding calls are I/O-bound), automatic OpenAPI docs (useful for the demo video and grading), and native Pydantic validation, which directly satisfies the "robust error handling and validation" requirement. |
| **Pydantic v2** | Single source of truth for request/response schemas; also reused for settings management (`pydantic-settings`) so all config is environment-variable driven, per the assignment's explicit requirement. |
| **SQLAlchemy 2.0 + Alembic** | Typed ORM with explicit migrations — demonstrates schema evolution discipline rather than `Base.metadata.create_all()` hand-waving. |

## Data Layer

| Choice | Why |
|---|---|
| **PostgreSQL** | Relational integrity for sessions/questions/answers (clear foreign-key relationships, per assignment's "structured records" requirement); mature, free, and — if the vector-store approach needs to be simplified for grading environments — supports the `pgvector` extension as a drop-in fallback so there's no second database to run. |
| **ChromaDB** (primary vector store) | Embedded/local mode requires no separate server, ships with a simple Python API, and supports metadata filtering (used to scope retrieval to `role` and `document_id`). This keeps setup to `pip install` rather than standing up a managed vector DB for an intern assignment. |
| **`pgvector`** (documented fallback) | For environments that prefer a single database technology, the `VectorStore` interface (see below) has a Postgres-backed implementation as an alternative — a config flag, not a rewrite. |

## AI / ML Layer

| Choice | Why |
|---|---|
| **`sentence-transformers/all-MiniLM-L6-v2`** for embeddings | Runs locally/offline, no per-call API cost or latency, small (~80MB), good semantic quality for retrieval over textbook-style prose. Keeps the RAG pipeline reproducible in a grader's environment without requiring an embeddings API key. |
| **LangChain `RecursiveCharacterTextSplitter`** for chunking | Splits on paragraph → sentence → word boundaries in order, which preserves semantic context far better than naive fixed-length slicing — directly addresses the assignment's "context preservation" expectation. Chunk size 800 chars / 120 overlap balances retrieval granularity against context loss at chunk boundaries. |
| **OpenAI `gpt-4o-mini`** for question generation (pluggable) | Strong instruction-following at low cost/latency for a demo-scale app; abstracted behind an `LLMProvider` interface (`generate(prompt) -> str`) so grading environments without an OpenAI key can swap in a local model (e.g., Ollama + Llama 3) by changing one environment variable and implementing one small adapter class — no business logic changes. |
| **Resume parsing: `pdfplumber` + `spaCy` (`en_core_web_sm`) + curated regex/keyword lists** | `pdfplumber` reliably extracts text (and layout) from PDF resumes; spaCy's NER plus a curated skills/technology keyword list (e.g., a maintained list of languages, frameworks, tools) gives a pragmatic, explainable extraction approach rather than an opaque black box — important since "resume utilisation" needs to be traceable, not just accurate. |

## Infrastructure

| Choice | Why |
|---|---|
| **Docker + docker-compose** | One-command reproducible setup (`docker-compose up`) for grading — spins up backend, frontend, and Postgres together; matches the assignment's emphasis on a "complete, modular system, not a single script." |
| **Alembic migrations** | Explicit, versioned schema changes checked into the repo — shows data-layer maturity rather than ad-hoc table creation. |
| **Pytest / Vitest** | Minimal but real test coverage on the service layer (resume parsing, query building, report building) and key UI components, without over-investing given the time box. |

## Interfaces That Make the System Swappable

Two abstractions are deliberately introduced so grading/demo environments aren't locked to one
paid API:

```python
# app/llm/base.py
class LLMProvider(Protocol):
    def generate(self, prompt: str, **kwargs) -> str: ...

# app/rag/vector_store.py
class VectorStore(Protocol):
    def upsert(self, collection: str, ids, embeddings, metadatas, documents): ...
    def query(self, collection: str, query_embedding, k: int, filter: dict) -> list[Chunk]: ...
```

This is a small amount of extra structure that pays for itself: it keeps `QuestionGenerator`
and `RAGRetriever` fully unit-testable with fakes, and means "no OpenAI key available" is a
non-blocking issue during grading rather than a dead end.

## What Was Deliberately Not Used

- **Redis / Celery** — not needed at this scale; adds operational complexity without a
  corresponding requirement (no long-running background jobs beyond one-time KB ingestion,
  which is a CLI script, not a queued task).
- **A managed/paid vector DB (Pinecone, Weaviate Cloud, etc.)** — would add an external
  dependency and account setup friction for a 48-hour, locally-graded assignment; the
  `VectorStore` interface makes this a config swap if ever needed.
- **NextAuth / full auth system** — out of scope per the assignment's focus (RAG + backend +
  data flow), and called out explicitly in `ARCHITECTURE.md §7` as a non-goal rather than
  silently omitted.
