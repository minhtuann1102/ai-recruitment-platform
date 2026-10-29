# Eval A/B: Evaluator v3 vs v4 (trích nguồn, Phase 03a)

Golden 48 mẫu × 3 lần (nhãn `final` + `rater_a`, không có tài liệu đối chiếu); mô phỏng quick matrix 10 phiên, agent +
simulator LLM, RAG bật. Mỗi vòng v3 và v4 chạy **cùng lúc**. Vòng 1: prompt v4 trước khi sửa theo review; vòng 2: bản
cuối. JSON (gitignored): `plans/reports/eval-evaluator-03a-*.json`, `eval-sim-03a-*.json`.

## Golden (độ lệch điểm so với người)

| Chỉ số | v3 r1 | v4 r1 | v3 r2 | v4 r2 |
|---|---|---|---|---|
| Agreement ±1 band (n = 516) | 0.930 | 0.922 | 0.919 | 0.919 |
| MAE | 0.702 | 0.758 | 0.713 | 0.738 |
| Leniency bias (âm = khắt hơn người) | −0.337 | −0.479 | −0.376 | −0.467 |
| answer_type đúng | 0.977 | 0.953 | 0.977 | 0.977 |
| Quote hợp lệ | 0.971 | 0.990 | 0.974 | 0.983 |
| Id nguồn bịa (golden không có tài liệu) | 0 | 0 | 0 | 0 |
| Token vào / ra (144 lượt) | | | 379k / 24.7k | 425k / 26.7k |

## Mô phỏng (vòng 2)

| Chỉ số | v3 | v4 |
|---|---|---|
| Evaluator p50 / p95 (ms) | 2595 / 4081 | 3007 / 4404 |
| TTFT p50 / p95 (s) | 3.69 / 5.49 | 3.86 / 6.16 |
| Chi phí TB / phiên (USD) | 0.00833 | 0.00854 |
| Ý covered: supported / contradicted / no_source | – | 0.47 / 0 / 0.53 (73 ý) |
| Lượt `confidence = low` | – | 0.22 (32 lượt) |

## Nhận xét
- Agreement v3 dao động 0.919–0.930 giữa hai vòng; v4 bằng v3 ở vòng 2, kém 0.008 ở vòng 1 (trong mức nhiễu). Cả hai
  đều có lần dưới ngưỡng 0.93 của plan: ngưỡng chưa ổn định với golden hiện tại.
- **v4 khắt hơn có hệ thống** (leniency −0.47 so với −0.34/−0.38, cả hai vòng), MAE +0.03–0.06.
- Evaluator chậm hơn ~0.3–0.4 s (p50 và p95, cả hai vòng). Evaluator chạy trước Interviewer nên **cộng thẳng vào TTFT**.
- Không ý nào bị `contradicted` trong 153 ý của hai vòng mô phỏng: nhánh chặn điểm theo `R` chưa được dùng thực tế.
- Khoảng một nửa ý chấm có tài liệu ủng hộ; nửa còn lại chấm bằng kiến thức của model.

## Câu hỏi chưa giải quyết
- Để v4 mặc định (được trích nguồn, khắt hơn, +0.3–0.4 s) hay giữ v3 mặc định, v4 bật bằng `EVALUATOR_PROMPT_VERSION`?
- Hiệu chỉnh độ khắt của v4 (luật 12 "chấm theo tài liệu") trước 03b?
- Golden cần thêm mẫu có tài liệu đối chiếu để đo `supported` / `contradicted` so với người.
