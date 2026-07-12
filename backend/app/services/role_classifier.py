import re
import json
import logging
from dataclasses import dataclass
from app.core.config import settings
from app.models.role_family import RoleFamily

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    family_id: str | None
    family_slug: str | None
    method: str  # 'keyword' | 'llm' | 'unclassified'
    confidence: float | None


def _get_llm():
    if settings.groq_api_key:
        try:
            from app.llm.groq_provider import GroqProvider
            return GroqProvider()
        except Exception:
            pass

    if settings.gemini_api_key:
        try:
            from app.llm.gemini_provider import GeminiProvider
            return GeminiProvider()
        except Exception:
            pass

    if settings.openai_api_key:
        try:
            from app.llm.openai_provider import OpenAIProvider
            return OpenAIProvider()
        except Exception:
            pass

    from app.llm.fallback_provider import FallbackProvider
    return FallbackProvider()


class RoleClassifierService:
    """
    Two-stage classification:
    1. Keyword match against role_families.keywords (fast, free, deterministic)
    2. LLM fallback if no confident keyword match (flexible, smart)
    """

    KEYWORD_CONFIDENCE_THRESHOLD = 0.7

    def __init__(self, db_session, llm_provider=None):
        self.db = db_session
        self.llm = llm_provider or _get_llm()

    def classify(self, role_text: str) -> ClassificationResult:
        role_text_lower = role_text.lower().strip()

        # Stage 1: keyword match
        keyword_result = self._match_keywords(role_text_lower)
        if keyword_result:
            logger.info(f"RoleClassifier: Match found via keyword: {keyword_result.family_slug}")
            return keyword_result

        # Stage 2: LLM fallback
        logger.info(f"RoleClassifier: No keyword match. Falling back to LLM...")
        return self._classify_with_llm(role_text)

    def _match_keywords(self, role_text_lower: str) -> ClassificationResult | None:
        families = self.db.query(RoleFamily).all()
        best_match = None
        best_score = 0.0

        for family in families:
            for keyword in family.keywords:
                if keyword.lower() in role_text_lower:
                    # Simple scoring: exact word match > substring match
                    words = re.findall(r"\w+", role_text_lower)
                    score = 1.0 if keyword.lower() in words else 0.6
                    if score > best_score:
                        best_score = score
                        best_match = family

        if best_match and best_score >= self.KEYWORD_CONFIDENCE_THRESHOLD:
            return ClassificationResult(
                family_id=str(best_match.id),
                family_slug=best_match.slug,
                method="keyword",
                confidence=best_score,
            )
        return None

    def _classify_with_llm(self, role_text: str) -> ClassificationResult:
        families = self.db.query(RoleFamily).all()
        family_list = "\n".join(
            f"- {f.slug}: {f.description}" for f in families
        )

        prompt = f"""A candidate entered their target role as: "{role_text}"

Which of these role families best matches? Consider synonyms, related titles, and seniority variants (e.g. "Senior Backend Dev" matches "software_engineering").

{family_list}

Respond with ONLY the slug of the best match, or "unclassified" if none fit reasonably well. Also give a confidence score 0.0-1.0.

Return strictly as JSON: {{"slug": "...", "confidence": 0.0}}"""

        try:
            response = self.llm.generate(prompt, temperature=0.0, max_tokens=100)
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", response.strip(), flags=re.IGNORECASE | re.DOTALL)
            parsed = json.loads(cleaned)
            slug = parsed.get("slug")
            confidence = parsed.get("confidence", 0.0)

            if slug == "unclassified" or confidence < 0.5:
                return ClassificationResult(
                    family_id=None,
                    family_slug=None,
                    method="unclassified",
                    confidence=confidence,
                )

            family = self.db.query(RoleFamily).filter_by(slug=slug).first()
            if not family:
                return ClassificationResult(
                    family_id=None,
                    family_slug=None,
                    method="unclassified",
                    confidence=confidence,
                )

            return ClassificationResult(
                family_id=str(family.id),
                family_slug=family.slug,
                method="llm",
                confidence=confidence,
            )
        except Exception as e:
            logger.warning(f"LLM role classification failed: {e}. Degrading to unclassified.")
            return ClassificationResult(
                family_id=None,
                family_slug=None,
                method="unclassified",
                confidence=None,
            )
