"""Evaluator LLM (FR-AI-030..032): cham mot cau tra loi theo rubric, roi code hau kiem (evaluation_checks).

Luong: precheck bang code (dont_know ngan, manipulation) -> goi LLM qua LlmGateway (structured output)
-> hau kiem quote / tran band -> Evaluation. LLM loi sau retry thi dung mock heuristic va danh dau
degraded (luot khong tinh diem, BRU-05) de phien khong chet.
"""
import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import List, Literal, Optional, Tuple

import openai
from pydantic import BaseModel

from .. import mock_evaluator
from ..evaluator_source_checks import (SourcedPoint, check_sources, confidence, label, merge_misconceptions,
                                      refuted_by_reference, source_blocks)
from ..evaluation_checks import (MAX_COVERED, apply_caps, build_evaluation, matched_key_points, precheck_answer,
                                 quote_in_answer, slug_tags, supports_point, zero_evaluation)
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
    follow_up_focus: Optional[str]


class SourcedCoveredPoint(CoveredPoint):
    # mac dinh chi cho che do json_object (khong strict) chiu duoc model bo truong; strict_schema bat buoc moi truong
    source_ids: List[str] = []
    support: Literal["supported", "contradicted", "no_source"] = "no_source"


class EvaluatorOutputV4(EvaluatorOutput):
    """v4 (Phase 03a): moi y covered ghi tai lieu doi chieu (S1.., R) va muc ung ho."""
    covered: List[SourcedCoveredPoint]


def uses_sources(prompt_version: str) -> bool:
    return int(prompt_version.lstrip("v") or 0) >= 4


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
    reference_answer: str = ""  # cap Q&A chuan trong kho khi cau vua hoi lay tu kho (question_bank)
    turn_snippets: List[str] = field(default_factory=list)  # Phase 02: chunk theo cau vua hoi + cau tra loi


def build_messages(system_prompt: str, inp: EvaluationInput, with_ids: bool = False) -> List[dict]:
    """Phan tinh (rubric, anchor) o system de huong prompt caching; du lieu nguoi dung boc <untrusted>.
    with_ids (v4): moi tai lieu doi chieu co id [S1].. / [R] de Evaluator trich nguon."""
    data = {"level": inp.level, "phase": inp.phase, "difficulty": inp.difficulty, "turn_kind": inp.turn_kind,
            "topic": {"title": inp.topic.title, "objective": inp.topic.objective,
                      "key_points": inp.topic.key_points},
            "question": inp.question}
    turns = "\n".join(f"Q: {t.q}\nA: {t.a}" for t in inp.topic_turns[-5:]) or "(không có)"
    # snippet cua topic (luc start) truoc, chunk theo luot sau; prompt coi ca hai la tai lieu doi chieu (luat 8)
    blocks = source_blocks(all_snippets(inp), inp.reference_answer)
    texts = [label(i, t) if with_ids else t for i, t in blocks]
    reference = texts.pop() if inp.reference_answer else "(không có)"
    snippets = "\n---\n".join(texts) or "(không có)"
    user = "\n\n".join([json.dumps(data, ensure_ascii=False), wrap_untrusted("topic_turns", turns),
                        wrap_untrusted("reference_snippets", snippets),
                        wrap_untrusted("reference_answer", reference),
                        wrap_untrusted("answer", inp.answer)])
    return [{"role": "system", "content": f"{system_prompt}\n\n{UNTRUSTED_NOTICE}"},
            {"role": "user", "content": user}]


def all_snippets(inp: EvaluationInput) -> List[str]:
    # snippet cua topic (luc start) truoc, chunk theo luot sau: thu tu nay quyet dinh id S1..Sn
    return [*inp.topic.reference_snippets, *inp.turn_snippets]


def _sourced(c: CoveredPoint) -> SourcedPoint:
    return SourcedPoint(c.point, c.quote, list(getattr(c, "source_ids", [])), getattr(c, "support", "no_source"))


def postcheck(out: EvaluatorOutput, inp: EvaluationInput) -> Evaluation:
    """Ap luat khat khe bang code len output LLM (docs 05 muc 6.2); v4 kiem them trich nguon."""
    candidates = out.covered[:MAX_COVERED]
    verified = [_sourced(c) for c in candidates
                if supports_point(c.quote, c.point) and quote_in_answer(c.quote, inp.answer)]
    dropped = len(candidates) - len(verified)
    if dropped:
        log.info("evaluator_quote_dropped turn=%d dropped=%d", inp.turn_number, dropped)
    misconceptions = [m for m in out.misconceptions if m.strip()]
    sourced = isinstance(out, EvaluatorOutputV4)
    ids = [i for i, _ in source_blocks(all_snippets(inp), inp.reference_answer)]
    if sourced:
        verified, contradicted, invalid = check_sources(verified, ids)
        # dap an chuan bac bo: hieu sai (luat 4 chan technical_accuracy); quote sai lam roi y nay thi LLM van
        # ghi no trong misconceptions (prompt v4 luat 12), code chi bo trung
        misconceptions = merge_misconceptions(refuted_by_reference(contradicted), misconceptions)
        if invalid or contradicted:
            log.info("evaluator_sources turn=%d invalid_ids=%d contradicted=%d", inp.turn_number, invalid,
                     len(contradicted))
    if inp.reference_answer:
        # cau tu kho chi hoi mot khia canh cua topic: tran completeness theo so y co quote (1 y -> 2, 3+ y -> 4)
        # thay vi ti le key_points cua ca topic (se ep diem thap du tra loi du dap an chuan)
        verified_kp, total_kp = (min(len(verified) + 1, 4) if verified else 0), 4
    else:
        verified_kp = matched_key_points([c.point for c in verified], inp.topic.key_points)
        total_kp = len(inp.topic.key_points)
    bands = apply_caps(out.scores.model_dump(), answer_type=out.answer_type, verified_key_points=verified_kp,
                       total_key_points=total_kp, has_misconception=bool(misconceptions),
                       turn_kind=inp.turn_kind)
    return build_evaluation(
        turn_number=inp.turn_number, answer_type=out.answer_type, bands=bands,
        covered_points=[c.point for c in verified], missing_points=out.missing_points,
        misconceptions=misconceptions,
        evidence=[Evidence(claim=c.point[:150], quote=c.quote[:100], source_ids=c.source_ids,
                           support=c.support if sourced else None) for c in verified],
        # tag do code sinh tu y da kiem chung (v2 khong bat LLM viet tag: bot token o duong nong)
        strength_tags=slug_tags(c.point for c in verified), gap_tags=slug_tags(out.missing_points),
        follow_up_focus=out.follow_up_focus, confidence=confidence(verified, bool(ids)) if sourced else None)


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
            sourced = uses_sources(self._prompt.version)
            result = await self._gateway.complete(self.agent, build_messages(self._prompt.text, inp, sourced),
                                                  EvaluatorOutputV4 if sourced else EvaluatorOutput,
                                                  prompt_version=self._prompt.version,
                                                  collector=collector)
        except (LlmError, ConfigError, openai.APIError) as err:  # openai.APIError: loi API con lai sau khi het retry
            log.warning("evaluator_degraded turn=%d error=%s", inp.turn_number, type(err).__name__)
            if collector is not None:
                collector.add(CallRecord(self.agent, "mock-heuristic", prompt_version=self._prompt.version,
                                         fallback="evaluator_mock_heuristic"))
            fallback = mock_evaluator.evaluate(inp.answer, inp.question, inp.topic, inp.turn_kind, inp.turn_number)
            return None, fallback.model_copy(update={"degraded": True})
        return result.data, await asyncio.to_thread(postcheck, result.data, inp)
