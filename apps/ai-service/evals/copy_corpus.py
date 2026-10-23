"""Thu nghiem doi model embedding (rag-design muc 7.4): sao chep interview_qa tu ai_db (chi doc, aie_reader) vao
mot Postgres + pgvector CUC BO va embed lai bang model khac. Khong ghi vao ai_db dung chung (duong ghi la cua DE).

  docker run -d --name rag_pg_exp -e POSTGRES_PASSWORD=pg -p 5545:5432 pgvector/pgvector:pg16
  AI_DB_URL=<aie_reader> python -m evals.copy_corpus --target postgresql://postgres:pg@localhost:5545/postgres \
      --model openai/text-embedding-3-large [--estimate]
Noi dung crawl khong commit (repo public): DB cuc bo chi de do, xoa container sau khi xong.
"""
import argparse
import asyncio
import sys
from typing import List
from urllib.parse import urlparse

import psycopg
from psycopg.types.json import Jsonb

from app.llm.gateway import build_client
from app.llm.settings import load_llm_settings
from app.rag.repository import vector_literal
from app.rag.settings import load_rag_settings, stored_model_name

SOURCE_MODEL = "text-embedding-3-small"
DDL = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS knowledge_chunks (
  id UUID PRIMARY KEY, content TEXT NOT NULL, content_hash CHAR(32) NOT NULL,
  embedding vector(1536) NOT NULL, embedding_model VARCHAR(50) NOT NULL, source_type VARCHAR(30) NOT NULL,
  category VARCHAR(30), difficulty VARCHAR(10), topic_id VARCHAR(80), language VARCHAR(5),
  metadata JSONB NOT NULL DEFAULT '{}', created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (content_hash, embedding_model));
"""
COLS = "id, content, content_hash, source_type, category, difficulty, topic_id, language, metadata"


def read_source() -> List[tuple]:
    settings = load_rag_settings()
    with psycopg.connect(settings.db_url, connect_timeout=settings.connect_timeout_s) as conn:
        return conn.execute(f"SELECT {COLS} FROM knowledge_chunks WHERE source_type = 'interview_qa' "
                            "AND embedding_model = %s ORDER BY id", [SOURCE_MODEL]).fetchall()


async def embed_all(texts: List[str], model: str, batch: int = 100, concurrency: int = 4) -> List[List[float]]:
    client, sem = build_client(load_llm_settings()), asyncio.Semaphore(concurrency)
    out: List[List[float]] = [None] * len(texts)

    async def one(start: int):
        async with sem:
            resp = await client.embeddings.create(model=model, input=texts[start:start + batch], dimensions=1536)
            for i, d in enumerate(resp.data):
                out[start + i] = d.embedding
            print(f"embedded {min(start + batch, len(texts))}/{len(texts)}", file=sys.stderr)

    await asyncio.gather(*(one(s) for s in range(0, len(texts), batch)))
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--model", default="openai/text-embedding-3-large")
    parser.add_argument("--estimate", action="store_true", help="chi dem ky tu, khong goi API")
    args = parser.parse_args()
    host = urlparse(args.target).hostname or ""
    if args.target == load_rag_settings().db_url or host not in ("localhost", "127.0.0.1"):
        raise SystemExit("--target phai la Postgres CUC BO (localhost); khong bao gio ghi vao ai_db dung chung")
    rows = read_source()
    chars = sum(len(r[1]) for r in rows)
    print(f"{len(rows)} ban ghi, {chars} ky tu (~{chars // 3} token uoc than trong)")
    if args.estimate:
        return
    vectors = asyncio.run(embed_all([r[1] for r in rows], args.model))
    name = stored_model_name(args.model)
    with psycopg.connect(args.target, autocommit=True) as conn:
        conn.execute(DDL)
        with conn.cursor() as cur:
            cur.executemany(
                f"INSERT INTO knowledge_chunks ({COLS}, embedding, embedding_model) VALUES "
                "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector, %s) ON CONFLICT DO NOTHING",
                [(*r[:8], Jsonb(r[8]), vector_literal(v), name) for r, v in zip(rows, vectors)])
    print(f"da ghi {len(rows)} ban ghi model {name} vao DB cuc bo")


if __name__ == "__main__":
    main()
