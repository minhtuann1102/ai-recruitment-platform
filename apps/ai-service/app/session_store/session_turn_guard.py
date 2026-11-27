"""Kiem luot next-turn voi checkpoint truoc khi chay graph (doc 12 G7), va replay luot da xong.

So voi state luu (turn_count = so luot cua cau hoi dang cho tra loi):
- cung turn_number + cung answer voi luot gan nhat -> replay (tra lai dung `done` cu, khong goi Evaluator / LLM)
- phien done -> 409 session_invalid_state; cung turn_number, answer khac -> 409 turn_already_answered
- turn_number != turn_count -> 409 turn_out_of_order
- thread chua co, hoac cu (thieu `session` / `turn`, log session_schema_outdated) -> 404 session_not_found
Doc checkpoint loi -> 503 session_store_unavailable (retryable), khong lui ve state request (hai nguon su that).
"""
import asyncio
import logging
from typing import AsyncIterator, Dict, Optional, Tuple

from ..api_error import ApiError
from ..models_interview_http import NextTurnBody
from .session_checkpointer import STORE_TIMEOUT_S, thread_config

log = logging.getLogger("ai_service.session_store")


async def stored_values(graph, session_id: str) -> Dict:
    """Checkpoint cua phien. Loi doc -> 503 (retryable); thread chua co -> 404 session_not_found."""
    try:
        snap = await asyncio.wait_for(graph.aget_state(thread_config(session_id)), STORE_TIMEOUT_S)
    except Exception as err:  # TimeoutError khi DB treo: tra 503 nhanh, khong giu khoa phien
        log.warning("session_store_unavailable error=%s", type(err).__name__)
        raise ApiError(503, "session_store_unavailable", "Không đọc được trạng thái phiên", {"retryable": True})
    values = snap.values or {}
    if not values.get("state"):
        log.info("session_not_found")
        raise ApiError(404, "session_not_found", "Không tìm thấy phiên phỏng vấn")
    if not values.get("session") or not values.get("turn"):  # thread ghi truoc phase 04: thieu truong de dung request
        log.warning("session_schema_outdated")
        raise ApiError(404, "session_not_found", "Không tìm thấy phiên phỏng vấn")
    return values


def _same_answer(last: Dict, req: NextTurnBody) -> bool:
    return last.get("answer") == req.answer and last.get("answer_source") == req.answer_source


async def check_turn(stored: Dict, body: NextTurnBody) -> Optional[Dict]:
    """`stored`: checkpoint cua phien (stored_values, da co state). None: chay luot. Dict: luot da xong, tra lai
    (last_turn). Nem ApiError 409."""
    last, state = stored.get("last_turn"), stored["state"]
    if last and last["turn_number"] == body.turn_number and _same_answer(last, body):
        log.info("session_turn_replayed turn=%d", body.turn_number)
        return last
    if state.get("phase") == "done":  # sau replay: luot ket thuc phien gui lai van replay duoc
        raise ApiError(409, "session_invalid_state", "Phiên đã kết thúc")
    if last and last["turn_number"] == body.turn_number:
        raise ApiError(409, "turn_already_answered", "Lượt này đã được trả lời", {"turn_number": body.turn_number})
    if body.turn_number != state.get("turn_count"):
        raise ApiError(409, "turn_out_of_order", "turn_number không khớp lượt đang chờ trả lời",
                       {"expected_turn_number": state.get("turn_count"), "turn_number": body.turn_number})
    return None


async def replay_events(last: Dict) -> AsyncIterator[Tuple[str, dict]]:
    """meta -> token (ca cau, mot lan) truoc `done`; phien ket thuc thi khong co cau hoi."""
    if last.get("meta"):
        yield "meta", last["meta"]
    question = last["done"].get("question")
    if question:
        yield "token", {"t": question}
