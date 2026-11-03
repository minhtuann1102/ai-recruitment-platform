"""Ket thuc som khi ung vien yeu keo dai (design 03 muc 4.4): bien tung dieu kien va luong day du qua API."""
import pytest
from test_interview_flow import play, strong

from app.early_stop import low_performance_stop
from app.mock_planner import build_plan
from app.models_interview import CandidateState, TopicState
from app.turn_engine import flat_topics

TOPICS = flat_topics(build_plan("java_backend", "senior", 30, None))  # t1 intro, t2-t4 technical, t5 scenario
LAST_TECH = 3  # vi tri t4


def state(bands, evaluated=6):
    """bands: score_band cua t1..t4 (t5 chua hoi)."""
    ts = [TopicState(id=t.id, score_band=b) for (_, t), b in zip(TOPICS, list(bands) + [None])]
    return CandidateState(topics=ts, evaluated_turns=evaluated)


@pytest.mark.parametrize("bands,evaluated,level,action,expected", [
    ((3.0, 0.5, 1.0, 1.4), 6, "senior", "next_topic", True),
    ((3.0, 0.5, 1.0, 1.4), 6, "middle", "next_phase", True),
    ((0.5, 3.0, 1.0, 1.4), 6, "senior", "next_topic", False),  # chi 2 topic technical yeu
    ((3.0, 0.5, 1.0, 1.4), 5, "senior", "next_topic", False),  # chua du luot duoc cham
    ((3.0, 0.5, 1.0, 1.5), 6, "senior", "next_topic", False),  # 1.5 khong < WEAK_BAND
    ((3.0, 0.5, 1.0, 1.4), 6, "junior", "next_topic", False),
    ((3.0, 0.5, 1.0, 1.4), 6, "fresher", "next_topic", False),
    ((3.0, 0.5, 1.0, 1.4), 6, "senior", "hint", False),  # chua dong topic: van duoc goi y
    ((3.0, 0.5, 1.0, 1.4), 6, "senior", "follow_up", False),
    ((0.0, 0.5, 1.0, 1.4), 6, "senior", "next_topic", True),  # intro yeu khong tinh, chi xet technical
])
def test_low_performance_stop_conditions(bands, evaluated, level, action, expected):
    assert low_performance_stop(state(bands, evaluated), TOPICS, LAST_TECH, level, action) is expected


def test_unscored_topic_does_not_break_the_weak_streak():
    plan = build_plan("java_backend", "senior", 30, None)
    plan.phases[1].topics.append(plan.phases[1].topics[0].model_copy(update={"id": "t4b"}))
    topics = flat_topics(plan)  # t1, t2, t3, t4, t4b, t5
    ts = [TopicState(id=t.id, score_band=b) for (_, t), b in zip(topics, (3.0, 0.5, None, 1.0, 1.2, None))]
    st = CandidateState(topics=ts, evaluated_turns=6)
    assert low_performance_stop(st, topics, 4, "senior", "next_topic") is True
    assert low_performance_stop(st, topics, 3, "senior", "next_topic") is False  # moi 2 topic co diem


def test_short_plan_needs_all_technical_topics_weak():
    topics = flat_topics(build_plan("java_backend", "senior", 20, None))  # t1 intro, t2-t3 technical, t4 scenario
    assert sum(ph == "technical" for ph, _ in topics) == 2
    st = CandidateState(topics=[TopicState(id=t.id, score_band=b) for (_, t), b in zip(topics, (3.0, 0.5, 1.0, None))],
                        evaluated_turns=6)
    assert low_performance_stop(st, topics, 2, "senior", "next_topic") is True
    assert low_performance_stop(st, topics, 1, "senior", "next_topic") is False  # moi dong 1/2 topic technical
    st.topics[2].score_band = 1.5
    assert low_performance_stop(st, topics, 2, "senior", "next_topic") is False


@pytest.mark.parametrize("duration", [20, 30])
def test_weak_senior_wraps_up_after_technical_and_skips_scenario(client, duration):
    _, state, turns, _ = play(client, "senior", lambda t, q: "em không biết ạ", duration_minutes=duration)
    assert state["phase"] == "done" and state["end_reason"] == "low_performance"
    phases = [t["phase"] for t in turns]
    assert "scenario" not in phases and phases[-1] == "wrap_up"
    assert sum(t["turn_kind"] == "hint" for t in turns) >= 3  # moi topic van duoc goi y truoc khi dung


def test_strong_middle_still_reaches_scenario(client):
    _, state, turns, _ = play(client, "middle", strong)
    assert state["end_reason"] == "plan_complete" and "scenario" in {t["phase"] for t in turns}


def test_weak_junior_is_not_cut_early(client):
    _, state, turns, _ = play(client, "junior", lambda t, q: "em không biết ạ")
    assert state["end_reason"] == "plan_complete" and "scenario" in {t["phase"] for t in turns}
