"""Gia tri luu vao checkpoint cua phien (key lau dai cua graph, doc 12 G6). Luu dict JSON, khong luu object pydantic.

- session: track / level / duration_minutes (ghi o /start; thread chua co thi ghi o luot dau)
- plan: plan goc tu /start (topic doi nam trong state.swaps), chi ghi mot lan
- state: CandidateState sau luot; question: cau hoi da gui gan nhat (cau ma luot sau tra loi)
- transcript: moi luot mot phan tu nho {turn_number, question, answer, source} (channel cong don)
- last_turn: luot gan nhat du de replay (meta + done khong metadata). Chi giu MOT luot: blob khong phinh theo phien.
"""
import asyncio
import logging
from typing import Dict

from ..models_interview import NextTurnRequest, StartRequest
from ..turn_result import TurnResult, turn_payload
from .session_checkpointer import STORE_TIMEOUT_S, prune_memory_store, thread_config

log = logging.getLogger("ai_service.session_store")


def start_values(req: StartRequest, result: TurnResult) -> Dict:
    return {"session": {"track": req.track, "level": req.level, "duration_minutes": req.duration_minutes},
            "plan": result.plan.model_dump(mode="json"), "state": result.state.model_dump(mode="json"),
            "question": result.question, "last_turn": None}


def turn_values(stored: Dict, req: NextTurnRequest, result: TurnResult) -> Dict:
    """Ghi sau khi luot xong (node `record`): ca luot hoi tiep lan luot ket thuc phien."""
    out = {"state": result.state.model_dump(mode="json"),
           "transcript": [{"turn_number": req.turn_number, "question": req.question, "answer": req.answer,
                           "source": req.answer_source}],
           "last_turn": {"turn_number": req.turn_number, "answer": req.answer, "answer_source": req.answer_source,
                         "meta": result.meta or None, "done": turn_payload(result, mode="json")}}
    if result.question is not None:  # phien ket thuc: khong hoi them, giu cau cu
        out["question"] = result.question
    if not stored.get("session"):  # phien bat dau truoc khi bat luu phien (hoac store memory da restart)
        out["session"] = {"track": req.track, "level": req.level}
    if not stored.get("plan"):
        out["plan"] = req.plan.model_dump(mode="json")
    return out


async def record_start(graph, req: StartRequest, result: TurnResult) -> None:
    """/start xong (cau hoi dau da gui): xoa thread cu cung session_id (/start gui lai) roi ghi checkpoint dau.
    Ghi nhu node `record` vua chay: thread khong con viec do dang (next rong). Ghi loi thi chi log: /start van `done`
    (khong bat ung vien tra Planner + Interviewer lan nua), next-turn dau gap thread chua co thi chay tu request roi ghi."""
    async def write() -> None:
        await graph.checkpointer.adelete_thread(req.session_id)
        await graph.aupdate_state(thread_config(req.session_id), start_values(req, result), as_node="record")
        await prune_memory_store()
    try:
        await asyncio.wait_for(write(), 2 * STORE_TIMEOUT_S)
    except Exception as err:
        log.warning("session_start_not_recorded error=%s", type(err).__name__)
