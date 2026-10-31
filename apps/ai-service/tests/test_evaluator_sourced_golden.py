"""Golden co tai lieu (Phase 05): dinh dang mau, nhan quan sat tu output tho, chi so precision / recall."""
from collections import Counter

from evals.label_sheet import load_golden
from evals.run_evaluator_sourced import GOLDEN, observed, summarize, to_input

SAMPLES = load_golden(GOLDEN)


def test_golden_shape_and_mix():
    assert len(SAMPLES) == 20 and len({s["id"] for s in SAMPLES}) == 20
    assert Counter(s["expect"]["support"] for s in SAMPLES) == {"supported": 10, "contradicted": 6, "no_source": 4}
    contra = [s for s in SAMPLES if s["expect"]["support"] == "contradicted"]
    assert sum(bool(s["reference_answer"]) for s in contra) == 3  # 3 qua R, 3 chi qua S
    for s in SAMPLES:
        assert s["documents"] or s["reference_answer"]
        inp = to_input(s)
        assert inp.topic.reference_snippets == s["documents"] and inp.reference_answer == s["reference_answer"]


def test_observed_label_prefers_contradicted_and_ignores_invalid_ids():
    assert observed([{"support": "supported", "source_ids": ["S1"]},
                     {"support": "contradicted", "source_ids": ["s1"]}], ["S1"]) == "contradicted"
    assert observed([{"support": "supported", "source_ids": ["S9"]}], ["S1"]) == "no_source"
    assert observed([{"support": "supported", "source_ids": []}], ["S1"]) == "no_source"
    assert observed([], ["S1"]) == "no_source"


def test_summarize_precision_recall_and_contradicted_by_doc():
    def run(obs, acc=2, mis=0, degraded=False):
        return {"observed": obs, "degraded": degraded, "invalid_ids": 1, "technical_accuracy": acc, "misconceptions": mis}

    results = {s["id"]: [run(s["expect"]["support"])] for s in SAMPLES}
    g11, g14, g17 = "g11-con-R-hashmap", "g14-con-S-gil", "g17-nos-nplus1"
    results[g14] = [run("supported", acc=3)]  # S khong bac bo duoc
    results[g17] = [run("supported")]  # tai lieu khong lien quan ma van supported
    results[g11].append(run("no_source", degraded=True))  # lan degraded bi loai
    out = summarize(SAMPLES, results)
    assert out["degraded_runs_excluded"] == 1 and out["invalid_source_ids"] == 21
    assert out["per_label"]["contradicted"] == {"precision": 1.0, "recall": round(5 / 6, 3), "n": 6}
    assert out["per_label"]["supported"]["precision"] == round(10 / 12, 3)
    assert out["contradicted_recall_by_doc"] == {"R": 1.0, "S": round(2 / 3, 3)}
    assert out["confusion_expected_observed"]["no_source->supported"] == 1
    assert out["by_sample"][g14] == {"supported": 1}
