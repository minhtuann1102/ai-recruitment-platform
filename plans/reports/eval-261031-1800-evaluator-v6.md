# Evaluator v6: cite đáp án chuẩn `R`, siết `supported` (2026-10-31)

Sửa hai lỗi mà golden có tài liệu (`eval-261031-1730-evaluator-sourced-golden.md`) chỉ ra. gpt-4o-mini qua OpenRouter, 3 lần chạy mỗi bộ, v5 và v6 đo cùng buổi.

## Thay đổi (`app/prompts/evaluator.v6.md`, luật 12)
- Khi có `reference_answer`, `R` là một id: ý được đáp án chuẩn xác nhận hay bác bỏ phải ghi `"R"` vào `source_ids`.
- `supported` chỉ khi tài liệu nói về đúng ý đó; cùng chủ đề chưa đủ; hai ví dụ âm (npm vs libuv, cache cấp hai vs N+1).
- `evals/run_evaluator`: thêm `invented_source_id_values` để thấy id bịa là gì.

## Golden có tài liệu (20 mẫu × 3)

| | v5 | v6 |
|---|---|---|
| `contradicted` qua `R` (9 lượt) | **0/9** | **9/9** |
| `contradicted` qua `S` (9 lượt) | 9/9 | 9/9 |
| `supported` precision / recall | 0.81 / 1.0 | 0.91 / 1.0 |
| `no_source` → quan sát `supported` (12 lượt, sau khi code bỏ id sai) | 7/12 | 3/12 |
| `no_source` → model **ghi** `supported` (bất kể id) | 9/12 | 8/12 |

- **Lỗi `R` sửa xong.** Cả 18 lượt câu trả lời sai đều ra `contradicted` với id hợp lệ, nên `refuted_by_reference` và luật chặn `technical_accuracy` trong `postcheck` lần đầu có hiệu lực thật.
- **Lỗi cite tài liệu không liên quan không sửa được bằng prompt.** Model vẫn ghi `supported` cho 8/12 lượt (v5: 9/12), dù prompt có đúng ví dụ âm của hai mẫu đó. Con số "3/12" sau kiểm là do model điền chữ `no_source` vào `source_ids` thay vì id, code bỏ id sai nên rớt về `no_source` một cách tình cờ. Không coi đây là tiến bộ.
- Thử kiểm từ vựng trong code (từ của ý phải có trong tài liệu được cite): trên bộ này tách tốt, nhưng trên chunk thật của mô phỏng chỉ bắt 15/61 ca judge gọi `unrelated` và loại nhầm 2/105 ca đúng, vì chunk dài nên luôn trùng vài từ. Không đưa vào.

## Golden thường (51 mẫu × 3, nhãn 1 người)

| Chỉ số | v5 | v6 | Ngưỡng |
|---|---|---|---|
| Khớp ±1 band | 0.969 | 0.971 | ≥ 0.80 |
| Lệch khoan dung | −0.244 | −0.248 | [−0.3, 0.3] |
| Thứ tự strong > medium > weak | 1.0 | 1.0 | — |
| Bắt injection | 0.75 | 0.75 | 1.0 |
| Quote hợp lệ | 0.960 | 0.981 | — |
| Độ lệch chuẩn 3 lần | 0.052 | 0.047 | — |
| Id bịa (bộ này không có tài liệu) | 0 | **113** (`R` 101, `no_source` 12) | 0 |

- Điểm số không đổi trong nhiễu. v6 không làm Evaluator khắt hơn hay dễ hơn.
- **Hồi quy nhỏ:** khi không có đáp án chuẩn, v6 vẫn ghi `R` ở 101 ý. Prompt đã nói "`reference_answer` là (không có) thì không có id `R`" mà model bỏ qua. `check_sources` bỏ id không có trong lượt nên ý đó thành `no_source`, đúng với kết quả v5 (v5 để `source_ids` rỗng); khác nhau chỉ ở độ sạch của output. Chấp nhận, ghi lại để theo dõi `invented_source_id_values`.

## Kết luận
- Dùng v6 làm mặc định: sửa được lỗi `R` (có hiệu lực lên điểm), không đổi điểm số, không thêm lỗi chức năng.
- Độ chính xác `supported` (~0.64 trên mô phỏng theo `judge_support`) **chưa sửa được ở prompt**. Hướng còn lại: (1) đổi model Evaluator mạnh hơn cho riêng bước gán `support`, (2) để `judge_support` chạy hậu kiểm ở eval, hoặc (3) đo lại sau khi Phase 04 nạp giáo trình, vì phần lớn `no_source` là kho thiếu.

## Câu hỏi còn mở
- Có chấp nhận chi phí một lời gọi phụ (model mạnh hơn hoặc judge) chỉ để gán `support`, hay giữ `supported` là "tự khai" và ghi rõ trong báo cáo?
