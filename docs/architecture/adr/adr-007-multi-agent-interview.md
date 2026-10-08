# ADR-007: Multi-agent phỏng vấn, chấm điểm cuối phiên

**Ngày:** 2026-10-03  
**Trạng thái:** Superseded bởi [ADR-008](adr-008-evaluator-per-turn-orchestrator.md)  
**Cập nhật:** ADR-004 (nội dung response từ AI)

## Bối cảnh

Thiết kế ban đầu: một endpoint `/api/evaluate` gọi LLM một lần mỗi lượt, trả scores + decision + câu hỏi tiếp. Agent chỉ là nhãn trong JSON, chấm từng câu thiếu bối cảnh cả phiên.

## Quyết định

Tách `ai-service` thành 3 agent trong một workflow có kiểm soát (graph, thứ tự cố định):

- **Planner**: chọn `deepen` / `switch_topic` / `keep_difficulty` (mỗi lượt).
- **Interviewer**: sinh câu hỏi tiếp + `answer_signal` nội bộ (mỗi lượt).
- **Evaluator**: chấm **từng câu** theo 4 tiêu chí + nhận xét từng câu + tổng kết, chạy **một lần cuối phiên**.

API: `/api/start`, `/api/next-turn`, `/api/finalize`, `/api/health`. Thay thế `/api/evaluate`.

Ứng viên không thấy điểm giữa phiên; sau phiên thấy điểm và nhận xét từng câu.

## Lý do

- Evaluator thấy cả transcript → chấm nhất quán hơn.
- Chấm điểm ra khỏi đường latency mỗi lượt.
- Tool tách theo vai, test và debug theo vai.

## Đánh đổi

- Nhiều LLM call hơn (ước tính ~16/phiên 5 lượt so với ~5): chi phí, latency mỗi lượt cao hơn.
- `/finalize` chậm → FE cần trạng thái chờ, BE cần timeout dài.
- Giữa phiên không có điểm → Planner dùng `answer_signal` sơ bộ.
- Đổi contract với FSD (`AiInterviewClient`, `interview_turns.scores` nullable).

## Hệ quả

- `ai-service` vẫn stateless; `interview-service` vẫn sở hữu dữ liệu (ADR-004 giữ nguyên).
- Cần đo so sánh 1-call vs 1-agent vs 3-agent trên 20+ câu trả lời mẫu (S3-AIE-4) để chứng minh giá trị.
