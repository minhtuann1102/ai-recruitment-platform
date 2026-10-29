"""Tai lieu cho study_plan (Phase 03b): lay tu cac nguon Evaluator v4 da trich o cac luot cua topic, KHONG do LLM viet.

Uu tien nguon bac bo y cua ung vien (contradicted: dung cho can on nhat) roi nguon ung ho, theo thu tu luot; con
thieu thi bu bang cau Q&A DE gan cho topic luc start (reference_sources): ung vien yeu it y dung nen it nguon duoc
trich (do 29/10: 5/10 phien khong co tai lieu nao). Bo trung theo ref (qa_id / id chunk). Reporter LLM chi chon id
r1.. trong danh sach nay; code tra ra title + url.
"""
from typing import Dict, List, Sequence

from .models_interview import FinalizeTurn, SourceRef

MAX_RESOURCES = 3


def topic_sources(turns: List[FinalizeTurn], topic_id: str, plan_sources: Sequence[SourceRef] = ()
                  ) -> List[SourceRef]:
    cited = [s for t in turns if t.topic_id == topic_id and t.evaluation for s in t.evaluation.sources]
    out: Dict[str, SourceRef] = {}
    for s in sorted(cited, key=lambda s: s.support != "contradicted"):  # sort on dinh: giu thu tu luot
        out.setdefault(s.ref, s)
    for s in plan_sources:
        out.setdefault(s.ref, s)
    return list(out.values())


def plan_sources(plan) -> Dict[str, List[SourceRef]]:
    return {t.id: list(t.reference_sources) for ph in plan.phases for t in ph.topics}


def resource(source: SourceRef) -> Dict:
    return {"title": source.title, "url": source.url}


def resource_catalog(turns: List[FinalizeTurn], topic_ids: List[str],
                     fallback: Dict[str, List[SourceRef]] = None) -> Dict[str, Dict]:
    """id r1.. -> {topic_id, title, url} cho cac topic (dua vao input Reporter; code doi id ra tai lieu)."""
    catalog: Dict[str, Dict] = {}
    for topic_id in topic_ids:
        for s in topic_sources(turns, topic_id, (fallback or {}).get(topic_id, ()))[:MAX_RESOURCES]:
            catalog[f"r{len(catalog) + 1}"] = {"topic_id": topic_id, **resource(s)}
    return catalog
