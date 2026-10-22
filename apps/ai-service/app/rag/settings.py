"""Cau hinh RAG tu bien moi truong. RAG tat mac dinh: khong co ai_db thi ai-service van chay (FR-AI-022)."""
import os
from dataclasses import dataclass
from typing import Mapping, Optional

from dotenv import load_dotenv

from ..llm.errors import ConfigError
from ..llm.settings import _flag

load_dotenv()


@dataclass(frozen=True)
class RagSettings:
    enabled: bool
    db_url: str
    embedding_model: str  # ten chuan luu trong cot embedding_model (khong tien to provider)
    connect_timeout_s: int


def stored_model_name(name: str) -> str:
    """'openai/text-embedding-3-small' -> 'text-embedding-3-small' (contract: ten khong tien to provider)."""
    return name.strip().split("/", 1)[-1]


def load_rag_settings(env: Optional[Mapping[str, str]] = None) -> RagSettings:
    env = os.environ if env is None else env
    enabled = _flag(env.get("RAG_ENABLED", ""), False)
    db_url = (env.get("AI_DB_URL") or "").strip()
    if enabled and not db_url:
        raise ConfigError("RAG_ENABLED=true nhung AI_DB_URL chua duoc dat")
    raw_timeout = env.get("AI_DB_CONNECT_TIMEOUT_S") or "3"
    try:
        timeout = int(raw_timeout)
    except ValueError:
        timeout = 0
    if timeout <= 0:  # libpq coi 0 la cho vo han
        raise ConfigError(f"AI_DB_CONNECT_TIMEOUT_S phai la so nguyen duong, nhan '{raw_timeout}'")
    return RagSettings(
        enabled=enabled,
        db_url=db_url,
        embedding_model=stored_model_name(env.get("EMBEDDING_MODEL") or "text-embedding-3-small"),
        connect_timeout_s=timeout,
    )
