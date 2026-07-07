"""
OpenRouter LLM Provider
========================
Uses OpenRouter's OpenAI-compatible API endpoint.
OpenRouter gives access to 200+ models including Gemini, Claude, Llama etc.
via a single API key and the standard OpenAI SDK interface.

Default model: google/gemini-flash-1.5 (fast, capable, very low cost)
"""
import logging
from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterProvider:
    def __init__(self):
        self.client = OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=settings.openrouter_api_key,
        )
        self.model = settings.llm_model
        logger.info("OpenRouterProvider initialized — model: %s", self.model)

    def generate(self, prompt: str, **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 600),
            extra_headers={
                "HTTP-Referer": "https://candidate-screening.local",
                "X-Title": "Candidate Screening System",
            },
        )
        text = response.choices[0].message.content.strip()
        logger.debug("OpenRouter response (%s): %s", self.model, text[:200])
        return text
