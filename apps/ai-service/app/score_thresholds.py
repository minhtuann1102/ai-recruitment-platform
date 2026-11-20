"""Nguong diem band 0-4 cho policy (luat 6/10), momentum topic sau va ket thuc som.

Mac dinh 1.5 / 3.0 hieu chinh theo thang cham cua gpt-4o-mini. Doi model Evaluator (vd gpt-6-luna cham cau ap ung cao
hon) thi chinh qua env POLICY_WEAK_BELOW / POLICY_STRONG_FROM, khong sua code. Gia tri la, NaN/inf hoac sai thu tu ->
ca cap ve mac dinh va log canh bao mot lan. Doc env moi lan goi (nhu POLICY_MODE) de sim / test doi duoc.
"""
import logging
import math
import os
from functools import lru_cache
from typing import Mapping, Optional, Tuple

DEFAULT_WEAK_BELOW, DEFAULT_STRONG_FROM = 1.5, 3.0
log = logging.getLogger("ai_service.policy")


def _num(raw: str, default: float) -> Optional[float]:
    if not raw.strip():
        return default
    try:
        v = float(raw)
    except ValueError:
        return None
    return v if math.isfinite(v) else None


@lru_cache(maxsize=8)
def _parse(raw_weak: str, raw_strong: str) -> Tuple[float, float]:
    """Cache theo chuoi env: canh bao cau hinh sai chi log mot lan."""
    weak, strong = _num(raw_weak, DEFAULT_WEAK_BELOW), _num(raw_strong, DEFAULT_STRONG_FROM)
    if weak is None or strong is None or not 0 < weak < strong <= 4:
        log.warning("policy_thresholds_invalid weak=%r strong=%r -> dung mac dinh %s / %s",
                    raw_weak, raw_strong, DEFAULT_WEAK_BELOW, DEFAULT_STRONG_FROM)
        return DEFAULT_WEAK_BELOW, DEFAULT_STRONG_FROM
    return weak, strong


def score_thresholds(env: Optional[Mapping[str, str]] = None) -> Tuple[float, float]:
    """(weak_below, strong_from): diem < weak_below la yeu, >= strong_from la manh. Can 0 < weak < strong <= 4."""
    env = os.environ if env is None else env
    return _parse(env.get("POLICY_WEAK_BELOW", ""), env.get("POLICY_STRONG_FROM", ""))
