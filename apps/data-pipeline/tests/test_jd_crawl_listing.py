"""crawl_source / extract_detail_links (T011): gioi han luot, bo qua id da co, robots, record khong dung duoc."""
from datetime import datetime, timezone

import pytest

from crawlers.jd_listing_crawler import crawl_source, extract_detail_links, scrub_record
from crawlers.jd_sources import SOURCES
from crawlers.polite_fetcher import PoliteFetcher
from jd_fake_site import FakeJdWeb

NOW = datetime(2026, 10, 27, 3, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def web(fixtures_dir):
    return FakeJdWeb(fixtures_dir)


def crawl(web, name, existing=(), max_jobs=10, max_pages=None):
    source = SOURCES[name]
    fetcher = PoliteFetcher(
        source.base_url, delay=0, max_pages=100, transport=web.transport, sleep=lambda _s: None, log=lambda _m: None
    )
    return crawl_source(source, fetcher, set(existing), max_jobs, NOW, max_pages=max_pages, log=lambda _m: None)


@pytest.mark.parametrize(
    "name, ids",
    [
        ("itviec", ["1101", "1102", "1103"]),
        ("topdev", ["2201", "2202", "2203"]),
        ("careerviet", ["35C1A2B3", "35C1A2B4", "35C1A2B5"]),
        ("careerlink", ["3301", "3302"]),
    ],
)
def test_extract_links_from_each_listing_fixture(fixtures_dir, name, ids):
    source = SOURCES[name]
    html = (fixtures_dir / "jd" / f"{name}_listing.html").read_text(encoding="utf-8")
    links = extract_detail_links(html, source.listing_url(1), source)
    assert [job_id for _, job_id in links] == ids
    assert all(url.startswith(source.base_url) and "?" not in url and "#" not in url for url, _ in links)


def test_itviec_links_drop_duplicates_categories_and_other_hosts(fixtures_dir):
    source = SOURCES["itviec"]
    html = (fixtures_dir / "jd" / "itviec_listing.html").read_text(encoding="utf-8")
    urls = [url for url, _ in extract_detail_links(html, source.listing_url(1), source)]
    assert urls == [
        "https://itviec.com/it-jobs/backend-nodejs-developer-may-xanh-gia-1101",
        "https://itviec.com/it-jobs/frontend-react-developer-sao-bang-gia-1102",
        "https://itviec.com/it-jobs/devops-engineer-luc-binh-gia-1103",
    ]


def test_max_jobs_caps_detail_requests(web):
    web.serve("itviec")
    records, stats = crawl(web, "itviec", max_jobs=2)
    assert len(records) == stats["new_records"] == stats["detail_pages"] == 2
    assert len(web.detail_requests("itviec")) == 2 and stats["status"] == "ok"
    assert records[0]["crawled_at"] == "2026-10-27T03:00:00Z"


def test_max_pages_caps_listing_pages(web):
    web.serve("itviec", mode="endless")
    _, stats = crawl(web, "itviec", max_jobs=100, max_pages=2)
    assert stats["listing_pages"] == 2 and stats["detail_pages"] == 4


def test_rerun_with_everything_known_stays_within_max_pages(web):
    web.serve("itviec", mode="endless")
    known = {"101", "102", "201", "202"}
    _, stats = crawl(web, "itviec", existing=known, max_jobs=100, max_pages=2)
    assert stats["skipped_existing"] == 4 and stats["new_records"] == 0 and stats["status"] == "ok"
    assert len(web.page_requests("itviec")) == 2 and web.detail_requests("itviec") == []


def test_known_ids_are_skipped_without_request(web):
    web.serve("itviec")
    records, stats = crawl(web, "itviec", existing={"1101"})
    assert {r["source_job_id"] for r in records} == {"1102", "1103"}
    assert stats["skipped_existing"] == 1
    assert not any(url.endswith("-1101") for url in web.requests)


def test_robots_disallowed_detail_counts_as_skip_not_error(web):
    web.serve("itviec", robots_text="User-agent: *\nDisallow: /it-jobs/frontend\n")
    records, stats = crawl(web, "itviec")
    assert {r["source_job_id"] for r in records} == {"1101", "1103"}
    assert stats["skipped_by_robots"] == 1 and stats["errors"] == 0
    assert not any("frontend" in url for url in web.requests)


def test_robots_disallowed_listing_stops_quietly(web):
    web.serve("itviec", robots_text="User-agent: *\nDisallow: /it-jobs\n")
    records, stats = crawl(web, "itviec")
    assert records == [] and stats["skipped_by_robots"] == 1 and stats["errors"] == 0
    assert stats["status"] == "empty" and web.page_requests("itviec") == []


def test_pages_without_job_posting_are_counted_unusable_not_written(web):
    web.serve("topdev", mode="bad_details")
    records, stats = crawl(web, "topdev")
    assert records == [] and stats["detail_pages"] == stats["unusable"] == 3
    assert stats["status"] == "empty"


def test_scrub_record_keeps_identity_fields_and_scrubs_nested_values():
    record = {
        "source": "itviec", "source_job_id": "0912345678", "url": "https://itviec.com/it-jobs/x-0912345678",
        "crawled_at": "2026-10-27T03:00:00Z", "title": "Dev",
        "skills_raw": ["Node", "lienhe@congty-gia.vn"],
        "salary_raw": {"text": "Gọi 0912 345 678", "min": None, "max": None},
        "synthetic": False,
    }
    scrubbed = scrub_record(record)
    assert scrubbed["source_job_id"] == record["source_job_id"] and scrubbed["url"] == record["url"]
    assert scrubbed["skills_raw"] == ["Node", "[email]"]
    assert scrubbed["salary_raw"] == {"text": "Gọi [phone]", "min": None, "max": None}
    assert scrubbed["synthetic"] is False
