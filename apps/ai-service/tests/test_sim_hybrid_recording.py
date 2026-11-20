"""Sim do duoc policy lai (phase 04, audit C2): recorder chuyen de xuat qua evaluate_with_raw, simulate_session chep 5 khoa
TurnInfo, sim_policy_metrics tinh agreement / overrule. policy_action la hanh dong TRUOC apply (next_topic, khong ask_main)."""
import asyncio

import pytest

import app.turn_engine as engine
from app import mock_evaluator
from evals.personas import all_personas
from evals.sim_policy_metrics import hybrid_policy
from evals.simulate import run_all, summarize
from evals.simulate_session import POLICY_KEYS
from evals.cost_latency import load_pricing
from evals.simulator import RuleSimulator
from evals.turn_source_recorder import record_documents
from tests.test_policy_hybrid import prop

IDS = ["junior-java-average"]


class FakeV9Evaluator:
    """Cham bang heuristic cua mock, luon de xuat next_topic (nhu LlmEvaluator v9: evaluate_with_raw tra output V9)."""
    async def evaluate_with_raw(self, inp, collector=None):
        ev = mock_evaluator.evaluate(inp.answer, inp.question, inp.topic, inp.turn_kind, inp.turn_number)
        return prop("next_topic", None, 0, "đủ ý cho topic này"), ev

    async def evaluate(self, inp, collector=None):
        return (await self.evaluate_with_raw(inp, collector))[1]


class EvaluateOnly:
    async def evaluate(self, inp, collector=None):
        return (await FakeV9Evaluator().evaluate_with_raw(inp, collector))[1]


def play(monkeypatch, mode, evaluator=FakeV9Evaluator):
    if mode:
        monkeypatch.setenv("POLICY_MODE", mode)
    else:
        monkeypatch.delenv("POLICY_MODE", raising=False)
    monkeypatch.setattr(engine, "get_evaluator", lambda: evaluator())
    return asyncio.run(run_all(IDS, RuleSimulator()))


def test_hybrid_session_records_decisions_and_pre_apply_policy_action(monkeypatch):
    sessions = play(monkeypatch, "hybrid")
    turns = [t for t in sessions[IDS[0]]["turns"] if t["decided_by"]]
    assert turns and all(set(POLICY_KEYS) <= set(t) for t in sessions[IDS[0]]["turns"])
    assert any(t["decided_by"] == "llm" and t["proposed_action"] == "next_topic" for t in turns)
    assert {t["policy_action"] for t in turns if t["policy_action"]} <= {"follow_up", "hint", "clarify", "next_topic"}
    assert any(t["policy_action"] == "next_topic" and t["action"] == "ask_main" for t in turns)  # truoc apply
    stats = summarize(sessions, all_personas(), load_pricing())["hybrid_policy"]
    assert stats["proposal_turns"] > 0 and 0 <= stats["agreement"] <= 1 and 0 <= stats["overrule_rate"] <= 1
    assert stats["decided_by"].get("llm", 0) > 0


def test_rules_session_has_no_policy_fields_and_empty_metrics(monkeypatch):
    sessions = play(monkeypatch, None)
    assert all(t[k] is None for t in sessions[IDS[0]]["turns"] for k in POLICY_KEYS)
    stats = hybrid_policy(sessions)
    assert stats["proposal_turns"] == 0 and stats["agreement"] is None and stats["overrule_rate"] is None


def test_wrapper_without_passthrough_would_make_hybrid_equal_rules(monkeypatch):
    # evaluator chi co `evaluate`: turn_engine khong thay de xuat -> no_proposal. Khoa hanh vi de recorder khong thoai hoa
    sessions = play(monkeypatch, "hybrid", evaluator=EvaluateOnly)
    turns = [t for t in sessions[IDS[0]]["turns"] if t["decided_by"]]
    assert turns and all(t["proposed_action"] is None and t["overrule_reason"] == "no_proposal" for t in turns)


def test_hybrid_policy_metrics_exclude_forced_turns_and_compute_rates():
    turns = [
        {"decided_by": "llm", "proposed_action": "follow_up", "policy_action": "follow_up", "overrule_reason": None},
        {"decided_by": "llm", "proposed_action": "next_topic", "policy_action": "follow_up", "overrule_reason": None},
        {"decided_by": "policy", "proposed_action": "follow_up", "policy_action": "hint",
         "overrule_reason": "action_not_allowed"},
        {"decided_by": "forced", "proposed_action": "follow_up", "policy_action": None, "overrule_reason": None},
        {"decided_by": "policy", "proposed_action": None, "policy_action": "next_topic",
         "overrule_reason": "no_proposal"},
        {"decided_by": None, "proposed_action": None, "policy_action": None, "overrule_reason": None}]
    stats = hybrid_policy({"s": {"turns": turns}})
    assert stats["decided_turns"] == 5 and stats["forced_turns"] == 1 and stats["proposal_turns"] == 3
    assert stats["agreement"] == pytest.approx(0.333, abs=1e-3) and stats["overrule_rate"] == pytest.approx(0.333, abs=1e-3)
    assert stats["overrule_reasons"] == {"action_not_allowed": 1}


def test_recorder_passes_raw_through_and_tolerates_evaluate_only_inner():
    async def go():
        with record_documents():
            wrapped = engine.get_evaluator()
            assert hasattr(wrapped, "evaluate_with_raw")
    real = engine.get_evaluator
    engine.get_evaluator = lambda: EvaluateOnly()
    try:
        asyncio.run(go())
    finally:
        engine.get_evaluator = real


def test_invalid_proposals_count_as_overrules_and_llm_rate_excludes_sensitive_kind():
    base = {"policy_action": "follow_up"}
    turns = [
        {**base, "decided_by": "llm", "proposed_action": "follow_up", "overrule_reason": None},
        {**base, "decided_by": "policy", "proposed_action": "invalid", "overrule_reason": "action_not_allowed"},
        {**base, "decided_by": "policy", "proposed_action": "invalid", "overrule_reason": None},  # van la bac
        {**base, "decided_by": "policy", "proposed_action": "next_topic", "overrule_reason": "sensitive_kind"}]
    stats = hybrid_policy({"s": {"turns": turns}})
    assert stats["overrule_rate"] == 0.75 and stats["overrule_rate_llm"] == pytest.approx(0.667, abs=1e-3)
    assert stats["proposed_actions"]["invalid"] == 2
