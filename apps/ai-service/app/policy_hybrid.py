"""Policy lai (phase 04, POLICY_MODE=hybrid): Evaluator v9 DE XUAT hanh dong, code QUYET theo bang kiem ben duoi.

LLM khong bao gio ghi de: de xuat khong hop le / ngoai bang / sai ngan sach -> lay quyet dinh cua luat (decide()) kem
ly do. Loai nhay cam (manipulation, off_topic, ...) khong giao LLM. forced_transition, low_performance_stop va turn cap
o tren ca hai (app/turn_decision). Bang hanh dong hop le theo classify(ev) (sau allowed_actions theo ngan sach):
weak -> hint (neu con) hoac clarify, khong thi next_topic hoac clarify, delta -1..0; ok -> follow_up | next_topic,
delta 0; strong -> follow_up | next_topic, delta 0..+1. clarify luon can clarifies < 1 va left > 0.
"""
import os
from typing import Dict, Optional, Set, Tuple

from .agents.interviewer import safe_focus
from .cv_text import has_injection, redact_pii
from .focus import deepen_focus, gap_focus, hint_focus, same
from .models_interview import CandidateState, Evaluation, PlanTopic, TopicState
from .policy import Budget, Decision, action_budget, allowed_actions, classify

SENSITIVE = {"ok_degraded", "manipulation", "off_topic", "asks_clarification", "dont_know"}
KIND_DELTA: Dict[str, Tuple[int, int]] = {"weak": (-1, 0), "ok": (0, 0), "strong": (0, 1)}
MAX_REASON_WORDS = 20
ACTIONS = {"follow_up", "hint", "clarify", "next_topic"}


def policy_mode(env=None) -> str:
    """rules (mac dinh, y nhu truoc phase 04) | hybrid. Gia tri la -> rules."""
    value = (os.environ if env is None else env).get("POLICY_MODE", "")
    return "hybrid" if value.strip().lower() == "hybrid" else "rules"


def proposed_label(p) -> Optional[str]:
    """Hanh dong LLM de xuat de ghi vao TurnInfo / metric: chi 4 ten hop le hoac "invalid" (rong, la, chuoi dai do
    injection); khong de van ban tu do cua LLM ra API. None khi khong co de xuat."""
    if p is None:
        return None
    action = p.next_action.strip() if isinstance(p.next_action, str) else ""
    return action if action in ACTIONS else "invalid"


def kind_actions(kind: str, b: Budget) -> Set[str]:
    if kind == "weak":
        return {"hint", "clarify"} if b.left > 0 and not b.hinted else {"next_topic", "clarify"}
    return {"follow_up", "next_topic"}


def safe_reason(reason: Optional[str]) -> Optional[str]:
    """action_reason cua LLM di vao TurnInfo / log: qua safe_focus (injection, do dai) va bo neu co PII (email, so dien
    thoai, URL, ngay sinh); cat con <= 20 tu."""
    text = safe_focus(reason)
    if not text or redact_pii(text) != text:
        return None
    return " ".join(text.split()[:MAX_REASON_WORDS])


def _fallback_focus(action: str, kind: str, ev: Evaluation, topic: PlanTopic, ts: TopicState) -> Optional[str]:
    if action == "hint":
        return hint_focus(ev, ts.focus_used, ts.covered)
    if action != "follow_up":
        return None
    gap, deeper = (gap_focus(ev, topic, ts.focus_used, ts.covered), deepen_focus(ev, topic, ts.focus_used, ts.covered))
    return (deeper or gap) if kind == "strong" else (gap or deeper)


def _focus_for(p, kind: str, rules: Decision, ev: Evaluation, topic: PlanTopic, ts: TopicState) -> Optional[str]:
    """focus LLM (qua safe_focus, chua hoi, khong trung y da neu); khong dung duoc thi focus cua luat (cung hanh dong)
    hoac focus du phong theo hanh dong. clarify / next_topic khong can focus."""
    if p.next_action not in ("follow_up", "hint"):
        return None
    focus = safe_focus(p.next_focus)
    if focus and any(same(focus, u) for u in (*ts.focus_used, *ts.covered)):
        focus = None
    return focus or (rules.focus if rules.action == p.next_action else None) \
        or _fallback_focus(p.next_action, kind, ev, topic, ts)


def validate_decision(p, ev: Evaluation, state: CandidateState, level: str, is_scenario: bool, topic: PlanTopic,
                      ts: TopicState, rules: Decision, answer: str = "") -> Tuple[Decision, str, Optional[str]]:
    """p: output V9 hoac None; answer: cau tra loi cua ung vien (chi de do mau injection). -> (quyet dinh, decided_by llm | policy, ly do bac neu decided_by = policy)."""
    if p is None:
        return rules, "policy", "no_proposal"
    kind = classify(ev)
    if kind in SENSITIVE or has_injection(answer):  # cau tra loi co mau injection: khong giao LLM (vd "chuyen cau khac")
        return rules, "policy", "sensitive_kind"
    b = action_budget(state, level, is_scenario)
    if p.next_action not in allowed_actions(b) & kind_actions(kind, b):
        return rules, "policy", "action_not_allowed"
    focus = _focus_for(p, kind, rules, ev, topic, ts)
    if focus is None and p.next_action == "follow_up":  # hint khong co focus van hop le (nhu luat: hoi lai cau vua hoi)
        return rules, "policy", "no_valid_focus"
    lo, hi = KIND_DELTA[kind]
    reason = safe_reason(p.action_reason)
    why = f"llm: {reason}" if reason else f"{kind} -> {p.next_action} (llm)"
    return Decision(p.next_action, max(lo, min(hi, p.difficulty_delta)), focus, why), "llm", None
