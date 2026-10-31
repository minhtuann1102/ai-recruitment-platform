"""Cau hinh LLM tu bien moi truong: ket noi chung + tham so theo agent (docs/ai-service/08 muc 9.3)."""
import os
from dataclasses import dataclass
from typing import Mapping, Optional

from dotenv import load_dotenv

from ..security import STRICT_ENVS
from .errors import ConfigError

load_dotenv()

AGENTS = ("cv_parser", "jd_parser", "planner", "evaluator", "interviewer", "reporter")
# Agent chi dung trong evals (ung vien gia lap, design 09 muc 10.2 tang 3); nen dat LLM_MODEL_SIMULATOR khac Evaluator
EVAL_AGENTS = ("simulator",)

# agent -> (temperature, max_tokens, timeout_s, seed, tong ngan sach retry s)
# Theo bang design 08 muc 9.3. jd_parser chua co trong design: dung thong so nhu cv_parser (gia dinh).
_DEFAULTS = {
    "cv_parser": (0.0, 1200, 20.0, None, None),
    "jd_parser": (0.0, 1200, 20.0, None, None),
    "planner": (0.4, 1500, 25.0, None, None),  # 1500: planner.v2 khong viet hint/backup (do 22/10: P50 13 s)
    "evaluator": (0.0, 400, 8.0, 7, 10.0),  # v5+ cho phep 4 y covered kem nguon; 400 de khong bi cat
    "interviewer": (0.7, 200, 5.0, None, None),
    "reporter": (0.3, 2000, 60.0, None, None),
    "simulator": (0.8, 500, 20.0, None, None),  # 350 cat cau tra loi tieng Anh dai (persona english_answers, 24/10)
    "judge": (0.0, 300, 20.0, 7, None),  # evals: LLM-as-judge cho cau hoi Interviewer (evals/judge_interviewer.py)
    "query_rewriter": (0.0, 60, 3.0, None, 0.0),  # viet lai truy van RAG (ADR-010): 3 s, khong retry; loi -> tu dien
}


@dataclass(frozen=True)
class LlmSettings:
    api_key: str
    base_url: str
    default_model: str
    embedding_model: str
    embedding_dimensions: int
    structured_outputs: bool
    log_io: bool


@dataclass(frozen=True)
class AgentSettings:
    agent: str
    model: str
    temperature: float
    max_tokens: int
    timeout_s: float
    seed: Optional[int]
    retry_budget_s: Optional[float]


def _flag(value: str, default: bool) -> bool:
    value = (value or "").strip().lower()
    return default if not value else value in ("1", "true", "yes", "on")


def load_llm_settings(env: Optional[Mapping[str, str]] = None) -> LlmSettings:
    env = os.environ if env is None else env
    api_key = (env.get("LLM_API_KEY") or "").strip()
    if not api_key:
        raise ConfigError("LLM_API_KEY chua duoc dat. Copy .env.example thanh .env va dien key.")
    return LlmSettings(
        api_key=api_key,
        base_url=env.get("LLM_BASE_URL") or "https://openrouter.ai/api/v1",
        default_model=env.get("LLM_MODEL") or "openai/gpt-4o-mini",
        embedding_model=env.get("EMBEDDING_MODEL") or "openai/text-embedding-3-small",
        embedding_dimensions=int(env.get("EMBEDDING_DIMENSIONS") or 1536),
        structured_outputs=_flag(env.get("LLM_STRUCTURED_OUTPUTS", ""), True),
        # noi dung prompt / output chi duoc ghi log o may dev (docs 07 muc 8.6): staging / production bo qua co nay
        log_io=_flag(env.get("LOG_LLM_IO", ""), False) and env.get("APP_ENV", "dev").lower() not in STRICT_ENVS,
    )


def agent_settings(agent: str, llm: LlmSettings, env: Optional[Mapping[str, str]] = None) -> AgentSettings:
    if agent not in _DEFAULTS:
        raise ConfigError(f"agent khong hop le: {agent}")
    env = os.environ if env is None else env
    temperature, max_tokens, timeout_s, seed, budget = _DEFAULTS[agent]
    model = env.get(f"LLM_MODEL_{agent.upper()}") or llm.default_model
    return AgentSettings(agent, model, temperature, max_tokens, timeout_s, seed, budget)
