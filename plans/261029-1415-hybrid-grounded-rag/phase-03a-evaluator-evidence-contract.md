# Phase 03a: Hợp đồng trích nguồn cho Evaluator

## Context Links
- [plan.md](plan.md) (Phase 03 tách 03a lõi Evaluator, 03b Interviewer `focus_source` + Reporter trích nguồn)
- [phase-02](phase-02-per-turn-retrieval.md): chunk theo lượt nối sau `reference_snippets` của topic
- Code: `app/agents/evaluator.py`, `app/evaluation_checks.py`, `app/prompts/evaluator.v3.md`, `evals/run_evaluator.py`
- Rubric, luật khắt khe: `docs/ai-service/05-rubric-and-final-report.md` mục 6; đo: `docs/ai-service/09` mục 10

## Overview
- Priority P1. Trạng thái: **xong**, merge PR #55.
- Hiện nay Evaluator nhận snippet + đáp án chuẩn làm tài liệu đối chiếu nhưng không nói mình dựa vào tài liệu nào; code
  chỉ kiểm quote nằm trong câu trả lời. Không biết điểm có bám tài liệu (DE đã duyệt) hay dựa kiến thức của model.
- Phase này: mỗi ý `covered` ghi `source_ids` (tài liệu nào) + `support`; code hậu kiểm id; đo tỉ lệ bám nguồn.

## Quyết định
- **Id theo vị trí trong lượt:** `S1..Sn` (snippet topic trước, chunk theo lượt sau, đúng thứ tự gửi), `R` cho
  `reference_answer`. Không đổi plan / contract snippet (vẫn là chuỗi). Id bền qua lượt (cho Reporter) để 03b.
- **Schema v4:** `covered[]` thêm `source_ids: [str]`, `support: supported | contradicted | no_source`.
  - `supported`: tài liệu nói cùng ý với ứng viên. `contradicted`: tài liệu nói ngược. `no_source`: không có tài liệu
    nào nói về ý đó.
- **Hậu kiểm bằng code** (`app/evaluator_source_checks.py`):
  - Bỏ id không có trong lượt; `supported` / `contradicted` mà không còn id hợp lệ thì thành `no_source`.
  - Lượt không có tài liệu nào thì mọi ý là `no_source`.
  - `contradicted` (có id hợp lệ): ý không được tính covered. Chỉ khi `R` bác bỏ mới thêm vào `misconceptions` → luật 4
    (`technical_accuracy ≤ 1`): snippet / chunk BM25 chỉ gần đúng chủ đề, một chunk lệch không đủ để chặn điểm (review).
    LLM vẫn tự ghi hiểu sai vào `misconceptions` (quote sai làm rơi ý thì không mất); code đặt ý đã kiểm lên đầu, bỏ trùng.
  - Ý `contradicted`: `point` ghi điều ứng viên nói, không chép key point (tránh báo câu đúng là hiểu sai).
  - `EVALUATOR_PROMPT_VERSION` sai → Evaluator heuristic `degraded`, không trả 500.
- **Độ tin cậy:** `Evaluation.confidence = low` khi có tài liệu nhưng không ý `covered` nào `supported` (điểm không
  bám nguồn), `high` khi có ý `supported`, `null` khi không tài liệu / không ý nào / v3 / mock. Không hạ điểm vì
  `no_source`: thiếu tài liệu không có nghĩa ứng viên sai.
- `Evidence` thêm `source_ids`, `support` (mặc định rỗng / `no_source`): chỉ bổ sung, client cũ không vỡ.
- Prompt v4 = v3 + mô tả id + luật trích nguồn. v3 giữ nguyên (không đánh id) để A/B: `EVALUATOR_PROMPT_VERSION=v3`.

## Related Code Files
- **Tạo:** `app/prompts/evaluator.v4.md`, `app/evaluator_source_checks.py`, `tests/test_evaluator_source_checks.py`
- **Sửa:** `app/agents/evaluator.py` (schema theo version, đánh id, postcheck), `app/agents/evaluator_provider.py`
  (`EVALUATOR_PROMPT_VERSION`), `app/models_interview.py` (`Evidence`, `Evaluation.confidence`),
  `evals/run_evaluator.py` (tỉ lệ id hợp lệ, phân bố `support`)
- **Docs:** `docs/ai-service/05` (luật hậu kiểm), `06-api-contract.md` (trường mới), `09` (chỉ số), `.env.example`

## Todo List
- [x] Prompt v4 + schema + đánh id
- [x] Hậu kiểm nguồn + `confidence`
- [x] Test: id lạ bị bỏ, không tài liệu → no_source, contradicted → misconception, v3 không đổi
- [x] Đo golden v3 vs v4 ([báo cáo](../reports/eval-261029-1757-evaluator-v4-evidence-ab.md)): agreement 0.919 = v3
  (v3 dao động 0.919–0.930), v4 khắt hơn (leniency −0.47 so với −0.37), 0 id bịa
- [x] Đo mô phỏng: supported 0.47 / contradicted 0 / no_source 0.53; Evaluator +0.3–0.4 s (vào thẳng TTFT)
- [x] Docs, review độc lập (sửa: chỉ `R` bác bỏ mới chặn điểm, point của ý contradicted, gộp misconceptions, version sai không 500)
- [x] Chốt v4 mặc định (owner), owner test

## Success Criteria
- Agreement ±1 band trên golden ≥ 0.93 và không thấp hơn v3.
- ≥ 95% `source_ids` LLM trả về là id có thật.
- Evaluator p95 không tăng quá 0.5 s (output dài hơn).

## Risk Assessment
- **LLM gán `contradicted` sai** → điểm accuracy bị chặn oan. Giảm: bắt buộc id hợp lệ; đo tỉ lệ contradicted.
- **Output dài hơn** → Evaluator chậm, tốn token. Giảm: `source_ids` ngắn (`S1`), không bắt trích quote từ tài liệu.
- Golden set không có snippet → chỉ đo được độ lệch điểm; tỉ lệ bám nguồn đo trên mô phỏng.

## Security Considerations
- Snippet vẫn bọc `<untrusted>`; id do code gán, không lấy từ nội dung chunk.

## Next Steps
- 03b: id bền cho chunk trong plan, Interviewer `focus_source`, Reporter trích lượt + chunk.
