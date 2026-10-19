import asyncio

import pytest

from app.llm.retry import call_with_retry, is_retryable, retry_after_seconds
from fakes.fake_llm import status_error, timeout_error


def run(coro):
    return asyncio.run(coro)


class Seq:
    """Ham async tra ve/nem lan luot theo kich ban."""

    def __init__(self, items):
        self.items, self.calls = list(items), 0

    async def __call__(self):
        self.calls += 1
        item = self.items.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


def retry(fn, **kw):
    delays = []

    async def fake_sleep(d):
        delays.append(d)

    result = run(call_with_retry(fn, sleep=fake_sleep, rng=lambda: 0.0, **kw))
    return result, delays


@pytest.mark.parametrize("err", [timeout_error(), status_error(429), status_error(500), status_error(503)])
def test_transient_errors_are_retryable(err):
    assert is_retryable(err)


@pytest.mark.parametrize("status", [400, 401, 403])
def test_client_errors_are_not_retried(status):
    fn = Seq([status_error(status)])
    with pytest.raises(Exception):
        retry(fn)
    assert fn.calls == 1


def test_two_retries_with_documented_backoff_then_success():
    fn = Seq([timeout_error(), status_error(429), "ok"])
    (result, attempts), delays = retry(fn)
    assert result == "ok" and attempts == 3 and fn.calls == 3
    assert delays == [0.5, 1.5]


def test_gives_up_after_two_retries():
    fn = Seq([status_error(500)] * 3)
    with pytest.raises(Exception):
        retry(fn)
    assert fn.calls == 3  # 1 lan dau + 2 retry


def test_retry_after_header_is_respected():
    err = status_error(429, {"retry-after": "3"})
    assert retry_after_seconds(err) == 3.0
    (_, _), delays = retry(Seq([err, "ok"]))
    assert delays == [3.0]


def test_jitter_is_added_within_20_percent():
    delays = []

    async def fake_sleep(d):
        delays.append(d)

    run(call_with_retry(Seq([timeout_error(), "ok"]), sleep=fake_sleep, rng=lambda: 1.0))
    assert delays == [pytest.approx(0.6)]


def test_budget_stops_retrying_early():
    clock = iter([0.0, 0.0, 0.9, 0.9])  # da dung 0.9 s, delay 1.5 s se vuot ngan sach 2 s

    fn = Seq([timeout_error(), timeout_error(), "ok"])
    with pytest.raises(Exception):
        run(call_with_retry(fn, sleep=lambda d: asyncio.sleep(0), rng=lambda: 0.0, budget_s=2.0,
                            clock=lambda: next(clock)))
    assert fn.calls == 2
