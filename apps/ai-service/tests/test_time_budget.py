"""Gioi han cung va ngan sach thoi gian (FR-AI-035, 036; design 03 muc 4.4): test bien tung dieu kien."""
import pytest
from conftest import parse_sse

from app.mock_planner import build_plan
from app.models_interview import CandidateState
from app.state_update import apply_action
from app.time_budget import duration_s, forced_transition, phase_deadline_s, topic_budget_s, turn_cap
from app.turn_engine import flat_topics

PLAN = build_plan("java_backend", "junior", 20, None)  # 1 intro + 3 technical + 1 scenario, tong 20 phut


def state(**kw):
    return CandidateState(**{"turn_count": 2, **kw})


@pytest.mark.parametrize("duration,cap", [(15, 12), (20, 16), (30, 24)])
def test_turn_cap_scales_with_duration(duration, cap):
    assert turn_cap(build_plan("java_backend", "junior", duration, None)) == cap


def test_phase_deadlines_borrow_time():
    intro = PLAN.phases[0].time_budget_min * 60
    assert duration_s(PLAN) == 1200 and phase_deadline_s(PLAN, "intro") == intro
    assert phase_deadline_s(PLAN, "technical") == intro + PLAN.phases[1].time_budget_min * 60
    assert topic_budget_s(PLAN, "technical") == PLAN.phases[1].time_budget_min * 60 / 3


@pytest.mark.parametrize("elapsed,st,phase,expected", [
    (1200 + 180, state(), "technical", ("end", "time_hard_limit")),
    (1200 + 179, state(), "technical", ("wrap_up", "time_up")),
    (1200, state(), "scenario", ("wrap_up", "time_up")),
    (100, state(turn_count=16), "technical", ("wrap_up", "turn_cap")),
    (100, state(turn_count=15), "intro", None),
    (None, state(), "intro", ("next_phase", "phase_time")),  # elapsed = han intro + 60
    (None, state(), "scenario", None),  # phase cuoi khong chuyen phase, het gio thi wrap_up
    (100, state(counters={"consecutive_dont_know": 2}), "intro", ("next_topic", "two_dont_know")),
    (100, state(counters={"consecutive_dont_know": 1}), "intro", None),
])
def test_forced_transition_priority(elapsed, st, phase, expected):
    if elapsed is None:
        elapsed = phase_deadline_s(PLAN, "intro") + 60
        if phase == "scenario":
            st.topic_started_s = elapsed
    assert forced_transition(elapsed, st, PLAN, phase) == expected


def test_topic_overrun_closes_topic():
    budget = topic_budget_s(PLAN, "technical")
    st = state(topic_started_s=300)
    assert forced_transition(300 + int(1.5 * budget), st, PLAN, "technical") == ("next_topic", "topic_time")
    assert forced_transition(300 + int(1.5 * budget) - 1, st, PLAN, "technical") is None


def test_next_phase_skips_remaining_topics_and_records_start_times():
    topics = flat_topics(PLAN)
    st = CandidateState(phase="technical", active_topic_id=topics[1][1].id,
                        topics=[{"id": t.id, "status": "active" if i == 1 else "done" if i == 0 else "pending"}
                                for i, (_, t) in enumerate(topics)])
    action, changed, target = apply_action(st, topics, 1, "next_phase", 0, 777)
    assert (action, changed, topics[target][0]) == ("ask_main", True, "scenario")
    assert [t.status for t in st.topics] == ["done", "done", "done", "done", "active"]
    assert st.phase_started_s == st.topic_started_s == 777


def _start(client):
    done = parse_sse(client.post("/api/start", json={"session_id": "s", "track": "java_backend", "level": "junior",
                                                    "duration_minutes": 20}).text)[-1][1]
    return done


def _answer(client, done, answer, elapsed, turn_no=1, plan=None):
    body = {"session_id": "s", "level": "junior", "track": "java_backend", "plan": plan or done["plan"],
            "state": done["state"], "turn_number": turn_no, "question": done["question"], "answer": answer,
            "turn_kind": done["turn"]["turn_kind"], "elapsed_seconds": elapsed}
    return parse_sse(client.post("/api/next-turn", json=body).text)[-1][1]


def test_hard_limit_ends_immediately_but_still_scores(client):
    nd = _answer(client, _start(client), "Em làm backend Java Spring Boot cho hệ thống đơn hàng", 1200 + 180)
    assert nd["session_end"] and nd["question"] is None and nd["turn"] is None
    assert nd["state"]["end_reason"] == "time_hard_limit" and nd["evaluation"] is not None


def test_two_dont_know_in_a_row_moves_to_next_topic(client):
    done = _start(client)
    first = _answer(client, done, "Em không biết ạ", 60)
    assert first["turn"]["action"] == "hint"
    second = _answer(client, first, "Em không biết ạ", 90, turn_no=2, plan=done["plan"])
    assert second["turn"]["action"] == "ask_main" and second["state"]["active_topic_id"] != done["state"]["active_topic_id"]
    assert "two_dont_know" in second["turn"]["reasoning"]


def test_phase_overrun_jumps_to_next_phase(client):
    done = _start(client)
    late = phase_deadline_s(PLAN, "intro") + 60
    nd = _answer(client, done, "Em làm backend Java Spring Boot cho hệ thống đơn hàng", late)
    assert nd["turn"]["phase"] == "technical" and nd["state"]["phase_started_s"] == late
