# Code Review: 009 US4 `seed-jobs` (branch `feat/data-pipeline/jd-seed` vs `main`)

## Scope
- Commits: bb4717a (feat), f135f6e (docs)
- Files (apps/data-pipeline/): `pipeline/job_seed_selector.py` (136), `pipeline/job_db_seed_preflight.py` (81), `pipeline/job_db_seed_writer.py` (155), `pipeline/jd_seed_command.py` (114), `pipeline/settings.py` (+17), `pipeline/__main__.py` (+6), `.env.example` (+4), 3 test files (197). Specs: data-model.md, tasks.md, specs/README.md
- All code files < 200 lines
- Tests: 388 pass (`pytest -q`, 2.9 s). No linter in venv (ruff / pyflakes / mypy not installed), so no lint count
- Method: read code + spec (FR-018..FR-022, R10, Mapping table, CLI contract, docs data-model §1–§2, users migration); ran selector on real `data/processed/jd_normalized.jsonl` (read-only, no DB); checked psycopg 3.3.6 dumper OIDs offline; no DB touched

## Overall
Small, readable code that sticks to the spec. Selector is correct and deterministic on real data. Selector dedup key matches the SQL idempotency key. Writing user_db before job_db is the right order. The SQL layer is parameterized. Main risks show up only on the real schema (T038/T048): preflight can block on a table seed only reads (false positive), `--clean` won't be safe once 008 adds tables referencing `job_postings`, and constraint mismatches during writes come out as tracebacks with the wrong exit code.

## Critical
None.

## High

**H1. Preflight checks for NOT NULL columns without a default in `experience_levels`, a table seed only reads, so a correct schema can fail with exit 2**
`job_db_seed_preflight.py:24, 50-59, 74-80`. `unfilled_required_columns` loops over every table in `EXPECTED_COLUMNS`, including `experience_levels`, which seed only reads. Contract §2 has `experience_levels.sort_order int`. A MikroORM `@Property() sortOrder!: number` becomes `int not null` with no default, so preflight reports `experience_levels.sort_order NOT NULL khong co default` and stops T048 on a correct schema. Reproduced with the pure function:
```
actual['experience_levels']['sort_order'] = True -> ['experience_levels.sort_order']
```
The throwaway contract DB passed, most likely because it made `sort_order` nullable.
Fix: split expected columns into `WRITTEN` (users, company_profiles, job_postings, job_skills, skills) and `READ` (experience_levels). Check missing columns on both and required columns on `WRITTEN` only. Add a test where `experience_levels` has a required `sort_order` and preflight returns `[]`.

**H2 (latent until 008). `--clean` hard-deletes `job_postings` with no check for rows that reference them**
`job_db_seed_writer.py:137-145`, `jd_seed_command.py:44-51`. Contract §2: `applications`, `saved_jobs` (and `application_events` through applications) reference `job_postings`. Once 008 lands and a candidate applies to or saves a seed posting during a demo:
- FK `ON DELETE CASCADE` → clean silently deletes real candidates' applications/saved jobs. This breaks FR-020 / AS-5 ("không đụng dữ liệu khác").
- FK `RESTRICT / NO ACTION` → `IntegrityError` that nothing catches → traceback, exit 1. The job_db tx rolls back, so the job_skills deletes are undone (atomic, good).
The throwaway-DB clean test had no such tables, so it doesn't cover this.
Fix: before deleting, look up FKs that point at `job_postings` (`pg_constraint` where `confrelid = 'job_postings'::regclass`). Count referencing rows for the seed employer ids. If any exist, refuse with exit 2 and a message (or require `--force`). Add this to the T048 checklist.

## Medium

**M1. Errors on the write path are uncaught, so exit 1 collides with the contract**
`jd_seed_command.py:90-101, 107-114`. Only `ConfigError` and `psycopg.OperationalError` are caught. `CheckViolation`, `NotNullViolation`, `DataError` (varchar length, int range), `IntegrityError`, `InsufficientPrivilege`, a malformed URL (`ProgrammingError: invalid connection option`, verified), `ValueError` from `_deadline` (`date.fromisoformat`, outside the try) and `KeyError` from `dictionary.skills[slug]` (`writer.py:99`, if the dictionary was edited after process-jd) all produce a traceback with Python exit 1. In the contract, 1 means "thiếu JD đủ điều kiện".
Partial failure: if the error happens after `user_conn.commit()` (line 91), the Employer seed rows stay in user_db with no postings. That is harmless: a rerun reuses them by email and `--clean` removes them (seed domain). job_db rolls back fully (`with psycopg.connect` → rollback on exception). So the commit order is right, but the operator gets a traceback instead of a clear exit 2.
Fix: `except psycopg.Error as exc: print(...); return EXIT_PREFLIGHT_ERROR` in `run_seed_jobs`. Optionally validate `deadline` / dictionary membership before `ensure_employers`, so input errors exit 1 with nothing written.

**M2. FR-019 says "schema thiếu/khác" (missing or different), but preflight only checks that columns exist and whether they are NOT NULL without a default**
`job_db_seed_preflight.py:31-36`. It doesn't check `data_type` (e.g. `employer_id` uuid vs varchar, `salary_*` int), CHECK constraints or native enums on `role`, `status`, `work_type`, `salary_currency`, or the UNIQUE constraints seed depends on (see M3). Any mismatch fails in the middle of the write (M1). Role casing is fine: `libs/common` uses `Admin = 'Admin'`, so `'Employer'` matches the PascalCase convention.
Fix (cheap): also select `data_type` and compare a few key columns (uuid / integer / date). At T038, record by hand the CHECK/enum values for those 4 columns. Can wait for T038, but list it in the PR description.

**M3. Skills idempotency depends on a UNIQUE(slug) that preflight never checks; on a name conflict a posting can end up with 0 skills**
`job_db_seed_writer.py:93-106, 122`.
- Without a unique index on `slug`, `ON CONFLICT DO NOTHING` never conflicts. Every run then inserts duplicate `skills` rows, which breaks FR-020, and `{slug: id}` picks an arbitrary id.
- If 007 seeds its own catalog (e.g. `name='Node.js', slug='node-js'`), the dictionary's `nodejs` collides on `name` and is dropped. The warning lists slugs but doesn't check that each posting keeps ≥ 1 skill (FR-018). A posting whose skills all collide gets inserted with no tags, and SC-005 "NodeJS" search can miss it.
Fix: run `SELECT` by slug first and insert only the missing slugs, so it no longer depends on the constraint. On a name conflict, fall back to `lower(name) = lower(%s)` and reuse that id. Before committing job_db, check that every item has ≥ 1 skill id, otherwise exit 2.

**M4. The manifest is overwritten with the current selection only, so seed postings from earlier runs lose their synthetic flag (FR-026)**
`jd_seed_command.py:101`. If the normalized input changes (new crawl, process-jd rerun), the next run selects a different 200. Old postings stay in job_db (DB > `count`) but drop out of the manifest, and their `synthetic` flag is lost. `--clean` also leaves the stale manifest with deleted ids. SC-005's "chạy lại: 0 posting mới" (rerun creates 0 new postings) holds only when the input is identical.
Fix (pick one): (a) at seed time, count postings of the seed employers that aren't in the current manifest and warn "chạy --clean trước"; (b) merge the old manifest by `posting_id`. Delete or empty the manifest in `_clean`.

**M5. Deadlines already in the past while status is `open`**
`job_db_seed_writer.py:42-46`. Real data: 9/200 selected postings have `deadline < 2026-10-28`, 13 fall in 2026-10 and 180 in 2026-11. Postings are seeded with `status='open'`, but by demo time most will be past their deadline. If 007 search/listing filters `deadline >= today`, or job-service auto-closes expired postings, SC-005 and the demo lose most of the data. The code follows the Mapping table, so this is a spec decision (see questions). Suggestion: `max(jd_deadline, run_date + 30)`, keeping the original deadline in the manifest if needed.

**M6. Test gaps: the orchestration and exit codes (contract) are untested**
process-jd and synth-jd have command tests; seed-jobs has none. No DB needed, a fake conn/cursor that records SQL is enough:
- `seed_jobs`: preflight problems → 2 with no write/commit; `password_hash=None` → 2 (with and without `--clean`); `selection.errors` → 1 with no `ensure_employers`; happy path commits user_db before job_db and writes the manifest.
- `_clean`: commits job_db before user_db; SQL params contain the seed domain.
- `require_seed_settings`: missing `USER_DB_URL` / `JOB_DB_URL` → `ConfigError`.
- `ensure_employers`: two spellings of one company → 1 insert; existing email → reused, nothing inserted.
- `insert_postings`: found → `inserted=False` and no job_skills; duplicate slugs in `jd["skills"]` → one job_skills row.
- Invariant: `posting_key(jd)[1:] == (row["title"], row["description"])`, and `employer_email` derives from the same `company_slug`, so the selector dedup and the SQL key can't drift apart.
- Selector: value present but below floor → a `warnings` entry, not `errors` (no test hits this branch). Preflight: H1 case.

## Low
- L1 `__main__.py:135`: `--count` accepts 0 or negative values → selects 0, no error, empty manifest overwrites the old one. Use a positive-int argparse type.
- L2 `job_seed_selector.py:116-124`: step 1 fills every axis floor with crawl before the synthetic pass. The worst case is 5×20+3×20+3×20 = 220 > 200, so in theory the count cap could block synthetic from filling a group gap. It doesn't happen on real data (all eligible frontend/mobile/Đà Nẵng JDs are selected). Possible fix: per value, crawl first then synthetic.
- L3 `job_db_seed_writer.py:80`: the employer lookup ignores `users.deleted_at` (soft delete in the real migration) and can reuse a soft-deleted seed Employer. The real migration has no UNIQUE on `users.email` (contract says UK), so two concurrent runs create duplicates. Single-operator CLI; optional `pg_advisory_xact_lock`.
- L4 `job_db_seed_writer.py:133, 153`: the clean filter could be tighter: `email LIKE 'seed-%@seed.ai-recruit.test' AND role = 'Employer'`. If registration doesn't verify email ownership, a real account on that domain would be deleted (`.test` is reserved, so low risk). LIKE `.` is literal and the domain has no `_`, so the pattern is correct.
- L5 `job_db_seed_writer.py:61-63`: `_insert` builds the table/column names with an f-string. Every identifier comes from code constants (`employer_rows`, `posting_row`, the `"users"` / `"company_profiles"` / `"job_postings"` literals) and values are parameterized, so there is **no injection**. `psycopg.sql.Identifier` would be cleaner.
- L6 `job_db_seed_preflight.py:35`: `information_schema.columns` hides tables the role has no privilege on, and `current_schema()` is only the first schema in search_path. Both give a misleading "thieu bang" (missing table) error, but fail safe. A column whose domain type has a DEFAULT is a false positive. Info.
- L7 `job_db_seed_writer.py:20`: `PasswordHashFn = Callable[[], str]` doesn't fit T039 option (b) (pgcrypto `crypt(...)` needs the conn or a SQL expression). If (b) is chosen, a closure over `user_conn` is needed.
- L8: `is_eligible` doesn't require `company`. Safe today because `build_record` rejects JDs with no company (`REQUIRED_RAW_FIELDS`), but `{jd["company"]}` / `sorted(set(...))` would break on None. Defensive check only.
- L9: skills inserted by seed are not removed by `--clean` (catalog, by design). Note this in quickstart.

## Verified OK (as requested)
- **select_postings**: deterministic. Same result on 5 random shuffles of the real 365 JDs. On real data: 210 eligible → 200 selected, 24 synthetic, warnings frontend 17 / mobile 18 / Đà Nẵng 19 (equal to the eligible counts, so the floor logic took everything available), 1 duplicate key dropped; with 5 levels, 191 < 200 → error. Matches tasks.md. `jd_id` is unique in the data, so tie-breaks are stable. Crawl comes first in both steps; synthetic only fills gaps.
- **Idempotency key**: selector `posting_key` = (company_slug, `_text(title)`, `posting_description`). Writer: employer = `seed-<company_slug>@…` → `employer_id`, `title.strip()`, the same `posting_description`. SQL `employer_id = %s AND title = %s AND md5(description) = md5(%s)` uses the same values. Matches.
- **psycopg 3.3.6 typing**: `str` → `StrDumperUnknown` oid 0, which Postgres coerces into uuid/varchar columns. `list[str]` and `[]` → oid 0 text array → `ANY(%s::uuid[])` works even for an empty list; `slug = ANY(%s)` resolves to varchar[]. int → int4/int8 binary (max real salary 100,000,000 < int4 max). `date` → 1082, aware `datetime` → timestamptz (matches `timestamptz` in the users migration). `md5(unknown)` resolves to `md5(text)`.
- **information_schema predicate**: `is_identity` is YES/NO, `is_generated` is ALWAYS/NEVER (PG12+), and identity/generated columns have a NULL `column_default`, so excluding them is correct.
- **Transactions**: preflight / password / selection run before any write. user_db commits first. A job_db failure rolls back job_db only, and the leftover Employers can be reused (see M1). `_clean` commits job_db before user_db, so no posting is left pointing at a deleted Employer.
- **`--clean` scope**: limited to ids from seed-domain emails; the users DELETE filters by email again. `rowcount` is correct.
- **FR-021**: Employer rows have no person name or contact, `email_verified=True`, password from a hook (T039 open → exit 2 before writes, intentional). Role value `'Employer'` matches the `Role` enum casing.
- `.env.example` has placeholders only, no secrets. `__main__` already sets stdout to utf-8 (Vietnamese messages print fine on Windows).

## Outside the diff (observation)
- Upstream (US2): 364/365 normalized JDs have `work_type = onsite` (`normalize_work_type` defaults to onsite). All 200 seed postings are onsite, so a demo filter by work type has nothing to show.

## Recommended Actions (priority)
1. H1: limit the required-column check to tables seed writes, and add a test.
2. M1: catch `psycopg.Error` → exit 2. Check `deadline` / dictionary membership before writing.
3. M3: skills select-then-insert, map name conflicts by name, require ≥ 1 skill per posting before commit.
4. M6: fake-cursor tests for exit codes, commit order and the key invariant.
5. H2: guard `--clean` against referencing rows (do before 008 merges, or at least before the demo).
6. M4 / M5: manifest merge or warning, and a deadline decision (needs spec input).
7. M2: data_type check + list CHECK/enum values at T038.

## Metrics
- Type coverage: type hints on public functions; no mypy run
- Tests: 388 pass; new tests are pure functions only (selector 9, preflight 5, writer 6); command, DB functions and settings have 0 tests
- Lint: no linter installed in venv (not run)

## Unresolved Questions
1. Deadline (M5): keep the JD's deadline as the Mapping table says, or `max(deadline, run_date + N)`? Does 007 filter by deadline or auto-close expired postings? FSD needs to answer.
2. `--clean` once 008 exists (H2): refuse when applications/saved_jobs reference seed postings, or soft-delete (`deleted_at`)? Decide with FSD (FK ON DELETE behavior).
3. Will the real `skills` migration have UNIQUE on both `slug` and `name` (M3)? Will 007 seed its own skills catalog (slugs different from the dictionary)?
4. Is `experience_levels.sort_order` NOT NULL? Is there `created_at` / `updated_at` on `experience_levels` / `job_skills` (MikroORM BaseEntity)? If job_skills has an id/timestamps, seed has to write them; preflight already catches this correctly.
5. A seed run after the input changes: should it be "always `--clean` first" (doc) or should the code merge the manifest (M4)?
