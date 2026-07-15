import pytest
from app.models.session import SessionDifficulty
from app.services.question_generator import QuestionGeneratorService


def test_session_difficulty_defaults_to_intermediate(client, db_session):
    # Call create session API without specifying difficulty, assert it defaults to intermediate
    resp = client.post(
        "/api/v1/sessions",
        json={
            "role": "software_engineering",
            "mode": "self_prep",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["difficulty"] == "intermediate"


def test_difficulty_prompt_override():
    # Mock LLM provider to inspect prompt passed to it
    class MockLLM:
        def __init__(self):
            self.last_prompt = None

        def generate(self, prompt, temperature=0.7, max_tokens=500):
            self.last_prompt = prompt
            return '{"topic": "Design Patterns", "question": "Explain Singleton pattern?", "copilot_hints": {"outline": ["concept"], "keywords": ["singleton"]}}'

    llm = MockLLM()
    generator = QuestionGeneratorService(llm)

    # 1. Test Beginner
    generator.generate(
        role="software_engineering",
        topic="Databases",
        chunks=[],
        resume_signals={"extracted_skills": ["SQL"]},
        difficulty="beginner",
    )
    assert "Beginner difficulty" in llm.last_prompt
    assert "Advanced difficulty" not in llm.last_prompt

    # 2. Test Advanced
    generator.generate(
        role="software_engineering",
        topic="Databases",
        chunks=[],
        resume_signals={"extracted_skills": ["SQL"]},
        difficulty="advanced",
    )
    assert "Advanced difficulty" in llm.last_prompt
    assert "Beginner difficulty" not in llm.last_prompt
