import json

import pytest

from pipeline.seed_review_command import approve, parse_ids, unreviewed_pairs


def test_parse_ids_supports_ranges_and_single_ids():
    assert parse_ids("de-qa-1000..1002, de-qa-1050") == {"de-qa-1000", "de-qa-1001", "de-qa-1002", "de-qa-1050"}
    assert parse_ids("de-qa-1000..de-qa-1001") == {"de-qa-1000", "de-qa-1001"}
    with pytest.raises(ValueError):
        parse_ids("1000-1002")


def test_approve_sets_reviewer_only_on_listed_pairs(tmp_path, make_pair):
    pairs = [make_pair(1000, reviewed_by=...), make_pair(1001, reviewed_by=...), make_pair(1002, reviewed_by="DE")]
    (tmp_path / "hard-x.json").write_text(json.dumps(pairs, ensure_ascii=False), encoding="utf-8")
    assert [p["qa_id"] for p in unreviewed_pairs(tmp_path)] == ["de-qa-1000", "de-qa-1001"]

    assert approve({"de-qa-1000", "de-qa-9999"}, "minhtuann1102", tmp_path) == {"de-qa-1000"}
    saved = {p["qa_id"]: p.get("reviewed_by") for p in json.loads((tmp_path / "hard-x.json").read_text(encoding="utf-8"))}
    assert saved == {"de-qa-1000": "minhtuann1102", "de-qa-1001": None, "de-qa-1002": "DE"}
