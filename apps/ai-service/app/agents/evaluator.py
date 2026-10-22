"""Evaluator LLM (FR-AI-030..032): cham mot cau tra loi theo rubric, roi code hau kiem (evaluation_checks).

Luong: precheck bang code (dont_know ngan, manipulation) -> goi LLM qua LlmGateway (structured output)
-> hau kiem quote / tran band -> Evaluation. LLM loi sau retry thi dung mock heuristic va danh dau
degraded (luot khong tinh diem, BRU-05) de phien khong chet.
"""
import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import openai
from pydantic import BaseModel

from .. import mock_evaluator
from ..evaluation_checks import (MAX_COVERED, apply_caps, build_evaluation, matched_key_points, precheck_answer,
                                 quote_in_answer, supports_point, zero_evaluation)
from ..llm.errors import ConfigError, LlmError
from ..llm.gateway import LlmGateway
from ..llm.usage import CallRecord, UsageCollector
from ..models_common import AnswerType
from ..models_interview import Evaluation, Evidence, PlanTopic, TopicTurn
from ..prompts.store import UNTRUSTED_NOTICE, PromptStore, wrap_untrusted

log = logging.getLogger("ai_service.evaluator")


# Schema gui cho LLM: khong rang buoc min/max (che do strict khong ho tro het); code tu kep va cat.
class CoveredPoint(BaseModel):
    point: str
    quote: str


class RawBands(BaseModel):
    technical_accuracy: int
    completeness: int
    extensibility: int
    relevance: int


class EvaluatorOutput(BaseModel):
    answer_type: AnswerType
    covered: List[CoveredPoint]
    missing_points: List[str]
    misconceptions: List[str]
    scores: RawBands
    strength_tags: List[str]
    gap_tags: List[str]
    follow_up_focus: Optional[str]


@dataclass
class EvaluationInput:
    level: str
    phase: str
    topic: PlanTopic
    difficulty: int
    turn_kind: str
    turn_number: int
    question: str
    answer: str
    topic_turns: List[TopicTurn] = field(default_factory=list)


def build_messages(system_prompt: str, inp: EvaluationInput) -> List[dict]:
    """Phan tinh (rubric, anchor) o system de huong prompt caching; du lieu nguoi dung boc <untrusted>."""
    data = {"level": inp.level, "phase": inp.phase, "difficulty": inp.difficulty, "turn_kind": inp.turn_kind,
            "topic": {"title": inp.topic.title, "objective": inp.topic.objective,
                      "key_points": inp.topic.key_points},
            "question": inp.question}
    turns = "\n".join(f"Q: {t.q}\nA: {t.a}" for t in inp.topic_turns[-5:]) or "(không có)"
    snippets = "\n---\n".join(inp.topic.reference_snippets) or "(không có)"
    user = "\n\n".join([json.dumps(data, ensure_ascii=False), wrap_untrusted("topic_turns", turns),
                        wrap_untrusted("reference_snippets", snippets), wrap_untrusted("answer", inp.answer)])
    return [{"role": "system", "content": f"{system_prompt}\n\n{UNTRUSTED_NOTICE}"},
            {"role": "user", "content": user}]


def postcheck(out: EvaluatorOutput, inp: EvaluationInput) -> Evaluation:
    """Ap luat khat khe bang code len output LLM (docs 05 muc 6.2)."""
    candidates = out.covered[:MAX_COVERED]
    verified = [c for c in candidates if supports_point(c.quote, c.point) and quote_in_answer(c.quote, inp.answer)]
    dropped = len(candidates) - len(verified)
    if dropped:
        log.info("evaluator_quote_dropped turn=%d dropped=%d", inp.turn_number, dropped)
    bands = apply_caps(out.scores.model_dump(), answer_type=out.answer_type,
                       verified_key_points=matched_key_points([c.point for c in verified], inp.topic.key_points),
                       total_key_points=len(inp.topic.key_points), has_misconception=any(m.strip() for m in out.misconceptions),
                       turn_kind=inp.turn_kind)
    return build_evaluation(
        turn_number=inp.turn_number, answer_type=out.answer_type, bands=bands,
        covered_points=[c.point for c in verified], missing_points=out.missing_points,
        misconceptions=[m for m in out.misconceptions if m.strip()],
        evidence=[Evidence(claim=c.point[:150], quote=c.quote[:100]) for c in verified],
        strength_tags=out.strength_tags, gap_tags=out.gap_tags, follow_up_focus=out.follow_up_focus)


class LlmEvaluator:
    agent = "evaluator"

    def __init__(self, gateway: LlmGateway, prompts: Optional[PromptStore] = None, prompt_version: str = None):
        self._gateway = gateway
        self._prompt = (prompts or PromptStore()).get(self.agent, prompt_version)

    @property
    def prompt_version(self) -> str:
        return self._prompt.version

    async def evaluate(self, inp: EvaluationInput, collector: Optional[UsageCollector] = None) -> Evaluation:
        return (await self.evaluate_with_raw(inp, collector))[1]

    async def evaluate_with_raw(self, inp: EvaluationInput, collector: Optional[UsageCollector] = None
                                ) -> Tuple[Optional[EvaluatorOutput], Evaluation]:
        """Tra ca output LLM truoc hau kiem (None neu khong goi LLM) de evals do ti le evidence hop le."""
        code_type = precheck_answer(inp.answer)
        if code_type:  # FR-AI-032: khong goi LLM
            return None, zero_evaluation(inp.turn_number, code_type)
        try:
            result = await self._gateway.complete(self.agent, build_messages(self._prompt.text, inp),
                                                  EvaluatorOutput, prompt_version=self._prompt.version,
                                                  collector=collector)
        except (LlmError, ConfigError, openai.APIError) as err:  # openai.APIError: loi API con lai sau khi het retry
            log.warning("evaluator_degraded turn=%d error=%s", inp.turn_number, type(err).__name__)
            if collector is not None:
                collector.add(CallRecord(self.agent, "mock-heuristic", prompt_version=self._prompt.version,
                                         fallback="evaluator_mock_heuristic"))
            fallback = mock_evaluator.evaluate(inp.answer, inp.question, inp.topic, inp.turn_kind, inp.turn_number)
            return None, fallback.model_copy(update={"degraded": True})
        return result.data, await asyncio.to_thread(postcheck, result.data, inp)
