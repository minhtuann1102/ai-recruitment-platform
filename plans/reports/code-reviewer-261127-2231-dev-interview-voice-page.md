# Code Review: dev /dev/interview voice page + /dev/voice proxy

## Scope
- Files: app/dev_interview_page.py (42), app/dev_voice_proxy.py (108), app/security.py, app/main.py, app/dev_play_page.py (rename), requirements.txt, static/interview/{interview.html, .css, interview-app.js 105, interview-turn.js 130, interview-voice.js 173, interview-result.js 76}, assets/*.svg, tests/test_dev_interview_page.py
- LOC: ~950 new
- Focus: uncommitted diff on feat/ai-service/dev-interview-voice-page
- Tests: `pytest tests/test_dev_interview_page.py tests/test_dev_play_page.py` -> 14 passed
- Plan: plans/261127-2231-dev-interview-voice-page/plan.md has no TODO checklist, so there was nothing to tick. Left unedited.

## Overall
Solid, small, well-commented. The open-path rule and the file whitelist are safe, and /dev/play and API auth are unaffected. There are no Critical issues. The findings are browser-flow state bugs plus proxy robustness, all Medium or lower.

## Security: open path + whitelist (verified OK)
- `is_open_path` opens `/dev/interview` and `/dev/interview/*` only. `/dev/interviewX` stays closed, and `/dev/voice/*` stays token-protected, health included.
- Traversal: Starlette routes on the decoded `scope.path` without normalizing `..`. `/dev/interview/../api/start` (or `%2F`) is therefore routed to `dev_interview_file` with `name="../api/start"`, misses the `FILES` dict, and returns 404. It cannot reach `/api/*`, and the existing test covers `..%2F`.
- Strict env: both handlers call `ensure_dev()`, so they return 404 even when the token is unset (the middleware passes open paths, then the route 404s). The voice proxy returns 404 too.
- Router order is correct: dev_play's `/dev/{name}` would otherwise catch `/dev/interview`. `/dev/voice/x` and `/dev/interview/assets/x` contain a slash, so `{name}` does not match them.
- No `script` or `on*` handlers were found in the SVGs.

## High
None.

## Medium

### M1. Transcription result not bound to its question (stale transcript and Ctrl+Enter bypass)
- `onRecorded` (interview-voice.js:120) awaits `transcribe()` with no guard tying the result to the question. If the turn moves on, or the session ends, during the 2-30 s STT call, the result still sets `V.heard` and fills `#answer` on the NEXT question. That answer is then sent as `answer_source: "voice"` with the wrong metrics.
- How the turn can move during STT: `setRecorderState("busy")` disables only mic and send. `#answer` keydown Ctrl+Enter (interview-app.js:105) calls `sendAnswer()` regardless of `sendBtn.disabled`. `V.recorder` is already null, so its guard passes. This requires clicking typeBtn first, because `#answer` is hidden until then.
- Same bypass in the retry state (interview-turn.js:299): sendBtn is disabled to force "Gửi lại", but Ctrl+Enter rebuilds `S.pending`. If the user edited the answer and the server had already completed the turn, the result is 409 `turn_already_answered`, and that error then loops in the retry state (see M2).
- Fix:
  ```js
  // toggleRecording
  V.recTurn = S.turn.turn_number;
  // onRecorded, after await
  if (S.turn?.turn_number !== V.recTurn || !$("screenQuestion").offsetParent) return;
  // sendAnswer, first line
  if ($("sendBtn").disabled) return;
  ```

### M2. Non-retryable next-turn errors leave the page stuck in "Gửi lại"
- In `runNextTurn`'s catch (interview-turn.js:295), every error whose code does not start with `voice_` keeps `S.pending`, disables send and mic, and shows retry. Retry resends the identical body, so deterministic failures can never succeed:
  - 422 `invalid_request` (for example, a typed answer over 4000 chars, models_interview.py:122)
  - 409 `turn_already_answered` or `session_invalid_state`
  - 401 from a wrong token (the token input is on the setup screen, which is no longer reachable)
- The only exit is "Kết thúc buổi".
- Fix: offer retry only when there is no `err.code` (network or SSE-stream error), on 5xx, on 503 `session_store_unavailable` and on 409 `turn_in_progress`. Otherwise set `S.pending = null`, re-enable send and mic, and show the message.

### M3. Replay button is live while recording
- `replayBtn` is not touched by `setRecorderState`. Clicking it mid-recording calls `speakQuestion`, which sets `V.questionEndedAt = null` and later sets it to the TTS end. That makes it later than `recStartedAt`.
- Per the contract, voice-service then returns the `invalid_client_timestamps` warning and a null `thinking_time_s`, so the metric is lost.
- The TTS audio also plays into the open mic (echoCancellation only partly helps).
- No crash.
- Fix: disable `replayBtn` (and arguably `typeBtn`) in `setRecorderState` when state is not `idle`.

### M4. voice_speak can leak the httpx client/connection (dev_voice_proxy.py:128-150)
- Starlette 0.41.3 `StreamingResponse.__call__`:
  - On a client disconnect, the cancel scope ends the task group normally and the background `close()` runs. That case is fine.
  - If `upstream.aiter_bytes()` raises mid-stream (httpx `ReadError`/`RemoteProtocolError`/`ReadTimeout`), the exception escapes the task group, the background never runs, and `AsyncClient` plus the upstream response leak until GC.
- Also, on the non-200 path, `await upstream.aread()` is unguarded. A read error there leaks the client and becomes a bare 500.
- Fix:
  ```python
  async def body():
      try:
          async for chunk in upstream.aiter_bytes():
              yield chunk
      finally:
          await close()
  return StreamingResponse(body(), media_type="audio/mpeg")
  ```
  Wrap the error branch in `try/finally: await close()`.

## Low-Medium

### L1. Cross-origin "simple" requests can spend Blaze credit when the ai-service token is unset (dev default)
- `.env.example` ships `AI_SERVICE_INTERNAL_TOKEN=` empty.
- `/dev/voice/speak` and `/session-summary` relabel any incoming body as `application/json`, so a `text/plain` POST from any page (no preflight) is forwarded as valid JSON. `no-cors` multipart to `/transcribe` is also a CORS-safelisted request.
- When the token is unset, a malicious page in the dev's browser can drive billed TTS/STT on localhost:8000. The same exposure already exists for /api/* (LLM cost) in dev, and Chrome's local-network-access rules partly mitigate it.
- Fix (cheap): reject `Sec-Fetch-Site: cross-site` on `/dev/voice/*`, and require incoming `Content-Type: application/json` on speak/summary.

### L2. Timeout mislabelled as "unreachable"
- `_forward` and `voice_speak` map every `httpx.HTTPError`, `ReadTimeout` included, to 502 `voice_service_unreachable`, with a message saying voice-service on port 8020 is not running.
- After a read timeout, Blaze may already have billed the call (the contract avoids retrying after read timeout for this reason), and the message invites a re-record.
- Fix: catch `httpx.TimeoutException` first and return 504 `voice_service_timeout`.

## Low
- `_read_limited`: `int(declared)` raises `ValueError`, giving a 500 on a malformed Content-Length. uvicorn usually rejects these first, but wrapping in try and returning 400 is cheap. speak/session-summary bodies are unbounded (behind the token and dev-only, so acceptable).
- Error passthrough drops upstream headers such as `Retry-After` on 429. Upstream 401 (bad `VOICE_SERVICE_INTERNAL_TOKEN`) looks identical to ai-service's own 401 on the page. Consider mapping upstream 401 to 502 `voice_service_auth`.
- `speakQuestion` waits for `resp.blob()` before playing, so the proxy streaming brings no latency gain (the docstring says the browser plays the first chunk immediately). Either use MediaSource, or fix the comment.
- `is_open_path` opens the whole `/dev/interview/` prefix. Any future route placed under it would be unauthenticated. Add a comment or test pinning that only `dev_interview_file` lives there.
- SVGs and CSS are served without `X-Content-Type-Options: nosniff`. Fine for dev.
- `finalizeSession`: on finalize retry, `duration_s` is recomputed from `Date.now()`, so it grows by the time spent on the result screen. Freeze `S.endedAt` on the first call. A voice summary failure is silent (only shown in the trace).
- Mic `MediaStream` tracks, `AudioContext` and the level `setInterval` are never stopped after finalize, so the browser mic indicator stays on until reload.
- The 180 s auto-stop calls `V.recorder?.stop()` every 500 ms until `onstop` fires. That is harmless in current browsers.
- `new MediaRecorder(...)` in `toggleRecording` is not in a try. An exception would leave the UI without a status message.

## Edge cases checked (OK)
- TTS fetch vs record race: the `speakSeq` guard is correct, and `stopSpeaking` sets `questionEndedAt` before `recStartedAt`, so normal timestamps are ordered and in epoch ms per the contract.
- 422 `voice_no_speech` is raised before the stream (HTTP JSON), so `apiError` carries `.code` and `voiceRejected` clears `answer`/`V.heard`. `voice_unclear`/reask are unreachable because the page never sends `stt_confidence`.
- A retry after the server completed the turn sends the same answer and answer_source, so it is replayed by `session_turn_guard`.
- Finalize with 0 turns shows a message and skips both calls. Summary with `turns: []` is accepted by voice-service (`max_length=200` only).
- Transcribe forwards the raw bytes and the boundary Content-Type. httpx sets Content-Length (no chunked), which matches the contract's 411 rule. The 11 MB cap is above `VOICE_MAX_UPLOAD_MB` plus 64 KB.
- The `ensure_dev` rename has no remaining `_ensure_dev` references. httpx 0.28.1 is pinned and matches requirements-dev and the installed version.
- XSS: question/meta use `textContent`, and the voice summary uses `esc()`.

## Positive
- Whitelist by dict key, built from a glob at import time, so there is no filesystem path handling of user input.
- The server-side token is never exposed to the browser, and the proxy stays behind the ai-service token.
- Tests cover the open/protected split, strict-env 404 with no upstream call, the size limit before forwarding, the Content-Length plus token forwarding, and 502.

## Recommended actions (priority)
1. M1: guard `onRecorded` by turn_number and make `sendAnswer` respect `sendBtn.disabled`.
2. M2: offer retry only for retryable errors.
3. M3: disable replayBtn while recording or transcribing.
4. M4: close in the generator's `finally`, and guard `aread`.
5. L1/L2: add the `Sec-Fetch-Site` check and map timeouts to 504.

## Metrics
- Tests: 14/14 pass (target files). No JS tests.
- Lint/type: not run (no configured linter for static JS).

## Unresolved questions
- How will staging (014) set `APP_ENV`? No tracked compose or workflow sets it. If it falls back to the default `dev`, then `/dev/interview` and the billed `/dev/voice/*` proxy are live there behind only the internal token. The gate is pre-existing, but this change increases what is exposed if it is missing.
- Should a transcript the user edited heavily still count as `answer_source: voice`? `voiceFields` marks any answer as voice once `V.heard` is set, and that answer then goes through STT term normalization.
