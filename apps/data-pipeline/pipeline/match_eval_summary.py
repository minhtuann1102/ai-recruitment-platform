"""Tong hop so lieu cua match-eval (spec 017 US3): chat luong theo 3 cach, tach ngon ngu, do tre, chi phi, mo ta bo du lieu.

Tra mot dict JSON-able: vua la file ket qua tho (data/processed/match_eval/run-*.json), vua la dau vao cua
match_eval_report.render_markdown (mot nguon so lieu duy nhat cho bang va JSON).
"""
import json
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

from .match_eval_client import MatchReply
from .match_eval_data import EvalData
from .match_eval_metrics import METHODS, latency_summary, quality_summary
from .settings import MatchEvalSettings

INDEX_REPORT_GLOB = "run-report-index-jd-match-*.json"  # khong lan voi run-report-index-<ngay>.json cua index Q&A
VARIANTS = ("with_job_ids", "without_job_ids")
TIMINGS = ("server_score_ms", "server_total_ms", "client_ms")
LABEL_KEYS = ("labeled_by", "labeled_at", "method", "rubric", "pair_set", "agreement", "final_source")


def new_latency_samples() -> Dict[str, Dict[str, List[float]]]:
    return {variant: {timing: [] for timing in TIMINGS} for variant in VARIANTS}


def _number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def add_latency_sample(samples: Dict, variant: str, reply: MatchReply) -> None:
    timing = reply.body["metadata"].get("timing_ms") or {}
    for key, value in (("server_score_ms", timing.get("score")), ("server_total_ms", timing.get("total")),
                       ("client_ms", reply.client_ms)):
        if _number(value):
            samples[variant][key].append(float(value))


def embedding_tokens(body: Dict) -> int:
    value = (body["metadata"].get("usage") or {}).get("embedding_tokens")
    return value if type(value) is int else 0


def _read_index_report(path: Path) -> Optional[Dict]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        index = doc["index"]
        embedded, records, cleanup = index.get("embedded"), doc.get("chunks_out"), index.get("cleanup")
        return {"source": path.name, "embedding_tokens": int(index["embedding_tokens"]), "embedded": embedded, "records": records,
                "cleanup": cleanup,
                # day du = moi ban ghi deu duoc embed trong lan chay do va writer da don dataset (khong phai --limit / loi embed / chay tang dan)
                "complete": embedded is not None and embedded == records and cleanup == "done"}
    except (ValueError, KeyError, TypeError, AttributeError, OSError):
        return None


def find_index_report(directory: Path) -> Optional[Dict]:
    """Run report index-jd-match de tinh chi phi index toan bo JD.

    Uu tien lan chay day du moi nhat (embed het ban ghi); khong co thi lan moi nhat co token > 0 (complete = False);
    khong co nua thi lan moi nhat (lan chay lai: 0 token). Ten file co moc UTC nen xep theo ten = theo thoi gian.
    """
    found = [r for r in map(_read_index_report, sorted(directory.glob(INDEX_REPORT_GLOB), reverse=True)) if r]
    return (next((r for r in found if r["complete"]), None) or next((r for r in found if r["embedding_tokens"] > 0), None)
            or (found[0] if found else None))


def _per_method(items_by_cv, labels, keep=None) -> Dict:
    return {method: quality_summary(items_by_cv, labels, method, keep) for method in METHODS}


def build_summary(data: EvalData, jds: Dict[str, Dict], language_groups: Dict[str, str], bodies: Dict[str, Dict],
                  samples: Dict, token_counts: List[int], settings: MatchEvalSettings, index_report: Optional[Dict],
                  rounds: int, generated_at: str) -> Dict:
    """bodies: cv_id -> response cua lan goi chat luong (job_ids = pool, page_size 50)."""
    labels = data.labels
    items = {cv_id: body["items"] for cv_id, body in bodies.items()}
    meta = next(iter(bodies.values()))["metadata"]
    price = settings.embedding_price_per_1m
    mean_tokens = sum(token_counts) / len(token_counts) if token_counts else 0.0
    report = index_report or {"source": None, "embedding_tokens": None, "embedded": None, "records": None, "cleanup": None,
                              "complete": False}  # chua chay index-jd-match: de trong, khong doan
    tokens = report["embedding_tokens"]
    index_cost = {**report, "usd": None if tokens is None else tokens * price / 1_000_000}
    return {
        "generated_at": generated_at,
        "rounds": rounds,
        "dataset": {
            "n_cv": len(data.cvs), "n_jd": len(data.jd_ids), "n_pairs": sum(len(v) for v in items.values()), "as_of": data.as_of,
            "embedding_model": meta.get("embedding_model"), "index_size": meta.get("index_size"),
            "weights": meta.get("weights"), "max_level_gap": meta.get("max_level_gap"),
            "label_counts": dict(sorted(Counter(v for pairs in labels.values() for v in pairs.values()).items())),
            "jd_languages": dict(sorted(Counter(jd["language"] for jd in jds.values()).items())),
            "n_synthetic_jd": sum(1 for jd in jds.values() if jd.get("synthetic")),
            "labeling": {key: data.label_meta.get(key) for key in LABEL_KEYS},
        },
        "quality": _per_method(items, labels),
        "language_split": {group: _per_method(items, labels, keep=lambda jd_id, g=group: language_groups[jd_id] == g)
                           for group in ("same", "cross")},
        "per_cv": {cv_id: _per_method({cv_id: cv_items}, labels) for cv_id, cv_items in items.items()},
        "rankings": {cv_id: [{"job_id": i["job_id"], "label": labels[cv_id][i["job_id"]], "score": i["score"],
                              "cosine": i["components"]["cosine"], "skill_match": i["components"]["skill_match"]} for i in cv_items]
                     for cv_id, cv_items in items.items()},
        "latency": {variant: {timing: latency_summary(values) for timing, values in samples[variant].items()} for variant in VARIANTS},
        "cost": {"price_per_1m_usd": price, "index": index_cost,
                 "request": {"n_requests": len(token_counts), "mean_embedding_tokens": mean_tokens,
                             "usd": mean_tokens * price / 1_000_000}},
    }
