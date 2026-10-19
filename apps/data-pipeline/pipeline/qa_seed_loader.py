"""Doc cap Q&A tu cac thu muc nguon, moi thu muc gan voi mot dataset.

- data/seeds/interview_qa/*.json  -> de_interview_qa (seed curated, commit)
- data/raw/enriched_qa/*.json     -> de_crawled_qa (crawl + dich boi enrich, khong commit)
Moi file la mot mang cap Q&A; gop theo thu tu ten. Giu (file, vi tri) de bao loi dung cho.
Dinh dang: specs/005-rag-knowledge-base-qa/contracts/qa-seed-format.md.
"""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List, Tuple

from .settings import CURATED_DATASET


class SeedError(RuntimeError):
    pass


@dataclass(frozen=True)
class SeedItem:
    data: Any  # dict khi dung dinh dang; kieu khac de qa_seed_rules bao loi schema
    file: str
    index: int
    dataset: str = CURATED_DATASET

    @property
    def qa_id(self) -> str:
        if isinstance(self.data, dict) and isinstance(self.data.get("qa_id"), str):
            return self.data["qa_id"]
        return f"{self.file}#{self.index}"


def _load_dir(directory: Path, dataset: str) -> List[SeedItem]:
    items: List[SeedItem] = []
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SeedError(f"{path.name}:{exc.lineno}:{exc.colno}: JSON loi: {exc.msg}") from exc
        if not isinstance(data, list):
            raise SeedError(f"{path.name}: phai la mang JSON cac cap Q&A")
        items.extend(SeedItem(data=entry, file=path.name, index=i, dataset=dataset) for i, entry in enumerate(data))
    return items


def load_seed_items(sources: Iterable[Tuple[Path, str]]) -> List[SeedItem]:
    """sources = [(thu muc, dataset)]; thu muc khong ton tai duoc bo qua, tong 0 file la loi."""
    sources = list(sources)
    items = [item for directory, dataset in sources if Path(directory).is_dir() for item in _load_dir(Path(directory), dataset)]
    if not items:
        raise SeedError("khong co cap Q&A nao trong: " + ", ".join(str(d) for d, _ in sources))
    return items
