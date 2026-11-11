"""Bo held-out Evaluator (docs 09 muc 10.2): cau hoi moi, khong trung golden chinh, phieu cham an muc chat luong."""
import csv
from collections import Counter

from evals.label_sheet import GOLDEN, HOLDOUT, SETS, blind_id, export_sheet, load_golden, needs_label
from evals.run_evaluator import to_input

HELD = load_golden(HOLDOUT)
MAIN = load_golden(GOLDEN)


def test_holdout_shape():
    ids = [s["id"] for s in HELD]
    assert len(ids) == len(set(ids)) and sum(needs_label(s) for s in HELD) >= 20
    quality = [s for s in HELD if s["intended_tier"]]
    assert all(n == 3 for n in Counter(s["qid"] for s in quality).values())
    assert {s["level"] for s in quality} == {"fresher", "junior", "middle", "senior"}
    assert {s["phase"] for s in HELD} == {"technical", "scenario"}
    adv = [s for s in HELD if s["adversarial"]]
    assert {"english", "no_diacritics", "keyword_stuffing", "confident_wrong", "rambling",
            "correct_but_short"} <= {s["adversarial"] for s in adv}
    assert sum(s["expect"].get("answer_type") == "manipulation" for s in adv) >= 2
    for s in HELD:
        assert 3 <= len(s["topic"]["key_points"]) <= 6 and s["answer"].strip()
        to_input(s)


def test_holdout_does_not_reuse_main_golden():
    # held-out chi co gia tri khi prompt chua tung thay cau hoi nay
    assert not {s["id"] for s in HELD} & {s["id"] for s in MAIN}
    assert not {s["qid"] for s in HELD} & {s["qid"] for s in MAIN}
    assert not {s["question"] for s in HELD} & {s["question"] for s in MAIN}
    assert not {s["topic"]["title"] for s in HELD} & {s["topic"]["title"] for s in MAIN}
    assert not {blind_id(s["id"]) for s in HELD} & {blind_id(s["id"]) for s in MAIN}


def test_holdout_labels_live_apart_from_main_labels():
    assert SETS["holdout"][0] == HOLDOUT and SETS["holdout"][1] != SETS["main"][1]


def test_holdout_sheet_hides_tier_and_skips_injections(tmp_path):
    sheet = tmp_path / "holdout.csv"
    export_sheet(HELD, sheet)
    rows = list(csv.DictReader(sheet.open(encoding="utf-8")))
    assert len(rows) == sum(needs_label(s) for s in HELD)
    assert all(r["id"].startswith("s") and "-" not in r["id"] for r in rows)
    assert not any(r["answer"] == s["answer"] for r in rows for s in HELD if not needs_label(s))
