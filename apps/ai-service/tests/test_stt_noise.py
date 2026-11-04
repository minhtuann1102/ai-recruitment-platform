"""Mau golden nhieu STT (NFR-AI-QUAL17): khop voi mau sach, ke thua nhan, chi so chenh diem. Khong goi LLM."""
import json
import re

from evals.label_sheet import LABELS_DIR, load_golden
from evals.run_evaluator import to_input
from evals.stt_noise import inherit_labels, plain_samples, spoken_plain, stt_samples, stt_summary

CLEAN = load_golden()
NOISY = stt_samples(CLEAN)


def test_noisy_samples_pair_with_labelled_clean_samples():
    final = json.loads((LABELS_DIR / "final.json").read_text(encoding="utf-8"))
    by_id = {s["id"]: s for s in CLEAN}
    assert len(NOISY) >= 12 and len({s["id"] for s in NOISY}) == len(NOISY)
    assert {by_id[s["stt_of"]]["intended_tier"] for s in NOISY} == {"strong", "medium", "weak"}
    for s in NOISY:
        clean = by_id[s["stt_of"]]
        assert s["stt_of"] in final and s["answer"] != clean["answer"] and s["noise"]
        assert s["question"] == clean["question"] and s["qid"] == f"{clean['qid']}-stt"
        to_input(s)


def test_limit_without_clean_sample_drops_noisy_row():
    assert stt_samples(CLEAN[:3]) == [s for s in NOISY if s["stt_of"] in {c["id"] for c in CLEAN[:3]}]


def test_noisy_sample_inherits_clean_label():
    label = {"technical_accuracy": 3, "completeness": 2, "extensibility": 2, "relevance": 3}
    noisy = [{"id": "q01-strong-stt", "stt_of": "q01-strong"}]
    out = inherit_labels({"final": {"q01-strong": label}}, noisy)
    assert out["final"]["q01-strong-stt"] == label and out["final"]["q01-strong"] == label


def test_summary_compares_noisy_and_clean_means_and_skips_degraded():
    run = lambda score, kind="answered", degraded=False: {"turn_score_10": score, "answer_type": kind,  # noqa: E731
                                                          "degraded": degraded}
    noisy = [{"id": "a-stt", "stt_of": "a"}, {"id": "b-stt", "stt_of": "b"}, {"id": "c-stt", "stt_of": "c"}]
    results = {"a": [run(6), run(8)], "a-stt": [run(6.5), run(0, degraded=True)],
               "b": [run(5)], "b-stt": [run(2.5, "dont_know")],
               "c": [run(4, degraded=True)], "c-stt": [run(4)]}  # c: ban sach chi co lan degraded -> bo cap
    out = stt_summary(noisy, results)
    assert out == {"pairs": 2, "mean_diff": -1.5, "max_abs_diff": 2.5, "within_1": 0.5, "same_answer_type": 0.5}
    assert stt_summary(noisy, {}) == {"pairs": 0}


def test_plain_variant_keeps_terms_and_drops_punctuation_only():
    out = spoken_plain("Đọc thì GET key. Không truyền [] thì chạy một lần; xong.")
    assert out == "à đọc thì get key ừm không truyền mảng rỗng thì chạy một lần xong"
    plain = plain_samples(CLEAN)
    assert [s["stt_of"] for s in plain] == [s["stt_of"] for s in NOISY]
    assert all(s["id"].endswith("-plain") and not re.search(r"[.,;:!?]", s["answer"]) for s in plain)
