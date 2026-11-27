# Phase 06: Đo độ trễ + cập nhật docs

## Context Links
- [plan.md](plan.md) · doc 12 mục 7.4, mục 10 · `evals/cost_latency.py`, `evals/ttft_breakdown.py`

## Overview
- Priority: P1 · Status: code + docs xong 2026-11-27 (chờ user test; còn mục chờ duyệt / chờ user, xem Todo) · Effort: 0,5d (chia ra sau phase 02, 04, 05)

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
- [x] Đo overhead graph (mock): P50 4-5 ms memory (phase 02: 3,0-3,5), đạt < 50 ms
- [x] Đo checkpoint Postgres local: `evals/session_store_latency.py`, metric `ai_session_checkpoint_seconds{op,store}`
  (mixin `app/session_store/session_checkpoint_timing.py`); đọc+ghi P95 7,8 ms (per_turn) / 12,1 ms (session), đạt < 100 ms
  **trên local**. Báo cáo `plans/reports/eval-261127-2346-langgraph-latency.md`
- [ ] cost_latency thật (sau khi user đồng ý): **CHƯA LÀM**, cần user đồng ý vì tốn token
- [ ] Đo lại trên Supabase / staging khi DE dựng DB (RTT mạng làm số lớn hơn local)
- [x] Docs theo doc 12 mục 10 phần AIE: 03 / 06 (bảng metric) / 07 (kích thước) đã cập nhật ở phase 02-05 + 06, doc 12
  (dòng trạng thái), docs/ai-service/README (dòng đề xuất), `specs/README.md` (feature 018), `context/project-state.md` +
  `context/environment.md`; `.env.example` đã có `SESSION_*` / `SESSION_GRAPH` (kiểm lại); `check_docs.py` pass
- [ ] **Chờ duyệt, việc của DE (AIE không sửa):** README A4/A5 (`docs/ai-service/README.md` dòng A4, A5), constitution IV
  qua `/speckit-constitution`, ADR mới thay một phần ADR-004. Chưa ai duyệt đảo A4/A5 nên các dòng này giữ nguyên
- [x] Dọn checkpoint của lần chạy lỗi (review phase 05, M3): đo 10 lần `voice_no_speech` (422): +10 checkpoint cả `per_turn`
  lẫn `session`; Postgres +16,8 KB (per_turn) / +13,9 KB (session), ~1,5 KB mỗi lần. Chưa dọn trong code (nhỏ, tuyến tính).
  Khuyến nghị (DE): TTL theo phiên + dọn checkpoint cũ khi `/finalize`; tuỳ chọn giới hạn retry lỗi mỗi lượt (429)

## Success Criteria
- Overhead graph < 50 ms P50; đọc + ghi checkpoint < 100 ms P95 trên DB đích. Vượt thì báo, không tự nới ngân sách.

## Risk Assessment
- DB đích ở xa (Supabase) chậm hơn local nhiều: đo lại trên staging khi DE dựng xong.

## Security Considerations
- Báo cáo đo không chứa câu trả lời ứng viên.

## Next Steps
- Đóng plan, cập nhật `specs/README.md`.
