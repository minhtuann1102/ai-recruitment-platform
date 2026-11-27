"""Cong tai lap (reproduction gate) cua experiment embedding 017: harness offline voi vector text-embedding-3-small phai ra lai
so da cong bo trong specs/017-cv-jd-matching/eval-results.md (muc 2 va 3) trong +-0.005 truoc khi doi model.

Chi muc JD (vector, metadata, content) doc read-only tu ai_db dung cach endpoint nap (job_index + rows_to_snapshot), khong
dung jd_normalized.jsonl cho loc cung / diem (file co the da lech sau khi index); jd_normalized chi dung de kiem van ban
va metadata co con khop ban da index khong (chan doan).
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Dict, Sequence

import numpy as np

from .jd_match_text import build_match_record, build_match_text
from .match_embedding_ai_db import IndexRows, fetch_index_rows, first_row_per_jd, parse_vector, read_db_url
from .match_eval_metrics import quality_summary
from .qa_record_builder import content_hash

TOLERANCE = 0.005
# eval-results.md muc 2 (tong) va muc 3 (theo ngon ngu JD): same = JD vi, cross = JD en / mixed. (P@5, nDCG@5, so CV)
PUBLISHED_OVERALL = {"full": (0.642, 0.883, 24), "skill_match": (0.625, 0.847, 24), "cosine": (0.617, 0.842, 24)}
PUBLISHED_BY_LANGUAGE = {
    ("full", "same"): (0.455, 0.857, 22), ("skill_match", "same"): (0.482, 0.795, 22), ("cosine", "same"): (0.473, 0.875, 22),
    ("full", "cross"): (0.396, 0.962, 24), ("skill_match", "cross"): (0.396, 0.971, 24), ("cosine", "cross"): (0.396, 0.903, 24)}
METHODS = ("full", "skill_match", "cosine")
META_KEYS = ("title", "group", "level", "deadline", "skills")


@dataclass
class IndexData:
    snapshot: object  # JobIndexSnapshot (vector 1536 chieu da luu, jobs theo thu tu endpoint)
    content_by_id: Dict[str, str]
    meta_by_id: Dict[str, Dict]
    hash_by_id: Dict[str, str]
    info: Dict  # db_role, n_rows, n_jobs, max_created_at, vector_mismatch


def load_index(ai: SimpleNamespace, db_url_reader=read_db_url) -> IndexData:
    model = ai.settings.embedding_model
    rows: IndexRows = fetch_index_rows(db_url_reader(), model)
    snapshot = ai.job_snapshot.rows_to_snapshot([(r["embedding_text"], r["metadata"]) for r in rows.rows], model,
                                                datetime.now(timezone.utc))
    first = first_row_per_jd(rows.rows)
    mismatch = []  # chong lech dedup giua rows_to_snapshot va first_row_per_jd: vector cua ban da chon phai khop hang snapshot
    for i, job in enumerate(snapshot.jobs):
        vector = parse_vector(first[job.job_id]["embedding_text"])
        if not np.allclose(vector / np.linalg.norm(vector), snapshot.matrix[i], atol=1e-9):
            mismatch.append(job.job_id)
    return IndexData(
        snapshot, {j: r["content"] for j, r in first.items()}, {j: r["metadata"] for j, r in first.items()},
        {j: r["content_hash"] for j, r in first.items()},
        {"db_role": rows.db_role, "embedding_model": model, "n_rows": len(rows.rows), "n_jobs": len(snapshot),
         "max_created_at": rows.max_created_at.isoformat(), "vector_mismatch": mismatch})


def check_pool_texts(index: IndexData, jds: Dict[str, Dict], pool_ids: Sequence[str]) -> Dict:
    """build_match_text(jd) / content_hash / metadata cua JD pool trong jd_normalized.jsonl co khop ban da index khong."""
    text_diff, hash_diff, meta_diff = [], [], []
    for jd_id in pool_ids:
        stored, jd = index.content_by_id[jd_id], jds[jd_id]
        if build_match_text(jd) != stored:
            text_diff.append(jd_id)
        if content_hash(stored) != index.hash_by_id[jd_id]:
            hash_diff.append(jd_id)
        record, _ = build_match_record(jd)
        meta = index.meta_by_id[jd_id]
        if record is None or any(record["metadata"].get(k) != meta.get(k) for k in META_KEYS):
            meta_diff.append(jd_id)
    return {"pool": len(pool_ids), "text_differs_from_jd_normalized": text_diff, "stored_hash_differs_from_stored_content": hash_diff,
            "metadata_differs_from_jd_normalized": meta_diff}


def quality_tables(items_by_cv: Dict[str, Sequence[Dict]], labels: Dict, groups: Dict[str, str],
                   methods: Sequence[str] = METHODS) -> Dict:
    """quality_summary (endpoint-style: cosine / score da kep + lam tron) cho cac cach xep x (tong, vi, en/mixed)."""
    out: Dict = {"overall": {}, "by_language": {}}
    for method in methods:
        out["overall"][method] = quality_summary(items_by_cv, labels, method)
        for group in ("same", "cross"):
            out["by_language"][f"{method}/{group}"] = quality_summary(items_by_cv, labels, method, keep=lambda j, g=group: groups[j] == g)
    return out


def compare_published(tables: Dict, methods: Sequence[str] = METHODS) -> Dict:
    def row(name: str, pub, got: Dict) -> Dict:
        d_p, d_n = got["p_at_5"] - pub[0], got["ndcg_at_5"] - pub[1]
        return {"name": name, "published_p_at_5": pub[0], "got_p_at_5": got["p_at_5"], "delta_p": d_p,
                "published_ndcg_at_5": pub[1], "got_ndcg_at_5": got["ndcg_at_5"], "delta_ndcg": d_n,
                "published_n_cv": pub[2], "got_n_cv": got["n_cv"],
                "ok": abs(d_p) <= TOLERANCE and abs(d_n) <= TOLERANCE and pub[2] == got["n_cv"]}

    overall = [row(m, p, tables["overall"][m]) for m, p in PUBLISHED_OVERALL.items() if m in methods]
    language = [row(f"{m}/{g}", p, tables["by_language"][f"{m}/{g}"]) for (m, g), p in PUBLISHED_BY_LANGUAGE.items() if m in methods]
    return {"tolerance": TOLERANCE, "overall": overall, "by_language": language,
            "overall_pass": all(r["ok"] for r in overall), "language_pass": all(r["ok"] for r in language)}
