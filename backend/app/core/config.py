from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:postgres@db:5432/screening_db"
    vector_store_path: str = "/app/data/chroma"

    # ── LLM Provider Keys (priority: groq > gemini > openai > fallback) ──
    openai_api_key: str = ""
    groq_api_key: str = ""
    gemini_api_key: str = ""

    # Default model per provider
    groq_model: str = "llama-3.3-70b-versatile"
    gemini_model: str = "gemini-1.5-flash"
    openai_model: str = "gpt-4o-mini"

    # Embedding (always local — no API key needed)
    embedding_model: str = "all-MiniLM-L6-v2"

    # Chunking
    chunk_size: int = 800
    chunk_overlap: int = 120

    # Interview
    max_questions_per_session: int = 8
    retrieval_k: int = 4
    similarity_threshold: float = 0.35
    adaptive_mode: bool = False
    max_retries: int = 2

    # App
    env: Literal["development", "production", "test"] = "development"
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "extra": "allow"}


settings = Settings()
