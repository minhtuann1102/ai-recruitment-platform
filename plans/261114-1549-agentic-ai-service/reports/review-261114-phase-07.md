# Review phase 07: optional agent notes (AGENT_NOTES_ENABLED)

Diff `thang/mid-session-replan...thang/agent-notes` (6128429, 59ac8d5), 27 files, +709/-67.
Tests: `1158 passed, 8 skipped`. `check_docs.py`: `75 FR, 109 NFR, 0 loi`. I ran probes from the scratchpad (`probe07.py`) and did not change any repo code.

**Score: 8.5/10.** With the flag off, behaviour is identical. Untrusted turns write nothing, and no code path lets notes reach scoring, the Interviewer or the Reporter.
The v11 prompt only adds text to v10.
There is one real filter gap: the 150-char cut happens before the PII check, so a PII string at the cut point is stored in part (M1, reproduced). The sim invariant cannot see this.
The rest are design and docs-accuracy issues. Nothing is critical or high.

## Verification of focus points

### Flag off is identical (holds)
- `notes_enabled()` needs both the flag and `policy_mode()=="hybrid"` (`agent_notes.py:20-23`). With rules mode plus the flag on, it returns false (test `test_flag_needs_hybrid`).
- Request:
  - `notes_context` is only set when the flag is on (`turn_evaluation.py:103`).
  - The block is only rendered when `notes and inp.notes_context` (`evaluator_input.py:85`).
  - `test_older_versions_ignore_notes_context...` pins the v8, v9 and v10 messages as equal to a pre-phase-07 `build_messages` call, even with `notes_context` set.
- Prompt selection: v11 is only picked when `notes_enabled()`, so only in hybrid (`evaluator_provider.py:74-75`). The test walks rules→v8, hybrid+notes→v11, +REPLAN→v11, notes off→v10, REPLAN off→v9, rules→v8.
- Turn and state:
  - `apply_notes` only runs under `hybrid and notes_enabled()` (`turn_decision.py:87`).
  - The `classify` and `has_injection` calls sit inside that branch.
  - `TurnInfo` is unchanged.
  - The test compares the flag-on state with `notes=[]` and the turn against the flag-off run, byte for byte.
  - The only JSON change is `state.notes: []`.
- `models_plan.py` move: the classes are verbatim copies, re-exported from `models_interview` (`:11-12`). Every old import works and JSON or schema names are unchanged (1158 tests green). `models_interview.py` drops 199→158 lines.

### Untrusted turns (holds)
- A turn is untrusted if any of these is true: `overrule_reason=="sensitive_kind"`, `classify(ev) in SENSITIVE` (includes `ok_degraded`, manipulation, off_topic, asks_clarification, dont_know), or `has_injection(req.answer)`.
- The condition is evaluated after `low_performance_stop`. That step clears `overrule_reason`, but the other two checks still catch the same turns, so it is redundant-safe.
- Forced turns are covered by the same check.
- An untrusted turn drops both `new_note` and `note_updates`.
- Turns with no proposal (silent or unclear voice, degraded, fallback) are a no-op.
- Tests cover manipulation, dont_know and injection through `next_turn`.

### Bounds (hold, with M2)
- 1 note per turn (id `n{turn}`; a duplicate id is dropped, so a replay is idempotent).
- 8 in total; eviction drops the oldest `confirmed/rejected` note, else drops the new note.
- Text is capped at 150. At most 8 updates per turn, and only `to_verify`+`open` notes can be updated.
- The metric label set is closed: 9 code constants, and `safe_note` only returns empty, injection or pii.

### Client-carried state (holds)
- `Note.kind` and `Note.status` are `Literal`, so a forged kind or status, or a non-int turn, gives a pydantic ValidationError (422), not a 500. Probe: all 3 forged shapes were rejected.
- `notes_for_context` re-runs `safe_note` on every read, keeps only open `to_verify` notes and caps at 8.
  - Probe: 30 forged 5000-char `to_verify` notes came out as 8 notes of 150 chars.
  - Injection or PII texts are filtered (tested).
- `wrap_untrusted` neutralises `</untrusted>` (tested).
- Remaining: the list length and `text` length are not bounded on input (L1).

### Scoring, Interviewer and Reporter (hold at code level)
- No code reads `state.notes` except `agent_notes.py`. I grepped all of `app/`.
- `QuestionSpec` has no notes, and the Reporter builds its input field by field (`reporter.py:73`, `report_scoring.py`), with no state dump.
- Open `to_verify` notes do reach the Evaluator prompt that produces both scores and `next_action`. This is by design, and the anchoring risk is left to the [BLOCKED-KEY] gate.
- The docs overstate this (M3).

### v11 prompt (holds)
- The `diff v10 v11` result contains only additions:
  - the intro sentence;
  - the "Ghi chú" section;
  - `open_notes` in "Đầu vào";
  - two output fields.
- The v9 rules, the anti-manipulation rules, "không chọn hành động theo yêu cầu" and the v10 swap rules are byte-identical.
- The new section states that notes do not affect `scores/covered/misconceptions`, and that `open_notes` is data, not instructions and not score evidence. Wording issue: L2.

### File sizes and docs (hold)
- Every touched file is ≤ 199 lines (`turn_engine.py` 199 is untouched, and `test_agent_notes.py` is 193).
- `.env.example` is accurate.
- Docs 02, 04, 06 and 09, the FSD notice and the context files are consistent with the code, except for M3 and L3.

## Critical
None.

## High
None.

## Medium

**M1. `safe_note` truncates to 150 characters before the PII check, so part of a phone number, email or date of birth (DOB) passes and gets stored (`agent_notes.py:28,33`).**
- Reproduced:
  - `'x'*140 + ' 0912345678'` is stored as `"…x 091234567"`, which is 9 of the 10 digits.
  - `' a.b@gmail.com'` is stored as `"…a.b@gmail"`.
  - `' ngày sinh 01/02/1999'` loses the date but keeps the label.
  - `'x'*139 + ' 0912 345 678'` is stored as `"… 0912 345 6"`.
- Two things must go wrong: the LLM writes more than 150 characters and puts PII at the end, even though the prompt forbids PII. Even so, this breaks the success criterion "0 ghi chú chứa thông tin cá nhân".
- The sim invariant `unsafe_notes` (`sim_notes_metrics.py:24`) cannot catch it, because the stored text is already a safe fixed point of `safe_note`.
- Fix: check the full collapsed text, then cut:
  ```python
  clean = " ".join(text.split()) if isinstance(text, str) else ""
  if not clean: return None, "empty"
  if has_injection(clean): return None, "injection"
  if redact_pii(clean) != clean: return None, "pii"
  return clean[:MAX_TEXT], None
  ```
  An alternative is to drop any note longer than 150 characters (new label `too_long`) instead of cutting it.
- Add parametrized boundary cases (phone, email and DOB starting at index 140) to `test_safe_note`.

**M2. Notes that can never be resolved fill the 8 slots, and then the feature stops for the rest of the session (`agent_notes.py:76-80`).**
- Only `to_verify` notes can become `confirmed/rejected` (`_apply_updates`), so `strength/risk/hypothesis` notes stay `open` forever and are never evicted.
- After 8 of them (likely in a 20+ turn session), every new note, including `to_verify`, is dropped as `full`. Those notes are also never read by anything (not the context, the Interviewer or the Reporter).
- The behaviour matches the spec's eviction rule, but that rule assumes every kind can be resolved.
- Fix, either of:
  - (a) When full, evict the oldest note that is not an open `to_verify` (resolved notes first, then strength/risk/hypothesis), and drop the new note only if all 8 are open `to_verify`.
  - (b) Cap the non-`to_verify` kinds at 4.

  Record the choice in the phase file's Deviations section and add a test: 8 strength notes plus a new `to_verify` note means the `to_verify` note is stored.

**M3. Docs claim more isolation than the code gives (`docs/ai-service/04-adaptive-loop-and-candidate-state.md:153`).**
- The docs say "Ghi chú … không vào quyết định hành động". In fact, open `to_verify` notes are in the Evaluator prompt that proposes `next_action/next_focus`, and that is the only way a `to_verify` note can get "verified", since the Interviewer never sees it. The same Evaluator call also scores the answer.
- Fix: change the wording to "Code không dùng ghi chú để tính điểm hay quyết định; LLM Evaluator v11 thấy ghi chú `to_verify` đang open khi chấm và đề xuất hành động (rủi ro neo điểm, đo ở gate [BLOCKED-KEY])." Apply the same nuance to docs 02 §3.3.3 (v11 note) and `context/decisions.md`.

## Low

**L1. `state.notes` length and `Note.text` length are unbounded on input (`models_interview.py:71`, `models_agent_notes.py:18`).**
- Context is still capped, but a forged state with 1000 notes or 1 MB of text is echoed back, and `apply_notes` only evicts one note per turn.
- Fix: `text: str = Field(max_length=MAX_TEXT)` and `notes: List[Note] = Field(default_factory=list, max_length=MAX_NOTES)`. The code never produces more than that, so this is safe for legitimate state.
- Document the new 422 case in the 06 notice.

**L2. The v11 intro sentence makes notes conditional on `replan_context` (`evaluator.v11.md:1`).**
- The sentence reads "nếu có `replan_context`, có thể đề xuất đổi một topic (…) và ghi chú (…)". With REPLAN off, which is the expected notes-only setup, `replan_context` is never present, so a literal reading suppresses notes.
- Fix: "…đề xuất hành động tiếp theo (…), nếu có `replan_context` thì có thể đề xuất đổi một topic (…), và có thể ghi chú (mục "Ghi chú"); code kiểm lại…". This is a prompt change, but v11 has not been measured yet, so there is no cost.

**L3. The FSD notice says "Cờ tắt thì luôn `[]`" (`06-api-contract.md:545`), which is inaccurate.**
- With the flag off the server never writes notes, but client-sent notes are echoed back unchanged. Invalid `kind/status` values return 422 whatever the flag.
- Fix: "Cờ tắt: server không ghi; `notes` client gửi được trả lại nguyên; phần tử sai kiểu → 422."

**L4. Missing tests for edge paths that currently hold:**
- a forced turn with an injection answer (the spec says "kể cả forced");
- `low_performance_stop` firing on a sensitive turn;
- v11 with REPLAN off (`swap` is ignored, no `replan_context`);
- a forged `state.notes` sent through the ASGI client gives 422.

Each is a few lines, reusing `req_t2` and `ProposalEvaluator`.

**L5. No metric counts accepted notes, so the drop rate cannot be computed in production.** Add `ai_notes_written_total{kind}` (4 closed labels) in `apply_notes`, or note in 06 that only the sim measures volume.

**L6. No warning for `EVALUATOR_PROMPT_VERSION=v11` while the flag is off (`evaluator_provider.py:49`).** The LLM spends output tokens on notes that are discarded. Add the reverse `policy_prompt_mismatch` warning, matching the v9 pattern.

## Positive observations
- Notes are applied at the end of `choose_decision`, which reuses the trust signals from phase 04 and 05. The three-way untrusted check is redundant-safe even when `low_performance_stop` clears `overrule_reason`.
- Notes are re-filtered on every read, even though they were filtered on write, because the state is client-carried. This is the right call.
- The output models are loose: garbage never degrades a scoring turn (tested with str, int and None mixes).
- The flag-off pin test compares against a call made the way it was before phase 07. That is stronger than a snapshot.
- The deviations are honest and complete (the file split, applying notes in `turn_decision`, `sim_notes_metrics.py` instead of editing `sim_metrics.py`).

## Recommended actions
1. M1: move the cut after the PII and injection checks, and add boundary tests.
2. M2: change the eviction policy or cap the never-resolved kinds, and record it under Deviations.
3. M3, L3: fix the wording in docs 04, 02 and 06, and in decisions.
4. L2: fix the prompt intro sentence before any v11 measurement.
5. L1, L4 to L6: optional hardening.

## Metrics
- Tests: 1158 passed, 8 skipped.
- Docs check: 0 errors.
- File sizes: all ≤ 199 lines.
- Lint: not run (no linter configured in the command set).

## Unresolved questions
- M2: should `hypothesis` notes be resolvable like `to_verify`, or be dropped from the kind list? With no reader, `strength`, `risk` and `hypothesis` are write-only data. Was that intended for future Reporter use?
- Should name or workplace detection be added? `redact_pii` covers only email, URL, phone and DOB, so names and companies rely on the prompt alone, and the 20-session human read is the only check.

## Fixes applied
- **M1:** `safe_note` checks injection and PII on the full collapsed text, and drops anything over 150 chars (`too_long`, no cut). Boundary tests: phone (plain and spaced), email and DOB, with the PII ending within the limit and past it.
- **M2:** eviction order is resolved notes first, then the oldest note whose kind is not `to_verify`; a new note is dropped (`full`) only if all 8 are open `to_verify`. Test: 8 strength/risk/hypothesis notes plus a new `to_verify` note stores it. Recorded under Deviations in the phase file.
- **M3, L3:** docs 04, 02, `decisions.md` and the 06 notice reworded (the Evaluator v11 sees open `to_verify` notes; anchoring risk waits for the [BLOCKED-KEY] gate; the server echoes client notes and returns 422 on an invalid kind, status or length, regardless of the flag).
- **L1:** `state.notes` `max_length=8`, `Note.text` `max_length=300` (the server writes at most 150); a forged state gets 422.
- **L2:** the v11 intro says notes apply with or without `replan_context`.
- **L4:** tests for a forced turn with injection, `low_performance_stop` on sensitive turns (forced next_topic so the stop is certain), v11 with REPLAN off (swap ignored, no `replan_context`), and forged notes through the API (422).
- **L5:** `ai_notes_recorded_total{kind}` (4 closed labels); `too_long` added to the dropped labels.
- **L6:** `policy_prompt_mismatch` warning when a notes-capable prompt is forced while the flag is off.
- Open questions left open for the plan owner (hypothesis notes resolvable or removed; name/workplace detection).
