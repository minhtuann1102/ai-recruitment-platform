"""Vong lap tool calling cua gateway voi LLM gia: tham so request, tool_call_id, tran buoc, repair, ngan sach, latch."""
import asyncio
import json
import time

import pytest
from pydantic import BaseModel

from app.llm import tool_loop
from app.llm.errors import LlmError, LlmOutputError, LlmTimeoutError
from app.llm.gateway import LlmGateway
from app.llm.settings import load_llm_settings
from app.llm.tool_loop import complete_with_tools
from app.llm.usage import UsageCollector
from fakes.fake_llm import FakeOpenAI, Slow, limit_agent, reply, status_error, tool_reply

MSGS = [{"role": "system", "content": "s"}, {"role": "user", "content": "q"}]
TOOLS = [{"type": "function", "function": {"name": "lookup", "strict": True, "parameters": {
    "type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"],
    "additionalProperties": False}}}]
OK = reply('{"answer": "ok"}')
CALL = lambda cid="c1", args='{"query": "gil"}': tool_reply([(cid, "lookup", args)])  # noqa: E731


class Out(BaseModel):
    answer: str


@pytest.fixture(autouse=True)
def _latch():
    tool_loop.reset_tools_latch()
    yield
    tool_loop.reset_tools_latch()


def make(script, **env):
    llm = load_llm_settings({"LLM_API_KEY": "k", **env})

    async def no_sleep(_):
        pass

    client = FakeOpenAI(script)
    return LlmGateway(llm, client, env={}, sleep=no_sleep, rng=lambda: 0.0), client


def go(gw, run_tool=None, *, max_calls=2, step_deadline_s=5.0, budget_s=10.0, collector=None, started=None):
    calls = []

    async def default_tool(name, args):
        calls.append((name, args))
        return "chunk"

    res = asyncio.run(complete_with_tools(
        gw, "evaluator", list(MSGS), Out, TOOLS, run_tool or default_tool, max_calls=max_calls,
        step_deadline_s=step_deadline_s, budget_started=time.perf_counter() if started is None else started,
        budget_s=budget_s, prompt_version="v8", collector=collector))
    return res, calls


def test_no_tool_call_sends_full_params_and_returns_data():
    gw, client = make([OK])
    res, calls = go(gw)
    p = client.calls[0]
    assert res.data == Out(answer="ok") and res.tool_calls == 0 and calls == []
    assert p["tools"] == TOOLS and p["tool_choice"] == "auto" and p["parallel_tool_calls"] is False
    assert p["response_format"]["json_schema"]["strict"]
    assert p["extra_body"]["provider"] == {"require_parameters": True}  # base_url mac dinh la OpenRouter


def test_non_openrouter_base_url_has_no_provider_block():
    gw, client = make([OK], LLM_BASE_URL="https://api.openai.com/v1")
    go(gw)
    assert "extra_body" not in client.calls[0]


def test_reasoning_extra_body_kept_next_to_provider():
    gw, client = make([OK])
    gw._env = {"LLM_REASONING_EVALUATOR": "low"}
    go(gw)
    assert client.calls[0]["extra_body"] == {"reasoning": {"effort": "low"}, "provider": {"require_parameters": True}}


def test_one_tool_call_answers_right_id_and_counts_usage():
    gw, client = make([CALL("abc"), OK])
    col = UsageCollector()
    res, calls = go(gw, collector=col)
    assert calls == [("lookup", {"query": "gil"})] and res.tool_calls == 1 and res.record.tool_calls == 1
    msgs = client.calls[1]["messages"]
    assert msgs[-2]["tool_calls"][0]["id"] == "abc" and msgs[-2]["content"] is None
    assert msgs[-1] == {"role": "tool", "tool_call_id": "abc", "content": "chunk"}
    assert res.record.input_tokens == 20 and res.record.output_tokens == 10
    assert col.records == [res.record] and col.to_metadata()["usage"]["evaluator"]["tool_calls"] == 1


def test_metadata_has_no_tool_calls_key_when_none_used():
    gw, _ = make([OK])
    col = UsageCollector()
    go(gw, collector=col)
    assert "tool_calls" not in col.to_metadata()["usage"]["evaluator"]


def test_tools_byte_identical_every_step():
    gw, client = make([CALL(), CALL("c2"), OK])
    go(gw, max_calls=3)
    assert len({json.dumps(c["tools"], sort_keys=False) for c in client.calls}) == 1 and len(client.calls) == 3


def test_over_max_calls_final_step_is_tool_choice_none():
    gw, client = make([CALL(), OK])
    res, _ = go(gw, max_calls=1)
    assert [c["tool_choice"] for c in client.calls] == ["auto", "none"] and res.tool_calls == 1


def test_tool_calls_after_none_is_output_error_and_failed_record_kept():
    gw, _ = make([CALL(), CALL("c2")])
    col = UsageCollector()
    with pytest.raises(LlmOutputError):
        go(gw, max_calls=1, collector=col)
    assert len(col.records) == 1 and col.records[0].fallback == "tool_loop_failed" and col.records[0].tool_calls == 1


def test_repair_uses_tool_choice_none_and_repair_with_tool_calls_fails():
    gw, client = make([reply("not json"), OK])
    res, _ = go(gw)
    assert res.record.repaired and client.calls[1]["tool_choice"] == "none" and client.calls[1]["temperature"] == 0
    gw, _ = make([reply("not json"), CALL()])
    with pytest.raises(LlmOutputError):
        go(gw)


def test_tool_exception_becomes_error_string():
    async def boom(name, args):
        raise RuntimeError("secret detail")

    gw, client = make([CALL(), OK])
    res, _ = go(gw, boom)
    assert res.data.answer == "ok" and client.calls[1]["messages"][-1]["content"] == "error: tool_failed"


@pytest.mark.parametrize("name,args,expected", [
    ("lookup", "{bad", "error: invalid_arguments"), ("lookup", "[1]", "error: invalid_arguments"),
    ("lookup", '{"query": "   "}', "error: empty_query"), ("lookup", "{}", "error: empty_query"),
    ("other", '{"query": "x"}', "error: unknown_tool"), ("lookup", '{"query": "' + "a" * 2000 + '"}',
                                                          "error: invalid_arguments")])
def test_bad_tool_calls_do_not_run_tool(name, args, expected):
    gw, client = make([tool_reply([("c1", name, args)]), OK])
    res, calls = go(gw)
    assert calls == [] and client.calls[1]["messages"][-1]["content"] == expected and res.tool_calls == 1


def test_long_query_cut_to_200_chars():
    gw, _ = make([CALL(args=json.dumps({"query": "x" * 500})), OK])
    _, calls = go(gw)
    assert len(calls[0][1]["query"]) == 200


def test_parallel_extra_calls_each_answered():
    gw, client = make([tool_reply([("a", "lookup", '{"query": "1"}'), ("b", "lookup", '{"query": "2"}')]), OK])
    go(gw, max_calls=4)
    tool_msgs = [m for m in client.calls[1]["messages"] if m["role"] == "tool"]
    assert [m["tool_call_id"] for m in tool_msgs] == ["a", "b"]


def test_slow_first_step_stays_inside_budget_and_times_out(monkeypatch):
    limit_agent(monkeypatch, "evaluator", 2.0, 1.0)
    gw, _ = make([Slow(1.5, CALL()), Slow(1.5, OK)])  # thang 1 s ~ 10 s that
    col = UsageCollector()
    t = time.perf_counter()
    with pytest.raises(LlmTimeoutError):
        go(gw, budget_s=1.0, step_deadline_s=0.3, collector=col)
    assert time.perf_counter() - t < 1.0 + 0.5 and col.records[0].latency_ms >= 1


def test_exhausted_budget_caps_first_call_too():
    gw, client = make([OK])
    with pytest.raises(LlmTimeoutError):
        go(gw, budget_s=0.5, started=time.perf_counter() - 1.0)
    assert client.calls == []


def test_complete_with_budget_started_caps_first_call(monkeypatch):
    limit_agent(monkeypatch, "evaluator", 5.0, 5.0)
    gw, client = make([OK])
    with pytest.raises(LlmTimeoutError):
        asyncio.run(gw.complete("evaluator", MSGS, Out, budget_started=time.perf_counter() - 2.0, budget_s=1.0))
    assert client.calls == []
    gw, client = make([OK])  # khong truyen thi lan dau van du han nhu cu
    assert asyncio.run(gw.complete("evaluator", MSGS, Out)).data.answer == "ok"


@pytest.mark.parametrize("err", [status_error(404, message="No endpoints found that support tool use"), status_error(
    400, message="No endpoints found that can handle the requested parameters, support tools")])
def test_unsupported_combo_latches_and_next_call_sends_nothing(err):
    gw, client = make([err])
    with pytest.raises(LlmError, match="tools_unsupported"):
        go(gw)
    assert not tool_loop.tools_supported() and len(client.calls) == 1
    with pytest.raises(LlmError, match="tools_unsupported"):
        go(gw)
    assert len(client.calls) == 1


def test_other_provider_errors_map_to_llm_error_without_latch():
    gw, _ = make([status_error(401)])
    with pytest.raises(LlmError, match="tool_loop_failed"):
        go(gw)
    assert tool_loop.tools_supported()


def test_metrics_count_tool_calls_and_unsupported():
    from app import metrics
    from prometheus_client import REGISTRY
    before = REGISTRY.get_sample_value("ai_llm_tool_calls_total", {"agent": "evaluator"}) or 0
    gw, _ = make([CALL(), OK])
    col = UsageCollector()
    go(gw, collector=col)
    metrics.record_request("next-turn", "ok", "", 0.1, col, None)
    assert REGISTRY.get_sample_value("ai_llm_tool_calls_total", {"agent": "evaluator"}) == before + 1
    unsupported = REGISTRY.get_sample_value("ai_llm_tools_unsupported_total") or 0
    gw, _ = make([status_error(404, message="No endpoints found that support tools")])
    with pytest.raises(LlmError):
        go(gw)
    assert REGISTRY.get_sample_value("ai_llm_tools_unsupported_total") == unsupported + 1
