# Evaluator v6: cite `R`, siết `supported` (2026-11-02)

gpt-4o-mini, tracing tắt. Golden có tài liệu 32 mẫu × 3 lần, golden chính 51 mẫu × 3 lần (1 người chấm), v5 và v6 chạy cùng lúc. Mô phỏng quick matrix 10 phiên, `--serve`, RAG bật, chạy lần lượt v6 rồi v5. `judge_support` v2 hiệu chỉnh với LLM thứ hai, chưa với người.
JSON (gitignored): `plans/reports/eval-evaluator-{sourced,main}-{v5,v6}-*-261102.json`, `eval-sim-06-*.json`, `eval-judge-06-*.json`. Trước đó: `eval-261031-1730-evaluator-sourced-golden.md`.

## Kết luận
- **Đề xuất dùng v6**, kèm điều kiện DE sửa hoặc loại mục kho `cr-lz-python-basics-8979143a`. Đạt 4/5 ngưỡng đặt trước; trượt recall. Đã qua review độc lập, 579 test pass, 8 skip.
- **`supported` đáng tin hơn hẳn:** judge 0.675 → 0.964. Đổi lại v6 bỏ sót nhiều: recall ước tính 0.977 → 0.576, 39/86 ý `no_source` thực ra có căn cứ. `no_source` không ảnh hưởng điểm, nhưng từ v6 nó **không** có nghĩa "không có tài liệu nói ý này".
- **Lỗi có sẵn trên `main`:** trên mô phỏng, `R` chặn điểm chưa lần nào đúng (0/9). Golden báo precision 1.0 nên không lộ. Với prompt cuối còn 3 lần trên 4 vòng, chưa sửa xong.

## Kết quả (vòng cuối)
So cùng lúc với v5 trên prompt cuối, trước khi sửa theo review. Cột "Sau review" là v6 chạy lại trên code cuối, cùng prompt (1 lần golden, 2 vòng mô phỏng, judge không chạy lại). Lớp `restates_reference` áp dụng cả cho cột v5, nên cột đó không hoàn toàn là `main`.

Golden có tài liệu, 96 lượt:

| Chỉ số | v5 | v6 | Sau review |
|---|---|---|---|
| `supported` P / R | 0.79 / 0.82 | 0.98 / 0.94 | 0.98 / 0.94 |
| `contradicted` P / R | 1.00 / 0.48 | 1.00 / 0.81 | 1.00 / 0.81 |
| `contradicted` qua `R` | 0.08 | **0.92** | 0.92 |
| `contradicted` qua `S` | 1.00 | **0.67** (g15 về `no_source` 3/3) | 0.67 |
| `no_source` P / R | 0.39 / 0.54 | 0.80 / 1.00 | 0.80 / 1.00 |
| Chặn nhầm câu đúng có `R` | 0 | 0 | 0 |
| Điểm `technical_accuracy` câu đúng có `R` | 2.83 | 2.88 | 2.79 |

Golden chính và mô phỏng (2 vòng, 20 phiên, 0 lỗi RAG):

| Chỉ số | v5 | v6 | Sau review |
|---|---|---|---|
| ±1 band | 0.961 | 0.961 | 0.965 |
| Lệch khoan dung | −0.27 | −0.30 (ngưỡng ±0.3) | −0.31 |
| Thứ tự band, bắt injection | 1.0, 6/8 | 1.0, 6/8 | 1.0, 6/8 |
| `answer_type` đúng | 0.977 | 0.953 (chỉ mẫu a04 đổi) | 0.953 |
| Judge `supported` đúng | 0.675 (n=123) | **0.964** (n=55) | chưa chạy |
| Câu kho / câu AI tự đặt | 0.92 / 0.39 | 1.00 / 0.85 (AI chỉ n=13) | chưa chạy |
| Recall ước tính | 0.977 | **0.576** | chưa chạy |
| `no_source` ở `technical` | 0.11–0.16 | 0.55–0.66 | 0.63–0.66 |
| `low_confidence` | 0.06–0.08 | 0.52–0.56 | 0.60–0.61 |
| TTFT p50 / p95 | 3.24–3.30 / 5.03–5.71 s | 3.46–3.50 / 5.86–6.00 s | 3.38–3.39 / 5.16–5.27 s |
| Chi phí phiên | $0.0091–0.0093 | $0.0094–0.0098 | $0.0099–0.0104 |
| `study_plan.resources` mỗi phiên | 3.75 | 3.5 | chưa tính |

TTFT p50 gộp mọi vòng: v5 3.24–3.76 s (6 vòng), v6 3.38–3.90 s (8 vòng; 6 vòng gần nhất 3.38–3.50 s), nên chưa thấy khác biệt ngoài nhiễu. Token vào +19%. Chi phí trung bình $0.0091 (v5, 6 vòng) → $0.0099 (v6, 6 vòng gần nhất), khoảng +9%. Đối chứng judge 0.0 ở cả hai.

## Thay đổi
- `evaluator.v6.md`, luật 11: chưa nêu không phải nói sai; chỉ kết luận sai theo đáp án khi đáp án nói rõ điều ngược lại; `misconceptions` không chép câu của đáp án.
- Luật 12: so **`quote`** với tài liệu, không so key point; `R` là một id; diễn đạt khác vẫn `supported`, cùng chủ đề chưa đủ. Thêm mẫu neo trích nguồn, chủ đề index. Review phát hiện mẫu neo composite index gần trùng mẫu g26, tức có rò rỉ; v5 cũng đúng 3/3 ở mẫu này nên chưa thấy thổi số, nhưng nên đổi chủ đề ở lần sửa prompt sau.
- Code: `restates_reference` bỏ khỏi `misconceptions` câu gần như nguyên văn trong `R`, trừ khi có từ phủ định quanh bất kỳ lần xuất hiện nào (mặc định giữ lại). Áp dụng cho **mọi** phiên bản prompt có `R`.
- Code: ý bị `R` bác giờ ghi `quote` (lời ứng viên đã kiểm) thay vì `point`. Trước đó `point` được model viết theo mặt đúng của `R`, nên câu đúng của đáp án hiện ra thành "hiểu sai". `point` chép nguyên câu của `R` thì coi là ý chưa nêu, không tính bác bỏ.
- Golden thêm 12 mẫu: câu đúng có `R`, `R` không nói tới, tài liệu nhiều ý (530–740 ký tự, vẫn ngắn hơn chunk thật ~1.020). Bộ cũ không có câu đúng đi kèm `R` nên không đo được bác oan.
- `run_evaluator_sourced`: `r_blocked` đo trên `Evaluation` sau hậu kiểm, cần cả `R` bị trích là bác bỏ lẫn còn misconception.

## Vì sao cần 4 vòng

| Vòng | Sửa | `R` | Judge P / recall | ±1 band (v6 / v5) |
|---|---|---|---|---|
| 1 | Nói rõ `R` là id, `supported` cần đúng ý | 0.83 | chưa đo | chưa đo |
| 2 | So `quote` thay vì key point, bỏ "xét R trước" | 1.00 | 0.81 / 0.63 | 0.957 / 0.971 |
| 3 | Thêm "diễn đạt khác vẫn supported", mẫu tài liệu dài | 0.75 | 0.86 / 0.60 | 0.953 / 0.977 |
| 4 | Tách chưa nêu với nói sai, thêm `restates_reference` | 0.92 | **0.96 / 0.58** | 0.961 / 0.961 |

Vòng 1 làm 3 mẫu `R` không nói tới bị `supported` 9/9. Giả thuyết "chunk tiếng Anh" ở vòng 3 sai (0% tiếng Anh); nguyên nhân thật là chunk dài ~1.020 ký tự, nhiều ý.

## Ngưỡng đặt trước vòng 3

| Ngưỡng | v6 cuối | Kết quả |
|---|---|---|
| `contradicted` qua `R` ≥ 0.9 | 0.92 | Đạt |
| Không chặn nhầm câu đúng trên golden | 0 | Đạt |
| Judge precision ≥ 0.80 | 0.96 | Đạt |
| ±1 band tụt ≤ 0.02 | 0.00 | Đạt |
| Judge recall ≥ 0.80 | 0.58 | **Trượt** |

Ngưỡng recall do tôi đặt ở vòng 3, không nằm trong Success Criteria Phase 05.

Với Success Criteria của Phase 05: precision `supported`, recall `contradicted`, ±1 band đạt. **Precision `contradicted` ≥ 0.90 đạt trên golden nhưng không đạt trên mô phỏng.** Lệch khoan dung −0.30 vừa chạm mép.

## `R` chặn điểm trên dữ liệu thật
4 vòng mỗi bản: v5 3/104 lượt có `R`, v6 6/103. Đọc thủ công từng ca, chưa có người chấm thứ hai: **không ca nào bác đúng một lỗi thật của ứng viên** (0/9). Một ca persona average có thiếu sót nhỏ (bỏ `TIMED_WAITING`), nhưng điều bị ghi là hiểu sai ("Blocked không phải trạng thái chính") mới là sai.
- Model coi ý ứng viên **chưa nêu** là bác bỏ, chép câu đúng của `R` vào `misconceptions`, rồi luật 4 ép `technical_accuracy ≤ 1`. Ví dụ "Lớp java.lang.Throwable là lớp gốc..." thành "hiểu sai".
- **5/6 ca của v6 đến từ một mục:** `cr-lz-python-basics-8979143a`, câu vòng đời thread Java theo mô hình cũ `ready/running`, gắn nhãn python. Persona strong và average trả lời đúng theo `Thread.State` bị coi là sai.
- Vòng cuối còn 3 lần, cả 3 đều từ mục này: 2 lần vẫn chặn oan ("BLOCKED không phải trạng thái chính"), 1 lần `restates_reference` gỡ được (điểm 2, không có misconception). 2 vòng sau review không có lần nào, nhưng số quá nhỏ để coi là đã hết.
- Phát lại `restates_reference` trên 6 ca đã lưu chỉ gỡ cap 1/6: phần còn lại là misconception do LLM tự viết. Tức lớp code chỉ giảm nhẹ. Nó cũng không nâng được điểm nếu model đã tự cho thấp: `apply_caps` chỉ hạ điểm, nên có thể còn điểm thấp mà không có misconception nào giải thích (review M3, chưa có cách sửa tốt).
- Câu sai vẫn nhận điểm thấp khi luật chưa chạy (`technical_accuracy` trung bình 1.0 ở v5, 0.71 ở v6), nên luật này gần như chưa cho lợi ích đo được.

## Giới hạn
- Prompt chỉnh trên chính golden qua 4 vòng, và mô phỏng vòng 2–3 cũng dùng để chẩn đoán. Riêng mô phỏng vòng cuối không dùng để chỉnh, nhưng chỉ 2 vòng. Chưa có held-out.
- Golden g25 đúng 3/3 trong khi chính mục kho đó vẫn chặn oan trên mô phỏng: golden chưa tái hiện được lỗi này. Mẫu và nhãn golden do AIE tự viết. Judge chưa hiệu chỉnh với người. Precision judge của v5 dao động 0.56–0.77 giữa các vòng, n = 55 của v6 còn nhỏ.
- Recall là ước tính từ số ý judge xác nhận, không phải đo trên tập đúng.
- `contradicted` qua `S` giảm và điểm persona giảm nhẹ (strong 2.87 → 2.80, weak 1.19 → 0.88, gộp 4 vòng, gồm 2 vòng prompt vòng 3).
- `low_confidence` tăng mạnh. Trong repo chưa có code đọc `evaluation.confidence`, nên chưa ảnh hưởng sản phẩm, nhưng interview-service cần biết.

## Câu hỏi còn mở
1. Owner có chấp nhận recall 0.58 để đổi lấy precision 0.96 không?
2. DE sửa hay loại `cr-lz-python-basics-8979143a`? Có nên rà các mục cũ tương tự?
3. Có giữ luật `R` bác bỏ thì ép `technical_accuracy ≤ 1` không, khi trên mô phỏng chưa có ca đúng nào?
4. Recall: đã phân tích và thử ở `eval-261102-1159-evaluator-v6-recall-deep-dive.md`. `source_quote` không giúp được.
5. Sơ đồ trong `docs/architecture/diagrams/` vẫn ghi Evaluator v4.
6. Prompt còn vài điểm review nêu, để lại vì bản phát hành phải là bản đã đo: phần đầu ra nói `missing_points` theo `key_points` trong khi luật 11 nói theo `R`; mẫu neo "Yếu" và mẫu neo trích nguồn xử lý ý sai khác nhau trong `covered`. Ngoài prompt: `contradicted` chỉ từ `S` vẫn có thể ép điểm.
