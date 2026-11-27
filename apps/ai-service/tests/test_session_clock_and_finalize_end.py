"""Dong ho phien phia server va dieu kien finalize (app/session_store/session_clock.py).

- client gui elapsed_seconds = 0 mai: thoi gian thuc tu /start van day phien toi wrap-up / ket thuc
- elapsed khong lui duoc so voi luot truoc
- finalize phien chua done -> 409 session_not_done; candidate_ended va qua han cung thi duoc, roi phien bi chot done
"""
import time as real_time

import pytest
from conftest import parse_sse
from tests.session_store_helpers import body, start, stored

pytestmark = pytest.mark.usefixtures("session_graph_mode")  # chay ca hai gia tri SESSION_GRAPH

GOOD = "Em dùng HashMap với equals và hashCode, độ phức tạp O(1) trung bình."


class FakeClock:
    def __init__(self, offset_s: float):
        self.offset_s = offset_s

    def time(self) -> float:
        return real_time.time() + self.offset_s


def answer(client, sid, d, elapsed=0):
    b = {**body(sid, d, GOOD, plan=d["plan"]), "elapsed_seconds": elapsed}
    return parse_sse(client.post("/api/next-turn", json=b).text)[-1][1]


def test_start_records_server_clock_and_turns_record_elapsed(client):
    d = start(client, "c1")
    assert abs(stored("c1")["session"]["started_at"] - real_time.time()) < 5
    answer(client, "c1", d, elapsed=120)
    assert stored("c1")["transcript"][-1]["elapsed_seconds"] == 120


def test_client_sending_zero_still_times_out_on_server_clock(client, monkeypatch):
    d = start(client, "c2")
    monkeypatch.setattr("app.session_store.session_clock.time", FakeClock(3 * 3600))  # 3 gio sau /start
    done = answer(client, "c2", d, elapsed=0)
    assert done["session_end"] is True and done["state"]["end_reason"] == "time_hard_limit"
    assert stored("c2")["transcript"][-1]["elapsed_seconds"] >= 3 * 3600


def test_elapsed_never_goes_back(client):
    d = start(client, "c3")
    first = answer(client, "c3", d, elapsed=600)
    d2 = {**d, "state": first["state"], "turn": first["turn"]}
    answer(client, "c3", d2, elapsed=10)  # client lui dong ho
    assert stored("c3")["transcript"][-1]["elapsed_seconds"] == 600


def test_finalize_mid_session_is_409_session_not_done(client):
    d = start(client, "c4")
    answer(client, "c4", d)
    r = client.post("/api/finalize", json={"session_id": "c4", "end_reason": "plan_complete", "duration_s": 60})
    assert r.status_code == 409 and r.json()["error"] == "session_not_done"
    assert stored("c4")["state"]["phase"] != "done"  # tu choi thi khong doi phien


def test_candidate_ended_finalizes_and_closes_the_session(client):
    d = start(client, "c5")
    first = answer(client, "c5", d)
    r = client.post("/api/finalize", json={"session_id": "c5", "end_reason": "candidate_ended", "duration_s": 60})
    assert r.status_code == 200
    state = stored("c5")["state"]
    assert state["phase"] == "done" and state["end_reason"] == "candidate_ended"
    d2 = {**d, "state": first["state"], "turn": first["turn"]}
    nxt = client.post("/api/next-turn", json=body("c5", d2, GOOD, plan=d["plan"]))
    assert nxt.status_code == 409 and nxt.json()["error"] == "session_invalid_state"


def test_abandoned_session_past_hard_limit_can_be_finalized(client, monkeypatch):
    d = start(client, "c6")
    answer(client, "c6", d)
    monkeypatch.setattr("app.session_store.session_clock.time", FakeClock(3 * 3600))
    r = client.post("/api/finalize", json={"session_id": "c6", "end_reason": "plan_complete", "duration_s": 60})
    assert r.status_code == 200 and stored("c6")["state"]["end_reason"] == "time_hard_limit"


def test_candidate_ended_before_any_answer_closes_the_session_without_report(client):
    d = start(client, "c7")
    r = client.post("/api/finalize", json={"session_id": "c7", "end_reason": "candidate_ended", "duration_s": 5})
    assert r.status_code == 409 and r.json()["error"] == "session_no_turns"
    assert stored("c7")["state"]["phase"] == "done"
    nxt = client.post("/api/next-turn", json=body("c7", d, GOOD))
    assert nxt.status_code == 409 and nxt.json()["error"] == "session_invalid_state"


def test_retry_after_candidate_ended_keeps_the_stored_reason(client):
    d = start(client, "c8")
    answer(client, "c8", d)
    first = client.post("/api/finalize", json={"session_id": "c8", "end_reason": "candidate_ended", "duration_s": 60})
    again = client.post("/api/finalize", json={"session_id": "c8", "end_reason": "plan_complete", "duration_s": 60})
    assert first.status_code == again.status_code == 200
    assert again.json()["session"]["end_reason"] == "candidate_ended"


def test_failed_mark_done_is_503_leaves_session_open_and_retry_works(client, monkeypatch):
    d = start(client, "c9")
    answer(client, "c9", d)
    from app.session_store import session_record

    async def broken(*_a, **_k):
        raise RuntimeError("db down")
    real = session_record.asyncio.wait_for
    monkeypatch.setattr(session_record.asyncio, "wait_for", broken)
    r = client.post("/api/finalize", json={"session_id": "c9", "end_reason": "candidate_ended", "duration_s": 60})
    monkeypatch.setattr(session_record.asyncio, "wait_for", real)
    assert r.status_code == 503 and r.json()["details"]["retryable"] is True
    assert stored("c9")["state"]["phase"] != "done"
    r = client.post("/api/finalize", json={"session_id": "c9", "end_reason": "candidate_ended", "duration_s": 60})
    assert r.status_code == 200  # khoa da nha, gui lai duoc


def test_hard_limit_boundary_uses_server_clock(client, monkeypatch):
    from app.models_interview import InterviewPlan
    from app.time_budget import HARD_LIMIT_EXTRA_S, duration_s
    d = start(client, "c10")
    answer(client, "c10", d)
    limit = duration_s(InterviewPlan.model_validate(stored("c10")["plan"])) + HARD_LIMIT_EXTRA_S
    started = stored("c10")["session"]["started_at"]
    monkeypatch.setattr("app.session_store.session_clock.time", FakeClock(started + limit - 1 - real_time.time()))
    r = client.post("/api/finalize", json={"session_id": "c10", "end_reason": "plan_complete", "duration_s": 60})
    assert r.status_code == 409
    monkeypatch.setattr("app.session_store.session_clock.time", FakeClock(started + limit - real_time.time()))
    r = client.post("/api/finalize", json={"session_id": "c10", "end_reason": "plan_complete", "duration_s": 60})
    assert r.status_code == 200
