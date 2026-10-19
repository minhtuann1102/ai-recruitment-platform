"""Thong ke moi lan chay process / index (FR-016, constitution V): in ra va ghi JSON vao data/processed/."""
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, TextIO

from .settings import PROCESSED_DIR


@dataclass
class RunReport:
    command: str
    records_in: int = 0
    records_rejected: List[Dict] = field(default_factory=list)  # [{qa_id, reasons}]
    chunks_out: int = 0
    duplicates_dropped: int = 0
    index: Dict[str, object] = field(default_factory=dict)  # bo dem cua lenh index (T034)

    @property
    def dedup_ratio(self) -> float:
        before = self.chunks_out + self.duplicates_dropped
        return self.duplicates_dropped / before if before else 0.0

    def to_dict(self) -> Dict:
        return {**asdict(self), "dedup_ratio": round(self.dedup_ratio, 4)}

    def print(self, stream: TextIO = sys.stdout) -> None:
        print(f"== {self.command}: thong ke", file=stream)
        print(f"records_in        {self.records_in}", file=stream)
        print(f"records_rejected  {len(self.records_rejected)}", file=stream)
        for rejected in self.records_rejected:
            print(f"  - {rejected['qa_id']}: {'; '.join(rejected['reasons'])}", file=stream)
        print(f"chunks_out        {self.chunks_out}", file=stream)
        print(f"dedup_ratio       {self.dedup_ratio:.2%} ({self.duplicates_dropped} ban ghi trung)", file=stream)
        for key, value in self.index.items():
            print(f"{key:<17} {value}", file=stream)

    def write(self, out_dir: Path = PROCESSED_DIR) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = out_dir / f"run-report-{self.command}-{stamp}.json"
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path
