"""Graph LangGraph mot luot (plan 261127-1517 phase 02): thu tu node theo tung nhanh, loi 4xx giu nguyen kieu, so do
Mermaid du nhanh, client ngat giua stream thi huy ca graph. Hanh vi tung luot da duoc golden trace kiem
(test_golden_turns_match_fixture.py); o day kiem phan rieng cua graph."""
import asyncio
import gc
import json

import pytest

from app.agents.interviewer import get_interviewer
from app.api_error import ApiError
from app.turn_engine import turn_context
from app.turn_graph.turn_graph_builder import DECIDE_ACTIONS, turn_graph, turn_graph_mermaid
from app.main import app
from conftest import parse_sse
from tests.test_policy_hybrid_turn_engine import request


def node_path(req):
    """Chay graph, tra (ten node theo thu tu, ket qua luot)."""
    ctx = turn_context(req, interviewer=get_interviewer)

    async def go():
        return [name for update in [u async for u in turn_graph().astream({"ctx": ctx}, stream_mode="updates")]
                for name in update]
    return asyncio.run(go()), ctx.result


def test_answered_turn_goes_perceive_evaluate_decide_act_ask():
    path, result = node_path(request())
    assert path == ["perceive", "evaluate", "decide", "act", "ask"]
    assert result.question and result.source == "ai" and result.state.asked_questions  # finish_turn da chay trong ask


def test_low_confidence_voice_goes_to_reask_without_evaluating():
    req = request().model_copy(update={"answer_source": "voice", "stt_confidence": 0.2})
    path, result = node_path(req)
    assert path == ["perceive", "reask", "ask"] and result.turn.action == "clarify" and result.source == "fallback"


def test_answer_to_wrap_up_ends_at_perceive_and_hard_limit_ends_at_decide():
    req = request()
    path, result = node_path(req.model_copy(update={"state": req.state.model_copy(update={"phase": "wrap_up"})}))
    assert path == ["perceive"] and result.session_end and result.question is None
    path, result = node_path(req.model_copy(update={"elapsed_seconds": 99999}))
    assert path == ["perceive", "evaluate", "decide"] and result.state.end_reason == "time_hard_limit"


@pytest.mark.parametrize("update,code", [({"answer_source": "voice", "answer": "", "stt_confidence": 0.9},
                                          "voice_no_speech"), ({"state_phase": "done"}, "session_invalid_state")])
def test_api_errors_leave_the_graph_unwrapped(update, code):
    req = request()
    if update.pop("state_phase", None):
        req = req.model_copy(update={"state": req.state.model_copy(update={"phase": "done"})})
    with pytest.raises(ApiError) as err:
        node_path(req.model_copy(update=update))
    assert err.value.error == code  # endpoint (exception_handler) van nhan ApiError, ra dung ma HTTP


def test_mermaid_diagram_shows_every_node_and_decide_branch():
    mermaid = turn_graph_mermaid()
    for node in ("perceive", "reask", "evaluate", "decide", "act", "ask"):
        assert node in mermaid
    for action in DECIDE_ACTIONS:
        assert action in mermaid


class SlowInterviewer:
    """Stream 20 token cham; ghi lai so token da sinh va viec stream bi dong."""
    def __init__(self):
        self.sent, self.closed = 0, False

    async def stream(self, spec, collector=None):
        try:
            for i in range(20):
                await asyncio.sleep(0.01)
                self.sent += 1
                yield f"tok{i} "
        finally:
            self.closed = True


def post_and_disconnect(body, after: int, yield_in_send: bool, slow: SlowInterviewer):
    """Goi app truc tiep; client ngat sau `after` message. Do trang thai Interviewer NGAY khi app tra ve va sau 0,3 s,
    trong cung vong su kien (asyncio.run don task con sot khi dong vong nen assert sau do se sai)."""
    bodies, sent, gone = [json.dumps(body).encode()], [], asyncio.Event()

    async def receive():
        if bodies:
            return {"type": "http.request", "body": bodies.pop(), "more_body": False}
        await gone.wait()
        return {"type": "http.disconnect"}

    async def send(message):
        sent.append(message)
        if len(sent) >= after:
            gone.set()
            if yield_in_send:
                await asyncio.sleep(0)

    scope = {"type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"}, "http_version": "1.1",
             "method": "POST", "path": "/api/next-turn", "raw_path": b"/api/next-turn", "query_string": b"",
             "headers": [(b"content-type", b"application/json")], "client": ("t", 1), "server": ("t", 80),
             "scheme": "http", "root_path": ""}

    async def go():
        await app(scope, receive, send)
        at_return = (slow.sent, slow.closed)
        await asyncio.sleep(0.3)
        return at_return, (slow.sent, slow.closed)
    return sent, *asyncio.run(go())


@pytest.mark.parametrize("after,yield_in_send", [(1, False), (2, True), (2, False), (3, False), (4, False)])
def test_client_disconnect_mid_question_cancels_the_graph_and_closes_the_interviewer(monkeypatch, capsys, after,
                                                                                    yield_in_send):
    slow = SlowInterviewer()
    monkeypatch.setattr("app.main.get_interviewer", lambda: slow)
    sent, at_return, later = post_and_disconnect(json.loads(request().model_dump_json()), after, yield_in_send, slow)
    assert sent[0]["type"] == "http.response.start" and sent[0]["status"] == 200
    assert at_return[1] and at_return[0] < 20  # Interviewer da dong khi request xong, khong chay tiep trong nen
    assert later == at_return
    line = next(x for x in map(json.loads, (e for e in capsys.readouterr().err.splitlines() if e.startswith("{")))
                if x["event"] == "request_done")
    assert "status=cancelled" in line["msg"]


def test_every_action_source_is_a_decide_edge():
    """Hanh dong ngoai DECIDE_ACTIONS lam graph loi (KeyError): moi nguon hanh dong phai nam trong danh sach canh."""
    from app.policy_hybrid import ACTIONS as HYBRID_ACTIONS
    from app.turn_steps import SESSION_END
    forced = {"wrap_up", "next_phase", "next_topic"}  # time_budget.forced_transition tru "end"; low_performance: wrap_up
    assert HYBRID_ACTIONS | forced <= set(DECIDE_ACTIONS) and SESSION_END not in DECIDE_ACTIONS


def done_state_body():
    req = request()
    return json.loads(req.model_copy(update={"state": req.state.model_copy(update={"phase": "done"})})
                      .model_dump_json())


def test_rejected_turn_does_not_build_evaluator_or_interviewer(client, monkeypatch):
    def broken():
        raise RuntimeError("AGENT_*_MODE sai")
    monkeypatch.setattr("app.turn_engine.get_evaluator", broken)
    monkeypatch.setattr("app.main.get_interviewer", broken)
    r = client.post("/api/next-turn", json=done_state_body())
    assert r.status_code == 409 and r.json()["error"] == "session_invalid_state"  # khong thanh 500 vi agent loi


def test_failure_inside_ask_after_meta_becomes_an_sse_error_event(client, monkeypatch):
    def broken():
        raise RuntimeError("Interviewer khong dung duoc")
    monkeypatch.setattr("app.main.get_interviewer", broken)
    r = client.post("/api/next-turn", json=json.loads(request().model_dump_json()))
    names = [n for n, _ in parse_sse(r.text)]
    assert r.status_code == 200 and names == ["meta", "error"]
    assert parse_sse(r.text)[-1][1]["retryable"] is True
