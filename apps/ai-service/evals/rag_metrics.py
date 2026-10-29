"""Tinh recall@k theo nhom cho golden set RAG (NFR-AI-QUAL14). Ham thuan, khong goi mang."""
from collections import defaultdict
from typing import Dict, List, Sequence


def hit_at_k(retrieved: Sequence[str], relevant: Sequence[str], k: int) -> bool:
    """Truy van tinh la trung neu bat ky qa_id dung nao nam trong top-k (da khu trung)."""
    return bool(set(retrieved[:k]) & set(relevant))


def reciprocal_rank(retrieved: Sequence[str], relevant: Sequence[str], k: int) -> float:
    """1 / hang cua qa_id dung dau tien trong top-k; khong co thi 0 (MRR do thu tu, recall chi do co/khong)."""
    for i, key in enumerate(retrieved[:k], start=1):
        if key in relevant:
            return 1.0 / i
    return 0.0


def recall_by_group(results: List[Dict], k: int) -> Dict[str, Dict[str, float]]:
    """results: [{group, retrieved: [qa_id...], relevant: [qa_id...]}] -> {group: {n, hits, recall, mrr}} + 'all'."""
    buckets: Dict[str, List[float]] = defaultdict(list)
    for r in results:
        rr = reciprocal_rank(r["retrieved"], r["relevant"], k)
        buckets[r["group"]].append(rr)
        buckets["all"].append(rr)
    out = {}
    for g, h in buckets.items():
        hits = sum(1 for x in h if x > 0)
        out[g] = {"n": len(h), "hits": hits, "recall": round(hits / len(h), 3), "mrr": round(sum(h) / len(h), 3)}
    return out
