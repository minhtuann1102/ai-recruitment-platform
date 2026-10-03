# ADR-004: Dữ liệu phỏng vấn thuộc interview-service

**Ngày:** 2026-09-28  
**Trạng thái:** Accepted (response AI đã đổi, xem [ADR-007](adr-007-multi-agent-interview.md))

## Bối cảnh

Hệ thống có hai service liên quan đến phỏng vấn:
- `interview-service` (NestJS) — quản lý phiên, lưu trữ kết quả
- `ai-service` (FastAPI, tương lai) — logic AI agent, RAG, sinh câu hỏi

Cần quyết định dữ liệu phỏng vấn (session, lượt hỏi đáp, điểm) thuộc service nào.

## Quyết định

Toàn bộ dữ liệu phỏng vấn **thuộc `interview-service`**. AI service chỉ nhận lịch sử qua request và trả về kết quả, **không lưu trữ phiên**.

```
interview-service (owner)          ai-service (stateless processor)
┌──────────────────────┐          ┌─────────────────────────┐
│ interview_sessions   │          │ knowledge_chunks (RAG)  │
│ interview_turns      │  REST    │ agent logic             │
│ interview_scores     │ ──────▶  │                         │
│ question_bank        │ ◀──────  │ Tra ve: scores, next_q  │
│ interview_results    │          │ agent_decision, reason  │
└──────────────────────┘          └─────────────────────────┘
```

## Lý do

- **Single source of truth:** interview-service là nơi duy nhất lưu dữ liệu phỏng vấn
- **AI service stateless:** để scale, retry, swap model mà không mất data
- **Mock dễ dàng:** thay AI service bằng mock mà không ảnh hưởng data flow
- **Bảo mật:** dữ liệu ứng viên không rời khỏi backend NestJS (AI service chỉ nhận context cần thiết)

## Hệ quả

- `interview-service` cần `interview_db` với đầy đủ schema
- Request gửi đến AI service chứa: lịch sử câu hỏi/trả lời, metadata phiên
- Response từ AI service chứa: scores (JSONB), agent_decision, next_question, reasoning
- Mock AI service chỉ cần trả về response cố định từ question_bank
