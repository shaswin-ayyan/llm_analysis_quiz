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

    # ------------------------
    # AIPIPE SWITCH
    # ------------------------
    USE_AIPIPE: bool = True
    AIPIPE_API_KEY: str | None = None
    AIPIPE_BASE_URL: str = "https://aipipe.org/openrouter/v1"

    # ------------------------
    # SYSTEM UPGRADE CONFIG
    # ------------------------
    E2B_API_KEY: str | None = None
    LANGSMITH_API_KEY: str | None = None
    
    # Router Models
    MODEL_PRIMARY: str = "deepseek/deepseek-chat-v3-0324"
    MODEL_FALLBACK: str = "deepseek/deepseek-chat-v3-0324"
    MODEL_EXPENSIVE: str = "google/gemini-2.0-flash-001"

    LLM_CHAT_MODEL: str = MODEL_PRIMARY
    
    # Model Constants
    # Tier 1: Orchestrator (Speed & Multimodal)
    ORCHESTRATOR_MODEL: str = MODEL_PRIMARY
    # Tier 2: Worker (Deep Analysis)
    WORKER_MODEL: str = MODEL_FALLBACK
    # Audio Transcription
    AUDIO_MODEL: str = "google/gemini-2.0-flash-lite-001"

    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
