"""T004 (spec 017 US1): van ban embed + ban ghi knowledge_chunks cua JD (data-model §1, research R4). JD tu soan, offline."""
import unicodedata

import pytest

from pipeline.jd_match_text import MAX_TEXT_CHARS, build_match_record, build_match_records, build_match_text
from pipeline.qa_record_builder import content_hash
from jd_match_fakes import make_jd

METADATA_KEYS = {"dataset", "chunk_type", "jd_id", "title", "group", "level", "deadline", "skills", "synthetic"}


def test_text_has_title_level_group_then_requirements_only():
    text = build_match_text(make_jd())
    lines = text.split("\n")
    assert lines[0] == "Backend Developer (Java)"
    assert "Cấp bậc: Mid" in lines and "Nhóm: backend" in lines
    assert lines[-1] == "YEUCAU: 3 năm Java, hiểu SQL."
    assert "MOTA" not in text and "CONGVIEC" not in text and "PHUCLOI" not in text


def test_text_falls_back_to_responsibilities_then_description():
    jd = make_jd()
    del jd["sections"]["requirements"]
    assert build_match_text(jd).endswith("CONGVIEC: viết dịch vụ đặt lịch.")
    del jd["sections"]["responsibilities"]
    assert build_match_text(jd).endswith("MOTA: xây dựng API thanh toán.")
    jd["sections"]["requirements"] = "   "  # section rong coi nhu thieu
    assert build_match_text(jd).endswith("MOTA: xây dựng API thanh toán.")


def test_text_never_has_skills_line_or_summary():
    text = build_match_text(make_jd())
    assert "Kỹ năng" not in text and "Spring Boot" not in text and "Công ty" not in text


def test_text_without_any_body_section_is_just_the_header_lines():
    jd = make_jd(sections={"summary": "x", "benefits": "PHUCLOI"})
    assert build_match_text(jd) == "Backend Developer (Java)\nCấp bậc: Mid\nNhóm: backend"


def test_text_omits_level_line_when_level_is_missing():
    text = build_match_text(make_jd(level=None))
    assert "Cấp bậc" not in text and "Nhóm: backend" in text


def test_text_is_truncated_to_limit_and_hashes_the_stored_content():
    jd = make_jd(sections={"requirements": "Yêu cầu dài " * 400})
    record, _ = build_match_record(jd)
    assert MAX_TEXT_CHARS == 1200
    assert len(record["content"]) <= 1200 and len(build_match_text(jd)) <= 1200
    assert record["content"] == record["content"].rstrip()
    assert record["content_hash"] == content_hash(record["content"])


def test_text_is_nfc_normalized():
    decomposed = unicodedata.normalize("NFD", "Yêu cầu Java")
    text = build_match_text(make_jd(sections={"requirements": decomposed}))
    assert text.endswith(unicodedata.normalize("NFC", "Yêu cầu Java"))


def test_record_fields_follow_data_model():
    record, reason = build_match_record(make_jd())
    assert reason is None
    assert record["source_type"] == "job_description"
    assert (record["category"], record["difficulty"], record["topic_id"]) == (None, None, None)
    assert record["language"] == "vi"
    assert len(record["content_hash"]) == 32 and record["content_hash"] == content_hash(record["content"])
    assert record["metadata"] == {
        "dataset": "jd-match", "chunk_type": "jd_match_summary", "jd_id": "demo:1", "title": "Backend Developer (Java)",
        "group": "backend", "level": "Mid", "deadline": "2026-12-01", "skills": ["java", "spring-boot"], "synthetic": False,
    }
    assert set(record["metadata"]) == METADATA_KEYS


def test_metadata_keeps_null_level_and_deadline_and_synthetic_flag():
    record, _ = build_match_record(make_jd(level=None, deadline=None, synthetic=True, skills=[]))
    meta = record["metadata"]
    assert set(meta) == METADATA_KEYS
    assert meta["level"] is None and meta["deadline"] is None and meta["synthetic"] is True and meta["skills"] == []


def test_group_null_is_rejected_with_no_group_reason():
    assert build_match_record(make_jd(group=None)) == (None, "no_group")


@pytest.mark.parametrize("language,expected", [("mixed", "mixed"), ("vi-VN-extra", "vi-VN"), ("", None), (None, None)])
def test_language_is_cut_to_five_chars(language, expected):
    record, _ = build_match_record(make_jd(language=language))
    assert record["language"] == expected


def test_build_match_records_skips_no_group_and_duplicate_hash_keeping_first():
    jds = [make_jd("a:1"), make_jd("a:2", group=None), make_jd("b:3"), make_jd("c:4", title="Khác", level="Senior")]
    records, skipped = build_match_records(jds)
    assert [r["metadata"]["jd_id"] for r in records] == ["a:1", "c:4"]
    assert skipped == [{"jd_id": "a:2", "reason": "no_group"}, {"jd_id": "b:3", "reason": "duplicate_hash"}]


def test_duplicate_hash_keeps_latest_deadline_and_reports_the_loser():
    jds = [make_jd("a:1", deadline="2026-11-08"), make_jd("a:2", deadline="2026-11-22"), make_jd("a:3", deadline="2026-11-20")]
    records, skipped = build_match_records(jds)
    assert [r["metadata"]["jd_id"] for r in records] == ["a:2"]
    assert skipped == [{"jd_id": "a:1", "reason": "duplicate_hash"}, {"jd_id": "a:3", "reason": "duplicate_hash"}]


def test_duplicate_hash_none_deadline_counts_as_earliest_and_ties_keep_first():
    records, skipped = build_match_records([make_jd("a:1", deadline=None), make_jd("a:2", deadline="2026-11-01")])
    assert [r["metadata"]["jd_id"] for r in records] == ["a:2"] and [s["jd_id"] for s in skipped] == ["a:1"]
    records, skipped = build_match_records([make_jd("b:1", deadline="2026-11-05"), make_jd("b:2", deadline="2026-11-05"),
                                            make_jd("b:3", deadline=None), make_jd("b:4", deadline=None)])
    assert [r["metadata"]["jd_id"] for r in records] == ["b:1"] and len(skipped) == 3
    records, _ = build_match_records([make_jd("c:1", deadline=None), make_jd("c:2", deadline=None)])
    assert [r["metadata"]["jd_id"] for r in records] == ["c:1"]


def test_duplicate_hash_winner_keeps_the_slot_of_first_occurrence_and_its_own_metadata():
    jds = [make_jd("a:1", deadline="2026-11-08", skills=["docker"]), make_jd("z:9", title="Khác"),
           make_jd("a:2", deadline="2026-11-22", skills=["fastapi"])]
    records, _ = build_match_records(jds)
    assert [r["metadata"]["jd_id"] for r in records] == ["a:2", "z:9"]
    assert records[0]["metadata"]["skills"] == ["fastapi"] and records[0]["metadata"]["deadline"] == "2026-11-22"
