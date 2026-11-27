# Dev interview page (AI + Voice, local)

Branch `feat/ai-service/dev-interview-voice-page` (from origin/main 8665da9). Status: implemented, reviewed (plans/reports/code-reviewer-261127-2231-dev-interview-voice-page.md, M1-M4 + L1/L2 fixed), not committed.

## Goal
Local-only page to test the full ai-service interview loop with real voice-service (Blaze STT/TTS), UI after
Figma community file "AI Video Interview App" (Ads4X79Jw8rapNzYfYo69I, page "04 __ Design").

## Placement
`GET /dev/interview` in ai-service, next to `/dev/play`. Same gate: 404 when `APP_ENV` staging/production.
Vanilla HTML/CSS/JS (no build). Reuse `dev-play-api.js` (POST/SSE + token), `dev-play-trace.js`, `dev-play-report.js`.

## Screens (Figma frame → page)
| Figma | Page screen | Data |
|---|---|---|
| 10:45 Fill the Basic Details | setup | track, level, duration, CV file, JD text, token |
| 10:61 Permission Screen | mic + consent, voice-service health | getUserMedia(audio), GET /dev/voice/health |
| 10:69 Audio Question | question loop | /api/start, /api/next-turn (SSE), TTS, record, STT |
| 10:125 Result Screen | result + report | /api/finalize, /dev/voice/session-summary |
Skipped: welcome, tutorial, instruction, connection check, MCQ, video, coding.
Branding: "happierwork" logo, avatar photo, contact email, webcam preview NOT copied (project wordmark, initials).

## Voice proxy (browser cannot call voice-service: no CORS, server token)
`app/dev_voice_proxy.py`: `/dev/voice/{health,transcribe,speak,session-summary}` → `VOICE_SERVICE_URL`
(default `http://localhost:8020`), adds `VOICE_SERVICE_INTERNAL_TOKEN` from server env. Body forwarded as bytes
(Content-Length set, no chunked). Proxy paths stay behind `X-Internal-Token` (Blaze is billed); page assets open.
Voice turn: transcript → `/api/next-turn` with `answer_source=voice`, no `stt_confidence` (Blaze has none; null skips gate).

## Files
- create `app/dev_interview_page.py`, `app/dev_voice_proxy.py`, `app/static/interview/*` (html, css, 3 js, svg assets)
- modify `app/main.py` (routers), `app/security.py` (open page paths), `requirements.txt` (httpx pinned, used directly)
- create `tests/test_dev_interview_page.py`

## Done when
pytest green; page loads; manual run: start → voice turn → finalize with both services up (or note what was not run).

## Verification (2026-11-27)
- tests/test_dev_interview_page.py 13 pass, test_dev_play_page 4 pass; full suite: 7 failures pre-existing on main (Windows: turn_graph disconnect, session_store_concurrency, grounding socket, golden_turns read_text w/o utf-8)
- E2E puppeteer (fake mic = TTS mp3): setup -> permission -> Q1 -> record -> Blaze STT transcript -> next-turn -> finalize + session-summary, no console/HTTP errors

## Change 2026-11-27 23:15 (user request)
- Question screen = chat: AI bubbles left, candidate bubbles right, read-only (textContent, no edit). Stop recording →
  STT → transcript bubble → auto-send to /api/next-turn. Typing only via "Gõ thay vì nói" (new message, not an edit).
- Track select has no default (was ai_engineer by list order → ML questions for a software candidate).
- E2E rerun after change: ok, no console/HTTP errors.

## Change 2026-11-28 (user: treat as end-user screen, no dev output)
- Removed dev trace drawer, token field (now `?token=`), JSON download, raw JSON, dev-play JS deps; Vietnamese
  user copy + friendlyError (interview-api.js); report screen rebuilt (interview-report.js); track titles.
- Hard stop: "Kết thúc & xem đánh giá" always enabled; `S.ended` drops late STT / next-turn results (no extra turn).
- Stop intent (spoken/typed) -> native `<dialog>` confirm, focus on cancel; regex needs "phỏng vấn" object or a
  whole-utterance stop ("Dừng lại"); 24 sample sentences classified right (no hit on "timer dừng ngay").
- Typing choice kept across turns; voice-service failure mid-session -> switch to typing.
- Review: plans/reports/code-reviewer-261128-0005-interview-page-end-user-polish.md (H1, M1, M2, L1–L4 fixed).
- Verified: 17 tests pass; E2E voice turn -> typed stop phrase -> cancel (sent as answer) -> voice turn -> End during
  STT -> 2 next-turn requests, 2 turns, report rendered, no console/HTTP errors.

## Change 2026-11-28 (pulled main #117–#119, slim session API)
- Fast-forwarded to origin/main 91ef5e5; resolved main.py import + specs/README.md row conflicts (both rows "018":
  Thắng langgraph-session-memory vs DE cv-jd-matching-comparison — numbering clash, tell team).
- Page now sends next-turn {session_id, turn_number, answer, elapsed_seconds, answer_source} and finalize
  {session_id, end_reason, duration_s}; session_not_found -> friendly reload message.
- Tests: 30 failures identical on clean main (Windows); 6 more only when real .env agentic flags leak into tests.
  E2E on new main ok (fallbacks=-, no 4xx).

## Unresolved
- ai-service local on Windows: fixed via scripts/run_local.py (selector loop); OpenAI key revoked -> OpenRouter
- Question bank picks Node/Python items for java_backend topics (DE data)
- Stop intent + coherence criterion belong in ai-service Evaluator (AIE); page-side regex is a stopgap
- /api/stt/phrases gives 232 terms > VOICE_MAX_KEYWORDS 100 -> keywords_truncated every turn
- staging APP_ENV must be staging/production or /dev/* is live there
- Blaze bills whole file: keep test answers short; auto-stop recording at 180 s.
