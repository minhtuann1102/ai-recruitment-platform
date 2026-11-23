"""017 US2 T017 (SC-006, FR-004): RAG phong van khong bao gio tra ban ghi job_description.

JD nam chung bang knowledge_chunks voi Q&A / textbook (source_type = 'job_description'). Moi duong doc cua RAG
(app/rag/repository.py, bm25_index.py, models.SearchFilters) phai loc source_type CHAT: moi lan `source_type` xuat hien
trong SQL doc kho phai la `= '<interview_qa|textbook>'` hoac `= ANY(%s)` (tham so la SearchFilters.source_types), khong
`<>`, `!=`, `NOT`, `IS NOT NULL`, `OR true`. Chi repository.py (RAG) va matching/job_index.py (goi y viec lam) duoc doc bang;
them mot duong doc moi ma khong loc thi test nay do.
"""
import asyncio
import re
from pathlib import Path

import pytest

import app
from app.matching import job_index
from app.rag import repository
from app.rag.bm25_index import Bm25Index
from app.rag.models import Chunk, SearchFilters
from app.rag.repository import PgKnowledgeRepository, build_bank_sql, build_search_sql
from app.rag.settings import load_rag_settings

APP_DIR = Path(app.__file__).resolve().parent
RAG_SOURCE_TYPES = {"interview_qa", "textbook"}
READERS_ALLOWED = {"rag/repository.py", "matching/job_index.py"}
SQL_CONSTANTS = {name: value for name, value in vars(repository).items()
                 if name.endswith("_SQL") and isinstance(value, str) and "knowledge_chunks" in value}
# moi lan source_type dung de SO SANH (cot trong danh sach SELECT / ROW(...) di sau boi dau phay thi khong tinh)
SOURCE_TYPE = re.compile(r"source_type(?!\s*[,)])", re.I)
STRICT_FILTER = re.compile(r"source_type\s*=\s*(?:'(\w+)'|ANY\(%s\))", re.I)  # chi hai dang nay duoc phep
TAUTOLOGY = re.compile(r"\bOR\s+\(?\s*(?:true|1\s*=\s*1)\b|\bNOT\b|<>|!=", re.I)
TABLE_READ = re.compile(r"\b(?:from|join|into|update)\s+knowledge_chunks\b", re.I)


def assert_strict_source_filter(sql: str, label: str) -> None:
    occurrences = len(SOURCE_TYPE.findall(sql))
    allowed = STRICT_FILTER.findall(sql)
    assert occurrences >= 1, f"{label}: khong loc source_type"
    assert occurrences == len(allowed), f"{label}: source_type dung toan tu khac '=' literal / '= ANY(%s)'"
    assert {lit for lit in allowed if lit} <= RAG_SOURCE_TYPES, f"{label}: source_type ngoai RAG"
    assert not TAUTOLOGY.search(sql), f"{label}: co OR true / NOT / <> / != co the mo rong bo loc"
    assert "job_description" not in sql, label


def test_the_repository_has_sql_constants_to_check():
    assert {"TOPIC_SQL", "PAIR_SQL", "CORPUS_SQL", "CORPUS_VERSION_SQL", "BANK_SQL", "COVERAGE_SQL"} <= set(SQL_CONSTANTS)


@pytest.mark.parametrize("name", sorted(SQL_CONSTANTS))
def test_every_rag_sql_constant_filters_source_type_strictly(name):
    assert_strict_source_filter(SQL_CONSTANTS[name], name)


@pytest.mark.parametrize("sql,ok", [
    ("SELECT 1 FROM knowledge_chunks WHERE source_type = 'interview_qa'", True),
    ("SELECT 1 FROM knowledge_chunks WHERE source_type = ANY(%s)", True),
    ("SELECT 1 FROM knowledge_chunks WHERE (source_type = 'interview_qa' AND x) OR source_type = 'textbook'", True),
    ("SELECT 1 FROM knowledge_chunks WHERE source_type = 'interview_qa' OR source_type IS NOT NULL", False),
    ("SELECT 1 FROM knowledge_chunks WHERE source_type = 'interview_qa' OR source_type <> 'x'", False),
    ("SELECT 1 FROM knowledge_chunks WHERE (source_type = 'interview_qa' OR true) AND x", False),
    ("SELECT 1 FROM knowledge_chunks WHERE source_type = 'interview_qa' OR 1=1", False),
    ("SELECT 1 FROM knowledge_chunks WHERE source_type = 'job_description'", False),
    ("SELECT 1 FROM knowledge_chunks WHERE source_type IN ('interview_qa')", False),
    ("SELECT 1 FROM knowledge_chunks WHERE x = 1", False),
])
def test_the_checker_itself_rejects_widened_filters(sql, ok):
    if ok:
        assert_strict_source_filter(sql, "case")
    else:
        with pytest.raises(AssertionError):
            assert_strict_source_filter(sql, "case")


def test_built_sql_filters_source_type_from_parameters_excluding_job_description():
    sql, params = build_search_sql([0.1] * 3, SearchFilters(), "text-embedding-3-small", 5)
    assert_strict_source_filter(sql, "build_search_sql")
    source_types = next(p for p in params if isinstance(p, list))
    assert set(source_types) == RAG_SOURCE_TYPES and "job_description" not in source_types
    bank_sql, _ = build_bank_sql("java.x", "text-embedding-3-small", "easy", 3)
    assert_strict_source_filter(bank_sql, "build_bank_sql")


def test_default_search_filters_exclude_job_description():
    assert set(SearchFilters().source_types) == RAG_SOURCE_TYPES
    assert "job_description" not in SearchFilters().source_types


def test_only_the_rag_repository_and_the_matching_index_read_the_table():
    # quet moi file app/**/*.py, khong phan biet hoa thuong (SQL ghep bang f-string van khop): them duong doc moi thi
    # phai vao danh sach nay VA qua kiem tra loc source_type o tren
    readers = {p.relative_to(APP_DIR).as_posix() for p in APP_DIR.rglob("*.py")
               if TABLE_READ.search(p.read_text(encoding="utf-8"))}
    assert readers == READERS_ALLOWED


def test_the_matching_index_reads_only_job_description_rows():
    assert re.search(r"source_type\s*=\s*'job_description'", job_index.JD_SQL)
    assert not re.search(r"source_type\s*=\s*'(interview_qa|textbook)'", job_index.JD_SQL)


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
