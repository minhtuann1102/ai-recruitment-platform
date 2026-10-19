# Phase 08. Voice và học từ dữ liệu (có điều kiện)

## Context Links
- [plan.md](plan.md) · [BRD §0.3, §4.3](../../docs/ai-service/requirements/01-brd.md) · quyết định A8 (voice) trong [docs/ai-service/README.md](../../docs/ai-service/README.md) · `specs/README.md` feature 015 · sprint-plan S4-DE-5 · FR-AI-110–133

## Overview
- **Priority:** P3 (Stretch) · **Status:** chưa bắt đầu, **chỉ làm sau gate 22/11** · **Tuần:** W7+
- Hai hướng voice mâu thuẫn nhau giữa BRD v0.3 và `main`. Mặc định theo `main` (tùy chọn A). Học từ dữ liệu hoãn, chỉ chuẩn bị tiền đề.

## Key Insights
- **Tùy chọn A (`main`, 15/10):** DE sở hữu (feature 015, S4-DE-5). TTS đọc `done.question` (không đọc theo token vì có `replace`); STT bấm-để-nói gửi transcript qua `/answer`; lưu bản STT gốc và bản đã sửa; không lưu audio; **ai-service không biết có voice**.
- **Tùy chọn B (BRD v0.3):** hội thoại realtime qua voice-gateway. `main` ghi rõ ngoài phạm vi vì TTFT ≈ 3.6 s và phải thiết kế lại turn-taking. Chỉ làm nếu owner xác nhận bằng văn bản; cần ADR-009.
- Học từ dữ liệu: constitution V và docs `main` đều chưa cho phép; cần consent, ẩn danh, tách golden set.

## Requirements
- **Gate go/no-go (22/11)** cho voice: (a) chat chạy end-to-end qua harness hoặc stack thật; (b) Evaluator ≥ 80% ±1 band; (c) giao diện của FSD có hoặc đúng tiến độ; (d) có số đo TTFT; (e) DE có tài khoản STT/TTS. Thiếu một điều kiện thì cắt voice.
- Phần AIE của tùy chọn A: câu hỏi đọc được thành tiếng (đã có từ Phase 06), prompt Evaluator biết transcript có thể sai chính tả, golden set có mẫu nhiễu STT (QUAL17).

## Architecture
A: `FE (TTS/STT) ⇄ interview-service /answer (+trường tùy chọn STT gốc) ⇄ ai-service (không đổi)`.
B (ngoài kế hoạch): thêm container voice-gateway, xem [L2 §3, §8.4](../../docs/ai-service/11-architecture-l2-containers.md).

## Related Code Files
- **Sửa (A):** `app/prompts/evaluator.v1.md` (ghi chú transcript STT), `evals/evaluator_golden.jsonl` (mẫu nhiễu), docs contract (trường tùy chọn của `/answer`, tên chốt ở spec 015).
- **Chưa tạo (B):** voice-gateway, ADR-009.
- **Học từ dữ liệu:** chỉ đề xuất cho FSD thêm cột `learning_consent_at` (nullable) và `media_consent_at` khi viết migration `interview_db`.

## Implementation Steps
1. Họp gate 22/11; ghi quyết định (go/no-go, A hay B).
2. Nếu go A: cập nhật prompt và golden set cho nhiễu STT; phối hợp DE về trường tùy chọn của `/answer`.
3. Nếu B: viết ADR-009, khảo sát hạ tầng voice-agent và chất lượng STT tiếng Việt xen thuật ngữ Anh **trước khi** cam kết.
4. Gửi đề xuất cột consent cho FSD (không đợi gate).

## Todo List
- [ ] Gate 22/11 có biên bản
- [ ] (A) prompt + golden set nhiễu STT
- [ ] Đề xuất cột consent cho FSD
- [ ] (B) chỉ khi owner xác nhận: ADR-009 + khảo sát

## Success Criteria
- Có quyết định gate ghi lại. Tùy chọn A: ai-service không đổi contract, báo cáo giữ chất lượng khi transcript nhiễu. Không có file audio trong lưu trữ.

## Risk Assessment
- Cố làm realtime trong 8 tuần làm trễ các phase lõi → mặc định cắt voice trước (mức cắt 1 của sprint plan).
- Chất lượng STT tiếng Việt chưa có số liệu → đo trước khi chọn.

## Security Considerations
- Âm thanh đi tới nhà cung cấp STT cần đồng ý riêng, không ghi lại; video chỉ hiển thị cục bộ (diễn giải A-6); không phân tích cảm xúc.

## Next Steps
Kết quả gate đưa vào Phase 09 (phạm vi báo cáo).
