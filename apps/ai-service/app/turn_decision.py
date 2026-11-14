"""Chon quyet dinh cho mot luot next-turn (docs/ai-service/03 muc 4): forced -> (hybrid: de xuat LLM da kiem) ->
decide() -> low_performance_stop. Tach khoi turn_engine; ket qua ghi lai nguon quyet dinh de TurnInfo / sim do duoc.

Thu tu uu tien khong doi: dieu kien thoi gian / turn cap (forced) va low_performance_stop luon o tren LLM.
"""
from dataclasses import dataclass
from typing import List, Optional, Tuple

from . import metrics
from .agent_notes import apply_notes, notes_enabled
from .early_stop import low_performance_stop
from .models_interview import CandidateState, Evaluation, InterviewPlan, NextTurnRequest, PlanTopic
from .policy import Decision, classify, decide
from .replan import attempt_swap
from .cv_text import has_injection
from .policy_hybrid import SENSITIVE, policy_mode, proposed_label, safe_reason, validate_decision
from .time_budget import phase_deadline_s


@dataclass
class DecisionTrace:
    """dec: quyet dinh cuoi. Cac truong con lai chi co khi POLICY_MODE=hybrid (rules thi None, TurnInfo giu mac dinh);
    proposed / policy la hanh dong TRUOC apply_action (next_topic chua doi thanh ask_main) va truoc low_performance."""
    dec: Decision
    decided_by: Optional[str] = None      # llm | policy | forced
    proposed: Optional[str] = None        # hanh dong LLM de xuat
    policy: Optional[str] = None          # hanh dong decide() (luat)
    overrule_reason: Optional[str] = None
    action_reason: Optional[str] = None   # ly do LLM da qua kiem (PII / injection thi None); chi khi decided_by = llm
    swap: Optional[str] = None            # phase 05: applied | ly do bac, khi LLM de xuat doi topic; "applied" thi state da doi


def time_hint(elapsed_s: int, plan: InterviewPlan, phase: str) -> str:
    """hurry khi con < 20% thoi gian phase (design 02 muc 3.3.4)."""
    ph = next((p for p in plan.phases if p.phase == phase), None)
    if ph is None:
        return "normal"
    left = phase_deadline_s(plan, phase) - elapsed_s
    return "hurry" if left < 0.2 * ph.time_budget_min * 60 else "normal"


def forced_decision(forced: Tuple[str, str], state: CandidateState) -> Decision:
    if forced[0] == "wrap_up":
        state.end_reason = forced[1]
    return Decision(forced[0], -1 if forced[1] == "two_dont_know" else 0, None,
                    f"{forced[1]} -> {forced[0]} (điều kiện ưu tiên, design 03 §4.4)")


def choose_decision(ev: Evaluation, proposal, state: CandidateState, phase: str, topic: PlanTopic,
                    topics: List[Tuple[str, PlanTopic]], pos: int, req: NextTurnRequest,
                    forced: Optional[Tuple[str, str]], plan: Optional[InterviewPlan] = None) -> DecisionTrace:
    """forced: ket qua forced_transition (khac "end", da xu ly o turn_engine). proposal: output V9 / V10 cua Evaluator hoac
    None. plan = plan thuc te: co thi (hybrid) xet de xuat doi topic cua v10 sau khi quyet dinh cuoi la next_topic va
    khong forced; doi that thi state.swaps / state.topics[i] da sua, turn_engine tinh lai topics."""
    hybrid = policy_mode() == "hybrid"
    proposed = proposed_label(proposal) if hybrid else None
    if forced:
        trace = DecisionTrace(forced_decision(forced, state), "forced" if hybrid else None, proposed)
    else:
        # covered: y da neu trong ca topic (record_evaluation da gop ca luot nay), de khong hoi lai y da tra loi
        ts = next(t for t in state.topics if t.id == topic.id)
        is_scn = phase == "scenario"
        rules = decide(ev, state, req.level, is_scn, topic, ts.focus_used, ts.covered)
        trace = DecisionTrace(rules, None, proposed, rules.action if hybrid else None)
        if hybrid:
            trace.dec, trace.decided_by, trace.overrule_reason = validate_decision(
                proposal, ev, state, req.level, is_scn, topic, ts, rules, req.answer)
            if trace.decided_by == "llm":  # ly do chi ghi khi quyet dinh that su la cua LLM
                trace.action_reason = safe_reason(proposal.action_reason)
    dec = trace.dec
    if dec.action in ("next_topic", "next_phase") and low_performance_stop(state, topics, pos, req.level, dec.action):
        state.end_reason = "low_performance"
        trace.dec = Decision("wrap_up", 0, None, "low_performance -> wrap_up (3 topic technical yếu liên tiếp)")
        trace.decided_by = "forced" if hybrid else None
        trace.overrule_reason = None
    if hybrid:
        metrics.record_policy_decision(trace.decided_by, trace.overrule_reason)
        if plan is not None:
            # chi doi khi quyet dinh khong forced, khong phai sensitive_kind (manipulation / injection: ung vien khong
            # duoc chon topic bi bo) va chinh LLM de xuat next_topic; con lai bi bac (forced / low_performance: not_applicable)
            gate = "untrusted" if trace.overrule_reason == "sensitive_kind" else \
                trace.dec.action if not forced and trace.proposed == "next_topic" else "not_applicable"
            trace.swap = attempt_swap(proposal, state, plan, topics, pos, phase, gate,
                                      time_hint(req.elapsed_seconds, plan, phase), req.turn_number)
            if trace.swap:
                metrics.record_replan_swap(trace.swap)
    if hybrid and notes_enabled():  # phase 07: ghi chu sau quyet dinh; luot sensitive / injection (cung forced) la untrusted
        apply_notes(state, proposal, req.turn_number, topic.id,
                    untrusted=trace.overrule_reason == "sensitive_kind" or classify(ev) in SENSITIVE
                    or has_injection(req.answer))
    return trace
