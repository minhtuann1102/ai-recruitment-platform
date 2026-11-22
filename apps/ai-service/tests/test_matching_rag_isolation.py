"""017 US2 T017 (SC-006, FR-004): RAG phong van khong bao gio tra ban ghi job_description.

JD nam chung bang knowledge_chunks voi Q&A / textbook (source_type = 'job_description'). Moi duong doc cua RAG
(app/rag/repository.py, bm25_index.py, models.SearchFilters) phai loc source_type; neu ai them mot duong doc moi ma khong
loc thi test nay do.
"""
import asyncio
import re
from pathlib import Path

import pytest

from app.rag import repository
from app.rag.bm25_index import Bm25Index
from app.rag.models import Chunk, SearchFilters
from app.rag.repository import PgKnowledgeRepository, build_bank_sql, build_search_sql
from app.rag.settings import load_rag_settings

RAG_DIR = Path(repository.__file__).resolve().parent
RAG_SOURCE_TYPES = {"interview_qa", "textbook"}
SQL_CONSTANTS = {name: value for name, value in vars(repository).items()
                 if name.endswith("_SQL") and isinstance(value, str) and "knowledge_chunks" in value}


def test_the_repository_has_sql_constants_to_check():
    assert {"TOPIC_SQL", "PAIR_SQL", "CORPUS_SQL", "CORPUS_VERSION_SQL", "BANK_SQL", "COVERAGE_SQL"} <= set(SQL_CONSTANTS)


@pytest.mark.parametrize("name", sorted(SQL_CONSTANTS))
def test_every_sql_constant_filters_source_type_and_never_names_job_description(name):
    sql = SQL_CONSTANTS[name]
    assert "job_description" not in sql
    assert re.search(r"source_type\s*=\s*'", sql) or "source_type = ANY(%s)" in sql, f"{name} khong loc source_type"
    literals = set(re.findall(r"source_type\s*=\s*'(\w+)'", sql))
    assert literals <= RAG_SOURCE_TYPES


def test_built_sql_filters_source_type_from_parameters_excluding_job_description():
    sql, params = build_search_sql([0.1] * 3, SearchFilters(), "text-embedding-3-small", 5)
    assert "source_type = ANY(%s)" in sql
    source_types = next(p for p in params if isinstance(p, list))
    assert set(source_types) == RAG_SOURCE_TYPES and "job_description" not in source_types
    bank_sql, _ = build_bank_sql("java.x", "text-embedding-3-small", "easy", 3)
    assert "q.source_type = 'interview_qa'" in bank_sql


def test_default_search_filters_exclude_job_description():
    assert set(SearchFilters().source_types) == RAG_SOURCE_TYPES
    assert "job_description" not in SearchFilters().source_types


def test_no_other_rag_module_reads_the_table_directly():
    # moi duong doc di qua repository.py (da kiem o tren); file moi nhac knowledge_chunks thi phai vao danh sach nay
    readers = {p.name for p in RAG_DIR.glob("*.py") if "FROM knowledge_chunks" in p.read_text(encoding="utf-8")
               or "JOIN knowledge_chunks" in p.read_text(encoding="utf-8")}
    assert readers == {"repository.py"}


def chunk(cid, source_type, text="spring boot transaction isolation"):
    return Chunk(id=cid, content=text, source_type=source_type, topic_id=None, category=None, difficulty=None,
                 qa_id=None, chunk_type=None)


def test_bm25_index_never_returns_job_description_chunks():
    chunks = [chunk("qa", "interview_qa"), chunk("tb", "textbook"), chunk("jd", "job_description"),
              chunk("jd2", "job_description", "spring boot transaction isolation developer")]
    index = Bm25Index(chunks)
    for filters in (SearchFilters(), SearchFilters(source_types=("interview_qa", "textbook")),
                    SearchFilters(source_types=("interview_qa",))):
        got = index.search("spring boot transaction isolation", filters, 10)
        assert got and all(c.source_type != "job_description" for c in got)
    assert {c.id for c in index.search("spring boot", SearchFilters(), 10)} == {"qa", "tb"}


class _Cursor:
    async def fetchall(self):
        return []


class _Conn:
    def __init__(self):
        self.executed = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def execute(self, sql, params):
        self.executed.append((sql, params))
        return _Cursor()


def test_repository_search_with_default_filters_sends_no_job_description_to_the_db():
    conn = _Conn()

    async def connect(dsn, **kw):
        return conn

    repo = PgKnowledgeRepository(load_rag_settings({"RAG_ENABLED": "1", "AI_DB_URL": "postgresql://ro@h/ai_db"}),
                                 connect)
    asyncio.run(repo.search([0.1] * 4, SearchFilters(), 5))
    asyncio.run(repo.load_corpus())
    asyncio.run(repo.list_by_topic_id("java.x", "easy", 3))
    assert len(conn.executed) == 3
    for sql, params in conn.executed:
        assert "job_description" not in sql
        assert not any(isinstance(p, list) and "job_description" in p for p in params)
