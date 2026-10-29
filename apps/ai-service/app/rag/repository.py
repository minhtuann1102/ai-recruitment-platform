"""Doc ai_db.knowledge_chunks bang psycopg 3 (async). Chi doc: phien DB dat read-only (FR-010 spec 005).

SQL theo contract knowledge-chunks-io (spec 005): cosine `<=>`, diem = 1 - khoang cach, luon loc embedding_model.
Tim theo tu khoa (hybrid) chay BM25 trong bo nho (app/rag/bm25_index.py) tren corpus doc mot lan (CORPUS_SQL).
"""
import asyncio
import logging
from typing import Any, Callable, List, Optional, Sequence, Tuple

import psycopg
from psycopg_pool import AsyncConnectionPool, PoolTimeout

from .models import Chunk, SearchFilters
from .question_bank import BankEntry
from .settings import RagSettings

log = logging.getLogger("ai_service.rag")

# Chi doc; truy van treo (mang dut giua chung) thi server huy sau 15 s thay vi giu ket noi / thread mai mai
READ_ONLY = "-c default_transaction_read_only=on -c statement_timeout=15000"
KEEPALIVES = {"keepalives": 1, "keepalives_idle": 30, "keepalives_interval": 10, "keepalives_count": 3}
# Start chay moi topic cung luc, moi topic 3 truy van (topic, vector, kho cau): 4-5 topic ky thuat ~10 truy van.
# Mo san 4 ket noi (mo moi 1.5-1.8 s) de khong xep hang qua han snippet; Supabase session pooler gioi han so client.
POOL_MIN_SIZE, POOL_MAX_SIZE = 4, 8
POOL_MAX_IDLE_S = 60  # dong ket noi ranh (tren min_size) truoc khi pooler cat
# Ket noi min_size khong bi max_idle dong: thay o nen moi 10 phut. Khong dung `check` (do 29/10: moi lan muon ket noi
# them mot vong toi Supabase, truy van 0.24 -> 0.53 s); ket noi da bi pooler cat thi _fetch thu lai mot lan.
POOL_MAX_LIFETIME_S = 600

_COLS = ("id::text, content, source_type, topic_id, category, difficulty, "
         "metadata->>'qa_id', metadata->>'chunk_type', metadata->>'source_url'")

# Q&A theo topic_id (khop chinh xac); uu tien dung muc do kho roi theo qa_id cho on dinh
TOPIC_SQL = (f"SELECT {_COLS}, NULL::float8 FROM knowledge_chunks "
             "WHERE source_type = 'interview_qa' AND topic_id = %s AND embedding_model = %s "
             "AND metadata->>'chunk_type' = 'qa_pair' "
             "ORDER BY (difficulty = %s) DESC NULLS LAST, metadata->>'qa_id' LIMIT %s")

PAIR_SQL = (f"SELECT {_COLS}, NULL::float8 FROM knowledge_chunks "
            "WHERE source_type = 'interview_qa' AND metadata->>'qa_id' = %s "
            "AND metadata->>'chunk_type' = 'qa_pair' AND embedding_model = %s LIMIT 1")


# Corpus cho BM25: moi qa_pair cua interview_qa + textbook (chunk question trung qa_id voi qa_pair nen bo)
_CORPUS_WHERE = ("WHERE embedding_model = %s AND "
                 "((source_type = 'interview_qa' AND metadata->>'chunk_type' = 'qa_pair') OR source_type = 'textbook')")
CORPUS_SQL = f"SELECT {_COLS}, NULL::float8 FROM knowledge_chunks {_CORPUS_WHERE}"
# Dau van tay corpus (doi khi them/xoa/sua dong, ke ca metadata): het TTL chi doc lai ca kho khi dau van tay doi
CORPUS_VERSION_SQL = ("SELECT md5(string_agg(md5(ROW(id, content_hash, source_type, category, difficulty, topic_id, "
                      f"metadata)::text), '' ORDER BY id)) FROM knowledge_chunks {_CORPUS_WHERE}")

# Ngan hang cau hoi: cau hoi (chunk question) + cap Q&A cung qa_id theo topic_id; uu tien dung do kho.
# Cot thu 5: do giong (cosine) cua cau hoi voi truy van topic khi co vector (hybrid xep hang), khong thi NULL.
BANK_SQL = ("SELECT q.metadata->>'qa_id', q.content, q.difficulty, p.content, {sim} FROM knowledge_chunks q "
            "JOIN knowledge_chunks p ON p.metadata->>'qa_id' = q.metadata->>'qa_id' "
            "AND p.metadata->>'chunk_type' = 'qa_pair' AND p.embedding_model = q.embedding_model "
            "WHERE q.source_type = 'interview_qa' AND q.topic_id = %s AND q.embedding_model = %s "
            "AND q.metadata->>'chunk_type' = 'question' "
            "ORDER BY (q.difficulty = %s) DESC NULLS LAST, q.metadata->>'qa_id' LIMIT %s")


def vector_literal(vector: Sequence[float]) -> str:
    return "[" + ",".join(f"{float(x):.7g}" for x in vector) + "]"


def _filter_where(filters: SearchFilters, model: str) -> Tuple[List[str], List[Any]]:
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
    return where, params


def build_search_sql(vector: Sequence[float], filters: SearchFilters, model: str,
                     limit: int) -> Tuple[str, List[Any]]:
    where, params = _filter_where(filters, model)
    vec = vector_literal(vector)
    sql = (f"SELECT {_COLS}, 1 - (embedding <=> %s::vector) AS score FROM knowledge_chunks "
           f"WHERE {' AND '.join(where)} ORDER BY embedding <=> %s::vector LIMIT %s")
    return sql, [vec, *params, vec, limit]


def build_bank_sql(topic_id: str, model: str, difficulty: Optional[str], limit: int,
                   vector: Optional[Sequence[float]] = None) -> Tuple[str, List[Any]]:
    if vector is None:
        return BANK_SQL.format(sim="NULL::float8"), [topic_id, model, difficulty, limit]
    return (BANK_SQL.format(sim="1 - (q.embedding <=> %s::vector)"),
            [vector_literal(vector), topic_id, model, difficulty, limit])


def row_to_chunk(row: Sequence[Any]) -> Chunk:
    cid, content, source_type, topic_id, category, difficulty, qa_id, chunk_type, source_url, score = row
    return Chunk(id=cid, content=content, source_type=source_type, topic_id=topic_id, category=category,
                 difficulty=difficulty, qa_id=qa_id, chunk_type=chunk_type,
                 score=None if score is None else float(score), source_url=source_url)


class PgKnowledgeRepository:
    """Doc qua pool ket noi giu san (do 29/10: mo ket noi Supabase moi lan mat 1.5-1.8 s, truy van chi 0.2-0.3 s; hybrid
    chay 3 truy van moi topic va dap an chuan co han 2 s nen khong the mo ket noi moi lan). Pool gan voi event loop da
    mo no: loop khac (test, script eval) thi tao pool moi. `connect` (test): mo ket noi ngan moi lan nhu cu."""

    def __init__(self, settings: RagSettings, connect: Optional[Callable] = None):
        self._settings, self._connect = settings, connect
        self._pool: Optional[AsyncConnectionPool] = None
        self._pool_loop = None

    def _conn_kwargs(self) -> dict:
        return {"autocommit": True, "connect_timeout": self._settings.connect_timeout_s, "options": READ_ONLY,
                **KEEPALIVES}

    async def _get_pool(self) -> AsyncConnectionPool:
        loop = asyncio.get_running_loop()
        if self._pool is None or self._pool_loop is not loop:
            if self._pool is not None:  # pool cua loop cu (script eval chay nhieu asyncio.run): khong dong duoc tu day
                log.info("rag_pool_replaced reason=event_loop_changed")
            self._pool = AsyncConnectionPool(self._settings.db_url, min_size=POOL_MIN_SIZE, max_size=POOL_MAX_SIZE,
                                             open=False, kwargs=self._conn_kwargs(),
                                             timeout=self._settings.connect_timeout_s, max_idle=POOL_MAX_IDLE_S,
                                             max_lifetime=POOL_MAX_LIFETIME_S, name="ai_db_reader")
            self._pool_loop = loop
            await self._pool.open(wait=False)
        return self._pool

    async def _fetch(self, sql: str, params: Sequence[Any], convert: Callable = None) -> List[Any]:
        convert = convert or row_to_chunk
        if self._connect is not None:
            conn = await self._connect(self._settings.db_url, **self._conn_kwargs())
            async with conn:
                cur = await conn.execute(sql, params)
                return [convert(r) for r in await cur.fetchall()]
        for attempt in (1, 2):
            try:
                async with (await self._get_pool()).connection() as conn:
                    cur = await conn.execute(sql, params)
                    return [convert(r) for r in await cur.fetchall()]
            except (PoolTimeout, psycopg.errors.QueryCanceled):  # DB khong toi duoc / server huy: thu lai vo ich
                raise
            except psycopg.OperationalError:
                if attempt == 2:  # ket noi trong pool bi pooler cat (idle): thu lai mot lan voi ket noi moi
                    raise
        return []

    async def close(self) -> None:
        """Luc tat service: tra ket noi ve pooler thay vi de server tu cat."""
        if self._pool is not None:
            pool, self._pool = self._pool, None
            await pool.close()

    async def list_by_topic_id(self, topic_id: str, difficulty: Optional[str], limit: int) -> List[Chunk]:
        return await self._fetch(TOPIC_SQL, [topic_id, self._settings.embedding_model, difficulty, limit])

    async def search(self, vector: Sequence[float], filters: SearchFilters, limit: int) -> List[Chunk]:
        sql, params = build_search_sql(vector, filters, self._settings.embedding_model, limit)
        return await self._fetch(sql, params)

    async def load_corpus(self) -> List[Chunk]:
        """Doc ~4.5 MB mat ~3 s (do 29/10). Chay trong thread voi ket noi dong bo rieng, ngoai pool: khong giu cho cua
        truy van snippet/dap an va khong chan event loop khi doi dong thanh Chunk (do: chan > 0.8 s, request dang chay
        qua han snippet)."""
        if self._connect is not None:
            return await self._fetch(CORPUS_SQL, [self._settings.embedding_model])
        return await asyncio.to_thread(self._load_corpus_sync)

    async def corpus_version(self) -> Optional[str]:
        rows = await self._fetch(CORPUS_VERSION_SQL, [self._settings.embedding_model], lambda r: r[0])
        return rows[0] if rows else None

    def _load_corpus_sync(self) -> List[Chunk]:
        with psycopg.connect(self._settings.db_url, **self._conn_kwargs()) as conn:
            return [row_to_chunk(r) for r in conn.execute(CORPUS_SQL, [self._settings.embedding_model]).fetchall()]

    async def list_bank(self, topic_id: str, difficulty: Optional[str], limit: int,
                        vector: Optional[Sequence[float]] = None) -> List[BankEntry]:
        sql, params = build_bank_sql(topic_id, self._settings.embedding_model, difficulty, limit, vector)
        return await self._fetch(sql, params, lambda r: BankEntry(
            qa_id=r[0], question=r[1], difficulty=r[2], pair=r[3], similarity=None if r[4] is None else float(r[4])))

    async def get_pair_by_qa_id(self, qa_id: str) -> Optional[Chunk]:
        rows = await self._fetch(PAIR_SQL, [qa_id, self._settings.embedding_model])
        return rows[0] if rows else None
