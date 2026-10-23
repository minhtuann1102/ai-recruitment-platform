"""LlmGateway: diem goi LLM duy nhat cho cac agent (retry, structured output, repair, do usage).

Quy tac (docs/ai-service/03 muc 4.6): retry loi tam thoi toi da 2 lan; sai schema thi repair 1 lan;
finish_reason=length thi thu lai 1 lan voi max_tokens x1.5. Khong log noi dung tru khi LOG_LLM_IO=true.
"""
import asyncio
import logging
import random
import time
from dataclasses import dataclass
from typing import AsyncIterator, List, Mapping, Optional, Type, Union

from openai import AsyncOpenAI
from pydantic import BaseModel

from .errors import LlmOutputError
from .retry import call_with_retry
from .settings import LlmSettings, agent_settings, load_llm_settings
from .structured_output import parse_output, repair_messages, response_format
from .usage import CallRecord, UsageCollector

log = logging.getLogger("ai_service.llm")


@dataclass
class LlmResult:
    data: Union[BaseModel, str]
    record: CallRecord


def build_client(llm: LlmSettings) -> AsyncOpenAI:
    # max_retries=0: retry do LlmGateway lam, tranh retry hai lop
    return AsyncOpenAI(api_key=llm.api_key, base_url=llm.base_url, timeout=30.0, max_retries=0)


class LlmGateway:
    def __init__(self, llm: LlmSettings, client=None, *, env: Optional[Mapping[str, str]] = None,
                 sleep=asyncio.sleep, rng=random.random):
        self.llm, self.client, self._env = llm, client or build_client(llm), env
        self._sleep, self._rng = sleep, rng

    async def _retry(self, fn, budget_s: Optional[float] = None):
        return await call_with_retry(fn, budget_s=budget_s, sleep=self._sleep, rng=self._rng)

    async def complete(self, agent: str, messages: List[dict], schema: Optional[Type[BaseModel]] = None,
                       *, prompt_version: str = "", collector: Optional[UsageCollector] = None) -> LlmResult:
        cfg = agent_settings(agent, self.llm, self._env)
        base = {"model": cfg.model, "temperature": cfg.temperature, "max_tokens": cfg.max_tokens,
                "timeout": cfg.timeout_s}
        if cfg.seed is not None:
            base["seed"] = cfg.seed
        if schema is not None:
            base["response_format"] = response_format(schema, self.llm.structured_outputs)
        rec, calls, started = CallRecord(agent, cfg.model, prompt_version=prompt_version), 0, time.perf_counter()

        async def chat(msgs: List[dict], **override):
            nonlocal calls
            params = {**base, **override, "messages": msgs}
            resp, attempts = await self._retry(lambda: self.client.chat.completions.create(**params),
                                               cfg.retry_budget_s)
            calls += attempts
            usage = getattr(resp, "usage", None)
            rec.input_tokens += getattr(usage, "prompt_tokens", 0) or 0
            rec.output_tokens += getattr(usage, "completion_tokens", 0) or 0
            choice = resp.choices[0]
            if choice.finish_reason == "length" and "max_tokens" not in override:
                return await chat(msgs, **{**override, "max_tokens": int(cfg.max_tokens * 1.5)})
            if choice.finish_reason == "length":
                raise LlmOutputError("Output bi cat do gioi han max_tokens")
            return choice.message.content or ""

        content = await chat(messages)
        data: Union[BaseModel, str] = content
        if schema is not None:
            try:
                data = parse_output(schema, content)
            except ValueError as err:  # gom ca pydantic.ValidationError
                rec.repaired = True
                fixed = await chat(repair_messages(messages, content, str(err)), temperature=0)
                try:
                    data = parse_output(schema, fixed)
                except ValueError as err2:
                    raise LlmOutputError(f"Dau ra khong hop le sau repair ({type(err2).__name__})") from err2
        rec.attempts, rec.latency_ms = calls, int((time.perf_counter() - started) * 1000)
        log.info("llm_call agent=%s model=%s in=%d out=%d ms=%d attempts=%d repaired=%s", agent, cfg.model,
                 rec.input_tokens, rec.output_tokens, rec.latency_ms, rec.attempts, rec.repaired)
        if self.llm.log_io:
            log.debug("llm_io agent=%s messages=%s output=%s", agent, messages, content)
        if collector is not None:
            collector.add(rec)
        return LlmResult(data, rec)

    async def stream(self, agent: str, messages: List[dict], *, prompt_version: str = "",
                     collector: Optional[UsageCollector] = None) -> AsyncIterator[str]:
        """Stream text (Interviewer). Chi retry luc mo stream; loi giua stream nem ra de orchestrator gui `replace`.
        Usage lay tu chunk cuoi (stream_options.include_usage), ghi vao collector ca khi stream dut giua chung."""
        cfg = agent_settings(agent, self.llm, self._env)
        params = {"model": cfg.model, "temperature": cfg.temperature, "max_tokens": cfg.max_tokens,
                  "timeout": cfg.timeout_s, "messages": messages, "stream": True,
                  "stream_options": {"include_usage": True}}
        rec, started = CallRecord(agent, cfg.model, prompt_version=prompt_version), time.perf_counter()
        try:
            resp, rec.attempts = await self._retry(lambda: self.client.chat.completions.create(**params),
                                                   cfg.retry_budget_s)
            async for chunk in resp:
                usage = getattr(chunk, "usage", None)
                if usage:
                    rec.input_tokens = getattr(usage, "prompt_tokens", 0) or 0
                    rec.output_tokens = getattr(usage, "completion_tokens", 0) or 0
                choices = getattr(chunk, "choices", None) or []
                text = choices[0].delta.content if choices and getattr(choices[0], "delta", None) else None
                if text:
                    yield text
        finally:
            rec.latency_ms = int((time.perf_counter() - started) * 1000)
            log.info("llm_stream agent=%s model=%s in=%d out=%d ms=%d", agent, cfg.model, rec.input_tokens,
                     rec.output_tokens, rec.latency_ms)
            if collector is not None:
                collector.add(rec)

    async def embed(self, texts: List[str], *, collector: Optional[UsageCollector] = None) -> List[List[float]]:
        started = time.perf_counter()
        resp, attempts = await self._retry(
            lambda: self.client.embeddings.create(model=self.llm.embedding_model, input=texts))
        vectors = [d.embedding for d in resp.data]
        if any(len(v) != self.llm.embedding_dimensions for v in vectors):
            raise LlmOutputError(f"So chieu embedding khong khop {self.llm.embedding_dimensions}")
        usage = getattr(resp, "usage", None)
        if collector is not None:
            collector.add(CallRecord("embedding", self.llm.embedding_model,
                                     input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                                     latency_ms=int((time.perf_counter() - started) * 1000), attempts=attempts))
        return vectors


_gateway: Optional[LlmGateway] = None


def get_gateway() -> LlmGateway:
    """Gateway dung chung (tao lan dau theo bien moi truong)."""
    global _gateway
    if _gateway is None:
        _gateway = LlmGateway(load_llm_settings())
    return _gateway
