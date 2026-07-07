# API Design

Base path: `/api/v1`. All responses are JSON. All endpoints validate input via Pydantic and
return the standard error envelope on failure (see `ARCHITECTURE.md §6`).

The API is organized around the **interview lifecycle**, not raw CRUD, so each endpoint maps
to a step in the assignment's "Expected System Flow."

---

## 1. Roles

### `GET /roles`
Returns the list of supported roles and their knowledge-base status (useful for the frontend's
role-select screen).

**Response 200**
```json
{
  "roles": [
    {"slug": "backend_engineer", "label": "Backend Engineer", "kb_ready": true},
    {"slug": "ai_ml_engineer", "label": "AI/ML Engineer", "kb_ready": true}
  ]
}
```

---

## 2. Resume Upload

### `POST /resume`
Uploads and parses a resume. Multipart form upload. Does **not** create a session by itself —
separating "parse a resume" from "start a session" keeps the resume service reusable/testable
independent of session state.

**Request**: `multipart/form-data`, field `file` (PDF or `.txt`, max 5MB)

**Response 201**
```json
{
  "resume_id": "3f9a1e2c-...",
  "extracted": {
    "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
    "technologies": ["REST APIs", "Kubernetes"],
    "domains": ["backend systems", "distributed systems"],
    "years_experience_estimate": 2
  }
}
```

**Errors**: `400` unsupported file type/too large, `422` unparsable/empty resume text.

---

## 3. Sessions

### `POST /sessions`
Creates an interview session, binding a parsed resume to a selected role. Triggers context
construction (query building) synchronously; retrieval + first question generation happens on
the first `GET /sessions/{id}/next-question` call (kept separate so session creation stays
fast and idempotent).

**Request**
```json
{ "resume_id": "3f9a1e2c-...", "role": "backend_engineer" }
```

**Response 201**
```json
{
  "session_id": "8b7c2d10-...",
  "status": "CONTEXT_BUILT",
  "role": "backend_engineer",
  "max_questions": 8
}
```

### `GET /sessions/{session_id}`
Returns current session status, progress (`questions_asked`, `max_questions`), and whether a
report is available. Used by the frontend to safely resume after a refresh.

---

## 4. Interview Flow

### `GET /sessions/{session_id}/next-question`
Core RAG-driven endpoint. Retrieves context, generates (or fetches, if already generated and
unanswered) the next question, and returns it.

**Response 200**
```json
{
  "question_id": "q_004",
  "sequence": 4,
  "topic": "database indexing",
  "question_text": "Your resume mentions PostgreSQL — can you explain how you would decide between a B-tree and a hash index for a high-write lookup table?",
  "source_chunks": ["kb_backend_engineer::chunk_0231", "kb_backend_engineer::chunk_0489"],
  "is_final_question": false
}
```

**Errors**: `404` session not found, `409` session already `COMPLETED`.

### `POST /sessions/{session_id}/answers`
Submits an answer to the current question. Persists it, marks the question answered, and
(if adaptive mode is enabled) feeds the answer into the next question-generation call.

**Request**
```json
{ "question_id": "q_004", "answer_text": "I'd use a B-tree because..." }
```

**Response 200**
```json
{
  "stored": true,
  "session_status": "IN_PROGRESS",
  "questions_asked": 4,
  "questions_remaining": 4
}
```

**Errors**: `400` answer empty, `404` question/session not found, `409` question already
answered or belongs to a different (e.g. completed) session.

### `POST /sessions/{session_id}/end`
Allows the candidate (or auto-trigger at `max_questions`) to end the interview early. Moves
session to `COMPLETED` and triggers report generation.

---

## 5. Reports

### `GET /sessions/{session_id}/report`
Returns the structured summary described in the assignment ("structured summary of the
interaction" + "basic insights or analysis").

**Response 200**
```json
{
  "session_id": "8b7c2d10-...",
  "role": "backend_engineer",
  "generated_at": "2026-07-06T10:15:00Z",
  "topics_covered": ["REST design", "database indexing", "caching", "concurrency"],
  "transcript": [
    {
      "sequence": 1,
      "question": "...",
      "answer": "...",
      "topic": "REST design",
      "source_chunks": ["..."]
    }
  ],
  "insights": {
    "questions_answered": 8,
    "average_answer_length_words": 64,
    "topics_with_thin_answers": ["concurrency"],
    "resume_alignment_note": "Strong coverage of skills explicitly listed on resume (Docker, PostgreSQL); limited depth shown on distributed systems despite resume mention."
  }
}
```

**Errors**: `404` no report yet (session not completed).

---

## 6. Error Envelope (all endpoints)

```json
{
  "error_code": "SESSION_NOT_FOUND",
  "message": "No session found with the given id.",
  "details": {}
}
```

| HTTP Status | Meaning |
|---|---|
| 400 | Malformed/invalid request body |
| 404 | Resource (resume/session/question) not found |
| 409 | Valid request, invalid lifecycle state (e.g., answering a completed session) |
| 422 | Semantically invalid input (e.g., unparsable resume) |
| 502 | Upstream LLM or embedding provider failure after retries |
| 500 | Unexpected server error |

## 7. Why This Shape

- **Lifecycle-first, not resource-first**: endpoints mirror `CREATED → CONTEXT_BUILT →
  RETRIEVING → IN_PROGRESS → COMPLETED → REPORT_READY` from `ARCHITECTURE.md §3`, so the API
  reads as "what stage of the interview is this," matching the assignment's explicit request
  for "proper handling of different stages of the interview lifecycle."
- **Resume parsing is decoupled from session creation** so a resume can be validated/previewed
  before a role is chosen, and so resume parsing is unit-testable via a plain HTTP call without
  needing a full session.
- **`source_chunks` is returned on every question** — this is what makes question generation
  traceable end-to-end (context → question → answer → storage), directly satisfying
  §7.5 of the assignment.
