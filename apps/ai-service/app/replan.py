"""Lap lai ke hoach giua buoi (phase 05, REPLAN_ENABLED + POLICY_MODE=hybrid): LLM (Evaluator v10) DE XUAT doi mot topic
technical `pending` lay topic du phong chuan bi san luc start; code KIEM va doi TAI CHO (cung vi tri) nen
`state.topics[i]` van khop `flat_topics(plan)[i]` va ngan sach thoi gian khong doi.

effective_plan(plan, state) dung mot lan o moi diem vao (next_turn, finalize, sim) de moi reader phia sau thay plan thuc
te. forced_transition / turn cap / low_performance_stop nam tren (turn_decision chi hoi doi khi khong forced, hanh dong
cuoi la next_topic). Bat ky loi nao -> khong doi (ket qua la ly do bac, khong nem loi).
"""
import os
from typing import List, Optional, Tuple

from .agents.evaluator_input import ReplanContext
from .models_interview import CandidateState, InterviewPlan, PlanTopic, Swap, TopicState
from .policy_hybrid import policy_mode, safe_reason

DEFAULT_MAX_SWAPS, MAX_SWAPS_CAP = 1, 2  # reserve toi da 2 topic nen khong the doi nhieu hon
RESULTS = ("applied", "budget", "bad_drop", "jd_priority", "bad_add", "not_applicable")  # nhan metric / TurnInfo


def replan_enabled(env=None) -> bool:
    """Co REPLAN_ENABLED (mac dinh tat) VA POLICY_MODE=hybrid: tat thi hanh vi, request va output y nhu truoc phase 05."""
    value = (os.environ if env is None else env).get("REPLAN_ENABLED", "")
    return value.strip().lower() in ("1", "true", "yes", "on") and policy_mode(env) == "hybrid"


def replan_max_swaps(env=None) -> int:
    value = (os.environ if env is None else env).get("REPLAN_MAX_SWAPS", "")
    try:
        return max(0, min(MAX_SWAPS_CAP, int(value)))
    except ValueError:
        return DEFAULT_MAX_SWAPS


def effective_plan(plan: InterviewPlan, state: CandidateState) -> InterviewPlan:
    """Plan thuc te: moi swap thay topic `drop` bang topic du phong `add` tai cung vi tri. Khong co swap / plan cu
    (khong co replan) -> tra nguyen plan. Plan goc khong bi sua; id khong khop thi bo qua swap do."""
    if not state.swaps or plan.replan is None:
        return plan
    reserve = {t.id: t for t in plan.replan.reserve}
    phases = []
    for ph in plan.phases:
        topics = list(ph.topics)
        if ph.phase == "technical":
            for s in state.swaps:
                i = next((k for k, t in enumerate(topics) if t.id == s.drop), None)
                if i is not None and s.add in reserve:
                    topics[i] = reserve[s.add]
        phases.append(ph.model_copy(update={"topics": topics}))
    return plan.model_copy(update={"phases": phases})


def _index_of(topics: List[Tuple[str, PlanTopic]], topic_id: str) -> Optional[int]:
    return next((i for i, (_, t) in enumerate(topics) if t.id == topic_id), None)


def validate_swap(p, state: CandidateState, plan: InterviewPlan, pos: int, topics: List[Tuple[str, PlanTopic]],
                  phase: str, action: str, hint: str, max_swaps: int) -> Optional[str]:
    """None = hop le, con lai la ly do bac (nhan metric). topics = flat_topics(plan thuc te); action la hanh dong cuoi
    cung truoc khi ap dung (sau low_performance_stop); p = SwapProposal."""
    if p is None or action != "next_topic" or phase != "technical":
        return "not_applicable"
    if plan.replan is None or len(state.swaps) >= max_swaps or hint == "hurry":
        return "budget"
    i = _index_of(topics, p.drop)
    if i is None or i <= pos or topics[i][0] != "technical" or state.topics[i].status != "pending" \
            or p.drop in {s.add for s in state.swaps}:  # chi topic ke hoach goc, chua hoi, o sau topic hien tai
        return "bad_drop"
    if p.drop in plan.replan.keep_ids:
        return "jd_priority"
    if p.add not in {t.id for t in plan.replan.reserve} or p.add in {s.add for s in state.swaps}:
        return "bad_add"
    return None


def apply_swap(state: CandidateState, p, i: int, turn: int) -> None:
    """Goi TRUOC apply_action; sau do topics = flat_topics(effective_plan(plan, state))."""
    state.swaps.append(Swap(drop=p.drop, add=p.add, turn=turn, reason=safe_reason(p.reason) or ""))
    state.topics[i] = TopicState(id=p.add)  # pending, cung vi tri


def attempt_swap(proposal, state: CandidateState, plan: InterviewPlan, topics: List[Tuple[str, PlanTopic]], pos: int,
                 phase: str, action: str, hint: str, turn: int) -> Optional[str]:
    """None khi LLM khong de xuat swap; con lai "applied" hoac ly do bac. Doi that thi sua state (swaps, topics[i])."""
    p = getattr(proposal, "swap", None)
    if p is None or not replan_enabled():
        return None
    why = validate_swap(p, state, plan, pos, topics, phase, action, hint, replan_max_swaps())
    if why is not None:
        return why
    apply_swap(state, p, _index_of(topics, p.drop), turn)
    return "applied"


def replan_context(plan: InterviewPlan, state: CandidateState, phase: str) -> Optional[ReplanContext]:
    """Khoi cho prompt v10: chi o topic technical khi con reserve chua dung va con luot doi; pending = topic technical
    chua hoi, sau topic hien tai, khong phai topic JD uu tien (nhung gi code co the chap nhan bo). plan = plan thuc te."""
    pool = plan.replan
    swaps_left = replan_max_swaps() - len(state.swaps)
    if not replan_enabled() or pool is None or phase != "technical" or swaps_left <= 0:
        return None
    flat = [(ph.phase, t) for ph in plan.phases for t in ph.topics]
    pos = next((i for i, (_, t) in enumerate(flat) if t.id == state.active_topic_id), None)
    if pos is None:
        return None
    used = {s.add for s in state.swaps}
    reserve = [(t.id, t.title) for t in pool.reserve if t.id not in used]
    pending = [(t.id, t.title) for i, (ph, t) in enumerate(flat) if i > pos and ph == "technical"
               and state.topics[i].status == "pending" and t.id not in pool.keep_ids and t.id not in used]
    if not reserve or not pending:
        return None
    return ReplanContext(pending, reserve, state.topics[pos].score_band, swaps_left)
