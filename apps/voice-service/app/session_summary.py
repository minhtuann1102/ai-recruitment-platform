"""Tong hop chi so trinh bay cua ca phien (FR-011..013, data-model.md SessionDeliverySummary). Thuan code, khong LLM.

- stats (trung vi, nho nhat, lon nhat, n) chi cho chi so co it nhat mot gia tri; chi so rong o moi luot khong xuat hien
  o stats lan notes (khong bao 0).
- notes: 0-4 cau mau co dinh, trung tinh, thu tu quang ngung -> toc do -> tu dem -> thoi gian suy nghi; khong nhac diem
  kien thuc. Nguong lay tu Settings (chot sau khi do).
"""
from statistics import median
from typing import Dict, List, Optional, Sequence

from .config import Settings
from .models import MetricStats, SessionDeliverySummary, SummaryCounts, TurnDeliveryMetrics

# (ten chi so, so chu so thap phan khi tra ve): giay 2, am tiet / phut 1, ty le 3
STAT_FIELDS = (("thinking_time_s", 2), ("answer_duration_s", 2), ("speech_rate_spm", 1), ("filler_ratio", 3))


def _values(turns: Sequence[TurnDeliveryMetrics], name: str) -> List[float]:
    return [getattr(t, name) for t in turns if getattr(t, name) is not None]


def _stats(turns: Sequence[TurnDeliveryMetrics]) -> Dict[str, MetricStats]:
    stats = {}
    for name, digits in STAT_FIELDS:
        values = _values(turns, name)
        if values:
            stats[name] = MetricStats(median=round(median(values), digits), min=round(min(values), digits),
                                      max=round(max(values), digits), n=len(values))
    return stats


def _pause_note(turns: Sequence[TurnDeliveryMetrics], config: Settings) -> Optional[str]:
    known = _values(turns, "long_pause_count")
    with_pause = sum(1 for v in known if v >= 1)
    if with_pause and with_pause * 3 >= len(known):  # tu 1/3 so luot tro len
        return (f"{with_pause}/{len(known)} câu trả lời có quãng ngừng dài trên {config.long_pause_s:g} giây. "
                "Có thể thử dàn ý nhanh vài ý chính trước khi nói để giữ mạch liền hơn.")
    return None


def _rate_note(turns: Sequence[TurnDeliveryMetrics], config: Settings) -> Optional[str]:
    values = _values(turns, "speech_rate_spm")
    if not values:
        return None
    mid = median(values)
    if mid < config.rate_slow_spm or mid > config.rate_fast_spm:
        side = "chậm hơn" if mid < config.rate_slow_spm else "nhanh hơn"
        return (f"Tốc độ nói trung vị khoảng {mid:.0f} âm tiết/phút, {side} khoảng tham chiếu "
                f"{config.rate_slow_spm:.0f}-{config.rate_fast_spm:.0f} âm tiết/phút.")
    return None


def _filler_note(turns: Sequence[TurnDeliveryMetrics], config: Settings) -> Optional[str]:
    values = _values(turns, "filler_ratio")
    if values and median(values) > config.filler_note_ratio:
        return f"Từ đệm chiếm khoảng {median(values) * 100:.0f}% số âm tiết ở một câu trả lời điển hình (trung vị)."
    return None


def _thinking_note(turns: Sequence[TurnDeliveryMetrics], config: Settings) -> Optional[str]:
    values = _values(turns, "thinking_time_s")
    if values and median(values) > config.thinking_note_s:
        return f"Thời gian suy nghĩ trung vị khoảng {median(values):.0f} giây trước khi bắt đầu nói."
    return None


def summarize(turns: Sequence[TurnDeliveryMetrics], config: Settings) -> SessionDeliverySummary:
    limits = [t.over_limit for t in turns if t.over_limit is not None]
    counts = SummaryCounts(
        turns_with_long_pause=sum(1 for v in _values(turns, "long_pause_count") if v >= 1),
        turns_over_limit=sum(1 for v in limits if v),
        turns_with_limit=len(limits))
    notes = [n for n in (_pause_note(turns, config), _rate_note(turns, config), _filler_note(turns, config),
                         _thinking_note(turns, config)) if n]
    return SessionDeliverySummary(voice_turns=len(turns), stats=_stats(turns), counts=counts, notes=notes)
