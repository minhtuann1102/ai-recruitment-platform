"""Gioi han cung va ngan sach thoi gian (FR-AI-035, 036; docs/ai-service/03 muc 4.4), thuan code.

Thu tu uu tien sau moi luot (dieu kien dau tien khop thang): qua han cung -> ket thuc ngay; het gio hoac
turn cap -> wrap_up; phase qua ngan sach + 1 phut -> phase ke; topic dat dieu kien dong -> topic ke.
Muon thoi gian: han cua phase la tong ngan sach cac phase tu dau toi phase do, nen phase xong som de du cho
phase sau. Ung vien bam ket thuc (uu tien 1) do interview-service xu ly qua /api/finalize.
"""
from typing import Optional, Tuple

from .models_interview import CandidateState, InterviewPlan

HARD_LIMIT_EXTRA_S = 180  # thoi luong + 3 phut
PHASE_GRACE_S = 60
TOPIC_OVERRUN = 1.5
TURN_CAP_PER_30_MIN = 24  # thiet ke goc; 20 phut -> 16 (FR-AI-035, de xuat)


def duration_s(plan: InterviewPlan) -> int:
    return sum(p.time_budget_min for p in plan.phases) * 60


def turn_cap(plan: InterviewPlan) -> int:
    return max(8, round(TURN_CAP_PER_30_MIN * duration_s(plan) / 1800))


def phase_deadline_s(plan: InterviewPlan, phase: str) -> int:
    """Han (tinh tu dau phien) cua phase = tong ngan sach tu phase dau toi phase nay (co muon thoi gian)."""
    total = 0
    for p in plan.phases:
        total += p.time_budget_min * 60
        if p.phase == phase:
            return total
    return total


def topic_budget_s(plan: InterviewPlan, phase: str) -> float:
    ph = next((p for p in plan.phases if p.phase == phase), None)
    return ph.time_budget_min * 60 / max(1, len(ph.topics)) if ph else 0.0


def forced_transition(elapsed_s: int, state: CandidateState, plan: InterviewPlan,
                      phase: str) -> Optional[Tuple[str, str]]:
    """-> (hanh dong, ly do) hoac None de policy quyet. Hanh dong: end | wrap_up | next_phase | next_topic."""
    total = duration_s(plan)
    if elapsed_s >= total + HARD_LIMIT_EXTRA_S:
        return "end", "time_hard_limit"
    if elapsed_s >= total:
        return "wrap_up", "time_up"
    if state.turn_count >= turn_cap(plan):
        return "wrap_up", "turn_cap"
    last_phase = plan.phases[-1].phase
    if phase != last_phase and elapsed_s >= phase_deadline_s(plan, phase) + PHASE_GRACE_S:
        return "next_phase", "phase_time"
    if state.counters.consecutive_dont_know >= 2:
        return "next_topic", "two_dont_know"
    if elapsed_s - state.topic_started_s >= TOPIC_OVERRUN * topic_budget_s(plan, phase):
        return "next_topic", "topic_time"
    return None
