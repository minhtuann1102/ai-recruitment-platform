"""Hedge request (docs 08 muc 9.2): lan goi dau cham qua N s thi gui them mot request, lay ket qua ve truoc.

Thoi gian that rat ngan (vai chuc ms), khong goi LLM.
"""
import asyncio
import time

import pytest
from pydantic import BaseModel

from app.agents.evaluator import LlmEvaluator
from app.llm.errors import ConfigError, LlmTimeoutError
from app.llm.gateway import LlmGateway
from app.llm.retry import call_with_retry
from app.llm.settings import agent_settings, load_llm_settings
from app.llm.usage import UsageCollector
from fakes.fake_llm import FakeOpenAI, Slow, limit_agent, reply, status_error, timeout_error

ENV = {"LLM_API_KEY": "k"}
MSGS = [{"role": "user", "content": "x"}]


class Out(BaseModel):
    answer: str


def run(coro):
    return asyncio.run(coro)


class Script:
    """Moi lan goi lay mot phan tu: (giay cho, ket qua hoac loi). Ghi lan nao bi huy."""

    def __init__(self, items):
        self.items, self.calls, self.cancelled = list(items), 0, 0

    async def __call__(self):
        self.calls += 1
        delay, item = self.items.pop(0)
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            self.cancelled += 1
            raise
        if isinstance(item, BaseException):
            raise item
        return item


async def _no_sleep(_):
    return None


def hedged(fn, **kw):
    return run(call_with_retry(fn, sleep=_no_sleep, rng=lambda: 0.0, **kw))


def test_fast_first_request_sends_no_hedge():
    fn = Script([(0.0, "ok")])
    assert hedged(fn, timeout_s=1.0, hedge_after_s=0.05) == ("ok", 1) and fn.calls == 1


def test_slow_first_request_is_hedged_and_cancelled_when_hedge_wins():
    fn = Script([(1.0, "cham"), (0.0, "nhanh")])
    started = time.perf_counter()
    assert hedged(fn, timeout_s=2.0, budget_s=3.0, hedge_after_s=0.05) == ("nhanh", 2)
    assert time.perf_counter() - started < 0.5 and fn.cancelled == 1


def test_first_request_still_wins_when_hedge_fails():
    fn = Script([(0.1, "dau"), (0.0, timeout_error())])
    assert hedged(fn, timeout_s=1.0, hedge_after_s=0.02) == ("dau", 2)


def test_error_before_hedge_goes_to_normal_retry_without_hedging_again():
    fn = Script([(0.0, timeout_error()), (0.08, "ok")])
    assert hedged(fn, timeout_s=1.0, hedge_after_s=0.02) == ("ok", 2) and fn.calls == 2


def test_hedge_shares_the_retry_budget():
    # hedge tra loi sau 0.3 s nhung chi con 0.2 - 0.05 s ngan sach: phai bi cat, khong duoc thang
    fn = Script([(1.0, "x"), (0.3, "y"), (0.0, "khong duoc goi")])
    started = time.perf_counter()
    with pytest.raises(LlmTimeoutError):
        hedged(fn, timeout_s=0.5, budget_s=0.2, hedge_after_s=0.05)
    assert time.perf_counter() - started < 0.7 and fn.calls == 2 and fn.cancelled == 2


def test_without_budget_hedge_ends_within_the_call_timeout():
    fn = Script([(1.0, "x"), (0.3, "y")])
    with pytest.raises(LlmTimeoutError):
        hedged(fn, timeout_s=0.2, max_retries=0, hedge_after_s=0.05)
    assert fn.calls == 2


def test_both_requests_fail_then_retry_counts_every_request():
    fn = Script([(0.1, timeout_error()), (0.0, timeout_error()), (0.0, "ok")])
    assert hedged(fn, timeout_s=1.0, budget_s=3.0, hedge_after_s=0.02) == ("ok", 3)


def test_non_retryable_error_wins_over_transient_one():
    fn = Script([(0.06, status_error(400)), (0.0, status_error(503)), (0.0, "khong duoc goi")])
    with pytest.raises(Exception) as err:
        hedged(fn, timeout_s=1.0, budget_s=3.0, hedge_after_s=0.02)
    assert getattr(err.value, "status_code", None) == 400 and fn.calls == 2


def test_no_hedge_when_no_budget_is_left_for_it():
    fn = Script([(0.1, "dau")])
    assert hedged(fn, timeout_s=1.0, budget_s=0.05, hedge_after_s=0.05) == ("dau", 1) and fn.calls == 1


def test_outer_cancel_cancels_both_requests():
    fn = Script([(1.0, "x"), (1.0, "y")])

    async def main():
        task = asyncio.ensure_future(call_with_retry(fn, timeout_s=2.0, hedge_after_s=0.02))
        await asyncio.sleep(0.08)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    run(main())
    assert fn.calls == 2 and fn.cancelled == 2


def test_no_hedge_when_it_would_start_after_the_timeout():
    fn = Script([(1.0, "x")])
    with pytest.raises(LlmTimeoutError):
        hedged(fn, timeout_s=0.03, max_retries=0, hedge_after_s=0.05)
    assert fn.calls == 1


def test_hedge_is_off_by_default_and_env_turns_it_on():
    llm = load_llm_settings(ENV)
    assert agent_settings("evaluator", llm, {}).hedge_after_s is None
    assert agent_settings("evaluator", llm, {"LLM_HEDGE_EVALUATOR": "5"}).hedge_after_s == 5.0
    assert agent_settings("evaluator", llm, {"LLM_HEDGE_EVALUATOR": "3.5"}).hedge_after_s == 3.5
    assert agent_settings("planner", llm, {"LLM_HEDGE_PLANNER": "10"}).hedge_after_s == 10.0
    for off in ("0", "off", "OFF"):
        assert agent_settings("evaluator", llm, {"LLM_HEDGE_EVALUATOR": off}).hedge_after_s is None
    for bad in ("-1", "nhanh", "nan", "inf"):
        with pytest.raises(ConfigError):
            agent_settings("evaluator", llm, {"LLM_HEDGE_EVALUATOR": bad})


def test_gateway_hedges_only_the_first_call_not_the_repair():
    llm = load_llm_settings(ENV)
    # lan dau tra JSON hong ngay (khong hedge), repair cham 0.15 s nhung khong duoc hedge
    client = FakeOpenAI([reply("khong phai json"), Slow(0.15, reply('{"answer": "ok"}'))])
    gw = LlmGateway(llm, client, env={"LLM_HEDGE_EVALUATOR": "0.05"}, sleep=_no_sleep, rng=lambda: 0.0)
    res = run(gw.complete("evaluator", MSGS, Out))
    assert res.data.answer == "ok" and len(client.calls) == 2 and res.record.attempts == 2

    client = FakeOpenAI([Slow(1.0, reply('{"answer": "cham"}')), reply('{"answer": "hedge"}')])
    gw = LlmGateway(llm, client, env={"LLM_HEDGE_EVALUATOR": "0.05"}, sleep=_no_sleep, rng=lambda: 0.0)
    res = run(gw.complete("evaluator", MSGS, Out))
    assert res.data.answer == "hedge" and res.record.attempts == 2


def test_evaluator_fallback_records_the_time_it_waited(monkeypatch):
    from test_llm_evaluator import inp, llm_json

    limit_agent(monkeypatch, "evaluator", 0.03)
    gw = LlmGateway(load_llm_settings(ENV), FakeOpenAI([Slow(1.0, llm_json())] * 3), env={},
                    sleep=_no_sleep, rng=lambda: 0.0)
    col = UsageCollector()
    ev = run(LlmEvaluator(gw).evaluate(inp(), col))
    assert ev.degraded
    meta = col.to_metadata()
    assert meta["fallbacks"] == ["evaluator_mock_heuristic"] and meta["latency_ms"]["evaluator"] >= 30
