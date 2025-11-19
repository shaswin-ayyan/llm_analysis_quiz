from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET: str = "changeme"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    OPENAI_BASE_URL: str = "https://aipipe.org/openai/v1"
    OPENAI_API_KEY: str | None = None
    LLM_CHAT_MODEL: str = "gpt-4.1-nano"
    LLM_FALLBACK_MODELS: List[str] = Field(default_factory=lambda: ["gemini-2.0-flash-lite"])

    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
