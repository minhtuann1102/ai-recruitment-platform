"""Ap ket qua Phase B (FR-028): quyet dinh tung cap, ap khi load, giu nhan goc, bo kem ly do, quet golden."""
from pipeline.qa_relabel_decisions import apply_decisions, build_decisions, decide, golden_qa_ids
from pipeline.qa_seed_loader import SeedItem
from pipeline.settings import CRAWLED_DATASET, CURATED_DATASET

QA = "cr-devi-node-0a1b2c3d"


def judgment(**overrides):
    row = {"qa_id": QA, "model": "gpt-6-luna", "topic_before": "t.current", "difficulty_before": "easy",
           "topic_fit": "main", "best_topic_id": "t.current", "difficulty": "medium", "interview_style": True,
           "reason": "ok"}
    row.update(overrides)
    return row


def test_main_keeps_topic_and_takes_model_difficulty():
    assert decide(QA, judgment(), None, None, False) == {"difficulty": "medium", "interview_style": True}


def test_off_or_related_with_other_topic_moves():
    assert decide(QA, judgment(topic_fit="off", best_topic_id="t.other"), None, None, False)["topic_id"] == "t.other"
    assert decide(QA, judgment(topic_fit="related", best_topic_id="t.other"), None, None, False)["topic_id"] == "t.other"
    assert "topic_id" not in decide(QA, judgment(topic_fit="related", best_topic_id="none"), None, None, False)


def test_off_none_drops_unless_golden():
    assert decide(QA, judgment(topic_fit="off", best_topic_id="none"), None, None, False)["drop"].startswith("gpt-6-luna:")
    kept = decide(QA, judgment(topic_fit="off", best_topic_id="none"), None, None, True)
    assert kept["golden_kept"].startswith("gpt-6-luna:") and "drop" not in kept


def test_golden_protects_against_human_drops_too():
    assert "golden_kept" in decide(QA, None, None, "nhan sai", True)
    assert "golden_kept" in decide(QA, None, {"quyet_dinh": "drop", "ly_do": "x"}, None, True)
    kept, gone = apply_decisions([SeedItem(data={"qa_id": QA, "topic_id": "t"}, file="a", index=0,
                                           dataset=CRAWLED_DATASET)], {QA: {"golden_kept": "DE: x"}})
    assert gone == [] and kept[0].data == {"qa_id": QA, "topic_id": "t"}


def test_review_and_de_take_priority():
    review = {"quyet_dinh": "fix", "do_kho_de_xuat": "easy"}
    assert decide(QA, judgment(difficulty="hard"), review, None, False)["difficulty"] == "easy"
    assert decide(QA, judgment(), {"quyet_dinh": "drop", "ly_do": "sai kien thuc"}, None, False)["drop"].startswith("duyet")
    assert decide(QA, judgment(), None, "nhan sai", False) == {"drop": "DE: nhan sai"}


def test_build_skips_empty_decisions():
    decisions = build_decisions({}, {QA: {"quyet_dinh": "ok", "do_kho_de_xuat": ""}}, {}, set())
    assert decisions == {}


def test_apply_changes_only_crawled_and_keeps_originals():
    crawled = SeedItem(data={"qa_id": QA, "topic_id": "t.current", "difficulty": "easy"}, file="a.json", index=0,
                       dataset=CRAWLED_DATASET)
    dropped = SeedItem(data={"qa_id": "cr-devi-node-11111111", "topic_id": "t.current", "difficulty": "easy"},
                       file="a.json", index=1, dataset=CRAWLED_DATASET)
    curated = SeedItem(data={"qa_id": "de-qa-0001", "topic_id": "t.current", "difficulty": "hard"}, file="s.json",
                       index=0, dataset=CURATED_DATASET)
    decisions = {QA: {"topic_id": "t.other", "difficulty": "medium", "interview_style": False},
                 "cr-devi-node-11111111": {"drop": "DE: sai"}, "de-qa-0001": {"drop": "khong ap cho curated"}}
    kept, gone = apply_decisions([crawled, dropped, curated], decisions)
    assert [k.qa_id for k in kept] == [QA, "de-qa-0001"] and gone == [("cr-devi-node-11111111", "DE: sai")]
    data = kept[0].data
    assert data["topic_id"] == "t.other" and data["topic_id_enriched"] == "t.current"
    assert data["difficulty"] == "medium" and data["difficulty_enriched"] == "easy" and data["interview_style"] is False
    assert crawled.data["topic_id"] == "t.current"  # khong sua ban goc trong bo nho


def test_golden_scan_finds_crawled_ids(tmp_path):
    (tmp_path / "g.json").write_text('{"expected_qa_ids": ["cr-lz-python-basics-8979143a", "de-qa-0001"]}',
                                     encoding="utf-8")
    assert golden_qa_ids([tmp_path / "g.json", tmp_path / "missing.json"]) == {"cr-lz-python-basics-8979143a"}
