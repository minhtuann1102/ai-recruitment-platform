"""Tich hop voi Postgres + pgvector that. Bo qua khi khong dat AI_DB_TEST_URL (CI mac dinh khong co DB).

Chay: docker run -d --name rag_pg -e POSTGRES_PASSWORD=pg -p 5544:5432 pgvector/pgvector:pg16
      AI_DB_TEST_URL=postgresql://postgres:pg@localhost:5544/postgres pytest -m integration
Test tu tao bang theo rag-design muc 3 (DB thu, khong phai ai_db that) va xoa du lieu cua minh sau khi chay.
"""
import asyncio
import os

import pytest

psycopg = pytest.importorskip("psycopg")

from app.rag.models import SearchFilters  # noqa: E402
from app.rag.repository import PgKnowledgeRepository, vector_literal  # noqa: E402
from app.rag.retriever import Retriever  # noqa: E402
from app.rag.settings import RagSettings  # noqa: E402

URL = os.environ.get("AI_DB_TEST_URL")
pytestmark = [pytest.mark.integration, pytest.mark.skipif(not URL, reason="AI_DB_TEST_URL chua dat")]
DATASET = "it_rag_read_path"
MODEL = "text-embedding-3-small"

DDL = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS knowledge_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), content TEXT NOT NULL, content_hash CHAR(32) NOT NULL UNIQUE,
  embedding vector(1536) NOT NULL, embedding_model VARCHAR(50) NOT NULL DEFAULT 'text-embedding-3-small',
  source_type VARCHAR(30) NOT NULL, category VARCHAR(30), difficulty VARCHAR(10), topic_id VARCHAR(80),
  language VARCHAR(5), metadata JSONB NOT NULL DEFAULT '{}', created_at TIMESTAMPTZ NOT NULL DEFAULT now());
"""


def onehot(i: int):
    v = [0.0] * 1536
    v[i] = 1.0
    return v


# (content, axis, source_type, topic_id, difficulty, qa_id, chunk_type)
ROWS = [
    ("Event loop la gi?", 0, "interview_qa", "node.core.event-loop", "medium", "it-1", "question"),
    ("Event loop la gi?\n\nMot vong lap...", 0, "interview_qa", "node.core.event-loop", "medium", "it-1", "qa_pair"),
    ("Backpressure?\n\nKhi consumer cham...", 1, "interview_qa", "node.core.streams", "hard", "it-2", "qa_pair"),
    ("Node.js > Streams\nBackpressure trong stream...", 1, "textbook", None, None, None, "section"),
]


@pytest.fixture(scope="module")
def seeded():
    with psycopg.connect(URL, autocommit=True) as conn:
        conn.execute(DDL)
        conn.execute("DELETE FROM knowledge_chunks WHERE metadata->>'dataset' = %s", [DATASET])
        for content, axis, st, topic, diff, qa_id, ctype in ROWS:
            meta = psycopg.types.json.Jsonb({"dataset": DATASET, "qa_id": qa_id, "chunk_type": ctype})
            conn.execute("INSERT INTO knowledge_chunks (content, content_hash, embedding, source_type, category, "
                         "difficulty, topic_id, language, metadata) VALUES (%s, md5(%s), %s::vector, %s, "
                         "'Backend', %s, %s, 'vi', %s)",
                         [content, DATASET + content, vector_literal(onehot(axis)), st, diff, topic, meta])
    yield PgKnowledgeRepository(RagSettings(True, URL, MODEL, 3))
    with psycopg.connect(URL, autocommit=True) as conn:
        conn.execute("DELETE FROM knowledge_chunks WHERE metadata->>'dataset' = %s", [DATASET])


def run(coro):
    return asyncio.run(coro)


def test_topic_lookup_returns_qa_pair_only(seeded):
    rows = run(seeded.list_by_topic_id("node.core.event-loop", "medium", 5))
    assert [(r.qa_id, r.chunk_type) for r in rows] == [("it-1", "qa_pair")]


def test_pair_lookup_by_qa_id(seeded):
    assert run(seeded.get_pair_by_qa_id("it-2")).content.startswith("Backpressure?")
    assert run(seeded.get_pair_by_qa_id("khong-co")) is None


def test_cosine_search_with_filters(seeded):
    rows = run(seeded.search(onehot(1), SearchFilters(("interview_qa", "textbook"), "Backend", "hard", "qa_pair"), 5))
    assert {r.dedup_key for r in rows} >= {"it-2"} and rows[0].score == pytest.approx(1.0)
    assert all(r.chunk_type != "question" for r in rows)


def test_read_only_session_rejects_writes(seeded):
    async def try_write():
        conn = await psycopg.AsyncConnection.connect(URL, autocommit=True,
                                                     options="-c default_transaction_read_only=on")
        async with conn:
            await conn.execute("DELETE FROM knowledge_chunks WHERE false")

    with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
        run(try_write())


def test_retriever_end_to_end_fallback(seeded):
    async def embed(_text):
        return onehot(1)

    out = run(Retriever(seeded, embed).retrieve_for_topic(
        topic_id="node.core.streams", category="Backend", difficulty=4, query="Backend | Streams"))
    assert [c.dedup_key for c in out][:1] == ["it-2"] and len({c.dedup_key for c in out}) == len(out)
