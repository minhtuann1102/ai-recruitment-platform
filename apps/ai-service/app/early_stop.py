"""Ket thuc som khi ung vien yeu keo dai (docs/ai-service/03 muc 4.4), thuan code.

Chi xet luc dong topic (next_topic / next_phase), sau dieu kien thoi gian va turn cap: middle/senior ma 3 topic
technical co diem gan nhat (plan it hon 3 thi tat ca topic technical) deu yeu va da du luot duoc cham thi wrap_up
som, bo phan con lai (thuong la scenario).
Ung vien van duoc goi y truoc khi topic bi danh gia yeu, vi luat khong ghi de follow_up / hint / clarify.
"""
from typing import List, Tuple

from .models_interview import CandidateState, PlanTopic
from .state_update import WEAK_BAND

EARLY_STOP_LEVELS = ("middle", "senior")
WEAK_TOPICS_TO_STOP = 3
MIN_SCORED_TURNS = 6  # khop nguong confidence cua report (report_scoring._confidence): it hon la "low"


def low_performance_stop(state: CandidateState, topics: List[Tuple[str, PlanTopic]], pos: int, level: str,
                         action: str) -> bool:
    """True khi nen wrap_up som. topics = flat_topics(plan); state.topics[i] ung voi topics[i]."""
    if level not in EARLY_STOP_LEVELS or action not in ("next_topic", "next_phase"):
        return False
    if state.evaluated_turns < MIN_SCORED_TURNS:
        return False
    # plan ngan (vd 20 phut chi co 2 topic technical): yeu het cac topic technical cung du de dung
    need = min(WEAK_TOPICS_TO_STOP, sum(1 for ph, _ in topics if ph == "technical"))
    # topic bi bo qua (next_phase) khong co diem nen khong cat chuoi "lien tiep"
    bands = [state.topics[i].score_band for i in range(pos + 1)
             if topics[i][0] == "technical" and state.topics[i].score_band is not None]
    recent = bands[-need:] if need else []
    return need > 0 and len(recent) == need and all(b < WEAK_BAND for b in recent)
