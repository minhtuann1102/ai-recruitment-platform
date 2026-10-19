"""Bien cap Q&A hop le thanh ban ghi san sang embed (US2, contracts/knowledge-chunks-io.md).

Moi cap -> dung 2 ban ghi: `question` (chi cau hoi) va `qa_pair` (cau hoi + dap an), cung qa_id
va phan loai. Dedup theo content_hash truoc embed (FR-008), giu ban ghi dau theo (qa_id, chunk_type).
"""
import hashlib
from typing import Dict, List, Tuple

from .qa_seed_loader import SeedItem
from .qa_seed_rules import SELF_SOURCE
from .settings import DATASET, SOURCE_TYPE
from .text_cleaning import clean_text


def content_hash(content: str) -> str:
    """md5(lower(strip(content))) tren content da lam sach (NFC) — khop comment DDL (research R3)."""
    return hashlib.md5(content.strip().lower().encode("utf-8")).hexdigest()


def _records_for_pair(item: SeedItem, topics: Dict[str, str]) -> List[Dict]:
    pair = item.data
    question = clean_text(pair["question"])
    answer = clean_text(pair["answer"])
    records = []
    for chunk_type, content in (("qa_pair", f"{question}\n\n{answer}"), ("question", question)):
        records.append(
            {
                "content": content,
                "content_hash": content_hash(content),
                "source_type": SOURCE_TYPE,
                "category": topics[pair["topic_id"]],
                "difficulty": pair["difficulty"],
                "topic_id": pair["topic_id"],
                "language": pair["language"],
                "metadata": {
                    "qa_id": pair["qa_id"],
                    "chunk_type": chunk_type,
                    "dataset": DATASET,
                    "tags": list(pair.get("tags", [])),
                    "source_url": None if pair["source"] == SELF_SOURCE else pair["source"],
                    "license": pair["license"],
                    "synthetic": pair["synthetic"],
                },
            }
        )
    return records


def build_records(pairs: List[SeedItem], topics: Dict[str, str]) -> Tuple[List[Dict], int]:
    """Tra ve (ban ghi sap theo (qa_id, chunk_type) da dedup, so ban ghi bi dedup)."""
    records = [r for item in pairs for r in _records_for_pair(item, topics)]
    records.sort(key=lambda r: (r["metadata"]["qa_id"], r["metadata"]["chunk_type"]))
    seen, kept = set(), []
    for record in records:
        if record["content_hash"] not in seen:
            seen.add(record["content_hash"])
            kept.append(record)
    return kept, len(records) - len(kept)
