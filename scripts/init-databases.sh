#!/bin/bash
# Creates one database per service plus pgvector + knowledge_chunks in ai_db.
# Idempotent: runs from /docker-entrypoint-initdb.d on an empty volume, and again
# via `make db-ensure` on an existing volume (the entrypoint skips init then).
set -eo pipefail

PSQL=(psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --no-password)

for db in user_db job_db interview_db notification_db ai_db; do
  echo "SELECT 'CREATE DATABASE $db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$db')\gexec" \
    | "${PSQL[@]}" --dbname postgres
done

# ai_db schema is owned by AIE (S0-AIE-2); copied from docs/architecture/rag-design.md §3,
# with IF NOT EXISTS added so the script can be re-run.
"${PSQL[@]}" --dbname ai_db <<'SQL'
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS knowledge_chunks (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content          TEXT NOT NULL,
  content_hash     CHAR(32) NOT NULL UNIQUE,   -- md5(lower(trim(content))), upsert idempotent
  embedding        vector(1536) NOT NULL,
  embedding_model  VARCHAR(50) NOT NULL DEFAULT 'text-embedding-3-small',
  source_type      VARCHAR(30) NOT NULL,       -- interview_qa | textbook (job_description: Stretch, AI không dùng)
  category         VARCHAR(30),                -- Backend | Database | System Design | DevOps | AI (khớp catalog)
  difficulty       VARCHAR(10),                -- easy | medium | hard (null với textbook)
  topic_id         VARCHAR(80),                -- id trong topic catalog; Q&A luôn có, textbook để NULL
  language         VARCHAR(5),                 -- vi | en
  metadata         JSONB NOT NULL DEFAULT '{}', -- qa_id, chunk_type, tags, source_url, section, heading_path...
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS knowledge_chunks_filter_idx ON knowledge_chunks (source_type, category);
CREATE INDEX IF NOT EXISTS knowledge_chunks_topic_idx ON knowledge_chunks (source_type, topic_id);
-- No vector index yet. When needed:
-- CREATE INDEX ON knowledge_chunks USING hnsw (embedding vector_cosine_ops);
SQL

echo "init-databases: done"
