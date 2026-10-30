"""Cau hinh RAG tu bien moi truong. RAG bat mac dinh; cau hinh sai hay ai_db loi thi phien chay khong co RAG va
response bao loi trong metadata.rag (plan_snippets.rag_status), ai-service van chay (FR-AI-022)."""
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
    textbook_enabled: bool = False  # bat khi DE da nap textbook vao knowledge_chunks
    query_rewrite: bool = True  # LLM viet lai truy van sang tieng Anh o duong vector (+~1.6 s, chi khi can vector)
    question_bank: bool = True  # cau hoi chinh phan technical lay tu kho interview_qa (app/rag/question_bank.py)
    cooldown_s: int = 60  # RAG loi lap lai thi khong goi ai_db trong N giay (rag/circuit_breaker.py); 0 = khong ngat
    hybrid: bool = True  # tu khoa + vector + topic_id gop RRF (app/rag/hybrid_search.py); false: duong cu
    turn_retrieval: bool = True  # moi next-turn tim them chunk BM25 theo cau hoi + tra loi (can hybrid)


def stored_model_name(name: str) -> str:
    """'openai/text-embedding-3-small' -> 'text-embedding-3-small' (contract: ten khong tien to provider)."""
    return name.strip().split("/", 1)[-1]


def load_rag_settings(env: Optional[Mapping[str, str]] = None) -> RagSettings:
    env = os.environ if env is None else env
    enabled = _flag(env.get("RAG_ENABLED", ""), True)
    db_url = (env.get("AI_DB_URL") or "").strip()
    if enabled and not db_url:
        raise ConfigError("RAG bat (mac dinh) nhung AI_DB_URL chua duoc dat; dat RAG_ENABLED=false de tat han")
    raw_timeout = env.get("AI_DB_CONNECT_TIMEOUT_S") or "3"
    try:
        timeout = int(raw_timeout)
    except ValueError:
        timeout = 0
    if timeout <= 0:  # libpq coi 0 la cho vo han
        raise ConfigError(f"AI_DB_CONNECT_TIMEOUT_S phai la so nguyen duong, nhan '{raw_timeout}'")
    raw_cooldown = env.get("RAG_COOLDOWN_S") or "60"
    try:
        cooldown = int(raw_cooldown)
    except ValueError:
        cooldown = -1
    if cooldown < 0:
        raise ConfigError(f"RAG_COOLDOWN_S phai la so nguyen >= 0, nhan '{raw_cooldown}'")
    return RagSettings(
        enabled=enabled,
        db_url=db_url,
        embedding_model=stored_model_name(env.get("EMBEDDING_MODEL") or "text-embedding-3-small"),
        connect_timeout_s=timeout,
        textbook_enabled=_flag(env.get("RAG_TEXTBOOK_ENABLED", ""), False),
        query_rewrite=_flag(env.get("RAG_QUERY_REWRITE", ""), True),
        question_bank=_flag(env.get("RAG_QUESTION_BANK", ""), True),
        cooldown_s=cooldown,
        hybrid=_flag(env.get("RAG_HYBRID", ""), True),
        turn_retrieval=_flag(env.get("RAG_TURN_RETRIEVAL", ""), True),
    )
