"""Doc seed Q&A curated: moi file data/seeds/interview_qa/*.json la mot mang cap Q&A.

Gop cac file theo thu tu ten; giu (file, vi tri) de thong bao loi chi dung cho can sua.
Dinh dang tung cap: specs/005-rag-knowledge-base-qa/contracts/qa-seed-format.md.
"""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List

from .settings import SEEDS_DIR


class SeedError(RuntimeError):
    pass


@dataclass(frozen=True)
class SeedItem:
    data: Any  # dict khi dung dinh dang; kieu khac de qa_seed_rules bao loi schema
    file: str
    index: int

    @property
    def qa_id(self) -> str:
        if isinstance(self.data, dict) and isinstance(self.data.get("qa_id"), str):
            return self.data["qa_id"]
        return f"{self.file}#{self.index}"


def load_seed_items(seeds_dir: Path = SEEDS_DIR) -> List[SeedItem]:
    files = sorted(Path(seeds_dir).glob("*.json"))
    if not files:
        raise SeedError(f"khong co file *.json trong {seeds_dir}")
    items: List[SeedItem] = []
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SeedError(f"{path.name}:{exc.lineno}:{exc.colno}: JSON loi: {exc.msg}") from exc
        if not isinstance(data, list):
            raise SeedError(f"{path.name}: phai la mang JSON cac cap Q&A")
        items.extend(SeedItem(data=entry, file=path.name, index=i) for i, entry in enumerate(data))
    return items
