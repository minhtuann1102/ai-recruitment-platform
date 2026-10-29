# Phase 03b: Tham chiếu bền vững và tài liệu trong báo cáo

## Context Links
- [plan.md](plan.md), [phase-03a](phase-03a-evaluator-evidence-contract.md) (id `S1..`/`R` chỉ có nghĩa trong lượt)
- Code: `app/source_refs.py`, `app/report_resources.py`, `app/agents/reporter.py`, `app/agents/evaluator.py`
- Contract báo cáo: `docs/ai-service/05-rubric-and-final-report.md` mục 6.4 (`resources` = `{title, url}`, URL do code
  tra, Reporter không viết URL)

## Overview
- Priority P2. Trạng thái: **đang làm** (nhánh `thang/report-sources`).
- 03a: Evaluator trích `S1`, `R`... nhưng id theo vị trí trong lượt, lúc finalize không biết là tài liệu nào;
  `study_plan.resources` luôn rỗng.
- 03b: mỗi chunk có tham chiếu bền (`ref` = `qa_id` / id chunk, `title` = dòng đầu, `url` = `metadata.source_url` của
  DE); Evaluation lưu nguồn đã trích; báo cáo lấy tài liệu cho `study_plan` từ đó.

## Quyết định (owner chốt 29/10)
- **Resources = câu Q&A của DE đã được Evaluator trích** ở các lượt của topic: `title` là câu hỏi, `url` là
  `source_url` (88 link, phần lớn README GitHub tổng hợp câu hỏi; 97% cặp có link). Kho chưa có textbook, catalog chưa
  có `resources`.
- **`focus_source` của Interviewer để sau**: `missing_points` chưa gắn id nguồn, giá trị thấp so với chi phí.
- Thứ tự: nguồn bác bỏ ý ứng viên (`contradicted`) trước, rồi nguồn ủng hộ, theo thứ tự lượt; bỏ trùng theo `ref`;
  tối đa 3 mỗi mục. **Còn thiếu thì bù bằng `reference_sources` của topic** (owner chốt sau đo: không bù thì ứng viên
  yếu, nhóm cần tài liệu nhất, gần như không có).
- `SourceRef` tự kiểm `url` (chỉ `http(s)`) và cắt `title` ở model: plan / evaluation do interview-service gửi lại.
- Reporter LLM chỉ chọn `resource_ids` (`r1..`) trong `input.resources` (gửi id + `topic_id` + `title`, không gửi URL);
  code đổi id ra `{title, url}`, id lạ bị bỏ. Báo cáo mock lấy thẳng 3 nguồn đầu của topic yếu.
- URL chỉ giữ dạng `http(s)://`; tiêu đề bỏ ký hiệu markdown, ≤ 150 ký tự.
- Trường mới chỉ bổ sung: `PlanTopic.reference_sources`, `Evaluation.sources`. Thiếu (plan cũ, interview-service bỏ
  trường) thì id vẫn hợp lệ nhưng không có tham chiếu, bỏ qua.
- Đáp án chuẩn `R`: `ref` = `qa_id`, `title` = câu hỏi trong `bank_questions`, chưa có `url` (cache đáp án chỉ giữ nội
  dung).

## Related Code Files
- **Tạo:** `app/source_refs.py`, `app/report_resources.py`, `app/prompts/reporter.v2.md`, `tests/test_report_sources.py`
- **Sửa:** `app/rag/models.py`, `app/rag/repository.py` (`source_url`), `app/rag/retriever.py` (`plan_snippets` trả
  chunk), `app/plan_snippets.py`, `app/turn_reference_snippets.py`, `app/turn_engine.py`, `app/agents/evaluator.py`,
  `app/evaluation_checks.py`, `app/models_interview.py`, `app/report_scoring.py`, `app/agents/reporter.py`
- **Docs:** `05`, `06-api-contract.md`, `02` (input Reporter)

## Todo List
- [x] `source_url` trong chunk, `SourceRef`, plan + chunk theo lượt mang tham chiếu
- [x] `Evaluation.sources` (id đã trích → ref bền, contradicted trước)
- [x] `study_plan.resources` (mock + Reporter v2 chọn id)
- [x] Test: tiêu đề / URL an toàn, thứ tự, bỏ trùng, id lạ, không gửi URL cho LLM
- [x] Mô phỏng lần 1: 10/28 mục có tài liệu; Reporter chọn đúng 100% khi topic có nguồn; 5/10 phiên (yếu, trung bình) không có → thêm bù
- [x] Mô phỏng lần 2 (có bù): 22/25 mục có tài liệu (3 mục trống là intro / scenario, không có Q&A), 33 link, 0/10 phiên
  trống, Reporter không lỗi. TTFT p95 7.84 s do Evaluator p95 8.5 s cùng lượt (LLM chậm; 03b không đổi đường lượt)
- [x] Docs, review độc lập (sửa: kiểm url ở model, id không phân biệt hoa thường, test thứ tự nhiều chunk)
- [ ] Owner test

## Success Criteria
- Mục `study_plan` của topic có lượt trích nguồn thì có ≥ 1 tài liệu; mọi URL lấy từ metadata DE.
- Không thay đổi điểm; Reporter không lỗi thêm.

## Risk Assessment
- Link là README GitHub tổng hợp câu hỏi, không phải tài liệu chính thức: chấp nhận tới khi DE bổ sung catalog
  `resources` / textbook (Phase 04).
- Plan và Evaluation to hơn (~3 tham chiếu mỗi topic / lượt): nhỏ so với snippet.

## Security Considerations
- URL không bao giờ từ LLM; chỉ `http(s)` từ metadata DE. Tiêu đề là dữ liệu DE, vẫn qua `wrap_untrusted` khi vào prompt.

## Next Steps
- Phase 04 (DE): catalog `resources`, textbook; khi có thì thêm nguồn đó vào `resource_catalog`.
- `focus_source` (để sau).
