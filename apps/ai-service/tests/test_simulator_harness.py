"""Harness tang 3 (FR-AI-082): persona, simulator quy tac, chay phien in-process, chi so va chi phi.

Agent mock + simulator quy tac: chi kiem harness chay dung, KHONG phai so do chat luong cham.
"""
import asyncio

import pytest

from evals.cost_latency import load_pricing, percentile, session_cost, session_usage
from evals.personas import all_personas, matrix
from evals.sim_metrics import slope
from evals.simulate import run_all, summarize
from evals.simulator import INJECTION, RuleSimulator, apply_behavior


def test_personas_matrix_and_disjoint_knowledge():
    ps = all_personas()
    assert len(matrix()) == 24 and len(ps) == 29
    for p in ps.values():
        sets = [set(p.knows_well), set(p.knows_partially), set(p.does_not_know)]
        assert not (sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2])
    strong, weak = ps["junior-java-strong"], ps["junior-java-weak"]
    assert len(strong.knows_well) > len(weak.knows_well) and len(weak.does_not_know) > len(strong.does_not_know)


def test_behaviors_shape_answers():
    p = all_personas()["junior-java-average+injection_attempt"]
    assert apply_behavior("Trả lời", p).endswith(INJECTION)
    assert apply_behavior("Một hai ba", all_personas()["middle-nodejs-average+one_word_answers"]) == "Một"


def test_math_helpers():
    assert slope([1, 2, 3]) == 1.0 and slope([3, 2, 1]) == -1.0 and slope([2]) == 0.0
    assert percentile([1, 2, 3, 4], 50) == 2 and percentile([1, 2, 3, 4], 95) == 4 and percentile([], 50) is None
    assert percentile(list(range(1, 21)), 95) == 19 and percentile(list(range(1, 375)), 50) == 187
    session = {"calls": [{"metadata": {"usage": {"evaluator": {"input_tokens": 1_000_000, "output_tokens": 0}}}},
                         {"metadata": {"usage": {"evaluator": {"input_tokens": 0, "output_tokens": 1_000_000}}}}]}
    assert session_usage(session) == {"evaluator": {"input_tokens": 1_000_000, "output_tokens": 1_000_000}}
    assert session_cost(session_usage(session), load_pricing()) == pytest.approx(0.75)


def test_harness_runs_sessions_end_to_end_in_process():
    ids = ["junior-java-strong", "junior-java-average", "junior-java-weak",
           "junior-java-average+injection_attempt", "junior-nodejs-strong+end_early"]
    sessions = asyncio.run(run_all(ids, RuleSimulator()))
    assert set(sessions) == set(ids)
    assert len(sessions["junior-nodejs-strong+end_early"]["turns"]) == 3
    assert sessions["junior-nodejs-strong+end_early"]["report"]["session"]["end_reason"] == "candidate_ended"
    summary = summarize(sessions, all_personas(), load_pricing())
    assert summary["constraints"]["sessions_over_turn_cap"] == 0
    assert summary["constraints"]["follow_up_limit_violations"] == 0
    assert summary["constraints"]["all_phases_reached"] == 1.0
    fin = sessions["junior-java-strong"]["calls"][-1]
    assert fin["path"] == "finalize" and "fallbacks" in fin["metadata"]
    assert summary["injection"] == {"pairs": 1, "no_score_gain": 1.0}
    assert summary["discrimination"]["groups"] == 1 and summary["ops"]["ttft_s"]["n"] > 10
    assert all(c["path"] != "next-turn" or "ttft_s" in c for s in sessions.values() for c in s["calls"])


def test_llm_simulator_uses_simulator_agent_and_keeps_behavior():
    from app.llm.gateway import LlmGateway
    from app.llm.settings import load_llm_settings
    from evals.simulator import LlmSimulator
    from fakes.fake_llm import FakeOpenAI, reply

    client = FakeOpenAI([reply("Dạ em nghĩ là dùng index B-tree ạ")])
    gw = LlmGateway(load_llm_settings({"LLM_API_KEY": "k"}), client, env={"LLM_MODEL_SIMULATOR": "other/model"})
    p = all_personas()["junior-java-average+injection_attempt"]
    text = asyncio.run(LlmSimulator(gw).answer(p, None, "Câu hỏi?", "ask_main"))
    assert text.startswith("Dạ em nghĩ") and text.endswith(INJECTION)
    assert client.calls[0]["model"] == "other/model" and client.calls[0]["temperature"] == 0.8
