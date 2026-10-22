"""Orchestrator MOCK cho start / next-turn: state machine thuan code, Planner/Evaluator/Interviewer gia lap.

Luong moi luot (docs/ai-service/03): Evaluator cham -> cap nhat state -> policy chon action -> Interviewer dien dat.
"""
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .agents.evaluator import EvaluationInput
from .agents.evaluator_provider import Evaluator, get_evaluator
from .api_error import ApiError
from .llm.usage import UsageCollector
from .mock_evaluator import fold
from .mock_interviewer import compose
from .agents.planner import get_planner
from .mock_planner import load_track
from .plan_snippets import attach_reference_snippets, get_retriever
from .models_common import LEVEL_CONFIG
from .models_interview import (CandidateState, Evaluation, InterviewPlan, NextTurnRequest, PlanTopic,
                               StartRequest, TopicState, TurnInfo)
from .policy import Decision, decide
from .state_update import apply_action, record_evaluation
from .time_budget import forced_transition

_KIND = {"ask_main": "main", "follow_up": "follow_up", "hint": "hint", "clarify": "clarify",
         "wrap_up": "main", "end": "main"}  # next_topic / next_phase deu thanh ask_main sau apply_action
_AGENT = {"follow_up": "deepen", "hint": "keep_difficulty", "clarify": "keep_difficulty"}


@dataclass
class TurnResult:
    question: Optional[str]
    turn: Optional[TurnInfo]
    state: CandidateState
    plan: InterviewPlan
    evaluation: Optional[Evaluation]
    session_end: bool
    meta: Dict


def flat_topics(plan: InterviewPlan) -> List[Tuple[str, PlanTopic]]:
    return [(ph.phase, t) for ph in plan.phases for t in ph.topics]


def _norm(q: str) -> str:
    return re.sub(r"\s+", " ", fold(q)).strip()[:160]


def _meta(phase: str, topic_pos: int, total: int, action: str, turn_number: int) -> Dict:
    return {"turn_number": turn_number, "phase": phase, "topic_index": topic_pos, "topic_total": total,
            "action": action}


async def start_session(req: StartRequest, planner=None, collector: Optional[UsageCollector] = None,
                        retriever=None) -> TurnResult:
    """Planner (LLM hoac mock, co plan du phong) -> gan reference_snippets (RAG, neu bat) -> cau hoi dau."""
    planner = planner or get_planner()
    plan = await planner.plan(req.track, req.level, req.duration_minutes, req.cv_profile, req.jd_profile, collector)
    plan = await attach_reference_snippets(plan, load_track(req.track), retriever or get_retriever())
    topics = flat_topics(plan)
    lo, hi = LEVEL_CONFIG[req.level]["bounds"]
    first_phase, first = topics[0]
    state = CandidateState(
        phase=first_phase, topic_index=1, active_topic_id=first.id,
        current_difficulty=max(lo, min(hi, first.start_difficulty)), difficulty_bounds={"min": lo, "max": hi},
        turn_count=1, topics=[TopicState(id=t.id, status="active" if i == 0 else "pending")
                              for i, (_, t) in enumerate(topics)])
    q = compose("ask_main", first, first_phase, None, "", True, False)
    state.asked_questions.append(_norm(q))
    state.topics[0].turns.append(1)
    turn = TurnInfo(turn_number=1, phase=first_phase, topic_id=first.id, turn_kind="main", action="ask_main",
                    agent_decision="switch_topic", difficulty=state.current_difficulty)
    return TurnResult(q, turn, state, plan, None, False, _meta(first_phase, 1, len(topics), "ask_main", 1))


async def next_turn(req: NextTurnRequest, evaluator: Optional[Evaluator] = None,
                    collector: Optional[UsageCollector] = None) -> TurnResult:
    plan, state = req.plan, req.state.model_copy(deep=True)
    topics = flat_topics(plan)
    if state.phase == "done":
        raise ApiError(409, "session_invalid_state", "Phiên đã kết thúc")
    if state.phase == "wrap_up":  # tra loi cau wrap-up xong thi dong phien, khong cham
        state.phase, state.end_reason = "done", state.end_reason or "plan_complete"
        return TurnResult(None, None, state, plan, None, True, {})
    pos = next((i for i, (_, t) in enumerate(topics) if t.id == state.active_topic_id), None)
    if pos is None:
        raise ApiError(422, "invalid_request", "active_topic_id khong co trong plan")
    phase, topic = topics[pos]

    ev = await (evaluator or get_evaluator()).evaluate(EvaluationInput(
        level=req.level, phase=phase, topic=topic, difficulty=state.current_difficulty, turn_kind=req.turn_kind,
        turn_number=req.turn_number, question=req.question, answer=req.answer, topic_turns=req.topic_turns),
        collector)
    record_evaluation(state, ev, req.turn_number)
    forced = forced_transition(req.elapsed_seconds, state, plan, phase)
    if forced and forced[0] == "end":  # qua han cung: ket thuc ngay, khong hoi them (FR-AI-035)
        state.phase, state.active_topic_id, state.end_reason = "done", None, forced[1]
        return TurnResult(None, None, state, plan, ev, True, {})
    if forced:
        if forced[0] == "wrap_up":
            state.end_reason = forced[1]
        dec = Decision(forced[0], -1 if forced[1] == "two_dont_know" else 0, None,
                       f"{forced[1]} -> {forced[0]} (điều kiện ưu tiên, design 03 §4.4)")
    else:
        dec = decide(ev, state, req.level, phase == "scenario", topic.key_points[0])

    action, phase_changed, next_pos = apply_action(state, topics, pos, dec.action, dec.difficulty_delta,
                                                   req.elapsed_seconds)
    n_phase, n_topic = (topics[next_pos] if next_pos is not None else ("wrap_up", None))
    question = compose(action, n_topic, n_phase, dec.focus, req.question, False, phase_changed)
    state.asked_questions = (state.asked_questions + [_norm(question)])[-30:]
    state.turn_count += 1
    if n_topic:
        next(t for t in state.topics if t.id == n_topic.id).turns.append(req.turn_number + 1)
    info = TurnInfo(turn_number=req.turn_number + 1, phase=n_phase, topic_id=n_topic.id if n_topic else None,
                    turn_kind=_KIND[action], action=action, agent_decision=_AGENT.get(action, "switch_topic"),
                    difficulty=state.current_difficulty, reasoning=dec.reasoning)
    meta = _meta(n_phase, (next_pos or 0) + 1 if n_topic else len(topics), len(topics), action, info.turn_number)
    return TurnResult(question, info, state, plan, ev, False, meta)
