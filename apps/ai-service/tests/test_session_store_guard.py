"""Luu phien phase 03 (app/session_store): kiem luot voi checkpoint - replay, 409 sai thu tu / phien xong, 503 khi
doc checkpoint loi, /start gui lai, thread chua co, log lech state. Moi test mot InMemorySaver moi (conftest)."""
from app.session_store.session_checkpointer import get_checkpointer
from conftest import parse_sse
from tests.session_store_helpers import CountingEvaluator, body, log_lines, start, stored, without_metadata

GOOD = "Em dùng HashMap với equals và hashCode, độ phức tạp O(1) trung bình."


def first_turn(client, sid="g1"):
    d = start(client, sid)
    b = body(sid, d, GOOD, plan=d["plan"])
    return d, b, client.post("/api/next-turn", json=b)


def test_resent_turn_replays_done_without_evaluator_or_interviewer(client, monkeypatch):
    ev = CountingEvaluator()
    monkeypatch.setattr("app.turn_engine.get_evaluator", lambda: ev)
    _, b, r = first_turn(client)
    events = parse_sse(r.text)
    assert ev.calls == 1

    def broken():
        raise AssertionError("replay khong duoc goi Interviewer")
    monkeypatch.setattr("app.main.get_interviewer", broken)
    again = parse_sse(client.post("/api/next-turn", json=b).text)
    assert [n for n, _ in again] == ["meta", "token", "done"] and ev.calls == 1
    assert again[0][1] == events[0][1] and again[1][1] == {"t": events[-1][1]["question"]}
    assert without_metadata(again[-1][1]) == without_metadata(events[-1][1])
    assert again[-1][1]["metadata"]["replayed"] is True and again[-1][1]["metadata"]["usage"] == {}


def test_same_turn_with_another_answer_is_rejected(client):
    _, b, _ = first_turn(client)
    r = client.post("/api/next-turn", json={**b, "answer": "Câu trả lời khác"})
    assert r.status_code == 409 and r.json()["error"] == "turn_already_answered"


def test_old_or_future_turn_is_out_of_order(client):
    d, b, r = first_turn(client)
    done1 = parse_sse(r.text)[-1][1]
    client.post("/api/next-turn", json=body("g1", done1, GOOD, plan=d["plan"]))  # luot 2 xong
    for turn_number in (1, 7):
        r = client.post("/api/next-turn", json={**b, "turn_number": turn_number, "answer": "khac"})
        assert r.status_code == 409 and r.json()["error"] == "turn_out_of_order"
        assert r.json()["details"]["expected_turn_number"] == 3


def test_finished_session_rejects_new_answers_but_replays_the_last_one(client):
    d = start(client, "g2")
    b = body("g2", d, GOOD, plan=d["plan"], elapsed_seconds=99999)  # qua han cung: phien ket thuc o luot nay
    end = parse_sse(client.post("/api/next-turn", json=b).text)
    assert end[-1][1]["session_end"] and [n for n, _ in end] == ["done"]
    r = client.post("/api/next-turn", json={**b, "answer": "tra loi them"})
    assert r.status_code == 409 and r.json()["error"] == "session_invalid_state"
    again = parse_sse(client.post("/api/next-turn", json=b).text)
    assert [n for n, _ in again] == ["done"] and without_metadata(again[-1][1]) == without_metadata(end[-1][1])


def test_unreadable_store_returns_503_retryable(client, monkeypatch):
    d = start(client, "g3")

    async def down(*_a, **_k):
        raise OSError("db mat ket noi")
    monkeypatch.setattr(get_checkpointer(), "aget_tuple", down)
    r = client.post("/api/next-turn", json=body("g3", d, GOOD, plan=d["plan"]))
    assert r.status_code == 503 and r.json()["error"] == "session_store_unavailable"
    assert r.json()["details"]["retryable"] is True


def test_resent_start_resets_the_session(client):
    first_turn(client, "g4")
    d = start(client, "g4")
    assert stored("g4")["transcript"] == [] and stored("g4")["state"]["turn_count"] == 1
    r = client.post("/api/next-turn", json=body("g4", d, GOOD, plan=d["plan"]))
    assert r.status_code == 200 and parse_sse(r.text)[-1][0] == "done"


def test_missing_thread_runs_from_request_and_starts_recording(client, capsys):
    d = start(client, "g5")
    b = body("other", d, GOOD, plan=d["plan"])  # phien bat dau truoc khi bat luu phien
    r = client.post("/api/next-turn", json=b)
    assert r.status_code == 200 and "session_thread_missing turn=1" in log_lines(capsys)
    values = stored("other")
    assert values["session"] == {"track": "java_backend", "level": "junior"} and values["plan"] == d["plan"]
    assert values["transcript"] == [{"turn_number": 1, "question": d["question"], "answer": GOOD, "source": "text"}]


def test_checkpoint_keeps_small_per_turn_values_and_logs_state_drift(client, capsys):
    d, b, r = first_turn(client, "g6")
    done1 = parse_sse(r.text)[-1][1]
    values = stored("g6")
    assert values["state"] == done1["state"] and values["question"] == done1["question"]
    assert values["last_turn"]["turn_number"] == 1 and values["last_turn"]["done"]["state"] == done1["state"]
    capsys.readouterr()
    drift = {**done1["state"], "current_difficulty": done1["state"]["current_difficulty"] + 1}
    client.post("/api/next-turn", json={**body("g6", done1, GOOD, plan=d["plan"]), "state": drift})
    assert "session_state_mismatch turn=2 fields=state.current_difficulty" in log_lines(capsys)
    assert len(stored("g6")["transcript"]) == 2


def test_full_session_has_no_state_drift(client, capsys):
    d = start(client, "g7")
    done, n = d, 0
    while not done.get("session_end") and n < 40:
        done, n = parse_sse(client.post("/api/next-turn", json=body("g7", done, GOOD, plan=d["plan"])).text)[-1][1], n + 1
    assert n > 3 and done["session_end"] and not [x for x in log_lines(capsys) if "session_state_mismatch" in x]
    assert len(stored("g7")["transcript"]) == n


def test_start_while_a_turn_runs_is_rejected_and_failed_start_write_still_sends_done(client, monkeypatch):
    from app.session_store.session_lock import turn_locks
    release = turn_locks.hold("g8")
    r = client.post("/api/start", json={"session_id": "g8", "track": "java_backend", "level": "junior"})
    assert r.status_code == 409 and r.json()["error"] == "turn_in_progress"
    release()

    async def down(*_a, **_k):
        raise OSError("db mat ket noi")
    monkeypatch.setattr(get_checkpointer(), "adelete_thread", down)
    r = client.post("/api/start", json={"session_id": "g8", "track": "java_backend", "level": "junior"})
    assert parse_sse(r.text)[-1][0] == "done" and not turn_locks.busy("g8")
    assert stored("g8") == {}  # chua ghi: next-turn dau chay tu request roi ghi


def test_memory_store_keeps_only_the_newest_sessions(client, monkeypatch):
    monkeypatch.setattr("app.session_store.session_checkpointer.MAX_MEMORY_SESSIONS", 2)
    for sid in ("m1", "m2", "m3"):
        start(client, sid)
    assert stored("m1") == {} and stored("m2") and stored("m3")


def test_hanging_store_returns_503_fast_and_frees_the_session(client, monkeypatch):
    import asyncio
    from app.session_store.session_lock import turn_locks
    d = start(client, "g9")

    async def hang(*_a, **_k):
        await asyncio.sleep(30)
    monkeypatch.setattr(get_checkpointer(), "aget_tuple", hang)
    monkeypatch.setattr("app.session_store.session_turn_guard.STORE_TIMEOUT_S", 0.05)
    r = client.post("/api/next-turn", json=body("g9", d, GOOD, plan=d["plan"]))
    assert r.status_code == 503 and r.json()["error"] == "session_store_unavailable" and not turn_locks.busy("g9")
