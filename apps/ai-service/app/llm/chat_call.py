"""Mot lan goi chat completion cua gateway: retry, hedge, cat ngan sach, xu ly finish_reason=length, do usage, repair.

Tach tu LlmGateway._complete de gateway thuong va vong lap tool (tool_loop.py) dung chung mot duong goi.
"""
import time
from typing import List, Optional, Type, Union

from pydantic import BaseModel

from .errors import LlmOutputError, LlmTimeoutError
from .settings import reasoning_body
from .structured_output import parse_output, repair_messages, response_format
from .usage import CallRecord


def trace_fields(cfg, prompt_version: str) -> dict:
    return {"model": cfg.model, "version": prompt_version or None,
            "model_parameters": {"temperature": cfg.temperature, "max_tokens": cfg.max_tokens}}


def trace_usage(rec: CallRecord) -> dict:
    meta = {"attempts": rec.attempts, "repaired": rec.repaired, "fallback": rec.fallback,
            "cached_tokens": rec.cached_tokens}
    if rec.tool_calls:
        meta["tool_calls"] = rec.tool_calls
    return {"usage_details": {"input": rec.input_tokens, "output": rec.output_tokens}, "metadata": meta}


def cached_tokens(usage) -> int:
    """Token input doc tu prompt cache; provider khong tra thi 0, nen 0 khong khang dinh la khong co cache."""
    return getattr(getattr(usage, "prompt_tokens_details", None), "cached_tokens", 0) or 0


def request_base(cfg, schema: Optional[Type[BaseModel]], llm) -> dict:
    """Tham so chung moi request chat cua mot agent (model, nhiet do, seed, reasoning, response_format)."""
    base = {"model": cfg.model, "temperature": cfg.temperature, "max_tokens": cfg.max_tokens,
            "timeout": cfg.timeout_s}
    if cfg.seed is not None:
        base["seed"] = cfg.seed
    base.update(reasoning_body(cfg.reasoning))
    if schema is not None:
        base["response_format"] = response_format(schema, llm.structured_outputs)
    return base


class ChatCall:
    """Goi chat nhieu lan trong mot luot (lan dau, repair, length, buoc tool) chung `rec` va ngan sach dong ho.

    Mac dinh (cap_first=False, hanh vi cu): chi cac lan sau lan goi dau bi cat theo phan du cua ngan sach retry; lan dau
    luon du timeout_s. cap_first=True: moi lan goi, ke ca lan dau, bi cat theo `budget_s - da troi qua` (con <= 0 thi
    LlmTimeoutError); hedge van chi o lan goi dau.
    """

    def __init__(self, gw, cfg, base: dict, rec: CallRecord, started: float, *, budget_s: Optional[float] = None,
                 cap_first: bool = False):
        self.gw, self.cfg, self.base, self.rec, self.started = gw, cfg, base, rec, started
        self.budget_s = cfg.retry_budget_s if budget_s is None else budget_s
        self.cap_first, self.calls = cap_first, 0

    async def __call__(self, msgs: List[dict], *, timeout_cap: Optional[float] = None, **override):
        """Tra ve choice dau tien. `timeout_cap`: tran thoi gian rieng cua lan goi nay (buoc tool)."""
        params = {**self.base, **override, "messages": msgs}
        timeout_s, budget_s = self.cfg.timeout_s, self.budget_s
        hedge_after_s = None if self.calls else self.cfg.hedge_after_s  # chi hedge lan goi dau, khong hedge repair / length
        if budget_s is not None and (self.calls or self.cap_first):  # repair / length dung chung ngan sach voi lan dau
            budget_s -= time.perf_counter() - self.started
            if self.cap_first and budget_s <= 0:
                raise LlmTimeoutError("Het ngan sach thoi gian truoc khi goi LLM")
            timeout_s = min(timeout_s, max(budget_s, 0.0))
        if timeout_cap is not None:
            timeout_s = min(timeout_s, max(timeout_cap, 0.0))
            budget_s = timeout_cap if budget_s is None else min(budget_s, timeout_cap)  # retry o lai trong buoc
        resp, attempts = await self.gw._retry(lambda: self.gw.client.chat.completions.create(**params),
                                              timeout_s, budget_s, hedge_after_s)
        self.calls += attempts
        usage = getattr(resp, "usage", None)
        self.rec.input_tokens += getattr(usage, "prompt_tokens", 0) or 0
        self.rec.output_tokens += getattr(usage, "completion_tokens", 0) or 0
        self.rec.cached_tokens += cached_tokens(usage)
        choice = resp.choices[0]
        if choice.finish_reason == "length" and "max_tokens" not in override:
            return await self(msgs, timeout_cap=timeout_cap,
                              **{**override, "max_tokens": int(self.cfg.max_tokens * 1.5)})
        if choice.finish_reason == "length":
            raise LlmOutputError("Output bi cat do gioi han max_tokens")
        return choice

    async def text(self, msgs: List[dict], **override) -> str:
        return (await self(msgs, **override)).message.content or ""


async def parse_or_repair(call: ChatCall, schema: Optional[Type[BaseModel]], messages: List[dict], content: str,
                          rec: CallRecord, **override) -> Union[BaseModel, str]:
    """Parse theo schema; sai thi repair 1 lan (temperature 0, `override` them vao request repair)."""
    if schema is None:
        return content
    try:
        return parse_output(schema, content)
    except ValueError as err:  # gom ca pydantic.ValidationError
        rec.repaired = True
        fixed = await call.text(repair_messages(messages, content, str(err)), temperature=0, **override)
        try:
            return parse_output(schema, fixed)
        except ValueError as err2:
            raise LlmOutputError(f"Dau ra khong hop le sau repair ({type(err2).__name__})") from err2
