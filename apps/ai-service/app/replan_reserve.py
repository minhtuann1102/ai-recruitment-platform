"""Chon topic du phong luc start cho lap lai ke hoach (phase 05), thuan code, sau Planner va prefer_covered.

Reserve = topic catalog cua level chua co trong plan (toi da 2, id `alt{n}`: khong dung `r*` cua yeu cau JD / resource
bao cao, khong dung `t{n}` cua plan). Co cau trong kho o do kho bat dau (khi biet coverage), xep theo JD uu tien roi do
trung CV nhu Planner. Plan khong con topic thua (vd fresher) -> khong co reserve -> khong lap lai ke hoach cho phien.
keep_ids = id topic plan map tu yeu cau JD: khong bao gio bi bo. Snippet + cau kho cua reserve duoc gan trong
attach_reference_snippets (chung han 5 s luc start).
"""
from typing import Optional

from .catalog.models import TrackCatalog
from .mock_planner import _rank_with_jd, catalog_topic
from .models_cv import CvProfile
from .models_interview import InterviewPlan, ReplanPool
from .models_jd import JdProfile
from .plan_bank_coverage import Coverage, bank_count
from .replan import replan_enabled

MAX_RESERVE = 2


def select_reserve(plan: InterviewPlan, catalog: TrackCatalog, level: str, coverage: Coverage,
                   cv: Optional[CvProfile], jd: Optional[JdProfile]) -> Optional[ReplanPool]:
    """None khi khong co topic du phong."""
    in_plan = {t.catalog_ref for ph in plan.phases for t in ph.topics if t.catalog_ref}
    start = next((t.start_difficulty for ph in plan.phases if ph.phase == "technical" for t in ph.topics), 2)
    spare = [t for t in catalog.topics_for(level) if t.id not in in_plan
             and (not coverage or bank_count(coverage, t.id, start) > 0)]  # coverage rong = khong biet: khong loc
    ranked = _rank_with_jd(spare, [s.name for s in cv.skills] if cv else [], jd)[:MAX_RESERVE]
    if not ranked:
        return None
    priority = set(jd.priority_topic_ids()) if jd else set()
    keep = [t.id for ph in plan.phases for t in ph.topics if t.catalog_ref in priority]
    return ReplanPool(reserve=[catalog_topic(f"alt{i}", t, level) for i, t in enumerate(ranked, 1)], keep_ids=keep)


def with_reserve(plan: InterviewPlan, catalog: TrackCatalog, level: str, coverage: Coverage,
                 cv: Optional[CvProfile], jd: Optional[JdProfile]) -> InterviewPlan:
    """Co tat (mac dinh) thi tra nguyen plan: plan.replan = None, output start y cu."""
    if not replan_enabled():
        return plan
    return plan.model_copy(update={"replan": select_reserve(plan, catalog, level, coverage, cv, jd)})
