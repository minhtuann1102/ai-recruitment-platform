"""Phan thuan cua thi nghiem so sanh embedding (plans/261126-2235-embedding-model-comparison): tim cosine trong bo nho,
bootstrap theo truy van, dem chunk bi cat. Chi numpy + stdlib (khong torch, khong mang) de pytest tests/ chay duoc
khi chua cai requirements-embedding-experiment.txt.

Duong tim DUY NHAT cho moi model (de so sanh chi do model): cosine toan kho -> lay k*OVERFETCH -> dedup theo qa_id
(app.rag.retriever.dedup) -> top-k. Kho duoc sap theo id, hoa diem thi lay chunk co id nho hon (argsort on dinh).
"""
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from app.rag.models import Chunk
from app.rag.retriever import OVERFETCH, dedup
from evals.rag_metrics import hit_at_k, reciprocal_rank

BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 20261126
CI_LEVEL = 0.95


def normalize(vectors: np.ndarray) -> np.ndarray:
    """Chuan hoa L2 theo hang (float32); vector 0 giu nguyen de khong chia cho 0."""
    v = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.where(norms == 0, 1.0, norms)


def retrieve_keys(matrix: np.ndarray, chunks: Sequence[Chunk], query_vec: np.ndarray, k: int = 5) -> List[str]:
    """Top-k dedup_key (qa_id) cua mot truy van. `matrix` da chuan hoa, hang i ung chunks[i]; query_vec chuan hoa."""
    scores = matrix @ np.asarray(query_vec, dtype=np.float32)
    order = np.argsort(-scores, kind="stable")[: k * OVERFETCH]
    return [c.dedup_key for c in dedup([chunks[i] for i in order])][:k]


def per_query_metrics(rows: Sequence[Dict], k: int = 5) -> Tuple[np.ndarray, np.ndarray]:
    """rows: [{retrieved, relevant}] -> (hit@k 0/1, reciprocal rank) theo tung truy van, cung ham voi rag_metrics."""
    hits = np.array([1.0 if hit_at_k(r["retrieved"], r["relevant"], k) else 0.0 for r in rows])
    rr = np.array([reciprocal_rank(r["retrieved"], r["relevant"], k) for r in rows])
    return hits, rr


def paired_bootstrap_ci(diffs: Sequence[float], resamples: int = BOOTSTRAP_RESAMPLES, seed: int = BOOTSTRAP_SEED,
                        level: float = CI_LEVEL) -> Optional[Tuple[float, float, float]]:
    """(trung binh, can duoi, can tren) cua hieu so theo tung truy van (model - co so), percentile bootstrap.
    Cung seed + cung so truy van thi cung chi so lay mau cho moi model (ghep cap). Rong thi None."""
    d = np.asarray(diffs, dtype=np.float64)
    if d.size == 0:
        return None
    idx = np.random.default_rng(seed).integers(0, d.size, size=(resamples, d.size))
    means = d[idx].mean(axis=1)
    lo, hi = np.percentile(means, [(1 - level) / 2 * 100, (1 + level) / 2 * 100])
    return float(d.mean()), float(lo), float(hi)


def verdict(lo: float, hi: float) -> str:
    """Luat quyet dinh cua plan: chi 'thang/thua' khi khoang tin cay 95% KHONG chua 0 (chat: lo>0 hoac hi<0).
    Khoang [0, 0] (moi hieu so bang 0) la ngang."""
    if lo > 0:
        return "better"
    if hi < 0:
        return "worse"
    return "tie"


def count_truncated(lengths: Sequence[int], max_len: int) -> Dict[str, float]:
    """So chunk co do dai token > max_len (se bi cat khi embed) va ti le %."""
    n = len(lengths)
    over = sum(1 for x in lengths if x > max_len)
    return {"n": n, "truncated": over, "pct": round(100.0 * over / n, 2) if n else 0.0, "max_len": max_len}


def truncation_by_type(lengths: Sequence[int], types: Sequence[str], max_len: int) -> Dict[str, Dict[str, float]]:
    """count_truncated cho tat ca va tach theo chunk_type (qa_pair / question)."""
    out = {"all": count_truncated(lengths, max_len)}
    for t in sorted(set(types)):
        out[t] = count_truncated([x for x, ty in zip(lengths, types) if ty == t], max_len)
    return out


def percentile_ms(samples_ms: Sequence[float], q: float) -> float:
    """Phan vi q (0-100) cua danh sach thoi gian (noi suy tuyen tinh, giong numpy)."""
    return float(np.percentile(np.asarray(samples_ms, dtype=np.float64), q))
