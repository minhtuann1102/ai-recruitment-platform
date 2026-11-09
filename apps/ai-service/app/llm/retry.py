"""Retry loi tam thoi khi goi LLM (docs/ai-service/03 muc 4.6): toi da 2 lan, backoff 0.5 s roi 1.5 s + jitter.

Hedge (docs 08 muc 9.2, tu 2026-11-09): lan goi dau qua `hedge_after_s` chua xong thi gui them mot request giong het,
lay ket qua ve truoc, huy request con lai. Log 03/11: 2.3% luot Evaluator het han 8 s mat ~11 s moi luot.
"""
import asyncio
import random
import time
from typing import Awaitable, Callable, List, Optional, Sequence, Tuple, TypeVar

from openai import APIConnectionError, APIStatusError

from .errors import LlmTimeoutError

T = TypeVar("T")
DELAYS = (0.5, 1.5)


def is_retryable(exc: BaseException) -> bool:
    """Timeout, loi mang, 429, 5xx thi retry; 400/401/403 va loi khac thi khong (retry vo ich)."""
    if isinstance(exc, (APIConnectionError, LlmTimeoutError)):  # gom ca APITimeoutError
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code == 429 or exc.status_code >= 500
    return False


def retry_after_seconds(exc: BaseException) -> Optional[float]:
    headers = getattr(getattr(exc, "response", None), "headers", None)
    if not headers:
        return None
    try:
        return float(headers.get("retry-after"))
    except (TypeError, ValueError):
        return None


async def _within(fn: Callable[[], Awaitable[T]], limit_s: Optional[float]) -> T:
    if limit_s is None:
        return await fn()
    try:
        return await asyncio.wait_for(fn(), limit_s)
    except asyncio.TimeoutError as err:
        raise LlmTimeoutError(f"Lan goi LLM qua {limit_s:.1f} s") from err


async def _hedged(fn: Callable[[], Awaitable[T]], limit_s: Optional[float], hedge_after_s: float,
                  hedge_limit_s: Optional[float], sent: List[asyncio.Future]) -> T:
    """Request ve truoc thang; mot request loi thi cho request kia, ca hai loi thi nem loi ve sau.
    `sent` ghi moi request da gui de dem so lan goi ca khi loi."""
    sent.append(asyncio.ensure_future(_within(fn, limit_s)))
    try:
        done, _ = await asyncio.wait(sent, timeout=hedge_after_s)
        if done:
            return sent[0].result()
        sent.append(asyncio.ensure_future(_within(fn, hedge_limit_s)))
        pending, error = set(sent), None
        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            finished = [(t, t.exception()) for t in done]  # doc moi loi: asyncio khong log "never retrieved"
            ok = next((t for t, exc in finished if exc is None), None)
            if ok is not None:
                return ok.result()
            for _, exc in finished:  # loi khong retry duoc (4xx) thang loi tam thoi: retry tiep vo ich
                if error is None or is_retryable(error):
                    error = exc
        raise error
    finally:
        for t in sent:
            if not t.done():
                t.cancel()


async def call_with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    max_retries: int = 2,
    delays: Sequence[float] = DELAYS,
    jitter: float = 0.2,
    timeout_s: Optional[float] = None,
    budget_s: Optional[float] = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    clock: Callable[[], float] = time.monotonic,
    rng: Callable[[], float] = random.random,
    hedge_after_s: Optional[float] = None,
) -> Tuple[T, int]:
    """Tra ve (ket qua, so lan goi, tinh ca request hedge). `budget_s`: tong thoi gian toi da cho retry (het ngan sach
    thi nem loi ngay). `timeout_s`: han tong cua moi lan goi. Lan dau luon du `timeout_s`, ke ca khi budget 0 (nghia la
    khong retry); lan retry chi con phan du cua ngan sach. `hedge_after_s`: chi hedge lan goi dau, request hedge chi con
    phan du cua ngan sach (khong co ngan sach thi phan du cua `timeout_s`); khong con thoi gian thi khong hedge."""
    start, attempt, sent = clock(), 0, []
    while True:
        limit_s = timeout_s
        if attempt and timeout_s is not None and budget_s is not None:
            limit_s = min(timeout_s, max(budget_s - (clock() - start), 0.0))
        try:
            # hedge dung chung ngan sach (khong co thi trong han cua lan goi): xong truoc han tong nhu retry
            deadline_s = budget_s if budget_s is not None else limit_s
            hedge_limit_s = None if deadline_s is None else deadline_s - (hedge_after_s or 0.0)
            if limit_s is not None and hedge_limit_s is not None:
                hedge_limit_s = min(limit_s, hedge_limit_s)
            if attempt == 0 and hedge_after_s and (hedge_limit_s is None or hedge_limit_s > 0):
                result = await _hedged(fn, limit_s, hedge_after_s, hedge_limit_s, sent)
            else:
                result = await _within(fn, limit_s)
            return result, attempt + max(len(sent), 1)
        except Exception as exc:
            if not is_retryable(exc) or attempt >= max_retries:
                raise
            delay = delays[min(attempt, len(delays) - 1)]
            delay = max(delay, retry_after_seconds(exc) or 0.0)
            delay += delay * jitter * rng()
            if budget_s is not None and (clock() - start) + delay > budget_s:
                raise
            await sleep(delay)
            attempt += 1
