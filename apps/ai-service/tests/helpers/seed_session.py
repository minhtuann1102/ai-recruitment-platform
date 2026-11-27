"""Ghi thang mot phien vao checkpoint (store memory) de test HTTP khong phai chay /start va dung state tu dung.

Ghi nhu node `record` (aupdate_state as_node="record"), cung khuon voi record_start cua app: /api/next-turn va
/api/finalize doc lai dung checkpoint nay. Khong goi LLM / agent nao.
"""
import asyncio
from typing import Dict, List, Optional

from app.session_store.session_checkpointer import thread_config
from app.turn_graph.session_graph_selector import session_graph

DEFAULT_SESSION = {"track": "java_backend", "level": "junior", "duration_minutes": 30, "jd_profile": None}


def seed_session(app_or_graph, session_id: str, plan: Dict, state: Dict, transcript: Optional[List[Dict]] = None,
                 turn: Optional[Dict] = None, question: str = "", session: Optional[Dict] = None) -> None:
    """`app_or_graph`: graph da compile, hoac bat ky gi khac (vd app / TestClient) thi dung session_graph() hien tai (theo SESSION_GRAPH).
    plan / state / turn / transcript: dict JSON nhu /start tra ve (turn = done["turn"] cua cau dang cho tra loi;
    moi phan tu transcript can topic_id, phase, turn_kind, difficulty, evaluation neu test finalize / topic_turns)."""
    graph = app_or_graph if hasattr(app_or_graph, "aupdate_state") else session_graph()
    values = {"session": {**DEFAULT_SESSION, **(session or {})}, "plan": plan, "state": state,
              "transcript": list(transcript or []),
              "turn": turn or {"turn_number": 1, "turn_kind": "main", "topic_id": None}, "question": question, "last_turn": None}

    async def write() -> None:
        await graph.checkpointer.adelete_thread(session_id)
        await graph.aupdate_state(thread_config(session_id), values, as_node="record")
    asyncio.run(write())


def seed_from_finalize_request(app_or_graph, req) -> Dict:
    """Test finalize dung tay mot FinalizeRequest: ghi plan / state / turns / jd_profile cua no vao checkpoint, tra body
    slim cua /api/finalize (session_id, end_reason, duration_s) de gui di."""
    session = {"track": req.track, "level": req.level,
               "jd_profile": req.jd_profile.model_dump(mode="json") if req.jd_profile else None}
    transcript = [{**t.model_dump(mode="json"), "source": "text"} for t in req.turns]
    seed_session(app_or_graph, req.session_id, req.plan.model_dump(mode="json"), req.state.model_dump(mode="json"),
                 transcript, session=session)
    return {"session_id": req.session_id, "end_reason": req.end_reason, "duration_s": req.duration_s}


def seed_from_next_turn_request(app_or_graph, req) -> Dict:
    """Test next-turn dung tay mot NextTurnRequest: ghi plan / state / question / turn_kind / topic_turns cua no vao
    checkpoint, tra body slim (session_id, turn_number, answer, answer_source, stt_confidence, elapsed_seconds)."""
    topic_id = req.state.active_topic_id
    turn = {"turn_number": req.turn_number, "phase": req.state.phase, "topic_id": topic_id,
            "turn_kind": req.turn_kind, "difficulty": req.state.current_difficulty}
    transcript = [{"turn_number": 0, "question": t.q, "answer": t.a, "source": t.source or req.answer_source,
                   "topic_id": topic_id, "phase": req.state.phase, "turn_kind": "main", "difficulty": 2,
                   "evaluation": None} for t in req.topic_turns]
    seed_session(app_or_graph, req.session_id, req.plan.model_dump(mode="json"), req.state.model_dump(mode="json"),
                 transcript, turn, req.question, {"track": req.track, "level": req.level})
    body = {"session_id": req.session_id, "turn_number": req.turn_number, "answer": req.answer,
            "answer_source": req.answer_source, "elapsed_seconds": req.elapsed_seconds}
    if req.stt_confidence is not None:
        body["stt_confidence"] = req.stt_confidence
    return body
