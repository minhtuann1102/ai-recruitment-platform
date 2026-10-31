# Golden có tài liệu: Evaluator v5 gán `support` đúng không (2026-10-31)

Phase 05 bước 5. 20 mẫu tự viết ở `evals/evaluator_golden_sourced.jsonl` (tài liệu do AIE viết, không dùng dữ liệu DE): 10 `supported` (trả lời đúng, tài liệu nói cùng ý), 6 `contradicted` (trả lời sai, tài liệu nói ngược: 3 qua đáp án chuẩn `R`, 3 chỉ qua snippet `S`), 4 `no_source` (trả lời đúng, tài liệu cùng chủ đề nhưng không nói ý đó). Nhãn là ý đồ của người viết mẫu, không phải người chấm độc lập. 3 lần chạy, gpt-4o-mini, Evaluator v5, đo output thô trước hậu kiểm (`evaluate_with_raw`).

Lệnh: `python -m evals.run_evaluator_sourced --runs 3 --out ../../plans/reports/eval-evaluator-sourced-261031.json`

## Kết quả (60 lượt = 20 mẫu × 3)

| Nhãn kỳ vọng → quan sát | Số lượt |
|---|---|
| supported → supported | 30 / 30 |
| contradicted → contradicted | 9 / 18 |
| contradicted → no_source | 9 / 18 |
| no_source → no_source | 5 / 12 |
| no_source → supported | 7 / 12 |

| Nhãn | Precision | Recall |
|---|---|---|
| `supported` | 0.81 | 1.00 |
| `contradicted` | 1.00 | 0.50 |
| `no_source` | 0.36 | 0.42 |

- `contradicted` theo loại tài liệu: qua `S` **3/3 mẫu, 9/9 lượt**; qua `R` **0/9 lượt**.
- Câu trả lời sai (6 mẫu): `technical_accuracy` trung bình 1.0, 100% lượt có `misconceptions`. Id bịa: 0.

## Đọc kết quả
1. **Không cite `R`.** Với 3 mẫu đáp án chuẩn bác bỏ, model ghi đúng `support: contradicted` và nêu đúng điều ứng viên nói sai, nhưng `source_ids` để rỗng cả 9/9 lượt, nên `check_sources` hạ xuống `no_source`. Hậu quả: `refuted_by_reference` không bao giờ kích hoạt, nên luật "R bác bỏ thì chặn `technical_accuracy`" trong `postcheck` chưa từng chạy trong thực tế. Điểm vẫn thấp (1.0) là nhờ model tự chấm và tự ghi `misconceptions`, không nhờ cơ chế trích nguồn. Prompt luật 12 chỉ nói "id các tài liệu", chưa nói rõ `R` cũng là id phải ghi.
2. **Tài liệu không liên quan vẫn được cite `supported`:** 7/12 lượt. Ví dụ tài liệu về npm được cite cho ý "I/O giao cho libuv"; tài liệu về cache cấp hai của Hibernate được cite cho ý N+1. Đây đúng là lỗi `judge_support` đo được trên mô phỏng (`supported` đúng 0.64). Hai cách đo độc lập cho cùng kết luận: Evaluator v5 coi "cùng chủ đề" là "ủng hộ".
3. **`contradicted` qua `S` hoạt động tốt** (9/9) và không có false positive (precision 1.0). Khi tài liệu nói ngược thẳng, model nhận ra.
4. **Giới hạn:** 20 mẫu tự viết, tài liệu ngắn và sạch hơn chunk thật; nhãn do người viết mẫu đặt. Số này nói về hành vi của prompt, không phải tỉ lệ trong phiên thật.

## Đề xuất cho Evaluator v6
- Luật 12: nói rõ `R` là một id, ý bị `reference_answer` bác bỏ phải ghi `source_ids: ["R"]`. Đo lại bằng chính bộ này: kỳ vọng `contradicted` qua `R` từ 0 lên gần 9/9.
- Thêm vào luật 12 điều kiện cho `supported`: tài liệu phải nói về **đúng ý đó**, cùng chủ đề chưa đủ; kèm một ví dụ âm. Đo bằng bộ này (no_source → supported, hiện 7/12) và `judge_support` trên mô phỏng.
- Giữ bộ golden này làm hồi quy cho mọi lần đổi prompt Evaluator, chạy cùng `run_evaluator`.

## Câu hỏi còn mở
- Thiết kế hiện tại để ý `contradicted` nằm trong `covered` rồi hậu kiểm bỏ ra. Có nên tách thành trường riêng (`refuted`) để model không phải nhồi ý sai vào danh sách "ý đã nêu đúng"?
