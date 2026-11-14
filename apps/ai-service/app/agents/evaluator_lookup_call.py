"""Duong goi Evaluator co tra cuu (phase 03): vong lap tool + fallback mot lan goi, chung MOT ngan sach dong ho.

Ngan sach B = retry_budget_s cua Evaluator (10 s), tinh tu t0 dau `evaluate_with_raw`: vong lap bi `wait_for` cat o
B - da troi qua; loi thi chi cham lai khong tools khi con >= MIN_FALLBACK_S, khong thi nem LlmTimeoutError de
LlmEvaluator dung mock + degraded. Han buoc tool ngan hon B de chua cho cho lan goi cuoi (`FINAL_RESERVE_S`).
"""
import asyncio
import logging
import time
from typing import List, Tuple

from .. import metrics
from ..evaluator_lookup import SEARCH_TOOL, fragment_text
from ..llm.errors import LlmError, LlmTimeoutError
from ..llm.settings import agent_settings
from ..llm.tool_loop import FINAL_RESERVE_S, TOOLS_UNSUPPORTED, complete_with_tools
from ..llm.usage import CallRecord, UsageCollector
from .evaluator_input import EvaluationInput

log = logging.getLogger("ai_service.evaluator")
MIN_FALLBACK_S = 2.5  # it hon the thi mot lan goi khong tools khong ve kip: chuyen thang sang mock + degraded
LOOKUP_FALLBACK = "evaluator_lookup_fallback"
DEFAULT_BUDGET_S = 10.0


async def call_with_lookup(gw, agent: str, system_prompt: str, build_messages, schema, prompt_version: str,
                           inp: EvaluationInput, collector, t0: float) -> Tuple[object, EvaluationInput]:
    """Tra (ket qua co `.data`, dau vao cho hau kiem). `build_messages(system_prompt, inp)` dung request.
    inp tra ve co chunk cong cu noi cuoi turn_snippets khi vong lap thanh cong va co chunk, con khong la `inp` goc."""
    lookup = inp.lookup
    cfg = agent_settings(agent, gw.llm, gw._env)
    budget = cfg.retry_budget_s or DEFAULT_BUDGET_S
    inner = UsageCollector()  # gateway tu them CallRecord(fallback=...) khi vong lap loi: gom lai, khong them lan hai
    left = budget - (time.perf_counter() - t0)
    try:
        if left < MIN_FALLBACK_S:
            raise LlmTimeoutError("Het ngan sach truoc khi tra cuu")
        step = max(min(lookup.settings.tool_deadline_s, left - FINAL_RESERVE_S), 0.05)
        messages = build_messages(f"{system_prompt}\n\n{fragment_text()}", inp)
        result = await asyncio.wait_for(
            complete_with_tools(gw, agent, messages, schema, [SEARCH_TOOL], lookup.run_tool,
                                max_calls=lookup.settings.max_calls, step_deadline_s=step, budget_started=t0,
                                budget_s=budget, prompt_version=prompt_version, collector=inner,
                                failure_fallback=LOOKUP_FALLBACK), left)
    except (LlmError, asyncio.TimeoutError) as err:
        _merge(collector, inner)
        if not inner.records and isinstance(err, (asyncio.TimeoutError, LlmTimeoutError)):
            # wait_for huy vong lap (BaseException, gateway khong kip ghi) hoac het ngan sach: ghi do tre o day
            _record_cut(collector, agent, cfg.model, prompt_version, t0)
        unsupported = str(err) == TOOLS_UNSUPPORTED
        metrics.record_evaluator_lookup("unsupported" if unsupported else "fallback")
        remaining = budget - (time.perf_counter() - t0)
        log.warning("evaluator_lookup_fallback turn=%d reason=%s remaining_s=%.1f", inp.turn_number,
                    type(err).__name__, remaining)
        if remaining < MIN_FALLBACK_S:
            raise LlmTimeoutError("no_budget_for_fallback") from err  # -> mock + degraded
        plain = await gw.complete(agent, build_messages(system_prompt, inp), schema, prompt_version=prompt_version,
                                  collector=collector, budget_started=t0, budget_s=budget)
        return plain, inp
    _merge(collector, inner)
    lookup.committed = True
    log.info("evaluator_lookup turn=%d fragment=%s calls=%d chunks=%d", inp.turn_number, "evaluator_tools.v1",
             result.tool_calls, len(lookup.texts))
    return result, lookup.extend(inp)


def _merge(collector, inner: UsageCollector) -> None:
    if collector is not None:
        for record in inner.records:
            collector.add(record)


def _record_cut(collector, agent: str, model: str, prompt_version: str, t0: float) -> None:
    if collector is not None:
        collector.add(CallRecord(agent, model, prompt_version=prompt_version, fallback=LOOKUP_FALLBACK,
                                 latency_ms=int((time.perf_counter() - t0) * 1000)))
