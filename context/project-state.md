# Trạng thái dự án (cập nhật 2026-11-03)

## Kế hoạch
- Kế hoạch gốc: `plans/20261019-1100-ai-interview-brd-implementation/` (9 phase). Phase 01–06 xong code và đã merge; Phase 07 (harness, đo LLM thật) xong phần AIE.
- **Giai đoạn tiếp theo:** `context/next-phase-plan.md` (đo chất lượng + làm sạch và tận dụng dữ liệu DE). Phase A xong 02/11 (owner chốt); Phase B đang chờ DE, mốc 09/11, **có nguy cơ trễ**: tính đến 03/11 chưa có tiến triển (PR #49, #50 vẫn draft từ 28/10) và Q1 giấy phép chưa chốt.

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
| #65 | 02/11 | Evaluator v6 cite đáp án chuẩn, siết `supported`, golden thêm nhóm `long_s` |
| #66 | 02/11 | Báo cáo `unscored`, health `degraded`, vá lỗ thoát `<untrusted>`, đo prompt cache |
| #68 | 02/11 | Interviewer v4: khuôn "Bạn có thể" 8.6%, hint đúng hành động 88% (nhãn LLM); ghi nhận Phase A xong |
| #69 | 02/11 | Hạn tổng thời gian mỗi lần gọi LLM, ngân sách retry CV/JD Parser 28 s, Reporter 80 s, stream 15 s |

Quy ước merge của owner: merge commit (không squash). Tiêu đề PR dạng `[scope] type: mô tả`.

## Số đo mới nhất (LLM thật, quick matrix `--serve`, 2026-10-30)
Sau khi sửa ngắt mạch (3 vòng, kể cả tải gấp đôi): RAG `error` 0, phiên mất kho 0/10, TTFT p50 3.57–4.06 s / p95 6.94–7.51 s (**chưa đạt** 3.5 / 6 s), $0.0086–0.0092/phiên. Gộp 5 lần RAG sạch: `no_source` ở `technical` 0.24 (dao động 0.10–0.35), câu kho supported 0.88, câu AI tự đặt 0.63. Chi tiết: `plans/reports/eval-261030-1640-phase-05-baseline.md`.

**TTFT trong các báo cáo trước 30/10 là tổng thời gian lượt**, không so trực tiếp với số trên.

## Đang làm
- Kế hoạch `plans/261029-1415-hybrid-grounded-rag/`: Phase 01–03 xong (`focus_source` để sau), Phase 05 đang làm (đo nền và `judge_support` v2 + repair xong; so nhãn LLM thứ hai đồng ý 0.85, kappa 0.70; `supported` đúng ~0.64, câu AI tự đặt 0.53, dưới ngưỡng 0.80; nhãn người 60 cặp là tùy chọn theo quyết định owner 31/10; golden có tài liệu xong: Evaluator không cite `R` nên `contradicted` qua đáp án chuẩn 0/9, tài liệu không liên quan vẫn `supported` 7/12, cần Evaluator v6), Phase 04 chờ DE.
- Evaluator v5 (nhánh `thang/evaluator-v5`, 31/10): ±1 band 0.963, lệch −0.27, thứ tự 1.0, injection 6/8; so với v4 0.919, −0.467, 0.917, 6/8. Nhồi thuật ngữ a04 đã chặn bằng code (3.1–3.8). Còn lọt injection không từ khóa; mẫu không dấu a10 chưa ổn định. Báo cáo `plans/reports/eval-261031-1456-evaluator-v5.md`.
- Evaluator v6 (PR #65, đã merge 02/11): `R` được cite, `supported` judge 0.964 nhưng recall ~0.58; đạt 4/5 ngưỡng đặt trước, đã qua review độc lập. Lộ lỗi có sẵn trên `main`: `R` chặn điểm oan trên mô phỏng (0/9 đúng), 5/6 ca của v6 từ mục `cr-lz-python-basics-8979143a`, cần DE sửa. Báo cáo `plans/reports/eval-261102-1109-evaluator-v6.md`.
- Tín hiệu lỗi luồng AI (PR #66, đã merge 02/11): báo cáo `unscored` khi không chấm được, bỏ `[Mock]`; `/api/health` có `agents`, staging/production thiếu cấu hình LLM thì không khởi động; `prompt_versions` thật; cờ `reference_missing`. Nguồn: `plans/reports/audit-261102-1539-ai-flow-errors-controls-evaluation.md`.
- Planner ưu tiên topic có câu trong kho (nhánh `thang/planner-bank-coverage`, 03/11, PR đang chờ merge): đếm câu theo topic và độ khó song song với Planner, đổi topic catalog không có câu sang topic cùng nhóm có câu, giữ topic JD; chờ tối đa 1 s sau Planner, lỗi hay chậm thì giữ plan cũ. Đếm trên kho thật (03/11, chỉ đọc, không gọi LLM): truy vấn ~0.2 s; 8 cặp track × level có topic không có câu gần độ khó bắt đầu (nhiều nhất ai_engineer: 4–5 topic mỗi level từ junior; java `java.spring.transaction`; python `celery-queues`, `sqlalchemy-sessions` ở senior); plan dự phòng chỉ đổi java senior 30/45 phút (`spring.transaction` → `jpa-hibernate`). Chưa đo với Planner LLM. Chi tiết: docs 02 mục 3.3.2.
- Vá chống injection và đo prompt cache (PR #66, đã merge 02/11): `wrap_untrusted` escape mọi biến thể thẻ đóng, bỏ ký tự vô hình; `is_manipulation` bắt thêm dạng lách, bỏ bắt nhầm "cho em full quyền...", quét 2 671 câu có sẵn: 470 lượt bắt trước và sau, không thêm không mất; `cached_tokens` trong `metadata.usage`. Đo 10 phiên LLM thật: 63.8% input là cached (docs 08).
- Interviewer v4 (PR #68, đã merge 02/11): khuôn "Bạn có thể" 25.2% → 8.6%, hint đúng hành động 62% → 88%, câu kho giữ 97%; Fable chấm `natural` 3.25 → 3.37, chưa chứng minh được và không thay được người chấm. Báo cáo `plans/reports/eval-261102-1815-interviewer-v4.md`.
- PR #49 (DE duyệt golden RAG): **chưa merge, đang conflict** ở `03-non-functional-requirements.md`; chờ DE duyệt lại g22/g24/h29/h30. Trên `main` chưa query nào có `approved_by`.
- Hạn tổng cho lần gọi LLM (PR #69, đã merge 02/11): `timeout_s` nay cắt thật mỗi lần gọi, quá hạn vào `degraded`/`partial`; thêm ngân sách retry CV/JD Parser 28 s, Reporter 80 s để fallback về trước timeout của interview-service; stream Interviewer có hạn tổng 15 s. Chỉ kiểm bằng test fake, chưa đo LLM thật. Ước tính từ log: ~1.8% lượt Evaluator chuyển thành `degraded` (trước đây các lượt này chờ 8–180 s). Chi tiết: docs 08 §9.3.

## Mốc
Feature freeze 06/12/2026; Sprint 5 07–21/12. Gate voice 22/11. Mốc Evaluator ±1 band ≥ 80% ở tuần 09–15/11.

## Phụ thuộc đang chờ người khác
- **Người chấm:** chỉ có 1 người (nhãn người thứ hai bị loại, PR #46); cần người thứ hai nếu báo cáo cần kappa.
- **DE:** sửa hoặc loại mục kho `cr-lz-python-basics-8979143a` (mô hình thread cũ, nhãn sai); duyệt lại golden RAG (PR #49); quyết định giấy phép (CC-BY-NC-ND, `unknown`); remap topic, nhãn độ khó, câu hard, duyệt bản dịch, textbook (Phase 04); JD (PR #50 draft); xem `context/de-data-assessment.md`.
- **FSD:** `interview-service`, giao diện, TCP `getCvFile`/`getJobDescription`. Từ PR #66 cần xác nhận `interview-service` nhận `overall.score` và `verdict` bằng `null` khi `status = "unscored"`, và lưu rồi gửi lại đầy đủ `evaluation` ở finalize.
- **Owner:** D7–D12 (đặc biệt D8 voice, D12 thời lượng); Q1–Q3 trong `context/next-phase-plan.md` (hạn 27/10, **quá hạn**; Q1 chặn Phase B, lọc giấy phép ở Phase C và Hybrid RAG Phase 04).

## Công cụ chạy thử
`/dev/play` và `evals.play`: xem `context/environment.md`. Sơ đồ ai-service và phiên phỏng vấn: `docs/architecture/diagrams/`.
