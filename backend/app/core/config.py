from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:postgres@db:5432/screening_db"
    vector_store_path: str = "/app/data/chroma"

    # S3 Settings
    s3_bucket_name: str = "voice-recordings-prod"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    s3_endpoint_url: str = ""
    recordings_local_dir: str = "data/recordings"

    # ── LLM Provider Keys (priority: groq > gemini > openai > fallback) ──
    openai_api_key: str = ""
    groq_api_key: str = ""
    gemini_api_key: str = ""

    # ── STT / TTS Keys ──
    assemblyai_api_key: str = "c08b2cf28c4047e7a8bdf73457bdec32"
    elevenlabs_api_key: str = "sk_91b72d69ec38a72adef6aa515e49122b49f6d53d20813599"
    sarvam_api_key: str = "sk_tix66uvv_9y6Fo3I9eWzwtA8mBdxvZePX"
    sarvam_api_key_fallback: str = "sk_kixv8l12_acWH0VDyvoYRzs8mtg9a0DCN"
    base_webhook_url: str = ""

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
