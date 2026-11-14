"""Vong lap tool calling trong gateway (docs/ai-service/02): model co the goi cong cu (vd tra cuu) vai lan roi tra JSON.

Thu vien noi bo, agent goi qua `complete_with_tools`. Rang buoc: moi loi quy ve LlmError (agent tu lui ve duong goi
mot lan khong tools); ngan sach dong ho chung voi buoc truoc cua luot (moi lan goi, ke ca lan dau, bi cat); buoc cuoi
luon tool_choice="none"; combo model + tools + JSON strict bi tu choi thi latch theo tien trinh (khong thu lai).
"""
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional, Type

import openai
from pydantic import BaseModel

from .. import metrics
from ..tracing import observation
from .chat_call import ChatCall, parse_or_repair, request_base, trace_fields, trace_usage
from .errors import LlmError, LlmOutputError
from .settings import agent_settings, is_openrouter, merge_extra_body
from .usage import CallRecord, UsageCollector

log = logging.getLogger("ai_service.llm")

TOOLS_UNSUPPORTED = "tools_unsupported"
FINAL_RESERVE_S = 1.5  # chua cho buoc `none` khi buoc tools dung het han cua no
MAX_QUERY_CHARS = 200  # strict schema khong bao dam maxLength: code cat
MAX_ARGS_CHARS = 1000  # chuoi JSON doi so qua dai la sai
_tools_supported = True  # latch theo tien trinh, dat lai khi restart


def tools_supported() -> bool:
    return _tools_supported


def reset_tools_latch() -> None:
    global _tools_supported
    _tools_supported = True


@dataclass
class ToolLoopResult:
    data: BaseModel
    record: CallRecord
    tool_calls: int


def _is_unsupported(err: Exception) -> bool:
    """OpenRouter: 404 (hoac 400 "No endpoints found ... support ...") khi require_parameters khong co provider hop."""
    if isinstance(err, openai.NotFoundError):
        return True
    text = str(err).lower()
    return isinstance(err, openai.BadRequestError) and "no endpoints" in text and "support" in text


def _map_error(err: Exception) -> LlmError:
    global _tools_supported
    if isinstance(err, LlmError):
        return err
    if _is_unsupported(err):
        _tools_supported = False
        metrics.record_tools_unsupported()
        return LlmError(TOOLS_UNSUPPORTED)
    return LlmError(f"tool_loop_failed ({type(err).__name__})")


def _assistant_tool_message(calls) -> dict:
    """SimpleNamespace / doi tuong SDK khong co model_dump dong nhat: tu dung message assistant."""
    return {"role": "assistant", "content": None, "tool_calls": [
        {"id": c.id, "type": "function", "function": {"name": c.function.name, "arguments": c.function.arguments}}
        for c in calls]}


async def _safe_run(run_tool: Callable[[str, Dict[str, Any]], Awaitable[str]], names: set, call, agent: str) -> str:
    """Loi cong cu thanh chuoi loi cho model, khong nem. Doi so: JSON object, `query` chuoi khong rong, cat 200 ky tu."""
    name, raw = call.function.name, call.function.arguments or ""
    if name not in names:
        return "error: unknown_tool"
    try:
        args = json.loads(raw) if len(raw) <= MAX_ARGS_CHARS else None
    except ValueError:
        args = None
    if not isinstance(args, dict):
        return "error: invalid_arguments"
    query = args.get("query")
    query = query.strip()[:MAX_QUERY_CHARS] if isinstance(query, str) else ""
    if not query:
        return "error: empty_query"
    try:
        return str(await run_tool(name, {**args, "query": query}))
    except Exception as err:  # cong cu hong khong duoc lam hong luot cham
        log.warning("tool_failed agent=%s tool=%s err=%s", agent, name, type(err).__name__)
        return "error: tool_failed"


async def complete_with_tools(gw, agent: str, messages: List[dict], schema: Type[BaseModel], tools: List[dict],
                              run_tool: Callable[[str, Dict[str, Any]], Awaitable[str]], *, max_calls: int,
                              step_deadline_s: float, budget_started: float, budget_s: float,
                              prompt_version: str = "", collector: Optional[UsageCollector] = None,
                              failure_fallback: str = "tool_loop_failed") -> ToolLoopResult:
    """`run_tool(ten, doi_so)` tra chuoi ket qua (caller tu boc `wrap_untrusted`). `tools` la hang so, gui nguyen
    moi buoc de prefix cache on dinh. `budget_started` (perf_counter) + `budget_s`: ngan sach chung ca luot.
    Loi: LlmError / LlmOutputError / LlmTimeoutError; da them CallRecord (fallback=failure_fallback, kem do tre)."""
    if not _tools_supported:
        raise LlmError(TOOLS_UNSUPPORTED)
    cfg = agent_settings(agent, gw.llm, gw._env)
    base = request_base(cfg, schema, gw.llm)
    base.update(tools=tools, tool_choice="auto", parallel_tool_calls=False)
    if is_openrouter(gw.llm.base_url):  # moi tham so (ca seed, reasoning) bat buoc duoc provider ho tro, khong thi 404
        merge_extra_body(base, {"provider": {"require_parameters": True}})
    names = {t["function"]["name"] for t in tools}
    rec, t0 = CallRecord(agent, cfg.model, prompt_version=prompt_version), time.perf_counter()
    chat = ChatCall(gw, cfg, base, rec, budget_started, budget_s=budget_s, cap_first=True)
    msgs, used = list(messages), 0
    try:
        with observation(agent, "generation", input=messages, **trace_fields(cfg, prompt_version)) as gen:
            while True:
                step_left = step_deadline_s - (time.perf_counter() - t0)
                last = used >= max_calls or step_left <= 0
                choice = await (chat(msgs, tool_choice="none") if last
                                else chat(msgs, timeout_cap=step_left + FINAL_RESERVE_S))
                calls = getattr(choice.message, "tool_calls", None) or []
                if not calls:
                    break
                if last:
                    raise LlmOutputError("Model van goi cong cu sau tool_choice=none")
                msgs.append(_assistant_tool_message(calls))
                for c in calls:  # parallel tat, nhung moi tool_call_id thua van phai duoc tra loi
                    with observation("tool:" + str(c.function.name)[:40], "span", nest=True):
                        msgs.append({"role": "tool", "tool_call_id": c.id,
                                     "content": await _safe_run(run_tool, names, c, agent)})
                used += len(calls)
                rec.tool_calls += len(calls)
            content = choice.message.content or ""
            data = await parse_or_repair(chat, schema, msgs, content, rec, tool_choice="none")  # M3: repair khong goi tool
            rec.attempts = chat.calls
            gen.update(output=data.model_dump(), **trace_usage(rec))
    except Exception as err:
        rec.attempts, rec.fallback = chat.calls, failure_fallback
        rec.latency_ms = int((time.perf_counter() - t0) * 1000)
        if collector is not None:
            collector.add(rec)  # giu do tre / token cua vong lap hong de bao cao khong thieu
        raise _map_error(err) from err
    rec.latency_ms = int((time.perf_counter() - t0) * 1000)
    log.info("llm_tool_loop agent=%s model=%s in=%d cached=%d out=%d ms=%d attempts=%d tool_calls=%d repaired=%s",
             agent, cfg.model, rec.input_tokens, rec.cached_tokens, rec.output_tokens, rec.latency_ms, rec.attempts,
             rec.tool_calls, rec.repaired)
    if gw.llm.log_io:
        log.debug("llm_io agent=%s messages=%s output=%s", agent, msgs, content)
    if collector is not None:
        collector.add(rec)
    return ToolLoopResult(data, rec, rec.tool_calls)
