# Phase 05: Đo độ bám nguồn của toàn bộ hệ thống

## Context Links
- [plan.md](plan.md), [phase-03a](phase-03a-evaluator-evidence-contract.md) (`source_ids`, `support`), [phase-03b](phase-03b-report-sources.md) (`Evaluation.sources`)
- Số đo gần nhất: [v3 vs v4](../reports/eval-261029-1757-evaluator-v4-evidence-ab.md), [nhãn người rater A](../reports/eval-261028-2255-golden-rater-a.md), [truy hồi theo lượt](../reports/eval-261029-1722-per-turn-retrieval-ab.md)
- Code đo: `evals/run_evaluator.py`, `evals/sim_metrics.py` (`grounding`), `evals/simulate.py`, `evals/run_rag.py`, `evals/judge_interviewer.py` (mẫu judge + hiệu chỉnh), `evals/label_sheet.py`
- Quy tắc judge: `context/quality-criteria.md`; khung đo: `docs/ai-service/09` mục 10

## Overview
- Priority P1. Trạng thái: **đang làm**. Đo nền xong: [báo cáo](../reports/eval-261030-1640-phase-05-baseline.md).
- Phase 03 đảm bảo được id nguồn có thật, **chưa đảm bảo nguồn nói đúng điều được gán cho nó**: code chỉ kiểm id, không kiểm
  nội dung. Một ý `supported` có thể trích chunk không liên quan mà không ai biết.
- Phase này trả lời 3 câu, kết quả dùng để chốt câu hỏi mở số 4 của plan và độ khắt của v4:
  1. Ý `supported` có thật sự được tài liệu ủng hộ không?
  2. Ý `no_source` là do kho không có tài liệu, do truy hồi không lấy ra, hay do LLM không trích? (gộp 5 lần RAG sạch:
     0.24 ở `technical`; `intro` + `scenario` không có tài liệu; cần phân loại ý ở `technical`)
  3. Nhánh `contradicted` có chạy đúng không? (có chạy: 2 ý ở đo nền, 1 ý theo `R`; 1 trong 2 chặn điểm oan trên tài liệu cũ)

## Key Insights
- **Mốc 53% `no_source` sai:** lần đó 35/98 lượt RAG lỗi. Gộp 5 lần sạch (345 ý): 0.24 ở `technical`, dao động 0.10–0.35 giữa
  các lần dù tài liệu và prompt không đổi. Không kết luận từ một lần chạy.
- **Một timeout từng tắt RAG của mọi phiên 60 giây** (8/12 lần chạy có RAG lỗi). Đã sửa 30/10: 0 lỗi qua 3 vòng, kể cả tải gấp
  đôi. Lần chạy có `rag_health.error > 0` không dùng làm mốc.
- **TTFT báo cáo trước là tổng thời gian lượt** (ASGI in-process đệm body). Đo TTFT phải dùng `--serve` hoặc `--base-url`.
- **`evidence` không có ý `contradicted`:** `postcheck` bỏ chúng khỏi covered. Đếm qua `sources` (cận dưới) hoặc log
  `evaluator_sources`; golden có tài liệu đo qua `evaluate_with_raw`. Mọi số "0 contradicted" trước đây là sai.
- **Đã có nhãn người cho điểm:** `evaluator_labels/final.json` 43/48 mẫu (1 người chấm, không có kappa). Chưa có nhãn cho
  **nguồn**: golden không có tài liệu đối chiếu, nên `supported` / `contradicted` chưa từng được so với người.
- **Ngưỡng 0.93 của plan không ổn định:** v3 tự dao động 0.919–0.930 giữa hai vòng, chênh v3 / v4 nằm trong nhiễu. Ngưỡng
  bắt buộc của dự án là ≥ 0.80 (S3-AIE-4). Đổi thành so cùng lúc với v3 (xem Success Criteria).
- **v4 khắt hơn có hệ thống:** leniency −0.47, ngoài dải [−0.3, +0.3]. Riêng strong đã lệch −0.88 từ v3.
- `Evaluation.sources` map `S1..` / `R` → `ref` bền, nên file JSON mô phỏng + `get_pair_by_qa_id` đủ dựng cặp (ý, chunk) cho
  ý **đã trích**. Chunk **không được trích** trong lượt thì không có trong response: câu hỏi 2 cần ghi thêm ở harness.
- Mô phỏng đã có `turn_kind`, `question_source`, `qa_id`, nên tách `no_source` theo loại lượt không tốn LLM.
- Judge cùng họ model với agent nên có thể thiên vị: chưa hiệu chỉnh với nhãn người thì **không dùng làm số đo**.

## Requirements
- Chạy lại được bằng một lệnh, kết quả ghi vào `plans/reports/`, JSON gitignored.
- Không đổi hành vi service; mọi thay đổi nằm trong `evals/` (trừ khi kết quả dẫn tới quyết định riêng).
- Nhãn người nhập qua phiếu CSV kiểu `label_sheet` (ẩn nhãn của model để tránh mồi).

## Architecture

```
simulate --serve (quick matrix, LLM)  ──► eval-sim-05-*.json, mỗi lượt có `documents` (mọi tài liệu Evaluator thấy)
        │
        ├─► grounding_breakdown: supported / no_source theo phase, turn_kind, nguồn câu hỏi       (không LLM)
        ├─► judge_support: (ý, quote, chunk) → entailed | contradicted | unrelated                 (LLM)
        │       └─ hiệu chỉnh với 60 cặp nhãn người: chỉ báo số khi đồng ý ≥ 0.8
        └─► no_source triage: có chunk trong lượt ủng hộ ý không → lỗi trích | lỗi truy hồi | kho thiếu

golden có tài liệu (20 mẫu, có câu sai cố ý) ──► run_evaluator: support của v4 so với nhãn người
```

## Related Code Files
- **Đã có:** `evals/turn_source_recorder.py` (bọc `get_evaluator`, ghi `documents`), `evals/simulate.py` (`--serve`),
  `evals/sim_metrics.py` (`grounding_breakdown`, `rag_health`), `tests/test_grounding_breakdown.py`
- **Tạo:** `evals/judge_support.py`, `evals/prompts/judge_support.v1.md`, `evals/support_set.py` (dựng cặp, xuất / nhập phiếu),
  `evals/support_labels/`, `evals/evaluator_golden_sourced.jsonl`, `tests/test_support_metrics.py`
- **Sửa:** `evals/run_evaluator.py` (chỉ số support, nhận mẫu có tài liệu)
- **Docs:** `docs/ai-service/09` mục 10 (chỉ số mới; sửa dòng "0/48 nhãn người" đã cũ ở mục 10.2)

## Implementation Steps
1. **Đo nền (xong):** quick matrix × 2 vòng với `--serve`; `grounding` theo `phase`, `turn_kind`, `question_source`; TTFT thật;
   chi phí phiên; `run_rag` held-out.
2. **Judge độ hỗ trợ:** `judge_support` nhận `point`, `quote`, nội dung chunk (bọc untrusted), trả nhãn + lý do ngắn. Chạy trên
   mọi ý có `source_ids`.
3. **Phiếu nhãn người:** chọn 60 cặp phân tầng (45 `supported`, 15 `no_source` ở `technical` ghép chunk tốt nhất trong lượt),
   xuất CSV.
   Owner / DE chấm rồi nhập lại. Tính đồng ý judge – người.
4. **Phân loại `no_source` ở `technical`** (đã có 60 ý có tài liệu trong 3 vòng `eval-sim-05-breaker-*`): với mỗi ý, judge dò
   `documents` của lượt.
   - Có chunk ủng hộ → **lỗi trích** (sửa prompt).
   - Không có, nhưng tìm toàn kho (BM25 theo ý) thì có → **lỗi truy hồi** (sửa truy vấn).
   - Toàn kho không có → **kho thiếu** (việc của Phase 04).
5. **Golden có tài liệu:** 20 mẫu có tài liệu + nhãn người: ~10 ủng hộ, ~6 câu trả lời sai ngược tài liệu (có `R` và chỉ có
   snippet), ~4 tài liệu không liên quan. Đo precision / recall của `supported`, `contradicted`.
6. **Tổng hợp:** báo cáo `eval-*-phase-05-grounding.md` kèm đề xuất cho câu hỏi mở số 4 và độ khắt của v4.

## Todo List
- [x] Ghi tài liệu theo lượt trong harness, breakdown `grounding`, `rag_health`, `--serve`
- [x] Đo nền trên main (bước 1)
- [x] `judge_support` + prompt v2 + repair + test (`evals/judge_support.py`; hiệu chỉnh với nhãn LLM 0.85 / 0.70, chưa với người)
- [ ] Phiếu 60 cặp đã xuất (`evals/support_set.py`), chờ nhãn người
- [ ] Hiệu chỉnh judge với nhãn người
- [x] Phân loại `no_source` (tạm, chờ hiệu chỉnh: `eval-261031-1700-judge-support.md`)
- [ ] Golden có tài liệu 20 mẫu, chờ nhãn người; chỉ số support trong `run_evaluator`
- [ ] Báo cáo, cập nhật `docs/ai-service/09`, review độc lập

## Success Criteria
Ngưỡng dưới đây là **đề xuất, chờ owner chốt**.

| Chỉ số | Hiện có | Ngưỡng |
|---|---|---|
| Id nguồn LLM ghi hợp lệ (mô phỏng) | 0.91–0.94 (id bịa bị code bỏ, không lọt ra) | ≥ 95% |
| RAG lỗi trong lần đo | 0 / 318 (3 vòng sau khi sửa) | 0 (không thì lần đo không dùng làm mốc) |
| Precision của `supported` (theo judge đã hiệu chỉnh) | chưa đo | ≥ 0.80 |
| Đồng ý judge – người | chưa đo | ≥ 0.80 thì mới dùng số của judge |
| Recall của `contradicted` trên golden có tài liệu | chưa đo | ≥ 0.70 |
| Precision của `contradicted` (bác oan chặn điểm) | chưa đo | ≥ 0.90 |
| `no_source` ở `technical`, gộp ≥ 150 ý | 0.243 (345 ý) | Chưa đặt tới khi phân loại xong (không tính toàn phiên: intro + scenario không có tài liệu) |
| Evaluator ±1 band | 0.919–0.922 | ≥ 0.90 và không thấp hơn v3 quá 0.02 khi chạy **cùng lúc** (thay cho 0.93) |
| Leniency bias | −0.47 | Trong [−0.3, +0.3], hoặc owner chấp nhận khắt hơn |
| TTFT p50 / p95 (qua socket, bỏ lượt không có token) | 3.6–4.1 s / 6.0–7.5 s | ≤ 3.5 s / ≤ 6 s (mục tiêu theo dõi, không chặn) |
| Chi phí phiên | $0.0083–0.0092 | < $0.10 |
| MRR held-out | 0.82–0.84 (~0.86 nếu bỏ 2 truy vấn timeout), Phase 01: 0.875 | Không tụt, đo khi không có timeout |

Xong phase khi 3 câu hỏi ở Overview có câu trả lời bằng số và owner chốt được câu hỏi mở số 4.

## Risk Assessment
- **RAG sập giữa lần đo:** kiểm `rag_health` trước khi đọc số; có `error` thì chạy lại.
- **Chờ nhãn người lâu:** bước 1, 2, 4 không phụ thuộc; bước 3 và 5 có thể chậm. Báo số thô của judge kèm ghi rõ chưa hiệu chỉnh.
- **Mẫu nhỏ:** 10 phiên chỉ ~70 ý mỗi lần; 2 vòng cho ~150 ý. Dao động ±0.05 là bình thường, không kết luận từ chênh nhỏ.
- **Một người chấm:** không có trần đồng ý người – người. Nếu được, nhờ DE chấm chéo 20 cặp.
- **Prompt chạy lại đổi kết quả:** ghi `prompt_version` + model trong báo cáo, so sánh luôn chạy cùng lúc.
- Mô phỏng khác người thật: `no_source` trên traffic thật có thể khác. Có Langfuse thì lấy mẫu phiên thật ở vòng sau.

## Security Considerations
- Chunk và câu trả lời vào judge đều bọc `wrap_untrusted`, kể cả chunk của DE.
- Phiếu nhãn là dữ liệu mô phỏng, không dùng phiên thật của ứng viên. `documents` nằm trong JSON báo cáo (gitignored).

## Next Steps
- Quyết định chính sách câu không có nguồn (câu hỏi mở số 4), hiệu chỉnh độ khắt của v4.
- Lỗi trích → prompt v5; lỗi truy hồi → sửa truy vấn theo lượt; kho thiếu → danh sách gửi DE cho Phase 04.
- Sau khi có traffic thật: chấm mẫu trace Langfuse bằng `judge_support`, ghi vào score của Langfuse.

## Unresolved Questions
1. Ai chấm 80 mẫu nhãn người (60 cặp + 20 golden), DE hay owner? Có chấm chéo không?
2. Ngưỡng Success Criteria có chốt như trên không, nhất là thay 0.93 bằng so cùng lúc với v3?
3. Nếu v4 vẫn khắt hơn sau đo: sửa prompt hay chấp nhận?
