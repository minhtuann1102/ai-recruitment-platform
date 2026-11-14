# Phase 02: Vòng lặp công cụ trong gateway (hạng mục 0)

## Context Links
- Đề xuất mục 4; research; code map mục "0. Gateway / tool calling"; audit H1, M2, M3, L2, L3, L6
- `app/llm/gateway.py:65-126`, `retry.py:87-95`, `usage.py:7-51`, `metrics.py:57-82`, `tracing.py:124`, `errors.py`,
  `tests/fakes/fake_llm.py:29-31`, `docs/ai-service/README.md` (A4), `docs/ai-service/06-api-contract.md:302` (first event ≤ 15 s)

## Overview
- Priority: P1 (chặn 03). Status: code done (fake LLM), live check [BLOCKED-KEY]. Nhánh: `thang/llm-tool-loop`. Effort 1,5d. Không phụ thuộc code 01 → song song.
- Thư viện nội bộ, chưa agent nào dùng → không cờ hành vi. **Không làm split mode** (M2): combo không hỗ trợ → lỗi
  `tools_unsupported`, latch theo tiến trình, caller đi đường cũ không tools.

## Key Insights
- Closure `chat()` (`gateway.py:85-105`): hedge chỉ lần đầu (`:89`); **chỉ lần gọi sau** bị cắt theo ngân sách (`:90-92`,
  `if calls and budget_s`); `call_with_retry` cho lần đầu đủ `timeout_s` dù budget 0 (`retry.py:87-89,93-95`). Vòng lặp
  nhiều bước + fallback sẽ vượt 10 s nếu không sửa (H1).
- `tool_calls` có thì `content=None`, `finish_reason="tool_calls"`; fake `reply()` không có `tool_calls` → `getattr`;
  SimpleNamespace không có `model_dump` → tự dựng message assistant. Fake đã ghi params (`FakeOpenAI.calls`); `status_error`
  chưa map 404 (`fake_llm.py:29-31`) → thêm `404: openai.NotFoundError`.
- OpenRouter `provider.require_parameters=True` biến "bỏ âm thầm tham số" thành 404; áp cho **mọi** tham số (seed,
  reasoning) → có thể đổi provider so với lượt không tools (L3, ghi trong probe). Chỉ gửi khi base_url là OpenRouter.
- Strict không đảm bảo `maxLength` → code cắt `query` ≤ 200. `tools` hằng module, gửi mọi bước (cache prefix).
- Lỗi quy về `LlmError`/`LlmOutputError`/`LlmTimeoutError` (Evaluator bắt ở `agents/evaluator.py:221`).

## Requirements
- F: `complete_with_tools(agent, messages, schema, tools, run_tool, *, max_calls, step_deadline_s, budget_started,
  budget_s, prompt_version, collector) -> ToolLoopResult(data, record, tool_calls)`.
- F: mọi request: `tools`, `tool_choice="auto"`, `parallel_tool_calls=False`, `response_format` strict; bước cuối
  `tool_choice="none"` (hết `max_calls` hoặc hết `step_deadline_s`).
- F: **ngân sách đồng hồ chung**: mọi lần gọi (kể cả lần đầu) timeout = `min(cfg.timeout_s, budget_s − elapsed)`; còn lại
  < 0 → `LlmTimeoutError`. Mỗi bước có tools: timeout = `min(…, step_deadline_s_còn_lại + FINAL_RESERVE_S)` (1,5 s) để luôn
  còn chỗ cho bước `none`.
- F: repair (parse lỗi) gửi `tool_choice="none"` (M3); repair vẫn ra `tool_calls` → `LlmOutputError`.
- F: lỗi công cụ (exception, JSON đối số sai, tên lạ, query rỗng) → chuỗi lỗi làm `role=tool`, không ném. Lỗi vòng lặp →
  lớp `LlmError`. 404/400 "no endpoints … support" → `LlmError("tools_unsupported")` + set latch `tools_supported=False`
  (L6) → các lượt sau không thử nữa (đến khi restart).
- F: usage cộng dồn; `CallRecord.tool_calls`; metadata chỉ thêm `tool_calls` khi > 0.
- NF: `gateway.py` < 200 dòng; test `test_llm_gateway.py` hiện có xanh không sửa.

## Architecture
```
gateway._complete ─┐                       llm/tool_loop.py
                   ├─► llm/chat_call.py: ChatCall(gw, cfg, base, rec, started, budget_s, cap_first=bool)
complete_with_tools┘     __call__(msgs, *, timeout_cap=None, **override) -> choice
                         request_base(cfg, schema, llm), parse_or_repair(call, schema, msgs, content, rec, **override)
```
`ChatCall` giữ hành vi cũ khi `cap_first=False` (gateway thường); `cap_first=True` cắt cả lần đầu theo ngân sách.
```python
async def complete_with_tools(gw, agent, messages, schema, tools, run_tool, *, max_calls, step_deadline_s,
                              budget_started, budget_s, ...):
    if not tools_supported(): raise LlmError("tools_unsupported")            # latch
    cfg = agent_settings(agent, gw.llm, gw._env)
    base = request_base(cfg, schema, gw.llm) | {"tools": tools, "tool_choice": "auto", "parallel_tool_calls": False}
    if is_openrouter(gw.llm.base_url): merge_extra_body(base, {"provider": {"require_parameters": True}})
    chat = ChatCall(gw, cfg, base, rec, started=budget_started, budget_s=budget_s, cap_first=True)
    msgs, used, t0 = list(messages), 0, now()
    with observation(agent, "generation", input=messages) as gen:
        while True:
            step_left = step_deadline_s - (now() - t0)
            last = used >= max_calls or step_left <= 0
            choice = await (chat(msgs, tool_choice="none") if last
                            else chat(msgs, timeout_cap=step_left + FINAL_RESERVE_S))
            calls = getattr(choice.message, "tool_calls", None) or []
            if not calls: break
            if last: raise LlmOutputError("tool_calls sau tool_choice=none")
            msgs.append(assistant_tool_msg(calls))
            for c in calls:     # parallel off; dư vẫn phải trả lời từng id
                with observation("tool:" + c.function.name, "span", nest=True):
                    msgs.append({"role": "tool", "tool_call_id": c.id, "content": await safe_run(run_tool, c)})
            used += 1; rec.tool_calls += 1
        data = await parse_or_repair(chat, schema, msgs, choice.message.content or "", rec, tool_choice="none")
    ...  # rec.latency_ms, log, collector.add(rec) như gateway:119-126
```
`safe_run`: `json.loads` lỗi → `"error: invalid_arguments"`; query cắt 200, rỗng → `"error: empty_query"`; kiểm injection
do caller (03); `run_tool` ném → log + `"error: tool_failed"`.

## Related Code Files
- Create: `app/llm/chat_call.py`, `app/llm/tool_loop.py`, `tests/test_llm_tool_loop.py`.
- Modify: `app/llm/gateway.py:74-126` (dùng ChatCall; `complete(..., budget_started=None, budget_s=None)` → khi có thì
  `cap_first=True`), `app/llm/usage.py:7-17,35-51`, `app/metrics.py:57-73` (`ai_llm_tool_calls_total{agent}`,
  `ai_llm_tools_unsupported_total`), `app/llm/settings.py` (`is_openrouter`), `tests/fakes/fake_llm.py` (`tool_reply`,
  `finish_reason="tool_calls"`, 404 → `NotFoundError`, độ trễ giả lập), `.env.example` (không cờ mới).
- Delete: không.

## Implementation Steps
1. Refactor thuần: `ChatCall` + `request_base` + `parse_or_repair` từ `_complete`; `test_llm_gateway.py`,
   `test_langfuse_tracing.py` không sửa → xanh. Commit riêng.
2. Ngân sách chung (`cap_first`, `budget_started`) trong ChatCall/`complete`; mặc định không đổi hành vi.
3. Fake: `tool_reply`, 404, sleep giả để đo thời gian.
4. `tool_loop.py`, latch, usage/metrics/tracing.
5. Test fake: không gọi tool (params đủ `tools`, `parallel_tool_calls=False`, `provider.require_parameters`); 1 lần (đúng
   `tool_call_id`); vượt `max_calls` → `none`; tool_calls sau `none` → `LlmOutputError`; repair dùng `none`; tool ném; JSON sai;
   query 500 → 200; bước 1 chậm (fake 9 s) → tổng < 10,5 s và ra `LlmTimeoutError`; budget còn 0 → lần đầu cũng bị cắt;
   404 → `tools_unsupported` + latch (lượt 2 không gửi request); `tools` byte-identical mọi bước; base_url OpenAI → không `provider`.
6. Docs: README A4 (không framework, có tool calling SDK), `02` (gateway: vòng lặp, ngân sách chung, latch), `06` §7.4
   (`usage[agent].tool_calls` tùy chọn), `08`; `context/decisions.md`. check_docs, pytest. PR
   `[ai-service] feat: vòng lặp tool calling trong LLM gateway`.

## Todo List
- [x] Refactor ChatCall (test cũ không sửa)
- [x] Ngân sách chung `cap_first`
- [x] Fake: tool_calls, 404, độ trễ
- [x] tool_loop + latch + usage/metrics/tracing
- [x] Test bước 5
- [x] Docs + decisions
- [ ] PR (chưa mở, theo yêu cầu không push)
- [ ] **[BLOCKED-KEY]** `complete_with_tools` thật (evaluator, tool giả) ra JSON hợp lệ; 404 thì latch hoạt động

## Success Criteria
- `gateway.py` < 200 dòng; `test_llm_gateway.py` không đổi mà xanh.
- Với `budget_s=10`, mọi kịch bản fake kết thúc ≤ 10,5 s; mọi lỗi vòng lặp là `LlmError`.
- Không agent dùng → output `/api/*` y hệt.
- **[BLOCKED-KEY]** `complete_with_tools` thật (evaluator, tool giả) ra JSON hợp lệ; nếu 404 → latch hoạt động.

## Risk Assessment
- Combo không hỗ trợ → lookup không bao giờ chạy; 03 vẫn an toàn (đường cũ). Khi đó mở lại thiết kế (split) sau probe.
- `require_parameters` đổi provider → độ trễ khác; đo ở 03.
- Hedge chỉ lần đầu (giữ `:89`), không kéo dài đồng hồ.

## Security Considerations
- Whitelist tên công cụ, kiểm kiểu/độ dài đối số; kết quả công cụ do caller bọc `wrap_untrusted`. Không log đối số khi `log_io` tắt.

## Next Steps
- 03 dùng `complete_with_tools` với `budget_started` của Evaluator.
