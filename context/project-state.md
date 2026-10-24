# Trạng thái dự án (cập nhật 2026-10-24)

## Kế hoạch
- Kế hoạch gốc: `plans/20261019-1100-ai-interview-brd-implementation/` (9 phase). Phase 01–06 xong code và đã merge; Phase 07 (harness, đo LLM thật) xong phần AIE.
- **Giai đoạn tiếp theo:** `context/next-phase-plan.md` (đo chất lượng + làm sạch và tận dụng dữ liệu DE).

## Đã merge gần đây (2026-10-24)
| PR | Nội dung |
|---|---|
| #33–#35 | Bật RAG trên ai_db dùng chung, cải tiến RAG, LLM viết lại truy vấn tiếng Việt (ADR-010) |
| #36 | `evals/play.py`: tự phỏng vấn thử trong terminal |
| #37 | Trang dev `/dev/play` (đóng vai interview-service) + bảng "Luồng hệ thống" |
| #38 | Đo và chặn sai ngôn ngữ đầu ra (tiếng Việt giữ thuật ngữ Anh) |
| #39 | Câu hỏi chính technical lấy từ kho `interview_qa`, Evaluator chấm theo đáp án chuẩn (`RAG_QUESTION_BANK`) |

Quy ước merge của owner: merge commit (không squash). Tiêu đề PR dạng `[scope] type: mô tả`.

## Số đo mới nhất (harness full, LLM thật, 2026-10-24)
TTFT P50 3.8 s / P95 6.0 s; $0.008/phiên; fallback 0; lặp câu 0; sai ngôn ngữ 0; câu technical từ kho 72/72; thứ tự strong > average > weak 5/8 (trước khi dùng kho: 8/8). Chi tiết: `plans/reports/eval-261024-1614-rag-question-bank.md`.

## Đang làm
Phase A (`context/next-phase-plan.md`): chỉ số văn phong trong harness, bộ 60 câu hỏi + phiếu người chấm, LLM-judge Interviewer (nhánh `thang/phase-a-question-quality`). Chờ 2 người chấm: phiếu `plans/reports/question-rating-sheet-261024.csv` và golden set Evaluator.

## Mốc
Feature freeze 06/12/2026; Sprint 5 07–21/12. Gate voice 22/11. Mốc Evaluator ±1 band ≥ 80% ở tuần 09–15/11.

## Phụ thuộc đang chờ người khác
- **Người chấm:** golden set Evaluator (48 mẫu, 0 nhãn) và bộ câu hỏi mới; xem `context/quality-criteria.md`.
- **DE:** duyệt golden set RAG; quyết định giấy phép (CC-BY-NC-ND, `unknown`); remap topic, nhãn độ khó, câu hard, duyệt bản dịch; JD (spec 009 Draft); xem `context/de-data-assessment.md`.
- **FSD:** `interview-service`, giao diện, TCP `getCvFile`/`getJobDescription`.
- **Owner:** D7–D12 (đặc biệt D8 voice, D12 thời lượng); Q1–Q3 trong `context/next-phase-plan.md`.

## Công cụ chạy thử
`/dev/play` và `evals.play`: xem `context/environment.md`. Sơ đồ luồng ai-service (archify): `.archify/` (cục bộ, không commit).
