"""Interviewer MOCK va cau du phong: dien dat dung mot cau hoi theo action da chon (khong LLM).

Moi action co vai cach dien dat; `candidates` tra theo thu tu uu tien de noi goi chon cau chua hoi (FR-AI-038).
"""
from typing import List, Optional

from .models_interview import PlanTopic

WRAP_UP = "Cảm ơn bạn, buổi phỏng vấn đến đây là kết thúc. Bạn còn câu hỏi nào dành cho mình không?"
_PHASE_INTRO = {"technical": "Giờ mình chuyển sang phần kiến thức chuyên môn nhé. ",
                "scenario": "Tiếp theo là một tình huống thực tế. "}
_FOLLOW_UP = ("Ok. Bạn nói rõ hơn giúp mình về {f}?", "Mình muốn đi sâu thêm một chút: {f} thì sao?",
              "Với {f}, bạn giải thích kỹ hơn giúp mình nhé?")
_HINT = ("Mình gợi ý nhé: hãy nghĩ tới {f}. Bạn thử trả lời lại xem?",
         "Gợi ý nhỏ: thử nghĩ theo hướng {f}. Bạn trả lời lại nhé?")
_CLARIFY = ("Mình hỏi lại cho rõ nhé: {q}", "Có thể mình hỏi chưa rõ. Ý mình là: {q}")


def candidates(action: str, topic: Optional[PlanTopic], phase: str, focus: Optional[str],
               last_question: str, first_turn: bool, phase_changed: bool) -> List[str]:
    if action == "wrap_up" or topic is None:
        return [WRAP_UP]
    f = focus or topic.title
    if action == "hint":
        return [h.format(f=f) for h in _HINT]
    if action == "clarify":
        return [c.format(q=last_question) for c in _CLARIFY]
    if action == "follow_up":
        return [t.format(f=f) for t in _FOLLOW_UP]
    greeting = "Chào bạn, mình bắt đầu nhé. " if first_turn else ""
    prefix = greeting + (_PHASE_INTRO.get(phase, "") if phase_changed else "")
    return [prefix + topic.backup_question,
            prefix + f"Về {topic.title}, bạn hiểu nó thế nào và đã áp dụng ra sao trong dự án?"]


def compose(action: str, topic: Optional[PlanTopic], phase: str, focus: Optional[str],
            last_question: str, first_turn: bool, phase_changed: bool) -> str:
    return candidates(action, topic, phase, focus, last_question, first_turn, phase_changed)[0]
