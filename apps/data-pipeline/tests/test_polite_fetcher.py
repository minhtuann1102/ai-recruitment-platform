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


# --- Dung nguon khi bi chan (FR-004, spec 009 T005): 3 phan hoi 403/429 / thu thach lien tiep ---

JD_ORIGIN = "https://nguon-gia.example"
OPEN_ROBOTS = "User-agent: *\nAllow: /\n"


def make_scripted_fetcher(fixtures_dir, script, robots_status=200, robots_text=OPEN_ROBOTS, logs=None):
    """Request trang thu n tra kich ban script[n]: so (HTTP status), 'ok', hoac 'challenge' (HTTP 200)."""
    clock, requested, responses = FakeClock(), [], iter(script)
    challenge = (fixtures_dir / "jd" / "challenge.html").read_text(encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(robots_status, text=robots_text)
        step = next(responses)
        if step == "ok":
            return httpx.Response(200, html="<html><body><p>Tin tuyen dung</p></body></html>")
        if step == "challenge":
            return httpx.Response(200, html=challenge)
        return httpx.Response(step, html="<html><body>blocked</body></html>")

    fetcher = PoliteFetcher(
        JD_ORIGIN,
        delay=0,
        transport=httpx.MockTransport(handler),
        clock=clock,
        sleep=clock.sleep,
        log=(logs.append if logs is not None else lambda _m: None),
    )
    return fetcher, requested


def fetch_all(fetcher, count):
    return [fetcher.fetch(f"{JD_ORIGIN}/it-jobs/job-{i}") for i in range(count)]


@pytest.mark.parametrize("status", [403, 429])
def test_three_consecutive_blocks_stop_source_and_send_no_more_requests(fixtures_dir, status):
    logs = []
    fetcher, requested = make_scripted_fetcher(fixtures_dir, [status, status, status, "ok"], logs=logs)
    results = fetch_all(fetcher, 3)
    assert results == [None, None, None] and fetcher.blocked
    assert f"source blocked: {JD_ORIGIN}" in logs
    pages_sent = fetcher.pages_requested
    assert fetcher.fetch(f"{JD_ORIGIN}/it-jobs/job-9") is None  # script con 'ok' nhung khong duoc gui
    assert requested == ["/robots.txt"] + [f"/it-jobs/job-{i}" for i in range(3)]
    assert fetcher.pages_requested == pages_sent and fetcher.skipped_by_robots == 0


def test_blocks_separated_by_a_normal_response_do_not_stop_source(fixtures_dir):
    fetcher, requested = make_scripted_fetcher(fixtures_dir, [403, "ok", 403, 403, "ok", 403])
    results = fetch_all(fetcher, 6)
    assert [r is None for r in results] == [True, False, True, True, False, True]
    assert not fetcher.blocked and len(requested) == 7  # robots + 6 trang


def test_other_http_error_between_blocks_breaks_the_streak(fixtures_dir):
    fetcher, _ = make_scripted_fetcher(fixtures_dir, [403, 404, 403, 403])
    fetch_all(fetcher, 4)
    assert not fetcher.blocked


def test_antibot_challenge_page_with_http_200_counts_as_blocked(fixtures_dir):
    logs = []
    fetcher, requested = make_scripted_fetcher(fixtures_dir, ["challenge", "challenge", "challenge", "ok"], logs=logs)
    assert fetch_all(fetcher, 3) == [None, None, None]  # trang thu thach khong bi tra nhu noi dung
    assert fetcher.blocked and f"source blocked: {JD_ORIGIN}" in logs
    assert fetcher.fetch(f"{JD_ORIGIN}/it-jobs/job-9") is None and len(requested) == 4


def test_mixed_status_and_challenge_in_a_row_stop_source(fixtures_dir):
    fetcher, _ = make_scripted_fetcher(fixtures_dir, [403, "challenge", 429])
    fetch_all(fetcher, 3)
    assert fetcher.blocked


@pytest.mark.parametrize("robots_status", [403, 429])
def test_robots_blocked_stops_source_before_any_page_request(fixtures_dir, robots_status):
    logs = []
    fetcher, requested = make_scripted_fetcher(fixtures_dir, ["ok"], robots_status=robots_status, logs=logs)
    assert fetcher.blocked and f"source blocked: {JD_ORIGIN}" in logs
    assert fetcher.fetch(f"{JD_ORIGIN}/it-jobs/job-1") is None
    assert requested == ["/robots.txt"] and fetcher.pages_requested == 0


@pytest.mark.parametrize("robots_status", [404, 503])
def test_robots_missing_or_server_error_is_not_a_block(fixtures_dir, robots_status):
    fetcher, _ = make_scripted_fetcher(fixtures_dir, ["ok"], robots_status=robots_status)
    assert not fetcher.blocked


def test_two_star_groups_robots_keeps_the_stricter_first_group(fixtures_dir):
    """urllib.robotparser giu nhom '*' dau tien (Disallow) lam mac dinh: cach hieu chat hon (FR-003)."""
    robots = (fixtures_dir / "jd" / "robots_two_star_groups.txt").read_text(encoding="utf-8")
    fetcher, requested = make_scripted_fetcher(fixtures_dir, ["ok"], robots_text=robots)
    assert fetcher.fetch(f"{JD_ORIGIN}/subscriptions/new") is None
    assert fetcher.skipped_by_robots == 1
    assert fetcher.fetch(f"{JD_ORIGIN}/it-jobs") is not None
    assert requested == ["/robots.txt", "/it-jobs"]  # /subscriptions/new khong bi goi
