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
        if not topics:
            topics = [
                "core concepts and principles",
                "practical problem solving",
                "system or workflow design",
                "performance and optimization",
                "testing and quality assurance",
                "security and reliability",
                "collaboration and communication",
                "prior project experience",
            ]

        top_skills = resume_signals.get("extracted_skills", [])[:5]
        top_tech = resume_signals.get("extracted_technologies", [])[:3]

        queries = []
        for i in range(min(max_questions, len(topics))):
            topic = topics[i % len(topics)]
            background_text = ""
            if top_skills or top_tech:
                background_text = f" — candidate background: {', '.join(top_skills + top_tech)}"
            query = f"{role_phrase}{background_text}. Focus: {topic}"
            queries.append(query)

        logger.info("Built %d retrieval queries for role=%s", len(queries), role)
        return queries
