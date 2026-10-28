"""Tach section + chunk JD (spec 009 T023, research R7, FR-012). JD tu soan, cong ty hu cau."""
from pipeline.collect_command import MAX_ANSWER_CHARS
from pipeline.jd_sections import build_chunks, build_summary, heading_key, split_sections, split_text

VI_DESCRIPTION = """Công ty Phần mềm Sao Mai tuyển lập trình viên.
Mô tả công việc
- Phát triển API cho hệ thống đặt vé.
Yêu cầu:
- 3 năm kinh nghiệm Node.js.
- Yêu cầu tối thiểu biết PostgreSQL và Docker trong môi trường production thực tế.
Quyền lợi
- Lương tháng 13."""

EN_DESCRIPTION = """Job Description
Build internal tools.
Your Role & Responsibilities:
• Own the deployment pipeline.
Your skills and experience
1. Python, Django.
Why you’ll love working here
Flexible hours."""


def _jd(sections):
    return {
        "jd_id": "itviec:1001", "sections": sections, "skills": ["nodejs"], "company": "Công ty Sao Mai",
        "language": "vi", "source_url": "https://itviec.example/it-jobs/backend-1001",
    }


def test_vietnamese_headings():
    sections = split_sections(VI_DESCRIPTION)
    assert list(sections) == ["description", "requirements", "benefits"]
    assert sections["description"].startswith("Công ty Phần mềm Sao Mai")  # noi dung truoc tieu de dau tien
    assert "Phát triển API" in sections["description"]
    # dong dai bat dau bang "Yêu cầu" la noi dung, khong phai tieu de moi
    assert "Yêu cầu tối thiểu biết PostgreSQL" in sections["requirements"]
    assert sections["benefits"] == "- Lương tháng 13."


def test_english_headings_with_marks_and_curly_apostrophe():
    sections = split_sections(EN_DESCRIPTION)
    assert sections == {
        "description": "Build internal tools.",
        "requirements": "1. Python, Django.",
        "responsibilities": "• Own the deployment pipeline.",
        "benefits": "Flexible hours.",
    }


def test_careerlink_and_careerviet_requirement_headings():
    careerlink = "Phát triển API nội bộ.\n* Kinh nghiệm / Kỹ năng chi tiết:\n- 2 năm Java."
    assert split_sections(careerlink)["requirements"] == "- 2 năm Java."
    careerviet = (
        "I. Mô tả công việc:\nVận hành kho dữ liệu.\nII. Tiêu chuẩn tuyển dụng:\n1. Trình độ:\nĐại học CNTT.\n"
        "2. Kinh nghiệm:\nTối thiểu 2 năm.\nIII. Quyền lợi:\nThưởng quý."
    )
    sections = split_sections(careerviet)
    assert sections["description"] == "Vận hành kho dữ liệu."
    # tieu de con cua section dang mo giu lai lam noi dung
    assert sections["requirements"] == "1. Trình độ:\nĐại học CNTT.\n2. Kinh nghiệm:\nTối thiểu 2 năm."
    assert sections["benefits"] == "Thưởng quý."


def test_heading_key_variants():
    assert heading_key("## REQUIREMENTS:") == "requirements"
    assert heading_key("II. Trách nhiệm") == "responsibilities"
    assert heading_key("Yêu cầu 3 năm kinh nghiệm") is None


def test_no_heading_gives_summary_and_description_chunks():
    text = "Chúng tôi cần một kỹ sư xây dựng API thanh toán bằng Node.js."
    sections = {"summary": build_summary("Backend Developer", "Công ty Sao Mai", ["Node.js"], "Mid"),
                **split_sections(text)}
    assert list(sections) == ["summary", "description"]
    chunks = build_chunks(_jd(sections))
    assert [c["section"] for c in chunks] == ["summary", "description"]
    assert chunks[0]["content"] == "Backend Developer\nCông ty: Công ty Sao Mai\nCấp bậc: Mid\nKỹ năng: Node.js"
    assert set(chunks[0]) == {"jd_id", "section", "content", "content_hash", "skills", "company", "language", "source_url"}
    assert chunks[0]["content_hash"].startswith("sha256:")


def test_long_section_split_without_losing_content():
    paragraphs = [f"Đoạn {i}: " + "phát triển dịch vụ backend " * 12 for i in range(30)]
    section = "\n".join(paragraphs)
    assert len(section) >= 9000
    chunks = build_chunks(_jd({"summary": "Backend", "requirements": section}))
    parts = [c["content"] for c in chunks if c["section"] == "requirements"]
    assert len(parts) >= 3
    assert all(len(p) <= MAX_ANSWER_CHARS for p in parts)
    assert "\n".join(parts) == section


def test_single_line_longer_than_limit_keeps_every_character():
    line = "x" * 9000
    parts = split_text(line, 4000)
    assert [len(p) for p in parts] == [4000, 4000, 1000]
    assert "".join(parts) == line


def test_chunk_hash_ignores_case_and_spacing():
    a = build_chunks(_jd({"benefits": "Lương  tháng 13"}))[0]["content_hash"]
    b = build_chunks(_jd({"benefits": "lương tháng 13"}))[0]["content_hash"]
    assert a == b
