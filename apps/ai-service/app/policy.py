"""Policy chon hanh dong tiep theo, thuan code (docs/ai-service/04 muc 5.4). Luat dau tien khop thang."""
from dataclasses import dataclass
from typing import Optional, Sequence, Set

from .models_common import LEVEL_CONFIG
from .focus import deepen_focus, gap_focus, hint_focus
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


@dataclass
class Budget:
    left: int        # luot follow-up / hint / clarify con lai trong topic
    hinted: bool     # da goi y trong topic
    clarifies: int   # so lan clarify da dung


def action_budget(state: CandidateState, level: str, is_scenario: bool) -> Budget:
    """Ngan sach hanh dong con lai trong topic; dung chung cho decide() va policy lai (policy_hybrid)."""
    cfg = LEVEL_CONFIG[level]
    c = state.counters
    return Budget((cfg["max_fu_scn"] if is_scenario else cfg["max_fu"]) - c.follow_ups, c.hints >= 1, c.clarifies)


def allowed_actions(b: Budget) -> Set[str]:
    """Hanh dong con hop le theo ngan sach: next_topic luon; cac hanh dong o lai topic can left > 0."""
    out = {"next_topic"}
    if b.left > 0:
        out.add("follow_up")
        if not b.hinted:
            out.add("hint")
        if b.clarifies < 1:
            out.add("clarify")
    return out


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
    b = action_budget(state, level, is_scenario)
    left, hinted, c = b.left, b.hinted, state.counters
    kind = classify(ev)
    gap = gap_focus(ev, topic, used_focus, covered)

    def d(action, delta, rule, f=None):
        return Decision(action, delta, f, f"{kind} -> {action} (luật {rule})")

    if kind == "manipulation":
        return d("follow_up", 0, 1, gap) if left > 0 and gap else d("next_topic", 0, 1)
    if kind in ("off_topic", "asks_clarification"):
        return d("clarify", 0, 2) if c.clarifies < 1 and left > 0 else d("next_topic", 0, 3)
    if kind in ("dont_know", "weak"):
        rule = 4 if kind == "dont_know" else 6
        if not hinted and left > 0:
            return d("hint", -1, rule, hint_focus(ev, used_focus, covered))
        return d("next_topic", -1, rule + 1)
    if kind == "ok_degraded":
        return d("next_topic", 0, 9)
    if kind == "ok":
        if left > 0 and ev.missing_points and gap:
            return d("follow_up", 0, 8, gap)
        return d("next_topic", 0, 9)
    deeper = deepen_focus(ev, topic, used_focus, covered)
    return d("follow_up", 1, 10, deeper) if left > 0 and deeper else d("next_topic", 1, 11)
