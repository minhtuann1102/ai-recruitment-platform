"""Co "vuot level" trong bao cao (docs/ai-service/05 muc Goi y level), do code tinh, Reporter khong sua.

Do kho bi chan o bounds.max cua level, nen ung vien gioi chon level thap chi nhan verdict exceeds ma khong co
tin hieu nen thu level cao hon. Co chi bat khi ung vien da cham tran do kho ma van tra loi tot on dinh.
"""
from typing import Dict, List, Optional

from .models_common import LEVEL_CONFIG
from .models_interview import FinalizeTurn

LEVEL_ORDER = ("fresher", "junior", "middle", "senior")
EXCEEDS_FROM = 8.5  # = nguong verdict exceeds (report_scoring.verdict)
CEILING_MIN_TURNS = 3
CEILING_GOOD_SCORE = 7.0  # = nguong verdict meets, tinh cho tung luot o do kho tran


def level_signal(level: str, scored: List[FinalizeTurn], overall: Optional[float], confidence: str) -> Optional[Dict]:
    """-> co above_level hoac None. scored: cac luot duoc cham (report_scoring.scored_turns)."""
    if level == LEVEL_ORDER[-1] or overall is None or overall < EXCEEDS_FROM or confidence == "low":
        return None
    ceiling = LEVEL_CONFIG[level]["bounds"][1]
    evidence = [t.turn_number for t in scored
                if t.difficulty >= ceiling and t.evaluation.turn_score_10 >= CEILING_GOOD_SCORE]
    if len(evidence) < CEILING_MIN_TURNS:
        return None
    suggested = LEVEL_ORDER[LEVEL_ORDER.index(level) + 1]
    return {"type": "above_level", "current_level": level, "suggested_level": suggested,
            "evidence_turns": evidence,
            "note": f"Ứng viên trả lời tốt ổn định ở mức khó cao nhất của level {level}; "
                    f"nên thử phỏng vấn ở level {suggested}."}
