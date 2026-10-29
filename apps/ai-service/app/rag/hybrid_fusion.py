"""Hybrid RAG (plans/261029-1415-hybrid-grounded-rag, Phase 01): gop nhieu danh sach xep hang bang Reciprocal Rank
Fusion co trong so.

RRF chi dung thu hang, khong dung diem goc, nen gop duoc diem cosine (vector), BM25 (tu khoa) va danh sach theo
topic_id (khong co diem) ma khong can chuan hoa. diem(chunk) = tong w / (RRF_K + hang) tren cac danh sach co no.
"""
from dataclasses import replace
from typing import Dict, List, Optional, Sequence

from .models import Chunk

RRF_K = 60  # hang so chuan cua RRF (Cormack 2009): giam anh huong cua vai hang dau mot danh sach
LEXICAL_WEIGHT = 0.5  # do 29/10: BM25 w=0.5 tot nhat (w=1.0 keo MRR xuong); vector va topic_id giu 1.0


def rrf(lists: Sequence[Sequence[Chunk]], weights: Optional[Sequence[float]] = None, k: int = RRF_K) -> List[Chunk]:
    """Gop cac danh sach (moi danh sach da xep hang tot -> kem) theo dedup_key; tra chunk co diem = diem RRF.
    Giu ban ghi dau tien gap cua moi khoa (thu tu danh sach truyen vao quyet dinh noi dung khi trung)."""
    weights = weights or [1.0] * len(lists)
    scores: Dict[str, float] = {}
    first: Dict[str, Chunk] = {}
    for ranked, weight in zip(lists, weights):
        seen = set()
        for rank, chunk in enumerate(ranked, start=1):
            key = chunk.dedup_key
            if key in seen:  # mot danh sach chi tinh moi khoa mot lan (hang tot nhat)
                continue
            seen.add(key)
            scores[key] = scores.get(key, 0.0) + weight / (k + rank)
            first.setdefault(key, chunk)
    order = sorted(scores, key=lambda key: (-scores[key], key))
    return [replace(first[key], score=round(scores[key], 6)) for key in order]
