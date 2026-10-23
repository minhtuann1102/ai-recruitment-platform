"""Planner LLM (FR-AI-020, 021, 023): khung phase do code tinh, LLM chon topic va viet key_points, code kiem.

Luong: goi LLM -> dung InterviewPlan (code gan id, thoi gian) -> plan_validator -> sai thi gui loi lai repair
1 lan -> van sai hoac LLM loi thi dung plan du phong cua mock_planner (plan sai khong bao gio den Interviewer).
"""
import asyncio
import json
import logging
from typing import List, Literal, Optional, Tuple

import openai
from pydantic import BaseModel, ValidationError

from .. import mock_planner
from ..llm.errors import ConfigError, LlmError
from ..llm.gateway import LlmGateway
from ..llm.usage import CallRecord, UsageCollector
from ..models_cv import CvProfile
from ..models_interview import InterviewPlan, PlanPhase, PlanTopic
from ..models_jd import JdProfile
from ..plan_template import PlanTemplate, build_template
from ..plan_validator import validate_plan
from ..prompts.store import UNTRUSTED_NOTICE, PromptStore, wrap_untrusted
from .registry import agent_mode, cached_llm_agent

log = logging.getLogger("ai_service.planner")


class LlmPlanTopic(BaseModel):
    title: str
    source: Literal["cv", "catalog", "scenario", "generic"]
    cv_ref: Optional[str]
    catalog_ref: Optional[str]
    objective: str
    key_points: List[str]
    start_difficulty: int


class LlmPlanPhase(BaseModel):
    phase: Literal["intro", "technical", "scenario"]
    topics: List[LlmPlanTopic]


class PlannerOutput(BaseModel):
    level_note: Optional[str]
    phases: List[LlmPlanPhase]


def to_plan(out: PlannerOutput, tpl: PlanTemplate, cv: Optional[CvProfile] = None, catalog=None
            ) -> Tuple[Optional[InterviewPlan], List[str]]:
    """Code gan id t1.., thoi gian theo khung, opening_hint/backup_question theo mau, cat do dai; loi schema
    (vd < 3 key_points) tra ve nhu loi plan."""
    projects = {p.id: p.name for p in cv.projects} if cv else {}
    try:
        n, phases = 0, []
        for ph in out.phases:
            topics = []
            for t in ph.topics:
                n += 1
                hint, backup = mock_planner.default_hints(t.source, t.title[:120], projects.get(t.cv_ref or ""))
                points = [k[:120] for k in t.key_points if k.strip()][:6]
                if len(points) < 3 and catalog is not None:  # LLM bo trong (do 22/10: 5/9 phien) -> code bu, khong goi lai
                    extra = mock_planner.default_key_points(t.source, t.catalog_ref, catalog)
                    points = (points + [p for p in extra if p not in points])[:6]
                topics.append(PlanTopic(id=f"t{n}", **{**t.model_dump(), "title": t.title[:120],
                                                       "key_points": points,
                                                       "objective": t.objective[:300], "opening_hint": hint,
                                                       "backup_question": backup}))
            phases.append(PlanPhase(phase=ph.phase, time_budget_min=tpl.minutes.get(ph.phase, 1), topics=topics))
        return InterviewPlan(level_note=(out.level_note or None) and out.level_note[:200], phases=phases), []
    except ValidationError as err:
        return None, [f"{e['loc']}: {e['msg']}" for e in err.errors()[:5]]


def build_messages(system: str, *, track: str, level: str, duration: int, tpl: PlanTemplate, catalog,
                   cv: Optional[CvProfile], jd: Optional[JdProfile]) -> List[dict]:
    data = {"track": track, "level": level, "duration_minutes": duration, "phase_template": tpl.as_prompt(),
            "difficulty": {"start": tpl.start, "min": tpl.min_difficulty, "max": tpl.max_difficulty},
            "catalog": [{"id": t.id, "title": t.title, "key_concepts": t.key_concepts} for t in catalog.topics_for(level)],
            "scenario_catalog": [{"id": s.id, "title": s.title} for s in catalog.scenarios_for(level)],
            "jd_priority": jd.priority_topic_ids() if jd else []}
    cv_json = cv.model_dump_json() if cv else "null"
    jd_json = json.dumps([r.model_dump() for r in jd.requirements], ensure_ascii=False) if jd else "[]"
    user = "\n\n".join([json.dumps(data, ensure_ascii=False), wrap_untrusted("cv_profile", cv_json),
                        wrap_untrusted("jd_requirements", jd_json)])
    return [{"role": "system", "content": f"{system}\n\n{UNTRUSTED_NOTICE}"}, {"role": "user", "content": user}]


class LlmPlanner:
    agent = "planner"
    deadline_s = 22.0  # chua 3 s cho Interviewer va RAG truoc moc 25 s

    def __init__(self, gateway: LlmGateway, prompts: Optional[PromptStore] = None, prompt_version: str = None):
        self._gateway = gateway
        self._prompt = (prompts or PromptStore()).get(self.agent, prompt_version)

    async def plan(self, track: str, level: str, duration: int, cv: Optional[CvProfile], jd: Optional[JdProfile],
                   collector: Optional[UsageCollector] = None) -> InterviewPlan:
        catalog, tpl = mock_planner.load_track(track), build_template(level, duration)
        check = {"topic_ids": {t.id for t in catalog.topics_for(level)},
                 "scenario_ids": {s.id for s in catalog.scenarios_for(level)}, "cv": cv,
                 "jd_priority": jd.must_topic_ids() if jd else ()}
        messages = build_messages(self._prompt.text, track=track, level=level, duration=duration, tpl=tpl,
                                  catalog=catalog, cv=cv, jd=jd)
        errors: List[str] = []

        async def attempts() -> Optional[InterviewPlan]:
            nonlocal messages, errors
            for attempt in range(2):  # lan 2 = repair voi danh sach loi (FR-AI-021)
                result = await self._gateway.complete(self.agent, messages, PlannerOutput,
                                                      prompt_version=self._prompt.version, collector=collector)
                plan, errors = to_plan(result.data, tpl, cv, catalog)
                errors = errors or validate_plan(plan, tpl, **check)
                if not errors:
                    return plan
                log.info("planner_invalid attempt=%d errors=%d", attempt + 1, len(errors))
                messages = messages + [
                    {"role": "assistant", "content": result.data.model_dump_json()},
                    {"role": "user", "content": "Plan chưa hợp lệ:\n- " + "\n- ".join(errors[:10]) +
                     "\nTrả lại toàn bộ plan đã sửa, đúng schema."}]
            return None

        try:
            # Han tong cho ca retry + repair: contract cho event dau cua /api/start <= 25 s (D06 muc 7.4)
            plan = await asyncio.wait_for(attempts(), timeout=self.deadline_s)
            if plan is not None:
                return plan
        except asyncio.TimeoutError:
            errors = ["timeout"]
        except (LlmError, ConfigError, openai.APIError) as err:
            errors = [type(err).__name__]
        log.warning("planner_fallback reason=%s", errors[:1])
        if collector is not None:
            collector.add(CallRecord(self.agent, "rule-based", prompt_version=self._prompt.version,
                                     fallback="planner_fallback_plan"))
        return mock_planner.build_plan(track, level, duration, cv, jd)


class MockPlanner:
    async def plan(self, track, level, duration, cv, jd, collector=None) -> InterviewPlan:
        return mock_planner.build_plan(track, level, duration, cv, jd)


def get_planner():
    if agent_mode("planner") == "mock":
        return MockPlanner()
    return cached_llm_agent("planner", LlmPlanner) or MockPlanner()
