# Code Review: 015 voice-mode, apps/voice-service (fc4f035..9c93028, 8 commits)

## Scope
- Worktree `C:/Users/NITRO/arp-voice-service`, branch `feat/voice-service/voice-mode`
- 47 files, +2741/-27: `apps/voice-service/**` (app 19 files, tests 14, evals 1), CI matrix, compose, .gitignore, ADR-011, ai-integration.md §10, services.md §7, tasks.md
- Read-only review. No code edits, no commits, no real Blaze calls, no `.env` reads
- Checked against: spec FR-003..024, contract, data-model, spike results (on branch docs/voice-mode-spec, research.md "Kết quả spike"), constitution

## Verification run
- Local env (fastapi 0.128 / starlette 0.50 / pydantic 2.12): 157 passed
- **Pinned stack** in a scratch venv (fastapi 0.115.6 / starlette 0.41.3 / pydantic 2.10.4, same as CI and Docker): **157 passed**. Starlette 0.41 uses `MultiPartParser.max_file_size`, and `keep_uploads_in_memory` sets it correctly. The rollover test is real (it patches `SpooledTemporaryFile.rollover`)
- Probe: a chunked multipart upload with no Content-Length, 3 MB, with `max_upload_mb=1`. It **rolls to disk** on both stacks, then returns 413
- Probe: client timestamps sent as epoch **seconds** (`1764079200`, `1764079205`). Result: gap 0.005 s, thinking_time 0.51 s, **no warning**
- Probe: one 0.2 s word gives 300 spm; "dạ vâng" spoken in 0.2 s gives 600 spm
- OpenAPI: `/transcribe` documents only 200. `/speak` and `/session-summary` advertise 422, but the code returns 400
- `docker compose config -q` passes. `env_file: {path, required}` needs Compose 2.24 or later, and this is the only service in the repo that uses that form
- Every file is under 200 lines (largest: test_blaze_client.py, 165)

## Overall
Good quality. The service is small, well commented and stateless, and it follows the spike shapes (string VAD times, `segments[].words[]`, no confidence field anywhere). Consent is checked before any provider call. Logs are content-free and a caplog test at DEBUG checks this. Tests run the full ASGI stack against an `httpx.MockTransport` that returns realistic payloads, so they test behavior, not mocks. The main gaps:
- STT retry semantics, which risk double billing and long latency
- FR-015 is still breachable with chunked bodies
- Silent misparse of epoch-second timestamps
- Swagger, contract, spec and data-model drift from the code
- Branch base and merge order

## Critical
None.

## High

**H1. STT is retried after read timeouts and 5xx: double billing plus a ~3 min tail.** Location: `app/blaze_client.py:83-105` (`_send`), called from `transcribe` at `:134`.
- `except httpx.TimeoutException` covers ReadTimeout and WriteTimeout. By then Blaze has received the upload and may be transcribing it, and the retry uploads and bills it again. 5xx from a gateway (502/504) after processing is retried the same way.
- HTTP timeout = provider_timeout_s + 5 = 65 s. With retries=2 the worst case is about 3 × 65 + 0.5 + 1 ≈ 197 s before the caller gets a 504. That is far beyond the revised SC-001 (≤ 20 s for ≤ 90 s answers) and longer than any sane caller timeout.
- Scenario: a network stall on a 60 s answer leads to 3 STT billings (about 3 × 1 min of credit) and a candidate waiting 3 minutes.
- Fix (KISS): add an `idempotent` flag to `_send`. For STT (and VAD, which is cheap but the same rule applies), retry only on `httpx.ConnectError`, `ConnectTimeout`, `PoolTimeout`, 429 (non-quota) and 503. Do not retry ReadTimeout, WriteTimeout, 500, 502 or 504; map them straight to 504/502. Separately, consider a lower STT HTTP timeout, derived from audio length (≈ 5 + 0.15 × dur + margin) or capped near 30 s. TTS can keep retrying, because nothing is billed before the first byte.
- Add a test: STT ReadTimeout gives exactly 1 request and a 504.

## Medium

**M1. FR-015 (MUST) breach: a chunked upload with no Content-Length spools audio to disk.** Location: `app/audio_validation.py:56-64`, `app/transcribe_route.py:66-67`.
- `reject_oversized_body` does nothing when the header is missing, and Starlette rolls the part to a temp file once it passes `max_upload_bytes + 64 KB`. This is confirmed on the pinned stack.
- The README admits it, but FR-015 is a MUST. The service is internal and token-gated, which lowers the risk but does not satisfy the MUST.
- Fix (one line): on `/api/voice/transcribe`, return `411 length_required` (or 413) when `Content-Length` is missing. Callers are server-side and always send it (fetch/axios/httpx with a buffered body). Alternative: a pure ASGI receive wrapper that counts bytes, which is more code.
- Add a test that sends a chunked body and expects 411 with no rollover. Must-fix or explicit owner waiver.

**M2. Epoch seconds are silently read as milliseconds, so thinking_time is wrong with no warning.** Location: `app/audio_validation.py:73-82`.
- Any number is divided by 1000. If a caller sends `Date.now()/1000` or a Python `time.time()`, both stamps become 1970 values. The gap shrinks 1000× (5 s becomes 0.005 s) and passes the 0..600 s check, so `thinking_time_s` is about equal to the first word's start, with no `invalid_client_timestamps` warning.
- Fix: a plausibility floor, for example treat a value < 1e12 ms (before 2001) or before 2020 as invalid (raise ValueError so the route adds the warning). Add the epoch-seconds case to `test_parse_client_time_rejects_garbage`.

**M3. Swagger does not match behavior (constitution: "Mỗi endpoint HTTP MUST có Swagger cập nhật").** Locations: `app/transcribe_route.py:63`, `app/speak_route.py:22`, `app/summary_route.py:11`.
- `/transcribe` lists only 200.
- `/speak` and `/session-summary` advertise 422, but the custom handler returns 400 `invalid_request`.
- No error schema; 401/402/413/415/429/502/503/504 are not listed.
- Fix: one shared `responses=` dict (`ErrorBody` model: error, message, details) with the contract codes per route, and `422` removed. FastAPI does not drop the auto 422 on its own. Remove it with `responses={422: ...}` overridden, or accept it and note it in the README.

**M4. The token check fails open if staging copies `.env.example` as-is.** Locations: `.env.example:13` (`APP_ENV=dev`), `docker-compose.yml:126-143` (publishes `8020:8020` on all interfaces, no `APP_ENV`), `app/security.py:25-36`.
- On the GCP VM, a `.env` with `BLAZE_API_KEY` set but `APP_ENV` left at `dev` and no token means anyone who reaches :8020 can burn Blaze credit. Fail-closed depends entirely on APP_ENV being set right. ai-service uses the same pattern, so this is consistent but inherited.
- Cheapest fix, either of:
  - (a) Compose: `ports: ['127.0.0.1:8020:8020']`. Other services reach it over `ai-recruit-network`; host access is for dev only.
  - (b) Fail closed when `blaze_api_key` is set, no token is set and `APP_ENV` is not `dev`/`test`, or at least log ERROR.
- Also add an `APP_ENV=staging` note to the 014 add-service checklist.

**M5. Docs and contract drift from the code (FR-020 / constitution III: same PR).** Exact list:
- Contract `contracts/voice-service-api.md`:
  - Header (l.3-5): "Mọi endpoint trừ GET /api/health" should be "trừ /api/health và /metrics". `/docs` and `/openapi.json` need the token when one is set.
  - Transcribe `segments` bullet: "đoạn có tiếng (VAD)" should say "đoạn liên tục theo mốc từ của STT, cắt tại quãng ngừng ≥ VOICE_LONG_PAUSE_S; STT không có `words` thì là đoạn VAD".
  - `provider.stt_ms`: nullable (null when `no_speech`).
  - `warnings`: add `empty_transcript`.
  - Transcribe errors: add `401 unauthorized`, `503 misconfigured`, and `411` if M1 is adopted. `413 audio_too_long` also covers "VAD speech end > VOICE_MAX_AUDIO_S".
  - Speak errors: add `400 invalid_request` (empty text, bad JSON), `401`, `503 provider_unconfigured | misconfigured`.
  - Session-summary: add `400 invalid_request` (invalid metric values, e.g. filler_ratio > 1).
- Spec `spec.md` FR-006 table: the 3 rows still use "đoạn có tiếng", so they no longer match the spike overrides:
  - Thời gian suy nghĩ: "+ mốc bắt đầu của từ đầu tiên"
  - Thời gian có tiếng: "độ dài − tổng quãng ngừng dài" (not "tổng độ dài các đoạn có tiếng")
  - Quãng ngừng dài: "khoảng trống giữa hai từ liền nhau"
  - Độ dài: "từ đầu tiên → từ cuối"
  - The docs branch (3816b67/a562f5d) only changed SC-001.
- Spec FR-012 says an empty list returns "không có dữ liệu voice"; the contract and code return `notes: []`. Align the spec text with the contract.
- `data-model.md`:
  - SpeechSegment "Nguồn: VAD" should be "mốc từ của STT, fallback VAD".
  - Env table: `VOICE_PROVIDER_TIMEOUT_S` says 30, the code has 60. `test_defaults_match_data_model_table` asserts 60, so the test name is false.
  - Missing vars: `VOICE_STT_REFINE`, `VOICE_TTS_SPEED`, `VOICE_TTS_STREAM_FORMAT`, `VOICE_PROVIDER_BACKOFF_S`, `VOICE_PARALLEL_PROVIDER_CALLS`, `VOICE_FILLERS`, `VOICE_RATE_SLOW_SPM`, `VOICE_RATE_FAST_SPM`, `VOICE_FILLER_NOTE_RATIO`, `VOICE_THINKING_NOTE_S`. The thresholds appear in prose but not in the table.
- `.env.example`: missing the same variables. FR-016 says ".env.example có tên biến", and the README points to it as the template.
- `docs/architecture/ai-integration.md:230`: the bare "contract §7.4" should link to `docs/ai-service/06-api-contract.md` §7.4.
- `apps/voice-service/README.md:43`: says defaults are in data-model.md, which is wrong until data-model is fixed.

**M6. Branch base and merge order.**
- Base fc4f035 is not on main. This branch's `specs/015-voice-mode/research.md` lacks "Kết quả spike", which the code comments cite ("spike 2026-11-25").
- `tasks.md` is edited on both branches: docs ticks T001-T003, feature ticks T004+ on the adjacent line, so git will likely conflict.
- Fix: merge `docs/voice-mode-spec` first (or rebase this branch onto it), resolve tasks.md, then open the PR. Otherwise the PR diff shows the spec commits as well, and reviewers cannot see the spike overrides the code implements.

## Low

- **L1** `app/blaze_client.py:136-137`: `_json_object` runs before the 202 check, so a 202 with a non-JSON or empty body becomes 502 `provider_error` instead of 504 `provider_timeout`. Check `response.status_code == 202` first.
- **L2** Billed-audio cap is weak. `_check_audio_length` (`transcribe_route.py:30-33`) uses the VAD speech end, not file duration, and 10 MB of webm/opus is about 40 min. Speech in the first seconds followed by 30 min of silence passes, and STT bills the whole file. It also uses `segments[-1].end` (sorted by start) rather than `max(end)`. Low because the caller is internal. Fix: `max(s.end for s in segments)`. A real duration cap would need container parsing (YAGNI for now); document it.
- **L3** `delivery_metrics.py:78`: very short answers give absurd rates (0.2 s single word → 300 spm; 2 tokens in 0.2 s → 600 spm), which skews the session median for "dạ"-only turns. Option: `speech_rate_spm=None` when speech_time < 1 s, or document it.
- **L4** `delivery_metrics.py:90`: `over_limit` compares the unrounded duration with the limit while the response shows a rounded duration (20.004 vs a 20 limit shows 20.0 with `over_limit=true`). Compare the rounded value.
- **L5** `api_error.py:52-57`: the generic handler logs only the type, but Starlette `ServerErrorMiddleware` re-raises, so uvicorn still logs the full traceback with the exception message. A pydantic ValidationError on `TranscriptionResult` would include `input_value` (possibly transcript text). This is unlikely, but the comment overstates the guarantee. Fix the comment, or catch inside the route and raise a plain ApiError.
- **L6** `blaze_errors.py:1-5,12`: the docstring says QUOTA_MARKERS "chỉnh sau spike", but the spike never saw an error body. Either leave the guess documented as unverified or update the comment. See Q1.
- **L7** `transcribe_form.py:96`: no per-keyword length cap. Each value can be up to Starlette's 1 MB `max_part_size`, and 100 of them are forwarded to Blaze. Cap at about 100 chars.
- **L8** `SummaryRequest.turns` is unbounded and `topic_id` has no length cap there (the transcribe form caps it at 200). Add `max_length` (for example 200 turns).
- **L9** Unexpected exceptions bypass `metrics_middleware`: ServerErrorMiddleware is outside the http middlewares, so 500s are not counted in `voice_requests_total`. This only matters if anyone alerts on it.
- **L10** `/metrics` is open. Acceptable: labels are endpoint, status and code only, with no content or session ids. It is only a concern combined with M4 (public port), where it reveals the `quota_exceeded` count. Fine once the port binds to 127.0.0.1.

## Edge cases checked (scout)
| Case | Result |
|---|---|
| No words, VAD speech | falls back to VAD spans (tested) |
| No timings at all | every metric null, `topic_id` kept (tested) |
| Single word, zero length | span end becomes start + 0.01, rate null (tested); short-but-nonzero gives a huge rate (L3) |
| Overlapping or unsorted words | sorted, merged on max end so far (unit tested on timings; **not** tested through `_word_timings` with multiple segments) |
| Reversed word (end < start) | end raised to start (`_finite_pair`), untested |
| Words as strings | float() coercion OK (untested for words; tested for VAD) |
| Punctuation tokens | stripped by `normalize`; only timings come from `words`, so punctuation never inflates the token count |
| Fillers "kiểu như", "nói chung là" | longest-first, no double count (tested); NFD input normalized (tested); trailing "ạ" not a filler (tested). Note: default "à" and "ừ" also catch the question particle and "yes", which is config-tunable |
| Pause exactly 2.0 s with float noise | `round(...,3) >= 2.0` counts it (tested) |
| Timestamps ISO "Z" / offset / naive (treated as UTC) / epoch ms | OK; epoch **seconds** silently wrong (M2) |
| One stamp missing, reversed, > 600 s | null plus a single deduped warning (tested) |
| Consent missing or non-"true" | 400 before any provider request (tested, 0 Blaze requests); checked before audio validation |
| TTS error before the first byte | JSON error; response closed (`_send` aread/aclose, `SpeechStream.open` aclose) |
| TTS client disconnect mid-stream | generator `finally` plus `BackgroundTask(aclose)`; httpx `aclose` is idempotent. OK, untested |
| Parallel mode, one call fails | first exception re-raised; STT credit is spent anyway (documented) |

## Positive observations
- Consent is enforced ahead of the parse/validate/provider chain. The neutral `audio.<ext>` filename avoids leaking user file names to Blaze.
- Provider error `message` is never copied into `details`, and there is a test for it.
- Config is an immutable dataclass with validation, fails fast on bad env, and tests never read `os.environ`.
- `transcript_tokens` is shared by the metrics and evals/wer.py (one normalization rule, DRY).
- Prometheus labels are bounded (unknown routes are bucketed as "other").
- The spool-threshold fix handles both starlette attribute names, and a real rollover test backs it.
- ADR-011 is concise and accurate, records the constitution VII deviation explicitly, and fits the ADR numbering (009 is reserved, 010 exists).

## YAGNI / KISS
- `VOICE_PARALLEL_PROVIDER_CALLS`: the spike chose sequential, parallel mode wastes credit on silence, and it needs its own path, 2 tests and a README caveat. Candidate for removal.
- `VOICE_TTS_SPEED` and `VOICE_TTS_STREAM_FORMAT`: parameters the spike did not verify. Remove them until needed.
- The VAD fallback when there are no words exists only for `blaze-stt-1.0`, which is not the default. It is one line, so keep it.
- Everything else is proportionate for a 12-day Stretch feature.

## Tests (behavior vs mocks)
These are behavior tests: the full app, real multipart, and MockTransport with spike-shaped payloads, asserting on request counts, logs and spool rollover. Missing:
1. STT ReadTimeout gives no retry and one request (after H1)
2. A chunked body with no Content-Length (after M1)
3. Epoch-seconds timestamps flagged invalid (after M2)
4. `_word_timings` with words spread across several segments, string times, unsorted order, end < start
5. 202 with a non-JSON body (L1)
6. TTS mid-stream error or disconnect closes the upstream response
7. A Swagger test that `/speak` does not advertise 422 (after M3)

## Metrics
- Type coverage: full type hints on public functions; no mypy in CI
- Tests: 157 pass on local and pinned stacks; coverage not measured (no pytest-cov)
- Lint: no linter configured for Python in CI; no syntax issues

## Verdict
**Ready after fixes.** No blocker on the pinned stack.

## Prioritized fix list
1. H1: STT retries only on connect-level errors, 429 and 503; no retry on read timeout or 5xx; lower the STT timeout; add a test
2. M1: reject a missing Content-Length on `/transcribe` (411), or get an explicit owner waiver of FR-015 for chunked bodies
3. M6: merge or rebase onto `docs/voice-mode-spec` before opening the PR; resolve tasks.md
4. M5: update the contract, spec FR-006/FR-012, data-model (env table, timeout 60, SpeechSegment source), `.env.example` and the ai-integration §7.4 link in the same PR
5. M2: plausibility floor for epoch-ms timestamps
6. M3: OpenAPI error responses, and stop advertising 422
7. M4: bind compose to `127.0.0.1:8020`, or harden fail-closed; staging checklist sets `APP_ENV`
8. Low items L1, L2 (`max(end)`), L3, L4, L7 as time allows; drop the parallel-mode, speed and stream_format options (YAGNI)

## Unresolved questions
1. Quota vs rate-limit: what are Blaze's real 429/402 error bodies? QUOTA_MARKERS is still a guess. A deliberate test with a low-credit key is impossible without spending credit, so ask Blaze support or the docs.
2. Does Blaze bill an STT request that ends in 202 (`timeout` exceeded) or in a client-side disconnect? This decides how strict H1 must be.
3. Which PR order does the owner want: docs/voice-mode-spec first, or one combined PR? Also, does the PR target main directly?
4. Is FR-015 allowed to tolerate the chunked-body case (owner waiver), or must it be enforced?
5. Will staging compose publish 8020, or will only interview-service reach it over the network? This decides M4's severity.
