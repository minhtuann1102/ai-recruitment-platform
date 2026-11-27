"""Phan thuan cua experiment embedding 017 (pipeline/match_embedding_*.py): khong mang, khong torch, khong ai-service.

Vector gia nho de kiem: xep hang cosine thuan (hoa -> job_id, khong kep 0), metric theo CV khop quality_summary, bootstrap ghep
theo CV (CI, tat dinh theo seed), cache vector, tien to e5, dung sai cua cong tai lap, va bao cao render duoc tu ket qua mau.
"""
import numpy as np
import pytest

from pipeline.match_embedding_gate import PUBLISHED_BY_LANGUAGE, PUBLISHED_OVERALL, TOLERANCE, compare_published
from pipeline.match_embedding_models import MODELS, PASSAGE, QUERY, VectorCache
from pipeline.match_embedding_report import render_markdown
from pipeline.match_embedding_stats import (cosine_by_label_group, cosine_scale, mean_scores, paired_bootstrap, per_cv_scores,
                                            raw_cosine_items, top_k_share, verdict)
from pipeline.match_eval_metrics import quality_summary

JOB_IDS = ["j-a", "j-b", "j-c", "j-d"]


def _unit(*xs):
    v = np.array(xs, dtype=float)
    return v / np.linalg.norm(v)


# ---------- xep hang cosine thuan ----------

def test_raw_cosine_ranks_by_cosine_then_job_id_on_ties():
    cv = _unit(1, 0)
    matrix = np.array([_unit(1, 1), _unit(1, 0), _unit(1, 1), _unit(0, 1)])  # j-a, j-c cung cosine
    items = raw_cosine_items(cv, matrix, JOB_IDS, JOB_IDS)
    from pipeline.match_eval_metrics import rank_items
    assert [i["job_id"] for i in rank_items(items, "cosine")] == ["j-b", "j-a", "j-c", "j-d"]


def test_raw_cosine_is_not_clipped_and_respects_allowed_subset():
    cv = _unit(1, 0)
    matrix = np.array([_unit(-1, 0.2), _unit(0, 1), _unit(1, 0), _unit(1, 1)])
    items = raw_cosine_items(cv, matrix, JOB_IDS, ["j-a", "j-c"])
    assert {i["job_id"] for i in items} == {"j-a", "j-c"}
    assert next(i for i in items if i["job_id"] == "j-a")["components"]["cosine"] < 0  # khong kep ve 0


def test_raw_cosine_is_scale_invariant():
    cv, matrix = _unit(1, 2, 0.5), np.array([_unit(1, 0, 0), _unit(0, 1, 1), _unit(1, 1, 1), _unit(0, 0, 1)])
    base = raw_cosine_items(cv, matrix, JOB_IDS, JOB_IDS)
    scaled = raw_cosine_items(cv * 7.0, matrix * 3.0, JOB_IDS, JOB_IDS)
    assert [round(i["score"], 12) for i in base] == [round(i["score"], 12) for i in scaled]


# ---------- metric theo CV ----------

def _items(scores):
    return [{"job_id": j, "score": s, "components": {"cosine": s, "skill_match": 0.0, "level_fit": 0.0}} for j, s in scores.items()]


LABELS = {"cv1": {"j-a": 2, "j-b": 0, "j-c": 1, "j-d": 0}, "cv2": {"j-a": 0, "j-b": 0, "j-c": 0, "j-d": 0},
          "cv3": {"j-a": 1, "j-b": 2, "j-c": 0, "j-d": 0}}
ITEMS = {"cv1": _items({"j-a": 0.9, "j-b": 0.8, "j-c": 0.7, "j-d": 0.1}), "cv2": _items({"j-a": 0.9, "j-b": 0.8, "j-c": 0.7, "j-d": 0.1}),
         "cv3": _items({"j-a": 0.2, "j-b": 0.9, "j-c": 0.5, "j-d": 0.1})}


def test_per_cv_scores_matches_quality_summary_and_drops_cvs_without_relevant_jd():
    per_cv = per_cv_scores(ITEMS, LABELS, "cosine")
    assert set(per_cv) == {"cv1", "cv3"}  # cv2 khong co JD lien quan
    summary, ref = mean_scores(per_cv), quality_summary(ITEMS, LABELS, "cosine")
    assert summary["ndcg_at_5"] == pytest.approx(ref["ndcg_at_5"])
    assert summary["p_at_5"] == pytest.approx(ref["p_at_5"])
    assert summary["n_cv"] == ref["n_cv"] == 2


def test_per_cv_scores_language_subset_keeps_relative_order():
    keep = lambda j: j in ("j-b", "j-c")  # noqa: E731
    per_cv = per_cv_scores(ITEMS, LABELS, "cosine", keep)
    assert per_cv["cv1"][1] == 0.5  # mau so = min(5, so JD dang xet) = 2; chi j-c lien quan
    assert mean_scores(per_cv)["ndcg_at_5"] == pytest.approx(quality_summary(ITEMS, LABELS, "cosine", keep)["ndcg_at_5"])


# ---------- bootstrap ghep theo CV ----------

def test_bootstrap_all_positive_differences_excludes_zero():
    base = {f"cv{i}": 0.5 for i in range(24)}
    other = {c: v + 0.05 + 0.001 * n for n, (c, v) in enumerate(base.items())}
    ci = paired_bootstrap(base, other)
    assert ci["excludes_zero"] and ci["ci_lo"] > 0 and verdict(ci) == "better"
    assert (ci["wins"], ci["losses"], ci["ties"]) == (24, 0, 0)


def test_bootstrap_negative_differences_is_worse_and_mixed_is_equal():
    base = {f"cv{i}": 0.5 for i in range(24)}
    assert verdict(paired_bootstrap(base, {c: v - 0.1 for c, v in base.items()})) == "worse"
    mixed = {c: v + (0.1 if n % 2 else -0.1) for n, (c, v) in enumerate(base.items())}
    ci = paired_bootstrap(base, mixed)
    assert verdict(ci) == "equal" and ci["ci_lo"] < 0 < ci["ci_hi"]


def test_bootstrap_identical_inputs_give_zero_interval_and_equal():
    base = {f"cv{i}": 0.4 + 0.01 * i for i in range(10)}
    ci = paired_bootstrap(base, dict(base))
    assert (ci["ci_lo"], ci["ci_hi"], ci["mean_diff"]) == (0.0, 0.0, 0.0)
    assert not ci["excludes_zero"] and verdict(ci) == "equal" and ci["ties"] == 10


def test_bootstrap_is_deterministic_per_seed_and_uses_common_cvs_only():
    rng = np.random.default_rng(1)
    base = {f"cv{i}": float(rng.random()) for i in range(24)}
    other = {c: v + float(rng.normal(0, 0.1)) for c, v in base.items()}
    assert paired_bootstrap(base, other, n_boot=500, seed=7) == paired_bootstrap(base, other, n_boot=500, seed=7)
    assert paired_bootstrap(base, other, n_boot=500, seed=7) != paired_bootstrap(base, other, n_boot=500, seed=8)
    assert paired_bootstrap({**base, "extra": 1.0}, other, n_boot=50)["n_cv"] == 24
    with pytest.raises(ValueError):
        paired_bootstrap({"a": 1.0}, {"b": 1.0})


def test_bootstrap_mean_diff_is_inside_interval():
    base = {f"cv{i}": 0.5 for i in range(24)}
    other = {c: 0.5 + (0.2 if n < 9 else -0.04) for n, c in enumerate(base)}
    ci = paired_bootstrap(base, other)
    assert ci["ci_lo"] <= ci["mean_diff"] <= ci["ci_hi"]


# ---------- chan doan ngon ngu / thang cosine ----------

def test_language_share_and_label_group_means():
    groups = {"j-a": "same", "j-b": "cross", "j-c": "same", "j-d": "cross"}
    same = lambda j: groups[j] == "same"  # noqa: E731
    assert top_k_share({"cv1": ITEMS["cv1"]}, same, k=2) == 0.5  # top 2 = j-a (vi), j-b (en)
    table = cosine_by_label_group({"cv1": ITEMS["cv1"]}, LABELS, groups.get)
    assert table["2"]["same"] == pytest.approx(0.9) and table["1"]["same"] == pytest.approx(0.7)
    assert table["0"]["cross"] == pytest.approx(0.45) and table["2"]["cross"] is None


def test_cosine_scale_counts_negative_and_rounded_ties():
    items = {"cv1": _items({"j-a": -0.2, "j-b": 0.50001, "j-c": 0.50002, "j-d": 0.9})}
    scale = cosine_scale(items)
    assert scale["n_negative"] == 1 and scale["n_rounded_ties"] == 1 and scale["min"] == -0.2 and scale["n_pairs"] == 4


# ---------- model / cache ----------

def test_e5_uses_query_and_passage_prefixes_others_none():
    e5, bge = MODELS["st-e5"], MODELS["st-bge"]
    assert e5.final_text(QUERY, "cv") == "query: cv" and e5.final_text(PASSAGE, "jd") == "passage: jd"
    assert bge.final_text(QUERY, "cv") == "cv" and MODELS["oa-small"].final_text(PASSAGE, "jd") == "jd"
    assert MODELS["oa-large"].api_dimensions == 1536 and MODELS["oa-small"].api_dimensions is None


def test_vector_cache_roundtrip_and_revision_invalidation(tmp_path):
    cache = VectorCache("st-x", "rev1" * 4, 3, tmp_path)
    assert cache.get("hello") is None and not cache.covers(["hello"])
    cache.put("hello", [1.0, 2.0, 3.0])
    cache.save()
    again = VectorCache("st-x", "rev1" * 4, 3, tmp_path)
    assert again.get("hello").tolist() == [1.0, 2.0, 3.0] and again.covers(["hello"])
    assert VectorCache("st-x", "rev1" * 4, 4, tmp_path).get("hello") is None  # doi so chieu -> bo cache cu


# ---------- cong tai lap ----------

def _tables(delta=0.0, drop_cv=False):
    def row(pub):
        return {"p_at_5": pub[0] + delta, "ndcg_at_5": pub[1] + delta, "n_cv": pub[2] - (1 if drop_cv else 0)}
    return {"overall": {m: row(p) for m, p in PUBLISHED_OVERALL.items()},
            "by_language": {f"{m}/{g}": row(p) for (m, g), p in PUBLISHED_BY_LANGUAGE.items()}}


def test_gate_tolerance_is_plus_minus_005_and_requires_same_cv_count():
    assert compare_published(_tables(0.004))["overall_pass"]
    assert not compare_published(_tables(TOLERANCE + 0.001))["overall_pass"]
    assert not compare_published(_tables(0.0, drop_cv=True))["overall_pass"]
    assert [r["name"] for r in compare_published(_tables(), methods=("skill_match",))["overall"]] == ["skill_match"]


# ---------- bao cao ----------

def _model(model_id, ndcg, ops, vs=None):
    score = {"ndcg_at_5": ndcg, "p_at_5": 0.6, "n_cv": 24}
    out = {"model_id": model_id, "name": model_id, "dims": 8, "revision": "abc", "ops": ops,
           "primary_cosine_only": {"overall": score, "same": score, "cross": score},
           "secondary_full_score": {"overall": score, "same": score, "cross": score},
           "endpoint_style_cosine_only": score, "skill_only_baseline": score,
           "diagnostics": {"cosine_scale": {"mean": 0.5, "std": 0.1, "min": 0.1, "max": 0.9, "n_negative": 0, "n_rounded_ties": 0},
                           "cosine_by_label_group": {str(label): {"same": 0.6, "cross": 0.5} for label in (0, 1, 2)},
                           "vi_share_top5_cosine_only": 0.69, "vi_share_top5_full": 0.56, "vi_share_of_relevant_pairs": 0.55}}
    if vs:
        out["vs_oa_small"] = {k: {**vs, "verdict": verdict(vs)} for k in ("primary_cosine_only", "secondary_full_score")}
    return out


def test_report_renders_models_gate_and_decision_rule():
    lat = {"n": 72, "p50": 50.0, "p95": 80.0}
    st_ops = {"latency_ms": {"query": lat, "passage": lat}, "max_seq_length": 128, "load_s": 1.5, "peak_rss_mb": 900.0,
              "truncation": {"query": {"rate": 1.0, "mean_tokens": 300, "max_tokens": 400},
                             "passage": {"rate": 0.9, "mean_tokens": 280, "max_tokens": 390}},
              "cpu": {"other_pct": 5.0, "own_pct": 30.0}}
    ci = {"mean_diff": 0.05, "ci_lo": 0.01, "ci_hi": 0.09, "excludes_zero": True, "wins": 15, "losses": 5, "ties": 4}
    gate = {"published": compare_published(_tables()), "pair_check": {"filtered_pairs": 264, "labeled_pairs": 264, "equal": True},
            "index": {"db_role": "aie_reader", "n_rows": 356, "n_jobs": 356, "max_created_at": "2026-11-23", "embedding_model": "m",
                      "vector_mismatch": []},
            "pool_text_check": {"pool": 36, "text_differs_from_jd_normalized": [], "stored_hash_differs_from_stored_content": [],
                                "metadata_differs_from_jd_normalized": []},
            "jd_vector_fresh_vs_stored_cosine": {"min": 0.9999, "mean": 0.99999}, "with_fresh_jd_vectors": {"overall_pass": True},
            "bootstrap_sanity": {"full_vs_skill_match": ci, "full_vs_cosine": ci},
            "settings": {"as_of": "2026-11-01", "weights": {}, "max_level_gap": 1}}
    models = {"oa-small": _model("oa-small", 0.84, {"network_latency_ms_query": lat}), "st-x": _model("st-x", 0.89, st_ops, ci)}
    md = render_markdown({"gate": gate, "models": models, "failures": {"st-y": "boom"}})
    assert "Quality winners over oa-small: **st-x**" in md and "BETTER" in md and "st-y: boom" in md and "PASS" in md


# ---------- chan doan lech so voi lan chay 017 goc ----------

def test_drift_vs_original_run_finds_changed_cv_and_patched_metrics(tmp_path):
    import json
    from pipeline.match_embedding_gate_drift import drift_vs_original_run

    def rows(scores):
        return [{"job_id": j, "score": s, "cosine": s, "skill_match": 0.0} for j, s in scores.items()]

    run = tmp_path / "run.json"
    run.write_text(json.dumps({"rankings": {"cv1": rows({"j-a": 0.9, "j-b": 0.8, "j-c": 0.7, "j-d": 0.6, "j-e": 0.5, "j-f": 0.4}),
                                            "cv3": rows({"j-a": 0.9, "j-b": 0.8})}}), encoding="utf-8")
    mine = {"cv1": _items({"j-a": 0.9, "j-b": 0.8, "j-c": 0.7, "j-d": 0.6, "j-e": 0.4001, "j-f": 0.4002}),  # hang 5 / 6 doi cho
            "cv3": _items({"j-a": 0.9, "j-b": 0.8})}
    labels = {"cv1": {"j-a": 1, "j-b": 0, "j-c": 0, "j-d": 0, "j-e": 0, "j-f": 1}, "cv3": {"j-a": 2, "j-b": 0}}
    out = drift_vs_original_run(mine, labels, run)
    assert [c["cv_id"] for c in out["cvs_with_different_full_order"]] == ["cv1"]
    assert out["cvs_with_different_full_order"][0]["first_difference_rank"] == 5
    assert out["near_ties_rank5_rank6"][0]["cv_id"] == "cv1" and out["max_abs_cosine_diff_all_pairs"] == pytest.approx(0.0999, abs=1e-4)
    patched = out["metrics_if_changed_cvs_use_original_ranking"]["full"]
    assert patched["p_at_5"] == pytest.approx((0.2 + 0.5) / 2)
    assert drift_vs_original_run(mine, labels, tmp_path / "missing.json") is None
