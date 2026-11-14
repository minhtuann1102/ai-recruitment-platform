"""`simulate --runs N`: sid rieng moi run, stdev gop + CI, end_reasons, persona skewed co JD/CV (phase 01 agentic).
Agent mock + simulator quy tac: chi kiem harness va cong thuc, khong phai so do chat luong."""
import asyncio
import math

from evals.personas import all_personas, skewed_personas
from evals.sim_metrics import end_reasons
from evals.sim_runs import bootstrap_ci, pooled_stdev, pooled_stdev_report, strong_weak_gap, summarize_runs
from evals.simulate import known_personas, run_all, summarize
from evals.simulate_session import session_id
from evals.simulator import RuleSimulator
from evals.turn_source_recorder import attach_documents
from evals.cost_latency import load_pricing


def sess(score, reason="plan_complete", persona="p"):
    return {"persona": persona, "turns": [], "report": {"overall": {"score": score},
                                                          "session": {"end_reason": reason}}}


def test_session_id_old_format_without_run():
    assert session_id("junior-java-strong") == "sim-junior-java-strong"
    assert session_id("junior-java-strong", 2) == "sim-junior-java-strong-r2"


def test_attach_documents_keeps_runs_apart():
    seen = {("sim-a-r1", 1): [{"id": "S1", "text": "one"}], ("sim-a-r2", 1): [{"id": "S1", "text": "two"}]}
    r1, r2 = {"a": {"turns": [{"turn_number": 1}]}}, {"a": {"turns": [{"turn_number": 1}]}}
    attach_documents(r1, seen, 1)
    attach_documents(r2, seen, 2)
    assert r1["a"]["turns"][0]["documents"][0]["text"] == "one"
    assert r2["a"]["turns"][0]["documents"][0]["text"] == "two"
    old = {"a": {"turns": [{"turn_number": 1}]}}
    attach_documents(old, {("sim-a", 1): []})  # khong run: sid cu
    assert old["a"]["turns"][0]["documents"] == []


def test_pooled_stdev_formula():
    runs = [{"a": sess(6), "b": sess(5), "c": sess(7)}, {"a": sess(8), "b": sess(5)}, {"b": sess(5)}]
    # a: [6,8] ss=2 df=1; b: [5,5,5] ss=0 df=2; c: 1 diem khong co df
    assert pooled_stdev(runs) == math.sqrt(2 / 3)
    assert pooled_stdev([{"a": sess(6)}]) is None
    assert pooled_stdev([{"a": {"report": None, "turns": []}}, {"a": sess(None)}]) is None  # run hong bi bo


def test_bootstrap_ci_deterministic_and_brackets_value():
    groups = [[6.0, 8.0], [5.0, 5.0], [7.0, 6.0], [4.0, 6.0]]
    report = pooled_stdev_report([{f"p{i}": sess(g[0]) for i, g in enumerate(groups)},
                                  {f"p{i}": sess(g[1]) for i, g in enumerate(groups)}])
    lo, hi = report["ci95"]
    assert lo <= report["value"] <= hi and report["personas"] == 4 and report["df"] == 4
    assert report == pooled_stdev_report([{f"p{i}": sess(g[0]) for i, g in enumerate(groups)},
                                          {f"p{i}": sess(g[1]) for i, g in enumerate(groups)}])
    assert bootstrap_ci([], lambda xs: 1.0) is None


def test_strong_weak_gap_averages_runs_and_skips_adversarial():
    ps = all_personas()
    runs = [{"junior-java-strong": sess(9), "junior-java-weak": sess(3), "junior-java-average": sess(6)},
            {"junior-java-strong": sess(8), "junior-java-weak": sess(4)}]
    gap = strong_weak_gap(runs, ps)
    assert gap["mean"] == 5.0 and gap["groups"] == 1 and gap["ci95"] == (5.0, 5.0)
    summary = summarize_runs(runs, ps)
    assert summary["runs"] == 2 and summary["strong_weak_gap"]["mean"] == 5.0


def test_end_reasons_distribution_and_correct_rate():
    ps = known_personas()
    sessions = {"junior-java-strong": sess(9, "plan_complete"), "junior-java-average": sess(6, "low_performance"),
                "junior-java-weak": sess(3, "low_performance"),
                "junior-java-average+rambling": sess(5, "low_performance"),  # adversarial: bo qua
                "junior-java-skewed": sess(5, "time_up")}  # skewed: bo qua
    out = end_reasons(sessions, ps)
    assert out["by_quality"] == {"average": {"low_performance": 1}, "strong": {"plan_complete": 1},
                                 "weak": {"low_performance": 1}}
    assert out["correct_reason"] == round(2 / 3, 3)  # average + low_performance la sai


def test_runs_two_sessions_same_persona_in_process_and_skewed_requirements():
    ids = ["junior-java-strong", "junior-java-skewed"]
    by_run = [asyncio.run(run_all(ids, RuleSimulator(), run=i)) for i in (1, 2)]
    assert all(set(s) == set(ids) for s in by_run)
    ps = known_personas()
    skewed = by_run[0]["junior-java-skewed"]["report"]
    assert skewed["requirements"]["total"] == 4 and skewed["requirements"]["items"][0]["kind"] == "must"
    assert "requirements" not in by_run[0]["junior-java-strong"]["report"] or \
        by_run[0]["junior-java-strong"]["report"]["requirements"] is None
    summary = summarize(by_run[0], ps, load_pricing())  # skewed khong lam hong discrimination / end_reasons
    assert summary["discrimination"]["groups"] == 0 and "end_reasons" in summary
    assert set(skewed_personas()) == {"junior-java-skewed", "junior-nodejs-skewed"}
    assert len(all_personas()) == 29  # ma tran khong doi


def test_skewed_persona_knowledge_split():
    p = skewed_personas()["junior-java-skewed"]
    assert p.knowledge("java.data.sql-index-tuning") == "none" and p.knowledge("java.spring.transaction") == "well"
    assert p.knowledge("not-in-catalog") == "partial"
    must = {t for r in p.jd_profile["requirements"] if r["kind"] == "must" for t in r["topic_ids"]}
    assert must & set(p.does_not_know) and must & set(p.knows_well)
