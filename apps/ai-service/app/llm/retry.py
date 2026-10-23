"""Retry loi tam thoi khi goi LLM (docs/ai-service/03 muc 4.6): toi da 2 lan, backoff 0.5 s roi 1.5 s + jitter."""
import asyncio
import random
import time
from typing import Awaitable, Callable, Optional, Sequence, Tuple, TypeVar

from openai import APIConnectionError, APIStatusError

T = TypeVar("T")
DELAYS = (0.5, 1.5)


def is_retryable(exc: BaseException) -> bool:
    """Timeout, loi mang, 429, 5xx thi retry; 400/401/403 va loi khac thi khong (retry vo ich)."""
    if isinstance(exc, APIConnectionError):  # gom ca APITimeoutError
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


async def call_with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    max_retries: int = 2,
    delays: Sequence[float] = DELAYS,
    jitter: float = 0.2,
    budget_s: Optional[float] = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    clock: Callable[[], float] = time.monotonic,
    rng: Callable[[], float] = random.random,
) -> Tuple[T, int]:
    """Tra ve (ket qua, so lan goi). `budget_s`: tong thoi gian toi da cho retry (het ngan sach thi nem loi ngay)."""
    start, attempt = clock(), 0
    while True:
        try:
            return await fn(), attempt + 1
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
