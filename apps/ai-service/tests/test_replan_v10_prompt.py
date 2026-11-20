"""Lap lai ke hoach (phase 05): request LLM Evaluator v10 (schema, khoi replan_context, parse swap) va provider chon prompt.
Gateway gia, khong goi LLM that."""
import asyncio

import pytest

import app.agents.evaluator_provider as provider
from app.agents.evaluator import LlmEvaluator
from app.agents.evaluator_input import ReplanContext
from app.agents.evaluator_output_models import EvaluatorOutputV10
from app.llm.gateway import LlmGateway
from app.llm.settings import load_llm_settings
from app.models_interview import Swap
from fakes.fake_llm import FakeOpenAI
from tests.test_llm_evaluator import inp, llm_json


def run(coro):
    return asyncio.run(coro)


def make10(script):
    async def no_sleep(_):
        return None

    client = FakeOpenAI(script)
    gw = LlmGateway(load_llm_settings({"LLM_API_KEY": "k"}), client, env={}, sleep=no_sleep, rng=lambda: 0.0)
    return LlmEvaluator(gw, prompt_version="v10"), client


def test_v10_request_schema_and_context_block_and_parsing():
    agent, client = make10([llm_json(next_action="next_topic", next_focus=None, difficulty_delta=0, action_reason="đủ",
                                     swap={"drop": "t4", "add": "alt1", "reason": "đã mạnh phần này"})])
    base = inp()
    base.replan_context = ReplanContext([("t4", "Index")], [("alt1", "Cache")], None, 1)
    raw, ev = run(agent.evaluate_with_raw(base))
    call = client.calls[0]
    assert agent.prompt_version == "v10" and call["response_format"]["json_schema"]["name"] == "EvaluatorOutputV10"
    assert "swap" in call["response_format"]["json_schema"]["schema"]["properties"]
    user = call["messages"][1]["content"]
    assert user.rstrip().endswith('"reserve": [{"id": "alt1", "title": "Cache"}]}')
    assert isinstance(raw, EvaluatorOutputV10) and (raw.swap.drop, raw.swap.add) == ("t4", "alt1") and not ev.degraded
    assert "replan_context" in call["messages"][0]["content"] and "swap" in call["messages"][0]["content"]


def test_v10_without_swap_field_or_with_garbage_still_grades():
    for extra in ({}, {"swap": "chuyen sang alt1"}, {"swap": 7}):
        agent, _ = make10([llm_json(next_action="next_topic", **extra)])
        raw, ev = run(agent.evaluate_with_raw(inp()))
        assert raw.swap is None and not ev.degraded and ev.scores.completeness == 3


@pytest.fixture()
def llm_mode(monkeypatch):
    monkeypatch.setenv("AGENT_EVALUATOR_MODE", "llm")
    monkeypatch.delenv("EVALUATOR_PROMPT_VERSION", raising=False)
    monkeypatch.setattr(provider, "get_gateway", lambda: object())
    monkeypatch.setattr(provider, "_llm", None)


def test_provider_picks_v10_only_for_hybrid_plus_replan_and_keeps_it_for_the_session(llm_mode, monkeypatch):
    monkeypatch.delenv("POLICY_MODE", raising=False)
    monkeypatch.setenv("REPLAN_ENABLED", "true")
    assert provider.get_evaluator().prompt_version == "v8"  # rules: co replan khong doi prompt
    monkeypatch.setenv("POLICY_MODE", "hybrid")
    first = provider.get_evaluator()
    assert first.prompt_version == "v10" and provider.get_evaluator() is first
    monkeypatch.setenv("REPLAN_ENABLED", "false")
    assert provider.get_evaluator().prompt_version == "v9"
    monkeypatch.delenv("REPLAN_ENABLED")
    assert provider.get_evaluator().prompt_version == "v9"


def test_replan_with_an_older_prompt_override_warns_once(llm_mode, monkeypatch, caplog):
    caplog.set_level("WARNING", logger="ai_service.evaluator")
    monkeypatch.setenv("POLICY_MODE", "hybrid")
    monkeypatch.setenv("REPLAN_ENABLED", "true")
    monkeypatch.setenv("EVALUATOR_PROMPT_VERSION", "v9")
    provider.get_evaluator()
    provider.get_evaluator()
    assert sum("REPLAN_ENABLED" in r.message for r in caplog.records) == 1


def test_swap_model_roundtrip():
    assert Swap.model_validate_json(Swap(drop="a", add="b", turn=2).model_dump_json()).reason == ""


def test_hybrid_replan_off_v9_request_is_unchanged():
    """Review M3: v9 (hybrid, REPLAN tat) gui dung request truoc phase 05; dat replan_context co y de chung minh chi
    cong phien ban prompt giu no ra ngoai."""
    from app.agents.evaluator_input import PolicyContext, build_messages
    agent, client = make10([llm_json(next_action="next_topic")])
    agent = LlmEvaluator(agent._gateway, prompt_version="v9")
    base = inp()
    base.policy_context = PolicyContext(1, False, 0, [], [], "normal", 2, {"min": 1, "max": 4})
    base.replan_context = ReplanContext([("t4", "X")], [("alt1", "Y")], None, 1)
    run(agent.evaluate_with_raw(base))
    call = client.calls[0]
    assert call["messages"] == build_messages(agent._prompt.text, base, True, True)  # goi 4 doi so nhu truoc phase 05
    assert call["response_format"]["json_schema"]["name"] == "EvaluatorOutputV9"
    assert "swap" not in call["response_format"]["json_schema"]["schema"]["properties"]
    assert "replan_context" not in call["messages"][1]["content"]
