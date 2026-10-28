from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture()
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture()
def sample_catalog_dir() -> Path:
    """Catalog nho (2 topic + 1 scenario) de test khong phu thuoc catalog that cua ai-service."""
    return FIXTURES_DIR / "catalog"


SAMPLE_TOPICS = {"smp.core.event-loop": "Backend", "smp.data.sql-index": "Database"}


@pytest.fixture()
def topics():
    return dict(SAMPLE_TOPICS)


@pytest.fixture()
def make_pair():
    """Tao cap Q&A hop le (cap cong khai); truyen kwargs de ghi de truong."""

    def factory(n: int, **overrides):
        pair = {
            "qa_id": f"de-qa-{n:04d}",
            "topic_id": "smp.core.event-loop",
            "question": f"Câu hỏi số {n} về event loop trong Node.js là gì?",
            "answer": f"Đáp án mẫu số {n}: event loop xử lý callback theo từng pha, microtask chạy trước.",
            "difficulty": "medium",
            "language": "vi",
            "tags": ["event-loop"],
            "source": "https://github.com/DevLoversTeam/nodejs-interview-questions",
            "license": "MIT",
            "attribution": "DevLoversTeam/nodejs-interview-questions contributors",
            "synthetic": False,
            "reviewed_by": "reviewer",
        }
        pair.update(overrides)
        return {k: v for k, v in pair.items() if v is not ...}  # truyen ... de xoa truong

    return factory


# Mo ta JD tu soan (FR-007: khong dung noi dung crawl that), du dai de qua MIN_DESCRIPTION_CHARS
JD_DESCRIPTION = (
    "Mô tả công việc\n"
    "- Phát triển API cho nền tảng đặt lịch khám của Công ty Phần mềm Sao Mai.\n"
    "- Tối ưu truy vấn PostgreSQL và viết test cho dịch vụ thanh toán.\n"
    "Yêu cầu\n"
    "- Ít nhất 3 năm kinh nghiệm Node.js, hiểu Docker và RESTful API.\n"
    "Quyền lợi\n"
    "- Lương tháng 13, bảo hiểm sức khỏe, 15 ngày phép mỗi năm."
)


@pytest.fixture()
def make_raw_jd():
    """Raw JD hop le theo contract (du lieu bia); kwargs ghi de truong, truyen ... de xoa truong."""

    def factory(job_id: str = "1001", source: str = "itviec", **overrides):
        raw = {
            "source": source,
            "source_job_id": job_id,
            "url": f"https://{source}.example/jobs/{job_id}",
            "crawled_at": "2026-10-27T03:00:00Z",
            "title": "Backend Developer (Node.js)",
            "company": "Công ty Phần mềm Sao Mai",
            "skills_raw": ["NodeJS", "PostgreSQL"],
            "description_text": JD_DESCRIPTION,
            "location_raw": ["Hồ Chí Minh"],
            "experience_raw": "36 months",
            "employment_type_raw": ["FULL_TIME"],
            "salary_raw": {"currency": "VND", "min": 20000000, "max": 30000000, "text": None},
            "date_posted": "2026-10-20",
            "valid_through": "2026-11-20",
            "synthetic": False,
        }
        raw.update(overrides)
        return {k: v for k, v in raw.items() if v is not ...}

    return factory
