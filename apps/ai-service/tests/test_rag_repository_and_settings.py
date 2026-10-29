"""SQL duong doc, map do kho, cau hinh RAG, factory (khong can DB that)."""
import asyncio

import pytest

from app.llm.errors import ConfigError
from app.rag.difficulty import difficulty_bucket
from app.rag.factory import build_retriever
from app.rag.models import SearchFilters
from app.rag.repository import PAIR_SQL, TOPIC_SQL, PgKnowledgeRepository, build_search_sql, vector_literal
from app.rag.settings import load_rag_settings, stored_model_name


@pytest.mark.parametrize("level,bucket", [(1, "easy"), (2, "easy"), (3, "medium"), (4, "hard"), (5, "hard")])
def test_difficulty_bucket(level, bucket):
    assert difficulty_bucket(level) == bucket


@pytest.mark.parametrize("level", [0, 6])
def test_difficulty_bucket_out_of_range(level):
    with pytest.raises(ValueError):
        difficulty_bucket(level)


def test_settings_default_enabled_and_strip_provider_prefix():
    s = load_rag_settings({"AI_DB_URL": "postgresql://ro@h/ai_db", "EMBEDDING_MODEL": "openai/text-embedding-3-small"})
    assert s.enabled and s.embedding_model == "text-embedding-3-small" and s.connect_timeout_s == 3
    assert not load_rag_settings({"RAG_ENABLED": "false"}).enabled  # tat han chi khi dat ro
    assert stored_model_name("text-embedding-3-small") == "text-embedding-3-small"


def test_settings_enabled_requires_db_url():
    for env in ({}, {"RAG_ENABLED": "true"}):  # mac dinh bat: thieu AI_DB_URL la loi cau hinh
        with pytest.raises(ConfigError):
            load_rag_settings(env)
    assert load_rag_settings({"RAG_ENABLED": "1", "AI_DB_URL": "postgresql://ro@h/ai_db"}).enabled
    for bad in ("0", "abc", "-1"):
        with pytest.raises(ConfigError):
            load_rag_settings({"AI_DB_URL": "postgresql://ro@h/ai_db", "AI_DB_CONNECT_TIMEOUT_S": bad})
    url = {"AI_DB_URL": "postgresql://ro@h/ai_db"}
    assert load_rag_settings(url).cooldown_s == 60 and load_rag_settings({**url, "RAG_COOLDOWN_S": "0"}).cooldown_s == 0
    for bad in ("abc", "-1"):
        with pytest.raises(ConfigError):
            load_rag_settings({**url, "RAG_COOLDOWN_S": bad})


def test_build_retriever_none_when_disabled():
    assert build_retriever(load_rag_settings({"RAG_ENABLED": "false"})) is None


def test_search_sql_filters_and_params():
    sql, params = build_search_sql([0.5, 0.25], SearchFilters(("textbook",), "Backend", "hard", "qa_pair"),
                                   "text-embedding-3-small", 20)
    assert "source_type = ANY(%s)" in sql and "embedding_model = %s" in sql
    assert "(difficulty = %s OR difficulty IS NULL)" in sql
    assert "ORDER BY embedding <=> %s::vector LIMIT %s" in sql
    assert params == ["[0.5,0.25]", ["textbook"], "text-embedding-3-small", "Backend", "hard", "qa_pair",
                      "[0.5,0.25]", 20]
    assert sql.count("%s") == len(params)
    bare_sql, bare = build_search_sql([1.0], SearchFilters(), "m", 5)
    assert "category = %s" not in bare_sql and bare_sql.count("%s") == len(bare) == 5


def test_read_sql_never_writes():
    for sql in (TOPIC_SQL, PAIR_SQL, build_search_sql([0.0], SearchFilters(), "m", 1)[0]):
        assert sql.lstrip().upper().startswith("SELECT")
        assert not any(w in sql.upper() for w in ("INSERT", "UPDATE", "DELETE", "DROP"))
    assert vector_literal([1, 0.123456789]) == "[1,0.1234568]"


class _Cursor:
    def __init__(self, rows):
        self.rows = rows

    async def fetchall(self):
        return self.rows


class _Conn:
    def __init__(self, rows):
        self.rows, self.executed = rows, []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def execute(self, sql, params):
        self.executed.append((sql, params))
        return _Cursor(self.rows)


def test_repository_opens_read_only_session_and_maps_rows():
    row = ("uuid-1", "Q\n\nA", "interview_qa", "node.x", "Backend", "hard", "de-qa-1", "qa_pair", None)
    conn, seen = _Conn([row]), {}

    async def connect(dsn, **kw):
        seen.update(kw, dsn=dsn)
        return conn

    settings = load_rag_settings({"RAG_ENABLED": "1", "AI_DB_URL": "postgresql://ro@h/ai_db"})
    chunk = asyncio.run(PgKnowledgeRepository(settings, connect).get_pair_by_qa_id("de-qa-1"))
    assert seen["options"] == "-c default_transaction_read_only=on" and seen["connect_timeout"] == 3
    assert chunk.qa_id == "de-qa-1" and chunk.score is None and chunk.dedup_key == "de-qa-1"
    assert conn.executed[0][1] == ["de-qa-1", "text-embedding-3-small"]
