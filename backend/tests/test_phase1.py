import uuid
from app.models.session import Session
from app.models.question import Question
from app.services.query_builder import QueryBuilderService


def test_create_session_without_resume(client, db_session):
    # Test POST /sessions with null resume_id
    payload = {
        "resume_id": None,
        "role": "Product Manager",
        "mode": "self_prep",
    }
    resp = client.post("/api/v1/sessions", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["session_id"] is not None
    assert data["role"] == "Product Manager"
    assert data["mode"] == "self_prep"

    # Verify session is saved in DB
    session = db_session.query(Session).filter(Session.id == uuid.UUID(data["session_id"])).first()
    assert session is not None
    assert session.resume_id is None
    assert session.role == "Product Manager"
    assert session.status == "CONTEXT_BUILT"
    assert len(session.retrieval_queries) > 0


def test_query_builder_fallback_for_custom_roles():
    builder = QueryBuilderService()
    
    # 1. Custom role with empty resume signals
    queries = builder.build_queries(
        resume_signals={"extracted_skills": [], "extracted_technologies": []},
        role="Growth Manager",
        max_questions=8,
    )
    
    assert len(queries) == 8
    assert all("Growth Manager concepts" in q for q in queries)
    # Check that default topics fallback is triggered
    assert "core concepts and principles" in queries[0]
    assert "practical problem solving" in queries[1]

    # 2. Custom role with populated resume signals
    queries_with_bg = builder.build_queries(
        resume_signals={
            "extracted_skills": ["Marketing Analytics", "A/B Testing"],
            "extracted_technologies": ["Python", "SQL"],
        },
        role="Growth Manager",
        max_questions=8,
    )
    assert len(queries_with_bg) == 8
    assert "candidate background: Marketing Analytics, A/B Testing, Python" in queries_with_bg[0]
