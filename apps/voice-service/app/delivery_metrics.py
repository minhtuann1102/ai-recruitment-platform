"""Chi so trinh bay cua mot luot (FR-006, research R5): thuan code, tat dinh, khong goi nha cung cap.

Nguon moc thoi gian (spike 2026-11-25): moc theo TU cua STT (`words`); VAD tho nen chi la cong "co tieng" truoc STT. Neu
STT khong tra `words` (vd blaze-stt-1.0) thi dung cac doan VAD, cung cong thuc. Ca hai deu la danh sach (start, end) giay
tinh tu dau file ("timings"). Dau vao khac: ban ghi GOC (FR-007), hai moc client (epoch giay, da parse), gioi han thoi gian.

- answer_duration_s = end lon nhat - start dau tien.
- quang ngung dai = khoang trong giua hai moc lien nhau >= long_pause_s.
- speech_time_s = answer_duration_s - tong cac quang ngung dai.
- speech_rate_spm = so token cua ban ghi / speech_time_s x 60; rong khi speech_time_s < 3 s (cau qua ngan cho toc do
  ao: mot tu 0.2 s ra 300 am tiet / phut, keo lech trung vi cua phien).
- over_limit so sanh answer_duration_s DA lam tron (so ung vien thay) voi gioi han.
- thinking_time_s = (bat dau ghi - cau hoi doc xong) + start dau tien.
Lam tron: giay 2 chu so, am tiet / phut 1, ty le 3.
"""
from typing import List, Optional, Sequence, Tuple

from .config import Settings
from .models import SpeechSegment, TurnDeliveryMetrics
from .transcript_tokens import count_fillers, tokens

Timing = Tuple[float, float]  # (start, end) giay
MAX_CLIENT_SKEW_S = 600.0  # hai moc lech qua 10 phut = khong hop le (data-model.md)
MIN_RATE_SPEECH_S = 3.0  # duoi muc nay khong tinh toc do noi
MIN_SPAN_S = 0.01  # doan chi co mot tu dai 0 giay van thanh doan hop le cua response
WARN_INVALID_TIMESTAMPS = "invalid_client_timestamps"
WARN_FILLERS_UNSUPPORTED = "fillers_unsupported"


def _split_at_long_pauses(timings: Sequence[Timing], long_pause_s: float) -> Tuple[List[Timing], List[float]]:
    """(cac doan lien tuc, danh sach do dai quang ngung dai). Moc chong nhau duoc gop; so khop theo end lon nhat so far."""
    spans: List[List[float]] = []
    pauses: List[float] = []
    for start, end in sorted(timings):
        # round(.., 3): tranh sai so nhi phan lam quang ngung dung 2.0 bi tinh thieu
        if spans and round(start - spans[-1][1], 3) >= long_pause_s:
            pauses.append(start - spans[-1][1])
            spans.append([start, end])
        elif spans:
            spans[-1][1] = max(spans[-1][1], end)
        else:
            spans.append([start, end])
    return [(s, e) for s, e in spans], pauses


def speech_spans(timings: Sequence[Timing], long_pause_s: float) -> List[SpeechSegment]:
    """Cac doan co tieng cua response: cat o quang ngung dai (contract: [{start, end}])."""
    spans, _ = _split_at_long_pauses(timings, long_pause_s)
    return [SpeechSegment(start=s, end=max(e, s + MIN_SPAN_S)) for s, e in spans]


def _thinking_time(question_ended_at: Optional[float], recording_started_at: Optional[float], first_start: float,
                   warnings: List[str]) -> Optional[float]:
    """Khong gui ca hai moc = rong, khong canh bao; thieu mot moc, moc nguoc hoac lech qua 10 phut = rong + canh bao
    (khong bao loi ca request)."""
    if question_ended_at is None and recording_started_at is None:
        return None
    if question_ended_at is None or recording_started_at is None:
        warnings.append(WARN_INVALID_TIMESTAMPS)
        return None
    gap = recording_started_at - question_ended_at
    if gap < 0 or gap > MAX_CLIENT_SKEW_S:
        warnings.append(WARN_INVALID_TIMESTAMPS)
        return None
    return round(gap + first_start, 2)


def compute_turn_metrics(transcript: str, timings: Sequence[Timing], question_ended_at: Optional[float],
                         recording_started_at: Optional[float], answer_limit_s: Optional[float],
                         topic_id: Optional[str], config: Settings) -> Tuple[TurnDeliveryMetrics, List[str]]:
    """TurnDeliveryMetrics + canh bao. Khong co moc nao: moi chi so rong (chi con topic_id)."""
    warnings: List[str] = []
    if not timings:
        return TurnDeliveryMetrics(topic_id=topic_id), warnings

    first_start = min(s for s, _ in timings)
    duration = max(e for _, e in timings) - first_start
    _, pauses = _split_at_long_pauses(timings, config.long_pause_s)
    speech_time = max(0.0, duration - sum(pauses))
    syllables = tokens(transcript)
    rate = None
    if syllables and speech_time >= MIN_RATE_SPEECH_S:
        rate = round(len(syllables) / speech_time * 60, 1)

    filler_ratio = None
    if not config.fillers_supported:
        warnings.append(WARN_FILLERS_UNSUPPORTED)
    elif syllables:
        filler_ratio = round(min(1.0, count_fillers(syllables, config.fillers) / len(syllables)), 3)

    metrics = TurnDeliveryMetrics(
        topic_id=topic_id,
        thinking_time_s=_thinking_time(question_ended_at, recording_started_at, first_start, warnings),
        answer_duration_s=round(duration, 2),
        over_limit=None if answer_limit_s is None else round(duration, 2) > answer_limit_s,
        speech_time_s=round(speech_time, 2),
        speech_rate_spm=rate,
        long_pause_count=len(pauses),
        filler_ratio=filler_ratio,
    )
    return metrics, warnings
