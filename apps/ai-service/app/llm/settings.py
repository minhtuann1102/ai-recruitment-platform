"""Cau hinh LLM tu bien moi truong: ket noi chung + tham so theo agent (docs/ai-service/08 muc 9.3)."""
import math
import os
from dataclasses import dataclass
from typing import Mapping, Optional
from urllib.parse import urlparse

from dotenv import load_dotenv

from ..security import STRICT_ENVS
from .errors import ConfigError

load_dotenv()

AGENTS = ("cv_parser", "jd_parser", "planner", "evaluator", "interviewer", "reporter")
# Agent chi dung trong evals (ung vien gia lap, design 09 muc 10.2 tang 3); nen dat LLM_MODEL_SIMULATOR khac Evaluator
EVAL_AGENTS = ("simulator",)

# agent -> (temperature, max_tokens, timeout_s, seed, tong ngan sach retry s)
# timeout_s: han tong moi lan goi, gateway cat bang asyncio. Agent duoc interview-service cho toi da N s (docs 06)
# phai co ngan sach < N, neu khong retry chay qua han do va fallback khong ve kip. Ngan sach tinh ca repair va length.
# Theo bang design 08 muc 9.3. jd_parser chua co trong design: dung thong so nhu cv_parser (gia dinh).
_DEFAULTS = {
    "cv_parser": (0.0, 1200, 20.0, None, 28.0),
    "jd_parser": (0.0, 1200, 20.0, None, 28.0),
    "planner": (0.4, 1500, 25.0, None, None),  # 1500: planner.v2 khong viet hint/backup (do 22/10: P50 13 s)
    "evaluator": (0.0, 400, 8.0, 7, 10.0),  # v5 cho phep 4 y covered kem nguon; 400 de khong bi cat
    "interviewer": (0.7, 200, 5.0, None, None),
    "reporter": (0.3, 2000, 60.0, None, 80.0),
    "simulator": (0.8, 500, 20.0, None, None),  # 350 cat cau tra loi tieng Anh dai (persona english_answers, 24/10)
    "judge": (0.0, 300, 20.0, 7, None),  # evals: LLM-as-judge cho cau hoi Interviewer (evals/judge_interviewer.py)
    "query_rewriter": (0.0, 60, 3.0, None, 0.0),  # viet lai truy van RAG (ADR-010): 3 s, khong retry; loi -> tu dien
}
# Hedge (docs 08 muc 9.2): LLM_HEDGE_<AGENT> = so giay; sau N s chua co ket qua thi gui them mot request, lay ket qua ve
# truoc. Mac dinh tat: do 09/11 Evaluator hedge sau 5 s ban 9/176 lan goi, cuu duoc 0 (luot treo thi ca hai cung treo).
# LLM_REASONING_<AGENT>: model co reasoning (gpt-5-nano, gpt-6-luna...) mac dinh tu suy nghi, ton token ra va bi cat
# max_tokens (do 03/11). off = tat han, con lai la effort cua OpenRouter. Khong dat thi khong gui gi (nhu cu).
REASONING_LEVELS = ("off", "minimal", "low", "medium", "high")


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
    reasoning: Optional[str] = None
    hedge_after_s: Optional[float] = None


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
    reasoning = (env.get(f"LLM_REASONING_{agent.upper()}") or "").strip().lower() or None
    if reasoning is not None and reasoning not in REASONING_LEVELS:
        raise ConfigError(f"LLM_REASONING_{agent.upper()} khong hop le: {reasoning} "
                          f"(chon {'/'.join(REASONING_LEVELS)})")
    return AgentSettings(agent, model, temperature, max_tokens, timeout_s, seed, budget, reasoning,
                         _hedge_after(agent, env))


def _hedge_after(agent: str, env: Mapping[str, str]) -> Optional[float]:
    raw = (env.get(f"LLM_HEDGE_{agent.upper()}") or "").strip().lower()
    if raw in ("", "0", "off"):
        return None
    try:
        value = float(raw)
    except ValueError:
        value = -1.0
    if not math.isfinite(value) or value <= 0:
        raise ConfigError(f"LLM_HEDGE_{agent.upper()} khong hop le: {raw} (so giay > 0, hoac 0 / off de tat)")
    return value


def reasoning_body(level: Optional[str]) -> dict:
    """Tham so `reasoning` cua OpenRouter (gui qua extra_body); rong khi khong cau hinh."""
    if level is None:
        return {}
    return {"extra_body": {"reasoning": {"enabled": False} if level == "off" else {"effort": level}}}


def merge_extra_body(base: dict, extra: dict) -> None:
    """Gop `extra` vao base["extra_body"] (giu khoa da co, vd reasoning)."""
    base["extra_body"] = {**base.get("extra_body", {}), **extra}


def is_openrouter(base_url: str) -> bool:
    """`provider.require_parameters` chi OpenRouter hieu; endpoint OpenAI goc se bao loi tham so la."""
    host = (urlparse(base_url or "").hostname or "").lower()
    return host == "openrouter.ai" or host.endswith(".openrouter.ai")
