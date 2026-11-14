"""LlmGateway: diem goi LLM duy nhat cho cac agent (retry, structured output, repair, do usage).

Quy tac (docs/ai-service/03 muc 4.6): retry loi tam thoi toi da 2 lan; sai schema thi repair 1 lan;
finish_reason=length thi thu lai 1 lan voi max_tokens x1.5. Khong log noi dung tru khi LOG_LLM_IO=true.
Moi lan goi bi cat o timeout_s (LlmTimeoutError); param `timeout` gui cho httpx chi la han tung lan doc.
"""
import asyncio
import logging
import random
import time
from dataclasses import dataclass
from typing import AsyncIterator, List, Mapping, Optional, Type, Union

from openai import AsyncOpenAI
from pydantic import BaseModel

from ..tracing import observation
from .chat_call import ChatCall, cached_tokens, parse_or_repair, request_base, trace_fields, trace_usage
from .errors import LlmOutputError
from .retry import call_with_retry
from .settings import LlmSettings, agent_settings, load_llm_settings, reasoning_body
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

    async def _retry(self, fn, timeout_s: Optional[float] = None, budget_s: Optional[float] = None,
                     hedge_after_s: Optional[float] = None):
        return await call_with_retry(fn, timeout_s=timeout_s, budget_s=budget_s, sleep=self._sleep, rng=self._rng,
                                     hedge_after_s=hedge_after_s)

    async def complete(self, agent: str, messages: List[dict], schema: Optional[Type[BaseModel]] = None,
                       *, prompt_version: str = "", collector: Optional[UsageCollector] = None,
                       budget_started: Optional[float] = None, budget_s: Optional[float] = None) -> LlmResult:
        """`budget_started` (perf_counter) + `budget_s`: ngan sach dong ho chung voi buoc truoc cua cung luot; moi lan
        goi, ke ca lan dau, bi cat theo phan du (het thi LlmTimeoutError). Khong truyen thi hanh vi cu."""
        if (budget_started is None) != (budget_s is None):
            raise ValueError("budget_started va budget_s phai di cung nhau")
        cfg = agent_settings(agent, self.llm, self._env)
        with observation(agent, "generation", input=messages, **trace_fields(cfg, prompt_version)) as gen:
            result = await self._complete(agent, cfg, messages, schema, prompt_version, collector,
                                          budget_started, budget_s)
            data = result.data
            gen.update(output=data.model_dump() if isinstance(data, BaseModel) else data, **trace_usage(result.record))
        return result

    async def _complete(self, agent: str, cfg, messages: List[dict], schema: Optional[Type[BaseModel]],
                        prompt_version: str, collector: Optional[UsageCollector],
                        budget_started: Optional[float] = None, budget_s: Optional[float] = None) -> LlmResult:
        rec, started = CallRecord(agent, cfg.model, prompt_version=prompt_version), time.perf_counter()
        capped = budget_started is not None
        chat = ChatCall(self, cfg, request_base(cfg, schema, self.llm), rec,
                        budget_started if capped else started, budget_s=budget_s, cap_first=capped)
        content = await chat.text(messages)
        data = await parse_or_repair(chat, schema, messages, content, rec)
        rec.attempts, rec.latency_ms = chat.calls, int((time.perf_counter() - started) * 1000)
        log.info("llm_call agent=%s model=%s in=%d cached=%d out=%d ms=%d attempts=%d repaired=%s", agent, cfg.model,
                 rec.input_tokens, rec.cached_tokens, rec.output_tokens, rec.latency_ms, rec.attempts, rec.repaired)
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
                  "stream_options": {"include_usage": True}, **reasoning_body(cfg.reasoning)}
        rec, started = CallRecord(agent, cfg.model, prompt_version=prompt_version), time.perf_counter()
        parts: List[str] = []
        with observation(agent, "generation", input=messages, **trace_fields(cfg, prompt_version)) as gen:
            try:
                resp, rec.attempts = await self._retry(lambda: self.client.chat.completions.create(**params),
                                                       cfg.timeout_s, cfg.retry_budget_s)
                async for chunk in resp:
                    usage = getattr(chunk, "usage", None)
                    if usage:
                        rec.input_tokens = getattr(usage, "prompt_tokens", 0) or 0
                        rec.output_tokens = getattr(usage, "completion_tokens", 0) or 0
                        rec.cached_tokens = cached_tokens(usage)
                    choices = getattr(chunk, "choices", None) or []
                    text = choices[0].delta.content if choices and getattr(choices[0], "delta", None) else None
                    if text:
                        if not parts:
                            gen.first_token()
                        parts.append(text)
                        yield text
            finally:
                rec.latency_ms = int((time.perf_counter() - started) * 1000)
                log.info("llm_stream agent=%s model=%s in=%d cached=%d out=%d ms=%d", agent, cfg.model,
                         rec.input_tokens, rec.cached_tokens, rec.output_tokens, rec.latency_ms)
                gen.update(output="".join(parts), **trace_usage(rec))  # ca khi stream dut: phan da nhan
                if collector is not None:
                    collector.add(rec)

    async def embed(self, texts: List[str], *, collector: Optional[UsageCollector] = None) -> List[List[float]]:
        started = time.perf_counter()
        with observation("embedding", "embedding", input=texts, model=self.llm.embedding_model) as obs:
            resp, attempts = await self._retry(
                lambda: self.client.embeddings.create(model=self.llm.embedding_model, input=texts))
            vectors = [d.embedding for d in resp.data]
            if any(len(v) != self.llm.embedding_dimensions for v in vectors):
                raise LlmOutputError(f"So chieu embedding khong khop {self.llm.embedding_dimensions}")
            usage = getattr(resp, "usage", None)
            tokens = getattr(usage, "prompt_tokens", 0) or 0
            obs.update(output={"vectors": len(vectors)}, usage_details={"input": tokens})
        if collector is not None:
            collector.add(CallRecord("embedding", self.llm.embedding_model, input_tokens=tokens,
                                     latency_ms=int((time.perf_counter() - started) * 1000), attempts=attempts))
        return vectors


_gateway: Optional[LlmGateway] = None


def get_gateway() -> LlmGateway:
    """Gateway dung chung (tao lan dau theo bien moi truong)."""
    global _gateway
    if _gateway is None:
        _gateway = LlmGateway(load_llm_settings())
    return _gateway
