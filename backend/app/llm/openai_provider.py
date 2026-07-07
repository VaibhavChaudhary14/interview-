import logging
from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)


class OpenAIProvider:
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.llm_model

    def generate(self, prompt: str, **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 500),
        )
        text = response.choices[0].message.content.strip()
        logger.debug("LLM response: %s", text[:200])
        return text
