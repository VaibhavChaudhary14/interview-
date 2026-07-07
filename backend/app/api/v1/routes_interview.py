import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from app.db.session import get_db
from app.models.resume import Resume
from app.models.session import Session
from app.models.question import Question
from app.models.answer import Answer
from app.services.query_builder import QueryBuilderService
from app.services.question_generator import QuestionGeneratorService
from app.schemas.question import QuestionResponse
from app.schemas.answer import AnswerSubmitRequest, AnswerSubmitResponse
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions/{session_id}", tags=["interview"])

query_builder = QueryBuilderService()

# Lazy singletons — initialized on first request to avoid startup failures
# if the OpenAI key or ChromaDB path isn't configured yet.
_llm = None
_embedder = None
_chroma_store = None
_retriever = None


def _get_llm():
    global _llm
    if _llm is None:
        if settings.groq_api_key:
            # Priority 1: Groq (llama-3.3-70b-versatile, verified working!)
            try:
                from app.llm.groq_provider import GroqProvider
                _llm = GroqProvider()
                logger.info("LLM: Groq provider initialized (model: %s)", settings.groq_model)
            except Exception as e:
                logger.warning("Groq provider failed (%s) — falling back to other providers", e)
                _llm = None

        if _llm is None and settings.gemini_api_key:
            # Priority 2: Direct Google Gemini API
            try:
                from app.llm.gemini_provider import GeminiProvider
                _llm = GeminiProvider()
                logger.info("LLM: Gemini provider initialized (model: %s)", settings.gemini_model)
            except Exception as e:
                logger.warning("Gemini provider failed (%s) — falling back to other providers", e)
                _llm = None

        if _llm is None and settings.openai_api_key:
            # Priority 3: OpenAI directly
            try:
                from app.llm.openai_provider import OpenAIProvider
                _llm = OpenAIProvider()
                logger.info("LLM: OpenAI provider initialized")
            except Exception as e:
                logger.warning("OpenAI provider failed (%s)", e)
                _llm = None

        if _llm is None:
            # Priority 4: Template fallback (no API key needed)
            from app.llm.fallback_provider import FallbackProvider
            _llm = FallbackProvider()
            logger.warning("LLM: No functional API keys/providers available — using FallbackProvider (template questions)")
    return _llm


def _get_retriever():
    global _embedder, _chroma_store, _retriever
    if _retriever is None:
        try:
            from sentence_transformers import SentenceTransformer
            from app.rag.retriever import Embedder, RAGRetriever
            from app.rag.chroma_store import ChromaStore
            _embedder = Embedder()
            _chroma_store = ChromaStore()
            _retriever = RAGRetriever(_chroma_store, _embedder)
            logger.info("RAG retriever initialized")
        except Exception as e:
            logger.warning("RAG retriever init failed: %s — questions will skip retrieval", e)
            _retriever = None
    return _retriever


@router.get("/next-question", response_model=QuestionResponse)
def get_next_question(session_id: str, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(404, detail={"error_code": "SESSION_NOT_FOUND", "message": "No session found.", "details": {}})
    if session.status in ("COMPLETED", "REPORT_READY"):
        raise HTTPException(409, detail={"error_code": "SESSION_COMPLETED", "message": "Session is already completed.", "details": {}})

    # Return existing unanswered question if present (safe resume after refresh)
    unanswered = (
        db.query(Question)
        .filter(Question.session_id == session.id)
        .outerjoin(Answer, Answer.question_id == Question.id)
        .filter(Answer.id.is_(None))
        .order_by(Question.sequence)
        .first()
    )
    if unanswered:
        return QuestionResponse(
            question_id=str(unanswered.id),
            sequence=unanswered.sequence,
            topic=unanswered.topic,
            question_text=unanswered.question_text,
            source_chunks=unanswered.source_chunk_ids or [],
            is_final_question=session.questions_asked >= session.max_questions,
        )

    # Check if we've hit the question limit
    if session.questions_asked >= session.max_questions:
        raise HTTPException(409, detail={"error_code": "ALL_QUESTIONS_ASKED", "message": "All questions have been asked.", "details": {}})

    # Advance state machine
    if session.status == "CONTEXT_BUILT":
        session.transition_to("RETRIEVING")
    elif session.status not in ("RETRIEVING", "IN_PROGRESS"):
        session.transition_to("RETRIEVING")

    # Load resume signals
    resume = db.query(Resume).filter(Resume.id == session.resume_id).first()
    resume_signals = {
        "extracted_skills": resume.extracted_skills if resume else [],
        "extracted_technologies": resume.extracted_technologies if resume else [],
    }
    years_exp = resume.years_experience_estimate if resume else 0

    # Determine topic for this question
    queries = session.retrieval_queries or []
    topic_index = session.questions_asked
    if topic_index < len(queries):
        query = queries[topic_index]
        topic = query.split("Focus: ")[-1] if "Focus: " in query else "general"
    else:
        topic = "general"
        query = f"{session.role} — Focus: general"

    # ─── RAG RETRIEVAL ────────────────────────────────────────────────────────
    chunks = []
    retriever = _get_retriever()
    if retriever:
        try:
            chunks = retriever.retrieve(query=query, role=session.role, k=settings.retrieval_k)
            logger.info("Retrieved %d chunks for topic '%s'", len(chunks), topic)
            # If no chunks above threshold, retry with role-generic query
            if not chunks:
                fallback_query = f"{session.role} {topic}"
                chunks = retriever.retrieve(query=fallback_query, role=session.role, k=settings.retrieval_k)
                logger.info("Fallback retrieval: %d chunks", len(chunks))
        except Exception as e:
            logger.warning("RAG retrieval failed: %s — proceeding without context", e)
            chunks = []
    # ─────────────────────────────────────────────────────────────────────────

    # Optional adaptive context from last answer
    prev_answer_text = None
    if settings.adaptive_mode:
        last_answer = (
            db.query(Answer)
            .join(Question, Question.id == Answer.question_id)
            .filter(Question.session_id == session.id)
            .order_by(Answer.answered_at.desc())
            .first()
        )
        if last_answer:
            prev_answer_text = last_answer.answer_text

    already_asked = [q.topic for q in db.query(Question).filter(Question.session_id == session.id).all()]

    # ─── QUESTION GENERATION ──────────────────────────────────────────────────
    llm = _get_llm()
    result = QuestionGeneratorService(llm).generate(
        role=session.role,
        topic=topic,
        chunks=chunks,
        resume_signals=resume_signals,
        topics_already_asked=already_asked,
        prev_answer=prev_answer_text,
        years_experience=years_exp,
    )
    # ─────────────────────────────────────────────────────────────────────────

    new_question = Question(
        session_id=session.id,
        sequence=session.questions_asked + 1,
        topic=result.get("topic", topic),
        question_text=result.get("question", ""),
        source_chunk_ids=[c.id for c in chunks],
        generation_strategy="adaptive" if prev_answer_text else "initial",
    )
    db.add(new_question)
    session.questions_asked += 1
    if session.status != "IN_PROGRESS":
        session.transition_to("IN_PROGRESS")
    db.commit()
    db.refresh(new_question)

    return QuestionResponse(
        question_id=str(new_question.id),
        sequence=new_question.sequence,
        topic=new_question.topic,
        question_text=new_question.question_text,
        source_chunks=new_question.source_chunk_ids or [],
        is_final_question=session.questions_asked >= session.max_questions,
    )


@router.post("/answers", response_model=AnswerSubmitResponse)
def submit_answer(session_id: str, body: AnswerSubmitRequest, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(404, detail={"error_code": "SESSION_NOT_FOUND", "message": "No session found.", "details": {}})
    if session.status in ("COMPLETED", "REPORT_READY"):
        raise HTTPException(409, detail={"error_code": "SESSION_COMPLETED", "message": "Session is already completed.", "details": {}})

    question = db.query(Question).filter(Question.id == body.question_id, Question.session_id == session.id).first()
    if not question:
        raise HTTPException(404, detail={"error_code": "QUESTION_NOT_FOUND", "message": "Question not found in this session.", "details": {}})

    existing = db.query(Answer).filter(Answer.question_id == question.id).first()
    if existing:
        raise HTTPException(409, detail={"error_code": "ALREADY_ANSWERED", "message": "This question has already been answered.", "details": {}})

    if not body.answer_text.strip():
        raise HTTPException(400, detail={"error_code": "EMPTY_ANSWER", "message": "Answer cannot be empty.", "details": {}})

    word_count = len(body.answer_text.split())
    answer = Answer(question_id=question.id, answer_text=body.answer_text, word_count=word_count)
    db.add(answer)

    if session.questions_asked >= session.max_questions:
        session.transition_to("COMPLETED")

    db.commit()

    remaining = session.max_questions - session.questions_asked
    return AnswerSubmitResponse(
        stored=True,
        session_status=session.status,
        questions_asked=session.questions_asked,
        questions_remaining=max(0, remaining),
    )


@router.post("/end")
def end_session(session_id: str, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(404, detail={"error_code": "SESSION_NOT_FOUND", "message": "No session found.", "details": {}})
    if session.status in ("COMPLETED", "REPORT_READY"):
        raise HTTPException(409, detail={"error_code": "ALREADY_ENDED", "message": "Session already ended.", "details": {}})

    session.transition_to("COMPLETED")
    db.commit()
    return {"status": "COMPLETED"}
