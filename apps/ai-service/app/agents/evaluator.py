"""Evaluator LLM (FR-AI-030..032): cham mot cau tra loi theo rubric, roi code hau kiem (evaluation_checks).

Luong: precheck bang code (dont_know ngan, manipulation) -> luot voice: doi thuat ngu STT phien am (stt_terms)
-> goi LLM qua LlmGateway (structured output) -> hau kiem quote / tran band -> Evaluation. LLM loi sau retry thi
dung mock heuristic va danh dau degraded (luot khong tinh diem, BRU-05) de phien khong chet.
"""
import asyncio
import logging
import time
from dataclasses import replace
from typing import List, Optional, Tuple

import openai

from .. import mock_evaluator
from ..evaluator_source_checks import (SourcedPoint, check_sources, confidence, merge_misconceptions,
                                      refuted_by_reference, restates_reference, source_blocks,
                                      split_tool_misconceptions)
from ..evaluation_checks import (MAX_COVERED, apply_caps, build_evaluation, is_term_list, matched_key_points,
                                 precheck_answer, quote_in_answer, slug_tags, supports_point, zero_evaluation)
from ..llm.errors import ConfigError, LlmError
from ..llm.gateway import LlmGateway
from ..llm.usage import CallRecord, UsageCollector
from ..models_interview import Evaluation, Evidence, TopicTurn  # noqa: F401  (re-export cho evals)
from ..prompts.store import PromptStore
from ..stt_terms import normalize_stt_terms_with_map, restore_quote
from .evaluator_lookup_call import call_with_lookup
from .evaluator_input import EvaluationInput, all_snippets, build_messages, cited_sources, source_refs  # noqa: F401
from .evaluator_output_models import (CoveredPoint, EvaluatorOutput, EvaluatorOutputV4, RawBands,  # noqa: F401
                                      SourcedCoveredPoint, uses_sources)

log = logging.getLogger("ai_service.evaluator")
DEFAULT_PROMPT_VERSION = "v8"


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
    if inp.reference_answer:  # truoc khi gop: cau dung cua dap an khong duoc chan technical_accuracy (luat 4)
        kept = [m for m in misconceptions if not restates_reference(m, inp.reference_answer)]
        if len(kept) < len(misconceptions):
            log.info("evaluator_reference_restated turn=%d dropped=%d", inp.turn_number,
                     len(misconceptions) - len(kept))
        misconceptions = kept
    sourced = isinstance(out, EvaluatorOutputV4)
    contradicted: List[SourcedPoint] = []
    ids = [i for i, _ in source_blocks(all_snippets(inp), inp.reference_answer)]
    if sourced:
        verified, contradicted, invalid = check_sources(verified, ids)
        # dap an chuan bac bo: hieu sai (luat 4 chan technical_accuracy); quote sai lam roi y nay thi LLM van
        # ghi no trong misconceptions (prompt v4 luat 12), code chi bo trung
        misconceptions = merge_misconceptions(refuted_by_reference(contradicted, inp.reference_answer), misconceptions)
        if invalid or contradicted:
            log.info("evaluator_sources turn=%d invalid_ids=%d contradicted=%d", inp.turn_number, invalid,
                     len(contradicted))
    tool_only: List[str] = []  # hieu sai chi dua vao chunk cong cu: vao bao cao, khong chan diem (luat H4)
    if sourced and inp.tool_base_ids is not None:
        misconceptions, tool_only = split_tool_misconceptions(misconceptions, contradicted, inp.tool_base_ids)
        if tool_only:
            log.info("evaluator_tool_misconception_uncapped turn=%d n=%d", inp.turn_number, len(tool_only))
    if inp.reference_answer:
        # cau tu kho chi hoi mot khia canh cua topic: tran completeness theo so y co quote (1 y -> 2, 3+ y -> 4)
        # thay vi ti le key_points cua ca topic (se ep diem thap du tra loi du dap an chuan)
        verified_kp, total_kp = (min(len(verified) + 1, 4) if verified else 0), 4
    else:
        verified_kp = matched_key_points([c.point for c in verified], inp.topic.key_points)
        total_kp = len(inp.topic.key_points)
    bands = apply_caps(out.scores.model_dump(), answer_type=out.answer_type, verified_key_points=verified_kp,
                       total_key_points=total_kp, has_misconception=bool(misconceptions),
                       turn_kind=inp.turn_kind,
                       term_list=inp.phase != "intro" and is_term_list(inp.answer))  # intro duoc liet ke stack
    return build_evaluation(
        turn_number=inp.turn_number, answer_type=out.answer_type, bands=bands,
        covered_points=[c.point for c in verified], missing_points=out.missing_points,
        misconceptions=[*misconceptions, *tool_only],
        evidence=[Evidence(claim=c.point[:150], quote=c.quote[:100], source_ids=c.source_ids,
                           support=c.support if sourced else None) for c in verified],
        # tag do code sinh tu y da kiem chung (v2 khong bat LLM viet tag: bot token o duong nong)
        strength_tags=slug_tags(c.point for c in verified), gap_tags=slug_tags(out.missing_points),
        follow_up_focus=out.follow_up_focus, confidence=confidence(verified, bool(ids)) if sourced else None,
        sources=cited_sources([*verified, *contradicted], inp) if sourced else [])


class LlmEvaluator:
    agent = "evaluator"
    supports_lookup = True  # turn_evaluation: chi agent LLM duoc tra cuu kho (EVALUATOR_TOOLS)

    def __init__(self, gateway: LlmGateway, prompts: Optional[PromptStore] = None, prompt_version: str = None):
        self._gateway = gateway
        # ghim v8 (ban da do): them prompt moi vao thu muc khong tu dong doi Evaluator, chi EVALUATOR_PROMPT_VERSION
        self._prompt = (prompts or PromptStore()).get(self.agent, prompt_version or DEFAULT_PROMPT_VERSION)

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
        # QUAL17: thuat ngu STT phien am ve dang dung; LLM, hau kiem quote va fallback cung thay mot ban
        raw_answer = inp.answer
        normalized, replaced = normalize_stt_terms_with_map(inp.answer) if inp.spoken else (inp.answer, [])
        if replaced:
            log.info("evaluator_stt_terms turn=%d", inp.turn_number)
            inp = replace(inp, answer=normalized)
        started = time.perf_counter()
        try:
            sourced = uses_sources(self._prompt.version)
            schema = EvaluatorOutputV4 if sourced else EvaluatorOutput
            if inp.lookup is not None and sourced:  # phase 03: 1 ngan sach 10 s cho vong lap tra cuu + fallback
                result, inp = await call_with_lookup(
                    self._gateway, self.agent, self._prompt.text, lambda text, i: build_messages(text, i, True),
                    schema, self._prompt.version, inp, collector, started)
            else:
                result = await self._gateway.complete(self.agent, build_messages(self._prompt.text, inp, sourced),
                                                      schema, prompt_version=self._prompt.version,
                                                      collector=collector)
        except (LlmError, ConfigError, openai.APIError) as err:  # openai.APIError: loi API con lai sau khi het retry
            log.warning("evaluator_degraded turn=%d error=%s", inp.turn_number, type(err).__name__)
            if collector is not None:
                # thoi gian cho truoc khi fallback (het han ~10 s): khong ghi thi latency_ms va /metrics bao 0
                collector.add(CallRecord(self.agent, "mock-heuristic", prompt_version=self._prompt.version,
                                         fallback="evaluator_mock_heuristic",
                                         latency_ms=int((time.perf_counter() - started) * 1000)))
            fallback = mock_evaluator.evaluate(inp.answer, inp.question, inp.topic, inp.turn_kind, inp.turn_number)
            return None, fallback.model_copy(update={"degraded": True})
        ev = await asyncio.to_thread(postcheck, result.data, inp)
        if replaced:  # evidence.quote trich nguyen van ban ghi, khong phai ban da doi thuat ngu
            ev.evidence = [e.model_copy(update={"quote": restore_quote(e.quote, raw_answer, replaced)})
                           for e in ev.evidence]
        return result.data, ev.model_copy(update={"prompt_version": self._prompt.version})
