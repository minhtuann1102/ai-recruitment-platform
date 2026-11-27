"""Gia tri luu vao checkpoint cua phien (key lau dai cua graph, doc 12 G6). Luu dict JSON, khong luu object pydantic.

- session: track / level / duration_minutes / jd_profile / started_at (ghi o /start; jd_profile None neu khong co)
- plan: plan goc tu /start (topic doi nam trong state.swaps), chi ghi mot lan
- state: CandidateState sau luot; question: cau hoi da gui gan nhat (cau ma luot sau tra loi)
- turn: TurnInfo cua cau hoi dang cho tra loi (turn_kind + topic_id cua cau do), ghi o /start va moi luot co cau moi
- transcript: moi luot mot phan tu {turn_number, question, answer, source, elapsed_seconds, topic_id, phase, turn_kind, difficulty,
  evaluation}; 4 truong giua lay tu `turn` cua cau duoc tra loi, evaluation None neu luot khong cham (channel cong don)
- last_turn: luot gan nhat du de replay (meta + done khong metadata). Chi giu MOT luot: blob khong phinh theo phien.
"""
import asyncio
import logging
import time
from typing import Dict

from ..api_error import ApiError
from ..models_interview import NextTurnRequest, StartRequest
from ..turn_result import TurnResult, turn_payload
from .session_checkpointer import STORE_TIMEOUT_S, prune_memory_store, thread_config

log = logging.getLogger("ai_service.session_store")


def start_values(req: StartRequest, result: TurnResult) -> Dict:
    jd = req.jd_profile.model_dump(mode="json") if req.jd_profile else None
    return {"session": {"track": req.track, "level": req.level, "duration_minutes": req.duration_minutes,
                        "jd_profile": jd, "started_at": int(time.time())},  # dong ho server (session_clock)
            "turn": result.turn.model_dump(mode="json"), "plan": result.plan.model_dump(mode="json"), "state": result.state.model_dump(mode="json"),
            "question": result.question, "last_turn": None}


def turn_values(stored: Dict, req: NextTurnRequest, result: TurnResult) -> Dict:
    """Ghi sau khi luot xong (node `record`): ca luot hoi tiep lan luot ket thuc phien. `stored["turn"]` la cau vua
    duoc tra loi (chua bi ghi de): lay topic_id / phase / turn_kind / difficulty cho phan tu transcript."""
    asked = stored.get("turn") or {}
    out = {"state": result.state.model_dump(mode="json"),
           "transcript": [{"turn_number": req.turn_number, "question": req.question, "answer": req.answer,
                           "source": req.answer_source, "elapsed_seconds": req.elapsed_seconds,
                           "topic_id": asked.get("topic_id"),
                           "phase": asked.get("phase"), "turn_kind": asked.get("turn_kind", req.turn_kind),
                           "difficulty": asked.get("difficulty"),
                           "evaluation": result.evaluation.model_dump(mode="json") if result.evaluation else None}],
           "last_turn": {"turn_number": req.turn_number, "answer": req.answer, "answer_source": req.answer_source,
                         "meta": result.meta or None, "done": turn_payload(result, mode="json")}}
    if result.question is not None:  # phien ket thuc: khong hoi them, giu cau + turn cu
        out["question"] = result.question
    if result.turn is not None:
        out["turn"] = result.turn.model_dump(mode="json")
    return out


async def record_start(graph, req: StartRequest, result: TurnResult) -> bool:
    """/start xong (cau hoi dau da gui): xoa thread cu cung session_id (/start gui lai) roi ghi checkpoint dau.
    Ghi nhu node `record` vua chay: thread khong con viec do dang (next rong). Tra True neu ghi duoc. Ghi loi thi log va
    tra False: checkpoint la nguon duy nhat nen endpoint /start bao `error` retryable (khong gui `done`), FSD goi lai /start."""
    async def write() -> None:
        await graph.checkpointer.adelete_thread(req.session_id)
        await graph.aupdate_state(thread_config(req.session_id), start_values(req, result), as_node="record")
        await prune_memory_store()
    try:
        await asyncio.wait_for(write(), 2 * STORE_TIMEOUT_S)
        return True
    except Exception as err:
        log.warning("session_start_not_recorded error=%s", type(err).__name__)
        return False


async def record_finalize_end(graph, session_id: str, state: Dict) -> None:
    """Finalize mot phien chua done (candidate_ended / qua han cung): ghi state `done` de next-turn sau do bi 409
    session_invalid_state, phien khong choi tiep duoc sau khi da co bao cao. Ghi loi -> 503 (chua tong ket)."""
    try:
        await asyncio.wait_for(graph.aupdate_state(thread_config(session_id), {"state": state}, as_node="record"),
                               STORE_TIMEOUT_S)
    except Exception as err:
        log.warning("session_end_not_recorded error=%s", type(err).__name__)
        raise ApiError(503, "session_store_unavailable", "Không ghi được trạng thái phiên", {"retryable": True})
