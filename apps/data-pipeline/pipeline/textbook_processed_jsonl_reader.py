"""Doc doan da xu ly cua mot nguon cho review-textbook-prepare va coverage-textbook (spec 012, data-model §3).

Dung processed_path / read_jsonl cua textbook_processed_io; them kiem truong toi thieu moi lenh can doc.
"""
from typing import Dict, List

from .textbook_processed_io import processed_path, read_jsonl


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
