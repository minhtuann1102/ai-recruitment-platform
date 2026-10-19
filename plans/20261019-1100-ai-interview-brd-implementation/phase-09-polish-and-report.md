# Phase 09. Hoàn thiện và báo cáo

## Context Links
- [plan.md](plan.md) · [sprint-plan](../../docs/sprint-plan.md) (S4-AIE-1–3, S5-3, S5-5, S5-6, S5-8) · [design 09 §10.3](../../docs/ai-service/09-agent-quality-evaluation.md) (quy trình)

## Overview
- **Priority:** P1 · **Status:** chưa bắt đầu · **Tuần:** W8 (30/11–06/12) + Sprint 5 (07–21/12)
- Khóa tính năng ngày **06/12**, chạy đánh giá cuối, tinh chỉnh, cập nhật tài liệu và viết phần AI của báo cáo.

## Key Insights
- Sprint 5 dành cho polish và báo cáo, không thêm tính năng. Số liệu đánh giá là bằng chứng chính của đồ án.
- Mọi dòng "giả định" trong NFR phải thành "đã đo" hoặc được ghi rõ là chưa đo.

## Requirements
- Cổng cuối: ±1 band ≥ 90%, độ lệch khoan dung trong [−0.3, +0.3], fallback < 2%, lỗi format < 1%. S4-AIE-1 (tinh chỉnh prompt), S4-AIE-2 (prompt theo category), S4-AIE-3 (cache RAG Redis, nếu còn thời gian), S5-3 (TTFT P95), S5-8 (anti-cheat, Stretch).

## Architecture
Không đổi. Chỉ tối ưu prompt, cache và cấu hình.

## Related Code Files
- **Sửa:** prompts v2, `app/rag/` (cache Redis, nếu làm), `docs/architecture/{api-contracts,ai-integration,data-model,services}.md`, `docs/ai-service/*`, ADR-008, `docs/sprint-plan.md`, `docs/project-roadmap.md` (nếu có).
- **Tạo:** `plans/reports/eval-final.md`, kịch bản demo, dữ liệu phiên demo.

## Implementation Steps
1. Chạy đầy đủ tầng 2 (70 mẫu) và tầng 3 (28 phiên); so với baseline Phase 07.
2. Tinh chỉnh prompt/policy tới khi đạt cổng cuối hoặc ghi rõ khoảng cách và nguyên nhân.
3. Cache RAG nếu TTFT cần; đo lại.
4. Rà soát bảo mật phần AI (S5-4): khóa API, injection, log không chứa nội dung, token nội bộ, route `/ai/*`.
5. Cập nhật toàn bộ tài liệu cho khớp code; chốt ADR; ratify constitution.
6. Viết chương AI cho báo cáo (kiến trúc agent, RAG, đánh giá, riêng tư và pháp lý) và slide.

## Todo List
- [ ] Chạy đánh giá cuối + báo cáo
- [ ] Đạt hoặc giải trình cổng cuối
- [ ] Rà soát bảo mật AI
- [ ] Docs, ADR, constitution khớp code
- [ ] Chương báo cáo + slide + kịch bản demo
- [ ] (Stretch) cache RAG, anti-cheat

## Success Criteria
- Demo end-to-end ổn định trên staging; mọi số liệu trong báo cáo trích từ `plans/reports/`; `main` build và CI xanh; không còn "giả định" chưa ghi rõ trong NFR.

## Risk Assessment
- Số đo cuối kém mục tiêu → báo cáo trung thực khoảng cách và hướng cải thiện (không chỉnh số).
- Trễ nhịp từ các phase trước → áp mốc cắt giảm trong plan.md.

## Security Considerations
- Dữ liệu demo tổng hợp, không PII thật; không đưa `.env` hay khóa vào báo cáo hay slide.

## Next Steps
Sau 21/12: hướng phát triển (voice realtime, học từ dữ liệu, chia sẻ kết quả với consent).
