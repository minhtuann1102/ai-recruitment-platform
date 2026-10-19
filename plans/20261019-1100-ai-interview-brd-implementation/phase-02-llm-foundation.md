# Phase 02. Nền tảng LLM

## Context Links
- [plan.md](plan.md) · [design 03 §4.6](../../docs/ai-service/03-orchestrator-state-machine.md) (xử lý lỗi) · [design 08 §9.3](../../docs/ai-service/08-latency-and-cost.md) (model từng agent) · FR-AI-063, 070, 080, 081

## Overview
- **Priority:** P1 · **Status:** chưa bắt đầu · **Tuần:** W2–W3
- Dựng lớp gọi LLM dùng chung cho 6 agent: retry, structured output, repair, đo usage, prompt có phiên bản, **LLM giả** để test logic điều phối trong CI.

## Key Insights
- Số đo thật qua OpenRouter: 4–5 s cho 150–200 token ra, embedding 0.7–1.5 s. Output gọn và `max_tokens` đúng là đòn bẩy độ trễ lớn nhất.
- Hiện endpoint là `def` đồng bộ, SSE đã async. SDK `openai` async dùng chung một client (keep-alive).
- Constitution VI: fake LLM chỉ để kiểm logic điều phối, không khẳng định chất lượng chấm.

## Requirements
- FR-AI-063 (client cấu hình bằng env), 070 (retry/repair), 080 (usage, latency, prompt_version, fallbacks), 081 (model, temperature, max_tokens, timeout theo agent).
- NFR: REL02 (retry ≤ 2, backoff 0.5 s rồi 1.5 s + jitter, tôn trọng Retry-After, không retry 4xx), PERF09 (≤ 10 s cho Evaluator), MNT05, MNT07, OBS01, SEC06 (khóa không vào log).

## Architecture
```
agent ──▶ LlmGateway.complete(agent, messages, schema?) ──▶ AsyncOpenAI (OpenRouter)
              │ retry · structured output · repair 1 lần · length ×1.5 · usage
              └─▶ PromptStore (app/prompts/<agent>.vN.md, prompt_version)
Agent registry: AGENT_<NAME>_MODE = mock | llm  (mock giữ làm fallback)
```

## Related Code Files
- **Tạo:** `app/llm/{gateway,retry,structured_output,usage,settings}.py`, `app/prompts/{__init__,store}.py` + `app/prompts/*.md`, `app/agents/registry.py`, `tests/fakes/fake_llm.py`, `tests/test_llm_gateway.py`.
- **Sửa:** `app/config.py` và `app/llm_client.py` → chuyển vào `app/llm/`; `.env.example` (biến theo agent: `LLM_MODEL_<AGENT>`, `AGENT_<NAME>_MODE`, `LLM_STRUCTURED_OUTPUTS`, `LOG_LLM_IO=false`); `scripts/smoke_llm.py`.
- **Giữ:** `mock_*.py` làm triển khai `mock` của từng agent.

## Implementation Steps
1. Định nghĩa `Settings` theo agent (model, temperature, max_tokens, timeout) theo bảng design 08 §9.3.
2. `LlmGateway`: gọi `chat.completions` async; structured output `json_schema` strict, fallback `json_object` + Pydantic; ghi usage và độ trễ vào `metadata`.
3. Retry lỗi tạm thời; repair 1 lần khi sai schema; `finish_reason == "length"` thì thử lại một lần với `max_tokens × 1.5`.
4. `PromptStore`: đọc `*.md`, tách header phiên bản, bọc nội dung không tin cậy trong khối `untrusted`.
5. `FakeLlm` kịch bản hóa (trả JSON cố định, ném timeout/429/JSON hỏng/cắt cụt) cho test.
6. Registry chọn `mock` hoặc `llm` theo env; mặc định `mock` để CI không cần khóa.

## Todo List
- [ ] Settings + gateway + retry + structured output
- [ ] Prompt store và cờ `LOG_LLM_IO`
- [ ] FakeLlm và test: đúng số lần retry, đúng backoff, repair, length
- [ ] Registry mode mock/llm, mặc định mock
- [ ] `smoke_llm.py` dùng gateway; một lần chạy thật xác nhận

## Success Criteria
- CI xanh không cần khóa; test chứng minh retry ≤ 2, không retry 4xx, repair 1 lần; một lần gọi thật qua gateway trả JSON hợp lệ kèm usage.

## Delivery (bàn giao)
- Gói `app/llm/` (gateway, retry, structured output, usage), `app/prompts/` có phiên bản, `FakeLlm`, registry mock/llm
- `.env.example` cập nhật biến theo agent
- `scripts/smoke_llm.py` chạy qua gateway

## Cách test và nghiệm thu
1. `pytest`: retry đúng 2 lần, backoff 0.5 s rồi 1.5 s, không retry 400/401/403, repair 1 lần, `length` thử lại ×1.5 (bằng FakeLlm, không mạng)
2. CI Python 3.11 xanh: `docker run --rm -v "$PWD":/w -w /w/apps/ai-service python:3.11-slim sh -c "pip install -q -r requirements-dev.txt && python -m pytest -q"` (đúng bản Python của CI)
3. Một lần chạy thật: `python -m scripts.smoke_llm` in model, thời gian, token, JSON hợp lệ
4. Kiểm tay: `LOG_LLM_IO=false` thì log không có nội dung prompt hay khóa

## Đồng bộ tài liệu (bắt buộc, cùng PR với thay đổi)
FR-AI-063/070/080/081 đổi trạng thái; NFR REL02, MNT05, MNT07, OBS01; design 03 §4.6 và 08 §9.3 ghi "đã cài đặt"; L2 §9 (bảng thành phần ai-service); `ai-integration.md`. BRD chỉ cập nhật bảng truy vết/trạng thái nếu yêu cầu đổi.
Sau khi sửa: chạy `python apps/ai-service/scripts/check_docs.py` (link, ID, truy vết BR→FR→NFR, số lượng trong mục lục).

## Nhánh
`thang/llm-foundation`. Mỗi nhánh một PR; mô tả PR ghi lại kết quả các bước test ở trên.

## Risk Assessment
- Một số model OpenRouter không hỗ trợ `json_schema` → có nhánh dự phòng `json_object`.
- Tốn tiền khi thử: giới hạn bằng `max_tokens` và chạy mock mặc định.

## Security Considerations
- Khóa chỉ từ env, không log nội dung prompt hay output khi `LOG_LLM_IO=false`; khối `untrusted` cho mọi dữ liệu người dùng.

## Next Steps
Phase 04, 05, 06 dùng gateway này.
