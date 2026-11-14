# Review phase 03: Evaluator tự tra cứu (`thang/evaluator-lookup` vs `thang/llm-tool-loop`)

Date: 2026-11-14. Reviewer: code-reviewer. Scope: `git diff thang/llm-tool-loop...HEAD`, 32 files, +1262/-155. Spec: phase-03, audit H1/H3/H4/M4/M8/L4/L5, review phase 02.

## Results
- pytest: **937 passed, 8 skipped** (13.5 s). `check_docs.py`: **75 FR, 109 NFR, 0 lỗi**.
- Probe (temp test, removed afterwards): slow loop + mock path with budget 1.2 s → wall 1205 ms, `latency_ms.evaluator` = **2405 ms** (see M1).
- Probe: `split_tool_misconceptions(["Nhầm HashMap là thread-safe (theo S1)"], [contradicted point quote "HashMap", ids S4], base 3)` → misconception freed (see M2).
- File sizes OK: evaluator.py 147, evaluator_input 78, evaluator_lookup_call 76, evaluator_lookup 141, tests ≤ 204.

## Focus checks
1. **Flag off: identical.** The split is a pure move (diff shows the same bodies). Old imports still work (`EvaluationInput`, `build_messages`, `all_snippets`, `source_refs`, `cited_sources`, output models re-exported; every importer resolves). `lookup=None` skips the new branch, `tool_base_ids=None` skips the H4 split, and `[*m, *[]]` is the same list. `DEFAULT_PROMPT_VERSION="v8"`, and v8 is the newest file today, so nothing changes now and a future v9 file will not switch the prompt automatically. OK.
2. **Id continuity: correct.** `base_ids = len(topic snippets + extra.texts)`, the same list `all_snippets` builds. `extend` appends to the end, so ids run `S{n+1}..`. `postcheck` receives the extended `inp` (evaluator.py:127). `cited_sources`/`source_refs`/`Evaluation.sources` include tool chunks (test at lookup_call:77). The recorder replaces `documents` only when `committed` (L5 OK), and `origin=tool` uses index `n >= tool_base_ids`, which is correct.
3. **H4 split: OK, with M2.** Only points whose valid ids are all tool ids are freed. Points with mixed, base or empty ids keep capping. The reordering `[*capping, *tool_only]` with `[:2]` in `build_evaluation` is correct: capping items are never hidden by uncapped ones, and score capping uses only `misconceptions` before the merge. When there are 2 or more capping items, the tool-only items drop out of `Evaluation.misconceptions`. That loss is acceptable because they carry no penalty weight. The real leak is the other direction (M3).
4. **Budget: OK.** There is one clock from `started`. `wait_for(left)` is a backstop and the ChatCall `cap_first` cuts each call. The fallback uses `budget_started=t0`, and the ≥ 2.5 s rule is checked after the failure. Cancellation is handled: `CancelledError` skips the tool_loop `except Exception`, `_record_cut` covers it, and inner records are merged once. There is no double `evaluator_lookup_fallback` record, but latency is double-counted (M1).
5. **Security: OK.** The query is cut to 200 chars plus `strip` (tool_loop), with `has_injection` → `invalid_query` and a casefolded duplicate check. Only `query` reaches `run_tool`. Filters come from `filters_for_turn` plus the difficulty bucket set by code, with `memory_only=True` (no DB). Results are capped at 3 chunks / 600 tokens, then trimmed to `MAX_RESULT_CHARS` before wrapping so the `</untrusted>` tag is never cut. `wrap_untrusted` neutralizes closing tags.
6. **Gate: complete.** Flag ∧ `supports_lookup` ∧ no R (evaluator.py, lookup_for_turn) ∧ not intro ∧ difficulty 1-5 ∧ hybrid + `turn_retrieval` ∧ BM25 ready ∧ latch ∧ filters, plus `sourced` (v≥4) in the evaluator. `precheck_answer` runs first. `MockEvaluator` lacks the attribute, so no lookup. The recorder wrapper forwards `supports_lookup`.
7. **Evals: fine for an approximation.** `--lookup` builds a fresh `TurnLookup` per sample per run, which resolves H3. `run_evaluator_sourced` counts tool ids as valid only when committed. The sim/TTFT split is fine apart from L5/L6.
8. **Docs** are accurate except the latency claim (M1) and the meaning of the `fallback` metric label (L3).

## Critical
None.

## High
None.

## Medium
**M1. Evaluator latency is double-counted on the mock path after a lookup failure.**
- Where: `app/agents/evaluator_lookup_call.py:46-49` + `app/agents/evaluator.py:136-140`.
- Problem: the failed-loop record (gateway `failure_fallback`, or `_record_cut`) carries latency ≈ L. The mock record then adds `now - started`, which already includes L. `to_metadata` sums them, so `latency_ms.evaluator` ≈ 2× wall time (probe: 2405 ms vs 1205 ms wall). The same happens for early loop failure → fallback call fails → mock. This skews `ttft_breakdown` (the evaluator stage, and `other` goes negative), `cost_latency` and the docs-06 claim "latency_ms.evaluator gồm cả thời gian vòng lặp lỗi".
- Fix: in the `except` of `evaluate_with_raw`, give the mock record only the time not already recorded. For example, `call_with_lookup` raises with `err.recorded_ms`, or compute `latency = elapsed - sum(r.latency_ms for r in collector.records[n0:] if r.agent == agent)`, where `n0 = len(collector.records)` is captured at `started`. Add an assertion to `test_slow_loop_...`: `to_metadata()["latency_ms"]["evaluator"] <= wall_ms + 50`.

**M2. H4 containment over-frees misconceptions.**
- Where: `app/evaluator_source_checks.py:88-91`.
- Problem: `_similar` accepts `t.lower() in m.lower()` where `t` is the point or quote of a tool-only contradicted point. Quotes can be 3 words and points are free LLM text (for example "Index" or "HashMap"). Any misconception containing that text is freed, even one grounded in a base snippet `S1` or in the LLM's own knowledge, or one that also matches a base-snippet contradicted point. Flag on can then score higher than flag off for reasons other than the tool chunk, which breaks the requirement.
- Fix:
  - (a) Keep `m` capping if it is `_similar` to any non-tool contradicted point (base or mixed ids).
  - (b) Use containment only when `len(_words(t)) >= 4`; otherwise use the ratio only.
  - (c) Add tests: a short point plus an unrelated misconception still caps, and a misconception matching both a tool-only and a base point still caps.

**M3. Tool-only misconceptions reach the Reporter unlabeled.**
- Where: `app/agents/evaluator.py:85`, `app/agents/reporter.py:74`.
- Problem: `Evaluation.misconceptions` mixes capping and uncapped items. The Reporter prompt uses "hiểu sai" for `improvements[].why`, so a claim the code judged as having no penalty authority can still appear as a weakness in the final report. The sim metric `misconception_rate` (`evals/sim_lookup_metrics.py:36`) also counts these items, so flag on inflates it by construction.
- Fix: either keep tool-only items out of `Evaluation.misconceptions` (log and trace only; YAGNI), or add `Evaluation.unverified_misconceptions` (FSD notice needed). Either way, compute `misconception_rate` on capping items only, or report both counts.

## Low
**L1. Stale "empty = newest" text after pinning v8.**
- Where: `app/agents/evaluator_provider.py:49`, `.env.example:39`, `evals/run_evaluator_sourced.py:146` (help "mac dinh ban moi nhat").
- Problem: these still describe the old default. Also `app/agents/registry.py:57` health-checks `get(agent, None)` (newest) while the runtime uses v8. If v8 is removed, health says llm but runtime returns config_error.
- Fix: update the text, and use `... or DEFAULT_PROMPT_VERSION` in the registry.

**L2. `load_lookup_settings` can crash every turn even with the flag off.**
- Where: `app/evaluator_lookup.py:55`.
- Problem: it runs on every turn before the flag check. `int(_number("inf"))` raises `OverflowError` and `"nan"` raises `ValueError`, so a typo in `EVALUATOR_MAX_TOOL_CALLS` breaks next-turn with the flag off.
- Fix: check `EVALUATOR_TOOLS` first and return `LookupSettings()`, and guard with `math.isfinite`.

**L3. `fallback` metric label is counted on the mock path too.**
- Where: `evaluator_lookup_call.py:51`; docs 02/09 say "chấm lại không tools".
- Problem: the label is recorded even when no plain re-score happens and the turn goes straight to mock.
- Fix: record `fallback` only before `gw.complete`, and a new label such as `budget_exhausted` when the turn goes to mock. Alternatively, reword the docs.

**L4. Fragment version is only partly recorded (audit L4 partial).**
- Where: `evaluator_lookup_call.py:62`.
- Problem: the fragment version appears only in the success log line, not in the Langfuse generation or the failure log.
- Fix: pass `metadata={"fragment": FRAGMENT}` through `observation`/`trace_fields`, or log it in the fallback warning.

**L5. Sim lookup metrics mix failed loops in.**
- Where: `evals/sim_lookup_metrics.py:30-35`.
- Problem: the failure record carries `tool_calls`, so failed loops count as lookups. `recorded` turns from failed loops have no tool docs, so they count as "empty".
- Fix: exclude turns whose `fallbacks` contain `evaluator_lookup_fallback` from `empty_rate`, or report them separately.

**L6. Fragment file is read from disk on every lookup turn.**
- Where: `app/evaluator_lookup.py:61-63`.
- Problem: `fragment_text()` does sync disk I/O in the event loop each time.
- Fix: `functools.lru_cache`.

**L7. The flag-off "byte-identical" test is weak.**
- Where: `tests/test_evaluator_lookup_call.py:69`.
- Problem: it only checks that there are no tools and no fragment.
- Fix: compare `client.calls[0]` to `build_messages(prompt.text, inp, True)` plus the expected params snapshot, or store a golden request JSON.

**L8. H4 misses points dropped by the quote check (conservative).**
- Problem: contradicted points that fail `quote_in_answer` (or fall beyond `MAX_COVERED`) never reach `contradicted`, so a misconception the LLM derived from a tool chunk with a paraphrased quote still caps. This is acceptable because it matches flag-off behavior.
- Fix: document it in docs 05.

## Positive
- The single clock is implemented exactly as H1 asked, and the tests cover a slow loop, late failure, a capped fallback and the latch.
- The result is trimmed before wrapping, so the untrusted block stays closed, and the ids stored match exactly what the LLM saw.
- `inner` collector plus merge avoids double fallback records, and `_record_cut` covers cancellation cleanly.
- `committed` handling satisfies L5, and the recorder wrapper forwards `supports_lookup`, which would otherwise have silently disabled lookup in the sim.
- The eval `--lookup` approximation (category None) is documented honestly.

## Recommended actions
1. M1: fix the latency accounting and add the assertion.
2. M2: tighten the matching and add 2 tests.
3. M3: decide whether tool-only misconceptions are reported, and fix `misconception_rate`.
4. L1-L3 (small), then the rest.

## Score: 8/10

## Unresolved questions
- M3: should the final report show "hiểu sai" that rests only on tool chunks? The spec says "vẫn trả về cho báo cáo", but this conflicts with "chunk tra cứu không có quyền phạt" at report level.
