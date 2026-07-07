import logging

logger = logging.getLogger(__name__)

ROLE_CONTEXT = {
    "backend_engineer": "core backend engineering concepts including APIs, databases, and system design",
    "ai_ml_engineer": "machine learning, deep learning, NLP, and AI engineering concepts",
}

TOPIC_CHECKLISTS = {
    "backend_engineer": [
        "API design", "databases", "caching", "concurrency",
        "system design", "testing", "security", "performance",
    ],
    "ai_ml_engineer": [
        "supervised learning", "neural networks", "NLP", "model evaluation",
        "feature engineering", "deep learning", "ML ops", "statistics",
    ],
}


class QueryBuilderService:
    def build_queries(self, resume_signals: dict, role: str, max_questions: int) -> list[str]:
        role_phrase = ROLE_CONTEXT.get(role, f"{role} concepts")
        topics = TOPIC_CHECKLISTS.get(role, [])
        top_skills = resume_signals.get("extracted_skills", [])[:5]
        top_tech = resume_signals.get("extracted_technologies", [])[:3]

        queries = []
        for i in range(min(max_questions, len(topics))):
            topic = topics[i % len(topics)]
            query = f"{role_phrase} — candidate background: {', '.join(top_skills + top_tech)}. Focus: {topic}"
            queries.append(query)

        logger.info("Built %d retrieval queries for role=%s", len(queries), role)
        return queries
