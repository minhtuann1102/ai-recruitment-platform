"""Golden set Evaluator dung dinh dang (design 09 muc 10.2), chi so dung, phieu gan nhan, summarize."""
import csv
from collections import Counter

import pytest

from evals.evaluator_metrics import agreement, consensus, consistency, ordering, quadratic_kappa
from evals.label_sheet import blind_id, export_sheet, load_golden, needs_label, parse_sheet
from evals.run_evaluator import summarize, to_input

SAMPLES = load_golden()
B = {"technical_accuracy": 3, "completeness": 2, "extensibility": 2, "relevance": 3, "answer_type": "answered"}


def test_golden_set_shape():
    ids = [s["id"] for s in SAMPLES]
    assert len(ids) == len(set(ids)) and len(SAMPLES) >= 40
    quality = [s for s in SAMPLES if s["intended_tier"]]
    by_q = Counter(s["qid"] for s in quality)
    assert all(n == 3 for n in by_q.values()) and len(by_q) >= 12
    assert {s["intended_tier"] for s in quality} == {"strong", "medium", "weak"}
    assert {s["level"] for s in quality} == {"fresher", "junior", "middle", "senior"}
    adv = [s for s in SAMPLES if s["adversarial"]]
    assert len(adv) >= 10 and len({s["adversarial"] for s in adv}) >= 8
    assert sum(s["expect"].get("answer_type") == "manipulation" for s in adv) >= 3
    for s in SAMPLES:
        assert 3 <= len(s["topic"]["key_points"]) <= 6 and s["answer"].strip()
        to_input(s)  # dung duoc lam dau vao Evaluator


def test_consensus_rules():
    other = {**B, "completeness": 3}
    far = {**B, "technical_accuracy": 1}
    assert consensus(B, other)[0]["completeness"] == 2.5 and consensus(B, other)[1] == "agreed"
    assert consensus(B, far) == (None, "needs_adjudication")
    assert consensus(B, far, final=B) == (B, "final")
    assert consensus(B, None)[1] == "single" and consensus(None, None) == (None, "unlabeled")
    assert consensus(B, {**B, "answer_type": "partial"})[0]["answer_type"] is None


def test_agreement_kappa_consistency_ordering():
    stats = agreement([(3, 3), (4, 2), (2, 2.5), (0, 1)])
    assert stats == {"n": 4, "within1": 0.75, "mae": 0.875, "leniency_bias": 0.125}
    assert agreement([])["within1"] is None
    assert quadratic_kappa([0, 1, 2, 3, 4], [0, 1, 2, 3, 4]) == 1.0
    assert quadratic_kappa([0, 4, 0, 4], [4, 0, 4, 0]) < 0
    runs = {"x": [{c: 2 for c in B if c != "answer_type"}, {c: 2 for c in B if c != "answer_type"}]}
    assert consistency(runs) == 0.0
    tiers = {"a": ("q", "strong"), "b": ("q", "medium"), "c": ("q", "weak"), "d": ("r", "strong")}
    assert ordering({"a": 8, "b": 5, "c": 2, "d": 1}, tiers) == 1.0
    assert ordering({"a": 5, "b": 5, "c": 2}, tiers) == 0.0


def test_label_sheet_is_blind_and_roundtrips(tmp_path):
    sheet = tmp_path / "sheet.csv"
    export_sheet(SAMPLES, sheet)
    rows = list(csv.DictReader(sheet.open(encoding="utf-8")))
    assert len(rows) == sum(needs_label(s) for s in SAMPLES) < len(SAMPLES)
    assert "intended_tier" not in rows[0] and "adversarial" not in rows[0]
    assert all(r["id"].startswith("s") and "-" not in r["id"] for r in rows)  # id mo, khong lo muc chat luong
    rows[0].update(technical_accuracy="3", completeness="2", extensibility="1", relevance="4", answer_type="partial")
    with sheet.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    sheet.write_text("\ufeff" + sheet.read_text(encoding="utf-8"), encoding="utf-8")  # BOM nhu Excel
    labels = parse_sheet(sheet, {s["id"] for s in SAMPLES})
    real_id = next(s["id"] for s in SAMPLES if blind_id(s["id"]) == rows[0]["id"])
    assert labels == {real_id: {"technical_accuracy": 3, "completeness": 2, "extensibility": 1,
                                      "relevance": 4, "answer_type": "partial"}}
    rows[1].update(technical_accuracy="7", completeness="2", extensibility="1", relevance="4", answer_type="answered")
    with sheet.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError, match=rows[1]["id"]):
        parse_sheet(sheet, {s["id"] for s in SAMPLES})


def test_summarize_without_and_with_labels():
    samples = [s for s in SAMPLES if s["qid"] == "q01" and s["intended_tier"]] + \
              [s for s in SAMPLES if s["id"] == "a01-injection-direct"]
    score = {"q01-strong": 3, "q01-medium": 2, "q01-weak": 1, "a01-injection-direct": 0}
    results = {s["id"]: [{**{c: score[s["id"]] for c in B if c != "answer_type"},
                          "answer_type": "manipulation" if s["adversarial"] else "answered",
                          "turn_score_10": score[s["id"]] * 2.5, "degraded": False, "llm": not s["adversarial"],
                          "quotes": 2, "valid_quotes": 1}]
               for s in samples}
    summary = summarize(samples, results, {})
    assert summary["agreement"]["n"] == 0 and summary["ordering"] == 1.0
    assert summary["manipulation_caught"] == 1.0 and summary["evidence_valid"] == 0.5
    labels = {"rater_a": {"q01-strong": B}, "rater_b": {"q01-strong": B}}
    summary = summarize(samples, results, labels)
    assert summary["agreement"] == {"n": 4, "within1": 1.0, "mae": 0.5, "leniency_bias": 0.5}
    assert summary["label_status"] == {"agreed": 1, "unlabeled": 3} and summary["answer_type_accuracy"] == 1.0
    assert summary["manipulation_caught_by_llm"] is None  # a01 bi regex chan, khong toi LLM
    single = summarize(samples, results, {"rater_a": {"q01-strong": B}})
    assert single["agreement"]["n"] == 0 and single["label_status"]["single"] == 1
    results["q01-weak"][0]["degraded"] = True
    assert summarize(samples, results, {})["ordering"] is None  # lan degraded bi loai
