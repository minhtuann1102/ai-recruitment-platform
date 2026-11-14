"""Chon Evaluator theo AGENT_EVALUATOR_MODE: mock (mac dinh, CI khong can khoa) hoac llm."""
import logging
import os
from typing import Optional, Protocol

from .. import mock_evaluator
from ..llm.errors import ConfigError
from ..llm.gateway import get_gateway
from ..llm.usage import CallRecord, UsageCollector
from ..models_interview import Evaluation
from ..policy_hybrid import policy_mode
from .evaluator_output_models import uses_policy
from .evaluator import DEFAULT_PROMPT_VERSION, EvaluationInput, LlmEvaluator
from .registry import agent_mode

log = logging.getLogger("ai_service.evaluator")
HYBRID_PROMPT_VERSION = "v9"  # POLICY_MODE=hybrid: Evaluator de xuat hanh dong (phase 04); v10 them o phase 05


class Evaluator(Protocol):
    async def evaluate(self, inp: EvaluationInput, collector: Optional[UsageCollector] = None) -> Evaluation: ...


class MockEvaluator:
    """Boc heuristic tu khoa cua mock vao cung giao dien voi LlmEvaluator.

    degraded=True: dung thay LLM khi cau hinh LLM loi (vd thieu LLM_API_KEY); luot khong tinh diem (BRU-05).
    """

    def __init__(self, degraded: bool = False):
        self.degraded = degraded

    async def evaluate(self, inp: EvaluationInput, collector: Optional[UsageCollector] = None) -> Evaluation:
        ev = mock_evaluator.evaluate(inp.answer, inp.question, inp.topic, inp.turn_kind, inp.turn_number)
        if not self.degraded:
            return ev
        if collector is not None:
            collector.add(CallRecord("evaluator", "mock-heuristic", fallback="evaluator_config_error"))
        return ev.model_copy(update={"degraded": True})


_llm: Optional[LlmEvaluator] = None


def _warn_mismatch(prompt_version: str) -> None:
    """Mot lan moi lan tao Evaluator: POLICY_MODE va EVALUATOR_PROMPT_VERSION lech nhau thi hybrid khong co de xuat
    (moi luot no_proposal) hoac rules gui prompt v9 ma khong co policy_context."""
    v9 = uses_policy(prompt_version)
    if policy_mode() == "hybrid" and not v9:
        log.warning("policy_prompt_mismatch POLICY_MODE=hybrid nhung Evaluator %s khong de xuat hanh dong", prompt_version)
    elif policy_mode() != "hybrid" and v9:
        log.warning("policy_prompt_mismatch Evaluator %s can policy_context nhung POLICY_MODE != hybrid", prompt_version)


def get_evaluator() -> Evaluator:
    """LlmEvaluator tao mot lan (doc prompt, gateway dung chung); mode doc lai moi lan de doi bang env."""
    global _llm
    if agent_mode("evaluator") == "mock":
        return MockEvaluator()
    # EVALUATOR_PROMPT_VERSION (vd v3) de A/B ghi de; trong thi v8 (ghim) hoac v9 khi POLICY_MODE=hybrid.
    # Doi POLICY_MODE luc chay thi tao lai Evaluator (cache theo phien ban prompt).
    version = os.getenv("EVALUATOR_PROMPT_VERSION") or (HYBRID_PROMPT_VERSION if policy_mode() == "hybrid" else None)
    if _llm is not None and _llm.prompt_version != (version or DEFAULT_PROMPT_VERSION):
        _llm = None
    if _llm is None:
        try:
            _llm = LlmEvaluator(get_gateway(), prompt_version=version)
            _warn_mismatch(_llm.prompt_version)
        except (ConfigError, FileNotFoundError) as err:  # thieu khoa / EVALUATOR_PROMPT_VERSION sai: khong tra 500
            log.error("evaluator_config_error error=%s", err)
            return MockEvaluator(degraded=True)
    return _llm
