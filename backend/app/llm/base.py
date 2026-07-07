from typing import Protocol


class LLMProvider(Protocol):
    def generate(self, prompt: str, **kwargs) -> str: ...
