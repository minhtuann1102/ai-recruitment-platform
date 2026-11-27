# Code Review: 017 US3 match-eval (branch feat/data-pipeline/jd-match-eval vs cec7e07)

## Scope
- Commits: 2629cfb (eval data + labels), 9105da6 (match-eval / match-eval-sheet), 4248c4b (eval-results + docs), c402819 (feature map)
- Files: 7 pipeline modules (869 LOC), 7 test files (851 LOC), 3 seed JSON files, 9 spec/doc files
- Checks run: `pytest -q` gives 771 passed. Metrics recomputed independently from the raw run JSON plus `labels.json` plus `jd_normalized.jsonl` (separate script, no pipeline imports). Kappa recomputed with `label_agreement.py`. Tie-order Monte Carlo (2000 shuffles). PII and crawl-text grep.
- Not verified: lint. Ruff, flake8 and pyflakes are not installed in the venv.
- No network, DB or ai-service calls were made.

## Overall
Code is correct, small, well tested, and matches the contract on everything that matters. Every number in eval-results.md §1–§5 reproduces exactly. SC-001 holds, and the reported gap is conservative (see below). The problems are in the **interpretation** in §7 and in how the caveats survive a rerun. These are doc fixes. **Ready to merge after the Medium doc fixes (M1–M4).** No code change blocks merge.

## Verification of numbers (focus 1)
| Item | eval-results.md | Recomputed |
|---|---|---|
| full P@5 / nDCG@5 / n_cv | 0.642 / 0.883 / 24 | 0.642 / 0.883 / 24 |
| skill_match | 0.625 / 0.847 / 24 | 0.625 / 0.847 / 24 |
| cosine | 0.617 / 0.842 / 24 | 0.617 / 0.842 / 24 |
| same (vi), full / skill / cos nDCG | 0.857 / 0.795 / 0.875, 22 CV, 123 pairs | identical |
| cross (en+mixed), full / skill / cos nDCG | 0.962 / 0.971 / 0.903, 24 CV, 132 pairs | identical |
| kappa (blind DE vs final LLM) | 0.718, exact 0.688, within-one 0.958 | 0.718 / 68.75% / 95.83% |
| kappa before rubric fix | 0.659 | 0.659 (vs llm_labels.v2) |
| index cost | 113600 tok ≈ $0.002272 | 113600 × 0.02/1e6 = 0.002272 |

- Per-CV check against the labels:
  - be-python-jr: full 0.947, skill 0.651.
  - ai-ml-mid: full 1.000, skill 0.665.
  - ai-llm-mid: full 0.864, skill 1.000.
  - All consistent with the labels.
- The endpoint order equals (score desc, job_id asc) for 24/24 CVs.
- `rankings` labels equal `labels.json` for every pair.
- Every CV has 10–12 pairs, so FR-019's "≥ 10 JD per CV" holds.
- Implementation matches the stated conventions:
  - linear gain;
  - ideal from all of the CV's labels in the set being scored;
  - a CV with no relevant JD is dropped;
  - `min(5, n)` denominator;
  - nearest-rank percentile.
  - The language subset is filtered after ranking, so relative order is kept (`match_eval_metrics.py:63-82`).
- Tie-order sensitivity (new evidence):
  - `skill_match` has 32 excess ties, `score` has 1, `cosine` has 0.
  - If tied items are ordered at random, the expected skill_match nDCG@5 is **0.836** (95% range 0.825..0.847).
  - The deterministic job_id tie-break (0.847) sits at the **top** of that range, so it flatters the baseline.
  - The expected full-vs-skill gap is therefore about 0.046, not 0.036. SC-001 is not an artifact of the tie-break.

## Critical
None.

## High
None.

## Medium

**M1. §7 language interpretation cites evidence that cannot test the claim.** (`specs/017-cv-jd-matching/eval-results.md:78-82`)
- What §7 does: it uses the within-group numbers ("cross: cosine 0.903 < skill 0.971") as support for "cosine bị phạt khi CV vi gặp JD en".
- Why that fails:
  - Inside a group, every JD has the same language. A uniform cross-language cosine offset cannot change the order inside the group.
  - So the within-group split measures only how well cosine separates JDs *among en JDs* versus *among vi JDs*.
- The data does support the hypothesis, but through cross-group numbers (computed from the raw run):
  - Mean cosine at equal labels, vi vs en:
    - label 0: 0.594 vs 0.530;
    - label 1: 0.614 vs 0.600;
    - label 2: 0.682 vs 0.637.
  - So en JDs get roughly 0.05–0.06 lower cosine.
  - Share of vi JDs in the top 5:
    - cosine-only: 69.2%;
    - full: 55.8%;
    - skill-only: 50.0%;
    - vi share among relevant pairs: about 55% (56 vi / 44 en / 2 mixed).
  - Cosine over-promotes vi JDs, and the full score corrects this almost exactly. That is a stronger and correct thesis point.
- Also wrong in the same paragraph:
  - "P@5 thấp (mẫu số nhỏ)" is wrong. The denominator is min(5, n) ≥ 4, and a smaller denominator would *raise* P@5. P@5 is low because each subset has only 1–3 relevant JDs.
  - With 4–7 JDs per subset (12/24 CVs have ≤ 5), P@5 is close to order-invariant. That is why all three methods show 0.396 in the cross group.
  - "(JD en)" should read "(JD en/mixed)".
- Fix:
  - Rewrite the §7 bullet around the cross-group numbers above.
  - In §3, either drop the P@5 column or annotate it as "gần như không phụ thuộc thứ tự khi tập con ≤ 5 JD".
  - Optional: have `match_eval_summary` emit vi-share@5 per method and mean cosine by (language, label), so the evidence regenerates.

**M2. The SC-001 "đạt" verdict has no uncertainty attached in the generated part.** (`match_eval_report.py:65-68`, `specs/README.md:31`)
- Paired per-CV results:
  - full vs skill: 12 wins / 6 losses / 6 ties; bootstrap 95% CI of the mean diff is −0.010..+0.084.
  - full vs cosine: 12 / 10 / 2; CI −0.023..+0.103.
- §7 says "chỉ coi là xu hướng" (good), but §7 is hand-written and disappears on rerun (M3). README states "SC-001 đạt" bare.
- "Kết hợp ba thành phần tốt hơn từng tín hiệu riêng" covers only 2 of the 3 signals (there is no level_fit-only baseline), and against cosine it is close to a coin flip.
- Fix:
  - In `_quality`, print the win/loss/tie count from `per_cv` (already in the raw JSON) and a simple paired bootstrap CI under the verdict.
  - Reword README to "SC-001 đạt (chênh 0,036, 24 CV, chưa có ý nghĩa thống kê)".
  - Reword §7 to "tốt hơn hai baseline đơn tín hiệu".

**M3. Rerunning overwrites the hand-written §7.** (`match_eval_command.py:67-68`, `quickstart.md:58` "Chạy lại lần 2…")
- The quickstart tells the reader to rerun. The default `--out` is the committed file, and `render_markdown` rewrites it whole. §7 even warns "cần chép lại mục này".
- Fix (pick one):
  - Move the analysis to `specs/017-cv-jd-matching/eval-analysis.md`, linked from eval-results.
  - Or make `_write_outputs` keep the text after a marker such as `<!-- manual -->` if the file exists.

**M4. Agreement wording is slightly optimistic or stale.**
- The 0.718 is measured on the **same 48 pairs** that prompted the rubric fix and the 88-pair relabel, so it is not an independent estimate. State this next to the 0.718 (labels.json `agreement` note and report `_dataset`).
- §7 "15/19 cặp lệch DE cao hơn" is the pre-fix count. After the fix it is **15/15** (all remaining disagreements are DE > LLM). That is a systematic leniency gap worth stating; it also means the labels are the strict reading.
- Positive: the report uses the blind kappa, not the adjudicated `de_final_labels.json`, which would give 0.738.

## Low
- **L1. Server timing resolution.** ai-service `_ms()` truncates to an int (`apps/ai-service/app/matching/service.py:44-45`). "0.0 ms / 2.0 ms" implies false precision: the true p95 is < 3 ms, and pool scoring is < 1 ms. Suggest a note in `_latency` that the values are whole ms, rounded down.
- **L2. Embed time is not recorded.** `timing_ms.embed` is in the response but not in `TIMINGS` (`match_eval_summary.py:18,31-35`). §7 claims "gần như hết là thời gian embed CV" without measuring it. Add `("server_embed_ms", timing.get("embed"))`.
- **L3. §7 "toàn bộ yêu cầu p95 ≈ 0,27 s".** That is the pool variant (270.9 ms). The full-index variant is 241.1 ms. Name the variant.
- **L4. SC-004 wording** (`match_eval_report.py:41-42`). Pair-set equality shows the endpoint filter agrees with the DE-written replica of the same rules. It is not independent proof, and it covers only the pool calls, not the full-index calls. Suggest "khớp bản sao luật lọc (R9)".
- **L5. The sheet renders the CV `note`** (`match_eval_sheet_command.py:39`). The note carries author intent (e.g. the .NET "gán track java_backend vì…"). The spec says the labeler does not see notes. The existing LLM labels were unaffected (`llm_input.json` has no note), but any future relabel from the sheet would see them. Drop the line or document it.
- **L6. Contract drift** (`contracts/pipeline-cli-match.md`):
  - The sheet prints full description / responsibilities / requirements, not a "trích đoạn yêu cầu".
  - The cost source is the newest *complete* index report (fallbacks: newest with tokens, then newest), not simply the newest.
  - The match-eval config error maps to exit 2, which is not listed.
  - Update the contract text.
- **L7. Reproducibility of kappa.** `de_blind_labels.json` (48 labels, no PII) and `label_agreement.py` exist only in the gitignored `data/processed/match_eval/`. That follows the data-model decision, but a thesis number then cannot be recomputed from the repo. Consider committing both under `data/seeds/match_eval/agreement/`.
- **L8. Process ticks.** T037 ("Review, mở PR-3") and T038, plus README "GĐ1 xong", are marked before PR-3 is reviewed or merged. Tick them on merge.
- **L9.** `tests/test_match_eval_command.py` is 219 lines (> 200). Split the cost tests into their own file if you want to follow the rule.
- **L10.** `embedding_tokens()` returns 0 when `usage` is missing, which would silently dilute the mean request cost (`match_eval_summary.py:38-40`). Harmless today (ai-service always sends it), but you could count the missing ones.

## Data files (focus 3)
- `cvs.json`: 24 synthetic profiles. No names, emails, phones, URLs or real companies (only `company_type`). `note` is a profile summary. Clean.
- `pool.json`: as_of plus 36 ids only. No crawl text in pool or labels (grep for description / requirement words gives 0; no `reasons` key).
- `labels.json`:
  - It is a superset of data-model §5 (`rubric`, `pair_set`, `agreement`, `final_source`), and data-model.md was updated.
  - Values are int 0/1/2 only: 162 / 62 / 40.
  - The loader rejects bool and float.

## Command vs contract (focus 4)
- Exit codes:
  - 0 / 1 / 2 / 4 as specified.
  - Pair-set mismatch exits 1 before the latency rounds (no wasted calls).
  - A config error exits 2.
  - `--rounds < 1` exits 1.
- Degraded and mock responses are checked on **every** call, quality and latency alike (`_call`). Nothing is written on exit 4, and the tests cover first-call and mid-latency failures.
- Body validation skips the component checks only for degraded responses, so code 4 is reached, not code 2.
- A truncated page (`total > len(items)`) gives exit 2 instead of a misleading "extra labels".
- The token header is sent only when set, and this is tested.
- Default paths: the repo-root specs file and the gitignored run dir (tested).
- The run JSON uses a microsecond timestamp, so reruns do not collide.
- Index report glob `run-report-index-jd-match-*` avoids the Q&A index reports (tested).

## Positive observations
- One summary dict feeds both the raw JSON and the markdown, so the numbers cannot drift between the two.
- Baselines are derived by re-ranking the endpoint's own components. No scoring formula is copied (DRY, and it measures the running code).
- Hand-computed metric tests cover linear vs exponential gain, ideal@5 with a relevant item below rank 5, ties, and subset order.
- The sheet's shuffle is seeded with a string over sorted ids (independent of PYTHONHASHSEED and of response order), and this is tested.
- The report honestly states that the labels are LLM labels, gives the kappa before and after the fix, and states that DE is more lenient.
- A test on the committed seeds guards against schema regressions.

## Recommended actions (priority)
1. M1: rewrite the §7 language bullet with the cross-group evidence; annotate or drop §3 P@5.
2. M2: add win/loss/tie and a bootstrap CI to the generated SC-001 line; add the caveat in README.
3. M3: move the hand analysis out of the overwritten file, or preserve it across reruns.
4. M4: note that 0.718 is measured on the tuning pairs; change 15/19 to "15/19 trước sửa, 15/15 sau sửa".
5. Low items as convenient (L1, L2 and L6 are cheap).

## Metrics
- Tests: 771 passed (all pipeline tests). The match-eval modules are covered by 5 test files.
- Lint: not run (no ruff, flake8 or pyflakes in the venv).
- File size: all modules < 200 lines; one test file is 219.

## Unresolved questions
1. Should §3 keep P@5 at all, given it is close to order-invariant on 4–7 JD subsets?
2. Commit the DE blind labels and the agreement script for thesis reproducibility (L7)? This needs an owner decision.
3. Was the DE blind labeling done on a page that showed the CV `note`? If so, add a sentence to the limitations.
