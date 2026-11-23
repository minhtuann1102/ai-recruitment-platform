"""Metric danh gia goi y CV-JD (spec 017 US3, FR-021, research R9): ham thuan, khong I/O.

Xep lai ket qua cua endpoint theo tung thanh phan (full = `score`, skill_match, cosine) de co baseline ma khong chep
cong thuc. Quy uoc (in vao bang ket qua):
- P@5: lien quan = nhan >= 1; mau so = min(5, so JD dang xet), de tap con ngon ngu (thuong < 5 JD) so sanh duoc.
- nDCG@5: gain = nhan (tuyen tinh); ideal xep tu moi nhan cua CV trong tap dang xet; ideal = 0 -> None.
- CV khong co JD lien quan (nhan >= 1) trong tap dang xet bi bo khoi ca hai trung binh (so CV con lai la `n_cv`).
- percentile: nearest-rank (gia tri quan sat duoc thu ceil(p/100 * n)), hop voi cach noi "95% yeu cau <= X ms".
"""
import math
from typing import Callable, Dict, List, Optional, Sequence

K = 5
METHODS = ("full", "skill_match", "cosine")


def _value(item: Dict, method: str) -> float:
    if method == "full":
        return item["score"]
    if method in ("skill_match", "cosine"):
        return item["components"][method]
    raise ValueError(f"cach tinh khong hop le: {method} (chon {', '.join(METHODS)})")


def rank_items(items: Sequence[Dict], method: str) -> List[Dict]:
    """Xep lai theo thanh phan giam dan, hoa thi job_id tang dan (giong luat cua endpoint); khong sua `items`."""
    return sorted(items, key=lambda item: (-_value(item, method), item["job_id"]))


def precision_at_k(labels: Sequence[int], k: int = K) -> float:
    """`labels` theo thu tu xep hang."""
    top = list(labels[:k])
    return sum(1 for label in top if label >= 1) / len(top) if top else 0.0


def _dcg(gains: Sequence[int], k: int) -> float:
    return sum(gain / math.log2(position + 2) for position, gain in enumerate(gains[:k]))


def ndcg_at_k(labels: Sequence[int], k: int = K) -> Optional[float]:
    ideal = _dcg(sorted(labels, reverse=True), k)
    return _dcg(labels, k) / ideal if ideal > 0 else None


def percentile(values: Sequence[float], p: float) -> float:
    if not values:
        raise ValueError("khong co gia tri de tinh percentile")
    ordered = sorted(values)
    rank = max(1, math.ceil(p / 100 * len(ordered)))
    return ordered[min(rank, len(ordered)) - 1]


def latency_summary(values: Sequence[float]) -> Dict:
    if not values:
        return {"n": 0, "p50": None, "p95": None}
    return {"n": len(values), "p50": percentile(values, 50), "p95": percentile(values, 95)}


def _mean(values: Sequence[float]) -> Optional[float]:
    return sum(values) / len(values) if values else None


def quality_summary(items_by_cv: Dict[str, Sequence[Dict]], labels: Dict[str, Dict[str, int]], method: str,
                    keep: Optional[Callable[[str], bool]] = None) -> Dict:
    """P@5 / nDCG@5 trung binh tren CV cho mot cach tinh.

    keep(jd_id) loc tap JD cua moi CV (tap con ngon ngu): xep hang truoc, loc sau, nen thu tu tuong doi giu nguyen.
    Tra {p_at_5, ndcg_at_5, n_cv, n_pairs}; n_pairs = tong so cap cua cac CV duoc tinh.
    """
    precisions: List[float] = []
    ndcgs: List[float] = []
    pairs = 0
    for cv_id, items in items_by_cv.items():
        ranked = [item["job_id"] for item in rank_items(items, method) if keep is None or keep(item["job_id"])]
        ranked_labels = [labels[cv_id][jd_id] for jd_id in ranked]
        ndcg = ndcg_at_k(ranked_labels)
        if ndcg is None:  # khong co JD lien quan trong tap nay
            continue
        precisions.append(precision_at_k(ranked_labels))
        ndcgs.append(ndcg)
        pairs += len(ranked_labels)
    return {"p_at_5": _mean(precisions), "ndcg_at_5": _mean(ndcgs), "n_cv": len(ndcgs), "n_pairs": pairs}
