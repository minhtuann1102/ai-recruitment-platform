"""T020: quyet dinh soat (data-model §4) — keep/drop/trim, loi trim, gop giu quyet dinh cu, doc/ghi file."""
import json

import pytest

from pipeline.qa_record_builder import content_hash
from pipeline.textbook_review_decisions import (
    Decisions,
    apply_decision,
    load_decisions,
    merge_decisions,
    save_decisions,
)

BODY = " ".join(f"word{i}" for i in range(40))
CONTENT = f"PostgreSQL > WAL\n\n{BODY}\n\nEdit this page on GitHub"


def test_keep_returns_content_unchanged():
    assert apply_decision(CONTENT, {"verdict": "keep"}) == (CONTENT, "keep")


def test_drop_returns_none_with_reason_default_other():
    assert apply_decision(CONTENT, {"verdict": "drop", "reason": "nav"}) == (None, "nav")
    assert apply_decision(CONTENT, {"verdict": "drop"}) == (None, "other")


def test_trim_removes_exact_string_once_and_keeps_heading_line():
    content, reason = apply_decision(CONTENT, {"verdict": "trim", "remove": ["Edit this page on GitHub"]})
    assert reason == "trimmed"
    assert content == f"PostgreSQL > WAL\n\n{BODY}"


@pytest.mark.parametrize("remove", [["Not in the passage"], [""], ["PostgreSQL > WAL"]])
def test_trim_string_missing_or_only_in_heading_raises_with_hash(remove):
    with pytest.raises(ValueError) as exc:
        apply_decision(CONTENT, {"verdict": "trim", "remove": remove})
    assert content_hash(CONTENT) in str(exc.value)


def test_trim_string_appearing_twice_raises():
    content = f"PostgreSQL > WAL\n\n{BODY}\n\nClick here\n\nClick here"
    with pytest.raises(ValueError, match=content_hash(content)):
        apply_decision(content, {"verdict": "trim", "remove": ["Click here"]})


def test_trim_leaving_under_30_words_becomes_drop():
    short = " ".join(f"w{i}" for i in range(31))
    content = f"PostgreSQL > WAL\n\n{short}"
    assert apply_decision(content, {"verdict": "trim", "remove": ["w0 w1"]}) == (None, "too_short_after_trim")


def test_heading_line_words_do_not_count_toward_30():
    short = " ".join(f"w{i}" for i in range(25))
    content = "A very long page title with many words in the heading path > Section\n\n" + short + " junk"
    assert apply_decision(content, {"verdict": "trim", "remove": [" junk"]}) == (None, "too_short_after_trim")


def test_merge_keeps_old_decisions_and_clears_approval():
    old = Decisions("pg", "2026-11-16", "tung", {"h1": {"verdict": "keep"}, "h2": {"verdict": "drop", "reason": "nav"}})
    new = Decisions("pg", "2026-11-20", "", {"h2": {"verdict": "keep"}, "h3": {"verdict": "drop", "reason": "other"}})
    merged = merge_decisions(old, new)
    assert merged.approved_by == ""
    assert merged.decisions["h2"] == {"verdict": "drop", "reason": "nav"}  # cu thang
    assert set(merged.decisions) == {"h1", "h2", "h3"}
    assert merged.reviewed_at == "2026-11-20"
    assert old.approved_by == "tung" and len(old.decisions) == 2  # khong sua doi tuong cu
    with pytest.raises(ValueError):
        merge_decisions(old, Decisions("other"))


def test_load_missing_file_is_empty(tmp_path):
    loaded = load_decisions("nothing", directory=tmp_path)
    assert loaded == Decisions(source_id="nothing", reviewed_at="", approved_by="", decisions={})


def test_save_load_roundtrip_utf8(tmp_path):
    original = Decisions(
        "pg", "2026-11-16", "",
        {"b": {"verdict": "trim", "remove": ["Chinh sua trang nay — đọc thêm"]}, "a": {"verdict": "keep"}},
    )
    path = save_decisions(original, directory=tmp_path / "reviews")
    assert path.name == "pg-decisions.json"
    assert list(json.loads(path.read_text(encoding="utf-8"))["decisions"]) == ["a", "b"]  # sap theo hash
    assert load_decisions("pg", directory=tmp_path / "reviews") == original


def test_load_rejects_unknown_verdict_and_empty_trim(tmp_path):
    for bad in ({"verdict": "maybe"}, {"verdict": "trim", "remove": []}):
        (tmp_path / "pg-decisions.json").write_text(json.dumps({"source_id": "pg", "decisions": {"h": bad}}), encoding="utf-8")
        with pytest.raises(ValueError):
            load_decisions("pg", directory=tmp_path)
