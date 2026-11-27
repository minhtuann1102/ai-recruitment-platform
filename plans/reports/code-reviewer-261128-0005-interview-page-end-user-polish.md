# Code Review: interview page end-user polish (/dev/interview)

## Scope
- Files: app/static/interview/{interview.html, interview.css, interview-api.js, interview-chat.js, interview-voice.js, interview-turn.js, interview-report.js, interview-result.js, interview-app.js}, app/dev_interview_page.py (~1.1k LOC)
- Focus: uncommitted end-user polish on feat/ai-service/dev-interview-voice-page. Proxy and security were covered by the earlier review (code-reviewer-261127-2231).
- Tests: 17 pass (not rerun). The stop-intent regex was checked in node against 16 sample sentences.

## Overall
The structure is clean and escaping is mostly right. Bubbles use textContent everywhere, and the report renderer wraps every API string in esc(). friendlyError maps the codes it should.
- One real race (H1): ending the session while STT is in flight lets an auto-submitted turn run after finalize.
- The stop-intent modal opens a hole in the M1 invariant (M1 below).
- The regex has many false positives on short technical answers.
- Nothing else blocks a dev-only page.

## Earlier fixes M1–M4
| Fix | Status |
|---|---|
| M1 stale STT dropped via V.recTurn + S.pending | Holds on the normal path. **Has a hole on the stop-intent path** (see M1 below). |
| M2 sendAnswer guarded by sendBtn disabled/hidden | Holds. |
| M3 replay disabled while recording | Holds: setRecorderState disables replayBtn, and speakQuestion returns early if V.recorder is set. |
| M4 non-retryable errors not stuck on retry | Holds. The only in-stream SSE error is AI_SERVICE_ERROR (main.py:225), which can be retried. |

## High

### H1. Ending during STT (or recording) lets a ghost turn run after finalize
- `setRecorderState("busy")` never disables `endBtn`, and `onRecorded` never calls setBusy.
- Repro:
  1. Record, then stop.
  2. Click "Kết thúc & xem đánh giá" while "Đang chuyển giọng nói thành chữ…" is showing.
  3. STT returns. `stale()` is false (same turn, no pending), so `submitTurn` → `runNextTurn` posts /api/next-turn behind the modal.
  4. Confirm. `finalizeSession` sends /api/finalize with S.turns that does not include this turn.
- When next-turn finishes:
  - it pushes into S.turns after finalize was sent;
  - `showQuestion` runs, and `speakQuestion` plays TTS for a new question on the result screen;
  - if `session_end` comes back, a second `finalizeSession` re-renders the report.
- Same path when the user confirms End and the STT result arrives after `abortRecording` already ran. abortRecording only covers a live recorder, not an upload in flight.
- `finalizeSession` also never closes a modal that is still open.
- Fix:
  - Set `S.ended = true` first thing in finalizeSession.
  - Add `|| S.ended` to `stale()` in onRecorded.
  - Bail out in `runNextTurn` after the await (`if (S.ended) return;`), and in `showQuestion` / `speakQuestion`.
  - Disable `endBtn` in `setRecorderState` when the state is not idle (or at least while busy).

## Medium

### M1. Stop-intent modal: controls are live underneath, no focus trap, nested askConfirm leaks
- **Controls live under the modal.** When the voice transcript matches STOP_INTENT, `await askConfirm` runs before `S.pending` is set. onRecorded's `finally` then sees not-stale and calls `setRecorderState("idle")`, so mic, replay and type buttons are enabled under the modal. The typed path is similar: sendBtn stays enabled.
- **No focus trap.** The backdrop blocks the mouse, but nothing stops keyboard focus leaving the dialog. Shift+Tab reaches micBtn, endBtn and the textarea, so a user can start a second recording, press Ctrl+Enter, or open a second modal.
- **Nested askConfirm.** A second call overwrites the onclick handlers but leaves the first promise's document `keydown` listener attached.
  - Click Cancel on the second modal: the first promise stays pending with an orphaned Esc listener.
  - A later Esc (even on the result screen) resolves it false, and submitTurn then sends that old answer as a turn.
- Fix:
  - Use a native `<dialog>` with `showModal()`. It makes the background inert, traps focus, handles Esc, and returns focus on close.
  - Add a reentrancy guard (reject or return the pending promise if one is open).
  - Call `setBusy(true)` before the await in submitTurn and restore it on cancel.

### M2. STOP_INTENT false positives and negatives; default focus is the destructive button
- Node run against the regex:
  - **All 9 technical sentences matched**, e.g. "timer dừng ngay", "Thread sẽ ngừng ngay…", "Vòng lặp kết thúc ngay…", "Khi user muốn dừng download…", "Cho dừng container bằng docker stop", "Nếu không muốn tiếp tục nữa thì return", "kết thúc điều kiện…".
  - Causes:
    - the `ngay` alternative;
    - `(muốn|cho) (dừng|kết thúc)` with no object;
    - `không muốn tiếp tục nữa`;
    - `đi\b`: JS `\b` is ASCII-only, so "đi" followed by "ều" counts as a word boundary.
  - The 160-character cap does not help, because technical answers are often short.
- **Missed** real stop phrases: "Dừng lại", "Em xin dừng ở đây", "Thôi, em không biết" (the last one is arguably a skip, not a stop).
- A false positive costs one extra modal, but `$("confirmOk").focus()` puts focus on "Kết thúc & xem đánh giá". A typed-path user who presses Enter right after Ctrl+Enter ends the session for good.
- Fix:
  - For the auto-detected modal, focus Cancel by default.
  - Require an interview object ("phỏng vấn" or "buổi"), or anchor the whole short utterance, e.g. `^\s*(em|tôi|mình)?\s*(xin )?(dừng|kết thúc|thôi)( lại| ở đây| phỏng vấn| buổi.*)?[.!]?\s*$` with a length of 50 characters or less.
  - Drop the bare `ngay` and the object-less `(muốn|cho) …` alternatives.

## Low

### L1. Report render failure is silent
- In finalizeSession, `setResult("…Đánh giá chi tiết ở bên dưới.")` runs before `renderReport`.
- If renderReport throws, the result is an unhandled rejection and an empty report under "details below".
- Possible throw points:
  - `x.point.replace`, `o.score`;
  - in renderVoiceSummary: `Object.entries(r.stats)`, `r.notes.length`.
- The fields are built in code (report_scoring.py:109-114), so this is Low.
- Fix: wrap the render calls in try/catch with a fallback message, and set the status text after the render succeeds.

### L2. Defence-in-depth escaping gaps (all sources trusted today)
- `href="${esc(s.url)}"`: esc() does not block `javascript:`. URLs come from catalog sources (report_resources.py), so the risk is low. Allow only `^https?://`.
- `dev_interview_page.py:39` puts `json.dumps(tracks)` inside `<script>` without escaping `<`, so a catalog title containing `</script>` would break out. Fix: `.replace("<", "\\u003c")`.
- `${s.n}` in renderVoiceSummary is not escaped (the value comes from voice-service). Wrap it in esc() or num().

### L3. Modal accessibility
- No `aria-describedby="confirmText"`.
- Focus is not returned to the opener on close.
- No focus trap (see M1).
- All three are solved by `<dialog>.showModal()`.

### L4. Polish
- When voice is not ready, typing mode opens automatically, yet speakQuestion still says "bấm 'Gõ thay vì nói'".
- With the mic denied but the voice service up, TTS `onended` shows "Bấm micro để trả lời" although there is no mic.
- `scrollChatEnd()` runs on every SSE token and pulls the user back down if they scroll up to reread.
- `aria-live="polite"` on #chatLog together with token streaming makes screen readers announce every chunk. Consider setting aria-busy while streaming, or announcing only the final text.
- finalizeRetryBtn is not disabled while a request is in flight, so a double-click sends two /api/finalize calls.

## Positive
- Bubbles, the modal text and the status lines all use textContent, never innerHTML with data.
- The report renderer calls esc() on every API string, and links use rel=noopener.
- dev_interview_page serves files from an allowlist only (no path traversal), and the page stays behind ensure_dev().
- The token is taken only from the URL and is never rendered.
- friendlyError hides internal detail but keeps the Vietnamese 4xx messages.
- Every error path checked ends in an actionable state (retry, re-answer, or typing). None leaves the UI stuck, apart from the H1 and M1 races.
- Files stay under 200 lines and the module split is clear.

## Recommended actions (ordered)
1. H1: add an S.ended guard in stale(), runNextTurn, showQuestion and speakQuestion, and disable endBtn while the recorder is busy.
2. M1: switch to `<dialog>.showModal()`, add a reentrancy guard, and set busy before the stop-intent await.
3. M2: tighten STOP_INTENT and focus Cancel on the auto-detected modal.
4. L1: try/catch around report rendering.
5. L2 and L3: url scheme allowlist, `<` escaping in __TRACKS__, aria-describedby.

## Metrics
- Type coverage: n/a (plain JS)
- Tests: 17 pass (reported). No JS unit tests for the race paths.
- Lint: not run (no JS linter configured for static/)

## Unresolved questions
1. On the auto-detected stop modal, Esc and backdrop click mean "send as answer" today. Should they instead go back without sending, so there are three choices: End / Send as answer / Re-answer?
2. Should "Gõ thay vì nói" persist across turns? showQuestion resets to voice mode every turn.
3. Should a voice failure in the middle of a session switch to typing automatically? V.svcOk is only set on the permission screen.
