"""Reporter LLM (FR-AI-052..054): chi viet nhan xet tren bao cao da co diem do code tinh.

Reporter chi nhan ket qua da qua Evaluator (khong nhan nguyen van cau tra loi). Code kiem: evidence_turns phai
la luot co that; diem manh chi giu khi cac luot dan chung co diem cao; bo chuoi nghi injection; khong co URL.
LLM loi sau retry thi tra bao cao chi co diem + nhan xet mau, status = partial (FR-AI-054).
"""
import json
import logging
import re
from typing import Dict, List, Literal, Optional

import openai
from pydantic import BaseModel

from .. import cv_text
from ..language_check import wrong_language
from ..llm.errors import ConfigError, LlmError
from ..llm.gateway import LlmGateway
from ..llm.usage import CallRecord, UsageCollector
from ..prompts.store import UNTRUSTED_NOTICE, PromptStore, wrap_untrusted
from ..report_scoring import build_report, scored_turns
from ..models_interview import FinalizeRequest
from .registry import agent_mode, cached_llm_agent

log = logging.getLogger("ai_service.reporter")
STRENGTH_MIN_SCORE = 6.0  # luot dan chung cho diem manh phai dat it nhat muc nay (chong "diem manh sai")
_URL = re.compile(r"https?://\S+|www\.\S+", re.I)


class Point(BaseModel):
    point: str
    evidence_turns: List[int]


class Improvement(BaseModel):
    point: str
    why: str
    evidence_turns: List[int]


class StudyItem(BaseModel):
    topic: str
    priority: Literal["high", "medium"]
    actions: List[str]


class IdComment(BaseModel):
    id: str
    comment: str


class ReporterOutput(BaseModel):
    summary: str
    strengths: List[Point]
    improvements: List[Improvement]
    study_plan: List[StudyItem]
    topic_comments: List[IdComment]
    turn_comments: List[IdComment]


def _text(value: str, limit: int) -> str:
    """Chuoi rong = bo muc LLM, giu ban code: nghi injection hoac sai ngon ngu (cau tieng Anh tron cau / khong dau)."""
    value = _URL.sub("", value).strip()
    return "" if cv_text.has_injection(value) or wrong_language(value) else value[:limit]


def reporter_input(report: Dict, req: FinalizeRequest) -> Dict:
    """Chi ket qua da cham (khong nguyen van tra loi, FR-AI-052)."""
    titles = {t.id: t.title for ph in req.plan.phases for t in ph.topics}
    turns = [{"turn_number": t.turn_number, "topic": titles.get(t.topic_id, ""), "turn_kind": t.turn_kind,
              "scores": t.evaluation.scores_10.model_dump(), "covered": t.evaluation.covered_points,
              "missing": t.evaluation.missing_points, "misconceptions": t.evaluation.misconceptions}
             for t in scored_turns(req)]
    return {"level": req.level, "track": req.track, "overall": report["overall"], "sections": report["sections"],
            "criteria": report["criteria"], "topics": report["topics"], "turns": turns,
            "requirements": report.get("requirements")}


def merge_comments(report: Dict, out: ReporterOutput) -> Dict:
    """Ghep nhan xet vao bao cao; diem giu nguyen. Muc khong con evidence hop le thi bi bo."""
    turn_score = {t["turn_number"]: sum(t["scores"].values()) / 4 for t in report["turns"]}
    valid = lambda turns: [n for n in dict.fromkeys(turns) if n in turn_score]  # noqa: E731
    strengths = []
    for s in out.strengths[:3]:
        ev = valid(s.evidence_turns)
        if ev and all(turn_score[n] >= STRENGTH_MIN_SCORE for n in ev) and _text(s.point, 200):
            strengths.append({"point": _text(s.point, 200), "evidence_turns": ev})
    improvements = [{"point": _text(i.point, 200), "why": _text(i.why, 300), "evidence_turns": valid(i.evidence_turns)}
                    for i in out.improvements[:3] if valid(i.evidence_turns) and _text(i.point, 200)]
    study = [{"topic": _text(s.topic, 150), "priority": s.priority,
              "actions": [a for a in (_text(x, 200) for x in s.actions[:3]) if a], "resources": []}
             for s in out.study_plan[:3] if _text(s.topic, 150)]
    topic_c = {c.id: _text(c.comment, 300) for c in out.topic_comments}
    turn_c = {c.id: _text(c.comment, 300) for c in out.turn_comments}
    merged = dict(report)
    merged["overall"] = {**report["overall"], "summary": _text(out.summary, 600) or report["overall"]["summary"]}
    # muc LLM bi loai het (evidence sai) thi giu ban do code dung, khong de bao cao trong
    merged.update(strengths=strengths or report["strengths"], improvements=improvements or report["improvements"],
                  study_plan=study or report["study_plan"])
    merged["topics"] = [{**t, "comment": topic_c.get(t["topic_id"]) or t["comment"]} for t in report["topics"]]
    merged["turns"] = [{**t, "comment": turn_c.get(str(t["turn_number"])) or t["comment"]} for t in report["turns"]]
    return merged


class LlmReporter:
    agent = "reporter"

    def __init__(self, gateway: LlmGateway, prompts: Optional[PromptStore] = None, prompt_version: str = None):
        self._gateway = gateway
        self._prompt = (prompts or PromptStore()).get(self.agent, prompt_version)

    async def report(self, req: FinalizeRequest, collector: Optional[UsageCollector] = None) -> Dict:
        base = build_report(req)
        data = json.dumps(reporter_input(base, req), ensure_ascii=False)
        messages = [{"role": "system", "content": f"{self._prompt.text}\n\n{UNTRUSTED_NOTICE}"},
                    {"role": "user", "content": wrap_untrusted("scored_session", data)}]
        try:
            result = await self._gateway.complete(self.agent, messages, ReporterOutput,
                                                  prompt_version=self._prompt.version, collector=collector)
        except (LlmError, ConfigError, openai.APIError) as err:
            log.warning("reporter_partial error=%s", type(err).__name__)
            if collector is not None:
                collector.add(CallRecord(self.agent, "rule-based", fallback="reporter_partial"))
            return {**base, "status": "partial"}
        report = merge_comments(base, result.data)
        report["meta"] = {**report["meta"], "prompt_versions": {**report["meta"]["prompt_versions"],
                                                                "reporter": self._prompt.version}}
        report["metadata"] = {"model": result.record.model, "latency_ms": result.record.latency_ms}
        return report


class MockReporter:
    async def report(self, req: FinalizeRequest, collector: Optional[UsageCollector] = None) -> Dict:
        return build_report(req)


def get_reporter():
    if agent_mode("reporter") == "mock":
        return MockReporter()
    return cached_llm_agent("reporter", LlmReporter) or MockReporter()
