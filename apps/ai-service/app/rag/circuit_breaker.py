"""Ngat RAG tam thoi khi ai_db / embedding loi: sau mot request co loi RAG, bo qua RAG trong `cooldown_s` giay de
moi /api/start khong phai cho het han 5 s roi moi chay khong RAG. Het han thi request sau thu lai (loi tiep thi ngat
tiep). cooldown_s = 0: khong ngat (moi request deu thu RAG)."""
import logging
import time
from typing import Callable, List, Sequence

log = logging.getLogger("ai_service.rag")
SOFT_ERRORS = frozenset({"rag_hybrid_partial"})  # mot duong hybrid loi, cac duong con lai van chay: khong ngat


class CircuitBreaker:
    def __init__(self, cooldown_s: int, clock: Callable[[], float] = time.monotonic):
        self.cooldown_s, self._clock = cooldown_s, clock
        self._open_until = 0.0
        self.last_errors: List[str] = []

    def is_open(self) -> bool:
        return self._clock() < self._open_until

    def remaining_s(self) -> int:
        return max(0, int(self._open_until - self._clock() + 0.999))

    def trip(self, errors: Sequence[str]) -> None:
        errors = [e for e in errors if e not in SOFT_ERRORS]
        if self.cooldown_s <= 0 or not errors:
            return
        self._open_until = self._clock() + self.cooldown_s
        self.last_errors = list(errors)
        log.warning("rag_circuit_open cooldown_s=%s errors=%s", self.cooldown_s, ",".join(errors))
