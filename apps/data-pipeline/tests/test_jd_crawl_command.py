"""run_crawl_jd tren web gia lap (T014): raw day du truong + 0 PII, chay lai idempotent, nguon bi chan, danh sach rong."""
import argparse
import json

import pytest

from crawlers.jd_page_parser import missing_required
from jd_fake_site import FakeJdWeb
from pipeline import jd_crawl_command
from pipeline.jd_crawl_command import run_crawl_jd, too_many_unusable
from pipeline.jd_pii import count_jd_pii


@pytest.fixture()
def web(fixtures_dir):
    return FakeJdWeb(fixtures_dir)


@pytest.fixture()
def raw_dir(tmp_path, monkeypatch):
    path = tmp_path / "raw" / "jd"
    monkeypatch.setattr(jd_crawl_command, "JD_RAW_DIR", path)
    return path


def crawl(web, sources, max_pages=3, max_jobs=10):
    args = argparse.Namespace(source=list(sources), max_pages=max_pages, max_jobs=max_jobs, delay=0)
    return run_crawl_jd(args, transport=web.transport, sleep=lambda _s: None)


def read_records(raw_dir, source):
    files = sorted((raw_dir / source).glob("*.jsonl"))
    return [json.loads(line) for f in files for line in f.read_text(encoding="utf-8").splitlines()]


def all_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from all_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from all_strings(item)


def test_raw_has_required_fields_and_zero_pii(web, raw_dir, capsys):
    web.serve("itviec")
    web.serve("careerviet")
    assert crawl(web, ["itviec", "careerviet"]) == 0
    for source in ("itviec", "careerviet"):
        records = read_records(raw_dir, source)
        assert sorted(r["source_job_id"] for r in records) == sorted({r["source_job_id"] for r in records})
        assert len(records) == 3 and all(missing_required(r) == [] for r in records)
        assert all(r["source"] == source and r["synthetic"] is False for r in records)
        assert sum(count_jd_pii(s) for r in records for s in all_strings(r)) == 0
    assert {r["source_job_id"] for r in read_records(raw_dir, "itviec")} == {"1101", "1102", "1103"}
    description = read_records(raw_dir, "careerviet")[0]["description_text"]
    assert "0912" not in description and "congty-gia.vn" not in description and "Liên hệ" not in description
    assert "ReactJS" in description  # noi dung that su van con
    assert "Email: [email]" in read_records(raw_dir, "itviec")[0]["description_text"]
    out = capsys.readouterr().out
    assert "robots checked: https://itviec.com/robots.txt [200]" in out and "record mới: 3" in out
    assert "Công ty" in next((raw_dir / "itviec").glob("*.jsonl")).read_text(encoding="utf-8")  # khong escape \u


def test_crawl_touches_only_own_hosts_and_never_other_host_links(web, raw_dir):
    web.serve("itviec")
    web.serve("careerviet")
    crawl(web, ["itviec", "careerviet"])
    assert all(url.startswith(("https://itviec.com/", "https://careerviet.vn/")) for url in web.requests)
    assert not any("khac-host" in url or "subscriptions" in url for url in web.requests)


def test_rerun_adds_no_record_and_sends_no_detail_request(web, raw_dir, capsys):
    web.serve("itviec")
    assert crawl(web, ["itviec"]) == 0
    web.requests.clear()
    capsys.readouterr()
    assert crawl(web, ["itviec"]) == 0
    out = capsys.readouterr().out
    assert "record mới: 0" in out and "id đã có, bỏ qua: 3" in out
    assert web.detail_requests("itviec") == []
    assert len(list((raw_dir / "itviec").glob("*.jsonl"))) == 1  # khong ghi file moi
    assert len(read_records(raw_dir, "itviec")) == 3


def test_blocked_source_exits_4_and_other_source_still_written(web, raw_dir, capsys):
    web.serve("itviec", mode="blocked")
    web.serve("careerviet")
    assert crawl(web, ["itviec", "careerviet"], max_pages=5) == 4
    assert len(read_records(raw_dir, "careerviet")) == 3
    assert read_records(raw_dir, "itviec") == []
    assert len(web.page_requests("itviec")) == 3  # dung dung sau 3 lan 403 lien tiep, khong gui them
    captured = capsys.readouterr()
    assert "source blocked: https://itviec.com" in captured.out and "trạng thái: blocked" in captured.out
    assert "itviec" in captured.err


@pytest.mark.parametrize("robots_status", [403, 429])
def test_robots_blocked_exits_4_without_any_page_request(web, raw_dir, robots_status):
    web.serve("itviec", robots_status=robots_status)
    assert crawl(web, ["itviec"]) == 4
    assert web.page_requests("itviec") == []


def test_listing_without_links_exits_1_and_writes_nothing(web, raw_dir, capsys):
    web.serve("careerlink", mode="no_links")
    web.serve("itviec")
    assert crawl(web, ["careerlink", "itviec"]) == 1
    assert read_records(raw_dir, "careerlink") == [] and len(read_records(raw_dir, "itviec")) == 3
    captured = capsys.readouterr()
    assert "trạng thái: empty" in captured.out and "careerlink" in captured.err


def test_detail_pages_without_job_posting_exit_1(web, raw_dir):
    web.serve("topdev", mode="bad_details")
    assert crawl(web, ["topdev"]) == 1
    assert read_records(raw_dir, "topdev") == []


def test_server_errors_are_not_reported_as_success(web, raw_dir):
    web.serve("careerviet", mode="server_error")
    assert crawl(web, ["careerviet"], max_pages=10) == 1  # khong phai 4: 500 khong phai tin hieu chan bot
    assert len(web.page_requests("careerviet")) == 3  # dung sau 3 trang danh sach loi lien tiep


def test_unusable_ratio_boundary():
    assert too_many_unusable({"detail_pages": 4, "unusable": 3})
    assert not too_many_unusable({"detail_pages": 4, "unusable": 2})  # dung 50% chua that bai
    assert not too_many_unusable({"detail_pages": 0, "unusable": 0})


@pytest.mark.parametrize("overrides", [{"max_pages": 0}, {"max_jobs": 0}])
def test_invalid_limits_exit_1_without_request(web, raw_dir, overrides):
    web.serve("itviec")
    assert crawl(web, ["itviec"], **overrides) == 1
    assert web.requests == []
