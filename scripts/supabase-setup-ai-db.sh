#!/bin/bash
# Sets up ai_db on a Supabase project so the team shares one vector store: pgvector in the `extensions`
# schema, the knowledge_chunks schema taken verbatim from init-databases.sh (AIE owns the DDL), then
# supabase-ai-db-access.sql (Data API blocked, read-only role aie_reader). Idempotent.
#
# Run from the repo root:  bash scripts/supabase-setup-ai-db.sh   (needs psql)
# Reads AI_DB_URL (Supabase session pooler URI, user postgres.<project_ref>) and AIE_READER_PASSWORD from the
# environment, else from apps/data-pipeline/.env. Then load data with `python -m pipeline index`.
set -euo pipefail

script_dir=$(cd "$(dirname "$0")" && pwd)
env_file=apps/data-pipeline/.env

die() { echo "supabase-setup-ai-db: $*" >&2; exit 1; }

# Environment first, then the pipeline env file. Not `source`d: URIs may hold shell metacharacters.
read_var() {
  local value=${!1:-}
  if [[ -z $value && -f $env_file ]]; then
    value=$(grep -E "^$1=" "$env_file" | tail -n1 | cut -d= -f2- | tr -d '\r') || true
    value=${value#[\"\']}; value=${value%[\"\']}
  fi
  printf '%s' "$value"
}

db_url=$(read_var AI_DB_URL)
reader_password=$(read_var AIE_READER_PASSWORD)

[[ $db_url =~ ^postgres(ql)?://([^:@/]+):[^@]+@([^/]+)/([^?]+) ]] \
  || die "AI_DB_URL is not a postgresql://user:password@host:port/db URI"
db_user=${BASH_REMATCH[2]} db_host=${BASH_REMATCH[3]} db_name=${BASH_REMATCH[4]}
# The access rules touch Supabase roles (anon, authenticated): never run them on the local docker ai_db
[[ $db_host =~ \.supabase\.(com|co)(:[0-9]+)?$ ]] || die "AI_DB_URL host '$db_host' is not a Supabase host"
# psycopg prepares repeated statements, which the transaction pooler (6543) does not support
[[ $db_host != *:6543 ]] || die "use the Session pooler URI (port 5432), not the Transaction pooler (6543)"
[[ $reader_password =~ ^[A-Za-z0-9_-]{16,}$ ]] || die "AIE_READER_PASSWORD must be >= 16 chars of [A-Za-z0-9_-]," \
  "e.g. python -c \"import secrets; print(secrets.token_urlsafe(24))\""

# The ai_db heredoc of init-databases.sh (CRLF stripped for Windows checkouts)
schema_sql=$(tr -d '\r' < "$script_dir/init-databases.sh" | awk "/<<'SQL'\$/ {f=1; next} /^SQL\$/ {f=0} f")
[[ $schema_sql == *"CREATE TABLE IF NOT EXISTS knowledge_chunks"* ]] \
  || die "ai_db schema block not found in init-databases.sh"

# The DDL comments are Vietnamese; psql on Windows would otherwise use the console code page
export PGCLIENTENCODING=UTF8
psql_run() { psql "$db_url" -v ON_ERROR_STOP=1 -q "$@"; }

echo "1/3 pgvector in schema extensions"
psql_run -c 'CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions'

echo "2/3 knowledge_chunks schema from init-databases.sh"
printf 'SET search_path = public, extensions;\n%s\n' "$schema_sql" | psql_run

echo "3/3 access rules and read-only role aie_reader"
psql_run -v reader_password="$reader_password" -f "$script_dir/supabase-ai-db-access.sql"

rows=$(psql_run -tAc 'SELECT count(*) FROM public.knowledge_chunks')
echo "done: knowledge_chunks has $rows rows. Reader URI for ai-service AI_DB_URL (send privately):"
echo "  postgresql://aie_reader${db_user#postgres}:<AIE_READER_PASSWORD>@${db_host}/${db_name}?sslmode=require"
