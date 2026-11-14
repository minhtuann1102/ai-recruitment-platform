"""Chi so mo phong cho ghi chu agent (phase 07, AGENT_NOTES_ENABLED). Ham thuan, khong goi mang.

Doc `state.notes` cuoi phien (session["notes"]) va bao cao:
  sessions_with_notes = so phien co it nhat 1 ghi chu
  notes_per_session   = trung binh so ghi chu moi phien (tinh moi phien co luot)
  by_kind             = phan bo kind
  to_verify           = {total, confirmed, rejected, open, resolved_rate}   # ti le duoc xac nhan / bac o luot sau
  unsafe_notes        = so ghi chu khong qua safe_note (injection / PII / dai)  # BAT BIEN: phai = 0
Cong chat luong (>= 85% ghi chu dung hoi thoai, band khong giam vs v8): [BLOCKED-KEY], doc tay 20 phien.
So sanh bat/tat co can hai lan chay (hybrid +- AGENT_NOTES_ENABLED, --runs 3): moi lan chay chi dung duoc mot co.
"""
from collections import Counter
from typing import Dict, Optional

from app.agent_notes import MAX_TEXT, safe_note


def notes_summary(sessions: Dict[str, Dict]) -> Dict:
    pooled = [s for s in sessions.values() if s.get("turns")]
    notes = [n for s in pooled for n in s.get("notes", [])]
    verify = [n for n in notes if n["kind"] == "to_verify"]
    done = sum(n["status"] in ("confirmed", "rejected") for n in verify)
    rate: Optional[float] = round(done / len(verify), 3) if verify else None
    unsafe = sum(safe_note(n["text"])[0] != n["text"] or len(n["text"]) > MAX_TEXT for n in notes)
    return {
        "sessions_with_notes": sum(bool(s.get("notes")) for s in pooled),
        "notes_per_session": round(len(notes) / len(pooled), 2) if pooled else None,
        "by_kind": dict(Counter(n["kind"] for n in notes)),
        "to_verify": {"total": len(verify), "confirmed": sum(n["status"] == "confirmed" for n in verify),
                      "rejected": sum(n["status"] == "rejected" for n in verify),
                      "open": sum(n["status"] == "open" for n in verify), "resolved_rate": rate},
        "unsafe_notes": unsafe}
