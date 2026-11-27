"""Giai doan `evaluate` (thuan numpy tren cache, khong goi mang, khong nap model): chay MOT duong tim cho moi model x
golden x chien luoc, recall@5 theo nhom + MRR, bootstrap ghep cap (10.000 lan, seed co dinh) cua hieu so so voi oa-small.

Chien luoc: raw (CHI SO CHINH, chi vector, khong bo loc category/difficulty) va raw+rewrite (ban viet lai LLM tao mot lan,
cung chuoi cho moi model, cung logic gop voi retrieval_experiment.texts_for). Chi so chinh theo TUNG tap (main, holdout);
dong gop chung (pooled) chi la phu, khong dung de ket luan thang/thua.
"""
import datetime
import subprocess
from typing import Dict, List

import numpy as np

from evals.embedding_experiment_cache import chunks_from_rows, load_corpus, read_json, text_key
from evals.embedding_experiment_core import (BOOTSTRAP_RESAMPLES, BOOTSTRAP_SEED, normalize, paired_bootstrap_ci,
                                             per_query_metrics, retrieve_keys, verdict)
from evals.embedding_experiment_corpus import precheck_missing
from evals.embedding_experiment_embed import store_for
from evals.embedding_experiment_models import REVISIONS, SPECS, resolve_revision
from evals.rag_metrics import recall_by_group
from evals.retrieval_experiment import texts_for

BASE, STRATEGIES, K = "oa-small", ("raw", "raw+rewrite"), 5
POOLED = "pooled"


def _git_head() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001 - thong tin phu
        return "unknown"


def _load_models(hashes: List[str]) -> Dict[str, Dict]:
    """Moi model: ma tran chuan hoa + vector truy van neu du; thieu thi ghi ly do vao status."""
    out: Dict[str, Dict] = {}
    for mid, spec in SPECS.items():
        rev = resolve_revision(spec)
        info = {"hf_or_api_name": spec.name, "revision": REVISIONS.get(mid, rev), "dims": spec.dims,
                "query_prefix": spec.query_prefix, "doc_prefix": spec.doc_prefix}
        store = store_for(spec)
        gap = store.missing(hashes)
        qvecs = read_json(f"qvec-{mid}-{rev[:12]}.json")
        if gap:
            info["status"] = f"chua chay: thieu vector kho ({len(hashes) - len(gap)}/{len(hashes)} chunk)"
        elif qvecs is None:
            info["status"] = "chua chay: thieu vector truy van"
        else:
            info["status"] = "ok"
            info["matrix"], info["qvecs"] = normalize(store.matrix(hashes)), qvecs
        out[mid] = info
    return out


def _run_set(golden: Dict, models: Dict, rewrites: Dict, chunks) -> Dict:
    res: Dict[str, Dict] = {}
    for strategy in STRATEGIES:
        if strategy == "raw+rewrite" and not all(q["query"] in rewrites for q in golden["queries"]):
            continue  # chua co ban viet lai cho moi truy van
        for mid, m in models.items():
            if m["status"] != "ok":
                continue
            texts = [q["query"] if strategy == "raw" else texts_for(q["query"], rewrites[q["query"]])["raw+rewrite"]
                     for q in golden["queries"]]
            if not all(text_key(t) in m["qvecs"] for t in texts):
                continue  # model nay chua embed du truy van cua chien luoc
            rows = []
            for q, text in zip(golden["queries"], texts):
                keys = retrieve_keys(m["matrix"], chunks, normalize(np.array(m["qvecs"][text_key(text)])), K)
                rows.append({"id": q["id"], "group": q["group"], "relevant": q["relevant"], "retrieved": keys})
            hits, rr = per_query_metrics(rows, K)
            res.setdefault(strategy, {})[mid] = {"by_group": recall_by_group(rows, K), "rows": rows,
                                                 "hits": hits.tolist(), "rr": rr.tolist()}
    return res


def _ci_block(vals_a: List[float], vals_b: List[float]) -> Dict:
    ci = paired_bootstrap_ci(np.array(vals_a) - np.array(vals_b))
    return {"diff": round(ci[0], 4), "lo": round(ci[1], 4), "hi": round(ci[2], 4), "verdict": verdict(ci[1], ci[2])}


def _cis(res: Dict) -> Dict:
    """Hieu so (model - oa-small) theo truy van, tong + tung nhom: {strategy: {model: {group: {n, recall, mrr}}}}."""
    out: Dict[str, Dict] = {}
    for strategy, by_model in res.items():
        if BASE not in by_model:
            continue
        base = by_model[BASE]
        groups = ["all"] + sorted({r["group"] for r in base["rows"]})
        for mid, cur in by_model.items():
            if mid == BASE:
                continue
            for g in groups:
                idx = [i for i, r in enumerate(base["rows"]) if g == "all" or r["group"] == g]
                out.setdefault(strategy, {}).setdefault(mid, {})[g] = {
                    "n": len(idx),
                    "recall": _ci_block([cur["hits"][i] for i in idx], [base["hits"][i] for i in idx]),
                    "mrr": _ci_block([cur["rr"][i] for i in idx], [base["rr"][i] for i in idx])}
    return out


def _pool(sets: Dict[str, Dict]) -> Dict:
    """Gop main + holdout (phu): noi hang va mang diem cua tung model theo thu tu tap."""
    pooled: Dict[str, Dict] = {}
    for part in sets.values():
        for strategy, by_model in part.items():
            for mid, cur in by_model.items():
                tgt = pooled.setdefault(strategy, {}).setdefault(mid, {"rows": [], "hits": [], "rr": []})
                for key in ("rows", "hits", "rr"):
                    tgt[key].extend(cur[key])
    for by_model in pooled.values():
        for cur in by_model.values():
            cur["by_group"] = recall_by_group(cur["rows"], K)
    return pooled


def _ops() -> Dict:
    return {mid: {"embed": read_json(f"ops-embed-{mid}.json"), "query": read_json(f"ops-query-{mid}.json")}
            for mid in SPECS}


def evaluate(versions: Dict[str, Dict], alt_dir) -> Dict:
    rows = load_corpus()
    hashes, chunks = [r["content_hash"] for r in rows], chunks_from_rows(rows)
    models = _load_models(hashes)
    rewrites = (read_json("rewrites.json") or {"rewrites": {}})
    results: Dict[str, Dict] = {}
    cis: Dict[str, Dict] = {}
    for version, v in versions.items():
        sets = {name: _run_set(g, models, rewrites["rewrites"], chunks) for name, g in v["sets"].items()}
        if len(sets) > 1:
            sets[POOLED] = _pool(sets)
        results[version] = {n: {s: {m: {k: x[k] for k in ("by_group", "hits", "rr", "rows")} for m, x in bm.items()}
                                for s, bm in strat.items()} for n, strat in sets.items()}
        cis[version] = {n: _cis(strat) for n, strat in sets.items()}
    main_sha = versions["repo"]["sha256"]
    return {
        "generated": datetime.date.today().isoformat(), "git_head": _git_head(), "k": K, "base": BASE,
        "bootstrap": {"resamples": BOOTSTRAP_RESAMPLES, "seed": BOOTSTRAP_SEED, "level": 0.95, "unit": "query"},
        "corpus": read_json("corpus-meta.json"),
        "golden": {ver: {"dir": v["dir"], "sha256": v["sha256"], "same_files_as_repo": v["sha256"] == main_sha,
                         "n_queries": {n: len(g["queries"]) for n, g in v["sets"].items()}}
                   for ver, v in versions.items()},
        "precheck_missing": precheck_missing(versions, [r["qa_id"] for r in rows]),
        "models": {m: {k: x for k, x in info.items() if k not in ("matrix", "qvecs")} for m, info in models.items()},
        "rewrites_meta": rewrites.get("meta"), "parity": read_json("parity.json"), "ops": _ops(),
        "results": results, "ci": cis}
