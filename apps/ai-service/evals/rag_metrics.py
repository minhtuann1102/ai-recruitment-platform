"""Tinh recall@k theo nhom cho golden set RAG (NFR-AI-QUAL14). Ham thuan, khong goi mang."""
from collections import defaultdict
from typing import Dict, List, Sequence


def hit_at_k(retrieved: Sequence[str], relevant: Sequence[str], k: int) -> bool:
    """Truy van tinh la trung neu bat ky qa_id dung nao nam trong top-k (da khu trung)."""
    return bool(set(retrieved[:k]) & set(relevant))


def recall_by_group(results: List[Dict], k: int) -> Dict[str, Dict[str, float]]:
    """results: [{group, retrieved: [qa_id...], relevant: [qa_id...]}] -> {group: {n, hits, recall}} + 'all'."""
    buckets: Dict[str, List[bool]] = defaultdict(list)
    for r in results:
        hit = hit_at_k(r["retrieved"], r["relevant"], k)
        buckets[r["group"]].append(hit)
        buckets["all"].append(hit)
    return {g: {"n": len(h), "hits": sum(h), "recall": round(sum(h) / len(h), 3)} for g, h in buckets.items()}
