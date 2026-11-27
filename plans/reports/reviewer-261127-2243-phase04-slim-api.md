# Review phase 04: slim /api/next-turn + /api/finalize (checkpoint = source of truth)

Scope: git diff main (app/main.py, session_store/*, turn_graph_nodes.py, dev-play.js, evals/simulate_session.py, tests, docs 03/06/07) + untracked models_interview_http.py, session_request_builder.py, tests/helpers/seed_session.py, tests/test_session_request_builder.py. Targeted tests: 53 passed. I probed behaviour with a temp test file in tests/ and deleted it afterwards. Nothing else in the repo was changed.

## Overall
Solid. The builder reproduces the old request on every golden turn, including STT reask, hybrid/swap, bank and hard-limit turns (test_session_request_builder compares the whole model_dump). Lock, replay and error order is correct. No Critical issues.

## High
H1. If the checkpoint write fails at /start, the stream still sends `done`, and every later call returns 404.
- Where: app/main.py:252-259 and session_record.py record_start (except branch only logs).
- Before phase 04, a missing thread fell back to the request body. Now the candidate sees question 1, answers it, and gets 404. FSD has to call /start again, which gives a new plan and a new question.
- The record_start docstring still says "next-turn dau gap thread chua co thi chay tu request roi ghi", which is stale.
- The test `test_start_while_a_turn_runs_is_rejected_and_failed_start_write_still_sends_done` locks this behaviour in.
- Fix: make record_start return a bool or raise. In `events()`, when the write failed, yield `event("error", {"errorCode": "SESSION_STORE_UNAVAILABLE", "retryable": True})` instead of done, so FSD retries /start right away. Update the test and doc 06.

H2. SESSION_STORE=memory is now a correctness problem, not just a durability one.
- Where: session_checkpointer.py:53 (warning only) and :70-75 (prunes after 500 sessions).
- A restart or a prune of an older live session now means 404 in the middle of a session. Before, it was a silent fallback.
- Fix: in strict env (staging/production), refuse to start with memory, as check_agent_config does. Or at least record this as a deploy gate in docs 07 §8.8 and the deployment guide.

## Medium
M1. The finalize `end_reason` from the body always wins in the report. This contradicts doc 06 and the spec's intent.
- Where: session_request_builder.py:48-51 sets `state.end_reason = stored or body`, but `FinalizeRequest.end_reason = body.end_reason`. report_scoring.py:107 reports `req.end_reason`.
- Probe: a session ended with plan_complete, finalized with `end_reason="anything_goes"`, shows report.session.end_reason = "anything_goes".
- test_session_request_builder.py:89 asserts this split (`state plan_complete`, `req user_ended`).
- Fix: compute `reason = stored_state.end_reason or body.end_reason` once and use it for both fields. Change the assert to expect `req.end_reason == "plan_complete"`.

M2. Threads written by phase 03 fail in two different ways.
- Probe: a seeded phase-03-shape thread (no `turn`, transcript entries without topic_id/phase).
- next-turn returns 200 but is silently wrong. `turn={}` gives turn_kind "main", and topic_id None matches every old entry, so topic_turns gets the last 5 turns across all topics. The new transcript entry is then written with topic_id/phase None.
- finalize raises KeyError 'phase' at session_request_builder.py:33, giving 500. A thread with no `session` key gives KeyError at :22 / main.py:280.
- Phase 03 was never deployed, so this only hits local Postgres dev threads. Still cheap to make clean.
- Fix: in stored_values (session_turn_guard.py), if `"turn" not in values or "session" not in values`, log `session_schema_outdated` and raise 404 session_not_found (the caller restarts). Or add `schema_version` to `session` now for the next migration.

M3. The notes-validation test is now vacuous.
- Where: test_agent_notes_turn_engine.py:104-112. It passes only because `state` is an extra field.
- Nothing else checks Note limits (grep: no other ValidationError tests on notes).
- Fix: rewrite it at model level: `pytest.raises(ValidationError): CandidateState(notes=[{..., **bad}])` and a list of 9 notes, keeping the 3 parametrized cases. Optionally keep one API case: `NextTurnBody(..., state=...)` gives 422, which is already covered by test_http_bodies_forbid_old_fields.

M4. There is no end-to-end test for jd_profile going from /start to the checkpoint to the finalize `requirements` block.
- start_values serializes it (session_record.py:24). The only check is `jd_profile is None` in test_checkpoint_keeps_*.
- test_reporter.py:99 seeds it directly with seed_from_finalize_request. The golden finalize compare asserts `built.jd_profile is None`, so no scenario has a JD.
- Fix: add one test: /start with jd_profile, 1 next-turn, finalize, assert `"requirements" in report`.

M5. `elapsed_seconds` is the only remaining body field that drives state.
- It feeds the time budget (forced_transition / time_hard_limit). The client can send 0 forever, so the session never times out, or send non-monotonic values.
- The caller is the internal FSD behind X-Internal-Token, so the risk is limited.
- Fix (optional): reject or clamp values below the last stored elapsed. Store `elapsed_seconds` in last_turn or the transcript; the guard returns 409 or uses max(). The other fields (answer_source/stt_confidence) are bounded by MAX_REASKS, then 422.

M6. main.py is 339 lines. A split is worthwhile and fits the existing routers (matching/router.py, dev_play_page.py).
- `app/request_lifecycle_telemetry.py`: _usage_meta, _finish_request, _logged_failure, _TurnStream, _stream, MODEL (about 100 lines).
- `app/interview_session_routes.py` (APIRouter): /api/start, /api/next-turn, /api/finalize (about 110 lines). Optionally move the "open trace on early error" block into a helper `_trace_on_error(endpoint, body)`. It is duplicated at main.py:291-295 and 325-328.
- main.py keeps app, lifespan, error handlers, health, cv/jd parse, metrics, stt phrases, include_router (about 130 lines).

## Low
L1. On the early-error path (main.py:293), the trace input includes `body.answer` even for 404 unknown sessions and 409s. The answer goes to Langfuse with no session. Fix: drop `input` there. The answer is already in the trace on the normal path.
L2. FinalizeBody.end_reason is an unbounded str (models_interview_http.py:31) that is echoed into the report. Fix: add `Field(min_length=1, max_length=40)` or a Literal of the known reasons.
L3. seed_from_next_turn_request turns `TopicTurn.source=None` into answer_source (seed_session.py:44). This is equivalent in practice, but not literally the same request. Fine for a test helper.
L4. Doc 07: §8.8 sits between 8.7 and 8.4. Move it to the end. Doc 03 text is fine.
L5. The stale module docstring in the golden runner is fine. session_store/__init__ was updated. The record_start docstring is stale (see H1).

## Focus checklist
1. Rebuilt requests: equal to the old ones on all golden turns (question, turn_kind, topic_turns incl. source and reask, swaps/alt, session-ending turn, finalize turns incl. evaluation null). Exceptions: end_reason precedence (M1) and the untested jd_profile path (M4).
2. main.py ordering:
   - Lock always released: hold fails → release None; store error/404/409/replay → finally releases; prime error → runner.aclose → on_finish.
   - Finalize releases the lock right after reading.
   - request_done is logged on every error via _logged_failure.
   - Replay still works with the new keys. last_turn is checked before phase=done.
3. Phase-03 threads: silently wrong on next-turn, 500 on finalize (M2). Acceptable to ship because phase 03 was never deployed, but the cheap 404 guard is recommended.
4. Tests: the 4 reworked guard tests and test_finalize_requires_turns match the spec (404 / 409 session_no_turns, old fields give 422). No hidden assertion weakening apart from the vacuous notes test (M3).
5. Security: the state-injection path is closed (extra="forbid"). The remaining lever is elapsed_seconds (M5). PII note in L1.
6. Split proposal: see M6.
7. Docs 06/07 match the code except the finalize end_reason sentence (M1) and the /start failure behaviour (H1). dev-play.js and simulate_session.py send correct slim bodies. dev-play guards finalize when no turn was answered.
8. Plan TODO: "Chạy local dev-play text + voice" is still unchecked. The Postgres checkpoint size after phase 04 has not been measured.

## Unresolved questions
- Should /start fail (error event) when the checkpoint write fails, or should FSD rely on the 404 → restart path? This needs a DE decision, since the FSD contract changes.
- Is memory store allowed in staging now that it is the only copy of the session?
- Should finalize be rejected (409) when the stored state is not `done` and body.end_reason is missing or "plan_complete"? Today any session can be finalized mid-way and the session can still continue afterwards.
