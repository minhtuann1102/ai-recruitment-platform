"""Doc ai_db.knowledge_chunks bang psycopg 3 (async). Chi doc: phien DB dat read-only (FR-010 spec 005).

SQL theo contract knowledge-chunks-io (spec 005): cosine `<=>`, diem = 1 - khoang cach, luon loc embedding_model.
"""
from typing import Any, Callable, List, Optional, Sequence, Tuple

import psycopg

from .models import Chunk, SearchFilters
from .question_bank import BankEntry
from .settings import RagSettings

_COLS = ("id::text, content, source_type, topic_id, category, difficulty, "
         "metadata->>'qa_id', metadata->>'chunk_type'")

# Q&A theo topic_id (khop chinh xac); uu tien dung muc do kho roi theo qa_id cho on dinh
TOPIC_SQL = (f"SELECT {_COLS}, NULL::float8 FROM knowledge_chunks "
             "WHERE source_type = 'interview_qa' AND topic_id = %s AND embedding_model = %s "
             "AND metadata->>'chunk_type' = 'qa_pair' "
             "ORDER BY (difficulty = %s) DESC NULLS LAST, metadata->>'qa_id' LIMIT %s")

PAIR_SQL = (f"SELECT {_COLS}, NULL::float8 FROM knowledge_chunks "
            "WHERE source_type = 'interview_qa' AND metadata->>'qa_id' = %s "
            "AND metadata->>'chunk_type' = 'qa_pair' AND embedding_model = %s LIMIT 1")


# Ngan hang cau hoi: cau hoi (chunk question) + cap Q&A cung qa_id theo topic_id; uu tien dung do kho
BANK_SQL = ("SELECT q.metadata->>'qa_id', q.content, q.difficulty, p.content FROM knowledge_chunks q "
            "JOIN knowledge_chunks p ON p.metadata->>'qa_id' = q.metadata->>'qa_id' "
            "AND p.metadata->>'chunk_type' = 'qa_pair' AND p.embedding_model = q.embedding_model "
            "WHERE q.source_type = 'interview_qa' AND q.topic_id = %s AND q.embedding_model = %s "
            "AND q.metadata->>'chunk_type' = 'question' "
            "ORDER BY (q.difficulty = %s) DESC NULLS LAST, q.metadata->>'qa_id' LIMIT %s")


def vector_literal(vector: Sequence[float]) -> str:
    return "[" + ",".join(f"{float(x):.7g}" for x in vector) + "]"


def build_search_sql(vector: Sequence[float], filters: SearchFilters, model: str,
                     limit: int) -> Tuple[str, List[Any]]:
    where, params = ["source_type = ANY(%s)", "embedding_model = %s"], [list(filters.source_types), model]
    if filters.category:
        where.append("category = %s")
        params.append(filters.category)
    if filters.difficulty:
        where.append("(difficulty = %s OR difficulty IS NULL)")
        params.append(filters.difficulty)
    if filters.chunk_type:
        where.append("(source_type <> 'interview_qa' OR metadata->>'chunk_type' = %s)")
        params.append(filters.chunk_type)
    vec = vector_literal(vector)
    sql = (f"SELECT {_COLS}, 1 - (embedding <=> %s::vector) AS score FROM knowledge_chunks "
           f"WHERE {' AND '.join(where)} ORDER BY embedding <=> %s::vector LIMIT %s")
    return sql, [vec, *params, vec, limit]


def row_to_chunk(row: Sequence[Any]) -> Chunk:
    cid, content, source_type, topic_id, category, difficulty, qa_id, chunk_type, score = row
    return Chunk(id=cid, content=content, source_type=source_type, topic_id=topic_id, category=category,
                 difficulty=difficulty, qa_id=qa_id, chunk_type=chunk_type,
                 score=None if score is None else float(score))


class PgKnowledgeRepository:
    """Moi lan goi mo mot ket noi ngan (RAG chi chay luc lap plan va tra dap an, so lan goi it)."""

    def __init__(self, settings: RagSettings, connect: Optional[Callable] = None):
        self._settings = settings
        self._connect = connect or psycopg.AsyncConnection.connect

    async def _fetch(self, sql: str, params: Sequence[Any], convert: Callable = None) -> List[Any]:
        conn = await self._connect(self._settings.db_url, autocommit=True,
                                   connect_timeout=self._settings.connect_timeout_s,
                                   options="-c default_transaction_read_only=on")
        async with conn:
            cur = await conn.execute(sql, params)
            return [(convert or row_to_chunk)(r) for r in await cur.fetchall()]

    async def list_by_topic_id(self, topic_id: str, difficulty: Optional[str], limit: int) -> List[Chunk]:
        return await self._fetch(TOPIC_SQL, [topic_id, self._settings.embedding_model, difficulty, limit])

    async def search(self, vector: Sequence[float], filters: SearchFilters, limit: int) -> List[Chunk]:
        sql, params = build_search_sql(vector, filters, self._settings.embedding_model, limit)
        return await self._fetch(sql, params)

    async def list_bank(self, topic_id: str, difficulty: Optional[str], limit: int) -> List[BankEntry]:
        return await self._fetch(BANK_SQL, [topic_id, self._settings.embedding_model, difficulty, limit],
                                 lambda r: BankEntry(qa_id=r[0], question=r[1], difficulty=r[2], pair=r[3]))

    async def get_pair_by_qa_id(self, qa_id: str) -> Optional[Chunk]:
        rows = await self._fetch(PAIR_SQL, [qa_id, self._settings.embedding_model])
        return rows[0] if rows else None
