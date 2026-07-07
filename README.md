# 🤖 AI-Powered Interview Screening System

An intelligent, RAG-powered candidate screening system that dynamically generates role-specific technical interview questions from a candidate's resume and a curated knowledge base — no pre-scripted question banks.

---

## 📋 Table of Contents

- [System Architecture](#system-architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Setup Instructions](#setup-instructions)
- [Knowledge Base Ingestion](#knowledge-base-ingestion)
- [Key Design Decisions](#key-design-decisions)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     Next.js 14 Frontend (:3000)                  │
│  ┌────────────┐   ┌─────────────────┐   ┌──────────────────┐    │
│  │  Home Page │   │  Interview Page  │   │   Summary Page   │    │
│  │  (Upload + │   │  (Q&A Session)   │   │   (Report View)  │    │
│  │   Role)    │   │                  │   │                  │    │
└──┴────────────┴───┴─────────────────┴───┴──────────────────┴────┘
                            │  HTTP/API
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (:8000)                         │
│                                                                  │
│   Resume Parser → Query Builder → RAG Retriever → LLM Generator  │
│         ↓               ↓               ↓                ↓       │
│   Extract Skills  Build Queries  Retrieve Chunks   Groq LLaMA   │
└──────────────────────────────────────────────────────────────────┘
         │                                        │
         ▼                                        ▼
┌─────────────────┐                    ┌──────────────────┐
│   PostgreSQL    │                    │    ChromaDB       │
│   (Sessions,    │                    │  (~50k chunks     │
│   Questions,    │                    │   from 7 books)   │
│   Answers)      │                    └──────────────────┘
└─────────────────┘
```

### End-to-End Flow

```
1. Resume Upload    → PDF parsed → skills/technologies extracted → stored in PostgreSQL
2. Role Selection   → Session created → 8 retrieval queries built from resume signals
3. Question Gen     → ChromaDB queried → 4 chunks retrieved → Groq LLaMA generates question
4. Answer Storage   → Candidate answers stored; prior answer optionally fed to next question
5. Report           → Structured summary: transcript + topic coverage + insights
```

---

## ✨ Features

- 📄 **Resume Processing** — PDF and plain-text upload; extracts skills, technologies, domains, and years of experience
- 🎯 **Role-Based Sessions** — `ai_ml_engineer` and `backend_engineer` roles (extensible)
- 📚 **RAG Pipeline** — 7 ML/AI textbooks ingested into ChromaDB; questions grounded in real reference material
- 🧠 **LLM Question Generation** — Groq (LLaMA 3.3 70B) generates unique, context-aware questions per session
- 🔄 **Adaptive Follow-ups** — Previous answer injected to calibrate depth of next question
- 💾 **Full Persistence** — All sessions, questions, and answers stored in PostgreSQL
- 📊 **Structured Reports** — Final report shows Q&A transcript, topics covered, resume alignment analysis
- 🐳 **One-Command Deploy** — Full stack via Docker Compose
- 🔌 **Multi-LLM Support** — Priority chain: Groq → Gemini → OpenAI → Template fallback

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript, Vanilla CSS |
| Backend | Python 3.11, FastAPI, SQLAlchemy, Alembic |
| Database | PostgreSQL 15 |
| Vector Store | ChromaDB (persistent) |
| Embeddings | `all-MiniLM-L6-v2` (sentence-transformers, local) |
| LLM | Groq API — `llama-3.3-70b-versatile` |
| Containerisation | Docker, Docker Compose |

---

## 🚀 Setup Instructions

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- A free [Groq API key](https://console.groq.com/) (optional — system works without one)

### 1. Clone the repository

```bash
git clone https://github.com/VaibhavChaudhary14/interview-.git
cd interview-
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and add your Groq API key:

```env
GROQ_API_KEY=gsk_your_key_here
```

> The system works without any API key using the built-in template fallback, but LLM-generated questions are significantly better.

### 3. Start all services

```bash
docker-compose up --build
```

This starts PostgreSQL, FastAPI backend, and Next.js frontend. Database migrations run automatically.

### 4. Ingest the knowledge base

In a new terminal while containers are running:

```bash
docker-compose exec backend python scripts/ingest_knowledge_base.py --role ai_ml_engineer
```

Processes 7 ML/AI textbooks (~50,000 chunks) into ChromaDB. Takes 5–15 minutes. The system functions without this step but RAG context will be unavailable.

### 5. Open the app

Navigate to **http://localhost:3000**

---

### Local Development (without Docker)

**Backend:**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

---

## 📚 Knowledge Base

Place PDF textbooks in `knowledge base/ai_ml_engineer/`. Books used for the AI/ML Engineer role:

| Book | Author |
|---|---|
| The Hundred-Page Machine Learning Book | Andriy Burkov |
| Machine Learning for Absolute Beginners | — |
| Introduction to Machine Learning with Python | — |
| Master Machine Learning Algorithms | Jason Brownlee |
| Pattern Recognition and Machine Learning | Christopher Bishop |
| Artificial Intelligence, Machine Learning & Deep Learning | — |

Re-running the ingestion script is safe — it uses `upsert` (idempotent).

---

## 🏛️ Key Design Decisions

### 1. RAG over Fine-Tuning
Questions are grounded in retrieved textbook chunks rather than fine-tuned model weights. This approach is updatable (add new books without retraining), traceable (every question stores source chunk IDs), and cost-effective (no GPU or fine-tuning API required).

### 2. Session State Machine
Sessions transition through well-defined states: `CREATED → CONTEXT_BUILT → RETRIEVING → IN_PROGRESS → COMPLETED → REPORT_READY`. This prevents invalid transitions and enables robust error handling and resumability.

### 3. Multi-Provider LLM Chain
The system tries providers in priority order: **Groq → Gemini → OpenAI → Template fallback**. Zero downtime if one provider is unavailable; works out-of-the-box with no API keys.

### 4. Local Embeddings
`all-MiniLM-L6-v2` runs entirely inside Docker — no embedding API calls, no rate limits, no cost. Knowledge base ingestion and retrieval work fully offline.

### 5. Resume Signals as Prompt Context
Extracted skills, technologies, and years of experience are injected into every question prompt. Combined with experience level, the LLM generates questions calibrated to the specific candidate — junior vs. senior framing, applied vs. theoretical depth.

### 6. Adaptive Question Calibration
When `ADAPTIVE_MODE=true`, the previous answer is fed into the next question prompt. This lets the LLM detect shallow answers and probe deeper, or advance to harder concepts when answers are strong.

### 7. Chunking Strategy
`RecursiveCharacterTextSplitter` with 800-character chunks and 120-character overlap. Overlap preserves cross-sentence context at boundaries; 800 characters keeps retrieval granular while fitting LLM context windows comfortably.

### 8. Progressive Ingestion
The ingestion pipeline upserts chunks to ChromaDB after each PDF is processed rather than buffering everything in memory. RAG queries work immediately after the first book finishes, and memory footprint is bounded regardless of library size.

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/resume` | Upload resume (PDF/txt), extract signals |
| `POST` | `/api/v1/sessions` | Create interview session |
| `GET` | `/api/v1/sessions/{id}` | Get session state |
| `GET` | `/api/v1/sessions/{id}/next-question` | Generate and return next question |
| `POST` | `/api/v1/sessions/{id}/answers` | Submit answer to current question |
| `POST` | `/api/v1/sessions/{id}/end` | Mark session as complete |
| `POST` | `/api/v1/sessions/{id}/report` | Build and persist final report |
| `GET` | `/api/v1/sessions/{id}/report` | Retrieve final report |

Interactive API docs: **http://localhost:8000/docs**

---

## 📁 Project Structure

```
interview-/
├── backend/
│   ├── app/
│   │   ├── api/v1/               # FastAPI route handlers
│   │   │   ├── routes_resume.py
│   │   │   ├── routes_session.py
│   │   │   ├── routes_interview.py
│   │   │   └── routes_report.py
│   │   ├── core/config.py        # Pydantic settings (env vars)
│   │   ├── db/                   # SQLAlchemy + Alembic migrations
│   │   ├── llm/                  # Groq / Gemini / OpenAI / Fallback providers
│   │   ├── models/               # SQLAlchemy ORM models
│   │   ├── rag/                  # Ingestion, retriever, ChromaDB wrapper
│   │   ├── schemas/              # Pydantic request/response schemas
│   │   └── services/             # Business logic: parser, query builder, generator, report
│   ├── scripts/
│   │   └── ingest_knowledge_base.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx              # Home: upload + role selection
│   │   ├── interview/[sessionId]/page.tsx   # Live Q&A
│   │   └── summary/[sessionId]/page.tsx     # Final report
│   ├── Dockerfile
│   └── package.json
│
├── knowledge base/
│   └── ai_ml_engineer/           # ML/AI textbook PDFs
│
├── docker-compose.yml
├── .env.example
└── README.md
```
