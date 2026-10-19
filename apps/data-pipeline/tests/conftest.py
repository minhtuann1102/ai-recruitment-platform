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
        }
        pair.update(overrides)
        return {k: v for k, v in pair.items() if v is not ...}  # truyen ... de xoa truong

    return factory
