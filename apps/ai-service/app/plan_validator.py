"""Kiem plan bang code (FR-AI-021, design 02 muc 3.3.2): plan sai khong bao gio den Interviewer.

Tra ve danh sach loi (rong = hop le). Loi duoc gui lai Planner LLM de repair 1 lan; van sai thi dung plan
du phong cua mock_planner.
"""
from typing import List, Optional, Sequence, Set

from . import cv_text
from .models_cv import CvProfile
from .models_interview import InterviewPlan
from .plan_template import PlanTemplate

PHASES = ("intro", "technical", "scenario")
SOURCE_BY_PHASE = {"intro": {"cv", "generic"}, "technical": {"catalog"}, "scenario": {"scenario"}}


def cv_usable(cv: Optional[CvProfile]) -> bool:
    """Intro lay tu du an trong CV khi CV lien quan track va co du an (FR-AI-015, 020)."""
    return bool(cv and cv.track_relevance != "low" and cv.projects)


def validate_plan(plan: InterviewPlan, tpl: PlanTemplate, *, topic_ids: Set[str], scenario_ids: Set[str],
                  cv: Optional[CvProfile], jd_priority: Sequence[str] = ()) -> List[str]:
    """jd_priority: topic_id tu yeu cau JD bat buoc (must). Co topic JD hop level ma plan khong chon cai nao -> loi
    (FR-AI-023: >= 1 topic technical theo JD)."""
    errors: List[str] = []
    phases = [p.phase for p in plan.phases]
    if phases != list(PHASES):
        return [f"phases phai dung thu tu {list(PHASES)}, nhan {phases}"]
    cv_refs = {p.id for p in cv.projects} if cv else set()
    seen_refs: Set[str] = set()
    for ph in plan.phases:
        want = tpl.topics[ph.phase]
        if len(ph.topics) != want:
            errors.append(f"phase {ph.phase} can {want} topic, nhan {len(ph.topics)}")
        for t in ph.topics:
            where = f"{ph.phase}/{t.title[:40]}"
            if t.source not in SOURCE_BY_PHASE[ph.phase]:
                errors.append(f"{where}: source '{t.source}' khong hop le cho phase {ph.phase}")
            allowed = topic_ids if ph.phase == "technical" else scenario_ids if ph.phase == "scenario" else None
            if allowed is not None and t.catalog_ref not in allowed:
                errors.append(f"{where}: catalog_ref '{t.catalog_ref}' khong co trong catalog da dua")
            if t.catalog_ref and t.catalog_ref in seen_refs:
                errors.append(f"{where}: catalog_ref '{t.catalog_ref}' bi trung")
            seen_refs.add(t.catalog_ref or "")
            if ph.phase == "intro":
                if cv_usable(cv) and (t.source != "cv" or t.cv_ref not in cv_refs):
                    errors.append(f"{where}: co CV lien quan thi intro phai source=cv voi cv_ref trong {sorted(cv_refs)}")
                if not cv_usable(cv) and t.source != "generic":
                    errors.append(f"{where}: khong co CV lien quan thi intro phai source=generic")
            if not tpl.min_difficulty <= t.start_difficulty <= tpl.max_difficulty:
                errors.append(f"{where}: start_difficulty {t.start_difficulty} ngoai "
                              f"[{tpl.min_difficulty}, {tpl.max_difficulty}]")
            if not t.backup_question.strip():
                errors.append(f"{where}: thieu backup_question")
            texts = [t.title, t.objective, t.opening_hint, t.backup_question, *t.key_points]
            if any(cv_text.has_injection(x) for x in texts):
                errors.append(f"{where}: noi dung chua chi dan (nghi injection tu CV/JD)")
    wanted = [t for t in jd_priority if t in topic_ids]
    chosen = {t.catalog_ref for ph in plan.phases if ph.phase == "technical" for t in ph.topics}
    if wanted and not chosen & set(wanted):
        errors.append(f"technical phai co it nhat 1 topic theo JD trong {wanted[:3]}")
    return errors
