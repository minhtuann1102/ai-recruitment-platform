"""Sim dem de xuat tho cua Evaluator v10/v11 (evals/sim_agent_counters): phan biet LLM tra null voi code bo de xuat.
Evaluator gia, khong goi LLM that."""
import asyncio

import app.turn_engine as engine
from app import mock_evaluator
from evals.sim_agent_counters import counters_delta, snapshot
from evals.simulate import run_all
from evals.simulator import RuleSimulator
from tests.test_agent_notes import note, v11
from tests.test_replan import sw, v10


class FakeEvaluator:
    """Cham bang heuristic cua mock; output tho co dinh (v10 / v11) do test chon."""
    prompt_version = "v11"  # nhu LlmEvaluator v10+: prompt render replan_context

    def __init__(self, raw):
        self.raw = raw

    async def evaluate_with_raw(self, inp, collector=None):
        return self.raw, mock_evaluator.evaluate(inp.answer, inp.question, inp.topic, inp.turn_kind, inp.turn_number)

    async def evaluate(self, inp, collector=None):
        return (await self.evaluate_with_raw(inp, collector))[1]


def counted(monkeypatch, raw, notes="false"):
    monkeypatch.setenv("POLICY_MODE", "hybrid")
    monkeypatch.setenv("REPLAN_ENABLED", "true")
    monkeypatch.setenv("AGENT_NOTES_ENABLED", notes)
    monkeypatch.setattr(engine, "get_evaluator", lambda: FakeEvaluator(raw))
    before = snapshot()
    asyncio.run(run_all(["junior-java-average"], RuleSimulator()))
    return counters_delta(before, snapshot(), in_process=True)


def test_null_swap_counts_as_llm_null_not_as_rejection(monkeypatch):
    c = counted(monkeypatch, v10(None, next_action="next_topic"))["replan"]
    assert set(c["offered"]) == {"null"} and c["offered"]["null"] > 0 and c["results"] == {}


def test_proposed_swap_counts_as_proposed_even_when_also_proposed_off_context(monkeypatch):
    # LLM gia luon tra swap, ca o luot khong co replan_context: results nhieu hon offered, "null" van = 0 (review H1)
    c = counted(monkeypatch, v10(sw("t4", "alt1"), next_action="next_topic"))["replan"]
    assert c["offered"].get("proposed", 0) > 0 and "null" not in c["offered"]
    assert c["results"].get("applied") == 1 and sum(c["results"].values()) >= c["offered"]["proposed"]


def test_turn_without_raw_output_is_not_counted_as_llm_null(monkeypatch):
    # raw None: mock evaluation khong degraded nen la "skipped" (nhu precheck); LLM loi thi ev.degraded -> "degraded"
    assert set(counted(monkeypatch, None)["replan"]["offered"]) == {"skipped"}
    monkeypatch.setattr(mock_evaluator, "evaluate", lambda *a: _degraded(*a))
    assert set(counted(monkeypatch, None)["replan"]["offered"]) == {"degraded"}


_real_mock = mock_evaluator.evaluate


def _degraded(*args):
    return _real_mock(*args).model_copy(update={"degraded": True})


def test_offered_needs_hybrid_replan_and_v10_prompt(monkeypatch):
    raw = v10(None, next_action="next_topic")
    monkeypatch.setattr(FakeEvaluator, "prompt_version", "v9")  # ghi de < v10: prompt khong co replan_context
    assert counted(monkeypatch, raw)["replan"]["offered"] == {}
    monkeypatch.setattr(FakeEvaluator, "prompt_version", "v11")
    monkeypatch.setenv("REPLAN_ENABLED", "false")
    monkeypatch.setattr(engine, "get_evaluator", lambda: FakeEvaluator(raw))
    before = snapshot()
    asyncio.run(run_all(["junior-java-average"], RuleSimulator()))
    assert counters_delta(before, snapshot(), in_process=True)["replan"]["offered"] == {}


def test_notes_proposed_counts_recorded_and_dropped(monkeypatch):
    none = counted(monkeypatch, v11(None), notes="true")["notes"]
    assert none == {"recorded": {}, "dropped": {}, "proposed": 0}  # LLM luon null: khong co gi de dem
    some = counted(monkeypatch, v11(note()), notes="true")["notes"]
    assert some["recorded"].get("to_verify", 0) > 0 and some["proposed"] >= some["recorded"]["to_verify"]


def test_remote_service_reports_none():
    assert counters_delta(snapshot(), snapshot(), in_process=False) is None
