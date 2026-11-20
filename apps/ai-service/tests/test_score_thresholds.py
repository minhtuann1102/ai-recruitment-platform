"""Nguong diem policy chinh qua env (POLICY_WEAK_BELOW / POLICY_STRONG_FROM): mac dinh y nhu truoc, gia tri la -> mac dinh,
va ca classify, momentum, ket thuc som cung dung mot nguong."""
import pytest
from test_early_stop import LAST_TECH, TOPICS, state as stop_state
from test_policy_hybrid import ev

from app.early_stop import low_performance_stop
from app.policy import classify
from app.state_update import apply_action
from app.score_thresholds import _parse, score_thresholds


def test_defaults_match_the_old_constants():
    assert score_thresholds({}) == (1.5, 3.0)


@pytest.mark.parametrize("env", [{"POLICY_WEAK_BELOW": "abc"}, {"POLICY_WEAK_BELOW": "3.5"},
                                 {"POLICY_WEAK_BELOW": "0"}, {"POLICY_STRONG_FROM": "5"},
                                 {"POLICY_WEAK_BELOW": "2", "POLICY_STRONG_FROM": "2"},
                                 {"POLICY_WEAK_BELOW": "nan"}, {"POLICY_STRONG_FROM": "inf"}])
def test_invalid_values_fall_back_to_defaults(env, caplog):
    _parse.cache_clear()
    assert score_thresholds(env) == (1.5, 3.0)
    assert "policy_thresholds_invalid" in caplog.text  # cau hinh sai khong im lang


def test_valid_override_is_used():
    assert score_thresholds({"POLICY_WEAK_BELOW": "2.0", "POLICY_STRONG_FROM": "3.25"}) == (2.0, 3.25)


def test_classify_and_early_stop_follow_the_env(monkeypatch):
    answer = ev(2).model_copy(update={"turn_score_10": 4.0})  # band 1.6: ok voi mac dinh, yeu khi nguong yeu = 2.0
    bands = (3.0, 1.6, 1.6, 1.6)
    assert classify(answer) == "ok"
    assert not low_performance_stop(stop_state(bands), TOPICS, LAST_TECH, "senior", "next_topic")
    monkeypatch.setenv("POLICY_WEAK_BELOW", "2.0")
    assert classify(answer) == "weak"
    assert low_performance_stop(stop_state(bands), TOPICS, LAST_TECH, "senior", "next_topic")


def test_momentum_follows_the_env(monkeypatch):
    def momentum(band):
        st = stop_state((3.0, band, None, None), evaluated=2)
        apply_action(st, TOPICS, 1, "next_topic", 0, 60)
        return st.momentum
    assert momentum(2.8) == 0  # 2.8 < 3.0: chua manh voi mac dinh
    monkeypatch.setenv("POLICY_STRONG_FROM", "2.75")
    assert momentum(2.8) == 1
