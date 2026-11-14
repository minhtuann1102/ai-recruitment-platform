## Code Review Summary: scope-check-prepare / scope-check-score (spec 005 FR-030, T067)

### Scope
- Files: apps/data-pipeline/pipeline/qa_scope_check_{points,prepare,judgments,score}.py (120/137/100/153 LOC), `__main__.py` diff (wiring only), tests/test_qa_scope_check.py (248 LOC)
- Tests: 417 pass. Real run: `scope-check-prepare` -> 222 halves, 8 batches.
- Checks run on real seeds (262 halves): exact ordered line-sequence check (points vs answer, minus heading lines and top-level `- `/`* ` markers) -> 0 mismatch, so no lost / duplicated / reordered answer text; every heading line present as `[prefix]`. No mid-line or odd-count fences in data. 104 short-colon headings (31 mid-paragraph).
- a/b mapping: confirmed. Map value[0] == key for all 131 originals (half a keeps old id, matches code-reviewer-261109-2210 line 106); reviewed keys all exist in map; 40 reviewed = 42 batch R3 minus canary 1173 a/b.

### Overall
Segmentation and prepare are correct on real data; judgment row validation is strict (whole row rejected, dup keeps first + error). Main risk is in score: incomplete judging is reported as success and as clean.

### High
1. score.py:36-37, 103, 144: missing judgments = clean + exit 0. Confirmed: 1 of 222 judged -> summary "co 0", `errors: 0`, exit=0. Items judged by no judge are dropped from `by_item` entirely, so the fix step (reading by_item) never sees them. Fix: exit 1 (or `complete: false`) when any `missing[j]` non-empty; add `unjudged` list = real items with zero valid rows.

### Medium
2. score.py:39, 98: `agreement`/`flagged_all_judges` count only judges that scored the item. Probe: q1 scored only by A (flag), B missing -> "all". Plan uses "all agree" as high confidence. Fix: compare against `found.judges`; add "partial" state when some judge missing.
3. score.py:79-84: calibration silently restricted to judged items. Probe: truth {q1,q2,q3: true}, q3 unjudged -> union items 2, recall 50% computed on 2; `truth_items: 3` shown but no error. A judge that skips hard items gets inflated recall. Fix: error when `usable` item unjudged by a judge (per judge) / by all (union).
4. score.py:92 + judgments.py:26: canary batch counted as real when `--canary-key` omitted (manifest ignored). Flagged/items inflated (223+), only visible via item count. Fix: read manifest; items not in manifest and not in canary key -> error; real_ids = manifest item_ids.

### Low
5. points.py:88-93: fence only recognised at line start. `- Ví dụ: ```python` (or unclosed fence) -> following bullets merged into one point (probe confirmed). 0 cases in data now; data can change after fixes. Fix: prepare fails when answer has odd ``` count or ``` not at line start.
6. Truth file keyed by qa_id but reviewed verdicts keyed by `<orig>/a|b` with ok/fix/relabel_medium; conversion is manual (a/b + whether relabel_medium = needs-fix). Fix: accept truth keyed by `half` (batch already carries it) or document mapping.
7. No fingerprint of point texts in batch/judgment: judgments from an older prepare run with same point count validate against regenerated batches. Fix: per-item hash in batch, echoed by judge, checked in check_record.
8. prepare.py:78 `[x, x]` map entry -> uncaught StopIteration; prepare.py:87 non-dict `--originals` -> AttributeError traceback. Fix: validate in half_key / after read_json.
9. prepare.py:94-95 deletes every batch-*.json in out-dir; a hand-made canary batch placed there is wiped on rerun (score then errors, not silent). Fix: keep canaries in separate dir or name pattern outside BATCH_GLOB and add a `--extra-batches` option.
10. points.py:68-69: short colon sentence mid-paragraph (31 cases, e.g. de-qa-1170 "...vì:") becomes heading prefix, never its own point. No text lost; judge can't label it separately. Acceptable; note in judge prompt.
11. tests/test_qa_scope_check.py 248 lines (> 200; other test files <= 196). Split segmentation tests vs score tests.

### Security
CLI-local paths only; judge JSONL validated per row (types, ids, statuses); unhashable values handled. proposed_fix/summary_vi copied verbatim into JSON report (fine). No issues.

### Positive
Strict row rejection, judge name from field, dup (judge,item) reported, sibling lookup across all halves (incl. reviewed), half_key strictness for all halves, --expect guard before writing, deterministic sort, all code files < 200 lines.

### Recommended Actions
1. Fix #1 before running the 222 audit (blocks trust). 2. #2, #3 before calibration gate. 3. #4 before canary run. Rest optional.

### Unresolved Questions
- relabel_medium (6 of 40) counts as true or false in calibration truth?
