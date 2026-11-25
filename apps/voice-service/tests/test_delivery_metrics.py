"""delivery_metrics (T019): cong thuc FR-006 tren moc theo tu (hoac doan VAD), tat dinh."""
from dataclasses import replace

import pytest

from app.delivery_metrics import compute_turn_metrics, speech_spans
from tests.helpers import make_settings

CONFIG = make_settings()
TWELVE = "ừm kiểu như HashMap là một bảng băm không an toàn luồng"  # 12 token, 3 token tu dem


def metrics(timings, transcript=TWELVE, q=None, r=None, limit=None, topic=None, config=CONFIG):
    return compute_turn_metrics(transcript, timings, q, r, limit, topic, config)


def test_scenario_thinking_time_is_gap_plus_first_word_start():
    # spec US1 kich ban 2: cach nhau 4 s, tieng dau o giay 1.2 -> 5.2
    m, warnings = metrics([(1.2, 4.0), (4.5, 9.0)], q=1764079200.0, r=1764079204.0)
    assert m.thinking_time_s == 5.2 and warnings == []


def test_no_client_timestamps_means_empty_thinking_time_without_warning():
    m, warnings = metrics([(1.2, 4.0)])
    assert m.thinking_time_s is None and warnings == []


@pytest.mark.parametrize("q,r", [(100.0, 99.0), (100.0, None), (None, 100.0), (100.0, 100.0 + 601)])
def test_reversed_missing_one_or_too_far_timestamps_warn_and_leave_thinking_empty(q, r):
    m, warnings = metrics([(1.0, 3.0)], q=q, r=r)
    assert m.thinking_time_s is None and warnings == ["invalid_client_timestamps"]


def test_timestamps_equal_or_ten_minutes_apart_are_valid():
    assert metrics([(1.0, 3.0)], q=100.0, r=100.0)[0].thinking_time_s == 1.0
    assert metrics([(1.0, 3.0)], q=100.0, r=700.0)[0].thinking_time_s == 601.0


def test_pause_exactly_at_threshold_counts_and_just_below_does_not():
    assert metrics([(0.0, 1.0), (3.0, 4.0)])[0].long_pause_count == 1  # 2.0 >= 2.0
    assert metrics([(0.0, 1.0), (2.99, 4.0)])[0].long_pause_count == 0
    assert metrics([(0.0, 5.2), (7.2, 9.0)])[0].long_pause_count == 1  # 7.2 - 5.2 sai so nhi phan van la 2.0


def test_full_formulas_duration_speech_time_rate_and_fillers():
    m, _ = metrics([(1.2, 5.2), (7.2, 9.2)], limit=7.0, topic="java.collections")
    assert m.topic_id == "java.collections"
    assert m.answer_duration_s == 8.0  # 9.2 - 1.2
    assert m.long_pause_count == 1
    assert m.speech_time_s == 6.0  # 8.0 - quang ngung 2.0
    assert m.speech_rate_spm == 120.0  # 12 token / 6 s x 60
    assert m.filler_ratio == 0.25  # 3 / 12
    assert m.over_limit is True


def test_over_limit_is_empty_without_limit_and_false_when_within():
    assert metrics([(0.0, 4.0)])[0].over_limit is None
    assert metrics([(0.0, 4.0)], limit=4.0)[0].over_limit is False
    assert metrics([(0.0, 4.0)], limit=3.99)[0].over_limit is True


def test_overlapping_timings_are_merged():
    m, _ = metrics([(0.0, 5.0), (1.0, 2.0), (4.0, 6.0)], transcript="a b c")
    assert (m.answer_duration_s, m.speech_time_s, m.long_pause_count) == (6.0, 6.0, 0)
    assert [(s.start, s.end) for s in speech_spans([(4.0, 6.0), (0.0, 5.0), (1.0, 2.0)], 2.0)] == [(0.0, 6.0)]


def test_speech_spans_split_at_long_pauses_only():
    spans = speech_spans([(0.0, 1.0), (1.5, 2.0), (4.5, 5.0)], 2.0)
    assert [(s.start, s.end) for s in spans] == [(0.0, 2.0), (4.5, 5.0)]


def test_zero_length_word_still_gives_valid_span():
    assert speech_spans([(1.0, 1.0)], 2.0)[0].end > 1.0


def test_no_timings_leaves_every_metric_empty():
    m, warnings = metrics([], topic="t")
    assert m.topic_id == "t" and warnings == []
    assert m.model_dump(exclude={"topic_id"}) == dict.fromkeys(
        ["thinking_time_s", "answer_duration_s", "over_limit", "speech_time_s", "speech_rate_spm", "long_pause_count",
         "filler_ratio"])


def test_empty_transcript_gives_no_rate_and_no_filler_ratio():
    m, _ = metrics([(0.0, 3.0)], transcript="")
    assert m.speech_rate_spm is None and m.filler_ratio is None and m.answer_duration_s == 3.0


def test_fillers_unsupported_by_config_leaves_ratio_empty_with_warning():
    m, warnings = metrics([(0.0, 3.0)], config=replace(CONFIG, fillers_supported=False))
    assert m.filler_ratio is None and warnings == ["fillers_unsupported"] and m.speech_rate_spm is not None


def test_same_input_gives_identical_output_twice():
    args = ([(1.2, 5.2), (7.2, 9.2)], TWELVE, 10.0, 14.0, 7.0, "t")
    first = compute_turn_metrics(args[1], args[0], args[2], args[3], args[4], args[5], CONFIG)
    second = compute_turn_metrics(args[1], list(args[0]), args[2], args[3], args[4], args[5], CONFIG)
    assert first[0].model_dump() == second[0].model_dump() and first[1] == second[1]
