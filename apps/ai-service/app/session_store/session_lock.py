"""Khoa mot luot dang chay cho moi phien: request thu hai cung session khi luot truoc chua xong -> 409 turn_in_progress.

Khoa trong tien trinh: dung khi ai-service chay mot instance (hien tai). Nhieu instance can khoa chung (advisory lock
Postgres giu tren mot ket noi suot stream, doc 12 G3) - chua lam, ghi o plan phase 03. Khong cho: luot dang chay thi
tu choi ngay, interview-service gui lai sau (khong tao hang doi trong ai-service).
"""
from typing import Callable, Set

from ..api_error import ApiError


class SessionTurnLock:
    def __init__(self):
        self._busy: Set[str] = set()

    def hold(self, session_id: str) -> Callable[[], None]:
        """Giu khoa; tra ham nha khoa (goi nhieu lan khong sao)."""
        if session_id in self._busy:
            raise ApiError(409, "turn_in_progress", "Lượt trước của phiên đang được xử lý",
                           {"retryable": True})
        self._busy.add(session_id)
        held = [True]

        def release() -> None:  # chi nha mot lan: lan goi sau khong nha khoa cua luot moi cung phien
            if held[0]:
                held[0] = False
                self._busy.discard(session_id)
        return release

    def busy(self, session_id: str) -> bool:
        return session_id in self._busy


turn_locks = SessionTurnLock()
