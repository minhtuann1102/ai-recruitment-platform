"""Duong ghi duy nhat vao ai_db.knowledge_chunks (FR-010..FR-016, research R4, contracts/knowledge-chunks-io.md).

1. preflight (khong goi API): co extension vector va bang knowledge_chunks
2. tra hash da co -> plan_writes (ham thuan): new | update cung dataset | skip dataset khac
3. co ban ghi moi: embed thu, roi embed + INSERT theo batch, commit tung batch
4. UPDATE cot phan loai + content cho hash da co cung dataset (khong embed lai)
5. don ban ghi cung dataset khong con trong lan chay — chi khi 0 loi embedding
Khong tao / sua bang (FR-011).
"""
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Sequence

from psycopg.types.json import Jsonb

from .settings import SOURCE_TYPE

_INSERT_SQL = """
INSERT INTO knowledge_chunks
  (content, content_hash, embedding, embedding_model, source_type, category, difficulty, topic_id, language, metadata)
VALUES (%s, %s, %s::vector, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (content_hash) DO NOTHING
"""
_UPDATE_SQL = """
UPDATE knowledge_chunks
SET content = %s, category = %s, difficulty = %s, topic_id = %s, language = %s, metadata = %s
WHERE content_hash = %s AND metadata->>'dataset' = %s
"""
_DELETE_SQL = """
DELETE FROM knowledge_chunks
WHERE source_type = %s AND metadata->>'dataset' = %s AND NOT (content_hash = ANY(%s))
"""


class PreflightError(RuntimeError):
    pass


@dataclass
class WritePlan:
    new: List[Dict] = field(default_factory=list)
    update: List[Dict] = field(default_factory=list)
    skip_other: List[Dict] = field(default_factory=list)
    keep_hashes: Dict[str, List[str]] = field(default_factory=dict)  # dataset -> hash cua lan chay


def plan_writes(records: Sequence[Dict], existing: Dict[str, str]) -> WritePlan:
    """existing = {content_hash: dataset} cua ban ghi da co trong kho."""
    plan = WritePlan()
    keep: Dict[str, List[str]] = defaultdict(list)
    for record in records:
        content_hash, dataset = record["content_hash"], record["metadata"]["dataset"]
        keep[dataset].append(content_hash)
        if content_hash not in existing:
            plan.new.append(record)
        elif existing[content_hash] == dataset:
            plan.update.append(record)
        else:
            plan.skip_other.append(record)
    plan.keep_hashes = dict(keep)
    return plan


def preflight(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        if cur.fetchone() is None:
            raise PreflightError("ai_db chua co extension vector — chay ha tang 001 (docker compose up, make db-ensure)")
        cur.execute("SELECT to_regclass('public.knowledge_chunks')")
        if cur.fetchone()[0] is None:
            raise PreflightError("ai_db chua co bang knowledge_chunks — chay ha tang 001 (scripts/init-databases.sh)")


def existing_hashes(conn, hashes: Sequence[str]) -> Dict[str, str]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT content_hash, metadata->>'dataset' FROM knowledge_chunks WHERE content_hash = ANY(%s)", (list(hashes),)
        )
        return {row[0].strip(): row[1] for row in cur.fetchall()}


def vector_literal(vector: Sequence[float]) -> str:
    return "[" + ",".join(repr(float(v)) for v in vector) + "]"


def _row(record: Dict) -> tuple:
    return (record["category"], record["difficulty"], record["topic_id"], record["language"], Jsonb(record["metadata"]))


def write_records(conn, plan: WritePlan, embed: Callable[[Sequence[str]], List[List[float]]], stored_model: str,
                  batch_size: int = 100) -> Dict[str, object]:
    """Thuc thi plan; tra bo dem cho run report. embed loi o batch nao thi dem batch do, chay tiep."""
    stats: Dict[str, object] = {"embedded": 0, "embed_errors": 0, "inserted": 0, "updated": 0,
                                "skipped_other_dataset": len(plan.skip_other), "deleted": 0}
    with conn.cursor() as cur:
        for start in range(0, len(plan.new), batch_size):
            batch = plan.new[start : start + batch_size]
            try:
                vectors = embed([r["content"] for r in batch])
            except Exception:  # loi provider sau retry cua SDK: dem, khong ghi do dang
                stats["embed_errors"] += len(batch)
                continue
            stats["embedded"] += len(batch)
            for record, vector in zip(batch, vectors):
                cur.execute(_INSERT_SQL, (record["content"], record["content_hash"], vector_literal(vector), stored_model,
                                          record["source_type"], *_row(record)))
                stats["inserted"] += cur.rowcount
            conn.commit()
        for record in plan.update:
            cur.execute(_UPDATE_SQL, (record["content"], *_row(record), record["content_hash"], record["metadata"]["dataset"]))
            stats["updated"] += cur.rowcount
        conn.commit()
        if stats["embed_errors"]:
            stats["cleanup"] = "skipped (embed_errors > 0)"
            return stats
        for dataset, hashes in plan.keep_hashes.items():
            cur.execute(_DELETE_SQL, (SOURCE_TYPE, dataset, hashes))
            stats["deleted"] += cur.rowcount
        conn.commit()
    stats["cleanup"] = "done"
    return stats
