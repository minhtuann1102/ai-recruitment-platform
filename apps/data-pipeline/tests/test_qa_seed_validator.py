import json

import pytest

from pipeline.qa_seed_loader import SeedError, SeedItem, load_seed_items
from pipeline.qa_seed_validator import validate_seed
from pipeline.settings import CRAWLED_DATASET, CURATED_DATASET


def items(*pairs):
    return [SeedItem(data=p, file="seed.json", index=i) for i, p in enumerate(pairs)]


def rules_of(result, level="error"):
    return {(i.qa_id, i.rule) for i in result.issues if i.level == level}


def test_valid_seed_has_no_pair_errors(make_pair, topics):
    pairs = [make_pair(1), make_pair(2, topic_id="smp.data.sql-index"), make_pair(3, source="self", license="CC-BY-4.0", synthetic=True, reviewed_by="DE", attribution=...)]
    result = validate_seed(items(*pairs), topics)
    assert result.errors == []
    assert [it.qa_id for it in result.valid] == ["de-qa-0001", "de-qa-0002", "de-qa-0003"]


@pytest.mark.parametrize(
    "overrides, rule",
    [
        ({"answer": ...}, "schema"),
        ({"topic_id": "smp.unknown.topic"}, "topic_id"),
        ({"topic_id": "scn.smp.cache-stampede"}, "topic_id"),
        ({"license": "CC-BY-NC-4.0"}, "license"),
        ({"license": "GPL-2.0"}, "license"),
        ({"attribution": ...}, "provenance"),
        ({"source": "self"}, "provenance"),
        ({"reviewed_by": ...}, "review"),
        ({"reviewed_by": "  "}, "review"),
        ({"synthetic": True, "reviewed_by": ...}, "review"),
        ({"license": "CC-BY-SA-4.0"}, "license"),
        ({"source": "self", "license": "MIT", "synthetic": True, "attribution": ...}, "license"),
        ({"qa_id": "qa-1"}, "qa_id"),
        ({"difficulty": "expert"}, "enum"),
        ({"answer": "Gọi 0912 345 678 để được giải thích event loop chi tiết hơn nhé"}, "pii"),
    ],
)
def test_invalid_pair_is_listed_with_reason(make_pair, topics, overrides, rule):
    bad = make_pair(2, **overrides)
    result = validate_seed(items(make_pair(1), bad), topics)
    assert rule in {r for _, r in rules_of(result)}
    assert [it.qa_id for it in result.valid] == ["de-qa-0001"]
    assert result.rejected_qa_ids and result.rejected_qa_ids[0] in (bad.get("qa_id"), "seed.json#1")


def test_exact_duplicate_question_reports_both_ids_and_keeps_lower(make_pair, topics):
    a = make_pair(7, question="Event loop   là gì?")
    b = make_pair(3, question="event LOOP là gì?")
    result = validate_seed(items(a, b), topics)
    dup = [i for i in result.issues if i.rule == "duplicate_question"]
    assert len(dup) == 1 and dup[0].qa_id == "de-qa-0007" and "de-qa-0003" in dup[0].message
    assert [it.qa_id for it in result.valid] == ["de-qa-0003"]


def test_near_duplicate_is_only_a_warning(make_pair, topics):
    a = make_pair(1, question="Sự khác nhau giữa process và thread là gì?")
    b = make_pair(2, question="Su khac nhau giua process va thread la gi")
    result = validate_seed(items(a, b), topics)
    assert ("de-qa-0002", "near_duplicate") in rules_of(result, "warning")
    assert len(result.valid) == 2


def test_thin_topic_is_warning_then_error_when_strict(make_pair, topics):
    pairs = items(make_pair(1), make_pair(2))  # smp.data.sql-index co 0 cap
    assert ("coverage" in {i.rule for i in validate_seed(pairs, topics).issues if i.level == "warning"})
    strict = validate_seed(pairs, topics, strict=True)
    assert (None, "coverage") in rules_of(strict)
    assert (None, "total") in rules_of(strict)


def test_public_share_is_informational_only(make_pair, topics):
    synthetic = dict(source="self", license="CC-BY-4.0", synthetic=True, reviewed_by="DE", attribution=...)
    pairs = items(make_pair(1), make_pair(2, **synthetic), make_pair(3, **synthetic))
    result = validate_seed(pairs, topics, strict=True)
    assert result.report["public_pairs"] == 1
    assert "public_share" not in {i.rule for i in result.issues}  # FR-003 bo nguong (2026-10-19)


def crawled(pair):
    return SeedItem(data=pair, file="devi-java.json", index=0, dataset=CRAWLED_DATASET)


def test_crawled_pair_needs_no_license_or_reviewer(make_pair, topics):
    pair = make_pair(1, qa_id="cr-devi-java-0a1b2c3d", license="unknown", reviewed_by=..., source="https://github.com/x/y/blob/HEAD/README.md")
    result = validate_seed([crawled(pair)], topics)
    assert result.errors == [] and result.valid[0].dataset == CRAWLED_DATASET


@pytest.mark.parametrize(
    "overrides, rule",
    [({"qa_id": "de-qa-0001"}, "qa_id"), ({"source": "self"}, "provenance"), ({"attribution": ...}, "provenance"), ({"synthetic": True}, "provenance")],
)
def test_crawled_pair_still_needs_source_and_attribution(make_pair, topics, overrides, rule):
    pair = make_pair(1, **{"qa_id": "cr-devi-java-0a1b2c3d", "license": "unknown", **overrides})
    assert rule in {i.rule for i in validate_seed([crawled(pair)], topics).errors}


def test_report_has_per_source_and_per_topic_counts(make_pair, topics):
    synthetic = dict(source="self", license="CC-BY-4.0", synthetic=True, attribution=...)
    pairs = items(
        make_pair(1),
        make_pair(2, source="https://github.com/sudheerj/reactjs-interview-questions/blob/master/README.md"),
        make_pair(3, source="https://react.dev/learn/synchronizing-with-effects", license="CC-BY-4.0"),
        make_pair(4, topic_id="smp.data.sql-index", **synthetic),
    )
    report = validate_seed(pairs, topics).report
    assert report["by_source"] == {
        "DevLoversTeam/nodejs-interview-questions": 1,
        "react.dev": 1,
        "self": 1,
        "sudheerj/reactjs-interview-questions": 1,
    }
    assert report["by_topic"] == {"smp.core.event-loop": 3, "smp.data.sql-index": 1}


def test_loader_merges_files_in_name_order_and_reports_bad_json(tmp_path, make_pair):
    (tmp_path / "b.json").write_text(json.dumps([make_pair(2)]), encoding="utf-8")
    (tmp_path / "a.json").write_text(json.dumps([make_pair(1)]), encoding="utf-8")
    loaded = load_seed_items([(tmp_path, CURATED_DATASET), (tmp_path / "missing", CRAWLED_DATASET)])
    assert [it.qa_id for it in loaded] == ["de-qa-0001", "de-qa-0002"]
    (tmp_path / "c.json").write_text("[{", encoding="utf-8")
    with pytest.raises(SeedError, match="c.json"):
        load_seed_items([(tmp_path, CURATED_DATASET)])
    with pytest.raises(SeedError, match="khong co cap"):
        load_seed_items([(tmp_path / "missing", CURATED_DATASET)])
