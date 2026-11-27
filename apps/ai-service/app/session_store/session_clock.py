"""Dong ho phien phia server va dieu kien duoc tong ket (finalize) phien.

Truoc phase 04 thoi gian phien chi dua vao `elapsed_seconds` client gui: gui 0 mai thi phien khong bao gio het gio.
Gio /start ghi `session.started_at` (epoch giay, dong ho server); moi luot dung
elapsed = max(elapsed client gui, elapsed luot truoc da luu, thoi gian thuc tu /start). Client van day nhanh duoc
(dev-play dong ho gia lap, evals.simulate) nhung khong lui hay dung duoc dong ho. Thread khong co `started_at`
(seed trong test) thi chi dung hai gia tri dau.

Finalize chi cho phep khi phien da `done`, tru hai truong hop phien chua done nhung phai tong ket duoc:
ung vien bam ket thuc (`candidate_ended`) va phien da qua han cung (ung vien bo di, khong goi next-turn nua).
Con lai -> 409 session_not_done.
"""
import time
from typing import Dict, List, Optional

from ..api_error import ApiError
from ..models_interview import InterviewPlan
from ..time_budget import HARD_LIMIT_EXTRA_S, duration_s

CANDIDATE_ENDED = "candidate_ended"


def server_elapsed(stored: Dict, now: Optional[float] = None) -> Optional[int]:
    """Giay tu /start theo dong ho server; None neu thread khong co started_at."""
    started = (stored.get("session") or {}).get("started_at")
    if started is None:
        return None
    return max(0, int((time.time() if now is None else now) - started))


def effective_elapsed(body_elapsed: int, stored: Dict, now: Optional[float] = None) -> int:
    transcript: List[Dict] = stored.get("transcript") or []
    last = max((t.get("elapsed_seconds") or 0 for t in transcript), default=0)
    return max(body_elapsed, last, server_elapsed(stored, now) or 0)


def finalize_end_reason(stored: Dict, body_end_reason: str, now: Optional[float] = None) -> str:
    """end_reason cua bao cao, hoac 409 session_not_done. Phien done: end_reason da luu thang (body chi dung khi
    state luu chua co)."""
    state = stored["state"]
    if state.get("phase") == "done":
        return state.get("end_reason") or body_end_reason
    if body_end_reason == CANDIDATE_ENDED:
        return CANDIDATE_ENDED
    elapsed = server_elapsed(stored, now)
    if elapsed is not None and elapsed >= duration_s(InterviewPlan.model_validate(stored["plan"])) + HARD_LIMIT_EXTRA_S:
        return "time_hard_limit"
    raise ApiError(409, "session_not_done", "Phiên chưa kết thúc, chưa tổng kết được",
                   {"phase": state.get("phase"), "allowed_early_end_reason": CANDIDATE_ENDED})
