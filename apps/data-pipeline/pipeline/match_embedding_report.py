"""Bao cao experiment embedding 017 (Phase 2): JSON tho + markdown (tieng Anh, ngan) tu dict ket qua cua match_embedding_experiment."""
import json
from pathlib import Path
from typing import Dict, List, Optional

from .match_embedding_report_notes import GATE_NOTES, LIMITS

JSON_NAME, MD_NAME = "matching-embedding-results.json", "matching-embedding-results.md"
COMMANDS = """```bash
cd apps/data-pipeline
.venv/Scripts/python.exe -m pip install --use-feature=truststore --index-url https://download.pytorch.org/whl/cpu torch
.venv/Scripts/python.exe -m pip install --use-feature=truststore -r requirements-embedding-experiment.txt
.venv/Scripts/python.exe -m pipeline.match_embedding_experiment            # gate, then all models (cached under data/processed/match_eval/embedding_cache); stops (exit 3) if the gate misses
.venv/Scripts/python.exe -m pipeline.match_embedding_experiment --accept-gate-miss "reproduced except one API-nondeterminism tie flip (accepted by main session)"   # command that produced this report
.venv/Scripts/python.exe -m pipeline.match_embedding_experiment --gate-only
.venv/Scripts/python.exe -m pipeline.match_embedding_experiment --models oa-small,st-bge --remeasure
```
Needs sandbox off for network (OpenAI, Hugging Face, ai_db). Keys: data-pipeline/.env (EMBEDDING_API_KEY), ai-service/.env (AI_DB_URL, read-only role)."""


def _f(v: Optional[float], digits: int = 3) -> str:
    return "n/a" if v is None else f"{v:.{digits}f}"


def _ci(c: Dict) -> str:
    return f"{c['mean_diff']:+.3f} [{c['ci_lo']:+.3f}, {c['ci_hi']:+.3f}]"


def _table(header: List[str], rows: List[List[str]]) -> str:
    return "\n".join(["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + ["| " + " | ".join(r) + " |" for r in rows])


def _gate_md(gate: Dict) -> str:
    pub = gate["published"]

    def rows(lst):
        return [[r["name"], f"{r['published_p_at_5']:.3f}", _f(r["got_p_at_5"]), f"{r['delta_p']:+.4f}", f"{r['published_ndcg_at_5']:.3f}",
                 _f(r["got_ndcg_at_5"]), f"{r['delta_ndcg']:+.4f}", f"{r['got_n_cv']}/{r['published_n_cv']}", "ok" if r["ok"] else "MISS"]
                for r in lst]

    head = ["method", "pub P@5", "got P@5", "delta", "pub nDCG@5", "got nDCG@5", "delta", "n_cv got/pub", ""]
    idx, chk, pair, partial = gate["index"], gate["pool_text_check"], gate["pair_check"], gate.get("partial", False)
    lines = [
        ("**PARTIAL gate (embedding-free part only): OpenAI keys rejected, the full gate did NOT run.** Skill-only ranking uses no "
         "embeddings, so this checks hard filters, JD metadata, pair set and tie order only. " if partial else "")
        + f"Result: **{'PASS' if pub['overall_pass'] else 'FAIL'}** (overall, tolerance +-{pub['tolerance']}); "
        f"by-language rows {'all within tolerance' if pub['language_pass'] else 'have a miss'}.", "",
        "JD side: vectors, metadata and content read **read-only from ai_db** (same WHERE / ORDER as `job_index.JD_SQL`, loaded through the real "
        f"`rows_to_snapshot`); role `{idx['db_role']}`, {idx['n_rows']} rows -> {idx['n_jobs']} jobs, newest `created_at` {idx['max_created_at']}, "
        f"embedding_model `{idx['embedding_model']}`. CV side: `cv_text.build_cv_text` embedded fresh with text-embedding-3-small"
        f"{' (NOT available: key rejected)' if partial else ''}. "
        f"Filter + score: the real `group_for_track`, `cv_skills`, `candidate_level_rank`, `rank_jobs` (job_ids = 36-JD pool, as_of {gate['settings']['as_of']}, "
        f"weights {gate['settings']['weights']}, max_level_gap {gate['settings']['max_level_gap']}).", "",
        f"Pair set: filtered {pair['filtered_pairs']} vs labeled {pair['labeled_pairs']} -> {'equal' if pair['equal'] else 'DIFFERENT'}.", "",
        "Overall (eval-results.md section 2):", _table(head, rows(pub["overall"])), "",
        "By JD language (eval-results.md section 3; same = vi JD, cross = en/mixed JD):", _table(head, rows(pub["by_language"])), "",
        f"Pool text vs stored content: {len(chk['text_differs_from_jd_normalized'])}/{chk['pool']} differ; stored hash vs md5(content): "
        f"{len(chk['stored_hash_differs_from_stored_content'])} differ; metadata (title/group/level/deadline/skills) vs jd_normalized: "
        f"{len(chk['metadata_differs_from_jd_normalized'])} differ; stored-vector/snapshot row mismatches: {len(idx['vector_mismatch'])}."]
    if not partial:
        fresh, bs = gate["jd_vector_fresh_vs_stored_cosine"], gate["bootstrap_sanity"]
        lines += ["", f"Re-embedded JD vectors vs stored: cosine min {fresh['min']:.6f}, mean {fresh['mean']:.6f}; gate with re-embedded JD vectors: "
                  f"overall {'PASS' if gate['with_fresh_jd_vectors']['overall_pass'] else 'FAIL'}.", "",
                  "Bootstrap sanity on oa-small (eval-analysis.md section 1 reports full vs skill +0.036 [-0.010, +0.084], 12/6/6 and full vs cosine +0.041, 12/10/2):",
                  *(f"- {name}: {_ci(c)}, W/L/T {c['wins']}/{c['losses']}/{c['ties']}"
                    for name, c in (("full - skill_match", bs["full_vs_skill_match"]), ("full - cosine", bs["full_vs_cosine"])))]
        lines += _drift_md(gate.get("drift_vs_original_run"))
    return "\n".join(lines)


def _drift_md(d: Optional[Dict]) -> List[str]:
    if not d:
        return []
    out = ["", f"Comparison with the original 017 run (`{d['run_file']}`, per-pair scores, not committed): max |cosine diff| over all 264 pairs "
           f"{d['max_abs_cosine_diff_all_pairs']:.5f}; CVs with diff > 1e-4: {d['cvs_with_cosine_diff_over_1e-4'] or 'none'}.",
           f"CVs whose full-score order differs from the original run: {len(d['cvs_with_different_full_order'])}"]
    for c in d["cvs_with_different_full_order"]:
        out.append(f"- {c['cv_id']}: first difference at rank {c['first_difference_rank']}; now {c['now']}, original {c['original_run']}")
    out += [f"CVs with rank-5/rank-6 full-score gap < 0.003 (flip-prone): {d['near_ties_rank5_rank6'] or 'none'}",
            "Published numbers if only the differing CVs use the original ranking: "
            + "; ".join(f"{m} P@5 {_f(v['p_at_5'])} nDCG@5 {_f(v['ndcg_at_5'])}" for m, v in d["metrics_if_changed_cvs_use_original_ranking"].items())]
    return out


def _models_md(res: Dict[str, Dict]) -> str:
    out: List[str] = []
    order = list(res)
    base = res["oa-small"]
    skill = base["skill_only_baseline"]
    rows = []
    for m in order:
        r = res[m]
        p, c = r["primary_cosine_only"]["overall"], r.get("vs_oa_small", {}).get("primary_cosine_only")
        rows.append([m, _f(p["ndcg_at_5"]), _f(p["p_at_5"]), "(baseline)" if c is None else _ci(c),
                     "-" if c is None else f"{c['wins']}/{c['losses']}/{c['ties']}", "-" if c is None else c["verdict"].upper()])
    out += ["## 3. PRIMARY: cosine-only ranking per CV (scale-invariant)", "",
            f"Raw cosine (no clipping/rounding) over the 264 hard-filter survivors; nDCG@5 / P@5 mean over {base['primary_cosine_only']['overall']['n_cv']} CVs. "
            "Delta = model - oa-small on per-CV nDCG@5, paired bootstrap by CV (10,000 resamples, seed 20261126), 95% percentile CI.", "",
            _table(["model", "nDCG@5", "P@5", "delta nDCG@5 vs oa-small [95% CI]", "W/L/T (CVs)", "verdict"], rows), "",
            f"Skill-only baseline (model independent): nDCG@5 {_f(skill['ndcg_at_5'])}, P@5 {_f(skill['p_at_5'])}. "
            "Endpoint-style cosine-only (clipped at 0, rounded to 4 digits, as in eval-results): "
            + "; ".join(f"{m} {_f(res[m]['endpoint_style_cosine_only']['ndcg_at_5'])}/{_f(res[m]['endpoint_style_cosine_only']['p_at_5'])}" for m in order) + " (nDCG/P@5).", ""]
    winners = [m for m in order if m != "oa-small" and res[m]["vs_oa_small"]["primary_cosine_only"]["verdict"] == "better"]
    losers = [m for m in order if m != "oa-small" and res[m]["vs_oa_small"]["primary_cosine_only"]["verdict"] == "worse"]
    out += ["## 4. Decision rule (predeclared, applied literally)", "",
            "A model wins on quality only if the 95% bootstrap CI of the nDCG@5 difference (by CV) excludes 0; otherwise it is treated as equal and the choice is operational. "
            "No multiple-comparison correction (as in the plan); " + f"{len(order) - 1} comparisons were made.", "",
            f"- Quality winners over oa-small: **{', '.join(winners) if winners else 'none'}**",
            f"- Significantly worse than oa-small: {', '.join(losers) if losers else 'none'}",
            "- Everything else: statistically indistinguishable from oa-small on these 24 CVs (equal); decide on cost/ops.", ""]
    rows = []
    for m in order:
        r, c = res[m], res[m].get("vs_oa_small", {}).get("secondary_full_score")
        f = r["secondary_full_score"]["overall"]
        rows.append([m, _f(f["ndcg_at_5"]), _f(f["p_at_5"]), "(baseline)" if c is None else _ci(c), "-" if c is None else c["verdict"].upper()])
    out += ["## 5. SECONDARY: full score (0.6 cosine + 0.3 skill + 0.1 level, unchanged weights)", "",
            "**Weights were tuned on the 3-small cosine scale**; other models have a different cosine scale/spread (see section 7), "
            "so the 0.6 weight means something different per model. Not used for the decision rule.", "",
            _table(["model", "nDCG@5", "P@5", "delta nDCG@5 vs oa-small [95% CI]", "verdict"], rows), ""]
    rows = []
    for m in order:
        for kind, label in (("primary_cosine_only", "cosine-only"), ("secondary_full_score", "full")):
            s, c = res[m][kind]["same"], res[m][kind]["cross"]
            rows.append([m, label, _f(s["ndcg_at_5"]), _f(s["p_at_5"]), str(s["n_cv"]), _f(c["ndcg_at_5"]), _f(c["p_at_5"]), str(c["n_cv"])])
    out += ["## 6. By JD language (CVs are all Vietnamese)", "",
            "Within-subset ranking only (eval-analysis.md section 2: cannot show cross-language bias; ignore P@5 there, subsets have 4-7 JDs per CV).", "",
            _table(["model", "method", "vi JD nDCG@5", "P@5", "n_cv", "en/mixed JD nDCG@5", "P@5", "n_cv"], rows), ""]
    rows = []
    for m in order:
        d = res[m]["diagnostics"]
        lab = d["cosine_by_label_group"]
        rows.append([m, f"{100 * d['vi_share_top5_cosine_only']:.0f}%", f"{100 * d['vi_share_top5_full']:.0f}%", f"{100 * d['vi_share_of_relevant_pairs']:.0f}%"]
                    + [f"{_f(lab[str(l)].get('same'))} / {_f(lab[str(l)].get('cross'))}" for l in (0, 1, 2)])
    out += ["## 7. Cross-language bias and cosine scale", "",
            "vi share of top-5: share of Vietnamese JDs among each CV's top 5 (published for 3-small: cosine-only 69%, full 56%; about 55% of relevant pairs are vi JD). "
            "Mean cosine by label for vi / en+mixed JD (published 3-small: label 0 0.594 / 0.530, label 2 0.682 / 0.637).", "",
            _table(["model", "vi share top5 (cos-only)", "vi share top5 (full)", "vi share of relevant pairs", "label 0 vi / en", "label 1 vi / en", "label 2 vi / en"], rows), ""]
    rows = []
    for m in order:
        s = res[m]["diagnostics"]["cosine_scale"]
        rows.append([m, _f(s["mean"]), _f(s["std"]), f"{_f(s['min'])} .. {_f(s['max'])}", str(s["n_negative"]), str(s["n_rounded_ties"])])
    out += [_table(["model", "cosine mean", "std", "min .. max", "negative pairs (clipped to 0 in scorer)", "tied pairs after 4-digit rounding"], rows), ""]
    return "\n".join(out)


def _ops_md(res: Dict[str, Dict]) -> str:
    rows = []
    for m, r in res.items():
        o = r["ops"]
        if "latency_ms" not in o:  # OpenAI: do tre mang
            lat = o.get("network_latency_ms_query") or {}
            rows.append([m, str(r["dims"]), "8191 tokens (API)", "0 (texts <= 1200 chars)", "n/a", "n/a", f"{_f(lat.get('p50'), 0)} / {_f(lat.get('p95'), 0)} (network, n={lat.get('n', 0)})", "n/a (API)", "n/a"])
            continue
        q, p, t = o["latency_ms"]["query"], o["latency_ms"]["passage"], o["truncation"]
        cpu = o["cpu"]
        rows.append([m, str(r["dims"]), str(o["max_seq_length"]), f"CV {100 * t['query']['rate']:.0f}% (mean {t['query']['mean_tokens']:.0f} tok, max {t['query']['max_tokens']}); JD {100 * t['passage']['rate']:.0f}% (mean {t['passage']['mean_tokens']:.0f}, max {t['passage']['max_tokens']})",
                     f"{o['load_s']:.1f}", f"{o['peak_rss_mb']:.0f}", f"{q['p50']:.0f} / {q['p95']:.0f}  (n={q['n']})", f"{p['p50']:.0f} / {p['p95']:.0f}  (n={p['n']})",
                     f"{cpu['other_pct']:.0f}% other, {cpu['own_pct']:.0f}% own"])
    return "\n".join(["## 8. Operations (CPU, torch 4 threads = e2-standard-4 shape; this machine is 12 logical cores)", "",
                      "Single-text encodes, 3 rounds after 3 warm-up calls, nearest-rank percentiles; each ST model in its own process (peak RSS = process peak working set). "
                      "OpenAI latency is a network round trip: not comparable with local CPU. `other` = system CPU% minus this process's share during the timed window "
                      "(contention from other work on this machine, e.g. the Phase 1 worker); high values inflate latency.", "",
                      _table(["model", "dims", "max_seq", "truncated (tokens incl. special + prefix)", "load s", "peak RSS MB", "CV embed p50 / p95 ms", "JD embed p50 / p95 ms", "CPU in window"], rows), ""])


def render_markdown(data: Dict, gate_failed: bool = False) -> str:
    gate, res = data["gate"], data.get("models", {})
    head = ["# Matching embedding comparison: 017 scorer, embedding swapped (Phase 2)", "",
            "Dev evidence on **264 labeled pairs (24 CVs x 36-JD pool, as_of 2026-11-01)** from 017; labels are LLM labels. Only the embedding model changes; hard filters, "
            "skill_match, level_fit and the 0.6/0.3/0.1 weights are the 017 code. The final matching decision is made on the 019 locked test set, not on this table.", "",
            "## 1. Models and pinned revisions", ""]
    if res:
        head += [_table(["id", "model", "dims", "revision"], [[m, r["name"], str(r["dims"]), r["revision"]] for m, r in res.items()]), "",
                 "Prefixes: st-e5 uses `query: ` for CV text and `passage: ` for JD text. oa-large uses `dimensions=1536`. All vectors L2-normalized, cosine. "
                 "Every model embeds the same strings: CV = `build_cv_text`, JD = the stored `content` that 3-small indexed.", ""]
    waiver = data.get("gate_waiver")
    head += [f"## 2. Gate: {waiver}" if waiver else "## 2. Reproduction gate (oa-small)", ""]
    if waiver:
        head += ["Literal tolerance check (+-0.005) FAILED on full-score P@5 only; the miss was investigated (below) and the caller accepted it "
                 "as reproduced. The numbers in the table are unchanged and unwaived.", ""]
    head += [_gate_md(gate), ""] + ([GATE_NOTES, ""] if waiver else [])
    if gate_failed:
        reason = data.get("blocked")
        note = (f"**GATE BLOCKED, model swaps were NOT run: {reason}.** Provide a valid OpenAI key (EMBEDDING_API_KEY in apps/data-pipeline/.env) and rerun."
                if reason else "**GATE FAILED: model swaps were not run.**")
        return "\n".join(head + [note, "", "## Reproduce", "", COMMANDS, ""])
    body = [_models_md(res), _ops_md(res)] if res else []
    fails = data.get("failures") or {}
    tail = [LIMITS, "## 10. Failures", "", *(f"- {m}: {msg}" for m, msg in fails.items()), *([] if fails else ["- none"]), "",
            "## 11. Reproduce", "", COMMANDS, ""]
    return "\n".join(head + body + tail)


def write_reports(data: Dict, out_dir: Path, gate_failed: bool = False) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / JSON_NAME).write_text(json.dumps(data, ensure_ascii=False, indent=2, default=float), encoding="utf-8")
    (out_dir / MD_NAME).write_text(render_markdown(data, gate_failed), encoding="utf-8")
