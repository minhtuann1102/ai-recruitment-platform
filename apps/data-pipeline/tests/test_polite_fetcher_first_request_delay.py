"""Request trang dau tien cung cach request robots.txt it nhat `delay` giay (FR-004, SC-002: 100% request)."""
import httpx

from crawlers.polite_fetcher import PoliteFetcher

ORIGIN = "https://nguon-gia.example"


def test_first_page_request_waits_delay_after_robots_request():
    now, waits = [1000.0], []

    def sleep(seconds):
        waits.append(seconds)
        now[0] += seconds

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        return httpx.Response(200, html="<html><body>ok</body></html>")

    fetcher = PoliteFetcher(
        ORIGIN, delay=2.0, transport=httpx.MockTransport(handler), clock=lambda: now[0], sleep=sleep, log=lambda _m: None
    )
    assert fetcher.fetch(f"{ORIGIN}/it-jobs") is not None
    assert waits == [2.0]  # request trang dau khong duoc ban ngay sau robots.txt
    assert fetcher.fetch(f"{ORIGIN}/it-jobs?page=2") is not None
    assert waits == [2.0, 2.0]
