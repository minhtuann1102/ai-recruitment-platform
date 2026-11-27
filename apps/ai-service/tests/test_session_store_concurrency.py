"""Luu phien phase 03: hai request cung phien dong thoi -> dung mot lan chay, lan kia 409 turn_in_progress; stream
dut giua cau hoi -> checkpoint giu state truoc luot, gui lai cung answer chay lai ca luot va ra dung ket qua."""
import asyncio
import json

import httpx

import pytest
from app.main import app
from app.session_store.session_lock import turn_locks
from conftest import parse_sse
from tests.session_store_helpers import CountingEvaluator, body, start, stored, without_metadata
from tests.test_turn_graph import SlowInterviewer, post_and_disconnect
from tests.helpers.seed_session import seed_session

pytestmark = pytest.mark.usefixtures("session_graph_mode")  # chay ca hai gia tri SESSION_GRAPH

GOOD = "Em dùng HashMap với equals và hashCode, độ phức tạp O(1) trung bình."


def test_concurrent_requests_run_once_and_reject_the_other(client, monkeypatch):
    d = start(client, "c1")
    b = body("c1", d, GOOD, plan=d["plan"])
    ev, slow = CountingEvaluator(), SlowInterviewer()
    monkeypatch.setattr("app.turn_engine.get_evaluator", lambda: ev)
    monkeypatch.setattr("app.interview_session_routes.get_interviewer", lambda: slow)

    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
            return await asyncio.gather(*(c.post("/api/next-turn", json=b) for _ in range(2)))
    first, second = sorted(asyncio.run(go()), key=lambda r: r.status_code)
    assert first.status_code == 200 and parse_sse(first.text)[-1][0] == "done"
    assert second.status_code == 409 and second.json()["error"] == "turn_in_progress"
    assert second.json()["details"]["retryable"] is True and ev.calls == 1
    assert not turn_locks.busy("c1")  # luot xong thi nha khoa: gui lai la replay
    assert client.post("/api/next-turn", json=b).status_code == 200 and ev.calls == 1


def test_lock_is_released_after_rejected_turns(client):
    d = start(client, "c2")
    seed_session(client, "c2", d["plan"], {**d["state"], "active_topic_id": "khong-co"}, turn=d["turn"],
                 question=d["question"])
    bad = body("c2", d, GOOD)
    assert client.post("/api/next-turn", json=bad).status_code == 422  # loi perceive sau khi giu khoa
    assert not turn_locks.busy("c2")
    assert client.post("/api/next-turn", json={**bad, "turn_number": 9}).status_code == 409  # loi guard
    assert not turn_locks.busy("c2")


def test_cut_stream_keeps_pre_turn_state_and_resend_gives_the_uncut_result(client, monkeypatch, capsys):
    twin = start(client, "c-twin")  # Planner / Interviewer mock tat dinh: phien sinh doi cho ket qua chuan
    uncut = parse_sse(client.post("/api/next-turn", json=body("c-twin", twin, GOOD, plan=twin["plan"])).text)[-1][1]
    d = start(client, "c3")
    b = body("c3", d, GOOD, plan=d["plan"])
    ev, slow = CountingEvaluator(), SlowInterviewer()
    monkeypatch.setattr("app.turn_engine.get_evaluator", lambda: ev)
    with monkeypatch.context() as m:
        m.setattr("app.interview_session_routes.get_interviewer", lambda: slow)
        sent, at_return, _ = post_and_disconnect(json.loads(json.dumps(b)), 3, False, slow)
    assert at_return[1] and at_return[0] < 20 and not turn_locks.busy("c3")
    values = stored("c3")
    assert values["state"] == d["state"] and values["transcript"] == [] and values["last_turn"] is None
    again = parse_sse(client.post("/api/next-turn", json=b).text)[-1][1]
    assert ev.calls == 2  # chay lai ca luot (cham lai), khong resume giua ask
    assert without_metadata(again) == without_metadata(uncut)
