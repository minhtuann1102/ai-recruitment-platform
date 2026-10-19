# Phase 06. Interviewer, Reporter, orchestrator và độ bền

## Context Links
- [plan.md](plan.md) · [design 03](../../docs/ai-service/03-orchestrator-state-machine.md) · [design 04](../../docs/ai-service/04-adaptive-loop-and-candidate-state.md) · [design 05 §6.3–6.4](../../docs/ai-service/05-rubric-and-final-report.md) · FR-AI-035–039, 052–056, 070–072, 091

## Overview
- **Priority:** P1 · **Status:** chưa bắt đầu · **Tuần:** W4–W6
- Interviewer LLM stream, Reporter LLM, hoàn thiện luật orchestrator và toàn bộ nhánh lỗi/fallback.

## Key Insights
- Policy và tính điểm là code thuần đã có test (mock); Interviewer chỉ **diễn đạt**, Reporter chỉ **viết lời**.
- Câu hỏi sinh ra phải đọc tự nhiên được (không markdown, ngắn): làm sẵn cho TTS của voice tùy chọn A mà không tốn thêm.
- Mock còn thiếu: hạn cứng +3 phút, ngân sách phase/topic, mượn thời gian, hai `dont_know` liên tiếp đóng topic, `replace` event, chống lặp câu.

## Requirements
- FR-AI-035/036 (giới hạn cứng, chuyển phase, wrap-up), 037 (một câu hỏi, không lộ điểm), 038 (Jaccard ≥ 0.8 sinh lại một lần), 039 (`meta/token/done/replace/error`), 052–055 (Reporter, link từ catalog, partial), **056 `requirements` (S3-AIE-6)**, 070–072, 091 (`X-Internal-Token`).
- NFR: PERF01–05, REL01–04/09, QUAL11–13, SEC01, USE01.

## Architecture
```
next-turn: Evaluator → hậu kiểm → cập nhật state → policy (code) → Interviewer (stream)
                lỗi→ degraded       lỗi trước token → backup_question; giữa stream → event replace
finalize : code tính điểm → Reporter (JSON) → kiểm evidence_turns, tra link catalog → report | partial
```

## Related Code Files
- **Tạo:** `app/agents/{interviewer,reporter}.py`, `app/prompts/{interviewer,reporter}.v1.md`, `app/time_budget.py` (ngân sách phase/topic, mượn thời gian), `app/requirements_coverage.py`, `app/security.py` (`X-Internal-Token`), `tests/test_time_budget.py`, `tests/test_resilience.py`.
- **Sửa:** `app/turn_engine.py` (tách module < 200 dòng: transition, state update), `app/policy.py`, `app/sse.py` (`replace`), `app/report_scoring.py`, `app/main.py`.

## Implementation Steps
1. Hoàn thiện `time_budget` và điều kiện chuyển trạng thái theo design 03 §4.4; test biên (đúng giới hạn follow-up, hết giờ, độ khó chạm min/max).
2. Interviewer LLM stream từng token; lỗi trước token → `backup_question`; lỗi giữa stream → `replace`; chống lặp.
3. Reporter LLM nhận kết quả đã qua Evaluator (không nhận nguyên văn); kiểm `evidence_turns` tồn tại; link chỉ tra từ catalog; lỗi → `status = partial`.
4. Khối `requirements` cho JD: mỗi yêu cầu `assessed | not_assessed | out_of_catalog` kèm band, evidence_turns, confidence; không coi "chưa hỏi" là "yếu"; không kết luận tuyển hay không.
5. Lỗi Evaluator → `degraded` (loại khỏi điểm, hạ `confidence`); đánh dấu mọi fallback trong `metadata.fallbacks`.
6. Middleware `X-Internal-Token` (trừ `/api/health`).

## Todo List
- [ ] time_budget + điều kiện chuyển phase, test biên
- [ ] Interviewer stream + fallback + replace + chống lặp
- [ ] Reporter + partial + evidence kiểm
- [ ] Khối `requirements`
- [ ] Nhánh lỗi có test; token nội bộ

## Success Criteria
- 0 phiên vượt giới hạn cứng (test biên); mọi nhánh trong bảng lỗi design 03 §4.6 có test; fallback < 2% và lỗi format < 1% trong phiên giả lập; unit test orchestrator ≥ 90% nhánh.

## Risk Assessment
- Evaluator rồi Interviewer nối tiếp chậm → đo từ Phase 07; phương án design 08 §9.2 (Evaluator gọn, model nhanh hơn, tách Evaluator hai pha).
- Reporter bịa → chặn bằng kiểm `evidence_turns` và link từ catalog.

## Security Considerations
- Token nội bộ so sánh hằng thời gian; Reporter không nhận nguyên văn câu trả lời (giảm đường injection); không log nội dung.

## Next Steps
Phase 07 khóa contract và đo; Phase 09 tinh chỉnh prompt.
