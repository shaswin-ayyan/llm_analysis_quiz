from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET: str = "changeme"
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # ------------------------
    # GEMINI SUPPORT
    # ------------------------
    GEMINI_API_KEY: str = ""
    GEMINI_MODELS: List[str] = Field(
        default_factory=lambda: ["gemini-2.5-flash-preview-09-2025"]
    )

    # ------------------------
    # OpenRouter / OpenAI-compatible
    # ------------------------
    OPENAI_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENAI_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None
    
    # AI Pipe Proxy (Optional/Legacy)
    AIPIPE_PROXY_URL: str = "https://aipipe.org/proxy"

    LLM_CHAT_MODEL: str = "google/gemma-3-27b-it"
    
    # Model Constants
    # Tier 1: Orchestrator (Speed & Multimodal)
    ORCHESTRATOR_MODEL: str = "google/gemma-3-27b-it"
    # Tier 2: Worker (Deep Analysis)
    WORKER_MODEL: str = "alibaba/tongyi-deepresearch-30b-a3b"
    # Audio Transcription
    AUDIO_MODEL: str = "google/gemini-2.0-flash-lite-preview-02-05"

    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
