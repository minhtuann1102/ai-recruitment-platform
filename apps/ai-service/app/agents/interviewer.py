"""Interviewer (FR-AI-037): dien dat dung mot cau hoi theo hanh dong orchestrator da chon, stream tung manh.

Interviewer khong quyet dinh gi: action, focus, topic do policy (code) chon. MockInterviewer dung mau co dinh
cua mock_interviewer, cung la cau du phong khi LLM loi (FR-AI-071).
"""
import asyncio
import json
import os
from dataclasses import dataclass, field
from typing import AsyncIterator, List, Optional

from .. import mock_interviewer
from ..llm.gateway import LlmGateway
from ..llm.usage import UsageCollector
from ..models_interview import PlanTopic
from ..prompts.store import UNTRUSTED_NOTICE, PromptStore, wrap_untrusted
from ..sse import chunk_tokens
from .registry import agent_mode, cached_llm_agent


@dataclass
class QuestionSpec:
    """Dau vao Interviewer (design 02 muc 3.3.4): chi chua thu Interviewer can."""
    action: str  # ask_main | follow_up | hint | clarify | wrap_up
    phase: str
    topic: Optional[PlanTopic]
    difficulty: int
    focus: Optional[str] = None
    last_question: str = ""
    last_answer: str = ""
    first_turn: bool = False
    phase_changed: bool = False
    asked_on_topic: List[str] = field(default_factory=list)
    time_hint: str = "normal"  # normal | hurry


def fallback_question(spec: QuestionSpec) -> str:
    """Cau mau bang code: backup_question cua topic khi ask_main, mau co dinh cho cac hanh dong khac."""
    return mock_interviewer.compose(spec.action, spec.topic, spec.phase, spec.focus, spec.last_question,
                                    spec.first_turn, spec.phase_changed)


def build_messages(system: str, spec: QuestionSpec) -> List[dict]:
    topic = spec.topic
    data = {"action": spec.action, "phase": spec.phase, "difficulty": spec.difficulty, "focus": spec.focus,
            "first_turn": spec.first_turn, "time_hint": spec.time_hint,
            "topic": {"title": topic.title, "objective": topic.objective, "opening_hint": topic.opening_hint}
            if topic else None,
            "transition": {"phase_changed": spec.phase_changed} if spec.action == "ask_main" else None,
            "last_question": spec.last_question, "asked_questions_on_topic": spec.asked_on_topic[-5:]}
    user = json.dumps(data, ensure_ascii=False) + "\n\n" + wrap_untrusted("last_answer", spec.last_answer[:2000])
    return [{"role": "system", "content": f"{system}\n\n{UNTRUSTED_NOTICE}"}, {"role": "user", "content": user}]


class LlmInterviewer:
    agent = "interviewer"

    def __init__(self, gateway: LlmGateway, prompts: Optional[PromptStore] = None, prompt_version: str = None):
        self._gateway = gateway
        self._prompt = (prompts or PromptStore()).get(self.agent, prompt_version)

    def stream(self, spec: QuestionSpec, collector: Optional[UsageCollector] = None) -> AsyncIterator[str]:
        return self._gateway.stream(self.agent, build_messages(self._prompt.text, spec),
                                    prompt_version=self._prompt.version, collector=collector)


class MockInterviewer:
    async def stream(self, spec: QuestionSpec, collector: Optional[UsageCollector] = None) -> AsyncIterator[str]:
        delay = float(os.getenv("MOCK_STREAM_DELAY_MS", "0")) / 1000  # mo phong do tre de thu qua APISIX
        for tok in chunk_tokens(fallback_question(spec)):
            if delay:
                await asyncio.sleep(delay)
            yield tok


def get_interviewer():
    if agent_mode("interviewer") == "mock":
        return MockInterviewer()
    return cached_llm_agent("interviewer", LlmInterviewer) or MockInterviewer()
