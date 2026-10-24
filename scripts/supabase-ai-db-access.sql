-- Supabase-only access rules for ai_db.knowledge_chunks. Run by scripts/supabase-setup-ai-db.sh after the
-- schema from init-databases.sh. Idempotent. Needs psql variable reader_password.
--
-- Writer: the project owner `postgres` (data pipeline `index`), owns the table so RLS does not apply to it.
-- Reader: `aie_reader` for ai-service (AIE), SELECT only, every transaction read-only.

-- Supabase's Data API (PostgREST) serves the public schema to the anon/authenticated roles, and new public
-- tables get grants for them by default: without this, anyone holding the anon key could read and write.
ALTER TABLE public.knowledge_chunks ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.knowledge_chunks FROM anon, authenticated;

SELECT 'CREATE ROLE aie_reader LOGIN' WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'aie_reader')\gexec
ALTER ROLE aie_reader WITH LOGIN PASSWORD :'reader_password';
-- The Supavisor pooler silently drops the `options` startup parameter ai-service sends
-- (-c default_transaction_read_only=on, verified 2026-10-23), so read-only must be set on the role
ALTER ROLE aie_reader SET default_transaction_read_only = on;
-- pgvector lives in the `extensions` schema on Supabase; the reader uses unqualified ::vector and <=>
ALTER ROLE aie_reader SET search_path = public, extensions;
ALTER ROLE aie_reader SET statement_timeout = '10s';
GRANT USAGE ON SCHEMA public, extensions TO aie_reader;
GRANT SELECT ON public.knowledge_chunks TO aie_reader;

-- RLS applies to every non-owner role, so the reader needs its own policy
DROP POLICY IF EXISTS aie_reader_select ON public.knowledge_chunks;
CREATE POLICY aie_reader_select ON public.knowledge_chunks FOR SELECT TO aie_reader USING (true);

DO $$
BEGIN
  IF has_table_privilege('anon', 'public.knowledge_chunks', 'SELECT')
     OR has_table_privilege('authenticated', 'public.knowledge_chunks', 'SELECT') THEN
    RAISE EXCEPTION 'anon/authenticated can still read knowledge_chunks';
  END IF;
  IF has_table_privilege('aie_reader', 'public.knowledge_chunks', 'INSERT') THEN
    RAISE EXCEPTION 'aie_reader can write knowledge_chunks';
  END IF;
END $$;
