import json
import logging
import re

logger = logging.getLogger(__name__)


class QuestionGeneratorService:
    def __init__(self, llm_provider):
        self.llm = llm_provider

    def generate(self, role: str, topic: str, chunks: list, resume_signals: dict,
                 topics_already_asked: list[str] | None = None,
                 prev_answer: str | None = None,
                 years_experience: int = 0) -> dict:

        context = "\n\n".join(
            f"[Source: {c.metadata.get('source_doc', 'unknown')}, page {c.metadata.get('page', '?')}]\n{c.text}"
            for c in chunks
        ) if chunks else "No specific context available."

        signals_text = ", ".join(
            resume_signals.get("extracted_skills", []) +
            resume_signals.get("extracted_technologies", [])
        ) or "No specific signals extracted."

        already_asked = topics_already_asked or []

        prompt_parts = [
            f"You are a senior technical interviewer for the role of {role}. Ask exactly ONE question.",
            "It must be answerable using solid understanding of the provided context, and should require the candidate to explain reasoning, not just recall a fact.",
        ]
        if already_asked:
            prompt_parts.append(f"Do not repeat earlier topics: {', '.join(already_asked)}.")
        if years_experience >= 4:
            prompt_parts.append(f"The candidate has ~{years_experience} years experience — favor applied/design-tradeoff questions over textbook-definition questions.")
        elif years_experience <= 1:
            prompt_parts.append("The candidate is junior — ask foundational-but-reasoning questions.")

        prompt_parts.append(f"\nContext (retrieved from reference material):\n{context}")
        prompt_parts.append(f"\nCandidate background signals:\n{signals_text}")

        if prev_answer:
            prompt_parts.append(f"Candidate's previous answer, for calibrating depth/follow-up: \"{prev_answer}\"")

        prompt_parts.append('\nReturn strictly as JSON: {"topic": "...", "question": "..."}')

        prompt = "\n".join(prompt_parts)

        for attempt in range(3):
            try:
                raw = self.llm.generate(prompt, temperature=0.7, max_tokens=500)
                result = self._parse_json(raw)
                return result
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("LLM JSON parse attempt %d failed: %s", attempt + 1, e)
                if attempt == 0:
                    prompt += "\n\nReturn ONLY valid JSON. No markdown, no explanation."
                continue

        return {"topic": topic, "question": f"Explain the key concepts related to {topic} in {role}."}

    def _parse_json(self, text: str) -> dict:
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE | re.DOTALL)
        return json.loads(cleaned)
