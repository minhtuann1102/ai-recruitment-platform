"""Log co cau truc cho ai-service (NFR-AI-OBS02): moi dong kem session_id, turn_number; khong kem noi dung.

Uvicorn chi cau hinh logger cua no; khong co ham nay thi log `ai_service.*` muc INFO bi bo (Python chi in WARNING tro
len, khong dinh dang). Route goi `bind_request` mot lan; contextvar di theo task cua request (ca stream SSE,
asyncio.to_thread, task con) nen moi log ben duoi tu co session_id, khong phai truyen tay.

Env: LOG_LEVEL (mac dinh INFO), LOG_FORMAT = json (mac dinh, cho he thong gom log) | text (doc tren may dev).
"""
import json
import logging
import os
import re
import sys
import traceback
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional

LOGGER = "ai_service"
SESSION_CHARS = 64
_UNSAFE = re.compile(r"[^\w.:-]")  # session_id do client gui: bo ky tu xuong dong / khoang trang (gia mao dong log)
_session_id: ContextVar[Optional[str]] = ContextVar("log_session_id", default=None)
_turn_number: ContextVar[Optional[int]] = ContextVar("log_turn_number", default=None)
TEXT_FORMAT = "%(asctime)s %(levelname)s %(name)s [session=%(session_id)s turn=%(turn_number)s] %(message)s"


def safe_session_id(session_id: Optional[str]) -> Optional[str]:
    return _UNSAFE.sub("_", session_id)[:SESSION_CHARS] if session_id else None


def bind_request(session_id: Optional[str], turn_number: Optional[int] = None) -> None:
    """Gan id phien / luot cho moi log trong request hien tai (task cua request, khong lan sang request khac)."""
    _session_id.set(safe_session_id(session_id))
    _turn_number.set(turn_number)


def bound_session_id() -> Optional[str]:
    return _session_id.get()


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.session_id = _session_id.get()
        record.turn_number = _turn_number.get()
        return True


class JsonFormatter(logging.Formatter):
    """Mot dong JSON moi log. `event` = tu dau cua message (vd rag_turn, llm_call) de loc / dem theo loai."""

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        out = {"ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
               "level": record.levelname, "logger": record.name, "event": message.split(" ", 1)[0],
               "msg": message, "session_id": getattr(record, "session_id", None),
               "turn_number": getattr(record, "turn_number", None)}
        if record.exc_info and record.exc_info[0]:
            # chi ten loi + vi tri code: message cua exception co the chua noi dung (vd ValidationError co input_value)
            out["exc_type"] = record.exc_info[0].__name__
            out["exc"] = "".join(traceback.format_list(traceback.extract_tb(record.exc_info[2])))
        return json.dumps(out, ensure_ascii=False)


class _StderrHandler(logging.StreamHandler):
    """Luon ghi vao sys.stderr hien tai (pytest thay stderr luc capture; giu stream cu se ghi vao file da dong)."""

    @property
    def stream(self):
        return sys.stderr

    @stream.setter
    def stream(self, _):
        pass


def configure_logging() -> None:
    """Gan handler cho logger `ai_service` (goi lai khong gan them). Van propagate: pytest caplog doc duoc."""
    logger = logging.getLogger(LOGGER)
    level_name = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    level = int(level_name) if level_name.isdigit() else logging.getLevelName(level_name)
    logger.setLevel(level if isinstance(level, int) else logging.INFO)
    if not any(isinstance(h, _StderrHandler) for h in logger.handlers):
        handler = _StderrHandler()
        handler.addFilter(RequestContextFilter())
        logger.addHandler(handler)
    handler = next(h for h in logger.handlers if isinstance(h, _StderrHandler))
    text = os.getenv("LOG_FORMAT", "json").lower() == "text"
    handler.setFormatter(logging.Formatter(TEXT_FORMAT) if text else JsonFormatter())
    if not isinstance(level, int):
        logger.warning("log_level_invalid value=%s fallback=INFO", _UNSAFE.sub("_", level_name)[:20])
