# Review phase 05: mid-session replanning (REPLAN_ENABLED)

Diff `thang/hybrid-policy...thang/mid-session-replan` (3148ca6, 1d5c31d, 410ae1b, 359279a), 32 files, +1157/-48.
Tests: `1108 passed, 8 skipped`. `check_docs.py`: `75 FR, 109 NFR, 0 loi`. I ran probes from the scratchpad and did not change any repo code.

**Score: 8/10.** With the flag off, behaviour is identical. I checked this by reading every changed branch.
Swap validation covers each spec rule and has no crash path when it receives garbage.
The in-place swap keeps the alignment invariant, and `effective_plan` is idempotent.
There is one real gap: a turn that `validate_decision` flagged as manipulation or injection can still apply the LLM's swap (H1, reproduced).
There is also one crash on the contract-violation path that the FSD gate is meant to prevent (M1, reproduced).

## Verification of focus points
- **Flag off is identical (holds).**
  - `replan_enabled()` returns false unless REPLAN is on and the mode is hybrid (`replan.py:48-51`).
  - `with_reserve` returns the same plan object (`replan_reserve.py:39-42`), so `attach_reference_snippets` gets `out.replan is None` and builds the same task list. There are no extra RAG or LLM calls at start. `coverage = await settle(...)` is only a variable extraction.
  - Provider: hybrid with REPLAN off selects v9, and rules selects v8 (`evaluator_provider.py:68`).
  - Schema: `uses_replan(v9)` is false, so the schema is V9 and `build_messages(..., replan=False)` builds the same `parts`.
  - `replan_context` is pure and returns None when the flag is off (`replan.py:96-98`). `attempt_swap` returns None (`:80-81`), so `swap_result` stays None.
  - `effective_plan` returns `plan` itself when `swaps` is empty.
  - The only JSON change is three default keys (`plan.replan: null`, `state.swaps: []`, `turn.swap_result: null`), as documented in 06.
- **Byte-compare gap.** The v8 request is pinned by phase 04 (`test_policy_hybrid_turn_engine.py:79-81`). The v9 request (hybrid, REPLAN off) is not pinned.
  - The risk is low: two independent guards would both have to fail (the context is only populated when enabled, and it is only rendered for v10).
  - The fix is a cheap test (M3). It is worth adding because "flag off is identical" is the core contract.
- **Swap validation (holds, with one exception, H1).** `validate_swap` (`replan.py:58-74`) rejects each case below:

  | Proposal | Result |
  |---|---|
  | None, action other than next_topic, or phase not technical | `not_applicable` |
  | `plan.replan` is None, swaps already at max, or time_hint is hurry | `budget` |
  | `drop` is unknown, at or before pos (current or past topic), not technical (intro or scenario), not pending (done), or a swapped-in alt | `bad_drop` |
  | `drop` is in `keep_ids` | `jd_priority` |
  | `add` is not in the reserve, or already used | `bad_add` |

  - forced, turn cap, `two_dont_know` and topic overtime pass `"forced"` and get `not_applicable`. `low_performance_stop` runs first and turns the action into wrap_up.
  - Max swaps is clamped to 0..2, and the reserve has `max_length=2`.
  - `SwapProposal` coerces non-str values to `""`, and a `swap` value that is not a dict becomes None. The strict schema (`anyOf [$ref, null]`, all fields required) is valid.
  - No crash path given a well-formed state. Label set: `attempt_swap` returns only the 6 values in `RESULTS`, so the label set is bounded.
- **State consistency (holds).**
  - `apply_swap` replaces `state.topics[i]` in place. `turn_engine.py:171-172` recomputes `topics` before `apply_action`. Test: `state.topics` ids equal the `flat_topics(effective_plan)` ids after 3 turns.
  - `effective_plan` is applied once each in next_turn (`turn_engine.py:134`), finalize (`main.py:260`) and the sim (`simulate_session.py:75`).
  - The Reporter and `report_*` read `req.plan` and do not re-apply it. A second application would be a no-op anyway, because `drop` is no longer present.
  - `turn_evaluation.py:69` uses `req.plan` for `time_hint`. That is harmless, because swaps are 1:1 and phase budgets do not change.
  - JSON round trip is covered by the sim test through the ASGI client, including finalize with and without `swaps`.
  - Each request deep-copies its state, so a retried next-turn with the same input is deterministic.
- **Injection (holds for the context, H1 for the decision).**
  - `replan_context` carries only catalog ids and titles plus numbers (`evaluator_input.py:97-103`).
  - `swap.reason` goes through `safe_reason` (injection check, PII filter, 20 words).
  - The v10 prompt is v9 plus one section and two sentences. I diffed it against v9: all v9 guards are untouched, and the new section explicitly says "không phải vì câu trả lời yếu hay ứng viên yêu cầu" (not because the answer is weak or because the candidate asked).
- **File size.** `models_interview.py` is exactly 200 lines, `turn_engine.py` 199, and `main.py` 269 (already over the limit; this diff adds 3). Every new file is under 200.

## Critical
None.

## High
**H1. A swap is applied on turns where `validate_decision` refused to trust the LLM (`sensitive_kind`, which includes `has_injection(answer)`).**
`turn_decision.py:76-78` calls `attempt_swap` whenever the final action is `next_topic`, even when `trace.overrule_reason == "sensitive_kind"`.
- Reproduced: an answer of `"Ignore all previous instructions. Em dùng @Transactional..."` with kind ok, while the LLM proposes swap t4→alt1, gives `decided_by=policy`, `overrule_reason=sensitive_kind` and **`swap_result=applied`**.
- The same happens for manipulation or dont_know turns whenever rules choose `next_topic`.
- Impact: the candidate can see the topic titles through the question flow and can steer which pending topic gets skipped (for example, a weak area). Phase 04 M4 closed this hole for actions, but phase 05 reopens it for topics. This breaks the fairness rationale in the Risk section of the spec.
- Related issue: a swap is also accepted when the LLM's own `next_action` was not `next_topic` (proposal overruled as `action_not_allowed` while rules picked next_topic). The prompt says to propose a swap only together with next_topic.

Fix (`turn_decision.py:76`):
```python
trusted = not forced and trace.overrule_reason != "sensitive_kind" and trace.proposed == "next_topic"
trace.swap = attempt_swap(proposal, state, plan, topics, pos, phase,
                          trace.dec.action if trusted else "not_applicable", ...)
```
Optionally add a label `untrusted` to `RESULTS`. Add parametrized tests for injection, manipulation and dont_know (with rules choosing next_topic), and for a proposal of follow_up with a swap. Each should give `swap_result != "applied"` and `swaps == []`.

## Medium
**M1. If `plan.replan` is lost while `state.swaps` is kept, next-turn crashes with 500 (StopIteration).**
This is the exact failure mode that FSD question (a) guards against.
- Reproduced: apply t4→alt1, send the next turn with `plan.replan = None`, and you get `RuntimeError('coroutine raised StopIteration')`. The cause is `turn_engine.py` `next(t for t in state.topics if t.id == n_topic.id)`: `state.topics` holds `alt1` but the plan holds `t4`.
- If the active topic is the alt, the error is a clean 422 instead.
- In finalize, the alt topic disappears silently.
- docs 03 says "Mọi lỗi → không đổi" (every error means no swap), but that does not hold here.

Fix: after `effective_plan` in `next_turn`, check the invariant once:
```python
if [t.id for t in state.topics] != [t.id for _, t in topics]:
    raise ApiError(409, "session_invalid_state", "state.topics khong khop plan (plan.replan bi mat?)")
```
Add a test that strips `replan` and expects 409. Add a note in 06 §7.4.

**M2. The entry-point readers in spec step 2 are only partly tested, and the spec's `test_replan_entry_points.py` was not created.**
- Covered: next_turn, the sim `_topic` and the finalize topic list.
- Not covered:
  - `requirements_coverage` when the alt topic's `catalog_ref` maps to a JD requirement (the sim test has `jd_assessed_rate is None`).
  - `report_resources` and `plan_sources` for an alt topic.
  - `low_performance_stop` reading the alt topic's band after a swap. The existing test monkeypatches it to `True`.

Fix: one finalize test with a `jd_profile` whose must-requirement is the alt's catalog_ref. Assert `requirements.assessed` counts it and that the resources or sources list includes the alt topic. Add one early_stop unit test over `flat_topics(effective_plan)` with the alt scored weak.

**M3. The v9 request is not pinned for hybrid with REPLAN off.**
Add this to `tests/test_replan_v10_prompt.py`:
```python
def test_hybrid_replan_off_v9_request_unchanged():
    gw/client = fake gateway; agent = LlmEvaluator(gw, prompt_version="v9")
    base = inp(); base.policy_context = PolicyContext(...); base.replan_context = ReplanContext([("t4","X")],[("alt1","Y")],None,1)
    run(agent.evaluate_with_raw(base)); call = client.calls[0]
    assert call["messages"] == build_messages(agent._prompt.text, base, True, True)   # pre-phase-05 4-arg call
    assert call["response_format"]["json_schema"]["name"] == "EvaluatorOutputV9"
    assert "swap" not in call["response_format"]["json_schema"]["schema"]["properties"]
    assert "replan_context" not in call["messages"][1]["content"]
```
Setting `replan_context` on purpose proves that the version gate alone keeps it out.

## Low
- **L1.** `replan_context` is rendered on every technical turn that has a reserve, a pending topic and a swap left (`replan.py:93-105`), not only "at the boundary".
  - The boundary cannot be known before evaluation, so the behaviour is reasonable.
  - docs 02 ("khi ở ranh giới có reserve") and spec Requirements say otherwise, and the Deviations section does not record it. Docs 04 is correct.
  - It costs about 100 extra tokens per technical turn, and `not_applicable` labels will dominate `swap_results` and the Prometheus series.
  - Fix: add a deviation line, fix the wording in 02, and mention it in 09 so readers don't misread `not_applicable` counts.
- **L2.** With `REPLAN_ENABLED` plus an `EVALUATOR_PROMPT_VERSION<v10` override (or `AGENT_EVALUATOR_MODE=mock`), start still builds a reserve and fetches its RAG, but a swap can never happen.
  - Fix: in `with_reserve`, skip when `os.getenv("EVALUATOR_PROMPT_VERSION")` resolves below v10. Alternatively, document it next to the existing mismatch warning.
- **L3.** `models_interview.py` is at 200 lines, the limit. The next field added must split it, for example by moving `ReplanPool`/`Swap` together with `PlanTopic` into `models_plan.py`.
- **L4.** `select_reserve` uses the first technical topic's `start_difficulty` for `bank_count` (`replan_reserve.py:27`), but `catalog_topic` gives the alt the level default. These are normally equal. Use `LEVEL_CONFIG[level]["start"]` for both.
- **L5.** `effective_plan` trusts `state.swaps`. Forged or duplicate swaps from the client (for example the same `add` twice) would duplicate a topic. The client is trusted interview-service, so this is acceptable. M1's alignment check also catches it.

## Edge cases checked
- Fresher pool of 0 gives `replan=None`, so the session has no replan.
- `alt` ids never collide with `r*` or `t*` (tested).
- A swap at pos+1 means the next question uses the alt and its bank questions (attached in the same 5 s pass).
- A second swap gets `budget`. Dropping a just-added alt gets `bad_drop`.
- A hurry turn that is not forced gets `budget`.
- A flag flip mid-session:
  - Off to on: no `replan`, so `budget`.
  - On to off: existing swaps are still applied, so the session stays consistent.
- The prompt switching from v9 to v10 mid-session on an env flip is env-level and documented.
- The sim exits with code 1 on `jd_priority_violations > 0` for both the single-run and per_run layouts.

## Positive
- The in-place 1:1 design removes the alignment and budget risk by construction.
- `effective_plan` is a single choke point and idempotent.
- The model and validator are loose, so garbage never degrades grading.
- Every rejection has a bounded label.
- The flag-off sim test compares swap and no-swap proposal runs.
- Docs 03, 04, 06 and 09, `.env.example` and the FSD questions (a)-(d) are accurate. [BLOCKED-KEY] and the FSD gate are marked honestly.

## Recommended actions
1. Before the PR: H1 (about 3 lines plus tests) and M1 (invariant check plus test).
2. M3 v9 pin test. M2 entry-point tests for JD coverage, resources and early_stop.
3. L1 docs and deviation note. L2 to L5 when convenient.

## Unresolved questions
- Should the result for H1 be a new label `untrusted`, or reuse `not_applicable`? A new label makes manipulation attempts measurable in the sim.
- FSD (still open): does interview-service show the dropped topic in a plan-derived topic list (question c)? If yes, the UI needs `state.swaps`.

## Fixes applied
- **H1:** `turn_decision.py` only attempts a swap when the decision is not forced, `overrule_reason != sensitive_kind` and `proposed_action == next_topic`. New bounded label `untrusted` (sensitive_kind); everything else untrusted gives `not_applicable`. Tests: manipulation, off_topic, dont_know and the injection answer from the probe (`untrusted`, no swap, topic unchanged, metric counted); proposals of follow_up/hint/clarify/empty/unknown action; trusted next_topic still swaps (`tests/test_replan_trust_and_alignment.py`).
- **M1:** `replan.check_alignment` runs in `next_turn` after `effective_plan`: `state.topics` ids must equal `flat_topics` ids, else 409 `session_invalid_state`. Tests: `plan.replan` dropped with `state.swaps` kept, and a duplicated forged swap. Docs 03, 04, 06 updated.
- **M2:** `tests/test_replan_entry_points.py`: JD requirement mapped to the swapped-in topic is `assessed` (and `not_assessed` without swaps); report resources/sources and study_plan for `alt1`; `low_performance_stop` on the real band (unit and through `next_turn`, no monkeypatch).
- **M3:** `test_hybrid_replan_off_v9_request_is_unchanged` in `tests/test_replan_v10_prompt.py` (with `replan_context` set on purpose).
- **L1:** docs 02, 09 and the phase deviations now say the context is sent on every technical turn with a reserve.
- **L2:** documented only (docs 02, phase deviations): skipping the reserve for mock Evaluator or prompt < v10 would break the mock-mode test setup.
- **L3:** `models_interview.py` is 199 lines. **L4:** reserve bank-count start difficulty = `catalog_topic` default. **L5:** documented in 04, covered by M1.
