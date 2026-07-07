# AI-Powered Role-Based Candidate Screening System

An intelligent interview simulator that generates dynamic, context-aware technical interview
questions from a candidate's resume, a selected job role, and a role-specific knowledge base,
using a Retrieval-Augmented Generation (RAG) pipeline.

> Built for the PGAGI AI/ML & Backend Intern Assignment.

---

## 1. What This System Does

1. Candidate uploads a resume and picks a target role (Backend Engineer, AI/ML Engineer, etc.)
2. The backend parses the resume and extracts skills, technologies, and domain signals.
3. The system builds retrieval queries from the resume + role, and pulls relevant chunks from a
   role-specific vector knowledge base (textbooks provided in the assignment).
4. An LLM generates interview questions grounded in the retrieved context and shaped by the
   candidate's background.
5. The candidate answers questions one at a time through the UI; the system persists every
   question/answer pair and can adapt the next question based on the previous answer.
6. At the end, the system produces a structured summary with basic analysis (topics covered,
   answer quality signals, resume-to-role fit).

See `ARCHITECTURE.md` for component-level design, `RAG_PIPELINE.md` for the AI/ML core,
`API_DESIGN.md` for the contract between frontend and backend, and `DATABASE_SCHEMA.md` for
persistence.

---

## 2. Tech Stack At a Glance

| Layer            | Choice                                             |
|-------------------|-----------------------------------------------------|
| Frontend          | Next.js 14 (App Router) + TypeScript + Tailwind CSS |
| Backend           | Python 3.11 + FastAPI                               |
| Relational DB     | PostgreSQL 15                                       |
| Vector DB         | ChromaDB (local/embedded, swappable for pgvector)   |
| Embeddings        | `sentence-transformers/all-MiniLM-L6-v2` (local)    |
| LLM (generation)  | OpenAI `gpt-4o-mini` (pluggable via LLM adapter)    |
| Resume parsing    | `pdfplumber` + `spaCy` (en_core_web_sm) + regex     |
| Chunking          | LangChain `RecursiveCharacterTextSplitter`          |
| ORM               | SQLAlchemy 2.0 + Alembic (migrations)                |
| Task/session state| FastAPI + Postgres-backed session table (no Redis required for MVP) |
| Containerization  | Docker + docker-compose                             |
| Testing           | Pytest (backend), Vitest + React Testing Library (frontend) |

Full reasoning behind each choice is in `TECH_STACK.md`.

---

## 3. Repository Structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app entrypoint
│   │   ├── core/
│   │   │   ├── config.py            # env-driven settings (pydantic-settings)
│   │   │   └── logging.py
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── routes_sessions.py
│   │   │       ├── routes_resume.py
│   │   │       ├── routes_interview.py
│   │   │       └── routes_reports.py
│   │   ├── models/                  # SQLAlchemy models
│   │   ├── schemas/                 # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── resume_parser.py
│   │   │   ├── query_builder.py
│   │   │   ├── rag_pipeline.py
│   │   │   ├── question_generator.py
│   │   │   └── report_builder.py
│   │   ├── rag/
│   │   │   ├── ingestion.py         # chunking + embedding + upsert to vector store
│   │   │   ├── retriever.py
│   │   │   └── vector_store.py      # Chroma wrapper
│   │   ├── db/
│   │   │   ├── session.py
│   │   │   └── migrations/
│   │   └── llm/
│   │       ├── base.py              # LLMProvider interface
│   │       └── openai_provider.py
│   ├── data/
│   │   └── knowledge_base/          # source PDFs per role
│   ├── scripts/
│   │   └── ingest_knowledge_base.py # one-off ingestion CLI
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app/
│   │   ├── page.tsx                 # landing / resume upload + role select
│   │   ├── interview/[sessionId]/page.tsx
│   │   └── summary/[sessionId]/page.tsx
│   ├── components/
│   ├── lib/api.ts                   # typed API client
│   ├── store/                       # Zustand store for interview state
│   ├── package.json
│   └── Dockerfile
├── docs/
│   ├── README.md
│   ├── ARCHITECTURE.md
│   ├── TECH_STACK.md
│   ├── API_DESIGN.md
│   ├── DATABASE_SCHEMA.md
│   └── RAG_PIPELINE.md
├── docker-compose.yml
└── .env.example
```

---

## 4. Setup Instructions

### 4.1 Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (recommended for one-command setup)
- An OpenAI API key (or swap in a local LLM via the `LLMProvider` interface — see `TECH_STACK.md`)

### 4.2 Environment Variables (`.env`)

```bash
# Backend
DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/screening_db
VECTOR_STORE_PATH=/app/data/chroma
OPENAI_API_KEY=sk-xxxxxxxx
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=all-MiniLM-L6-v2
CHUNK_SIZE=800
CHUNK_OVERLAP=120
MAX_QUESTIONS_PER_SESSION=8
ENV=development
LOG_LEVEL=INFO

# Frontend
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

### 4.3 Quick Start (Docker)

```bash
git clone <repo-url>
cd candidate-screening-system
cp .env.example .env        # fill in OPENAI_API_KEY
docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend docs (Swagger): http://localhost:8000/docs

### 4.4 One-time Knowledge Base Ingestion

Place role-specific source PDFs (from the assignment's provided reading list) into
`backend/data/knowledge_base/<role_slug>/`, then run:

```bash
docker-compose exec backend python scripts/ingest_knowledge_base.py --role ai_ml_engineer
docker-compose exec backend python scripts/ingest_knowledge_base.py --role backend_engineer
```

This chunks each document, generates embeddings, and upserts them into a role-scoped Chroma
collection (`kb_<role_slug>`).

### 4.5 Manual (Non-Docker) Setup

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

---

## 5. Key Design Decisions (Summary)

- **Resume-aware retrieval, not generic retrieval.** Queries sent to the vector store are
  synthesized from extracted resume entities + role, not just the role name, so retrieval is
  personalized rather than static.
- **LLM is abstracted behind an interface** (`LLMProvider`) so grading/local runs can swap
  OpenAI for a local model (e.g., Ollama) without touching business logic.
- **Every question is traceable** back to the retrieved chunk(s) and the resume signal that
  triggered it, stored in the `questions` table — satisfying the "traceability" requirement.
- **Adaptive follow-ups are optional and isolated** in `question_generator.py` behind a
  strategy flag, so the baseline linear flow keeps working even if adaptivity is disabled.
- **Postgres does double duty** for both relational session data and (optionally) `pgvector`
  as a fallback vector store, keeping infra minimal for an intern-scope project.

Full rationale: see `TECH_STACK.md` and `ARCHITECTURE.md`.

---

## 6. Testing

```bash
# Backend
cd backend && pytest -v

# Frontend
cd frontend && npm run test
```

---

## 7. Known Limitations / Future Extensions

- No auth/user accounts (single-session, link-based access) — noted in `ARCHITECTURE.md` §7.
- Adaptive questioning uses a simple heuristic (answer length + keyword overlap), not a full
  scoring model — a natural next step is a lightweight answer-quality classifier.
- Vector store is local/embedded (Chroma) for simplicity; swapping to a managed vector DB
  (Pinecone/Qdrant) is a config change, not a code rewrite, due to the `VectorStore` interface.
