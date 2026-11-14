"""Ghi chu agent (phase 07, AGENT_NOTES_ENABLED + POLICY_MODE=hybrid): Evaluator v11 DE XUAT mot ghi chu moi va cap nhat
trang thai ghi chu cu; code loc va quyet. Ghi chu KHONG dung de tinh diem, khong vao Interviewer / Reporter.

Chi ghi chu `to_verify` dang `open` duoc dua lai vao context Evaluator (notes_for_context): strength / risk chi luu, de
khong neo diem (audit H2). Text sinh tu cau tra loi khong tin cay: gop khoang trang, bo neu > 150 ky tu, co mau injection
hoac PII. Luot nhay cam / injection (untrusted) khong ghi gi.
Khi day 8 ghi chu: bo ghi chu da xong (confirmed / rejected) cu nhat, khong co thi ghi chu cu nhat khong phai to_verify
(strength / risk / hypothesis khong bao gio xong nen khong duoc chiem cho mai), chi bo ghi chu moi khi ca 8 la to_verify open. Moi ly do bo la nhan metric co gioi han.
"""
import os
from typing import List, Optional, Tuple

from . import metrics
from .cv_text import has_injection, redact_pii
from .models_agent_notes import MAX_NOTES, NOTE_KINDS, Note
from .policy_hybrid import policy_mode

MAX_TEXT, MAX_UPDATES = 150, 8
_DONE = ("confirmed", "rejected")


def notes_enabled(env=None) -> bool:
    """Co AGENT_NOTES_ENABLED (mac dinh tat) VA POLICY_MODE=hybrid: tat thi request, quyet dinh va gia tri y nhu cu."""
    value = (os.environ if env is None else env).get("AGENT_NOTES_ENABLED", "")
    return value.strip().lower() in ("1", "true", "yes", "on") and policy_mode(env) == "hybrid"


def safe_note(text) -> Tuple[Optional[str], Optional[str]]:
    """(text da loc, None) hoac (None, ly do bo): empty | too_long | injection | pii. Kiem tren TOAN BO van ban da gop
    khoang trang; qua dai thi bo han (khong cat, vi cat giua so dien thoai / email se lot PII mot phan)."""
    clean = " ".join(text.split()) if isinstance(text, str) else ""
    if not clean:
        return None, "empty"
    if len(clean) > MAX_TEXT:
        return None, "too_long"
    if has_injection(clean):
        return None, "injection"
    if redact_pii(clean) != clean:
        return None, "pii"
    return clean, None


def _drop(reason: str) -> None:
    metrics.record_note_dropped(reason)


def _apply_updates(state, updates) -> None:
    """Chi ghi chu to_verify dang open (nhung gi Evaluator duoc thay) moi doi duoc trang thai; con lai bi bo."""
    for u in (updates if isinstance(updates, list) else [])[:MAX_UPDATES]:
        uid, status = getattr(u, "id", ""), getattr(u, "status", "")
        note = next((n for n in state.notes if n.id == uid and n.kind == "to_verify" and n.status == "open"), None)
        if note is None:
            _drop("unknown_id")
        elif status not in _DONE:
            _drop("bad_status")
        else:
            note.status = status


def apply_notes(state, raw, turn: int, topic_id: Optional[str], untrusted: bool = False) -> None:
    """Goi trong next_turn sau record_evaluation, chi khi notes_enabled. raw = output V11 (None: khong co de xuat).
    untrusted: luot nhay cam / injection -> bo ca de xuat."""
    new, updates = getattr(raw, "new_note", None), getattr(raw, "note_updates", None)
    if new is None and not updates:
        return
    if untrusted:
        _drop("untrusted")
        return
    _apply_updates(state, updates)
    if new is None:
        return
    kind = getattr(new, "kind", "")
    text, why = safe_note(getattr(new, "text", ""))
    if kind not in NOTE_KINDS:
        _drop("invalid_kind")
    elif text is None:
        _drop(why)
    elif any(n.id == f"n{turn}" for n in state.notes):
        _drop("duplicate")
    else:
        if len(state.notes) >= MAX_NOTES:  # day: bo ghi chu da xong cu nhat, roi ghi chu cu nhat khong phai to_verify
            old = next((n for n in state.notes if n.status in _DONE), None) \
                or next((n for n in state.notes if n.kind != "to_verify"), None)
            if old is None:
                _drop("full")
                return
            state.notes.remove(old)
        state.notes.append(Note(id=f"n{turn}", turn=turn, topic_id=topic_id, kind=kind, text=text))
        metrics.record_note_recorded(kind)


def notes_for_context(state) -> List[Tuple[str, str]]:
    """(id, text) cua ghi chu to_verify con open, loc lai de state tu client khong dua text la vao prompt."""
    out = []
    for n in state.notes:
        text, _ = safe_note(n.text)
        if n.kind == "to_verify" and n.status == "open" and text:
            out.append((n.id, text))
    return out[-MAX_NOTES:]
