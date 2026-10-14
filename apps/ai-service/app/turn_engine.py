"""Orchestrator MOCK cho start / next-turn: state machine thuan code, Planner/Evaluator/Interviewer gia lap.

Luong moi luot (docs/ai-service/03): Evaluator cham -> cap nhat state -> policy chon action -> Interviewer dien dat.
"""
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .api_error import ApiError
from .mock_evaluator import evaluate, fold, is_scored, turn_score
from .mock_interviewer import compose
from .mock_planner import build_plan
from .models_common import LEVEL_CONFIG, TURN_CAP
from .models_interview import (CandidateState, Evaluation, InterviewPlan, NextTurnRequest, PlanTopic,
                               StartRequest, Tagged, TopicState, TurnInfo)
from .policy import Decision, decide

_KIND = {"ask_main": "main", "follow_up": "follow_up", "hint": "hint", "clarify": "clarify",
         "wrap_up": "main", "end": "main"}
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


def _clamp(v: int, state: CandidateState) -> int:
    return max(state.difficulty_bounds["min"], min(state.difficulty_bounds["max"], v))


def _norm(q: str) -> str:
    return re.sub(r"\s+", " ", fold(q)).strip()[:160]


def _meta(phase: str, topic_pos: int, total: int, action: str, turn_number: int) -> Dict:
    return {"turn_number": turn_number, "phase": phase, "topic_index": topic_pos, "topic_total": total,
            "action": action}


def start_session(req: StartRequest) -> TurnResult:
    plan = build_plan(req.track, req.level, req.duration_minutes, req.cv_profile)
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


def _tag(items: List[Tagged], tags: List[str], turn: int) -> None:
    for tag in tags:
        found = next((x for x in items if x.tag == tag), None)
        if found:
            found.turns.append(turn)
        elif len(items) < 10:
            items.append(Tagged(tag=tag, turns=[turn]))


def _record(state: CandidateState, ev: Evaluation, turn_no: int) -> None:
    ts = next(t for t in state.topics if t.id == state.active_topic_id)
    if is_scored(ev):
        ts.n_scored += 1
        ts.score_sum += turn_score(ev)
        ts.score_band = round(ts.score_sum / ts.n_scored, 1)
        state.evaluated_turns += 1
    _tag(state.strengths, ev.strength_tags if ev.scores.completeness >= 2 else [], turn_no)
    _tag(state.gaps, ev.gap_tags if ev.scores.completeness < 2 else [], turn_no)
    state.counters.consecutive_dont_know = state.counters.consecutive_dont_know + 1 if ev.answer_type == "dont_know" else 0


def _end_reason(req: NextTurnRequest, state: CandidateState, plan: InterviewPlan) -> Optional[str]:
    if req.elapsed_seconds >= sum(p.time_budget_min for p in plan.phases) * 60:
        return "time_up"
    return "turn_cap" if state.turn_count >= TURN_CAP else None


def next_turn(req: NextTurnRequest) -> TurnResult:
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

    ev = evaluate(req.answer, req.question, topic, req.turn_kind, req.turn_number)
    _record(state, ev, req.turn_number)
    forced = _end_reason(req, state, plan)
    dec = decide(ev, state, req.level, phase == "scenario", topic.key_points[0])
    if forced:
        state.end_reason = forced
        dec = Decision("wrap_up", 0, None, f"{forced} -> wrap_up (điều kiện ưu tiên)")

    action, phase_changed, next_pos = _apply(state, topics, pos, dec)
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


def _apply(state: CandidateState, topics, pos: int, dec: Decision):
    """Ap dung Decision vao state. Tra ve (action, phase_changed, vi tri topic ke tiep hoac None)."""
    c = state.counters
    if dec.action in ("follow_up", "hint", "clarify"):
        c.follow_ups += 1
        c.hints += dec.action == "hint"
        c.clarifies += dec.action == "clarify"
        if dec.action == "hint":
            next(t for t in state.topics if t.id == state.active_topic_id).hint_used = True
        state.current_difficulty = _clamp(state.current_difficulty + dec.difficulty_delta, state)
        return dec.action, False, pos
    cur = next(t for t in state.topics if t.id == state.active_topic_id)
    cur.status = "done"
    band = cur.score_band
    state.momentum = 0 if band is None else 1 if band >= 3.0 else -1 if band < 1.5 else 0
    state.counters = type(c)()
    if dec.action == "wrap_up" or pos + 1 >= len(topics):
        state.phase, state.active_topic_id = "wrap_up", None
        return "wrap_up", True, None
    n_phase, n_topic = topics[pos + 1]
    changed = n_phase != state.phase
    state.phase, state.active_topic_id = n_phase, n_topic.id
    state.topic_index = 1 if changed else state.topic_index + 1
    next(t for t in state.topics if t.id == n_topic.id).status = "active"
    state.current_difficulty = _clamp(n_topic.start_difficulty + state.momentum, state)
    return "ask_main", changed, pos + 1
