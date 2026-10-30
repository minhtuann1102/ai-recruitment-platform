"""Ngat RAG tam thoi khi ai_db / embedding loi that: `threshold` request loi trong `window_s` giay thi bo qua ai_db
trong `cooldown_s` giay, de moi /api/start khong phai cho het han 5 s roi moi chay khong RAG. Het han thi request sau
thu lai. cooldown_s = 0: khong ngat (moi request deu thu RAG).

Ngat la toan service nen mot request cham khong du de ngat: do 30/10, mot `rag_timeout` luc 4 phien cung start (LLM
viet lai truy van cham, ai_db van tot) tat RAG cua moi phien 60 s, 8/12 lan mo phong dinh loi nay."""
import logging
import time
from collections import deque
from typing import Callable, Deque, List, Sequence

log = logging.getLogger("ai_service.rag")
FAILURES_TO_OPEN, FAILURE_WINDOW_S = 3, 120.0  # cua so rong: luu luong thap thi loi cach nhau hang chuc giay
START_PARTIAL_ERROR = "rag_start_partial"  # /api/start qua han nhung mot so topic da co ket qua
MEMORY_ONLY_ERROR = "rag_memory_only"  # dang ngat: luot chi dung BM25 + cache dap an, khong doi ai_db
# Mot duong hybrid loi (cac duong con lai van chay), truy hoi theo luot loi (van co snippet topic), start con ket qua
# mot phan, hay dang ngat nhung con phan trong bo nho: khong tinh la loi that
SOFT_ERRORS = frozenset({"rag_hybrid_partial", "rag_turn_failed", START_PARTIAL_ERROR, MEMORY_ONLY_ERROR})


class CircuitBreaker:
    def __init__(self, cooldown_s: int, clock: Callable[[], float] = time.monotonic,
                 threshold: int = FAILURES_TO_OPEN, window_s: float = FAILURE_WINDOW_S):
        self.cooldown_s, self._clock = cooldown_s, clock
        self.threshold, self.window_s = threshold, window_s
        self._open_until = 0.0
        self._failures: Deque[float] = deque()
        self.last_errors: List[str] = []

    def is_open(self) -> bool:
        return self._clock() < self._open_until

    def remaining_s(self) -> int:
        return max(0, int(self._open_until - self._clock() + 0.999))

    def record(self, errors: Sequence[str]) -> None:
        """Ghi mot request loi (loi nhe khong tinh); du `threshold` lan trong cua so thi ngat."""
        errors = [e for e in errors if e not in SOFT_ERRORS]
        if self.cooldown_s <= 0 or not errors or self.is_open():  # request dang do luc mo: khong keo dai thoi gian ngat
            return
        now = self._clock()
        self._failures.append(now)
        while now - self._failures[0] > self.window_s:
            self._failures.popleft()
        self.last_errors = list(errors)
        if len(self._failures) >= self.threshold:
            self._failures.clear()
            self._open_until = now + self.cooldown_s
            log.warning("rag_circuit_open cooldown_s=%s errors=%s", self.cooldown_s, ",".join(errors))
