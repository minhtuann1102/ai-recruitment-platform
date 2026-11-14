# Task review: spec 005 Phase B (B2/B3/B5/B6), 2026-11-09

Branch `feat/data-pipeline/qa-relabel`, uncommitted, base 77c9b8d (origin/main is 13 commits ahead; only change touching
our area is a comment in `ai-service/app/rag/question_bank.py`, no conflict). Review only, no files edited.

## Scope
- Code: 5 new `pipeline/qa_relabel_*.py` (74-171 LOC each, all < 200), 5 modified pipeline modules, 3 new + 1 modified
  test files (code was already reviewed in `code-reviewer-261108-2133-005-qa-relabel.md`, so this pass is task-level).
- Data: 6 modified `hard-*.json`, 3 new seed files, NOTICE, `data/reviews/qa-split-map.json`, `qa-drops.json`.
- Docs: spec.md, tasks.md, 3 contracts, `.env.example`, root CLAUDE.md.
- Verified by running: `pytest` 396 passed; `validate --strict` exit 0 (0 errors, 760 warnings); `process_seed` in-memory
  (no write) = 8,356 records; own scripts (scratchpad) for seed integrity, split map, golden refs, and a re-implementation
  of the ai-service bank filter (`spoken_ok` + shared topic word, generic words removed, level start difficulty
  fresher/junior=easy, middle=medium, senior=hard).

## Verified claims (match data)
- 4,178/4,863 valid; easy 2,478 / medium 1,390 / hard 310; process 8,356 records; 0 topic < 3 pairs (min 3:
  `ai.infer.serving-optimization`).
- decisions.json: 4,517 judged, 562 drops (luna 509, review 27/10 52, DE 1), 224 topic moves, 149 `interview_style=false`
  (also 149 in processed metadata), golden_protected 0. Golden files in ai-service reference 0 crawl ids.
- Bank coverage (my re-implementation reproduces tasks.md exactly): senior 58/58, middle 59/80, junior 51/63, fresher
  31/37. Senior stays 58/58 when an `interview_style` filter is added.
- 12 B6 topics: every level of each has >= 3 readable questions at that level's difficulty.
- Seeds: 343 pairs, 0 duplicate ids, all ids inside NOTICE ranges; 131 split pairs -> 262 halves, all with `split_from`,
  map == seeds (0 mismatches, halves in same file, same topic); 14 new hard in second ranges; 54 B6 (18 easy / 36
  medium; ai 45, java 6, python 3); 12 halves now medium; 0 non-spoken questions left; all `source=self`,
  `CC-BY-4.0`, `synthetic=true`, `grounding_urls` present; no `question_original`/quotes fields; no long English runs or
  quoted English > 60 chars (no verbatim doc text); half answers = original blocks (renumbered lists only), union of
  halves covers 99.8% of original lines (1003, 1068 lost one block each by review fix).
- Planted review traps did not leak: MCP pair `de-qa-0318` says client:server 1:1; `de-qa-0200` says default rollback =
  RuntimeException + Error, checked commits; `de-qa-1173`/`1463` questions match their answers.
- No secrets in diff or untracked files; `data/raw/` (decisions, judgments) gitignored; new seed/review files not ignored.

## Verdict
One pre-commit must-fix: H3 (false provenance claim in a public NOTICE + missing Clarification). Cheap docs fix.
Everything else is non-blocking. No code/data defect, secret or gitignored file blocks the commit if staging is by path
(M5).

## Critical
None beyond H3's must-fix status.

## High
H1. FR-029 claims more than the data backs. FR-029 says every catalog topic MUST have >= 3 readable questions at each of
its levels' difficulty. Data: middle 21, junior 12, fresher 6 topic-levels short. Worst: `ai.llm.prompting-structured-output`
(levels fresher/junior/middle) has 4 pairs, all hard, 0 usable at any level; also short: `ai.llm.model-selection-routing`,
`py.web.fastapi-async`, `py.data.sqlalchemy-sessions`, `py.web.api-auth`, `node.web.nestjs-di`,
`ai.infer.serving-optimization` (middle 0). T066 silently narrows it to the 12 B6 topics. Fix: reword FR-029 (per-level
clause applies to the 12 B6 topics; rest tracked as follow-up) or mark FR-029 partial in tasks.md.

H2. SC-010 not met yet. Clause 1 (DE blind sample ~100 pairs, >= 85% on-topic) is T064, still open; only clauses 2-3
(58/58 senior, 0 topic < 3 pairs) are verified. Phase B must not be reported as done; `index` not run. Clause 2 is met
numerically but 6 senior topics rest on the 14 unreviewed hard pairs (H3): `ai.dl.transformers-attention` (1484-1486)
and `java.arch.microservices-resilience` (1422-1424) entirely; `fe.web.security` (1563, 1564), `node.core.event-loop`
(1322), `ai.llm.evaluation-hallucination` (1488), `ai.llm.context-engineering` (1487) for their 2nd/3rd question.

H3 (pre-commit must-fix). Public provenance wording vs what happened. NOTICE says "every pair read by a human reviewer
(reviewed_by)"; qa-seed-format.md says `reviewed_by` is filled only after a real read (exception only for self-written
hard pairs per Session 2026-10-23, and that exception still needs "báo cáo duyệt có bằng chứng"). Actual:
- 222 of 262 halves not read (random-sample fix rate 5/20 = 25% -> ~55 need fixes, mostly "answer has points the
  question does not ask", which Evaluator v7 turns into `missing_points`).
- 14 new hard pairs (`de-qa-1322/1323`, `1422-1424`, `1484-1488`, `1518`, `1563-1565`): only quote existence checked
  (78/78 found) then `approve-seed`; no rubric review, no canary, no report (grep of plans/reports + tasks.md finds none).
- 54 B6 easy/medium pairs: reviewed by subagents + DE decision, outside the hard-pair exception.
The owner decision lives only in tasks.md prose. Fix in this commit: add spec Clarification Session 2026-11-09 (accept
the 222 unread halves, 14 quote-checked-only hard pairs and B6 subagent review as accepted risk, with the 25% estimate),
correct NOTICE wording, and persist which 40 halves were reviewed (today only in scratchpad `review/results-r*.json`) so
the rest can be targeted later. Recommended follow-up: a rubric review of the 14 new hard pairs (small, and 6 senior
topics depend on them).

## Medium
M1. Spec Clarification B5 bullet is stale: still says "Rút gọn 131 câu xuống <= 200 ký tự ... giữ đáp án đã duyệt" and
"câu đã sửa phải duyệt lại". Approach changed to split on 2026-11-08 (tasks T065) and re-review was waived.

M2. `split_from` (262 pairs) not documented in `contracts/qa-seed-format.md` (only mentioned in tasks.md); not validated
(pattern / referenced id exists) and not carried to chunk metadata, so `qa-split-map.json` is AIE's only link.
`grounding_urls` also undocumented (pre-existing).

M3. qa-seed-format.md table broken: blank line before the `interview_style` row makes it an orphan headerless table.

M4. Reproducibility: decisions.json and judgments are only on DE disk (gitignored). Any `process`/`index` without the file
silently returns to enrich labels (`load_decisions()` returns `({}, {})` for a missing file, no message; re-adds 562
dropped pairs to `ai_db`, loses interview_style). Back up both (e.g.
private review repo) and consider a loud warning in `index` when `enriched_qa/` exists but decisions.json does not.

M5. Commit scope: working tree also has unrelated untracked 009/JD reports, pr-body drafts, golden-label check,
`plans/261027-0241-cloud-credit-crawl-review-and-009/` and the root CLAUDE.md "Subagent Models" change (repo-wide, not
spec 005). Stage by explicit path, no `git add -A`; put CLAUDE.md in its own `docs:`/`chore:` commit. Rebase on
origin/main before PR (no overlapping files).

## Low
- L1. Task checkboxes: T063, T065, T066 text says done but boxes unchecked; T064 still says "`validate --strict` hỏng
  tới khi B5 vào" (now passes).
- L2. Phase 9 header plans "PR 1 tools + labels, PR 2 content (B5, B6)"; this branch holds both. Split or update header.
- L3. Counts: "hạ medium" = 6 (review report table) / 13, 7 after fix (report text) / 12 (tasks.md, data = 12).
  tasks.md "56 câu hard đang là đáp án đúng": data = 57 unique de-qa-1xxx in rag_golden + holdout, 54 affected by split.
- L4. "chép nguyên văn" for halves: accurate except list renumbering and one reworded heading (1508); fine, say
  "near-verbatim".
- L5. `hard-*.json` now hold 12 medium halves; NOTICE header comment says hard. Cosmetic.
- L6. B6 traps were corrupted copies of 2 real drafts (54 drafts reviewed as 52 real + 2 traps, all 54 in seeds), so the
  clean versions of those two (one MCP, one Spring transaction pair) only got a trap-version review. I checked the MCP
  and Spring rollback claims in the seeds: clean. Note it; no action needed.
- L7. `.env.example` comment fine; no secrets.

## AIE handoff (must go out before `index`)
1. Golden relabel via `data/reviews/qa-split-map.json`: 23 ids in `rag_golden.json`, 31 in `rag_golden_holdout.json`
   (half a keeps the old id but now holds half the answer). Order: AIE updates `relevant` -> DE `index` -> AIE re-runs
   eval; otherwise RAG eval regresses for reasons unrelated to retrieval.
2. `interview_style` filter not in `question_bank.rank` / `BANK_SQL` / `COVERAGE_SQL` (also not on origin/main): 149
   rows marked false will still be served until AIE adds it. Contract row in knowledge-chunks-io.md is ready.
3. Evaluator "optional points" question (qa-review report Q3) still open; it decides whether the ~55 estimated unread
   halves with extra answer points are a real scoring problem.
4. Restart ai-service after `index` to reload BM25 (T064 already says so).

## Positive
- Every number in tasks.md T062-T066 I could recompute matched (except L3 nits).
- Decisions applied at load, enriched_qa untouched, drops carry reasons, golden protection built in.
- Split is careful: same file, same topic, map consistent, answers traceable to reviewed originals.
- Review process used canaries and quote re-fetch; traps were caught and did not leak.

## Recommended actions (order)
1. Before commit: H3 (Clarification 2026-11-09 + NOTICE wording + persist reviewed-40 list), M1, M2 (add `split_from`
   row), M3, L1; reword FR-029 or mark partial (H1).
2. Commit by path; CLAUDE.md separately; rebase on origin/main.
3. Back up decisions.json + judgments (M4).
4. T064: blind ~100 sample (SC-010 clause 1) -> AIE golden relabel -> `index` -> AIE interview_style filter.

## Metrics
- Tests: 396 passed. validate --strict: 0 errors. Linter: none configured in data-pipeline.
- Type coverage / test coverage %: not measured.

## Unresolved questions
1. FR-029 per-level clause: meant for all catalog topics or only the 12 B6 topics? (DE)
2. Accept 222 unread halves permanently, or schedule a reviewer pass before Evaluator relies on them? (DE, depends on AIE Q3)
   Same question for the 14 new hard pairs, which had no content review.
3. One PR or two as Phase 9 header says? (DE)
4. Where to back up decisions.json / judgments (private review repo?) (DE)
5. MCP revision target 2025-11-25 vs 2026-07-28 (open in qa-review report; current pairs state both). (DE)
