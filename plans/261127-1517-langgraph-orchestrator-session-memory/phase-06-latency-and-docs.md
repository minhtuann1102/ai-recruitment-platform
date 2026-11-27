# Phase 06: Đo độ trễ + cập nhật docs

## Context Links
- [plan.md](plan.md) · doc 12 mục 7.4, mục 10 · `evals/cost_latency.py`, `evals/ttft_breakdown.py`

## Overview
- Priority: P1 · Status: pending · Effort: 0,5d (chia ra sau phase 02, 04, 05)

## Requirements
- Đo overhead của graph và checkpoint: TTFT P50 / P95, thời gian đọc + ghi checkpoint mỗi lượt. Không được ăn vào
  ngân sách khoảng 10 s của Evaluator.
- Đo bằng mock trước (overhead thuần). Bản LLM thật chỉ chạy `cost_latency` **một lần** sau phase 04, **hỏi user trước** (tốn token).

## Related Code Files
- Sửa: `evals/cost_latency.py` (thêm thời gian checkpoint nếu chưa có trong metadata), `app/metrics.py`
  (histogram `session_checkpoint_seconds`)
- Docs (theo doc 12 mục 10): README A4 (sau 02), README A5 + ADR mới thay một phần ADR-004 + constitution IV
  qua `/speckit-constitution` (DE, sau khi duyệt), docs 06 / 07 (sau 04), doc 03 (sau 02 / 05), `.env.example`,
  `specs/README.md` (thêm feature, công cụ: workflow `plans/`, trỏ plan này), `context/*`, doc 12 (trạng thái)

## Implementation Steps
1. Sau 02: so TTFT mock trước / sau graph. Ghi kết quả vào báo cáo `plans/reports/`.
2. Sau 04: đo checkpoint với Postgres local; hỏi user rồi chạy `cost_latency` thật một lần.
3. Cập nhật docs theo danh sách trên; `check_docs.py`.

## Todo List
- [ ] Đo overhead graph (mock)
- [ ] Đo checkpoint Postgres local
- [ ] cost_latency thật (sau khi user đồng ý)
- [ ] Docs theo doc 12 mục 10
- [ ] Dọn checkpoint của lần chạy lỗi (SESSION_GRAPH=session): mỗi lượt 409 / 422 / bị ngắt / Reporter lỗi ghi thêm một
  checkpoint con của `wait_answer` (durability exit), không bao giờ bị xoá; đo mức phình rồi quyết định dọn / TTL (review phase 05, M3)

## Success Criteria
- Overhead graph < 50 ms P50; đọc + ghi checkpoint < 100 ms P95 trên DB đích. Vượt thì báo, không tự nới ngân sách.

## Risk Assessment
- DB đích ở xa (Supabase) chậm hơn local nhiều: đo lại trên staging khi DE dựng xong.

## Security Considerations
- Báo cáo đo không chứa câu trả lời ứng viên.

## Next Steps
- Đóng plan, cập nhật `specs/README.md`.
