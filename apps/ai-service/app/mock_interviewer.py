"""Interviewer MOCK: dien dat dung mot cau hoi theo action da chon (khong LLM)."""
from typing import Optional

from .models_interview import PlanTopic

WRAP_UP = "Cảm ơn bạn, buổi phỏng vấn đến đây là kết thúc. Bạn còn câu hỏi nào dành cho mình không?"
_PHASE_INTRO = {"technical": "Giờ mình chuyển sang phần kiến thức chuyên môn nhé. ",
                "scenario": "Tiếp theo là một tình huống thực tế. "}


def compose(action: str, topic: Optional[PlanTopic], phase: str, focus: Optional[str],
            last_question: str, first_turn: bool, phase_changed: bool) -> str:
    if action == "wrap_up" or topic is None:
        return WRAP_UP
    if action == "hint":
        return f"Mình gợi ý nhé: hãy nghĩ tới {focus}. Bạn thử trả lời lại xem?"
    if action == "clarify":
        return f"Mình hỏi lại cho rõ nhé: {last_question}"
    if action == "follow_up":
        return f"Ok. Bạn nói rõ hơn giúp mình về {focus}?"
    greeting = "Chào bạn, mình bắt đầu nhé. " if first_turn else ""
    prefix = _PHASE_INTRO.get(phase, "") if phase_changed else ""
    return f"{greeting}{prefix}{topic.backup_question}"
