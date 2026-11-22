"""Cau hinh goi y viec lam tu bien moi truong (contract match-jobs-api.md muc Cau hinh).

Khong phu thuoc RAG_ENABLED. Khong bao gio doi AI_DB_URL hay LLM_API_KEY o day: chi muc khong doc duoc ai_db thi
request tra 503 match_index_unavailable (job_index), khong lam app khong khoi dong duoc. Chi sai MATCH_WEIGHTS va
cac so sai la ConfigError ("service tu choi khoi dong", spec Edge Cases).
"""
import math
import os
from dataclasses import dataclass
from typing import Callable, Mapping, Optional, TypeVar

from ..llm.errors import ConfigError
from ..llm.settings import _flag
from ..rag.settings import stored_model_name

DEFAULT_WEIGHTS = "0.6,0.3,0.1"
WEIGHTS_SUM_TOLERANCE = 1e-6

T = TypeVar("T")


@dataclass(frozen=True)
class MatchWeights:
    cosine: float
    skill_match: float
    level_fit: float


@dataclass(frozen=True)
class MatchSettings:
    mock: bool
    weights: MatchWeights
    max_level_gap: int
    max_results: int
    index_refresh_s: int
    embed_timeout_s: float
    db_url: str  # rong = chua cau hinh: nap chi muc se bao match_index_unavailable
    connect_timeout_s: int
    embedding_model: str  # ten chuan luu trong cot embedding_model (khong tien to provider)


def parse_weights(raw: str) -> MatchWeights:
    """'cosine,skill_match,level_fit': dung 3 so huu han, moi so >= 0, tong bang 1 (sai so 1e-6)."""
    try:
        values = [float(part) for part in raw.split(",")]
    except ValueError:
        raise ConfigError(f"MATCH_WEIGHTS phai la 3 so cach nhau dau phay, nhan '{raw}'") from None
    if len(values) != 3 or not all(math.isfinite(v) for v in values):  # nan / inf lot qua cac so sanh duoi
        raise ConfigError(f"MATCH_WEIGHTS phai la 3 so huu han (cosine,skill_match,level_fit), nhan '{raw}'")
    if any(v < 0 for v in values):
        raise ConfigError(f"MATCH_WEIGHTS khong duoc am, nhan '{raw}'")
    if abs(sum(values) - 1.0) > WEIGHTS_SUM_TOLERANCE:
        raise ConfigError(f"MATCH_WEIGHTS phai cong bang 1, nhan '{raw}' (tong {sum(values)})")
    return MatchWeights(*values)


def _number(env: Mapping[str, str], name: str, default: str, cast: Callable[[str], T], ok: Callable[[T], bool],
            rule: str) -> T:
    raw = (env.get(name) or "").strip() or default
    try:
        value = cast(raw)
    except ValueError:
        raise ConfigError(f"{name} phai {rule}, nhan '{raw}'") from None
    if isinstance(value, float) and not math.isfinite(value) or not ok(value):
        raise ConfigError(f"{name} phai {rule}, nhan '{raw}'")
    return value


def load_match_settings(env: Optional[Mapping[str, str]] = None) -> MatchSettings:
    env = os.environ if env is None else env
    return MatchSettings(
        mock=_flag(env.get("MATCH_MOCK", ""), False),
        weights=parse_weights((env.get("MATCH_WEIGHTS") or "").strip() or DEFAULT_WEIGHTS),
        max_level_gap=_number(env, "MATCH_MAX_LEVEL_GAP", "1", int, lambda v: v >= 0, "la so nguyen >= 0"),
        max_results=_number(env, "MATCH_MAX_RESULTS", "50", int, lambda v: v >= 1, "la so nguyen >= 1"),
        index_refresh_s=_number(env, "MATCH_INDEX_REFRESH_S", "300", int, lambda v: v >= 1, "la so nguyen >= 1"),
        embed_timeout_s=_number(env, "MATCH_EMBED_TIMEOUT_S", "5", float, lambda v: v > 0, "la so > 0"),
        db_url=(env.get("AI_DB_URL") or "").strip(),
        # libpq coi 0 la cho vo han nen phai > 0 (giong rag/settings.py)
        connect_timeout_s=_number(env, "AI_DB_CONNECT_TIMEOUT_S", "3", int, lambda v: v > 0, "la so nguyen duong"),
        embedding_model=stored_model_name(env.get("EMBEDDING_MODEL") or "text-embedding-3-small"),
    )
