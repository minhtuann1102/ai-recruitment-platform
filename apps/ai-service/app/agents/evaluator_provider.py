"""Chon Evaluator theo AGENT_EVALUATOR_MODE: mock (mac dinh, CI khong can khoa) hoac llm."""
import logging
from typing import Optional, Protocol

from .. import mock_evaluator
from ..llm.errors import ConfigError
from ..llm.gateway import get_gateway
from ..llm.usage import CallRecord, UsageCollector
from ..models_interview import Evaluation
from .evaluator import EvaluationInput, LlmEvaluator
from .registry import agent_mode

log = logging.getLogger("ai_service.evaluator")


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


def get_evaluator() -> Evaluator:
    """LlmEvaluator tao mot lan (doc prompt, gateway dung chung); mode doc lai moi lan de doi bang env."""
    global _llm
    if agent_mode("evaluator") == "mock":
        return MockEvaluator()
    if _llm is None:
        try:
            _llm = LlmEvaluator(get_gateway())
        except ConfigError as err:  # khong de loi cau hinh lam moi luot tra 500
            log.error("evaluator_config_error error=%s", err)
            return MockEvaluator(degraded=True)
    return _llm
