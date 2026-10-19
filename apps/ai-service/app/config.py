"""Cau hinh ai-service doc tu bien moi truong (.env khi chay local)."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    llm_model: str
    embedding_model: str
    embedding_dimensions: int
    timeout_seconds: float


def load_settings() -> Settings:
    api_key = os.getenv("LLM_API_KEY", "").strip()
    if not api_key:
        raise ConfigError("LLM_API_KEY chua duoc dat. Copy .env.example thanh .env va dien key.")
    return Settings(
        api_key=api_key,
        base_url=os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1"),
        llm_model=os.getenv("LLM_MODEL", "openai/gpt-4o-mini"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small"),
        embedding_dimensions=int(os.getenv("EMBEDDING_DIMENSIONS", "1536")),
        timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
    )
