"""Khoi `requirements` cua bao cao theo JD (FR-AI-056, BR-23, BRU-19). Thuan code.

Moi yeu cau JD xuat hien dung mot lan: `assessed` (co luot duoc cham o topic map tu yeu cau), `not_assessed`
(chua hoi - KHONG coi la yeu), `out_of_catalog` (khong map duoc ve catalog). Khong ket luan tuyen hay khong.
"""
from typing import Dict, List, Optional

from .models_interview import FinalizeTurn, InterviewPlan
from .models_jd import JdProfile


def _band(score: float) -> str:
    return "exceeds" if score >= 8.5 else "meets" if score >= 7.0 else "near" if score >= 5.0 else "below"


def requirements_block(jd: Optional[JdProfile], plan: InterviewPlan, scored: List[FinalizeTurn],
                       all_turns: List[FinalizeTurn]) -> Optional[Dict]:
    if jd is None or not jd.requirements:
        return None
    plan_topic_by_ref = {t.catalog_ref: t.id for ph in plan.phases for t in ph.topics if t.catalog_ref}
    degraded_topics = {t.topic_id for t in all_turns if t.evaluation and t.evaluation.degraded}
    items = []
    for r in jd.requirements:
        item = {"id": r.id, "text": r.text, "kind": r.kind, "status": "not_assessed", "score": None, "band": None,
                "evidence_turns": [], "confidence": None}
        if r.out_of_catalog or not r.topic_ids:
            item["status"] = "out_of_catalog"
            items.append(item)
            continue
        plan_ids = {plan_topic_by_ref[t] for t in r.topic_ids if t in plan_topic_by_ref}
        turns = [t for t in scored if t.topic_id in plan_ids]
        if turns:
            score = round(sum(t.evaluation.turn_score_10 for t in turns) / len(turns), 1)
            low = len(turns) < 2 or bool(plan_ids & degraded_topics)
            item.update(status="assessed", score=score, band=_band(score),
                        evidence_turns=[t.turn_number for t in turns], confidence="low" if low else "medium")
        items.append(item)
    assessed = sum(1 for i in items if i["status"] == "assessed")
    return {"assessed": assessed, "total": len(items),
            "summary": f"Đã đánh giá {assessed}/{len(items)} yêu cầu của JD. Yêu cầu chưa được hỏi không bị "
                       "tính là điểm yếu; báo cáo không kết luận tuyển hay không tuyển.",
            "items": items}
