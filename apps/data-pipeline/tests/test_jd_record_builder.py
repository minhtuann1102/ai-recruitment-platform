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


GENERIC_DESCRIPTION = (
    "Mô tả công việc\n- Hỗ trợ vận hành hệ thống nội bộ của Công ty Phần mềm Sao Mai, xử lý yêu cầu từ các phòng ban.\n"
    "Yêu cầu\n- Cẩn thận, chủ động, giao tiếp tốt; tốt nghiệp đại học chuyên ngành liên quan.\n"
    "Quyền lợi\n- Lương tháng 13, bảo hiểm sức khỏe, 15 ngày phép mỗi năm."
)


@pytest.mark.parametrize(
    "title, skills_raw",
    [
        ("Nhân viên IT", ...),  # "IT" viet hoa la tu khoa nghe
        ("Kỹ sư hệ thống", ...),
        ("Chuyên viên an toàn thông tin", ...),
        ("Network Administrator", ...),
        ("Nhân viên kiểm thử", ...),
        ("Chuyên viên", ["Java"]),  # the skills_raw co ky nang trong danh muc
    ],
)
def test_it_titles_and_tags_are_kept(dictionary, make_raw_jd, title, skills_raw):
    raw = make_raw_jd(title=title, skills_raw=skills_raw, description_text=GENERIC_DESCRIPTION)
    record, reason = build_record(raw, dictionary)
    assert reason is None and record["title"] == title


@pytest.mark.parametrize(
    "title", ["Senior Security Consultant", "Nhân viên IT - BA ĐÌNH", "IT Support (ca 5 PM - 10 PM)"]
)
def test_technical_consultant_and_lookalike_abbreviations_stay_it(dictionary, make_raw_jd, title):
    record, reason = build_record(make_raw_jd(title=title, description_text=GENERIC_DESCRIPTION), dictionary)
    assert reason is None


def test_generic_skills_alone_do_not_make_a_job_it(dictionary, make_raw_jd):
    # JD ngan hang nhac "cơ sở dữ liệu", "bảo mật thông tin", the "QA/QC": khong du la IT
    description = GENERIC_DESCRIPTION + "\n- Bảo mật thông tin khách hàng, cập nhật cơ sở dữ liệu tài sản."
    raw = make_raw_jd(title="Chuyên viên định giá tài sản", skills_raw=["QA/QC"], description_text=description)
    assert build_record(raw, dictionary) == (None, "not_it")


def test_title_skills_decide_group(dictionary, make_raw_jd):
    description = GENERIC_DESCRIPTION + "\n- Triển khai trên AWS, Azure, Nginx, Docker, Kubernetes."
    record, _ = build_record(make_raw_jd(title="Angular Developer", skills_raw=..., description_text=description), dictionary)
    assert record["group"] == "frontend"  # mo ta nghieng devops nhung tieu de la frontend
    record, _ = build_record(make_raw_jd(title="Chuyên viên", skills_raw=..., description_text=description), dictionary)
    assert record["group"] == "devops"  # tieu de khong co ky nang -> nhom nhieu nhat


@pytest.mark.parametrize(
    "title",
    [
        "Chuyên viên tư vấn giải pháp phần mềm",  # ban hang / tu van phan mem
        "Chuyên viên phân tích nghiệp vụ phần mềm",  # BA tieng Viet
        "Chuyên viên quản lý dự án phần mềm",  # PM tieng Viet
        "Korean IT Interpreter",
        "Chuyen vien San Pham PHAN TICH NGHIEP VU",  # tieu de khong dau
        "Software Sales Executive",
        "Giảng viên Công nghệ thông tin",
        "IT Business Analyst",  # BA / PO / PM ngoai 5 nhom (Clarifications 2026-10-28)
        "Product Owner (Fintech)",
        "Technical Project Manager",
        "BA tiếng Nhật",
    ],
)
def test_out_of_scope_titles_are_not_it_even_with_skills(dictionary, make_raw_jd, title):
    # mo ta mac dinh khop >= 2 ky nang va skills_raw co NodeJS, van bi loai vi tieu de
    assert build_record(make_raw_jd(title=title), dictionary) == (None, "not_it")


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
