# Code Review: spec 005 Phase B relabel tools (`feat/data-pipeline/qa-relabel`, uncommitted)

## Scope
- New: `pipeline/qa_relabel_{prompt,command,agreement,decisions,apply_command}.py`, `data/reviews/qa-drops.json`, `tests/test_qa_relabel{,_decisions}.py` (~690 LOC)
- Modified: `__main__.py`, `settings.py`, `offline_commands.py`, `qa_record_builder.py`, `qa_seed_rules.py`, `.env.example`, `tests/test_qa_record_builder.py`, specs/005 (spec, tasks, 3 contracts). Diff +171/-4
- Tests: `pytest -q` passed 389 in 2.85s. No linter (ruff/pyflakes) in the venv
- Probes: scratch scripts only. Decisions were built **in memory** from the local luna judgments (60), `decisions-all.csv` (389) and `qa-drops.json`. `relabel`, `relabel-apply` and `index` were not run, and no file under `data/` was written

## Overall
The code is compact and readable, and every file is under 200 lines. The core intent works:
- `relabel` judges the original labels (`apply_relabel=False`).
- Drops show up in `records_rejected` (simulated 62 out of 62).
- Index takes the UPDATE path with no re-embed, because the content hash doesn't change.
- OpenAI and OpenRouter get the right request params.
- Concurrency is safe because only the main thread writes the cache.

One real rule-order bug (H1), two crash bugs (H2, M1) and several silent-failure paths need fixing before T062/T064.

## High

### H1. Drops run before dedup, so an unjudged duplicate twin comes back
- `offline_commands.py:31-35` applies drops **before** `validate_seed`. `_drop_duplicates` therefore keeps the twin that used to lose as `duplicate_question`.
- `qa_relabel_command.py:78-83` (`crawled_pairs`) judges only `result.valid` with `apply_relabel=False`. The dropped twin wins dedup again there, so the returning twin can **never** be judged.
- Evidence from the simulation: 62 drops; valid pairs went 4503 to 4443. 2 pairs became valid with no judgment:
  - `cr-sudheerj-js-783aaab2`: same question as `cr-lz-javascript-basics-d52b5806`, which luna dropped as `none` (RegExp test/exec). The same off-topic question gets into the index with its enrich labels.
  - `cr-sudheerj-js-0b90fee1`: twin of `cr-devlovers-python-65434e7d`, dropped by the 27/10 review (a Python asyncio answer under the Node event-loop topic). This JS twin is probably the right pair to keep.
- Scale: the crawled set has 160 `duplicate_question` warnings, and these are the candidates at full scale (estimated ~650 drops).
- Fix (recommended): (a) `crawled_pairs` judges every crawled item that passes `check_pair` before dedup. That is about 160 extra calls, roughly $0.08 with luna.
- Alternative: (b) spread each drop to its group of identical questions. This would also lose the good JS twin above.
- In both cases, add a line to `relabel-apply`/`validate` along the lines of "N valid crawled pairs have no judgment".

### H2. `parse_judgment` crashes the whole run on a non-string `best_topic_id`
- `qa_relabel_prompt.py:66`: `best not in topic_ids` (a set) raises `TypeError: unhashable type: 'list'` when the model returns a list or dict. Verified.
- `work()` calls `parse_judgment` outside its `try` (`qa_relabel_command.py:102`). The error escapes `pool.map` and stops `relabel`, and up to 50 calls already paid for in that batch are lost, because the append happens after the loop.
- Fix: `if not isinstance(best, str) or (best != NO_TOPIC and best not in topic_ids): return None, "unknown_topic"`. Also consider putting the parse inside the `try`.

## Medium

### M1. `stats.pop("cost_micro_usd")` raises KeyError when there is nothing to judge
- Location: `qa_relabel_command.py:147`. The Counter only gets this key inside the loop. Verified: the 2nd run returns `Counter({'cached': 1})`, then KeyError.
- Triggers:
  - rerunning after a full run (`relabel --ids sample-60-ids.json` a second time)
  - `--ids` that are all cached or match nothing (see L4, BOM)
- Result: a traceback and the wrong exit code. Fix: `stats.pop("cost_micro_usd", 0)`.

### M2. Golden protection applies only to the LLM `off + none` drop
- `qa_relabel_decisions.py:51-54`: a DE drop and a 27/10 review drop `return` before `protected` is checked.
- The `relabel-apply` contract says it "does not drop golden pairs that DE/AIE use".
- No impact today: 7 golden files were scanned and none references a `cr-*` id.
- Decide the rule: does a DE drop override protection? Should a review drop (done by Claude) respect it, or at least print a warning? Add a test either way.

### M3. Review CSV missing means silently `{}`
- Location: `qa_relabel_decisions.py:41-43`.
- `data/processed/` is gitignored. On another checkout, or after a cleanup, the 52 drops and 389 difficulty overrides disappear. The only sign is `meta.review_rows: 0`.
- Fix: error out when the file is missing, and add an explicit `--no-review` flag for when it really should be skipped.

### M4. `relabel-apply` uses judgments without validating them
- `read_cache` reads the raw rows. Haiku judgments come from a subagent (T060; T062 "Haiku: run by subagent in batches"), so they skip `parse_judgment` entirely: no enum or catalog check, and no forcing of `main` to the current topic.
- A missing `topic_before` or `model` key gives a KeyError in `decide`.
- Both current 60-row files are valid (checked: catalog ids valid, no `main` with best != before).
- Fix: re-validate each row in `relabel-apply` (reuse the enums and the catalog check), then skip and count bad rows.

### M5. The cache can go stale without warning
- `read_cache` keys only by `qa_id` (`qa_relabel_command.py:64-68, 92-93`), and `relabel-apply` also ignores `prompt_version` and `topic_before`.
- After a `PROMPT_VERSION` bump or a re-enrich that changes the topic, old judgments are reused. `decide()` treats `judgment["topic_before"]` as the current topic, so a pair can be moved based on the old topic.
- Fix:
  - `judge_pairs` re-judges rows where `prompt_version != PROMPT_VERSION` or `topic_before != pair.topic_id`.
  - `apply_decisions` skips a topic change when the data topic no longer matches (keep `topic_before` in the decision).

### M6. Run-report accounting doesn't add up
- `pairs_in` and `records_in` count pairs **after** the drop (4664 to 4602 in the simulation), but `records_rejected` includes the 62 dropped pairs. So `records_in - rejected != valid`.
- `validate` prints `valid/pairs_in`, which also hides the drops.
- Fix: count `pairs_in` before `apply_decisions`, or add a `relabel_dropped` field to the report.

### M7. `decisions.json` is applied silently and loaded without guards
- `load_decisions` (`qa_relabel_decisions.py:86-90`) has no error handling. A JSON error, or a missing `decisions` key, is not caught by `run_validate`/`run_process`/`index_records`, which catch only `CatalogError`/`SeedError`. The user gets a traceback.
- Nothing prints that decisions are being applied. A leftover trial file (for example from the 60-pair trial in T063) would push partial labels to the shared `ai_db` through `index`.
- Fix:
  - Raise `SeedError` on a malformed file.
  - When decisions are non-empty, `_load_inputs` prints one line: `ap decisions.json: model=…, judged=…, created_at=…`.
  - `relabel-apply` prints coverage (judged / valid crawled).

## Low
- **L1. OpenAI cost shows as zero.** OpenAI responses carry no `usage.cost`, so the summary prints "~0.0000 USD". Print "provider khong bao" or estimate from tokens.
- **L2. Reasoning can use up the whole token budget.** Empty `content` (reasoning hit `max_completion_tokens`) is counted as `invalid:bad_json`. Log `finish_reason == "length"` as a separate `truncated` reason.
- **L3. Prompt injection.** The question and answer are inserted into the prompt with no delimiters, so text like "CURRENT TOPIC:" or "TOPICS" inside them can confuse the model. Impact is limited: output is checked against the enums and the catalog, and the worst case is the pair dropping itself through `off + none` (reversible). Wrap the entry in `<entry>…</entry>` or JSON-encode it, and point to the tag in the system prompt.
- **L4. UTF-8 BOM.**
  - `read_ids` doesn't strip U+FEFF. Verified: a JSON file with a BOM gives 0 valid ids, which then hits M1.
  - `read_human` and `qa-drops.json` use `json.loads` with utf-8. A BOM in `qa-drops.json` exits cleanly with 1; in `read_human` it raises an uncaught traceback.
  - Notepad and PowerShell 5 `Set-Content` write a BOM. Use `utf-8-sig` for hand-edited inputs.
- **L5. A truncated last JSONL line** (process killed during the append) makes `read_cache` raise JSONDecodeError: `relabel` can't resume and `relabel-score` crashes. Skip bad lines with a warning.
- **L6. `relabel-apply --model` default** is hard-coded to `gpt-6-luna`. Read `RELABEL_MODEL` instead, as `relabel` does.
- **L7. Review CSV values aren't validated.** `do_kho_de_xuat` and `quyet_dinh` are not checked; current values are fine (easy 214 / medium 158 / hard 17; drop 52). A bad value causes an enum error, and the pair drops out silently as a warning.
- **L8. Spec numbers don't match the CSV.** The spec session says fix 221 / drop 50 (including 2 DE decisions). The CSV has fix 219 / drop 52, and T063 says 52 + 1 DE. Reword as "50 + 2 DE = 52".
- **L9. The base-URL fallback differs from `index`.** `index` uses EMBEDDING_BASE_URL, then LLM_BASE_URL. `relabel` uses EMBEDDING_BASE_URL, then api.openai.com. If EMBEDDING_BASE_URL is empty and the key is an OpenRouter key, `relabel` returns 401. This is documented in the contract, so low priority.
- **L10. `.env.example`.** One commented line holds 3 variables (`# RELABEL_API_KEY=  RELABEL_BASE_URL=…  RELABEL_MODEL=…`). Uncommented as-is, it becomes a single variable with a garbage value. Split it into 3 lines. On OpenRouter the model id is `openai/gpt-6-luna`.
- **L11. OpenRouter reasoning off.** The docs say `effort: "none"` disables reasoning. `enabled: false` is accepted but not guaranteed for every model, and models with `reasoning.mandatory` reject `none`.
- **L12. Unchanged pairs aren't counted.** `related + none` and `off + best == current` keep the topic with no record (3 such pairs in the luna sample). Count them in `summarize` for auditing.
- **L13. `golden_kept` pairs need manual reassignment** per the spec, but `summarize` only counts them. Print the ids.
- **L14. DRY.** `_read_judgments` duplicates `read_cache`. `crawled_pairs` loads the catalog twice and imports the private `_load_inputs`.
- **L15. Sequencing.** In the simulation, `topics_missing_hard` goes from 0 to 5 after applying decisions (already noted in T063). Once `decisions.json` exists, `validate --strict` fails, so B5 (T065) has to land before the T064 `index`.

## Checked and OK
- `relabel` judges the original labels: `crawled_pairs` passes `apply_relabel=False`.
- Each drop becomes `Issue(rule="relabel", warning)`, then `rejected_entries`, then `records_rejected` (62/62 in the simulation). Originals stay in `*_enriched`, and the in-memory originals are not mutated.
- Index: the content hash is unchanged, so `plan.update` UPDATEs topic, difficulty, category and metadata with no re-embed. Dropped hashes are removed by `_DELETE_SQL` only when `embed_errors == 0`; otherwise they stay until the next clean run, which is the existing behaviour.
- OpenAI params: `max_completion_tokens` + `reasoning_effort`, no temperature. OpenRouter params: `temperature: 0`, `max_tokens`, `extra_body.reasoning`/`usage`.
- `judge_pairs`: the pool exists only per batch, and the main thread does all writes, so there are no write races.
- Windows: `main()` reconfigures stdout/stderr to UTF-8, and all file I/O is utf-8. The JSONL gets CRLF line endings, which is harmless with `splitlines`.
- `data/raw/` and `data/processed/` are gitignored. `qa-drops.json` holds only an id and a reason, which is fine for a public repo.
- The rubric matches `ai-service/evals/judge_bank.py`. The golden regex catches `rag_golden.json`, which uses qa_ids.

## Test gaps
1. `_load_inputs` with decisions puts the drop into `rejected_entries` / `records_rejected`; `apply_relabel=False` ignores decisions.
2. Duplicate twin + drop (H1).
3. `parse_judgment` with list/dict/None `best_topic_id` (H2).
4. `run_relabel` with everything cached / no pairs (M1).
5. `decide` with protected + DE/review drop (M2); `run_relabel_apply` exit codes, missing CSV, malformed qa-drops.
6. Malformed `decisions.json` and judgment rows missing keys.

## Recommended actions (in order)
1. H1: judge crawled pairs before dedup, plus an "unjudged valid pairs" warning. This must be in place before T062.
2. H2 + M1: one-line guards.
3. M7 + M3: print which decisions/review file was applied; fail on missing or malformed inputs.
4. M2: decide the golden-vs-human-drop rule, write it into the contract, add a test.
5. M4/M5: validate judgment rows in apply; re-judge on `prompt_version`/`topic_before` mismatch.
6. M6: fix the `records_in` accounting.
7. L-items as convenient; add the tests listed above.

## Metrics
- Type hints: present on nearly all new functions
- Tests: 389 passed; new code is covered at the unit level, not at the CLI/integration level
- Lint: not run (no linter installed)

## Unresolved questions
1. With reasoning on for Anthropic models, does OpenRouter reject `temperature: 0` or drop it? Not verified.
2. Which twin should survive in the duplicate case (H1): the lowest qa_id again, or whichever twin is judged?
3. Do human drops (DE, 27/10 review) override golden protection?
4. What key schema does the `--human` export from the rating page use (`topic_fit`/`best_topic_id`/`difficulty`/`interview_style` at top level or under `data`)?
5. Should `related + none` also drop, or always keep the topic as now?
