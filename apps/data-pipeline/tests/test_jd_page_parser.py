"""parse_job_page tren fixture tu soan cua 4 nguon (T010): JSON-LD mang / @graph, JSON loi, luong chu / so."""
import dataclasses
import json

import pytest

from crawlers.jd_page_parser import missing_required, parse_job_page
from crawlers.jd_sources import SOURCES

NOW = "2026-10-27T03:00:00Z"
URLS = {
    "itviec": "https://itviec.com/it-jobs/backend-nodejs-developer-may-xanh-gia-1101",
    "careerviet": "https://careerviet.vn/vi/tim-viec-lam/lap-trinh-vien-frontend-reactjs.35C1A2B3.html",
    "topdev": "https://topdev.vn/detail-jobs/backend-developer-java-spring-2201",
    "careerlink": "https://www.careerlink.vn/viec-lam/lap-trinh-vien-net/3301",
}


def parse_fixture(fixtures_dir, name, source_name=None, url=None, source=None):
    source_name = source_name or name.split("_")[0]
    html = (fixtures_dir / "jd" / f"{name}.html").read_text(encoding="utf-8")
    return parse_job_page(html, source or SOURCES[source_name], url or URLS[source_name], NOW)


def page_with(posting: dict) -> str:
    body = json.dumps({"@type": "JobPosting", "title": "Dev", **posting}, ensure_ascii=False)
    return f'<html><head><script type="application/ld+json">{body}</script></head></html>'


def test_itviec_picks_job_posting_out_of_json_ld_array(fixtures_dir):
    record = parse_fixture(fixtures_dir, "itviec_detail")
    assert (record["source"], record["source_job_id"], record["url"], record["crawled_at"]) == (
        "itviec", "1101", URLS["itviec"], NOW
    )
    assert record["title"] == "Backend NodeJS Developer"
    assert record["company"] == "Công ty TNHH Phần mềm Mây Xanh Giả"
    assert record["skills_raw"] == ["NodeJS", "TypeScript", "PostgreSQL", "Docker"]
    assert record["location_raw"] == ["Hồ Chí Minh", "Hà Nội"]  # addressRegion, khong phai quan / huyen
    assert record["experience_raw"] == "24 months"
    assert record["employment_type_raw"] == ["FULL_TIME"]
    assert (record["date_posted"], record["valid_through"]) == ("2026-10-20", "2026-11-20")
    assert record["synthetic"] is False
    assert missing_required(record) == []


def test_itviec_text_salary_has_no_numbers(fixtures_dir):
    record = parse_fixture(fixtures_dir, "itviec_detail")
    assert record["salary_raw"] == {"text": "Sign in to view salary", "min": None, "max": None}


def test_description_keeps_section_headings_on_own_lines_and_inline_tags_joined(fixtures_dir):
    lines = parse_fixture(fixtures_dir, "itviec_detail")["description_text"].split("\n")
    assert lines[0] == "Mô tả công việc"
    assert {"Yêu cầu", "Quyền lợi"} <= set(lines)
    assert "Thiết kế schema PostgreSQL và viết migration" in lines  # <strong> khong ngat dong


def test_careerviet_graph_numeric_salary_and_string_skills(fixtures_dir):
    record = parse_fixture(fixtures_dir, "careerviet_detail")
    assert record["source_job_id"] == "35C1A2B3"
    assert record["title"] == "Lập trình viên Frontend ReactJS"
    assert record["skills_raw"] == ["ReactJS", "TypeScript", "Redux"]
    assert record["salary_raw"] == {"currency": "VND", "min": 20000000, "max": 30000000, "text": None}
    assert record["experience_raw"] == "36 months"
    assert record["location_raw"] == ["Hồ Chí Minh"]
    assert record["valid_through"] == "2026-11-20"  # bo gio / mui gio
    # parser khong xoa PII: viec do crawl_source, de test duoc rieng
    assert "Liên hệ: Anh Minh - 0912 345 678 - hr@congty-gia.vn" in record["description_text"]


def test_topdev_takes_full_description_from_html_not_short_json_ld(fixtures_dir):
    record = parse_fixture(fixtures_dir, "topdev_detail")
    text = record["description_text"]
    assert "Thiết kế API và tối ưu truy vấn MySQL" in text  # chi co trong HTML
    assert "Yêu cầu" in text.split("\n") and "Quyền lợi" in text.split("\n")
    assert len(text) > 300
    assert record["location_raw"] == ["Đà Nẵng"]
    assert record["salary_raw"] == {"text": "Thỏa thuận", "min": None, "max": None}


@pytest.mark.parametrize("selector", [None, "#khong-co-phan-tu-nay"])
def test_topdev_falls_back_to_json_ld_description(fixtures_dir, selector):
    source = dataclasses.replace(SOURCES["topdev"], description_selector=selector)
    record = parse_fixture(fixtures_dir, "topdev_detail", source=source)
    assert record["description_text"].startswith("Tham gia phát triển hệ thống thanh toán nội bộ")
    assert len(record["description_text"]) < 200


def test_careerlink_has_no_skills_and_merges_location_type(fixtures_dir):
    record = parse_fixture(fixtures_dir, "careerlink_detail")
    assert record["skills_raw"] == []
    assert record["employment_type_raw"] == ["FULL_TIME", "TELECOMMUTE"]
    assert record["experience_raw"] == "1 - 3 năm"
    assert record["salary_raw"] == {"text": "Thỏa thuận", "min": None, "max": None}
    assert record["location_raw"] == ["Hà Nội"]


def test_broken_json_ld_block_is_skipped_valid_block_still_parsed(fixtures_dir):
    record = parse_fixture(fixtures_dir, "broken_jsonld", "itviec")
    assert record["title"] == "Kỹ sư DevOps (Kubernetes)"
    assert record["description_text"] == "Vận hành cụm Kubernetes và quy trình CI/CD cho các dịch vụ nội bộ."
    assert record["salary_raw"] is None and record["skills_raw"] == []


def test_page_without_job_posting_returns_none(fixtures_dir):
    assert parse_fixture(fixtures_dir, "no_jobposting", "itviec") is None
    assert parse_fixture(fixtures_dir, "challenge", "itviec") is None


def test_missing_required_names_empty_fields(fixtures_dir):
    record = parse_fixture(fixtures_dir, "itviec_detail", url="https://itviec.com/it-jobs/python")
    assert record["source_job_id"] == "" and missing_required(record) == ["source_job_id"]
    record = parse_job_page(page_with({"hiringOrganization": {"name": "Cty"}}), SOURCES["itviec"], URLS["itviec"], NOW)
    assert missing_required(record) == ["description_text"]


@pytest.mark.parametrize(
    "base_salary, expected",
    [
        ({"currency": "VND", "value": {"value": 15000000}}, {"currency": "VND", "min": 15000000, "max": 15000000, "text": None}),
        ({"currency": "USD", "value": {"minValue": "1000", "maxValue": 2000.5}}, {"currency": "USD", "min": 1000, "max": 2000.5, "text": None}),
        ({"currency": "VND", "value": {"minValue": 0, "maxValue": 0}}, None),
        ("Cạnh tranh", {"text": "Cạnh tranh", "min": None, "max": None}),
        ({"currency": "VND", "value": {"minValue": "15.000.000", "maxValue": "25.000.000"}},
         {"currency": "VND", "min": 15000000, "max": 25000000, "text": None}),
        ({"currency": "USD", "value": {"minValue": "1.500", "maxValue": "2,500"}},
         {"currency": "USD", "min": 1500, "max": 2500, "text": None}),
        ({"currency": "USD", "value": {"value": "2.5"}}, {"currency": "USD", "min": 2.5, "max": 2.5, "text": None}),
        ({"value": {"minValue": "Thỏa thuận"}}, {"text": "Thỏa thuận", "min": None, "max": None}),
        (None, None),
    ],
)
def test_salary_number_shapes(base_salary, expected):
    html = page_with({"baseSalary": base_salary, "hiringOrganization": "Cty", "description": "Mô tả"})
    assert parse_job_page(html, SOURCES["itviec"], URLS["itviec"], NOW)["salary_raw"] == expected
