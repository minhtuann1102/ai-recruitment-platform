"""session_summary + POST /api/voice/session-summary (T024): thong ke, dem, nhan xet mau co dinh."""
from dataclasses import replace

from app.models import TurnDeliveryMetrics
from app.session_summary import summarize
import pytest

from tests.helpers import FakeBlaze, make_settings

CONFIG = make_settings()


def turn(**kw) -> dict:
    return {"topic_id": "t", "thinking_time_s": 4.0, "answer_duration_s": 30.0, "over_limit": None, "speech_time_s": 28.0,
            "speech_rate_spm": 150.0, "long_pause_count": 0, "filler_ratio": 0.02, **kw}


@pytest.fixture()
def client(build_client):
    return build_client(FakeBlaze({}))  # summary khong goi nha cung cap


def summary(client, turns):
    r = client.post("/api/voice/session-summary", json={"turns": turns})
    assert r.status_code == 200
    return r.json()


def test_three_of_eight_turns_with_long_pause_gives_pause_note(client):
    turns = [turn(long_pause_count=2), turn(long_pause_count=1), turn(long_pause_count=3)] + [turn() for _ in range(5)]
    body = summary(client, turns)
    assert body["voice_turns"] == 8
    assert body["counts"]["turns_with_long_pause"] == 3
    assert body["notes"][0].startswith("3/8 câu trả lời có quãng ngừng dài trên 2 giây.")
    assert body["stats"]["answer_duration_s"] == {"median": 30.0, "min": 30.0, "max": 30.0, "n": 8}


def test_empty_turns_means_no_voice_data(client):
    assert summary(client, []) == {
        "voice_turns": 0, "stats": {}, "notes": [],
        "counts": {"turns_with_long_pause": 0, "turns_over_limit": 0, "turns_with_limit": 0}}


def test_metric_empty_in_every_turn_is_absent_from_stats_and_notes(client):
    turns = [turn(thinking_time_s=None), turn(thinking_time_s=None)]
    body = summary(client, turns)
    assert "thinking_time_s" not in body["stats"] and set(body["stats"]) >= {"answer_duration_s"}
    assert not any("suy nghĩ" in n for n in body["notes"])


def test_stats_use_only_turns_that_have_the_value_and_are_rounded():
    turns = [TurnDeliveryMetrics(**turn(thinking_time_s=2.0)), TurnDeliveryMetrics(**turn(thinking_time_s=None)),
             TurnDeliveryMetrics(**turn(thinking_time_s=9.0)), TurnDeliveryMetrics(**turn(thinking_time_s=3.0))]
    stats = summarize(turns, CONFIG).stats["thinking_time_s"]
    assert (stats.median, stats.min, stats.max, stats.n) == (3.0, 2.0, 9.0, 3)


def test_limit_counts():
    turns = [TurnDeliveryMetrics(**turn(over_limit=True)), TurnDeliveryMetrics(**turn(over_limit=False)),
             TurnDeliveryMetrics(**turn(over_limit=None))]
    counts = summarize(turns, CONFIG).counts
    assert (counts.turns_over_limit, counts.turns_with_limit) == (1, 2)


def test_no_pause_note_below_one_third_of_turns():
    turns = [TurnDeliveryMetrics(**turn(long_pause_count=1))] + [TurnDeliveryMetrics(**turn()) for _ in range(3)]
    assert summarize(turns, CONFIG).notes == []  # 1/4 < 1/3 va cac chi so khac trong nguong


def test_notes_follow_fixed_order_and_thresholds():
    slow = [TurnDeliveryMetrics(**turn(long_pause_count=1, speech_rate_spm=80.0, filler_ratio=0.09, thinking_time_s=12.0))
            for _ in range(3)]
    notes = summarize(slow, CONFIG).notes
    assert [n.split()[0] for n in notes] == ["3/3", "Tốc", "Từ", "Thời"]
    assert "chậm hơn" in notes[1] and "9%" in notes[2] and "12 giây" in notes[3]
    fast = [TurnDeliveryMetrics(**turn(speech_rate_spm=230.0))]
    assert "nhanh hơn" in summarize(fast, CONFIG).notes[0]


def test_thresholds_come_from_config_and_at_threshold_has_no_note():
    on_edge = [TurnDeliveryMetrics(**turn(speech_rate_spm=100.0, filler_ratio=0.05, thinking_time_s=10.0))]
    assert summarize(on_edge, CONFIG).notes == []
    assert len(summarize(on_edge, replace(CONFIG, rate_slow_spm=120, filler_note_ratio=0.04, thinking_note_s=9)).notes) == 3


def test_notes_never_mention_knowledge_scores():
    turns = [TurnDeliveryMetrics(**turn(long_pause_count=2, speech_rate_spm=250.0, filler_ratio=0.2, thinking_time_s=30.0))]
    text = " ".join(summarize(turns, CONFIG).notes).lower()
    assert "điểm" not in text and "kiến thức" not in text


def test_same_input_same_output():
    turns = [TurnDeliveryMetrics(**turn(long_pause_count=1)) for _ in range(4)]
    assert summarize(turns, CONFIG).model_dump() == summarize(list(turns), CONFIG).model_dump()


def test_invalid_metric_values_are_rejected_with_400(client):
    for bad in ({"filler_ratio": 1.5}, {"thinking_time_s": -1}, {"long_pause_count": -2}):
        r = client.post("/api/voice/session-summary", json={"turns": [bad]})
        assert (r.status_code, r.json()["error"]) == (400, "invalid_request")
    assert client.post("/api/voice/session-summary", json={}).status_code == 400
