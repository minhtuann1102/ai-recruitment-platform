"""Dung request noi bo (NextTurnRequest / FinalizeRequest) tu body HTTP slim + checkpoint cua phien (phase 04).

turn_engine, Reporter va report_scoring van doc request cu nen khong doi. Moi truong ben goi tung gui nay lay tu
checkpoint: question / turn_kind = cau dang cho tra loi (`question`, `turn`), topic_turns = <= 5 luot cuoi cung topic
trong transcript (gom ca luot hoi lai vi STT, nhu ben goi truoc day), track / level / jd_profile tu `session`.
"""
from typing import Dict, List

from ..api_error import ApiError
from ..models_interview import FinalizeRequest, FinalizeTurn, NextTurnRequest, TopicTurn
from ..models_interview_http import FinalizeBody, NextTurnBody
from .session_clock import effective_elapsed, finalize_end_reason

MAX_TOPIC_TURNS = 5  # = max_length cua NextTurnRequest.topic_turns


def _topic_turns(transcript: List[Dict], topic_id) -> List[TopicTurn]:
    same = [t for t in transcript if t.get("topic_id") == topic_id]
    return [TopicTurn(q=t["question"], a=t["answer"], source=t.get("source")) for t in same[-MAX_TOPIC_TURNS:]]


def build_next_turn_request(body: NextTurnBody, stored: Dict) -> NextTurnRequest:
    session, turn = stored["session"], stored.get("turn") or {}
    return NextTurnRequest(
        session_id=body.session_id, level=session["level"], track=session["track"], plan=stored["plan"],
        state=stored["state"], turn_number=body.turn_number, question=stored["question"],
        turn_kind=turn.get("turn_kind", "main"),
        topic_turns=_topic_turns(stored.get("transcript") or [], turn.get("topic_id")),
        elapsed_seconds=effective_elapsed(body.elapsed_seconds, stored), answer=body.answer, answer_source=body.answer_source,
        stt_confidence=body.stt_confidence)


def _finalize_turn(t: Dict) -> FinalizeTurn:
    fields = {"turn_number": t["turn_number"], "phase": t["phase"], "topic_id": t.get("topic_id"),
              "turn_kind": t.get("turn_kind") or "main", "question": t["question"], "answer": t["answer"],
              "evaluation": t.get("evaluation")}
    if t.get("difficulty") is not None:
        fields["difficulty"] = t["difficulty"]
    return FinalizeTurn(**fields)


def build_finalize_request(body: FinalizeBody, stored: Dict) -> FinalizeRequest:
    """Transcript rong (chua tra loi luot nao) -> 409 session_no_turns. Phien chua done -> 409 session_not_done, tru
    candidate_ended / qua han cung (session_clock.finalize_end_reason)."""
    transcript = stored.get("transcript") or []
    if not transcript:
        raise ApiError(409, "session_no_turns", "Phiên chưa có lượt trả lời nào để tổng kết")
    session = stored["session"]
    reason = finalize_end_reason(stored, body.end_reason)  # mot nguon cho ca state va report
    state = {**stored["state"], "phase": "done", "end_reason": reason}
    return FinalizeRequest(
        session_id=body.session_id, track=session["track"], level=session["level"], plan=stored["plan"],
        state=state, end_reason=reason, duration_s=body.duration_s,
        turns=[_finalize_turn(t) for t in transcript], jd_profile=session.get("jd_profile"))
