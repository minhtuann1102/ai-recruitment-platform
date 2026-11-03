# So model cho Evaluator trên OpenRouter (2026-11-03)

Prompt Evaluator v7 (nhánh `thang/evaluator-v7`, PR #72), giá lấy từ API công khai `openrouter.ai/api/v1/models` ngày 03/11. JSON golden (gitignored): `eval-evaluator-{main,sourced}-mm-{4omini,gemflashlite}-261103.json`. Script thử nhanh ở scratchpad, không commit.

## Lọc
- 155 model có `structured_outputs`, input ≤ $0.6/M, output ≤ $2.5/M, context ≥ 32k.
- Thử nhanh 9 model đáng tin trên 3 mẫu golden chính (gọi thẳng, `max_tokens` 1200, tắt reasoning nếu được), chạy song song nên độ trễ chỉ để so tương đối:

| Model | Chi phí/lượt | Thời gian (3 mẫu) | Token vào | JSON | Ghi chú |
|---|---|---|---|---|---|
| gpt-4o-mini (đang dùng) | $0.00042 | 4.5 / 3.9 / 2.7 s | ~4 000 | 3/3 | mốc |
| **gpt-6-luna** | $0.00029 | 4.4 / 3.3 / 2.7 s | ~4 000 | 3/3 | cùng tokenizer; cần gửi `reasoning.enabled=false` |
| **gpt-5-nano** | $0.00026 | 3.0 / 3.2 / 2.7 s | ~4 000 | 3/3 | cần `reasoning.effort=minimal` |
| **Gemini 2.5 Flash-Lite** | $0.00025 | 1.9 / 1.7 / 1.6 s | ~3 600 | 3/3 | nhanh nhất; đầu ra dài gấp ~2 |
| DeepSeek V4 Flash | $0.00049 | 6.6 / 1.8 / 4.6 s | ~4 700 | 3/3 | đắt hơn, chậm hơn |
| Mistral Small 3.2 | $0.00034 | 6.2 / 4.9 / 3.5 s | ~3 700 | 3/3 | chậm hơn |
| Qwen3.8 Flash | $0.00068 | 14.5 / 18.2 / 5.5 s | ~3 600 | 2/3 | tắt reasoning không ăn, 1 lần cắt `length` |
| GLM-5.3 Flash | $0.00017 | 2.7 / 7.6 / 3.4 s | ~3 700 | 3/3 | vẫn reasoning tới 1 027 token |
| gpt-oss-120b | $0.00014 | 4.6 / 21.6 / 7.0 s | ~3 700 | 3/3 | vẫn reasoning, có lượt 21 s |
| Claude Haiku 5.5 | ~$0.0010 | 4.1 s | **7 794** | - | tokenizer gấp ~2 với tiếng Việt; mặc định reasoning hết 400 token → timeout |
| gpt-4.1-nano | - | 2.5 s | ~4 000 | - | dừng theo yêu cầu (thử 2 mẫu: ±1 band 0.25, lệch −2.1) |

## Golden: Gemini 2.5 Flash-Lite so với gpt-4o-mini (chạy cùng lúc, 3 lần)
| Chỉ số | gpt-4o-mini | Gemini 2.5 Flash-Lite |
|---|---|---|
| ±1 band (golden chính) | 0.968 | 0.958 (−1 điểm %, trong ngưỡng 5) |
| MAE, lệch khoan dung | 0.554, −0.264 | **0.351, −0.185** |
| Độ lệch chuẩn giữa 3 lần | 0.065 | 0.0 |
| `answer_type`, thứ tự band, injection | 0.977, 1.0, 6/8 | 0.952, 1.0, 6/8 |
| `supported` P / R (golden có tài liệu) | **0.968** / 0.813 | 0.857 / 1.0 |
| `contradicted` R, qua `R` / `S` | 0.6, 0.917 / 0.389 | 0.7, 1.0 / 0.5 |
| Chặn nhầm câu đúng có `R` | 0 | 0 |
| Lần `degraded` / 294 | 3 (timeout) | 7 (3 cắt `length` ở 600 token, 3 timeout, 1 rate limit) |
| Token ra | 46.6k | **108k** (gấp 2.3) |
| Chi phí hai golden | $0.124 | $0.085 (−31%) |
| Thời gian chạy | 122 + 98 s | 80 + 77 s |

- Gemini chấm điểm sát người hơn (MAE, lệch) và ổn định hơn, nhưng `supported` precision tụt 0.968 → 0.857: quay lại đúng lỗi v6 đã sửa (cite tài liệu cho ý tài liệu không nói). Đây là chỉ số hiển thị cho ứng viên qua `sources`.
- Đầu ra dài gấp đôi nên vượt `max_tokens` 400 thường xuyên, gateway gọi lại với 600 và vẫn có lần bị cắt. Muốn dùng phải tăng `max_tokens`, chi phí và độ trễ tăng lại một phần.
- Golden nhỏ, 1 người chấm; chênh 1 điểm % ±1 band là trong nhiễu.

## Kết luận
- Chưa có model nào **rõ ràng tốt hơn** gpt-4o-mini cho Evaluator. Rẻ hơn thì có (25–40%/lượt), nhưng số tiền nhỏ (~$0.001–0.002/phiên).
- Đáng đo tiếp: **gpt-6-luna** (cùng tokenizer, rẻ hơn 31%, độ trễ như cũ, hành vi gần gpt-4o-mini nhất) và **gpt-5-nano**. Cả hai cần gateway gửi tham số tắt/giảm reasoning, hiện chưa có (`app/llm/gateway.py` không gửi `reasoning`); thiếu thì model tự reasoning, chậm và dễ cắt `length`.
- Gemini 2.5 Flash-Lite: nhanh nhất (~1.7 s/lượt so với ~3.7 s), có ích cho TTFT nếu Evaluator nằm trên đường nóng, nhưng phải sửa `supported` precision trước.

## Đợt 2: gpt-6-luna và gpt-5-nano (03/11, nhánh `thang/llm-reasoning-config`)
Thêm `LLM_REASONING_<AGENT>` vào gateway (docs 08 §9.3). Prompt **v6** (bản trên `main`), gpt-4o-mini chạy cùng lúc làm mốc, 3 lần mỗi golden. JSON: `eval-evaluator-{main,sourced}-rs-{4omini,luna,nano}-261103.json`.

| Chỉ số | gpt-4o-mini | **gpt-6-luna** (`off`) | gpt-5-nano (`minimal`) |
|---|---|---|---|
| ±1 band | 0.959 | **0.981** | 0.740 |
| MAE, lệch khoan dung | 0.565, −0.289 | **0.310, −0.155** | 1.148, −0.887 |
| Độ lệch chuẩn 3 lần | 0.063 | 0.081 | 0.275 |
| `answer_type` đúng | **0.977** | 0.907 | 0.907 |
| Bắt injection | 6/8 | **8/8** | 6/8 |
| Quote hợp lệ | 0.987 | 0.987 | 0.698 |
| `supported` P / R | 0.982 / 0.789 | 0.974 / **1.0** | 0.605 / 0.986 |
| `contradicted` P / R | 1.0 / 0.633 | 1.0 / **0.733** | 0.9 / 0.3 |
| `contradicted` qua `R` / `S` | **1.0** / 0.389 | 0.833 / **0.667** | 0.333 / 0.278 |
| `no_source` P | 0.59 | **0.857** | 0.778 |
| Chặn nhầm câu đúng có `R` | 0 | 0 | 0 |
| Id nguồn bịa | 0 | 0 | 15 |
| Lần `degraded` / 294 | 6 (timeout) | **0** | 5 (timeout) |
| Token ra | 46.2k | 51.0k | 66.7k |
| Tỉ lệ input cached | 86% | 96% | 88% |
| Chi phí hai golden | $0.121 | **$0.041 (−66%)** | $0.038 |
| Thời gian chạy (cùng tải) | 132 + 114 s | 142 + 127 s (+9%) | 117 + 113 s |

- **gpt-6-luna tốt hơn gpt-4o-mini ở gần hết chỉ số**, kể cả hai chỗ đang hở trên `main`: bắt được 2 mẫu injection không từ khóa (a14, a15) mà gpt-4o-mini lọt từ v5, và recall `supported` 0.79 → 1.0 (v6 đổi recall lấy precision). Golden và prompt được chỉnh 4 vòng trên gpt-4o-mini, nên lợi thế của luna không do tối ưu riêng.
- Điểm kém: `answer_type` 0.977 → 0.907, do gắn `partial` cho câu yếu q06-weak, q10-weak và a04 (nhồi thuật ngữ) ở cả 3 lần, nhãn là `answered`; `contradicted` qua `R` 1.0 → 0.833. Độ trễ cao hơn ~9% (đo thô bằng thời gian chạy cùng tải).
- Rẻ hơn chủ yếu nhờ giá cache read $0.01 so với $0.075, mà Evaluator gần như toàn input cached.
- **gpt-5-nano loại**: ±1 band 0.74, bịa id nguồn 15 lần, quote hợp lệ 0.70.

## Mô phỏng full: gpt-6-luna làm Evaluator (03/11)
28 phiên, mọi agent chạy LLM, simulator LLM, prompt v6, `LLM_REASONING_EVALUATOR=off`. Mốc: lần chạy v4c (gpt-4o-mini, 02/11). JSON: `eval-sim-evaluator-luna-261103.json`, `eval-sim-interviewer-ab-v4c.json`.

| Chỉ số | v4c (gpt-4o-mini) | gpt-6-luna |
|---|---|---|
| Chi phí thật/phiên | $0.00778 | **$0.00646** (−17%) |
| Chi phí Evaluator/phiên | $0.00435 | **$0.00236** (−46%) |
| TTFT p50 / p95 | 4.46 / 8.47 s | 5.13 / 7.35 s |
| Evaluator p50 / p95 | 3061 / 6212 ms | 3862 / 5769 ms |
| Nhóm persona đúng thứ tự | 7/7 | 6/8 |
| `turn_score` weak / average / strong | 2.53 / 3.78 / 5.38 | **4.16** / 5.00 / 5.79 |
| Khoảng cách strong − weak | 3.74 | **2.44** |
| Tỉ lệ hint cho weak | 0.371 | 0.199 |
| `gap_recall` | 0.87 | 0.76 |
| Topic chưa biết đóng trong 2 lượt | 1.0 | 0.92 |
| Lượt/phiên | ~9–11 | ~12–13 |
| `dont_know` ở persona weak | 10 | **0** |
| `supported` / low_confidence | 0.247 / 0.632 | 0.396 / 0.386 |
| Fallback, RAG degraded | 0.025, 7 | 0.01, 2 |

- **Luna khoan dung hơn hẳn trên hội thoại thật**, ngược với golden. Persona weak hay trả lời kiểu "mình không chắc lắm, có thể là equals và hashCode?": gpt-4o-mini gắn `dont_know`, luna gắn `answered`, `completeness` 0–1 nhưng vẫn cho 5.0/10. Không còn `dont_know` thì policy không đóng topic sớm, ít hint, phiên dài hơn, và độ phân biệt ứng viên yếu/mạnh hẹp lại 1/3.
- Golden không bắt được điều này vì chỉ có vài mẫu "đoán mò kèm từ khóa đúng"; đây là kiểu câu persona weak sinh ra nhiều nhất.
- TTFT p50 +0.7 s, p95 −1.1 s. Chi phí rẻ hơn như dự đoán.
- Một lần chạy, mốc ở ngày khác; nhưng `dont_know` 10 → 0 và weak +1.6 điểm là quá lớn để là nhiễu.

## Kết luận (cập nhật sau mô phỏng)
- **Chưa đổi Evaluator, giữ gpt-4o-mini.** Luna thắng trên golden nhưng làm hỏng chỉ số quan trọng nhất của buổi phỏng vấn: phân biệt ứng viên yếu và mạnh.
- Muốn dùng luna phải: thêm vào golden các mẫu "đoán mò, rào đón, đúng từ khóa" (nhãn `dont_know` hoặc điểm thấp), rồi chỉnh prompt cho luna (luật nhận diện `dont_know` khi ứng viên tự nói không chắc và không giải thích). Chỉ đo lại khi golden đã có các mẫu đó.
- Code `LLM_REASONING_<AGENT>` vẫn có ích (bắt buộc cho mọi model có reasoning), giữ lại.
- `partial` không đổi hành động của policy (`app/policy.py` chỉ rẽ nhánh theo `manipulation`, `off_topic`, `asks_clarification`, `dont_know`, còn lại theo điểm), nên lệch `answer_type` ở golden không phải nguyên nhân; nguyên nhân là mất `dont_know` và điểm cao.

## Reporter: gpt-6-luna so với gpt-4o-mini (03/11)
Chạy lại Reporter (prompt v2) trên 28 phiên đã lưu của lần mô phỏng v4c, nên điểm và đầu vào giống hệt nhau, mỗi model 2 lần. State dựng lại từ các lượt (chỉ `hint_used` dùng tới), khớp điểm tổng 28/28. Luna chạy với `LLM_REASONING_REPORTER=off`. Script ở scratchpad (`reporter_ab.py`, `reporter_ab_compare.py`); JSON: `eval-reporter-ab-{4omini,luna}-261103.json`.

| Chỉ số | gpt-4o-mini | gpt-6-luna |
|---|---|---|
| Báo cáo `partial` (Reporter lỗi) | 0/56 | 0/56 |
| `gap_recall` (2 lần) | 0.87 / 0.91 | **1.0 / 1.0** |
| Điểm mạnh sai (`false_strengths`) | 0 | 0 |
| Báo cáo dùng điểm mạnh LLM (không bị code loại hết) | 54% | 66% |
| Độ dài summary trung bình | 226 ký tự | 319 ký tự |
| Câu bị cắt ở giới hạn độ dài | 0 | 2/161 `why` |
| Token ra | 853 | 1241 (+45%) |
| Chi phí/báo cáo | $0.000813 | $0.000724 (−11%) |
| Độ trễ p50 / p95 | 10.3 / 17.9 s | 10.9 / 13.6 s |

- **Luna viết báo cáo tốt hơn rõ.** Nhận xét gắn đúng lượt ("Ở lượt 4 bạn nhầm rằng…"), nêu cụ thể ý còn thiếu, đầu việc học làm được ngay ("Tạo đoạn code có process.nextTick, setTimeout, setImmediate; dự đoán rồi kiểm tra thứ tự chạy"). gpt-4o-mini chung chung hơn ("Đọc tài liệu về…") và có lần gắn sai topic.
- Đã soát lỗi sai luna nêu ra: lấy từ `misconceptions` của Evaluator, không bịa.
- Điểm khoan dung không ảnh hưởng ở đây, vì code giữ nguyên điểm và chỉ nhận điểm mạnh có lượt đủ điểm làm bằng chứng (`merge_comments`).
- Rẻ hơn ít (−11%) vì viết dài hơn. Lý do đổi là chất lượng, không phải tiền. Reporter chạy lúc kết thúc phiên, không nằm trên đường TTFT.
- Giới hạn: không có nhãn người cho chất lượng báo cáo; chỉ đọc tay vài báo cáo và dùng `gap_recall` (heuristic, 23 lỗ hổng được hỏi).

## Câu hỏi còn mở
- Đổi Reporter sang gpt-6-luna (`LLM_MODEL_REPORTER=openai/gpt-6-luna`, `LLM_REASONING_REPORTER=off`)? Cần người đọc vài báo cáo xác nhận trước.
- Câu "đoán mò kèm từ khóa đúng" nên là `dont_know` hay `answered` điểm thấp? Cần người chấm quyết để làm nhãn golden.
- `partial` cho câu yếu: nhãn golden `answered` có đúng không, hay luna đúng hơn?
