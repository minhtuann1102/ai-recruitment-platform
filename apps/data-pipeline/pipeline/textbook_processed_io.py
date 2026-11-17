"""Doc / ghi file JSONL cua textbook (spec 012, data-model §1): trang tho va doan da xu ly (+ khoa quyet dinh).

Duong dan doc tu `settings` luc goi (khong chup luc import) de test doi duoc thu muc du lieu.
"""
import json
import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from . import settings


def processed_path(source_id: str) -> Path:
    return Path(settings.TEXTBOOK_PROCESSED_DIR) / f"{source_id}.jsonl"


def latest_raw_file(source_id: str) -> Optional[Path]:
    """File thô moi nhat cua nguon; ten file la moc UTC (YYYYMMDDTHHMMSSZ) nen sap theo ten = sap theo thoi gian."""
    directory = Path(settings.TEXTBOOK_RAW_DIR) / source_id
    files = sorted(directory.glob("*.jsonl")) if directory.is_dir() else []
    return files[-1] if files else None


def read_jsonl(path: Path) -> List[Dict]:
    """Moi dong khong rong la mot JSON object; dong hong -> ValueError nem ten file va so dong."""
    rows: List[Dict] = []
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}: dong {number} khong phai JSON ({exc})") from exc
    return rows


def write_jsonl(path: Path, rows: Iterable[Dict]) -> None:
    """Ghi nguyen tu (tmp roi replace), UTF-8, newline '\\n': cung noi dung -> file giong het tung byte."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    os.replace(tmp, path)


def read_processed(source_id: str) -> List[Dict]:
    """Cac ban ghi cua mot nguon theo thu tu file. File chua co -> FileNotFoundError; dong hong / thieu truong -> ValueError."""
    path = processed_path(source_id)
    records = read_jsonl(path)
    for number, record in enumerate(records, start=1):
        if not record.get("content") or not record.get("content_hash"):
            raise ValueError(f"{path.name}: ban ghi thu {number} thieu content / content_hash")
    return records


def original_hash(record: Dict) -> str:
    """Hash cua noi dung TRUOC khi ap trim: khoa quyet dinh trong file decisions."""
    return (record.get("metadata") or {}).get("original_hash") or record["content_hash"]
