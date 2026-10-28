"""Sinh + hau kiem JD synthetic (spec 009 T033, research R9, FR-024, FR-025, FR-027): client LLM gia, offline."""
import json
from datetime import datetime, timezone

import pytest

from jd_fake_llm import FakeLlm, good_answer
from pipeline.jd_synthetic_generator import MAX_RETRIES, generate_one
from pipeline.jd_synthetic_prompt import build_messages, build_params, fictional_company, group_skill_names
from pipeline.skill_dictionary import load_skill_dictionary

NOW = datetime(2026, 10, 28, 6, 0, 0, tzinfo=timezone.utc)
CELL = ("backend", "Junior", "Hà Nội")
RAW_FIELDS = {
    "source", "source_job_id", "url", "crawled_at", "title", "company", "skills_raw", "description_text",
    "location_raw", "experience_raw", "employment_type_raw", "salary_raw", "date_posted", "valid_through", "synthetic",
}


@pytest.fixture(scope="module")
def dictionary():
    return load_skill_dictionary()


def _generate(dictionary, fake, cell=CELL, n=1, companies=frozenset()):
    return generate_one(cell, n, dictionary, fake, companies, NOW)


@pytest.mark.parametrize("cell", [
    ("backend", "Junior", "Hà Nội"), ("frontend", "Intern", "Đà Nẵng"), ("devops", "Lead", "Hồ Chí Minh"),
    ("ai_data", "Senior", "Đà Nẵng"), ("mobile_fullstack", "Manager", "Hà Nội"), ("backend", "Mid", "Hồ Chí Minh"),
])
def test_valid_answer_gives_raw_jd_with_synthetic_flags(dictionary, cell):
    fake = FakeLlm()
    outcome = _generate(dictionary, fake, cell=cell, n=3)
    raw = outcome.record
    assert raw is not None, outcome.reasons
    assert len(fake.calls) == outcome.calls == 1
    assert RAW_FIELDS | {"cell"} == set(raw)
    assert raw["synthetic"] is True and raw["source"] == "synthetic" and raw["url"] is None
    assert raw["cell"] == {"group": cell[0], "level": cell[1], "city": cell[2]}
    assert raw["source_job_id"] == f"syn-{cell[0]}-{cell[1]}-{cell[2]}-3"
    assert raw["location_raw"] == [cell[2]]
    assert set(raw["skills_raw"]) <= set(group_skill_names(dictionary, cell[0]))


@pytest.mark.parametrize("bad_answer, reason", [
    ("không phải json", "bad_json"),
    (json.dumps({"title": "Junior Backend Developer"}), "bad_json"),
    ("EMAIL", "pii"),
    ("PHONE", "pii"),
    ("URL", "url"),
    ("FOREIGN", "foreign_skill"),
    ("CS_DEGREE", "banned_phrase"),
    ("NO_REQUIREMENTS", None),
    ("WRONG_LEVEL", "cell_mismatch"),
])
def test_bad_answer_is_dropped_after_retries_without_looping(dictionary, bad_answer, reason):
    def answer(messages, attempt):
        extras = {
            "EMAIL": "- Gửi CV về tuyendung@maytrang-gia.vn",
            "PHONE": "- Hotline tuyển dụng 0912 345 678",
            "URL": "- Xem thêm tại https://maytrang-gia.vn/careers",
            "FOREIGN": "- Biết thêm React là lợi thế.",
            "CS_DEGREE": "- Ưu tiên tốt nghiệp Khoa học máy tính.",
        }
        if bad_answer in extras:
            return good_answer(messages, extra=extras[bad_answer])
        if bad_answer == "NO_REQUIREMENTS":
            return good_answer(messages, requirements=False)
        if bad_answer == "WRONG_LEVEL":
            return good_answer(messages, level="Senior")
        return bad_answer

    fake = FakeLlm(answer)
    outcome = _generate(dictionary, fake)
    assert outcome.record is None
    assert len(fake.calls) == outcome.calls == 1 + MAX_RETRIES
    assert len(outcome.reasons) == 1 + MAX_RETRIES
    if reason:
        assert all(r.startswith(reason) for r in outcome.reasons), outcome.reasons


def test_retry_sends_reason_and_can_recover(dictionary):
    fake = FakeLlm(lambda messages, attempt: "{" if attempt == 0 else good_answer(messages))
    outcome = _generate(dictionary, fake)
    assert outcome.record is not None and outcome.calls == 2
    assert fake.calls[1][-2] == {"role": "assistant", "content": "{"}
    assert "bad_json" in fake.calls[1][-1]["content"]


def test_provider_error_counts_as_failed_attempt(dictionary):
    def broken(messages):
        raise ConnectionError("mang loi")

    outcome = generate_one(CELL, 1, dictionary, broken, frozenset(), NOW)
    assert outcome.record is None and outcome.calls == 1 + MAX_RETRIES
    assert all(r.startswith("error") for r in outcome.reasons)


def test_generic_skills_from_other_groups_are_allowed(dictionary):
    # "kiểm thử", "bảo mật", "cloud" la ky nang chung chung (nhom devops) xuat hien tu nhien trong JD backend
    extra = "- Phối hợp với QA để kiểm thử, đảm bảo bảo mật thông tin và triển khai trên cloud."
    outcome = _generate(dictionary, FakeLlm(lambda m, a: good_answer(m, extra=extra)))
    assert outcome.record is not None, outcome.reasons


def test_worker_node_banned_outside_devops(dictionary):
    phrase = "- Vận hành cụm máy chủ, theo dõi worker node."
    backend = _generate(dictionary, FakeLlm(lambda m, a: good_answer(m, extra=phrase)))
    assert backend.record is None and backend.reasons[0].startswith("banned_phrase")


def test_same_cell_and_number_give_same_company_id_and_prompt(dictionary):
    first, second = build_params(CELL, 7, dictionary, set()), build_params(CELL, 7, dictionary, set())
    assert first == second and build_messages(first) == build_messages(second)
    assert first.source_job_id == "syn-backend-Junior-Hà Nội-7"
    assert build_params(CELL, 8, dictionary, set()).source_job_id.endswith("-8")


def test_company_is_fictional_and_avoids_crawl_names(dictionary):
    taken = fictional_company(CELL, 1, set())
    other = fictional_company(CELL, 1, {taken.upper()})  # so khop sau chuan hoa
    assert other != taken
    outcome = _generate(dictionary, FakeLlm(), companies={taken})
    assert outcome.record["company"] != taken


def test_prompt_holds_only_cell_parameters(dictionary):
    params = build_params(CELL, 1, dictionary, {"Công ty Thật Sự Tồn Tại"})
    text = "\n".join(m["content"] for m in build_messages(params))
    assert "Công ty Thật Sự Tồn Tại" not in text
    assert "Hà Nội" in text and all(skill in text for skill in params.skills)
