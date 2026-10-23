"""Truy hoi chi doc de DE kiem chung (search / eval) — dung hop dong doc trong contracts/knowledge-chunks-io.md.

Khong thay retrieve() cua AIE (research R1). Cosine `<=>`, luon loc embedding_model, lay du 4k roi
giu ban ghi diem cao nhat moi qa_id (rag-design §4) truoc khi cat con k.
"""
import sys
from typing import Dict, List, Optional, Sequence, Tuple

from .knowledge_chunk_writer import vector_literal
from .settings import SOURCE_TYPE

OVERFETCH = 4
FILTER_COLUMNS = {"category": "category", "difficulty": "difficulty", "topic_id": "topic_id", "chunk_type": "metadata->>'chunk_type'"}


def build_search_sql(filters: Dict[str, Optional[str]], stored_model: str, query_vector: Sequence[float], limit: int) -> Tuple[str, list]:
    where, params = ["source_type = %s", "embedding_model = %s"], [SOURCE_TYPE, stored_model]
    for key, column in FILTER_COLUMNS.items():
        if filters.get(key):
            where.append(f"{column} = %s")
            params.append(filters[key])
    vector = vector_literal(query_vector)
    sql = (
        "SELECT id, content, 1 - (embedding <=> %s::vector) AS score, metadata->>'qa_id', metadata->>'chunk_type', "
        "topic_id, category, difficulty FROM knowledge_chunks WHERE " + " AND ".join(where) +
        " ORDER BY embedding <=> %s::vector LIMIT %s"
    )
    return sql, [vector, *params, vector, limit]


def dedup_by_qa_id(rows: List[Dict], k: int) -> List[Dict]:
    """rows da sap theo diem giam dan; giu ban ghi dau tien moi qa_id."""
    seen, result = set(), []
    for row in rows:
        if row["qa_id"] not in seen:
            seen.add(row["qa_id"])
            result.append(row)
        if len(result) == k:
            break
    return result


def search(conn, query_vector: Sequence[float], filters: Dict[str, Optional[str]], stored_model: str, k: int = 5) -> List[Dict]:
    sql, params = build_search_sql(filters, stored_model, query_vector, k * OVERFETCH)
    with conn.cursor() as cur:
        cur.execute(sql, params)
        keys = ("id", "content", "score", "qa_id", "chunk_type", "topic_id", "category", "difficulty")
        rows = [dict(zip(keys, row)) for row in cur.fetchall()]
    results = dedup_by_qa_id(rows, k)
    # FR-017: log qa_id + diem moi lan truy hoi de chon nguong sau nay
    print("search " + " ".join(f"{r['qa_id']}:{r['score']:.3f}" for r in results), file=sys.stderr)
    return results
