"""Golden co tai lieu (Phase 05): dinh dang mau, nhan quan sat tu output tho, chi so precision / recall."""
from collections import Counter

from evals.label_sheet import load_golden
from evals.run_evaluator_sourced import GOLDEN, observed, summarize, to_input

SAMPLES = load_golden(GOLDEN)


def test_golden_shape_and_mix():
    assert len(SAMPLES) == 47 and len({s["id"] for s in SAMPLES}) == 47
    assert Counter(s["expect"]["support"] for s in SAMPLES) == {"supported": 25, "contradicted": 10, "no_source": 12}
    contra = [s for s in SAMPLES if s["expect"]["support"] == "contradicted"]
    assert sum(bool(s["reference_answer"]) for s in contra) == 4  # 4 qua R, 6 chi qua S
    # cau dung di kem R: do chieu nguoc lai, R bac nham cau dung
    assert sum(bool(s["reference_answer"]) and s["expect"]["support"] != "contradicted" for s in SAMPLES) == 8
    for s in SAMPLES:
        assert s["documents"] or s["reference_answer"]
        inp = to_input(s)
        assert inp.topic.reference_snippets == s["documents"] and inp.reference_answer == s["reference_answer"]
        assert bool(inp.reference_source) == bool(s["reference_answer"])


def test_long_s_cohort_matches_real_turn_shape():
    """Nhom nay ton tai de lo loi doc tai lieu dai: mat hinh dang nay thi recall lai lac quan nhu golden cu."""
    long_s = [s for s in SAMPLES if s.get("cohort") == "long_s"]
    assert Counter(s["expect"]["support"] for s in long_s) == {"supported": 8, "contradicted": 3, "no_source": 4}
    # luot that khong R la follow_up / hint
    assert all(not s["reference_answer"] and s["turn_kind"] != "main" for s in long_s)
    assert all(len(to_input(s).topic_turns) == len(s["topic_turns"]) >= 1 for s in long_s)  # follow_up luon co lich su
    assert all(2 <= len(s["documents"]) <= 5 and min(map(len, s["documents"])) >= 600 for s in long_s)
    assert max(len(d) for s in long_s for d in s["documents"]) >= 1500  # co chunk o duoi phan bo that (p90 ~1800)


def test_observed_label_prefers_contradicted_and_ignores_invalid_ids():
    assert observed([{"support": "supported", "source_ids": ["S1"]},
                     {"support": "contradicted", "source_ids": ["s1"]}], ["S1"]) == "contradicted"
    assert observed([{"support": "supported", "source_ids": ["S9"]}], ["S1"]) == "no_source"
    assert observed([{"support": "supported", "source_ids": []}], ["S1"]) == "no_source"
    assert observed([], ["S1"]) == "no_source"


def test_summarize_precision_recall_and_contradicted_by_doc():
    def run(obs, acc=2, mis=0, degraded=False, blocked=False):
        return {"observed": obs, "degraded": degraded, "invalid_ids": 1, "technical_accuracy": acc,
                "misconceptions": mis, "r_blocked": blocked}

    results = {s["id"]: [run(s["expect"]["support"])] for s in SAMPLES}
    g11, g14, g17, g25, g28 = ("g11-con-R-hashmap", "g14-con-S-gil", "g17-nos-nplus1", "g25-nos-R-threadstate",
                               "g28-con-RS-jwt")
    results[g14] = [run("supported", acc=3)]  # S khong bac bo duoc
    results[g17] = [run("supported")]  # tai lieu khong lien quan ma van supported
    results[g11].append(run("no_source", degraded=True))  # lan degraded bi loai
    results[g25] = [run("contradicted", acc=1, mis=1, blocked=True)]  # R bac nham cau dung
    results[g28] = [run("contradicted", acc=1, mis=1, blocked=True)]
    out = summarize(SAMPLES, results)
    assert out["degraded_runs_excluded"] == 1 and out["invalid_source_ids"] == 48
    assert out["per_label"]["contradicted"] == {"precision": round(9 / 10, 3), "recall": round(9 / 10, 3), "n": 10}
    assert out["per_label"]["supported"]["precision"] == round(25 / 27, 3)
    assert out["per_label_by_cohort"]["short"]["contradicted"]["n"] == 7
    assert out["per_label_by_cohort"]["long_s"]["supported"] == {"precision": 1.0, "recall": 1.0, "n": 8}
    assert out["r_blocked_wrong_answers"] == 0.25 and out["r_blocked_correct_answers"] == 0.125
    assert out["correct_with_r_with_misconception"] == 0.125
    assert out["contradicted_recall_by_doc"] == {"R": 1.0, "S": round(5 / 6, 3)}
    assert out["confusion_expected_observed"]["no_source->supported"] == 1
    assert out["by_sample"][g14] == {"supported": 1}
