"""Raw JD -> Normalized JD, loc IT, dedup (spec 009 T025, research R7, FR-008, FR-013, FR-028). Du lieu bia."""
import pytest

from pipeline.jd_record_builder import MIN_DESCRIPTION_CHARS, build_record, content_hash
from pipeline.jd_record_dedup import build_records
from pipeline.skill_dictionary import load_skill_dictionary

NOT_IT_DESCRIPTION = (
    "Mô tả công việc\n- Thiết kế ấn phẩm quảng cáo, banner và bao bì cho chuỗi cửa hàng bánh Hoa Mai.\n"
    "- Phối hợp phòng marketing lên ý tưởng chiến dịch mùa lễ hội.\n"
    "Yêu cầu\n- Thành thạo Photoshop, Illustrator; có thẩm mỹ tốt, chịu được áp lực deadline.\n"
    "Quyền lợi\n- Thưởng theo dự án, du lịch hằng năm."
)


@pytest.fixture(scope="module")
def dictionary():
    return load_skill_dictionary()


def test_normalized_fields(dictionary, make_raw_jd):
    record, reason = build_record(make_raw_jd(), dictionary)
    assert reason is None
    assert record["jd_id"] == "itviec:1001"
    assert record["skills"] == ["docker", "nodejs", "postgresql", "rest-api"]
    assert (record["group"], record["level"], record["work_type"], record["city"]) == ("backend", "Mid", "onsite", "Hồ Chí Minh")
    assert (record["salary_min"], record["salary_max"], record["salary_currency"]) == (20000000, 30000000, "VND")
    assert (record["date_posted"], record["deadline"], record["language"]) == ("2026-10-20", "2026-11-20", "vi")
    assert list(record["sections"]) == ["summary", "description", "requirements", "benefits"]
    assert record["content_hash"].startswith("sha256:") and record["synthetic"] is False
    assert record["source_url"] == "https://itviec.example/jobs/1001"


def test_graphic_design_job_is_not_it(dictionary, make_raw_jd):
    raw = make_raw_jd(title="Nhân viên Thiết kế Đồ họa", skills_raw=["Photoshop"], description_text=NOT_IT_DESCRIPTION)
    assert build_record(raw, dictionary) == (None, "not_it")


def test_short_non_it_posting_is_not_it_and_short_it_posting_is_missing(dictionary, make_raw_jd):
    short = "Bán hàng tại cửa hàng tiện lợi, ca xoay, thưởng doanh số."
    assert build_record(make_raw_jd(title="Nhân viên bán hàng", description_text=short), dictionary) == (None, "not_it")
    short_it = "Phát triển API Node.js cho hệ thống nội bộ."
    assert len(short_it) < MIN_DESCRIPTION_CHARS
    assert build_record(make_raw_jd(description_text=short_it), dictionary) == (None, "missing_field")


@pytest.mark.parametrize("field", ["title", "company", "description_text", "url"])
def test_missing_required_field(dictionary, make_raw_jd, field):
    assert build_record(make_raw_jd(**{field: ...}), dictionary) == (None, "missing_field")


def test_synthetic_needs_no_url(dictionary, make_raw_jd):
    record, _ = build_record(make_raw_jd("syn-backend-Mid-hcm-1", source="synthetic", url=None, synthetic=True), dictionary)
    assert record["synthetic"] is True and record["source_url"] is None


def test_careerlink_without_skills_raw_extracts_from_description(dictionary, make_raw_jd):
    raw = make_raw_jd(source="careerlink", title="Lập trình viên", skills_raw=...)
    record, _ = build_record(raw, dictionary)
    assert record["skills"] == ["docker", "nodejs", "postgresql", "rest-api"]


def test_unknown_skills_are_kept_and_text_salary_is_empty(dictionary, make_raw_jd):
    raw = make_raw_jd(skills_raw=["NodeJS", "Odoo"], salary_raw={"text": "You'll love it", "min": None, "max": None})
    record, _ = build_record(raw, dictionary)
    assert record["skills_unknown"] == ["Odoo"]
    assert (record["salary_min"], record["salary_max"], record["salary_currency"]) == (None, None, None)


def test_cleaning_keeps_vietnamese_marks_and_removes_contact(dictionary, make_raw_jd):
    description = "<p>Phát&nbsp;triển   ứng dụng​ Node.js</p>\n" + "Liên hệ: Chị Lan 0912 345 678\n" + "x" * 200
    record, _ = build_record(make_raw_jd(description_text=description), dictionary)
    text = record["sections"]["description"]
    assert text.startswith("Phát triển ứng dụng Node.js")
    assert "Chị Lan" not in text and "0912" not in text


def test_duplicate_across_sources_keeps_richer_record(dictionary, make_raw_jd):
    poor = make_raw_jd("C1", source="careerlink", location_raw=[], salary_raw=None, valid_through=None)
    rich = make_raw_jd("1001", source="itviec")
    result = build_records([poor, rich], dictionary)
    assert [r["jd_id"] for r in result.records] == ["itviec:1001"]
    assert result.rejected == [{"jd_id": "careerlink:C1", "reason": "duplicate"}]


def test_same_id_in_two_raw_files_is_duplicate(dictionary, make_raw_jd):
    result = build_records([make_raw_jd(), make_raw_jd()], dictionary)
    assert len(result.records) == 1 and result.rejected == [{"jd_id": "itviec:1001", "reason": "duplicate"}]


def test_near_duplicate_only_warns(dictionary, make_raw_jd):
    a = make_raw_jd("2002")
    b = make_raw_jd("3003", source="topdev", description_text=a["description_text"] + "\n- Làm việc thứ 2 đến thứ 6.")
    result = build_records([b, a], dictionary)
    assert [r["jd_id"] for r in result.records] == ["itviec:2002", "topdev:3003"]  # sap theo jd_id
    assert result.near_duplicates == [["itviec:2002", "topdev:3003"]]
    assert result.rejected == []


def test_content_hash_normalizes_case_space_and_unicode_form():
    composed = content_hash("Công ty A", "Backend Dev", "Phát triển")
    decomposed = content_hash("CÔNG  TY a", "backend  dev", "Phát triển")
    assert composed == decomposed
