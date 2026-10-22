"""Policy chon hanh dong tiep theo, thuan code (docs/ai-service/04 muc 5.4). Luat dau tien khop thang."""
from dataclasses import dataclass
from typing import Optional, Sequence

from .models_common import LEVEL_CONFIG
from .focus import clean_point, deepen_focus, gap_focus
from .models_interview import CandidateState, Evaluation, PlanTopic
from .mock_evaluator import turn_score

WEAK_BELOW = 1.5    # gia dinh mock, chinh sau khi chay ung vien gia lap
STRONG_FROM = 3.0


@dataclass
class Decision:
    action: str            # follow_up | hint | clarify | next_topic
    difficulty_delta: int
    focus: Optional[str]
    reasoning: str


def classify(ev: Evaluation) -> str:
    if ev.degraded:  # FR-AI-072: Evaluator loi han -> coi nhu ok, khong thieu y (khong hoi sau dua tren diem doan)
        return "ok_degraded"
    if ev.answer_type in ("manipulation", "off_topic", "asks_clarification", "dont_know"):
        return ev.answer_type
    s = turn_score(ev)
    return "weak" if s < WEAK_BELOW else "strong" if s >= STRONG_FROM else "ok"


def decide(ev: Evaluation, state: CandidateState, level: str, is_scenario: bool, topic: PlanTopic,
           used_focus: Sequence[str] = (), covered: Sequence[str] = ()) -> Decision:
    """used_focus: focus da hoi trong topic; covered: y ung vien da neu o cac luot truoc cua topic (app/focus.py)."""
    cfg = LEVEL_CONFIG[level]
    c = state.counters
    left = (cfg["max_fu_scn"] if is_scenario else cfg["max_fu"]) - c.follow_ups
    kind = classify(ev)
    gap = gap_focus(ev, topic, used_focus, covered)
    hinted = c.hints >= 1

    def d(action, delta, rule, f=None):
        return Decision(action, delta, f, f"{kind} -> {action} (luật {rule})")

    if kind == "manipulation":
        return d("follow_up", 0, 1, gap) if left > 0 and gap else d("next_topic", 0, 1)
    if kind in ("off_topic", "asks_clarification"):
        return d("clarify", 0, 2) if c.clarifies < 1 and left > 0 else d("next_topic", 0, 3)
    if kind in ("dont_know", "weak"):
        rule = 4 if kind == "dont_know" else 6
        if not hinted and left > 0:
            return d("hint", -1, rule, gap or clean_point(topic.key_points[0]))
        return d("next_topic", -1, rule + 1)
    if kind == "ok_degraded":
        return d("next_topic", 0, 9)
    if kind == "ok":
        if left > 0 and ev.missing_points and gap:
            return d("follow_up", 0, 8, gap)
        return d("next_topic", 0, 9)
    deeper = deepen_focus(ev, topic, used_focus, covered)
    return d("follow_up", 1, 10, deeper) if left > 0 and deeper else d("next_topic", 1, 11)
