# Trạng thái dự án (cập nhật 2026-10-31)

## Kế hoạch
- Kế hoạch gốc: `plans/20261019-1100-ai-interview-brd-implementation/` (9 phase). Phase 01–06 xong code và đã merge; Phase 07 (harness, đo LLM thật) xong phần AIE.
- **Giai đoạn tiếp theo:** `context/next-phase-plan.md` (đo chất lượng + làm sạch và tận dụng dữ liệu DE).

## Đã merge gần đây
| PR | Ngày | Nội dung |
|---|---|---|
| #51 | 29/10 | Interviewer v3: câu ngắn, tự nhiên hơn, hint theo đáp án chuẩn |
| #52 | 29/10 | RAG bật mặc định, tìm kiếm kết hợp BM25 + vector + `topic_id` |
| #53, #54 | 29/10 | Truy hồi theo lượt bằng BM25 cho Evaluator và hint |
| #55 | 29/10 | Evaluator v4 trích nguồn cho từng ý chấm |
| #56 | 29/10 | Tham chiếu nguồn bền, `study_plan.resources` lấy từ chunk được trích |
| #57, #58 | 30/10 | Log JSON có `session_id`, tracing Langfuse có che PII |
| #59 | 30/10 | Một lỗi RAG không còn tắt RAG của mọi phiên; đo nền Phase 05 |

Quy ước merge của owner: merge commit (không squash). Tiêu đề PR dạng `[scope] type: mô tả`.

## Số đo mới nhất (LLM thật, quick matrix `--serve`, 2026-10-30)
Sau khi sửa ngắt mạch (3 vòng, kể cả tải gấp đôi): RAG `error` 0, phiên mất kho 0/10, TTFT p50 3.57–4.06 s / p95 6.94–7.51 s (**chưa đạt** 3.5 / 6 s), $0.0086–0.0092/phiên. Gộp 5 lần RAG sạch: `no_source` ở `technical` 0.24 (dao động 0.10–0.35), câu kho supported 0.88, câu AI tự đặt 0.63. Chi tiết: `plans/reports/eval-261030-1640-phase-05-baseline.md`.

**TTFT trong các báo cáo trước 30/10 là tổng thời gian lượt**, không so trực tiếp với số trên.

## Đang làm
- Kế hoạch `plans/261029-1415-hybrid-grounded-rag/`: Phase 01–03 xong (`focus_source` để sau), Phase 05 đang làm (đo nền xong; còn `judge_support`, phân loại `no_source`, golden có tài liệu cho `contradicted`), Phase 04 chờ DE.
- Evaluator v5 (nhánh `thang/evaluator-v5`, 31/10): ±1 band 0.963, lệch −0.27, thứ tự 1.0, injection 6/8; so với v4 0.919, −0.467, 0.917, 6/8. Nhồi thuật ngữ a04 đã chặn bằng code (3.1–3.8). Còn lọt injection không từ khóa; mẫu không dấu a10 chưa ổn định. Báo cáo `plans/reports/eval-261031-1456-evaluator-v5.md`.
- PR #49 (DE duyệt golden RAG): **chưa merge, đang conflict** ở `03-non-functional-requirements.md`; chờ DE duyệt lại g22/g24/h29/h30. Trên `main` chưa query nào có `approved_by`.

## Mốc
Feature freeze 06/12/2026; Sprint 5 07–21/12. Gate voice 22/11. Mốc Evaluator ±1 band ≥ 80% ở tuần 09–15/11.

## Phụ thuộc đang chờ người khác
- **Người chấm:** chỉ có 1 người (nhãn người thứ hai bị loại, PR #46); cần người thứ hai nếu báo cáo cần kappa.
- **DE:** duyệt lại golden RAG (PR #49); quyết định giấy phép (CC-BY-NC-ND, `unknown`); remap topic, nhãn độ khó, câu hard, duyệt bản dịch, textbook (Phase 04); JD (PR #50 draft); xem `context/de-data-assessment.md`.
- **FSD:** `interview-service`, giao diện, TCP `getCvFile`/`getJobDescription`.
- **Owner:** D7–D12 (đặc biệt D8 voice, D12 thời lượng); Q1–Q3 trong `context/next-phase-plan.md`.

## Công cụ chạy thử
`/dev/play` và `evals.play`: xem `context/environment.md`. Sơ đồ ai-service và phiên phỏng vấn: `docs/architecture/diagrams/`.
