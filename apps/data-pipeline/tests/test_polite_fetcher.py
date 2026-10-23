"""PoliteFetcher voi site fixture phuc vu qua httpx.MockTransport (khong ra mang) va dong ho gia."""
import httpx
import pytest

from crawlers.polite_fetcher import USER_AGENT, PoliteFetcher
from crawlers.react_docs_crawler import crawl_react_docs

PAGE = "<html><body><article><h1>{title}</h1><p>Noi dung {title}.</p>{links}</article></body></html>"


class FakeClock:
    """time.monotonic + time.sleep gia: sleep chi cong vao dong ho, ghi lai thoi diem moi request."""

    def __init__(self):
        self.now = 1000.0
        self.request_times = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        assert seconds > 0
        self.now += seconds


def make_site(robots_text, clock, status_for_robots=200):
    requested = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["user-agent"] == USER_AGENT
        path = request.url.path
        requested.append(path)
        if path == "/robots.txt":
            return httpx.Response(status_for_robots, text=robots_text)
        clock.request_times.append(clock.now)
        clock.now += 0.2  # tai trang mat 0.2s
        links = "".join(f'<a href="/learn/p{i}">p{i}</a>' for i in range(30))
        return httpx.Response(200, html=PAGE.format(title=path, links=links))

    return httpx.MockTransport(handler), requested


def make_fetcher(fixtures_dir, clock, delay=1.0, max_pages=60, status_for_robots=200, logs=None):
    robots = (fixtures_dir / "react_docs" / "robots.txt").read_text(encoding="utf-8")
    transport, requested = make_site(robots, clock, status_for_robots)
    fetcher = PoliteFetcher(
        "https://react.dev",
        delay=delay,
        max_pages=max_pages,
        transport=transport,
        clock=clock,
        sleep=clock.sleep,
        log=(logs.append if logs is not None else lambda _m: None),
    )
    return fetcher, requested


def test_robots_checked_once_and_disallowed_path_skipped(fixtures_dir):
    clock, logs = FakeClock(), []
    fetcher, requested = make_fetcher(fixtures_dir, clock, logs=logs)
    assert fetcher.fetch("https://react.dev/private/secret") is None
    assert fetcher.fetch("https://react.dev/learn") is not None
    assert fetcher.fetch("https://react.dev/private") is None
    assert requested == ["/robots.txt", "/learn"]  # robots doc 1 lan, /private khong bi goi
    assert fetcher.skipped_by_robots == 2 and fetcher.pages_requested == 1
    assert logs[0].startswith("robots checked: https://react.dev/robots.txt [200]")
    assert sum("robots disallow" in m for m in logs) == 2


@pytest.mark.parametrize("delay", [1.0, 2.5])
def test_gap_between_requests_at_least_delay(fixtures_dir, delay):
    clock = FakeClock()
    fetcher, _ = make_fetcher(fixtures_dir, clock, delay=delay, max_pages=5)
    for i in range(5):
        fetcher.fetch(f"https://react.dev/learn/p{i}")
    gaps = [b - a for a, b in zip(clock.request_times, clock.request_times[1:])]
    assert len(gaps) == 4 and all(gap >= delay for gap in gaps)


def test_crawl_never_exceeds_max_pages(fixtures_dir):
    clock = FakeClock()
    fetcher, requested = make_fetcher(fixtures_dir, clock, delay=0, max_pages=7)
    records = crawl_react_docs(fetcher)
    pages = [p for p in requested if p != "/robots.txt"]
    assert len(pages) == 7 == fetcher.pages_requested and fetcher.exhausted
    assert len(records) == 7 and len(set(pages)) == 7
    assert fetcher.fetch("https://react.dev/learn/p29") is None  # het luot -> khong gui them


def test_unreadable_robots_disallows_everything(fixtures_dir):
    clock = FakeClock()
    fetcher, requested = make_fetcher(fixtures_dir, clock, status_for_robots=503)
    assert fetcher.fetch("https://react.dev/learn") is None
    assert requested == ["/robots.txt"]
