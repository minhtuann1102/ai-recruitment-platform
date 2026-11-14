"""Lap lai ke hoach (phase 05) trong sim: simulate_session (topic alt* qua effective_plan), /api/finalize, sim_replan_metrics.
Evaluator gia, khong goi LLM that."""
import asyncio

import app.turn_engine as engine
from app import mock_evaluator
from app.models_interview import CandidateState, Swap
from evals.cost_latency import load_pricing
from evals.personas import all_personas
from evals.sim_replan_metrics import replan_summary
from evals.simulate import run_all, summarize
from evals.simulator import RuleSimulator
from tests.test_replan import sw, v10


def run(coro):
    return asyncio.run(coro)


def test_finalize_and_report_see_the_effective_plan(client, monkeypatch):
    s = play(monkeypatch)["junior-java-average"]
    swap = s["swaps"][0]
    topics = {t["topic_id"]: t for t in s["report"]["topics"]}
    reserve = {t["id"]: t for t in s["plan"]["replan"]["reserve"]}
    assert swap["add"] in topics and swap["drop"] not in topics  # alt* thay t4 trong bao cao do sim goi /api/finalize
    assert topics[swap["add"]]["title"] == reserve[swap["add"]]["title"]
    keys = ("turn_number", "phase", "topic_id", "turn_kind", "difficulty", "question", "answer", "evaluation")
    body = {"session_id": "x", "track": "java_backend", "level": "junior", "plan": s["plan"], "end_reason": "plan_complete",
            "duration_s": 600, "turns": [{k: t[k] for k in keys} for t in s["turns"]],
            "state": CandidateState(phase="done", swaps=[Swap(**w) for w in s["swaps"]]).model_dump()}
    assert swap["add"] in [t["topic_id"] for t in client.post("/api/finalize", json=body).json()["topics"]]
    body["state"]["swaps"] = []  # state cu khong co swaps: nhu truoc phase 05 (alt* khong nam trong plan.phases)
    assert swap["add"] not in [t["topic_id"] for t in client.post("/api/finalize", json=body).json()["topics"]]


class FakeV10Evaluator:
    """Cham bang heuristic cua mock; luon de xuat next_topic + doi t4 lay alt1 (nhu LlmEvaluator v10)."""
    async def evaluate_with_raw(self, inp, collector=None):
        ev = mock_evaluator.evaluate(inp.answer, inp.question, inp.topic, inp.turn_kind, inp.turn_number)
        return v10(sw("t4", "alt1"), next_action="next_topic"), ev

    async def evaluate(self, inp, collector=None):
        return (await self.evaluate_with_raw(inp, collector))[1]


def play(monkeypatch, replan="true", mode="hybrid"):
    monkeypatch.setenv("POLICY_MODE", mode)
    monkeypatch.setenv("REPLAN_ENABLED", replan)
    monkeypatch.setattr(engine, "get_evaluator", lambda: FakeV10Evaluator())
    return run(run_all(["junior-java-average"], RuleSimulator()))


def test_sim_runs_a_swapped_session_end_to_end_and_measures_it(monkeypatch):
    sessions = play(monkeypatch)
    s = sessions["junior-java-average"]
    assert [(w["drop"], w["add"]) for w in s["swaps"]] == [("t4", "alt1")]
    ids = [t["topic_id"] for t in s["turns"]]
    assert "alt1" in ids and "t4" not in ids  # _topic() tim topic alt1 qua effective_plan: simulator tra loi duoc
    results = [t["swap_result"] for t in s["turns"] if t["swap_result"]]
    assert results.count("applied") == 1 and set(results) <= {"applied", "budget", "not_applicable"}
    stats = summarize(sessions, all_personas(), load_pricing())["replan"]
    assert stats["swap_sessions"] == stats["sessions_with_reserve"] == 1 and stats["swap_rate"] == 1.0
    assert stats["swaps"] == 1 and stats["jd_priority_violations"] == 0 and stats["swap_results"]["applied"] == 1
    assert stats["scored_topics"] >= 3 and stats["jd_assessed_rate"] is None  # khong co JD


def test_sim_metric_flags_a_swap_that_dropped_a_jd_priority_topic():
    s = {"turns": [{"topic_id": "t2", "swap_result": "applied", "evaluation": None}],
         "plan": {"replan": {"reserve": [{"id": "alt1"}], "keep_ids": ["t4"]}},
         "swaps": [{"drop": "t4", "add": "alt1", "turn": 2, "reason": ""}], "report": None}
    assert replan_summary({"p": s})["jd_priority_violations"] == 1
    assert replan_summary({})["swap_rate"] is None


def test_sim_with_the_flag_off_matches_a_session_without_swap_proposals(monkeypatch):
    monkeypatch.setenv("POLICY_MODE", "hybrid")
    monkeypatch.setenv("REPLAN_ENABLED", "false")

    class NoSwap(FakeV10Evaluator):
        async def evaluate_with_raw(self, inp, collector=None):
            raw, ev = await super().evaluate_with_raw(inp, collector)
            return raw.model_copy(update={"swap": None}), ev
    keys = ("turn_number", "phase", "topic_id", "action", "difficulty", "decided_by", "swap_result", "question")
    runs = []
    for evaluator in (FakeV10Evaluator, NoSwap):
        monkeypatch.setattr(engine, "get_evaluator", lambda e=evaluator: e())
        s = run(run_all(["junior-java-average"], RuleSimulator()))["junior-java-average"]
        assert s["swaps"] == [] and s["plan"]["replan"] is None
        runs.append([{k: t[k] for k in keys} for t in s["turns"]])
    assert runs[0] == runs[1] and all(t["swap_result"] is None for t in runs[0])
