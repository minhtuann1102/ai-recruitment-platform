"""Quyet dinh soat doan giao trinh (spec 012, data-model §4): doc/ghi file, ap len noi dung, gop lo moi.

File: `settings.TEXTBOOK_DECISIONS_DIR/<source_id>-decisions.json`, khoa quyet dinh = content_hash cua noi dung
TRUOC khi ap. `approved_by` rong cho toi khi review-textbook-score thoat 0 (qua cong doan moi) va dat
`CANARY_GATE_APPROVER`; index-textbook tu choi file co approved_by rong.
"""
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from . import settings
from .qa_record_builder import content_hash
from .textbook_chunker import MIN_WORDS, SEP
from .textbook_noise_filter import prose_word_count

VERDICTS = ("keep", "drop", "trim")
CANARY_GATE_APPROVER = "auto:canary-gate"  # approved_by do review-textbook-score ghi khi lo qua cong doan moi (2026-11-17)


@dataclass
class Decisions:
    source_id: str
    reviewed_at: str = ""
    approved_by: str = ""
    decisions: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # content_hash -> {verdict, ...}


def decisions_path(source_id: str, directory: Optional[Path] = None) -> Path:
    return Path(directory or settings.TEXTBOOK_DECISIONS_DIR) / f"{source_id}-decisions.json"


def load_decisions(source_id: str, directory: Optional[Path] = None) -> Decisions:
    """File chua co -> Decisions rong (approved_by = ""). File hong / verdict la -> ValueError."""
    path = decisions_path(source_id, directory)
    if not path.exists():
        return Decisions(source_id=source_id)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: JSON khong hop le ({exc})") from exc
    items = raw.get("decisions") or {}
    for key, decision in items.items():
        _validate_decision(key, decision)
    return Decisions(
        source_id=raw.get("source_id") or source_id,
        reviewed_at=raw.get("reviewed_at") or "",
        approved_by=raw.get("approved_by") or "",
        decisions=items,
    )


def save_decisions(decisions: Decisions, directory: Optional[Path] = None) -> Path:
    """Ghi file (UTF-8, khoa quyet dinh sap theo hash de diff on dinh); tra duong dan da ghi."""
    path = decisions_path(decisions.source_id, directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_id": decisions.source_id,
        "reviewed_at": decisions.reviewed_at,
        "approved_by": decisions.approved_by,
        "decisions": {key: decisions.decisions[key] for key in sorted(decisions.decisions)},
    }
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, path)
    return path


def merge_decisions(old: Decisions, new: Decisions) -> Decisions:
    """Gop lo moi vao file cu: quyet dinh cu thang khi trung hash; approved_by luon reset (ham thuan; score dat lai
    CANARY_GATE_APPROVER chi sau khi lo moi qua cong)."""
    if old.source_id != new.source_id:
        raise ValueError(f"khac nguon: {old.source_id!r} vs {new.source_id!r}")
    return Decisions(
        source_id=old.source_id,
        reviewed_at=new.reviewed_at or old.reviewed_at,
        approved_by="",
        decisions={**new.decisions, **old.decisions},
    )


def apply_decision(content: str, decision: Dict[str, Any]) -> Tuple[Optional[str], str]:
    """Ap quyet dinh len `content` -> (noi dung moi | None, ly do).

    Ly do tra ve (T021 dung truc tiep): keep -> "keep"; trim -> "trimmed" (khop metadata.review);
    drop -> `reason` cua quyet dinh (mac dinh "other"); trim ma than con < MIN_WORDS tu -> "too_short_after_trim".
    `trim` chi cat trong THAN doan (sau dong tieu de dau tien); moi chuoi `remove` phai khop dung mot lan,
    neu khong -> ValueError nem hash cua noi dung goc.
    """
    verdict = decision.get("verdict")
    if verdict == "keep":
        return content, "keep"
    if verdict == "drop":
        return None, decision.get("reason") or "other"
    if verdict != "trim":
        raise ValueError(f"verdict khong hop le: {verdict!r} (hash {content_hash(content)})")

    head, sep, body = content.partition(SEP)
    if not sep:  # khong co dong tieu de: coi ca noi dung la than
        head, body = "", content
    for text in decision.get("remove") or []:
        found = body.count(text) if text else 0
        if found != 1:
            raise ValueError(
                f"trim: chuoi {text!r} khop {found} lan (can dung 1) trong doan hash {content_hash(content)}"
            )
        body = body.replace(text, "", 1)
    body = re.sub(r"\n{3,}", SEP, body).strip()
    if prose_word_count(body) < MIN_WORDS:
        return None, "too_short_after_trim"
    return (head + SEP + body if sep else body), "trimmed"


def _validate_decision(key: str, decision: Any) -> None:
    if not isinstance(decision, dict) or decision.get("verdict") not in VERDICTS:
        raise ValueError(f"quyet dinh {key}: verdict phai la mot trong {VERDICTS}")
    if decision["verdict"] == "trim":
        remove = decision.get("remove")
        if not isinstance(remove, list) or not remove or not all(isinstance(s, str) and s for s in remove):
            raise ValueError(f"quyet dinh {key}: trim can `remove` la danh sach chuoi khong rong")
