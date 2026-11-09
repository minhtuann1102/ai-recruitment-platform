"""evals.ttft_breakdown: tach TTFT theo chang tu file phien, tach rieng luot fallback."""
from evals.ttft_breakdown import breakdown, fit_line, turn_rows


def _call(ttft, evaluator_ms, out_tokens=150, fallbacks=(), path="next-turn"):
    return {"path": path, "ttft_s": ttft, "total_s": (ttft or 0) + 1,
            "metadata": {"latency_ms": {"evaluator": evaluator_ms, "interviewer": 1200, "total": 0},
                         "usage": {"evaluator": {"input_tokens": 4000, "output_tokens": out_tokens}},
                         "fallbacks": list(fallbacks)}}


def _sessions(calls):
    return {"p1": {"calls": calls}}


def test_rows_split_evaluator_and_other_and_skip_turns_without_evaluator():
    calls = [_call(4.0, 3000), _call(None, 0), {"path": "next-turn", "ttft_s": 1.0,
                                                 "metadata": {"latency_ms": {"interviewer": 900, "total": 0}}},
             _call(3.0, 2000, path="start")]
    rows = turn_rows(_sessions(calls))
    assert len(rows) == 1
    assert rows[0]["kind"] == "normal" and rows[0]["evaluator"] == 3.0 and abs(rows[0]["other"] - 1.0) < 1e-9


def test_evaluator_timeout_turns_are_kept_out_of_the_normal_stages():
    # Evaluator het han: latency_ms.evaluator = 0, ca thoi gian cho nam trong ttft
    calls = [_call(3.0 + i * 0.1, 2000 + i * 100, out_tokens=100 + i * 10) for i in range(10)]
    calls.append(_call(11.0, 0, fallbacks=["evaluator_mock_heuristic"]))
    out = breakdown(turn_rows(_sessions(calls)))
    assert out["fallback"]["evaluator_mock_heuristic"]["turns"] == 1
    assert out["normal"]["turns"] == 10 and out["normal"]["stages"]["evaluator"]["p95"] <= 3.0
    assert out["ttft"]["p95"] == 11.0 and out["without_fallback_turns"]["p95"] < 4.0
    # hai pha chi bot o luot binh thuong; luot het han giu nguyen
    assert out["two_phase_estimate"]["p95"] == 11.0


def test_fit_line_recovers_slope_and_intercept():
    a, b = fit_line([100, 150, 200], [2.0, 2.5, 3.0])
    assert abs(a - 1.0) < 1e-9 and abs(b - 0.01) < 1e-9
    assert fit_line([1, 1, 1], [1, 2, 3]) is None and fit_line([1, 2], [1, 2]) is None


def test_empty_input():
    assert breakdown([]) == {"turns": 0}
