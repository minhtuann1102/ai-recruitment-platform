"""Tracing Langfuse: moi request la mot trace (gom theo session_id), moi lan goi LLM la mot generation.

Co gui noi dung (prompt, output, cau tra loi) len Langfuse, da qua `mask_pii`; log thi van khong co noi dung
(docs/ai-service/07 muc 8.6). Thieu LANGFUSE_PUBLIC_KEY / SECRET_KEY hoac LANGFUSE_TRACING_ENABLED=false thi tat, moi
ham la no-op. Tracing tuy chon: loi SDK chi ghi log, khong bao gio lam hong luot phong van.

Khong dung context hien tai cua OpenTelemetry: `start_as_current_observation` phai detach dung task da attach, ma trace
mo o route va dong trong generator SSE. Thay vao do giu observation trong contextvar va tao con qua `start_observation`
cua cha; `propagate_attributes` chi boc lenh tao (dong bo) de moi observation co session_id. Ngoai request (evals goi
agent truc tiep, warm RAG) khong co cha nen khong tao trace.
"""
import asyncio
import logging
import os
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Dict, Optional, Sequence

from langfuse import Langfuse, propagate_attributes

from .cv_text import redact_pii

log = logging.getLogger("ai_service.tracing")
_client: Optional[Langfuse] = None
_loaded = False


def _safe(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as err:
            log.warning("tracing_failed where=%s error=%s", fn.__name__, type(err).__name__)
            return None
    return wrapper


def mask_pii(*, data: Any, **_: Any) -> Any:
    """Lop che cuoi truoc khi roi service: CV da redact luc parse, nhung cau tra loi co the co email / so dien thoai."""
    if isinstance(data, str):
        return redact_pii(data)
    if isinstance(data, dict):
        return {k: mask_pii(data=v) for k, v in data.items()}
    if isinstance(data, (list, tuple)):
        return [mask_pii(data=v) for v in data]
    return data


def _get_client() -> Optional[Langfuse]:
    global _client, _loaded
    if not _loaded:
        _loaded = True
        keys = os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
        if keys and os.getenv("LANGFUSE_TRACING_ENABLED", "true").lower() != "false":
            try:
                _client = Langfuse(mask=mask_pii, environment=os.getenv("APP_ENV", "dev").lower())
            except Exception as err:
                log.error("langfuse_config_error error=%s", type(err).__name__)
    return _client


class Observation:
    """Observation dang mo. `obs` None (tracing tat / ngoai request): moi method la no-op."""

    def __init__(self, obs: Any = None, attrs: Optional[Dict] = None):
        self._obs, self._attrs, self._ended = obs, attrs or {}, False

    @_safe
    def child(self, name: str, as_type: str, fields: Dict) -> "Observation":
        if self._obs is None:
            return self
        with propagate_attributes(**self._attrs):
            return Observation(self._obs.start_observation(name=name, as_type=as_type, **fields), self._attrs)

    @_safe
    def update(self, **fields: Any) -> None:
        if self._obs is not None:
            self._obs.update(**fields)

    def first_token(self) -> None:
        """Moc TTFT cua generation stream."""
        self.update(completion_start_time=datetime.now(timezone.utc))

    @_safe
    def end(self) -> None:
        if self._obs is not None and not self._ended:
            self._ended = True
            self._obs.end()

    @property
    def trace_id(self) -> Optional[str]:
        return getattr(self._obs, "trace_id", None)


_OFF = Observation()
_parent: ContextVar[Observation] = ContextVar("trace_parent", default=_OFF)
_root: ContextVar[Observation] = ContextVar("trace_root", default=_OFF)


@_safe
def start_request(name: str, *, session_id: Optional[str] = None, turn_number: Optional[int] = None,
                  tags: Sequence[str] = (), input: Any = None) -> None:
    """Mo trace cua request; song tiep qua stream SSE nhu `bind_request` (contextvar theo task request)."""
    client = _get_client()
    if client is None:
        return
    attrs: Dict[str, Any] = {"trace_name": name}
    if session_id:
        attrs["session_id"] = session_id
    if tags:
        attrs["tags"] = list(tags)
    if turn_number is not None:
        attrs["metadata"] = {"turn_number": str(turn_number)}
    with propagate_attributes(**attrs):
        root = Observation(client.start_observation(name=name, input=input), attrs)
    _root.set(root)
    _parent.set(root)


@contextmanager
def observation(name: str, as_type: str = "span", nest: bool = False, **fields: Any):
    """Observation con cua observation hien tai. `nest`: goi LLM ben trong thanh con cua no (chi dung trong coroutine,
    khong dung trong async generator vi contextvar phai reset cung context)."""
    obs = _parent.get().child(name, as_type, fields) or _OFF
    token = _parent.set(obs) if nest else None
    try:
        yield obs
    except asyncio.CancelledError:  # qua han (wait_for) hoac client ngat: khong hien thanh cong voi output rong
        obs.update(level="WARNING", status_message="cancelled")
        raise
    except Exception as err:
        obs.update(level="ERROR", status_message=type(err).__name__)
        raise
    finally:
        if token is not None:
            _parent.reset(token)
        obs.end()


def set_output(output: Any) -> None:
    _root.get().update(output=output)


def finish_request(status: str, error: str, **metadata: Any) -> None:
    root = _root.get()
    fields: Dict[str, Any] = {"metadata": {"status": status, **metadata}}
    if status != "ok":
        fields.update(level="ERROR" if status == "error" else "WARNING", status_message=error)
    root.update(**fields)
    root.end()


def trace_id() -> Optional[str]:
    """Id trace cua request hien tai, ghi vao log de tu dong log tim ra trace."""
    return _root.get().trace_id


@_safe
def warm() -> None:
    """Tao client luc khoi dong (~150 ms dong bo) thay vi trong request dau tien."""
    _get_client()


@_safe
def shutdown() -> None:
    """Gui not span con trong hang doi truoc khi tat service."""
    if _client is not None:
        _client.shutdown()
