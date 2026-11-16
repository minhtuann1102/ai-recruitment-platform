"""crawlers/textbook_manifest_crawler: chi tai URL status use, tai mot lan moi URL, loi / rong vao skipped, lo khong dung.
Offline: fetcher gia ghi lai moi loi goi de dem."""
from datetime import datetime, timezone

import pytest

from crawlers.textbook_manifest_crawler import crawl_source, github_target
from pipeline.textbook_manifest_models import Source, SourcePage

NOW = datetime(2026, 11, 16, 8, 30, 0, tzinfo=timezone.utc)
BLOB = "https://github.com/acme/primer/blob/master/solutions/cache.md"
RAW = "https://raw.githubusercontent.com/acme/primer/master/README.md"


def _page(url, status="use", sections=None):
    return SourcePage(url=url, status=status, sections=sections or [])


def _html_source(urls, selector="#docContent", **kwargs):
    pages = [_page(u) if isinstance(u, str) else u for u in urls]
    return Source(source_id="demo-html", format="html", content_selector=selector, status="use", pages=pages, **kwargs)


def _md_source(urls):
    return Source(source_id="demo-md", format="markdown", status="use", pages=[_page(u) for u in urls])


class FakeHtml:
    """fetch_html gia: tra theo bang {url: html | None | Exception}; URL la nem KeyError; calls ghi moi lan goi."""

    def __init__(self, table):
        self.table, self.calls = table, []

    def __call__(self, url):
        self.calls.append(url)
        value = self.table[url]
        if isinstance(value, Exception):
            raise value
        return value


class FakeMarkdown:
    def __init__(self, table=None, error=None):
        self.table, self.error, self.calls = table or {}, error, []

    def __call__(self, repo, path):
        self.calls.append((repo, path))
        if self.error:
            raise self.error
        return self.table.get((repo, path))


def _never(*_args):
    raise AssertionError("fetcher khong duoc goi")


@pytest.fixture()
def guide_html(fixtures_dir):
    return (fixtures_dir / "textbook" / "guide_page.html").read_text(encoding="utf-8")


@pytest.fixture()
def readme_md(fixtures_dir):
    return (fixtures_dir / "textbook" / "readme.md").read_text(encoding="utf-8")


def test_html_pages_parsed_with_sections_and_record_shape(guide_html):
    fetch = FakeHtml({"https://x.test/a": guide_html, "https://x.test/b": guide_html})
    pages, skipped = crawl_source(_html_source(["https://x.test/a", "https://x.test/b"]), fetch, _never, NOW)
    assert skipped == {} and len(pages) == 2
    first = pages[0]
    assert set(first) == {"source_id", "url", "title", "sections", "crawled_at"}
    assert first["source_id"] == "demo-html" and first["url"] == "https://x.test/a"
    assert first["title"] == "Explicit Locking"
    assert [s["heading_path"] for s in first["sections"]] == [[], ["Row-Level Locks"], ["Row-Level Locks", "FOR UPDATE"], ["Deadlocks"]]
    assert first["crawled_at"] == "2026-11-16T08:30:00+00:00"


def test_url_outside_manifest_and_excluded_page_are_never_called(guide_html):
    source = _html_source(["https://x.test/a", _page("https://x.test/excluded", status="excluded")])
    fetch = FakeHtml({"https://x.test/a": guide_html})
    crawl_source(source, fetch, _never, NOW)
    assert fetch.calls == ["https://x.test/a"]  # chi dung URL status use; excluded khong bi cham toi


def test_source_excluded_crawls_nothing(guide_html):
    source = _html_source(["https://x.test/a"])
    source.status = "excluded"
    pages, skipped = crawl_source(source, _never, _never, NOW)
    assert pages == [] and skipped == {}


def test_none_goes_to_skipped_and_batch_continues(guide_html):
    fetch = FakeHtml({"https://x.test/bad": None, "https://x.test/ok": guide_html})
    pages, skipped = crawl_source(_html_source(["https://x.test/bad", "https://x.test/ok"]), fetch, _never, NOW)
    assert skipped == {"https://x.test/bad": "fetch_failed"}
    assert [p["url"] for p in pages] == ["https://x.test/ok"]


def test_fetch_exception_is_fetch_failed_not_a_crash(guide_html):
    fetch = FakeHtml({"https://x.test/boom": RuntimeError("timeout"), "https://x.test/ok": guide_html})
    pages, skipped = crawl_source(_html_source(["https://x.test/boom", "https://x.test/ok"]), fetch, _never, NOW)
    assert skipped == {"https://x.test/boom": "fetch_failed"} and len(pages) == 1


def test_empty_body_or_no_content_region_is_empty(guide_html):
    fetch = FakeHtml({"https://x.test/blank": "  \n", "https://x.test/nosel": "<html><body><p>hi</p></body></html>"})
    pages, skipped = crawl_source(_html_source(["https://x.test/blank", "https://x.test/nosel"]), fetch, _never, NOW)
    assert pages == [] and skipped == {"https://x.test/blank": "empty", "https://x.test/nosel": "empty"}


def test_robots_skip_is_reported_when_fetcher_counts_it():
    class RobotsFetcher:  # giong PoliteFetcher: method fetch + bo dem skipped_by_robots
        skipped_by_robots = 0

        def fetch(self, url):
            if "private" in url:
                self.skipped_by_robots += 1
            return None

    fetcher = RobotsFetcher()
    _, skipped = crawl_source(_html_source(["https://x.test/private", "https://x.test/down"]), fetcher.fetch, _never, NOW)
    assert skipped == {"https://x.test/private": "robots_disallowed", "https://x.test/down": "fetch_failed"}


def test_same_url_in_several_rows_is_fetched_once(guide_html):
    rows = [_page("https://x.test/a", sections=["Row-Level Locks"]), _page("https://x.test/a", sections=["Deadlocks"])]
    fetch = FakeHtml({"https://x.test/a": guide_html})
    pages, _ = crawl_source(_html_source(rows), fetch, _never, NOW)
    assert fetch.calls == ["https://x.test/a"] and len(pages) == 1


@pytest.mark.parametrize("url", [BLOB, RAW, "https://raw.githubusercontent.com/acme/primer/refs/heads/master/solutions/cache.md"])
def test_markdown_source_calls_github_client_with_repo_and_path(readme_md, url):
    client = FakeMarkdown({("acme/primer", "solutions/cache.md"): readme_md, ("acme/primer", "README.md"): readme_md})
    pages, skipped = crawl_source(_md_source([url]), _never, client, NOW)
    expected = "README.md" if url == RAW else "solutions/cache.md"
    assert client.calls == [("acme/primer", expected)] and skipped == {}
    assert pages[0]["title"] == "The Sample Primer" and pages[0]["url"] == url  # url giu nguyen nhu trong manifest


def test_markdown_unrecognised_url_is_skipped_without_a_call():
    client, html = FakeMarkdown(), FakeHtml({})
    _, skipped = crawl_source(_md_source(["https://example.com/readme.md"]), html, client, NOW)
    assert skipped == {"https://example.com/readme.md": "fetch_failed"}
    assert client.calls == [] and html.calls == []  # sentinel ghi lai: khong goi nham sang fetch_html


def test_markdown_http_error_is_fetch_failed_and_empty_file_is_empty(readme_md):
    _, skipped = crawl_source(_md_source([BLOB]), _never, FakeMarkdown(error=RuntimeError("404")), NOW)
    assert skipped == {BLOB: "fetch_failed"}
    client = FakeMarkdown({("acme/primer", "solutions/cache.md"): "no headings here, just text\n"})
    pages, skipped = crawl_source(_md_source([BLOB]), _never, client, NOW)
    assert pages == [] and skipped == {BLOB: "empty"}


def test_now_may_be_a_callable_and_naive_datetime_is_utc(guide_html):
    fetch = FakeHtml({"https://x.test/a": guide_html})
    pages, _ = crawl_source(_html_source(["https://x.test/a"]), fetch, _never, lambda: datetime(2026, 1, 2, 3, 4, 5))
    assert pages[0]["crawled_at"] == "2026-01-02T03:04:05+00:00"


def test_github_target_parses_real_manifest_form_and_rejects_others():
    assert github_target("https://raw.githubusercontent.com/donnemartin/system-design-primer/master/README.md") == (
        "donnemartin/system-design-primer",
        "README.md",
    )
    assert github_target("https://github.com/a/b/blob/main/docs/x.md#frag") == ("a/b", "docs/x.md")
    assert github_target("https://gitlab.com/a/b/blob/main/x.md") is None
