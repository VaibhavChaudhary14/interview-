"""
Groq LLM Provider
===================
Uses Groq's OpenAI-compatible REST API.
Default model: llama-3.3-70b-versatile (highly capable, extremely fast)
"""
import logging
from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class GroqProvider:
    def __init__(self):
        self.client = OpenAI(
            base_url=GROQ_BASE_URL,
            api_key=settings.groq_api_key,
        )
        self.model = settings.groq_model
        logger.info("GroqProvider initialized — model: %s", self.model)

    def generate(self, prompt: str, **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 600),
        )
        text = response.choices[0].message.content.strip()
        logger.debug("Groq response (%s): %s", self.model, text[:200])
        return text
