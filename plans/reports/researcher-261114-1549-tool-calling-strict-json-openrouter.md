# Tool calling + strict JSON via OpenRouter (gpt-4o-mini) - 2026-11-14
Docs-only. Verified = seen in fetched docs this session. Unverified = prior knowledge, not confirmed in docs fetched.

## Answers
1. tools + response_format json_schema same request
 - Chat Completions accepts both params (unverified in fetched text; fetched Structured Outputs page truncated before combo section). Known behavior: each turn model emits tool_calls (content null) OR schema-conforming content. Schema applies to content only, not tool args (tool args governed by function `strict`).
 - Verified: json_schema response_format needs gpt-4o-mini / gpt-4o-2024-08-06+. Refusals land in `refusal`, may not match schema. First request w/ new schema has extra latency.
 - Verified: strict function: additionalProperties:false on every object; all props in `required` (optional = type incl. "null").
 - parallel_tool_calls: docs only say strict disabled when model makes multiple calls in a turn (stated for fine-tuned). Set false => 0 or 1 call/turn. Safe: set false.
 - Src: https://developers.openai.com/api/docs/guides/function-calling ("additionalProperties must be set to false"); https://developers.openai.com/api/docs/guides/structured-outputs
2. tool_choice:"none" + json_schema
 - Verified: "none" = model behaves as if no functions passed (function-calling guide). So it cannot call tools; response_format is a separate param, expected to still apply -> schema-valid content. Unverified by docs; confirm live.
 - Keep `tools` in the request on final step (OpenRouter docs: include tools on every request, router validates schema).
3. OpenRouter
 - Passes tools, tool_choice, parallel_tool_calls, response_format (OpenAI-compatible; tool-calling doc lists tool_choice none/auto/forced + parallel_tool_calls default true). Src: https://openrouter.ai/docs/features/tool-calling
 - provider.require_parameters: bool, default false. true => "only routes to providers that support all parameters in your request". false => providers lacking a param ignore it silently. Src: https://openrouter.ai/docs/features/provider-routing
 - Even with false, tools and response_format are a soft preference (best-effort routing to supporting providers); if no provider supports them, param is dropped, request still goes. => Recommend `extra_body={"provider": {"require_parameters": True}}` so silent drop of response_format/tools becomes a routing error (fail loud).
 - Azure: OpenRouter lists OpenAI + Azure as providers for gpt-4o-mini (unverified this session; check model page https://openrouter.ai/openai/gpt-4o-mini/providers). Azure supports tools + structured outputs for gpt-4o-mini on recent API versions (unverified). Optionally pin `provider.order:["OpenAI"], allow_fallbacks:false` for determinism; costs availability.
4. Message format (verified, OpenRouter doc)
 - Chat Completions: assistant msg w/ `tool_calls` [{id,type:"function",function:{name,arguments(JSON string)}}]; reply `{role:"tool", tool_call_id, content}` (content string). Must append the assistant tool_calls message verbatim before tool msgs; one tool msg per call id.
 - Send `tools` on every follow-up request. No OpenRouter-specific message-shape difference found; Chat Completions tool def nested under `function`.
5. Cost/latency
 - Verified: function defs "billed as input tokens", count against context.
 - Verified: prompt caching prefix includes tool definitions + output schemas; changing tools/schema breaks cache. Src: https://developers.openai.com/api/docs/guides/prompt-caching. Min 1024 tokens for caching (older models: varies by settings). Keep tools/schema/system prompt static and first; put dynamic content last. Cache via OpenRouter on OpenAI = automatic, no config (unverified; Azure may differ).
 - Each tool round = extra full LLM call (latency + cost) -> cap rounds.
6. Strict schema limits
 - Verified: additionalProperties:false, all fields required (optional via null union).
 - maxLength/minLength: historically NOT supported in strict mode (unsupported keywords rejected or ignored); fetched docs excerpt didn't cover the keyword list. Unverified for 2026 -> assume not enforced.
 - => YES, code must enforce `query` <= 200: truncate (or reject + return tool error message to model). Also validate business rules post-parse (docs: "validate business rules the schema can't express").
 - Strict first-use schema compile latency; avoid unsupported keywords (pattern/format/min/max) in schema to dodge 400s.

## Design implications
- Request every turn: tools(strict:true) + tool_choice + parallel_tool_calls:false + response_format json_schema(strict) + extra_body provider.require_parameters:true. Keep tools/schema/system prompt byte-stable for caching.
- Loop: while resp.tool_calls and round < MAX (e.g. 3): append assistant msg (incl tool_calls), run tool, append role:tool msg w/ tool_call_id. On last allowed round set tool_choice:"none" to force final schema JSON.
- Parse tool args with json.loads in try/except; code-enforce query len<=200 (truncate), non-empty, type checks; on invalid return error string as tool result (not raise).
- Final content: json.loads + pydantic validate; handle `refusal`, finish_reason=length/content_filter, empty content; retry once or fallback to no-tools single call.
- Handle 404 "no endpoints found that support..." from require_parameters (means no provider supports combo) -> fallback: drop response_format on tool turns, apply schema only on final tool_choice:"none" call (two-phase pattern, most robust).
- Per-turn token/latency log; track cached_tokens in usage.
- Cap rounds, dedupe repeated identical queries, tool timeout.

## Unresolved questions (verify live once key available)
1. Does gpt-4o-mini accept tools(strict)+response_format json_schema in one request via OpenRouter with require_parameters:true (no 404)? Does it return tool_calls with content null?
2. tool_choice:"none" + response_format: content schema-valid?
3. Is maxLength accepted/enforced in strict schemas on gpt-4o-mini (400 or silently ignored)?
4. Provider actually used (OpenAI vs Azure) in response `provider` field; Azure behavior w/ the combo; does pinning matter?
5. usage.prompt_tokens_details.cached_tokens > 0 on 2nd call w/ tools present, via OpenRouter?
6. parallel_tool_calls:false honored; any multi-call turn still appears?
7. Whether fetched-doc gaps (combo section, keyword list of Structured Outputs page chars 100000+) say anything different.
