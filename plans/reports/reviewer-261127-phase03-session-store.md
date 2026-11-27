# Review: phase 03 session store (uncommitted, branch thang/langgraph-session-store)

## Scope
- Files: app/main.py, app/turn_graph/{builder,nodes,runner}.py, app/turn_result.py, app/session_store/* (5 files),
  scripts/setup_session_checkpoint_tables.py, tests (guard, concurrency, settings, helpers, integration, conftest).
- ~300 LOC new + ~140 LOC changed. Focus: lock release, cancellation, durability="exit", replay, growth, PII.
- Ran: `pytest tests/test_session_store_{guard,concurrency,settings}.py tests/test_turn_graph.py` -> 32 passed.
- I also ran temporary probe tests (since deleted). Results:
  - 5x 422 voice_no_speech on one thread: each attempt wrote its own checkpoint (6 total) and left an ApiError pending write.
  - A replayed reask turn sent the same `meta` and `done` as the original.
  - When `record_start` fails, /start sends the whole question and then `error`.
  - When the `record` node fails, the stream sends tokens and then `error`. A retry runs the turn fresh.
- LangGraph source checked (1.0.1 / checkpoint-postgres 3.0.5): `_loop.py` _first / _suppress_interrupt / __aexit__,
  `_executor.py` AsyncBackgroundExecutor, `checkpoint/postgres/aio.py` _cursor.

## Overall
Solid. Lock release is correct on every path asked about: prime failure, disconnect before or after the first event,
task cancelled before it starts, replay, and guard 409/503. `release` is single-shot, so a late call cannot free a
newer holder's lock. `input={}` always starts a fresh run from START (is_resuming is False because input is not None
and no run_id is in metadata). It discards the unfinished tasks of a mid-`ask` checkpoint. Persistent channels are
written only by `record`, so a cut run can never leave a half-updated checkpoint. A failed exit write is re-raised
(the executor uses reraise_on_exit), so the client never gets `done` while the checkpoint is behind. Replay of reask
and session_end turns is correct. The main risks are DB-outage behaviour, the memory default in prod, and the guard
enforcing rules during what is meant to be a shadow phase.

## High

### H1. One DB stall serializes every session. 503 only arrives after 30 s multiplied by the queue length
- Where: `session_checkpointer.py:39` (pool built with the default `timeout=30`) and `session_turn_guard.py:23` (no timeout).
- Cause: `AsyncPostgresSaver._cursor` (aio.py:363) does `async with self.lock, get_connection(pool)`. The saver
  instance has ONE `asyncio.Lock`, and it is held while waiting for a pool connection. Every aget_state, exit
  `aput`/`aput_writes`, `adelete_thread` and `aupdate_state` of every session therefore queues behind that one lock.
  `pool_max=10` buys no concurrency.
- Failure: the DB is unreachable, or the pooler is saturated. With `open(wait=False)`, the first `getconn` waits 30 s
  (PoolTimeout) while holding the saver lock. K concurrent /next-turn calls get their 503 after up to K x 30 s, and
  each holds its session turn lock all that time.
  - Streams whose question already finished also block at the exit write before `done` (the user sees the full
    question, then a hang, then `error`).
  - /start hangs after the question in the same way.
  - The "503 session_store_unavailable, retryable" design only works if the failure is fast.
- Fix:
  - Set `AsyncConnectionPool(..., timeout=2-3)`.
  - Wrap `graph.aget_state` in `asyncio.wait_for(…, SESSION_DB_TIMEOUT_S)`, and wrap `record_start` too.
  - Optionally set a server `statement_timeout` (via `options`, if the pooler allows it).
  - Document that throughput is bounded by the single saver lock (it is a LangGraph limitation). If it matters,
    use several saver instances or shard by session hash.

### H2. `SESSION_STORE=memory` is the default in staging/production: unbounded RAM growth holding PII
- Where: `session_store_settings.py:34`, `session_checkpointer.py:16`.
- Cause: InMemorySaver keeps every checkpoint of every thread, plus every blob version and every write, for the
  process lifetime. Nothing deletes a thread, not even session_end or finalize.
  - Measured on Postgres: about 245 KB per 17-turn session. The transcript is re-stored in full each turn, which is
    O(N^2).
  - Every rejected attempt adds another checkpoint (see M4).
  - Previously ai-service was stateless. A deploy that does not set SESSION_STORE now slowly leaks memory (about
    2.5 GB per 10k sessions) and keeps candidate answers in RAM indefinitely.
  - `check_agent_config` fails closed for LLM config in staging/prod, but nothing equivalent covers the store.
- Fix: when APP_ENV is staging/production, require SESSION_STORE to be set explicitly (raise ConfigError at startup).
  And/or for memory: call `adelete_thread` at session_end and finalize, and cap the thread count (LRU).

## Medium

### M1. The guard enforces 409s in the shadow phase; a checkpoint ahead of the client locks the session permanently
- Where: `session_turn_guard.py:58-62`.
- Scenario: the pump runs ahead of the consumer, so `record` plus the exit write can commit before `done` reaches
  interview-service. Examples: the connection drops during the last buffered tokens; interview-service crashes or
  fails to persist after receiving `done`; `_stream` raises after the events.
  - If the turn is resent with the SAME answer, it replays. Good.
  - If it is resent with a different answer (voice re-recorded so STT gives different text, or the UI lets the
    candidate re-type after an error), it gets `409 turn_already_answered` forever.
  - The only escape is /start, which resets the whole session. The request state is still the source of truth in
    this phase and would have computed correctly. Before phase 03 this case worked.
  - `test_interview_flow.py:107` had to change for exactly this reason.
- Fix (pick one, then confirm with the interview-service owner):
  - (a) While in shadow mode, downgrade turn_already_answered and turn_out_of_order to log-only when the request is
    self-consistent: run from the request and overwrite. Enforce in phase 04.
  - (b) Keep the 409 but put the stored `answer`/`done` in `details` and make interview-service adopt it.
  - (c) At minimum, document in 06-api-contract that a retry MUST resend the identical answer and answer_source.

### M2. A failed checkpoint write on /start fails a successful start and repeats the LLM cost
- Where: `main.py:249`, `session_record.py:41-42`.
- Failure: the DB is down, slow (H1), or `aupdate_state` raises. The first question has already streamed, then the
  client gets `error`, and its retry re-runs Planner + Interviewer. Yet /next-turn already handles a missing thread:
  it runs from the request and starts recording (`session_turn_guard.py:49`).
- Fix: make `record_start` best-effort. Wrap it in try/except, with a timeout per H1. Log
  `session_record_failed` with the error type only and count it in metrics, then still send `done`. If
  `adelete_thread` succeeded but `aupdate_state` failed, the thread is missing, which is handled. If the delete
  failed, the old thread still has the start-state turn_count, so the guard passes and only logs a mismatch.

### M3. /start does not take the turn lock; a concurrent /start can lose to an in-flight turn's late write
- Where: `main.py:238-249` (no `turn_locks.hold`).
- Scenario:
  1. /start (retry or restart) for session S arrives while /next-turn for S holds the lock.
  2. `record_start` deletes the thread and seeds turn 1.
  3. The in-flight run's exit `aput` then lands on the same thread_id and becomes the latest checkpoint, holding the
     old session's turn_count N+1.
  4. The new session's turn 1 gets `409 turn_out_of_order` forever.
- Fix: hold `turn_locks` in /start, returning 409 turn_in_progress. Release it after `record_start`, or when the
  stream closes. Low likelihood, trivial fix.

### M4. Checkpoints grow without bound and are never deleted (cost and PII retention)
- Where: `session_record.py:22-35`, the runner's `durability="exit"`, and there is no cleanup anywhere.
- Facts:
  - Only the latest checkpoint is ever read, yet the full history is kept.
  - `transcript` (operator.add) stores the WHOLE list as a new blob version every turn, which is O(N^2).
  - `last_turn.done` stores `state` a second time.
  - Every rejected attempt writes a "loop" checkpoint plus a pending ERROR write (probe: 5x 422 gave 5 extra
    checkpoints). Exit durability saves on error too (`_suppress_interrupt`). This covers 422 voice retries,
    perceive 409/422 and Interviewer errors.
  - Nothing deletes a thread at session_end or finalize, so candidate answers are kept indefinitely. The plan defers
    TTL to DE, but per NT that rule is currently `unenforced` and should be stated as such.
- Fix:
  - After a successful turn, prune the older checkpoints of the thread (keep the latest), or run a periodic SQL job.
  - Delete the thread at finalize, or N days after session_end.
  - Drop `state` from `last_turn.done` and rebuild it from the `state` channel on replay. It is always equal,
    because last_turn is always the latest turn.
  - Optionally keep the transcript out of the checkpoint until phase 04 needs it.

## Low

### L1. A cancel that lands during the exit checkpoint write releases the lock before the write finishes
- Where: `turn_graph_runner.py:41-49`.
- Cause: `AsyncPregelLoop.__aexit__` runs the exit (checkpoint put) in a separate `exit_task`. If cancelled while
  awaiting it, LangGraph re-raises CancelledError with `exit_task` in `e.args` "to permit the consumer to await it".
  The pump's finally then releases the lock immediately.
- Failure: the client disconnects in the few ms of the final write. A quick retry can read the pre-turn state and
  re-evaluate. The old write lands later. With random version suffixes the newer run's checkpoint wins, so this is
  wasted cost rather than corruption.
- Fix: in `except CancelledError as e`, find any `asyncio.Task` in `e.args` and `await asyncio.shield(t)` (with a
  timeout) before re-raising.

### L2. `aclose` swallows the awaiting task's own cancellation and can call `on_finish` while the pump is still unwinding
- Where: `turn_graph_runner.py:81-86`.
- `except BaseException: pass` also eats a CancelledError aimed at the caller. That is mostly unreachable, because
  `_TurnStream` shields it, and only possible on a double cancel in `prime`.
- Fix: catch only when `self._task.done()`, re-raise any outer cancel, and call `on_finish` only when the task is done.

### L3. The setup script prints `{err}` despite its "do not print the URL" comment
- Where: `scripts/setup_session_checkpoint_tables.py:35`.
- psycopg conninfo parse errors (`missing "=" after "…"`, `invalid URI query parameter …`) can echo parts of the
  DSN. Print `type(err).__name__` only, or redact `SESSION_DB_URL` from the message.

### L4. Exception reprs are stored in `checkpoint_writes`
- On error exits, the ERROR write (the repr of the exception) is persisted. An Evaluator/Interviewer ValidationError
  can include raw LLM output that quotes the answer. This is minor PII in the DB, so add it to the TTL scope.

### L5. Switching stores can lock in-flight sessions
- Going SESSION_STORE postgres -> memory -> postgres (rollback, then re-enable) leaves stale threads that are behind
  their clients. In-flight sessions then get `turn_out_of_order` (same root cause as M1). Add this to the runbook,
  or clear the tables on re-enable.

## Checked and found correct (scout and edge cases)
- Lock: `hold` happens before `try`, so a 409 never releases someone else's lock.
  - `check_turn` raising 409/503, or being cancelled: the finally releases it.
  - `turn_context` raising: run is None, so it is released.
  - `prime` failing or being cancelled: aclose calls on_finish.
  - Task cancelled before start: aclose calls on_finish.
  - Pump finishing normally: `_END` is queued, then on_finish runs, with no await in between. The client sees
    `done` only after the lock is free and the checkpoint is durable.
  - The response never being invoked: the pump still finishes and releases.
  - Replay: released before the stream.
- `durability="exit"` + `{}`: a mid-`ask`, error, or 409/422 checkpoint has `next=('ask',)` or
  `('perceive',)`. The new run discards those tasks and starts at perceive. A stale `route` is overwritten. `record`
  is skipped only when the run did not finish, which is the intended "re-run whole turn".
- Replay: reask (probe: identical done and meta) and session_end (no meta, no token) match the live output.
  Replay is checked before `done`, so the final turn can be replayed.
- Logs: mismatch logs field names only, store errors log type only. No answer text in the new logs. The pre-existing
  tracing input already carries the answer.

## Positive
- `record` is the only writer of persistent keys, which keeps the semantics of cut runs simple.
- Single-shot release closure. Pump-task design is reused for cleanup.
- The Postgres integration test and the deviations are documented in the plan.
- Postgres version strings use random suffixes, so concurrent writers never collide on blobs.

## Recommended actions (order)
1. H1: pool timeout plus `wait_for` on reads and the start write.
2. H2: fail closed on memory store in staging/prod, or evict threads.
3. M1: decide shadow vs enforce for 409 already_answered/out_of_order (needs the interview-service owner).
4. M2: best-effort `record_start`. M3: lock /start.
5. M4: pruning and deletion policy. Declare TTL as `unenforced` until DE delivers it.
6. Low items as convenient.

## Metrics
- Tests: 32/32 targeted pass (full suite reported 1457 pass, not re-run).
- No tests yet for: DB timeout behaviour, /start record failure, /start concurrent with next-turn, cancel during
  the exit write.

## Unresolved questions
- Does interview-service guarantee an identical answer and answer_source on retry, including voice re-records? This
  decides M1.
- Which SESSION_STORE value will staging/prod deploy with in phase 03? This decides how urgent H2 is.
- Who owns checkpoint retention (DE job vs ai-service delete at finalize), and when?


## Xử lý (2026-11-27, sau review)
- H1 sửa: pool `timeout=3`, `asyncio.wait_for` quanh `aget_state` (guard) và ghi `/start`; test `test_hanging_store_returns_503_fast_and_frees_the_session`.
- H2 sửa một phần: memory giữ tối đa 500 phiên (xoá phiên cũ nhất khi `/start`), log `session_store_memory_in_strict_env` khi APP_ENV staging/production. Không chặn khởi động (pha song song).
- M1: giữ 409, ghi yêu cầu "retry gửi lại nguyên answer" vào 06 §7.4 + câu hỏi FSD.
- M2 sửa: `record_start` lỗi chỉ log `session_start_not_recorded`, `/start` vẫn `done`.
- M3 sửa: `/start` giữ khoá phiên (409 `turn_in_progress` khi lượt đang chạy).
- L3 sửa: script chỉ in tên lỗi.
- M4, L1, L2, L4, L5: chưa sửa, ghi ở phase 03 "Còn mở".
