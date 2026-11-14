# Audit: plan 261114-1549-agentic-ai-service (adversarial, code-verified)

Scope: plan.md + phase-01..06 vs code at `main` cbb51f7 (`apps/ai-service`). All file:line below re-read from code, not from plan.
Most plan line refs are correct (gateway, retry, evaluator, turn_engine, policy, state_update, early_stop, source checks). Wrong ones in L1.

## Hard-requirement checklist

| Requirement | Status | Finding |
|---|---|---|
| Each item own flag, default off; off = unchanged | **Broken** (v9 changes default for direct `LlmEvaluator(gw)`); API JSON gains keys | C1, M6 |
| LLM proposes, code decides; fallback; forced/low_perf/turn cap above LLM | Mostly OK; fallback path can blow the 15 s first-event limit; validator too weak on weak/strong consistency | H1, H8 |
| Untrusted text: injection + length caps | focus/notes/swap reason OK; `action_reason` and tool `query` only length-cut | M8 |
| Positional alignment in replanning; finalize/report see swaps | OK (in-place swap + `effective_plan` at 3 entry points; readers verified) | M5, M9 |
| Tool chunks S{n+1}, postcheck/cited_sources/source_refs see them; only R refutes | Ids OK; "only R refutes" **not enforced** for LLM-written `misconceptions` | H4 |
| Code + fake tests first, live steps wait | OK ordering; but several gates **cannot be measured** with tooling as planned | C2, H3, H5, H6, H7 |

## Critical

**C1. Adding `evaluator.v9.md` still changes the default prompt — the pin in the provider does not cover direct callers.**
Plan: phase-04 Key Insights / Step 2 ("`test_llm_evaluator.py:63,129` vẫn xanh vì ghim").
Code: `PromptStore.get(version=None)` → max version (`app/prompts/store.py:37-38`). `LlmEvaluator.__init__` passes `prompt_version` straight through (`app/agents/evaluator.py:191-193`). Direct constructions with no version: `tests/test_llm_evaluator.py:50` (asserts `"v8"` at `:63`, `:129`), `tests/test_llm_hedge.py:168`, `tests/test_report_failure_signals.py:130`; eval scripts `evals/run_evaluator.py:41,119` and `evals/run_evaluator_sourced.py:62,137` (`--prompt` default None = "bản mới nhất"). Once v9 (then v10) exists, these pick it up: tests fail (version + V9 required fields missing from fake JSON → repair → degraded), and every Phase 03 baseline run of `run_evaluator` silently switches to v9.
Fix: pin inside `LlmEvaluator` (e.g. `DEFAULT_EVALUATOR_PROMPT = "v8"` used when `prompt_version is None`) and keep provider logic only for choosing v9/v10 per `POLICY_MODE`. Update eval-script help text ("mặc định v8, ghim"). Add test: with v9 file present, `LlmEvaluator(gw).prompt_version == "v8"`. Keep the `v9→v99` edit in `test_evaluator_source_checks.py:83`.

**C2. Hybrid policy is never active in the simulator, and the agreement/overrule metrics cannot be computed from sim output.**
Plan: phase-04 Key Insights ("`_RecordingEvaluator` không có → decide()"), Step 9, Success Criteria; phase-06 matrix.
Code: every sim run wraps the evaluator: `evals/simulate.py:97` (`with record_documents()`), wrapper has only `evaluate` (`evals/turn_source_recorder.py:31-37`). So `evaluate_with_raw` is never found → no proposal → `hybrid` == `rules` in all sims → overrule/stdev/gap gates compare rules vs rules.
Also: `evals/simulate_session.py:74-77` copies a fixed key list from `turn` (no `decided_by`/`policy_action`/`action_reason`), so `sim_metrics` never sees the new fields. And `TurnInfo.action` is the post-apply action: `next_topic` becomes `ask_main` (`app/turn_engine.py:34-35`, `app/state_update.py:81`), low-perf turns become `wrap_up` → planned `decision_agreement = policy_action == action` is always false for next_topic. Overrule reason only goes to a Prometheus counter, which the sim does not read.
Fix: (a) give `_RecordingEvaluator` an `evaluate_with_raw` passthrough (or record in `evaluate_turn`); (b) in `simulate_session` copy `decided_by`, `policy_action`, `proposed_action`, `overrule_reason`; (c) store pre-apply `dec.action` values (`policy_action` = rules, `proposed_action` = LLM, `overrule_reason`) in TurnInfo (or a debug-only block) and define agreement on those; (d) add a test that a sim session with fake V9 evaluator in hybrid yields `decided_by="llm"` on some turn.

## High

**H1. Fallback after a failed tool loop can exceed the 10 s budget and the 15 s first-event limit.**
Plan: phase-02 Requirements ("chia sẻ ngân sách"), pseudocode `ChatCall(... started=budget_started)`; phase-03 `call_with_lookup` fallback `gateway.complete(..., budget_started=t0)`.
Code: only calls after the first in a closure are budget-capped (`app/llm/gateway.py:89-92`, `if calls and budget_s ...`); `call_with_retry` gives the first attempt the full `timeout_s` even with budget 0 (`app/llm/retry.py:87-89,93-95`). A new `ChatCall`/`complete` starts with `calls=0` → full 8 s again (+hedge). `deadline_s=2.0` is only checked between steps, a single step can run 8 s. Worst case: loop ~10 s → `LlmError` → fallback 8 s(+retry) → mock ≈ 18-20 s before `next_turn` returns; the `meta` event is sent only after that (`app/main.py:241`, `_stream`), contract says first event ≤ 15 s (`docs/ai-service/06-api-contract.md:302`). Today worst ≈ 10-11 s.
Fix: when `budget_started` is given, cap every call incl. the first at `min(timeout_s, budget_s - elapsed)`; skip the fallback LLM call (go straight to mock+degraded) if remaining < ~2.5 s; cap each loop step at `min(timeout_s, deadline remaining + final-call reserve)`. Add fake tests: slow step 1 → total < 10.5 s; failed loop + fallback stays inside 10 s.

**H2. Notes + PolicyContext go into the same Evaluator call that scores → "note không dùng để tính điểm" is false; no Evaluator-quality gate for v9/v10.**
Plan: phase-04 Requirements ("Không dùng note để tính điểm"), Success Criteria (no golden/holdout gate); phase-05 v10.
Code: Evaluator output bands come from the same LLM call (`app/agents/evaluator.py:217-230`); cách A puts state (`hinted`, `time_hint`, open notes like `risk: yếu X`) into that prompt → anchoring bias on scores. `run_evaluator` golden/holdout and `judge_support` are gated only in phase 03.
Fix: add to phase-04/05 gates: `run_evaluator --set main` + `holdout --runs 3` with v9 (and v10) band agreement not lower than v8; sim score gap with notes on vs off. Limit notes shown to Evaluator to `to_verify` (not `strength`/`risk`), or defer item 4 until hybrid shows value (only consumer of notes is this scoring call, since Reporter/Interviewer don't read them).

**H3. Phase 03 golden/holdout gate is a no-op.**
Plan: phase-03 Step 7, Success Criteria ("Độ khớp band golden + holdout không giảm").
Code: `evals/run_evaluator.py:45` and `run_evaluator_sourced.py:66` build `EvaluationInput` via `to_input(s)` with no `lookup` → `EVALUATOR_TOOLS=true` has no effect there; numbers equal by construction.
Fix: build a `TurnLookup` in both scripts when the flag is on (memory BM25 via `memory_retriever()` / `warm_rag()`, same filters), or drop the gate and rely on sim + `judge_support`. State which.

**H4. "Chỉ R bác ý sai" not enforced for LLM-written misconceptions; tool chunks raise penalty exposure.**
Plan: phase-03 Key Insights / Security ("Chunk công cụ không được bác ý"), Step 5 test "contradicted dựa S mới không hạ technical_accuracy".
Code: code-level refutation is R-only (`app/evaluator_source_checks.py:57-61`), but prompt v8 tells the LLM to also write `misconceptions` for any `contradicted` (`app/prompts/evaluator.v8.md:41`), and any misconception caps `technical_accuracy` (`app/agents/evaluator.py:172-173`, rule 4 at `evaluator.v8.md:29`). Lookup queries are steered by the candidate's answer. The planned test passes only because the fake LLM writes no misconceptions.
Fix: in `postcheck`, drop LLM misconceptions that match (quote/point, `SequenceMatcher ≥ 0.8` like `merge_misconceptions`) a contradicted point whose valid ids are all tool-chunk ids (ids > `base_ids`); add rule to `evaluator_tools.v1.md`; measure misconception rate and `technical_accuracy ≤ 1` rate flag on/off.

**H5. `--runs N` as specified breaks every sim metric and the document recorder.**
Plan: phase-01 Step 3 ("session key thêm `#run{i}`").
Code: metrics index `personas[pid]` by session key (`evals/sim_metrics.py:35,40,50,66,82,96,113-114`); `attach_documents` rebuilds sid as `sim-{pid}` (`evals/turn_source_recorder.py:54`); `run_session` uses `sid = f"sim-{persona.id}"` (`evals/simulate_session.py:51`) → concurrent runs of one persona collide on recorder key `(sid, turn_number)` (`turn_source_recorder.py:17,36`).
Fix: run N times producing `sessions_by_run: List[Dict[pid, session]]`, summarize per run with existing functions unchanged, aggregate in `sim_runs.py`; pass run index into `run_session` sid (`sim-{pid}-r{i}`) and `attach_documents`.

**H6. Stdev gate not measurable with 3 runs per persona.**
Plan: phase-04/06 Success Criteria ("stdev 3 lần mỗi persona ≤ 1,2× rules và ≤ 0,5/10").
Evidence: per-persona stdev from n=3 has df=2; ratio of two such stdevs needs to be ~6× (variance ratio ~39) to be significant at 5%. Simulator itself runs at temperature 0.8 (`app/llm/settings.py:29`), so most spread is simulator noise.
Fix: gate on pooled within-persona stdev across all personas (df ≈ 2×#personas) with bootstrap CI, or ≥5 runs on the quick set; same for the gap ±10% gate (report CI).

**H7. JD-coverage gate and `keep_ids` untestable in sim.**
Plan: phase-05 Requirements (`keep_ids`), Success Criteria ("Độ phủ yêu cầu JD không giảm"), Step 6.
Code: sim start sends no `jd_profile`/`cv_profile` (`evals/simulate_session.py:52-53`), finalize sends no `jd_profile` (`:89-92`) → `requirements_block` returns None (`app/requirements_coverage.py:17-18`); `Persona` has no JD (`evals/personas.py`).
Fix: add JD fixtures to `skewed` personas (and CV for ranking), pass in start + finalize; test that a JD-priority topic is never dropped in sim.

**H8. Hybrid validator allows decisions inconsistent with code-checked score.**
Plan: phase-04 `validate_decision`.
Code: proposal comes from raw LLM output before `postcheck` caps (`app/agents/evaluator.py:230`); validator only checks sensitive kinds + budget. Rules give weak answers a hint before moving on (`app/policy.py:48-52`); LLM could pick `next_topic` (no hint) or `follow_up` with `+1` on a weak (post-cap) answer.
Fix: after clamping, enforce sign by `classify(ev)`: weak → delta ≤ 0 and if rules chose `hint`, allow only `hint`/`clarify`; strong → delta ≥ 0; ok → delta 0. Test each.

## Medium

**M1. `POLICY_MODE=shadow` is YAGNI and unmeasurable.** phase-04 Overview/Architecture. In shadow, `decided_by="policy"` and action = rules, agreement only in a log line/Prometheus. Offline sim of `hybrid` already records the rules counterfactual (`policy_action`). No production traffic to shadow. Fix: drop shadow (two modes `rules|hybrid`); saves v9 cost on non-effective turns and tests.

**M2. Split final-call mode is speculative and differs from researcher's fallback.** phase-02 Overview/pseudocode (`msgs_for_final` rewrites tool messages into a user message, default `true` before probe). Researcher fallback keeps tools and applies schema on the final `tool_choice="none"` call (`plans/reports/researcher-261114-1549-...md:37`); OpenAI natively supports tools + json_schema strict. Default `true` makes the least-verified path the default. Fix: build the non-split loop only; on `tools_unsupported` latch a process flag and route to the existing no-tools path; add split only if the probe returns 404/400.

**M3. Repair inside the loop is under-specified.** phase-02 pseudocode `parse_or_repair(chat, ...)` reuses the tool-enabled `ChatCall` (`tool_choice="auto"`) → repair turn can return `tool_calls` and `content=None`; in split mode repair runs under `json_object` not strict. Fix: repair with `tool_choice="none"` (and strict schema/final ChatCall in split); test it.

**M4. Failed-loop latency is lost.** Gateway adds a `CallRecord` only on success (`app/llm/gateway.py:124-125`); a failed loop then fallback → `latency_ms.evaluator` underreports, `ttft_breakdown` cannot split (`evals/ttft_breakdown.py:39-40` uses `fallbacks`). Fix: on loop failure add `CallRecord(..., fallback="evaluator_lookup_fallback", latency_ms=...)`; add to `FALLBACK_KINDS`; report new fallback code to FSD.

**M5. v10 per-turn prompt switching is under-specified and unfair.** phase-05 Requirements ("chọn v10 khi ... `plan.replan` có reserve chưa dùng"). `get_evaluator()` has no plan/state (`app/agents/evaluator_provider.py:42-54`); switching v9↔v10 mid-session changes the scoring prompt and breaks prompt cache. Fix: one new version for the session (v10 whenever REPLAN on, `swap: null` when not applicable; context block only when reserve exists), or merge swap into v9 as nullable field.

**M6. "Flags off = output identical" is false for JSON shape.** phase-05 Success Criteria ("output `/api/start`, `/api/next-turn`, `/api/finalize` y cũ") contradicts phase-04 NF ("chỉ thêm khóa null"). `model_dump()` emits defaults (`app/main.py:230-231,245-247`): `plan.replan: null`, `state.swaps: []`, `state.notes: []`, TurnInfo nulls. Fix: reword to "decisions/values unchanged, new keys with defaults"; one FSD notice for all new keys (04+05 together).

**M7. Phase-01 scenario category change misses callers and cites wrong line.** Step 2 says `plan_snippets.py:127`; scenario branch is `:116` (`:127` is technical). `Retriever.retrieve_for_topic`/`plan_snippets` take singular `category` and build `SearchFilters` (`app/rag/retriever.py:110,127,135,152-156`); hybrid search passes it on. Fix: list `rag/retriever.py` (+ `hybrid_search.py` if it filters) in Modify; keep `category` param and add `categories`; test vector path SQL with 1-element list == old SQL.

**M8. Untrusted text filters incomplete.** `action_reason` is only cut to 160 chars and goes to `TurnInfo.reasoning` (returned to interview-service, `app/turn_engine.py:205`); tool `query` only cut to 200 (requirement asks injection checks). Fix: pass `action_reason` through `safe_focus` + PII regex (`app/cv_text.py:20-24`), drop on hit; `has_injection(query)` → `"error: invalid_query"` (cheap, logs metric).

**M9. FSD gate question too narrow.** phase-05 Step 0 asks only "lưu nguyên JSON". interview-service may resolve `turn.topic_id` (now `alt1`) against its stored plan or render the plan topic list (dropped topic shown, never asked). Fix: add both questions to the FSD request.

**M10. Threshold calibration method overfits.** phase-01 Architecture (midpoint P75 weak / P25 average from persona labels). Persona quality ≠ per-turn quality; tuning and checking "gap không giảm" on the same sim runs. Fix: calibrate on labelled golden turns (`evals/evaluator_golden*.jsonl` bands) or tune on one run set and verify on another; mark result provisional.

## Low

- L1. Wrong refs: Evaluation block is `models_interview.py:174-226` (not 166); `evaluator_provider.py` has 54 lines (plan cites `:17-60`, `:40-60`); phase-05 lists `turn_engine:96` (inside `start_session`) as a next_turn reader; `plan_snippets :127` vs `:116` (M7).
- L2. `tests/fakes/fake_llm.py` already records params (`FakeOpenAI.calls`); `status_error(404)` maps to `InternalServerError` (`fake_llm.py:29-31`) → add `404: openai.NotFoundError` for the unsupported test.
- L3. `require_parameters=True` applies to all params (seed, reasoning) → may route lookup turns to a different provider than non-tool turns; probe should log provider with/without it.
- L4. Tools fragment version not in metadata; do not encode as `"v8+tools1"` (`uses_sources` does `int(...)`, `app/agents/evaluator.py:67`); add separate metadata/trace field.
- L5. Recorder should read `inp.lookup` only when the loop succeeded (texts are appended before a later failure).
- L6. `tools_unsupported` "log once" still pays a failed request every turn → latch (see M2).
- L7. 02 does not depend on 01 code (only probe for default) → can run in parallel; phase 06 could be a checklist in 05's PR. 6 phases acceptable otherwise.

## Planner deviations (plan.md)

| Deviation | Verdict |
|---|---|
| Pin v8 as default | Agree, but pin in `LlmEvaluator`, not provider (C1) |
| Separate `evaluator_tools` fragment | Agree (keeps v8/v9 orthogonal; `PromptStore` glob `evaluator.v*.md` won't match `evaluator_tools.v1.md`). Note L4 |
| Decision via `evaluate_with_raw` | Agree; needs recorder passthrough + sim fields (C2) |
| No `skipped` status | Agree; verified `report_scoring.py:84-86` skips topics with no scored turns, readers covered by `effective_plan` |
| Reporter not reading notes | Agree (YAGNI); consequence: only consumer is the scoring Evaluator (H2) — consider deferring item 4 |
| `effective_plan` at entry points | Justified: next-turn does not return plan (`main.py:245-247`), readers verified (`report_scoring:82,100`, `requirements_coverage:20`, `report_resources:26`, `reporter.py:71`, `simulate_session:47`) |

## Verdict

**Ready after fixes.** Must fix in plan before coding: C1, C2, H1 (and H4 for phase 03). Fix before any [BLOCKED-KEY] measurement: H3, H5, H6, H7. Rest can be folded into phase steps. Drop shadow (M1) and defer split mode (M2) to cut ~1d.

## Unresolved questions

1. Does OpenAI/OpenRouter accept `role=tool` history without a `tools` param? Only matters if split mode is kept (M2).
2. Owner: drop `POLICY_MODE=shadow`? Defer notes (item 4) until hybrid passes gates?
3. FSD: does interview-service resolve `topic_id` against its stored plan / show the plan topic list (M9)? Accept new default keys in `plan`/`state`/`turn` (M6)?
4. Should lookup work when `RAG_TURN_RETRIEVAL=false` but BM25 loaded? Gate in phase 03 does not say.
5. Is a pooled-stdev gate (H6) acceptable to the team in place of per-persona 1,2×?
