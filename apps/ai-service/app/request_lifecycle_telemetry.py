"""Tong ket moi request AI (log request_done, metric, trace) va khung stream SSE cua next-turn / start.

Tach khoi main.py (phase 04): usage_meta / finish_request / logged_failure dung cho moi endpoint, TurnStream /
_stream cho endpoint SSE. Hanh vi giu nguyen, chi doi cho dat.
"""
import asyncio
import logging
import time
from contextlib import aclosing, contextmanager
from typing import AsyncIterator, Awaitable, Callable, Optional, Tuple

import anyio
from fastapi.responses import StreamingResponse

from . import metrics, tracing
from .api_error import ApiError
from .llm.usage import UsageCollector
from .plan_snippets import note_rag_errors, rag_status
from .sse import SSE_HEADERS, event
from .turn_result import TurnResult

MODEL = "mock-v2"
log = logging.getLogger("ai_service")


def usage_meta(started: float, collector: Optional[UsageCollector] = None) -> dict:
    total = int((time.perf_counter() - started) * 1000)
    if collector is None or not collector.records:
        meta = {"usage": {}, "latency_ms": {"total": total}, "prompt_versions": {"mock": MODEL}, "fallbacks": []}
    else:
        meta = collector.to_metadata()
        meta["latency_ms"]["total"] = total  # tong thoi gian request, khong chi thoi gian goi LLM
    # RAG bat mac dinh: loi thi phien chay khong co RAG, bao o day (status error + fallback rag_unavailable)
    meta["rag"] = rag_status(collector)
    note_rag_errors(collector)  # sau khi bao: ngat RAG tam thoi cho cac request sau
    if meta["rag"]["status"] == "error":
        meta["fallbacks"].append("rag_unavailable")
    return meta


def finish_request(endpoint: str, started: float, collector: UsageCollector, status: str, error: str = "-",
                    rag: Optional[str] = None, error_code: Optional[str] = None) -> None:
    """Dong tong ket moi request, ca khi loi (lam so lieu TTFT / fallback / RAG tu log; chi so do va ma) + dong trace
    + so lieu Prometheus. `rag`: trang thai da bao trong metadata (giu dung gia tri do); None thi tinh lai tu
    collector. `error_code`: ma loi API (voice_no_speech...) cho nhan so lieu, log van ghi ten loi."""
    fallbacks = ",".join(r.fallback for r in collector.records if r.fallback) or "-"
    rag = rag or rag_status(collector)["status"]
    seconds = time.perf_counter() - started
    log.info("request_done status=%s error=%s ms=%d tokens=%d fallbacks=%s rag=%s trace=%s", status, error,
             seconds * 1000, collector.total_tokens(), fallbacks, rag, tracing.trace_id() or "-")
    tracing.finish_request(status, error, fallbacks=fallbacks, rag=rag)
    metrics.record_request(endpoint, status, error_code or error, seconds, collector, rag)


@contextmanager
def logged_failure(endpoint: str, started: float, collector: UsageCollector, rag: Optional[str] = None):
    """Loi truoc khi stream (ApiError 409/422, loi ngoai du kien): van ghi request_done roi nem tiep."""
    try:
        yield
    except BaseException as err:
        status = "cancelled" if isinstance(err, asyncio.CancelledError) else "error"
        code = err.error if isinstance(err, ApiError) else None
        finish_request(endpoint, started, collector, status, type(err).__name__, rag, error_code=code)
        raise


class TurnStream(StreamingResponse):
    """Client ngat: Starlette huy task stream ma khong dong generator (chi GC dong, trong context bat ky, co khi cua
    request khac). Dong generator va tong ket request ngay tai day, trong context cua chinh request nay; generator
    chua kip chay cung qua day."""

    def __init__(self, content, on_close: Callable[[], None], cleanup: Optional[Callable[[], Awaitable]] = None):
        super().__init__(content, media_type="text/event-stream", headers=SSE_HEADERS)
        self._on_close, self._cleanup = on_close, cleanup

    async def __call__(self, scope, receive, send) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            try:
                with anyio.CancelScope(shield=True):
                    await self.body_iterator.aclose()
                    if self._cleanup is not None:  # graph da chay truoc response (prime): huy ca khi generator chua chay
                        await self._cleanup()
            finally:
                self._on_close()


def stream_response(endpoint: str, turn_events: AsyncIterator[Tuple[str, dict]], result_of: Callable[[], TurnResult],
            build_done: Callable[[TurnResult], dict], collector: UsageCollector, started: float,
            cleanup: Optional[Callable[[], Awaitable]] = None):
    """meta -> token... (Interviewer stream, co the replace) -> done. `turn_events` goi finish_turn khi het (cau hoi
    that da ghi vao state); `done` dung SAU do tu `result_of()`."""
    outcome = {"status": "cancelled", "error": "-", "rag": None}  # client ngat: khong qua hai nhanh gan ben duoi

    async def gen():
        try:
            ttft = None  # chu dau tien cua cau hoi toi client; ghi sau stream khi da biet nguon cau hoi
            async with aclosing(turn_events) as events:
                async for name, data in events:
                    if ttft is None and name in ("token", "replace"):
                        ttft = time.perf_counter() - started
                    yield event(name, data)
            result = result_of()
            if ttft is not None and result is not None:  # replay (result None): khong do TTFT, khong goi LLM
                metrics.observe_ttft(endpoint, result.source, ttft)
            done = build_done(result)
            outcome.update(status="ok", rag=done["metadata"]["rag"]["status"])
            tracing.set_output(done.get("question"))
            yield event("done", done)
        except Exception as err:  # loi ngoai du kien: bao error de interview-service cho gui lai (FR-AI-039)
            outcome.update(status="error", error=type(err).__name__)
            log.exception("stream_failed")
            yield event("error", {"errorCode": "AI_SERVICE_ERROR", "message": "AI tạm thời không phản hồi",
                                  "retryable": True})
    return TurnStream(gen(), lambda: finish_request(endpoint, started, collector, **outcome), cleanup)
