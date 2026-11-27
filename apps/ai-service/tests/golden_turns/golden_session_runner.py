"""Chay mot kich ban phong van qua HTTP (TestClient) nhu ben goi that va ghi lai moi luot thanh trace JSON.

Phase 04: HTTP chi nhan body slim (session_id, turn_number, answer...); ben goi gia VAN dung lai request day du
(plan / state / topic_turns / lich su finalize) nhu truoc de ghi vao trace. Fixture khong doi: response phai khop,
tuc request noi bo dung lai tu checkpoint (topic_turns, turns finalize) bang request cu dung tay.

Dung cho golden trace (plan 261127-1517, phase 01): ghi tu code truoc khi boc LangGraph, roi phase 02 / 04 so trace
cua code moi voi fixture. Ben goi gia giu plan / state / topic_turns giong interview-service (docs/ai-service/06):
- topic_turns: cac cap hoi dap TRUOC cau hien tai cua cung topic, toi da 5, reset khi doi topic.
- luot loi (4xx): giu nguyen state, luot sau gui lai cung turn_number.
"""
import json
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

SLIM_TURN_KEYS = ("session_id", "turn_number", "answer", "answer_source", "stt_confidence", "elapsed_seconds")
VOLATILE_KEYS = ("latency_ms",)  # do thoi gian thuc: khong xac dinh, bo khoi trace


def parse_sse(text: str) -> List[List]:
    """Body SSE -> [[event, data], ...] (cung cach tach nhu conftest.parse_sse)."""
    events = []
    for block in text.strip().split("\n\n"):
        lines = block.splitlines()
        name = next(l[7:] for l in lines if l.startswith("event: "))
        data = next(l[6:] for l in lines if l.startswith("data: "))
        events.append([name, json.loads(data)])
    return events


def strip_volatile(value):
    """Bo khoa do thoi gian (de quy) de hai lan chay cho ra cung trace."""
    if isinstance(value, dict):
        return {k: strip_volatile(v) for k, v in value.items() if k not in VOLATILE_KEYS}
    if isinstance(value, list):
        return [strip_volatile(v) for v in value]
    return value


@dataclass
class Caller:
    """Trang thai ben goi giu giua cac luot (nhu interview-service hien tai)."""
    session_id: str
    track: str
    level: str
    plan: dict = field(default_factory=dict)
    state: dict = field(default_factory=dict)
    question: str = ""
    turn: dict = field(default_factory=dict)
    turn_number: int = 1
    topic_turns: List[dict] = field(default_factory=list)
    history: List[dict] = field(default_factory=list)  # turns gui /finalize
    ended: bool = False


# answer_for(step, caller, topic) -> dict cac truong luot (answer, answer_source, stt_confidence, elapsed_seconds)
# hoac None de dung kich ban
AnswerFn = Callable[[int, Caller, Optional[dict]], Optional[Dict]]


def _topic(caller: Caller) -> Optional[dict]:
    topics = {t["id"]: t for ph in caller.plan.get("phases", []) for t in ph["topics"]}
    return topics.get(caller.state.get("active_topic_id"))


def compact_tokens(events: List[List]) -> List[List]:
    """Gop cac event `token` lien tiep thanh mot muc ["token*", {"n": so event, "t": chuoi noi}]: van so duoc noi
    dung va cach chia token, fixture nho hon nhieu."""
    out = []
    for name, data in events:
        if name == "token" and out and out[-1][0] == "token*":
            out[-1][1]["n"] += 1
            out[-1][1]["t"] += data["t"]
        elif name == "token":
            out.append(["token*", {"n": 1, "t": data["t"]}])
        else:
            out.append([name, data])
    return out


def _response_record(r) -> Dict:
    if r.headers.get("content-type", "").startswith("text/event-stream"):
        return {"status": r.status_code, "events": strip_volatile(compact_tokens(parse_sse(r.text)))}
    return {"status": r.status_code, "json": strip_volatile(r.json())}


def run_session(client, session_id: str, track: str, level: str, answer_for: AnswerFn, start_extra: Dict = None,
                max_steps: int = 40, finalize: bool = False, after_end: int = 0) -> Dict:
    """start -> next-turn (toi khi answer_for tra None / phien ket thuc) -> after_end luot gui them -> finalize."""
    start_body = {"session_id": session_id, "track": track, "level": level, **(start_extra or {})}
    r = client.post("/api/start", json=start_body)
    trace = {"start": {"request": start_body, "response": _response_record(r)}, "turns": []}
    done = parse_sse(r.text)[-1][1]
    c = Caller(session_id, track, level, done["plan"], done["state"], done["question"], done["turn"])
    for step in range(max_steps):
        fields = None if c.ended else answer_for(step, c, _topic(c))
        if fields is None:
            break
        _send(client, c, fields, trace)  # luot loi: state giu nguyen, luot sau gui lai cung luot
    for _ in range(after_end if c.ended else 0):  # gui them sau khi phien da ket thuc (mong doi 409)
        _send(client, c, {"answer": "Gửi thêm sau khi kết thúc."}, trace)
    if finalize:
        body = {"session_id": session_id, "track": track, "level": level, "plan": c.plan, "state": c.state,
                "end_reason": c.state.get("end_reason") or "user_ended", "duration_s": c.turn_number * 60,
                "turns": c.history, **({"jd_profile": start_extra["jd_profile"]}
                                       if start_extra and "jd_profile" in start_extra else {})}
        r = client.post("/api/finalize", json={k: body[k] for k in ("session_id", "end_reason", "duration_s")})
        trace["finalize"] = {"request": {k: v for k, v in body.items() if k not in ("plan", "state")},
                             "response": _response_record(r)}
    return trace


def _send(client, c: Caller, fields: Dict, trace: Dict) -> int:
    """Gui mot luot next-turn, ghi trace; 200 va phien chua ket thuc thi ben goi cap nhat state."""
    body = {"session_id": c.session_id, "level": c.level, "track": c.track, "plan": c.plan, "state": c.state,
            "turn_number": c.turn_number, "question": c.question, "turn_kind": c.turn["turn_kind"],
            "topic_turns": list(c.topic_turns), "elapsed_seconds": c.turn_number * 60, **fields}
    slim = {k: v for k, v in body.items() if k in SLIM_TURN_KEYS}
    r = client.post("/api/next-turn", json=slim)
    sent = {k: v for k, v in body.items() if k not in ("plan", "state")}  # state da co trong response luot truoc
    trace["turns"].append({"request": sent, "response": _response_record(r)})
    if r.status_code == 200 and not c.ended:
        _advance(c, body, parse_sse(r.text)[-1][1])
    return r.status_code


def _advance(c: Caller, body: Dict, done: Dict) -> None:
    """Ben goi cap nhat sau event done: lich su finalize, topic_turns, state / cau hoi moi."""
    c.history.append({"turn_number": c.turn_number, "phase": c.turn.get("phase") or c.state["phase"],
                      "topic_id": c.turn.get("topic_id"), "turn_kind": c.turn["turn_kind"],
                      "difficulty": c.turn.get("difficulty", 2), "question": c.question, "answer": body["answer"],
                      "evaluation": done["evaluation"]})
    c.state = done["state"]
    if done["session_end"]:
        c.ended = True
        return
    nxt = done["turn"]
    if nxt["topic_id"] == c.turn.get("topic_id"):
        c.topic_turns = (c.topic_turns + [{"q": c.question, "a": body["answer"],
                                           "source": body.get("answer_source", "text")}])[-5:]
    else:
        c.topic_turns = []
    c.question, c.turn, c.turn_number = done["question"], nxt, nxt["turn_number"]
