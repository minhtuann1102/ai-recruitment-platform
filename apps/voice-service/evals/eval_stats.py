"""Thong ke cua bo do voice (spec 015 T027): phan vi, gop loi nhan dang / thuat ngu, uoc tinh credit (SC-001..003, 007).

Ham thuan, khong goi mang: test duoc offline (SC-006).
"""
import math
from statistics import mean, median
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

# Muc do dai cau (giay) cho SC-001: <= 30 s thi p95 <= 10 s, <= 90 s thi p95 <= 20 s
LATENCY_BUCKETS: Tuple[Tuple[str, float, float], ...] = (("≤ 30 s", 30.0, 10.0), ("30–90 s", 90.0, 20.0))
TTS_FIRST_BYTE_TARGET_S = 1.5  # SC-003
TERM_TARGET = 0.85  # SC-002


def percentile(values: Sequence[float], pct: float) -> Optional[float]:
    """Phan vi theo hang gan nhat (nearest-rank): mau nho thi p95 ~ gia tri lon nhat, khong noi suy."""
    ordered = sorted(values)
    if not ordered:
        return None
    rank = max(1, math.ceil(pct / 100 * len(ordered)))
    return ordered[rank - 1]


def bucket_of(duration_s: Optional[float]) -> Optional[str]:
    if duration_s is None:
        return None
    for name, upper, _ in LATENCY_BUCKETS:
        if duration_s <= upper:
            return name
    return "> 90 s"


def latency_table(samples: Iterable[Tuple[Optional[float], float]], failures: int = 0) -> List[Dict]:
    """samples: (do dai cau uoc luong, thoi gian nhan ban ghi) cua lan co keywords thanh cong. Moi muc: n, p50, p95,
    nguong, dat? Co lan loi (timeout, 5xx: thuong la lan cham nhat, khong biet do dai) -> khong ket luan (None)."""
    grouped: Dict[str, List[float]] = {}
    for duration, elapsed in samples:
        name = bucket_of(duration)
        if name:
            grouped.setdefault(name, []).append(elapsed)
    rows = []
    for name, _, target in LATENCY_BUCKETS:
        values = grouped.get(name, [])
        p95 = percentile(values, 95)
        rows.append({"bucket": name, "n": len(values), "p50": percentile(values, 50), "p95": p95, "target": target,
                     "passed": None if p95 is None or failures else p95 <= target})
    if grouped.get("> 90 s"):
        values = grouped["> 90 s"]
        rows.append({"bucket": "> 90 s", "n": len(values), "p50": percentile(values, 50),
                     "p95": percentile(values, 95), "target": None, "passed": None})
    return rows


def recognition_summary(rows: List[Dict]) -> Dict:
    """rows: {ser, edits, ref_tokens, terms_found, terms_total} cua cac clip read trong mot che do. `ser_pooled` =
    tong loi / tong token ban chuan (clip dai nang ky hon, khong bi clip weak ngan lan at nhu trung binh tung clip)."""
    sers = [r["ser"] for r in rows]
    found = sum(r["terms_found"] for r in rows)
    total = sum(r["terms_total"] for r in rows)
    ref = sum(r["ref_tokens"] for r in rows)
    return {"clips": len(rows), "ser_mean": mean(sers) if sers else None, "ser_median": median(sers) if sers else None,
            "ser_pooled": sum(r["edits"] for r in rows) / ref if ref else None,
            "terms_found": found, "terms_total": total, "term_rate": found / total if total else None}


def stt_credit(audio_seconds: float, pricing: Dict) -> float:
    return audio_seconds / 60 * pricing["stt_credit_per_min"]


def session_credit(pricing: Dict) -> Dict:
    """Uoc tinh credit mot phien theo gia dinh trong pricing.json (SC-007)."""
    a = pricing["session_assumptions"]
    stt = a["candidate_speech_min"] * pricing["stt_credit_per_min"]
    tts = a["question_audio_min"] / 60 * pricing["tts_credit_per_hour_audio"]
    return {"session_min": a["session_min"], "stt": stt, "tts": tts, "total": stt + tts}


def fmt(value: Optional[float], digits: int = 2, suffix: str = "") -> str:
    return "–" if value is None else f"{value:.{digits}f}{suffix}"


def pct(value: Optional[float]) -> str:
    return "–" if value is None else f"{value * 100:.1f}%"
