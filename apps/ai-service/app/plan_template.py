"""Khung phase theo level va thoi luong (FR-AI-003), do code tinh, Planner (LLM hay mock) phai theo.

So topic technical = max(2, round(goc x thoi luong / 30)), toi da bang goc; thoi gian moi phase chia theo ti le cua cau hinh
30 phut. Cong thuc la de xuat (thiet ke goc cho 30 phut), chinh sau khi chay ung vien gia lap.
"""
from dataclasses import dataclass
from typing import Dict

from .models_common import LEVEL_CONFIG


@dataclass(frozen=True)
class PlanTemplate:
    topics: Dict[str, int]  # phase -> so topic
    minutes: Dict[str, int]  # phase -> phut
    start: int
    min_difficulty: int
    max_difficulty: int

    def as_prompt(self) -> list:
        return [{"phase": p, "topics": self.topics[p], "time_budget_min": self.minutes[p]}
                for p in ("intro", "technical", "scenario")]


def technical_topics(level: str, duration_minutes: int) -> int:
    """Khong vuot so goc: phien > 30 phut (contract van cho toi 45) giu nhu thiet ke goc, them luot thay vi topic."""
    base = LEVEL_CONFIG[level]["technical"]
    return min(base, max(2, round(base * duration_minutes / 30)))


def build_template(level: str, duration_minutes: int) -> PlanTemplate:
    cfg = LEVEL_CONFIG[level]
    scale = duration_minutes / 30
    m_intro, _, m_scn = (max(1, round(m * scale)) for m in cfg["minutes"])
    m_tech = max(1, duration_minutes - m_intro - m_scn)  # tong phut cac phase = thoi luong phien
    lo, hi = cfg["bounds"]
    return PlanTemplate(topics={"intro": 1, "technical": technical_topics(level, duration_minutes), "scenario": 1},
                        minutes={"intro": m_intro, "technical": m_tech, "scenario": m_scn},
                        start=max(lo, min(hi, cfg["start"])), min_difficulty=lo, max_difficulty=hi)
