"""Doc lo (batch-*.json) va judgments (.jsonl) cho scope-check-score, kiem tra tung dong judgment.

Mot dong judgments: {"item_id", "judge", "points": [{"id", "status"}], "proposed_fix"?, "summary_vi"?}.
Dong sai (JSON hong, thieu judge, item_id la, thieu / thua / trung id y, status la) bi loai CA DONG va ghi vao errors:
item do tinh la thieu (missing) cua judge de duoc cham lai, khong de dong nua dung anh huong co. Trung (judge, item_id):
giu dong hop le dau tien. Ten judge lay tu truong `judge`, khong tu ten file.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

from .qa_scope_check_points import BATCH_GLOB, FLAGGING_STATUSES, MANIFEST_NAME, STATUSES, ScopeCheckError

OPTIONAL_FIELDS = ("proposed_fix", "summary_vi")


@dataclass
class Judgments:
    by_judge: Dict[str, Dict[str, Dict[str, Any]]] = field(default_factory=dict)  # judge -> item_id -> dong hop le
    judges: Set[str] = field(default_factory=set)  # ca judge chi co dong sai
    errors: List[str] = field(default_factory=list)


def load_manifest_ids(batches_dir: Path) -> List[str]:
    """item_ids that (do prepare sinh) cua manifest.json. Item cai (canary) duoc chen vao lo SAU prepare nen khong co o day."""
    path = Path(batches_dir) / MANIFEST_NAME
    try:
        ids = json.loads(path.read_text(encoding="utf-8-sig"))["item_ids"]
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise ScopeCheckError(f"khong doc duoc {path} ({type(exc).__name__}: {exc}); chay scope-check-prepare truoc") from exc
    if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
        raise ScopeCheckError(f"{path}: item_ids phai la mang chuoi")
    return ids


def load_batch_items(batches_dir: Path) -> Dict[str, List[str]]:
    """{item_id: [id cac y theo thu tu]} tu moi batch-*.json, ke ca file lo them (chua canary)."""
    files = sorted(Path(batches_dir).glob(BATCH_GLOB))
    if not files:
        raise ScopeCheckError(f"khong co {BATCH_GLOB} trong {batches_dir}")
    items: Dict[str, List[str]] = {}
    for path in files:
        try:
            batch = json.loads(path.read_text(encoding="utf-8-sig"))
            for item in batch:
                if item["item_id"] in items:
                    raise ScopeCheckError(f"{path.name}: item_id trung giua cac lo: {item['item_id']}")
                items[item["item_id"]] = [point["id"] for point in item["points"]]
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise ScopeCheckError(f"{path.name}: lo hong ({type(exc).__name__}: {exc})") from exc
    return items


def check_record(record: Any, items: Dict[str, List[str]]) -> Optional[str]:
    """Ly do dong judgment sai, hoac None neu hop le."""
    if not isinstance(record, dict):
        return "dong khong phai object JSON"
    if not isinstance(record.get("judge"), str) or not record["judge"].strip():
        return "thieu judge"
    item_id = record.get("item_id")
    if not isinstance(item_id, str) or item_id not in items:
        return f"item_id la: {item_id!r}"
    points = record.get("points")
    if not isinstance(points, list) or not all(isinstance(p, dict) for p in points):
        return f"{item_id}: points phai la mang object"
    ids = [p.get("id") for p in points]
    known = items[item_id]
    unknown = [i for i in ids if i not in known]
    if unknown:
        return f"{item_id}: id y la {unknown}"
    if len(set(ids)) != len(ids):
        return f"{item_id}: id y bi lap"
    if set(known) - set(ids):
        return f"{item_id}: thieu id y {sorted(set(known) - set(ids))}"
    bad = [p.get("status") for p in points if p.get("status") not in STATUSES]
    if bad:
        return f"{item_id}: status khong hop le {bad} (chon {', '.join(STATUSES)})"
    return None


def read_judgments(paths: Iterable[Path], items: Dict[str, List[str]]) -> Judgments:
    result = Judgments()
    for path in paths:
        try:
            lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
        except OSError as exc:
            raise ScopeCheckError(f"khong doc duoc {path}: {exc}") from exc
        for number, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            where = f"{Path(path).name}:{number}"
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                result.errors.append(f"{where}: JSON hong ({exc.msg})")
                continue
            if isinstance(record, dict) and isinstance(record.get("judge"), str) and record["judge"].strip():
                result.judges.add(record["judge"].strip())
            reason = check_record(record, items)
            if reason:
                result.errors.append(f"{where}: {reason}")
                continue
            judge, item_id = record["judge"].strip(), record["item_id"]
            rows = result.by_judge.setdefault(judge, {})
            if item_id in rows:
                result.errors.append(f"{where}: {item_id} bi cham lan nua boi {judge}; giu dong dau")
                continue
            status = {p["id"]: p["status"] for p in record["points"]}
            rows[item_id] = {"flagged_points": [i for i in items[item_id] if status[i] in FLAGGING_STATUSES],
                             **{k: record[k] for k in OPTIONAL_FIELDS if record.get(k) is not None}}
    return result
