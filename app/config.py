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
    # AIPipe / OpenAI-compatible
    # ------------------------
    OPENAI_BASE_URL: str = "https://aipipe.org/openai/v1"
    OPENAI_API_KEY: str | None = None
    
    # AI Pipe Proxy
    AIPIPE_PROXY_URL: str = "https://aipipe.org/proxy"

    LLM_CHAT_MODEL: str = "gpt-4.1-nano"
    
    # Model Constants
    # Tier 1: Orchestrator (Speed)
    ORCHESTRATOR_MODEL: str = "gpt-4.1-nano"
    # Tier 2: Worker (Deep Analysis)
    WORKER_MODEL: str = "gemini-2.0-flash-lite"

    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
