"""Kiem luot next-turn voi checkpoint truoc khi chay graph (doc 12 G7), va replay luot da xong.

So voi state luu (turn_count = so luot cua cau hoi dang cho tra loi):
- cung turn_number + cung answer voi luot gan nhat -> replay (tra lai dung `done` cu, khong goi Evaluator / LLM)
- phien done -> 409 session_invalid_state; cung turn_number, answer khac -> 409 turn_already_answered
- turn_number != turn_count -> 409 turn_out_of_order
- thread chua co -> chay binh thuong tu request roi ghi (phase 04 moi tra 404)
Doc checkpoint loi -> 503 session_store_unavailable (retryable), khong lui ve state request (hai nguon su that).
Pha song song: van chay tu plan / state cua request; lech voi checkpoint thi log session_state_mismatch (chi ten truong).
"""
import asyncio
import logging
from typing import AsyncIterator, Dict, List, Optional, Tuple

from ..api_error import ApiError
from ..models_interview import NextTurnRequest
from .session_checkpointer import STORE_TIMEOUT_S, thread_config

log = logging.getLogger("ai_service.session_store")


async def stored_values(graph, session_id: str) -> Dict:
    try:
        snap = await asyncio.wait_for(graph.aget_state(thread_config(session_id)), STORE_TIMEOUT_S)
    except Exception as err:  # TimeoutError khi DB treo: tra 503 nhanh, khong giu khoa phien
        log.warning("session_store_unavailable error=%s", type(err).__name__)
        raise ApiError(503, "session_store_unavailable", "Không đọc được trạng thái phiên", {"retryable": True})
    return snap.values or {}


def _same_answer(last: Dict, req: NextTurnRequest) -> bool:
    return last.get("answer") == req.answer and last.get("answer_source") == req.answer_source


def mismatched_fields(stored: Dict, req: NextTurnRequest) -> List[str]:
    """Ten truong lech giua checkpoint va request (khong ghi gia tri: co cau tra loi cua ung vien)."""
    fields = []
    state, want = stored.get("state") or {}, req.state.model_dump(mode="json")
    fields += [f"state.{k}" for k in sorted(set(state) | set(want)) if state.get(k) != want.get(k)]
    if stored.get("plan") and stored["plan"] != req.plan.model_dump(mode="json"):
        fields.append("plan")
    if stored.get("question") is not None and stored["question"] != req.question:
        fields.append("question")
    return fields


async def check_turn(graph, req: NextTurnRequest) -> Optional[Dict]:
    """None: chay luot. Dict: luot da xong, tra lai (last_turn). Nem ApiError 409 / 503."""
    stored = await stored_values(graph, req.session_id)
    if not stored.get("state"):
        log.info("session_thread_missing turn=%d", req.turn_number)
        return None
    last, state = stored.get("last_turn"), stored["state"]
    if last and last["turn_number"] == req.turn_number and _same_answer(last, req):
        log.info("session_turn_replayed turn=%d", req.turn_number)
        return last
    if state.get("phase") == "done":  # sau replay: luot ket thuc phien gui lai van replay duoc
        raise ApiError(409, "session_invalid_state", "Phiên đã kết thúc")
    if last and last["turn_number"] == req.turn_number:
        raise ApiError(409, "turn_already_answered", "Lượt này đã được trả lời", {"turn_number": req.turn_number})
    if req.turn_number != state.get("turn_count"):
        raise ApiError(409, "turn_out_of_order", "turn_number không khớp lượt đang chờ trả lời",
                       {"expected_turn_number": state.get("turn_count"), "turn_number": req.turn_number})
    fields = mismatched_fields(stored, req)
    if fields:
        log.warning("session_state_mismatch turn=%d fields=%s", req.turn_number, ",".join(fields))
    return None


async def replay_events(last: Dict) -> AsyncIterator[Tuple[str, dict]]:
    """meta -> token (ca cau, mot lan) truoc `done`; phien ket thuc thi khong co cau hoi."""
    if last.get("meta"):
        yield "meta", last["meta"]
    question = last["done"].get("question")
    if question:
        yield "token", {"t": question}
