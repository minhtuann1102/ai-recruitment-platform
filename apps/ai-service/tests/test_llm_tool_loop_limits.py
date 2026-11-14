"""Tran cua vong lap tool: cong cu treo, qua nhieu tool_calls, length retry, latch chi dung loi that, hedge + ngan sach."""
import asyncio
import time

import pytest

from app.llm import tool_loop
from app.llm.errors import LlmError, LlmTimeoutError
from app.llm.usage import UsageCollector
from fakes.fake_llm import Slow, limit_agent, reply, status_error, tool_reply
from test_llm_tool_loop import CALL, MSGS, OK, Out, _latch, go, make  # noqa: F401


def test_slow_tool_times_out_inside_budget_and_loop_still_answers():
    async def slow(name, args):
        await asyncio.sleep(2.0)
        return "late"

    gw, client = make([CALL(), OK])
    t = time.perf_counter()
    res, _ = go(gw, slow, budget_s=1.0, step_deadline_s=0.3)
    assert time.perf_counter() - t < 1.0 + 0.5
    assert client.calls[1]["messages"][-1]["content"] == "error: tool_timeout" and res.data.answer == "ok"


def test_many_tool_calls_in_one_reply_run_only_up_to_quota():
    many = tool_reply([(f"c{i}", "lookup", '{"query": "q"}') for i in range(30)])
    gw, client = make([many, OK])
    res, calls = go(gw, max_calls=2)
    tool_msgs = [m for m in client.calls[1]["messages"] if m["role"] == "tool"]
    assert len(calls) == 2 and res.tool_calls == 2 and len(tool_msgs) == 30
    assert [m["content"] for m in tool_msgs[2:]] == ["error: call_limit"] * 28
    assert [c["tool_choice"] for c in client.calls] == ["auto", "none"]


def test_only_query_reaches_tool_and_result_is_capped():
    async def big(name, args):
        assert args == {"query": "gil"}
        return "y" * 10000

    gw, client = make([CALL(args='{"query": "gil", "extra": "inject"}'), OK])
    go(gw, big)
    assert len(client.calls[1]["messages"][-1]["content"]) == tool_loop.MAX_RESULT_CHARS


def test_length_retry_in_tool_step_cannot_eat_final_reserve(monkeypatch):
    limit_agent(monkeypatch, "evaluator", 5.0, 6.0)
    gw, client = make([Slow(0.4, reply("x", finish_reason="length")), Slow(5.0, CALL()), OK])
    t = time.perf_counter()
    with pytest.raises(LlmError):  # buoc tool het han (0.3 + 1.5 s) du length retry; khong den buoc none
        go(gw, step_deadline_s=0.3, budget_s=6.0)
    assert time.perf_counter() - t < 0.3 + tool_loop.FINAL_RESERVE_S + 0.5


def test_not_found_model_and_transient_errors_do_not_latch():
    for err in (status_error(404, message="model not found"), status_error(400, message="bad request"),
                status_error(429), status_error(500)):
        tool_loop.reset_tools_latch()
        gw, _ = make([err] * 3)
        with pytest.raises(LlmError, match="tool_loop_failed"):
            go(gw)
        assert tool_loop.tools_supported()


def test_latch_logs_warning(caplog):
    gw, _ = make([status_error(404, message="No endpoints found that support tool use")])
    with caplog.at_level("WARNING", logger="ai_service.llm"), pytest.raises(LlmError):
        go(gw)
    assert "tools_unsupported_latched" in caplog.text


def test_budget_args_must_come_together():
    gw, _ = make([OK])
    with pytest.raises(ValueError):
        asyncio.run(gw.complete("evaluator", MSGS, Out, budget_s=1.0))
    with pytest.raises(ValueError):
        asyncio.run(gw.complete("evaluator", MSGS, Out, budget_started=time.perf_counter()))


def test_schema_required():
    gw, _ = make([OK])
    with pytest.raises(AssertionError):
        asyncio.run(tool_loop.complete_with_tools(gw, "evaluator", MSGS, None, [], None, max_calls=1,
                                                  step_deadline_s=1, budget_started=0.0, budget_s=1))


def test_hedge_still_applies_to_first_call_with_cap_first(monkeypatch):
    limit_agent(monkeypatch, "evaluator", 3.0, 5.0)
    gw, client = make([Slow(1.0, OK), OK], LLM_HEDGE_EVALUATOR="0.1")
    gw._env = {"LLM_HEDGE_EVALUATOR": "0.1"}
    col = UsageCollector()
    t = time.perf_counter()
    res, _ = go(gw, budget_s=5.0, collector=col)
    assert len(client.calls) == 2 and time.perf_counter() - t < 0.8 and res.record.attempts == 2
