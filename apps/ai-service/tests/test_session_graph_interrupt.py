"""Graph ca phien co `interrupt` (plan 261127-1517 phase 05, SESSION_GRAPH=session): phien dung o wait_answer giua cac
luot, /next-turn resume, /finalize resume voi {"kind": "finalize"}, luot dut giua `ask` chay lai ca luot, thread cua graph
mot luot -> 404 session_graph_mismatch. Hanh vi HTTP tung luot da duoc golden trace + test luu phien kiem o ca hai che do."""
import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.session_store.session_graph_settings import load_session_graph_mode
from app.session_store.session_lock import turn_locks
from app.turn_graph.session_graph_builder import session_graph_mermaid
from app.turn_graph.session_graph_selector import session_graph
from app.turn_graph.turn_graph_builder import DECIDE_ACTIONS
from app.session_store.session_checkpointer import thread_config
from conftest import parse_sse
from tests.session_store_helpers import CountingEvaluator, body, log_lines, start, stored, without_metadata
from tests.test_turn_graph import SlowInterviewer, post_and_disconnect

GOOD = "Em dùng HashMap với equals và hashCode, độ phức tạp O(1) trung bình."


@pytest.fixture(autouse=True)
def session_mode(monkeypatch):
    monkeypatch.setenv("SESSION_GRAPH", "session")


def snapshot(sid):
    return asyncio.run(session_graph().aget_state(thread_config(sid)))


def post_turn(client, sid, d, **extra):
    r = client.post("/api/next-turn", json=body(sid, d, GOOD, **extra))
    return r, (parse_sse(r.text)[-1][1] if r.status_code == 200 else None)


def play_to_end(client, sid, limit=40):
    d, n = start(client, sid), 0
    while not d.get("session_end") and n < limit:
        _, d = post_turn(client, sid, d)
        n += 1
    return d, n


def test_session_waits_at_interrupt_after_start_and_after_every_turn(client):
    d = start(client, "i1")
    snap = snapshot("i1")
    assert snap.next == ("wait_answer",) and [i.value for i in snap.interrupts] == [{"waiting": "answer"}]
    assert stored("i1")["question"] == d["question"] and stored("i1")["transcript"] == []
    _, d2 = post_turn(client, "i1", d)
    snap = snapshot("i1")
    assert snap.next == ("wait_answer",) and snap.values["state"] == d2["state"] and len(snap.values["transcript"]) == 1
    assert d2["turn"]["turn_number"] == 2 and not turn_locks.busy("i1")


def test_resume_on_a_finished_session_is_409_and_replay_still_works(client):
    d, n = play_to_end(client, "i2")
    assert d["session_end"] and n > 3
    last = stored("i2")["last_turn"]
    r = client.post("/api/next-turn", json={"session_id": "i2", "turn_number": last["turn_number"],
                                            "answer": last["answer"]})
    assert r.status_code == 200 and parse_sse(r.text)[-1][1]["metadata"]["replayed"] is True
    r = client.post("/api/next-turn", json={"session_id": "i2", "turn_number": n + 1, "answer": "khac"})
    assert r.status_code == 409 and r.json()["error"] == "session_invalid_state"
    assert snapshot("i2").next == ("wait_answer",)  # luot bi tu choi khong lam graph di tiep


def test_finalize_mid_session_follows_phase_04_rules(client):
    d = start(client, "i3")
    body_ = {"session_id": "i3", "end_reason": "plan_complete", "duration_s": 60}
    assert client.post("/api/finalize", json=body_).status_code == 409  # chua tra loi luot nao
    _, d = post_turn(client, "i3", d)
    r = client.post("/api/finalize", json=body_)
    assert r.status_code == 409 and r.json()["error"] == "session_not_done"  # phien chua done, khong phai candidate_ended
    r = client.post("/api/finalize", json={**body_, "end_reason": "candidate_ended"})
    assert r.status_code == 200
    values = stored("i3")
    assert values["state"]["phase"] == "done" and values["state"]["end_reason"] == "candidate_ended"
    assert snapshot("i3").next == ("wait_answer",) and not turn_locks.busy("i3")
    again = client.post("/api/next-turn", json=body("i3", d, GOOD))
    assert again.status_code == 409 and again.json()["error"] == "session_invalid_state"


def test_finalize_twice_runs_the_reporter_twice_with_the_same_result(client):
    play_to_end(client, "i4")
    b = {"session_id": "i4", "end_reason": "plan_complete", "duration_s": 60}
    first, second = client.post("/api/finalize", json=b), client.post("/api/finalize", json=b)
    assert first.status_code == second.status_code == 200
    strip = lambda r: {k: v for k, v in r.json().items() if k != "metadata"}  # noqa: E731
    assert strip(first) == strip(second)
    assert snapshot("i4").next == ("wait_answer",) and stored("i4")["state"]["phase"] == "done"


def test_finalize_without_a_session_graph_thread_is_404(client):
    r = client.post("/api/finalize", json={"session_id": "khong-co", "end_reason": "plan_complete", "duration_s": 1})
    assert r.status_code == 404 and r.json()["error"] == "session_not_found"


def test_cut_stream_leaves_checkpoint_at_ask_and_the_same_answer_reruns_the_turn(client, monkeypatch):
    twin = start(client, "i5-twin")  # Planner / Interviewer mock tat dinh: phien sinh doi cho ket qua chuan
    uncut = post_turn(client, "i5-twin", twin)[1]
    d = start(client, "i5")
    b = body("i5", d, GOOD)
    ev, slow = CountingEvaluator(), SlowInterviewer()
    monkeypatch.setattr("app.turn_engine.get_evaluator", lambda: ev)
    with monkeypatch.context() as m:
        m.setattr("app.interview_session_routes.get_interviewer", lambda: slow)
        _, at_return, _ = post_and_disconnect(json.loads(json.dumps(b)), 3, False, slow)
    assert at_return[1] and at_return[0] < 20 and not turn_locks.busy("i5")
    assert snapshot("i5").next == ("ask",)  # luot dut: checkpoint moi nhat da qua wait_answer
    values = stored("i5")
    assert values["state"] == d["state"] and values["transcript"] == [] and values["last_turn"] is None
    again = parse_sse(client.post("/api/next-turn", json=b).text)[-1][1]
    assert ev.calls == 2 and without_metadata(again) == without_metadata(uncut)  # cham lai ca luot
    assert snapshot("i5").next == ("wait_answer",) and len(stored("i5")["transcript"]) == 1
    # lan dut thu hai: van lui duoc ve wait_answer (khong dung lai checkpoint ask cua lan dut truoc)
    nxt = body("i5", again, GOOD)
    with monkeypatch.context() as m:
        slow2 = SlowInterviewer()
        m.setattr("app.interview_session_routes.get_interviewer", lambda: slow2)
        post_and_disconnect(json.loads(json.dumps(nxt)), 3, False, slow2)
    assert client.post("/api/next-turn", json=nxt).status_code == 200 and len(stored("i5")["transcript"]) == 2


def test_cut_stream_then_finalize_rewinds_to_wait_answer_and_reports_answered_turns(client, monkeypatch):
    d = start(client, "i6")
    _, d = post_turn(client, "i6", d)
    slow = SlowInterviewer()
    with monkeypatch.context() as m:
        m.setattr("app.interview_session_routes.get_interviewer", lambda: slow)
        post_and_disconnect(json.loads(json.dumps(body("i6", d, GOOD))), 3, False, slow)
    assert snapshot("i6").next == ("ask",)
    r = client.post("/api/finalize", json={"session_id": "i6", "end_reason": "candidate_ended", "duration_s": 5})
    assert r.status_code == 200 and len(stored("i6")["transcript"]) == 1  # luot dut khong vao transcript
    assert snapshot("i6").next == ("wait_answer",) and stored("i6")["state"]["phase"] == "done"


def test_thread_written_by_the_per_turn_graph_is_404_session_not_resumable(client, monkeypatch, capsys):
    monkeypatch.setenv("SESSION_GRAPH", "per_turn")
    d = start(client, "i7")
    monkeypatch.setenv("SESSION_GRAPH", "session")  # doi co giua phien
    log_lines(capsys)
    r = client.post("/api/next-turn", json=body("i7", d, GOOD))
    assert r.status_code == 404 and r.json()["error"] == "session_not_found"
    assert "session_not_resumable" in log_lines(capsys) and not turn_locks.busy("i7")
    r = client.post("/api/finalize", json={"session_id": "i7", "end_reason": "candidate_ended", "duration_s": 5})
    # chua tra loi luot nao: finalize dung o kiem phase 04 (409), chua toi buoc resume
    assert r.status_code == 409 and r.json()["error"] == "session_no_turns" and not turn_locks.busy("i7")


def test_many_rejected_turns_do_not_lose_the_resume_point(client):
    d = start(client, "i9")
    no_speech = body("i9", d, "", answer_source="voice", stt_confidence=0.9)
    for _ in range(10):  # moi luot 422 ghi them mot checkpoint con (durability exit)
        assert client.post("/api/next-turn", json=no_speech).status_code == 422
    assert post_turn(client, "i9", d)[0].status_code == 200 and len(stored("i9")["transcript"]) == 1


def test_many_cut_streams_on_one_turn_still_resume(client, monkeypatch):
    d = start(client, "i10")
    b = body("i10", d, GOOD)
    for _ in range(9):
        slow = SlowInterviewer()
        with monkeypatch.context() as m:
            m.setattr("app.interview_session_routes.get_interviewer", lambda: slow)
            post_and_disconnect(json.loads(json.dumps(b)), 3, False, slow)
    assert client.post("/api/next-turn", json=b).status_code == 200 and len(stored("i10")["transcript"]) == 1


def test_reporter_failure_still_closes_the_session(monkeypatch):
    c = TestClient(app, raise_server_exceptions=False)
    d = start(c, "i11")
    _, d = post_turn(c, "i11", d)

    class Broken:
        async def report(self, *_a, **_k):
            raise RuntimeError("Reporter loi")
    monkeypatch.setattr("app.turn_graph.session_graph_nodes.get_reporter", lambda: Broken())
    r = c.post("/api/finalize", json={"session_id": "i11", "end_reason": "candidate_ended", "duration_s": 5})
    assert r.status_code == 500 and not turn_locks.busy("i11")
    assert stored("i11")["state"]["phase"] == "done"  # da chot truoc khi Reporter chay
    again = c.post("/api/next-turn", json=body("i11", d, GOOD))
    assert again.status_code == 409 and again.json()["error"] == "session_invalid_state"


def test_start_again_replaces_the_session_thread(client):
    d = start(client, "i8")
    post_turn(client, "i8", d)
    again = start(client, "i8")
    assert stored("i8")["transcript"] == [] and snapshot("i8").next == ("wait_answer",)
    assert again["turn"]["turn_number"] == 1


def test_invalid_session_graph_value_fails_startup(monkeypatch):
    assert load_session_graph_mode({"SESSION_GRAPH": " Session "}) == "session"
    assert load_session_graph_mode({}) == "per_turn"
    with pytest.raises(Exception, match="SESSION_GRAPH"):
        load_session_graph_mode({"SESSION_GRAPH": "tat-ca"})
    monkeypatch.setenv("SESSION_GRAPH", "tat-ca")
    with pytest.raises(Exception, match="SESSION_GRAPH"):
        with TestClient(app):
            pass


def test_mermaid_shows_the_loop_and_the_report_branch():
    mermaid = session_graph_mermaid()
    for node in ("plan", "wait_answer", "perceive", "reask", "evaluate", "decide", "act", "ask", "record", "report"):
        assert node in mermaid
    for action in DECIDE_ACTIONS:
        assert action in mermaid
    assert "record -->" in mermaid and "report -->" in mermaid and "act -->" in mermaid and "ApiError" not in mermaid

