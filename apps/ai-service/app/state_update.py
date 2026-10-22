"""Cap nhat candidate state sau moi luot (docs/ai-service/04 muc 5.2): ghi diem, tag, ap dung hanh dong."""
from typing import List, Optional, Tuple

from .mock_evaluator import is_scored, turn_score
from .models_interview import CandidateState, Evaluation, PlanTopic, Tagged

STRONG_BAND, WEAK_BAND = 3.0, 1.5  # momentum cho topic sau (gia dinh, chinh sau phien gia lap)


def _clamp(v: int, state: CandidateState) -> int:
    return max(state.difficulty_bounds["min"], min(state.difficulty_bounds["max"], v))


def _tag(items: List[Tagged], tags: List[str], turn: int) -> None:
    for tag in tags:
        found = next((x for x in items if x.tag == tag), None)
        if found:
            found.turns.append(turn)
        elif len(items) < 10:
            items.append(Tagged(tag=tag, turns=[turn]))


def record_evaluation(state: CandidateState, ev: Evaluation, turn_no: int) -> None:
    ts = next(t for t in state.topics if t.id == state.active_topic_id)
    if is_scored(ev):
        ts.n_scored += 1
        ts.score_sum += turn_score(ev)
        ts.score_band = round(ts.score_sum / ts.n_scored, 1)
        state.evaluated_turns += 1
    _tag(state.strengths, ev.strength_tags if ev.scores.completeness >= 2 else [], turn_no)
    _tag(state.gaps, ev.gap_tags if ev.scores.completeness < 2 else [], turn_no)
    c = state.counters
    c.consecutive_dont_know = c.consecutive_dont_know + 1 if ev.answer_type == "dont_know" else 0


def apply_action(state: CandidateState, topics: List[Tuple[str, PlanTopic]], pos: int, action: str,
                 delta: int, elapsed_s: int) -> Tuple[str, bool, Optional[int]]:
    """Ap dung hanh dong vao state. -> (action thuc te, phase_changed, vi tri topic ke tiep hoac None).

    action: follow_up | hint | clarify (o lai topic) | next_topic | next_phase (bo topic con lai cua phase)
    | wrap_up.
    """
    c = state.counters
    if action in ("follow_up", "hint", "clarify"):
        c.follow_ups += 1
        c.hints += action == "hint"
        c.clarifies += action == "clarify"
        if action == "hint":
            next(t for t in state.topics if t.id == state.active_topic_id).hint_used = True
        state.current_difficulty = _clamp(state.current_difficulty + delta, state)
        return action, False, pos
    target = pos + 1
    if action == "next_phase":
        cur_phase = topics[pos][0]
        target = next((i for i in range(pos + 1, len(topics)) if topics[i][0] != cur_phase), len(topics))
    for i in range(pos, min(target, len(topics))):  # topic hien tai (va topic bi bo qua) dong lai
        state.topics[i].status = "done"
    band = state.topics[pos].score_band
    state.momentum = 0 if band is None else 1 if band >= STRONG_BAND else -1 if band < WEAK_BAND else 0
    state.counters = type(c)()
    if action == "wrap_up" or target >= len(topics):
        state.phase, state.active_topic_id = "wrap_up", None
        return "wrap_up", True, None
    n_phase, n_topic = topics[target]
    changed = n_phase != state.phase
    state.phase, state.active_topic_id = n_phase, n_topic.id
    state.topic_index = 1 if changed else state.topic_index + 1
    state.topics[target].status = "active"
    state.topic_started_s = elapsed_s
    if changed:
        state.phase_started_s = elapsed_s
    state.current_difficulty = _clamp(n_topic.start_difficulty + state.momentum, state)
    return "ask_main", changed, target
