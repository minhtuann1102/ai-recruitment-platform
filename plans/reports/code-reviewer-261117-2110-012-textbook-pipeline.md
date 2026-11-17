# Code Review — 012 PR-A textbook ingestion pipeline (T035)

## Scope
- Diff: `git diff docs/textbook-ingestion-spec...HEAD -- apps/ docs/` — 59 files, +4527/-90 (apps/data-pipeline pipeline/, crawlers/, tests/, docs/architecture/data-pipeline.md)
- Judged vs contracts/pipeline-cli-textbook.md, textbook-source-manifest.md, data-model.md
- Tests: `.venv/Scripts/python.exe -m pytest -q` → **591 passed** (baseline holds)
- Known deviations (sections any-level match, github URL/ref drop, `_lazy` handlers) not re-reported

## Overall
Solid, well-tested, pure-function core (chunker, record builder, decisions, score). SQL fully parameterized. 005 writer change is safe. Main risk = silent deletion of live textbook chunks after a partial crawl, plus the canary-gate approval decision not actually implemented in code.

## 005 writer change (knowledge_chunk_writer.py) — no regression
- 005 records already carry `source_type` (INSERT line 115 reads `record["source_type"]`, unchanged), so `plan.source_types["de_interview_qa"] = "interview_qa"` → DELETE params identical to before for the 8,356 live rows.
- Textbook DELETE scoped `source_type='textbook' AND dataset=de_textbook_<S>` → cannot touch interview_qa.
- Cross-dataset hash collision → `skip_other`, still in `keep_hashes` → never deleted. OK.

## Critical
None.

## High

### H1. Partial crawl → silent DELETE of live textbook chunks in Supabase
- Chain:
  1. `pipeline/textbook_crawl_command.py:61-70` writes raw file + exit 0 whenever ≥1 page succeeded, even if others are `fetch_failed`.
  2. Markdown sources: `make_fetchers` line 38 `is_blocked = lambda: False`; `crawlers/github_raw_client.py:32` `raise_for_status()` → GitHub API rate-limit 403 (60 req/h w/o `GITHUB_TOKEN`) becomes `fetch_failed`, never exit 4. HTML: transient 5xx/timeouts or <3 consecutive 403 behave the same.
  3. `textbook_processed_io.latest_raw_file` picks that partial file.
  4. `pipeline/textbook_record_builder.py:96-98` silently `continue`s for manifest URLs absent from the raw file (no stat, no warning; only `pages_in` drops).
  5. `index-textbook` → `write_records` cleanup (`knowledge_chunk_writer.py:125-127`, runs because embed_errors=0) deletes every previously indexed chunk of the missing pages. Exit 0 at every step.
- Impact: shared store loses already-reviewed chunks; AIE retrieval degrades silently. Recoverable only by re-crawl + re-embed.
- Fix (any, ideally 1+2):
  1. process-textbook: count `pages_missing` (active manifest URL not in raw file), print each URL, exit 1 (or require `--allow-missing`).
  2. crawl-textbook: if any `fetch_failed`, still write file but exit non-zero (e.g. 1) so the operator re-crawls; or don't write.
  3. `GithubRawClient`: map 403/429 with `X-RateLimit-Remaining: 0` to a `blocked` flag → exit 4.
  4. Defensive in index: refuse (exit 1) if planned deletes > N% of the dataset's current rows without `--allow-shrink`.

### H2. Canary-gate approval decided (2026-11-17) but not implemented; score always resets approval
- `pipeline/textbook_review_decisions.py:76` `merge_decisions` → `approved_by=""` on every score; no code writes `"auto:canary-gate"` (grep: 0 hits in pipeline/). `textbook_review_score.py:130` still prints "approved_by de trong cho toi khi DE duyet".
- Committed decisions files (5 sources) have `"auto:canary-gate"` → set by hand. Every future score run (e.g. adding tracks/pages) resets it → index refuses until someone hand-edits again, i.e. a manual approval under another name, bypassable without passing the gate.
- Contract (pipeline-cli §Thứ tự, data-model §4) says score exit 0 → `auto:canary-gate`. Note contract §review-textbook-score text still says "approved_by đặt lại rỗng" → contract itself inconsistent.
- Fix: in `run_review_textbook_score` after gate passes, set `merged.approved_by = "auto:canary-gate"` before `save_decisions`; keep `merge_decisions` resetting (pure). Update message line 130, contract §review-textbook-score sentence, and docs/architecture/data-pipeline.md (+31 "DE duyệt file decisions (`approved_by`)", +49 "DE duyệt, điền approved_by"). Add test.

## Medium

### M1. index trusts processed file's `metadata.review`; doesn't re-check current decisions
- `pipeline/textbook_index_command.py:25-34` `check_ready` only checks `approved_by` non-empty + `metadata.review` present.
- Scenario: decisions edited/re-scored (a hash now `drop`) but process-textbook not re-run → dropped chunk indexed. Also processed file from another branch/older decisions passes.
- Fix: in `check_ready`, for each record require `decisions.decisions.get(original_hash(r))` exists and verdict ≠ `drop` (and for `trimmed`, `content_hash(apply_decision(...))` matches). Cheap; offline.

### M2. Excluded sources count as "known" in stray check → their chunks stay live
- `textbook_index_command.py:109` `known = {dataset_name(s.source_id) for s in check.sources}` includes `status: excluded`.
- Scenario: source flipped to excluded (robots now forbids / ToS) after being indexed → its rows remain served to RAG forever; no command removes them.
- Contract wording ("dataset trong manifest") is literally satisfied, so maybe intended; but excluded = access reason per contract §2, rows should go.
- Fix: `known` = only `status: use` sources (stray check then forces cleanup), or add explicit purge path for excluded datasets. Same gap for an all-dropped source (0 records → empty `keep_hashes` → `write_records` deletes nothing, stale rows stay).

### M3. Cross-source duplicate chunk: second source's tags never reach the store
- `knowledge_chunk_writer.plan_writes` → `skip_other` when hash exists under `de_textbook_<other>`; second source's `tracks`/`scenario_ids` lost in DB. Offline coverage counts it per source; `coverage-textbook --db` won't see it for the second source's scenarios → SC metrics diverge offline vs DB.
- Fix: process/validate warn on cross-source duplicate hashes (like in-source dedup), or index merges tags via UPDATE of the existing row's metadata (needs care: `_UPDATE_SQL` is dataset-scoped).

### M4. DRY: `textbook_processed_jsonl_reader.py` confirmed thin wrapper
- 22 lines: `read_processed` (= `processed_path` + `read_jsonl` + field check) and `original_hash`.
- Index uses raw `read_jsonl` (`textbook_index_command.py:98`) → row missing `content_hash` = `KeyError` traceback (exit 1 by accident, no message) instead of clean exit 1.
- Fix: move both functions into `textbook_processed_io.py`, delete wrapper, update imports (prepare, coverage, tests), and make index use `read_processed`.

### M5. Docs stale vs approval decision — see H2 (docs/architecture/data-pipeline.md diff lines +31, +49; also +13 "commit sau khi DE duyệt").

## Low
- L1. `plan_writes` ValueError (mixed source_type per dataset, `knowledge_chunk_writer.py:59-61`) escapes `run_index_textbook` except tuple (line 120) → traceback; unreachable for textbook today. Catch `ValueError` → exit 1.
- L2. `--source` `required=True` (`textbook_cli.py:53-57`) → argparse exits **2** when missing, colliding with contract's 2 = preflight; the run_* checks returning 1 (crawl line 78, index line 84) are dead code. Use `required=False` and let handlers return 1 (matches contract), or accept argparse convention and drop dead checks.
- L3. `load_canaries` (`textbook_review_prepare.py:44`) requires ≥3, contract §4 says ≥12 (file has 12 now). Align to 12 to keep canary rotation meaningful.
- L4. PII scrub only on `content`; `metadata.title` / `heading_path` stored unscrubbed (`textbook_record_builder.py:61-62`). Docs headings rarely hold PII; scrub or note.
- L5. `check_ready` doesn't verify `decisions.source_id == source.source_id` (copied file).
- L6. `review-textbook-prepare` leaves old `judgments-*.jsonl` (warning only); score then fails safely on id mismatch — OK, but deleting/archiving them would avoid confusion.

## Edge cases checked (OK)
- Hash/decision keys: key = md5(lower(strip(clean_text→scrub_pii content))) consistently in builder, prepare (`original_hash`), score (recomputed from batch content + `item_id_of` cross-check). Trimmed records: DB hash = final, `metadata.original_hash` = key. Dedup via original and final hash correct, including trim-collision case.
- Trim validation identical in score and process (both `apply_decision`, body-only match, exactly once).
- Score: writes nothing on any error/redo; canary not dropped → redo; extra/missing/duplicate item_ids caught.
- Atomic writes (tmp+replace) for raw/processed/decisions; blocked crawl writes no file.
- SQL: all parameterized (writer, stray check, vector check, counts).
- Re-run index: existing hashes → UPDATE path, probe/embed skipped.

## Positive
- Pure functions + fake embedder → strong unit coverage; deterministic byte-identical outputs.
- 005 writer change minimal, backward-compatible, and fails loudly on mixed source_type.
- Stray-dataset check runs before any write.

## Recommended actions (order)
1. H1: fail process on missing manifest URLs + make crawl non-zero on fetch_failed + GitHub rate-limit → blocked.
2. H2: score sets `auto:canary-gate` on pass; fix message/docs/contract sentence.
3. M1: check_ready re-validates against current decisions.
4. M4: fold reader into processed_io, index uses `read_processed`.
5. Decide M2/M3 policy; L-items as time allows.

## Metrics
- Tests: 591 passed. Lint/type: not run (no config requested). Coverage %: not measured.

## Unresolved questions
1. H2: should score auto-fill `approved_by="auto:canary-gate"` (my reading of the 11-17 decision), or is hand-filling intended as a final DE glance? Contract text contradicts itself.
2. M2: should flipping a source to `excluded` purge its indexed rows (via stray check) or keep them?
3. H1: acceptable policy for partial crawls — hard fail, or write + warn + require `--allow-missing` at process time?
4. M3: is cross-source duplicate content expected (spring-boot vs spring-framework vs spring-data-jpa overlap)? If yes, tag merge in DB matters for coverage --db.
