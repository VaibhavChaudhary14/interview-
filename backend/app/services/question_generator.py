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
                 years_experience: int = 0,
                 mode: str = "self_prep",
                 difficulty: str = "intermediate") -> dict:

        signals_text = ", ".join(
            resume_signals.get("extracted_skills", []) +
            resume_signals.get("extracted_technologies", [])
        ) or "No specific skills extracted."

        already_asked = topics_already_asked or []

        DIFFICULTY_CLAUSES = {
            "beginner": (
                "The candidate selected Beginner difficulty. Ask foundational "
                "questions that test core understanding, not edge cases or "
                "advanced trade-offs, regardless of their resume experience level."
            ),
            "intermediate": (
                "The candidate selected Intermediate difficulty. Balance "
                "foundational reasoning with some applied, real-world scenarios."
            ),
            "advanced": (
                "The candidate selected Advanced difficulty. Favor applied "
                "design-tradeoff and edge-case questions over textbook definitions, "
                "regardless of their resume experience level."
            ),
        }
        diff_clause = DIFFICULTY_CLAUSES.get(difficulty, DIFFICULTY_CLAUSES["intermediate"])

        # If no RAG chunks are retrieved, use the Fallback Prompt Template (no-KB mode)
        if not chunks:
            topics_clause = f"Do not repeat earlier topics: {', '.join(already_asked)}." if already_asked else ""
            prompt = f"""You are a supportive interview coach helping a candidate
prepare for a role as: {role}

The candidate has {years_experience} years of experience, with skills including: {signals_text}.

No reference material is available for this specific role, so rely on your general
knowledge of what a realistic interview for this role would cover. Ask exactly ONE
question that requires the candidate to explain reasoning, not just recall a fact.

{diff_clause}

{topics_clause}

Return strictly as JSON with this structure:
{{
  "topic": "Topic Name",
  "question": "The question text?",
  "copilot_hints": {{
    "outline": ["bullet point outline key 1", "bullet point outline key 2"],
    "keywords": ["keyword1", "keyword2", "keyword3"]
  }}
}}"""
        else:
            context = "\n\n".join(
                f"[Source: {c.metadata.get('source_doc', 'unknown')}, page {c.metadata.get('page', '?')}]\n{c.text}"
                for c in chunks
            )

            if mode == "agency":
                prompt_parts = [
                    f"You are a professional, rigorous technical recruiter/interviewer conducting a formal screening for the role of {role}. Ask exactly ONE question.",
                    "Maintain a formal, objective, and testing tone. The question must be answerable using solid understanding of the provided context, and should require the candidate to explain reasoning, not just recall a fact.",
                ]
            else:
                prompt_parts = [
                    f"You are a supportive, encouraging mock interviewer helping a candidate practice for the role of {role}. Ask exactly ONE question.",
                    "Maintain an encouraging, constructive, and helpful tone. The question must be answerable using solid understanding of the provided context, and should require the candidate to explain reasoning, not just recall a fact.",
                ]

            if already_asked:
                prompt_parts.append(f"Do not repeat earlier topics: {', '.join(already_asked)}.")
            
            prompt_parts.append(diff_clause)

            prompt_parts.append(f"\nContext (retrieved from reference material):\n{context}")
            prompt_parts.append(f"\nCandidate background signals:\n{signals_text}")

            if prev_answer:
                prompt_parts.append(f"Candidate's previous answer, for calibrating depth/follow-up: \"{prev_answer}\"")

            prompt_parts.append('\nReturn strictly as JSON with this structure:\n{\n  "topic": "Topic Name",\n  "question": "The question text?",\n  "copilot_hints": {\n    "outline": ["bullet point outline key 1", "bullet point outline key 2"],\n    "keywords": ["keyword1", "keyword2", "keyword3"]\n  }\n}')
            prompt = "\n".join(prompt_parts)

        for attempt in range(3):
            try:
                raw = self.llm.generate(prompt, temperature=0.7, max_tokens=500)
                result = self._parse_json(raw)
                if not isinstance(result, dict):
                    raise ValueError("Parsed output is not a JSON object")
                if "topic" not in result or "question" not in result:
                    raise ValueError("JSON missing required fields 'topic' or 'question'")
                if "copilot_hints" not in result or not isinstance(result["copilot_hints"], dict):
                    result["copilot_hints"] = {
                        "outline": [f"Discuss concepts related to {result.get('topic', topic)}"],
                        "keywords": [w.strip() for w in result.get("topic", topic).split() if len(w) > 2]
                    }
                return result
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("LLM JSON parse attempt %d failed: %s", attempt + 1, e)
                if attempt == 0:
                    prompt += "\n\nReturn ONLY valid JSON. No markdown, no explanation."
                continue

        return {
            "topic": topic,
            "question": f"Explain the key concepts related to {topic} in {role}.",
            "copilot_hints": {
                "outline": [f"Explain key concepts of {topic}"],
                "keywords": [topic]
            }
        }

    def _parse_json(self, text: str) -> dict:
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE | re.DOTALL)
        return json.loads(cleaned)
