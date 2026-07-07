"""
Google Gemini LLM Provider (direct API)
==========================================
Uses the Google Generative AI SDK to call Gemini models directly.
Requires: pip install google-generativeai

Default model: gemini-1.5-flash (fast, free-tier generous quota)
"""
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiProvider:
    def __init__(self):
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.gemini_api_key)
            self.model = genai.GenerativeModel(settings.gemini_model)
            self.model_name = settings.gemini_model
            logger.info("GeminiProvider initialized — model: %s", self.model_name)
        except ImportError:
            raise RuntimeError(
                "google-generativeai is not installed. "
                "Run: pip install google-generativeai"
            )

    def generate(self, prompt: str, **kwargs) -> str:
        import google.generativeai as genai

        generation_config = genai.GenerationConfig(
            temperature=kwargs.get("temperature", 0.7),
            max_output_tokens=kwargs.get("max_tokens", 600),
        )

        response = self.model.generate_content(
            prompt,
            generation_config=generation_config,
        )
        text = response.text.strip()
        logger.debug("Gemini response (%s): %s", self.model_name, text[:200])
        return text
