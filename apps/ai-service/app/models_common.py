"""Kieu dung chung cho cac contract ai-service (snake_case)."""
from typing import Literal

Level = Literal["fresher", "junior", "middle", "senior"]
Phase = Literal["intro", "technical", "scenario", "wrap_up", "done"]
TurnKind = Literal["main", "follow_up", "hint", "clarify"]
Action = Literal["ask_main", "follow_up", "hint", "clarify", "wrap_up", "end"]
AgentDecision = Literal["deepen", "switch_topic", "keep_difficulty"]
AnswerType = Literal["answered", "partial", "dont_know", "off_topic", "asks_clarification", "manipulation"]

# Gia dinh cho mock (docs/ai-service/03 muc 4.3; chua do tren du lieu that).
# (so topic technical, tong phut intro/technical/scenario, follow-up toi da, follow-up toi da scenario,
#  do kho min, max, bat dau)
LEVEL_CONFIG = {
    "fresher": {"technical": 4, "minutes": (4, 17, 7), "max_fu": 2, "max_fu_scn": 3, "bounds": (1, 3), "start": 1},
    "junior": {"technical": 4, "minutes": (4, 16, 8), "max_fu": 2, "max_fu_scn": 3, "bounds": (1, 4), "start": 2},
    "middle": {"technical": 3, "minutes": (5, 14, 9), "max_fu": 3, "max_fu_scn": 4, "bounds": (2, 5), "start": 3},
    "senior": {"technical": 3, "minutes": (5, 12, 11), "max_fu": 3, "max_fu_scn": 4, "bounds": (3, 5), "start": 4},
}
TURN_CAP = 24
