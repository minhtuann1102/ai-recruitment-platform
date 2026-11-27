"""Ngu canh mot request chay tren graph ca phien (runtime context, KHONG vao checkpoint).

/start dien start_req; /next-turn dien turn (TurnContext cua luot); /finalize dien finalize_req. Ket qua node ghi lai
tren chinh object nay (start_result, turn.result, report) de endpoint doc sau khi graph dung o interrupt.
"""
from dataclasses import dataclass
from typing import Any, Optional

from ..llm.usage import UsageCollector
from ..models_interview import FinalizeRequest, StartRequest
from ..turn_result import TurnResult
from ..turn_steps import TurnContext


@dataclass
class SessionRunContext:
    session_id: str
    collector: Optional[UsageCollector] = None
    interviewer: Any = None  # ham tra Interviewer (get_interviewer), chi node `ask` goi
    start_req: Optional[StartRequest] = None
    turn: Optional[TurnContext] = None
    finalize_req: Optional[FinalizeRequest] = None
    start_result: Optional[TurnResult] = None
    report: Optional[dict] = None

    @property
    def result(self) -> Optional[TurnResult]:
        """Ket qua cau hoi vua stream: cua luot (next-turn) hoac cua /start."""
        return self.turn.result if self.turn is not None else self.start_result
