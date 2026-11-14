# Review phase 02: gateway tool loop (`thang/llm-tool-loop` vs `thang/agentic-prep`)

Scope: `app/llm/chat_call.py` (105), `tool_loop.py` (152), `gateway.py` (140), `settings.py`, `usage.py`, `metrics.py`,
`tests/fakes/fake_llm.py`, `tests/test_llm_tool_loop.py` (223), docs 02/06/08/README, context. No real LLM called.

## Results
- pytest: **892 passed, 8 skipped** (7.98 s). `test_llm_gateway.py`, `test_langfuse_tracing.py` unchanged (empty diff).
- `check_docs.py`: 75 FR, 109 NFR, 0 errors.
- Probe (scratchpad, fake LLM): tool that sleeps 2 s with `budget_s=1.0` -> loop ends at **2.0 s** (budget overrun).
  One model reply with 30 tool_calls and `max_calls=1` -> **30 tool executions**.

## Focus checks
1. Refactor behavior-identical for `complete()` without budget args: yes. Line-by-line: `budget_s` defaults to
   `cfg.retry_budget_s`, cut only when `self.calls` (cap_first False), hedge only when `calls == 0`, length retry
   `max_tokens*1.5` once then `LlmOutputError`, repair `temperature=0` on original `messages`, `rec.attempts = chat.calls`,
   usage accumulation, log line, `log_io`, collector, trace metadata (adds `tool_calls` only if > 0). OK.
2. OpenAI protocol: assistant msg built by hand with `content=None` + `tool_calls` (id/type/function), every id answered in
   order, `tools` in base -> identical every step, `tool_choice="none"` on last step and repair (override), repair with
   tool_calls -> content "" -> `LlmOutputError`. OK.
3. Budget: every LLM call capped by `budget_s - (now - budget_started)`, retry budget = remainder, hedge limit within
   remainder, <= 0 -> `LlmTimeoutError` before request. LLM side bounded. **Tool execution is not bounded** (H1).
4. Errors: all paths -> `LlmError`/subclasses via `_map_error`; latch only on `NotFoundError` or 400 with "no endpoints" +
   "support". Retryable errors (429/5xx/timeout) never latch. Latch on any 404 is broad (M2).
5. Security: arg string <= 1000, JSON object required, name whitelist, query trimmed/<=200, exceptions logged by type only,
   no args logged unless `log_io`. Tool result size not capped (M3). No key logging.
6. Deviations: `run_tool(name, args)`, `max_calls` counts calls, step cap also caps retry budget, `failure_fallback` param:
   all acceptable and arguably better than spec. Caveat: counting calls is not enforced per step (H2).
7. Files < 200 LOC (test 223, fine). Tests meaningful; gaps listed in L-items. Docs accurate except minor (L3).

## Critical
None.

## High
**H1. `run_tool` has no timeout; total wall clock can exceed `budget_s`.** `tool_loop.py:90` awaits `run_tool` unbounded;
budget only checked at next LLM call (`chat_call.py:65-68`). Probe: 2 s tool, budget 1 s -> 2.0 s. Spec success criterion
"mọi kịch bản ≤ budget + 0.5 s" and H1 not met once phase 03 plugs in RAG (pgvector/embedding call can stall).
Fix: in `_safe_run` wrap with remaining time and return an error string:
```python
left = min(budget_s - (time.perf_counter() - budget_started), step_deadline_s - (time.perf_counter() - t0)) 
try:
    return str(await asyncio.wait_for(run_tool(name, {...}), max(left, 0.05)))
except asyncio.TimeoutError:
    return "error: tool_timeout"
```
(pass deadline into `_safe_run`; add a test with a slow tool asserting elapsed < budget + 0.5).

**H2. No per-step cap on number of executed tool calls.** `tool_loop.py:128-133` runs every call in the reply, then
`used += len(calls)`. Model ignoring `parallel_tool_calls=False` (or a provider not honoring it) with N calls -> N RAG
lookups in one step (probe: 30 with `max_calls=1`), multiplied tokens in next request. Fix: execute only
`max_calls - used` calls; answer the rest with `"error: call_limit"` (protocol still satisfied); count only executed ones.

## Medium
**M1. Length retry inside a tool step reuses full `timeout_cap`.** `chat_call.py:82` passes the same relative
`timeout_cap`, so a `finish_reason=length` retry gets another `step_left + 1.5` s; the reserve for the `none` step is lost
(global budget still holds). Fix: pass an absolute step deadline (`step_until`) and compute `cap = step_until - now` in
`__call__`, or recompute cap before the recursive call.

**M2. Latch on any 404 is broad and permanent.** `tool_loop.py:50-51`. A 404 from a bad model id/env typo or an OpenRouter
routing hiccup disables tools until restart with no signal beyond one counter. Fix: require message match for 404 too
("no endpoints"/"support"/"tool"), log a warning with status + truncated provider message at latch time, and consider a TTL
(e.g. re-probe after 10 min) instead of process-lifetime.

**M3. Tool result length not capped.** `tool_loop.py:90` `str(await run_tool(...))` appended verbatim. A big chunk set
grows every following request (cost/latency, step timeouts). Fix: `MAX_RESULT_CHARS` (e.g. 4000) truncation in
`_safe_run`, or document as hard caller contract in phase 03.

**M4. Double-record risk with phase 03.** `tool_loop.py:139-142` already adds `CallRecord(fallback=failure_fallback)`;
phase-03 spec (`phase-03-...md:49,90`) also says caller does `collector.add(... evaluator_lookup_fallback ...)`.
Fix: update phase-03 to pass `failure_fallback="evaluator_lookup_fallback"` and not add its own record; add the code to
`FALLBACK_KINDS` there.

## Low
- L1. `complete(budget_s=X)` without `budget_started` silently replaces retry budget but does not cap first call
  (`gateway.py` `_complete`, `ChatCall.__init__:57`); `budget_started` without `budget_s` and `retry_budget_s=None` -> no cap
  at all. Fix: require both or neither (`ValueError`), or document.
- L2. `ToolLoopResult.data: BaseModel` but `schema=None` would make `data.model_dump()` raise AttributeError (mapped to
  generic LlmError). Assert `schema is not None` at entry.
- L3. Docs 06 "đếm một lần mỗi process" for `ai_llm_tools_unsupported_total`: concurrent in-flight requests can each
  increment. Reword "≥ 1 lần".
- L4. `run_tool` gets `{**args, "query": query}`: extra untrusted keys pass through unvalidated. Pass only `{"query": q}`
  (strict schema has only `query`) or document.
- L5. Assistant tool step drops any `content` returned alongside tool_calls (`_assistant_tool_message`). Harmless; keep
  `choice.message.content` for fidelity.
- L6. `tool_loop.py` reaches `gw._env`, `gw._retry` private attrs; acceptable internally, could expose `gw.agent_cfg()`.
- L7. Test gaps: slow/hanging tool (H1), multi-call over quota (H2), 429/5xx exhausted not latching (only 401 tested),
  length inside a tool step, hedge with `cap_first`.

## Positive
- Clean extraction; old tests untouched and green; tracing parity kept.
- `cap_first` gives a true shared clock for LLM calls including hedge/retry; tested with scaled slow fake.
- Error paths all inside `LlmError`, failed loop keeps latency/tokens (audit M4).
- `is_openrouter` host check (not substring) and `merge_extra_body` keeps reasoning.
- Untrusted-arg handling strict and tested (bad JSON, list, empty, unknown tool, oversize).

## Score: 8/10
Refactor and protocol are solid; H1/H2 must be fixed before phase 03 wires a real lookup.

## Unresolved questions
- Does OpenRouter/OpenAI accept `parallel_tool_calls=false` together with `tool_choice="none"` under
  `require_parameters=true`? [BLOCKED-KEY] probe should cover it.
- Exact OpenRouter error text/status for "combo unsupported" (404 vs 400) unverified; affects M2 matcher.
