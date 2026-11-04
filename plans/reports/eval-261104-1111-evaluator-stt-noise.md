# Evaluator với bản ghi STT nhiễu (NFR-AI-QUAL17, voice tùy chọn A)

Ngày 04/11. Nhánh `thang/voice-evaluator-noise`. Model Evaluator gpt-4o-mini, 3 vòng mỗi mẫu, chi phí đo ~$0.33 (6 lần chạy).

## Tóm tắt
- Thêm 12 mẫu nhiễu STT (`evals/evaluator_golden_stt.jsonl`): 4 câu (q01, q04, q06, q11) × strong / medium / weak, cùng nội dung với mẫu sạch, chỉ khác bản ghi: không dấu câu, viết thường, thuật ngữ Anh phiên âm ("hát mắp", "thờ rét", "ri quét"), từ đệm, đồng âm. Nhãn lấy theo mẫu sạch.
- `python -m evals.run_evaluator --stt` chạy mẫu sạch cùng bản nhiễu trong một lần và báo `stt_noise` (chênh `turn_score_10` nhiễu − sạch theo cặp, chỉ lần không degraded).
- **v7:** bản nhiễu thấp hơn trung bình 1.51 điểm (thang 10), 3/12 cặp đổi `answer_type` (weak bị gắn `off_topic` / `dont_know`, nên policy đi nhánh khác).
- **v8** (`evaluator.v8.md` = v7 + đoạn về bản ghi giọng nói + một mẫu neo): đổi `answer_type` 3 → 1 cặp, chênh −1.51 → −1.18. Golden thường và golden có tài liệu không tụt.
- **Chưa đạt QUAL17 với ngưỡng đề xuất** (mục 4): câu strong nhiễu vẫn thấp hơn 1.3–2.9 điểm, chủ yếu `technical_accuracy` và `extensibility`.
- **STT tốt** (thuật ngữ đúng, chỉ mất dấu câu, mục 7): chênh −0.10, cặp lệch ≤ 1 điểm 12/12, đạt cả ba ngưỡng đề xuất. Mất điểm đến từ thuật ngữ phiên âm, không phải dấu câu.
- **Bảng tra thuật ngữ** (`app/stt_terms.py`, mục 6): đổi dạng phiên âm về thuật ngữ trước Evaluator. v8 + bảng: `answer_type` khớp 12/12, chênh −0.67, cặp lệch ≤ 1 điểm 0.75; gần đạt ngưỡng nhưng **số này lạc quan** vì bảng và bộ nhiễu cùng một người viết.

## 1. Chênh điểm theo cặp

| Mẫu | Sạch v7 | Nhiễu v7 | Sạch v8 | Nhiễu v8 |
|---|---|---|---|---|
| q01-strong | 9.4 | 6.7 | 9.4 | 6.5 |
| q01-medium | 5.0 | 5.0 | 5.0 | 5.0 |
| q01-weak | 2.7 | 0.0 `off_topic` | 2.7 | 1.3 |
| q04-strong | 6.9 | 5.6 | 6.9 | 5.6 |
| q04-medium | 5.0 | 4.8 | 5.0 | 5.0 |
| q04-weak | 1.9 | 0.0 `dont_know` | 1.9 | 1.9 |
| q06-strong | 8.1 | 6.0 | 8.1 | 5.8 |
| q06-medium | 5.0 | 5.0 | 5.0 | 4.8 |
| q06-weak | 1.9 | 0.0 `dont_know` | 1.9 | 0.0 `dont_know` |
| q11-strong | 9.4 | 5.6 | 8.8 | 6.2 |
| q11-medium | 4.4 | 2.5 | 4.4 | 2.5 |
| q11-weak | 1.9 | 2.3 | 1.9 | 2.3 |

| Chỉ số `stt_noise` | v7 | v8 |
|---|---|---|
| `mean_diff` | −1.51 | −1.18 |
| `max_abs_diff` | 3.8 | 2.93 |
| `within_1` (|chênh| ≤ 1) | 0.333 | 0.417 |
| `same_answer_type` | 0.75 | 0.917 |
| ±1 band (24 mẫu, nhãn sạch) | 0.861 | 0.893 |

Đọc: medium gần như không đổi; weak bị đẩy về 0 là lỗi nặng nhất của v7 vì `dont_know` bỏ qua chấm và đổi hành động của Interviewer. v8 sửa được 2/3 ca weak; q06-weak ("cát ơ sai là để rê đít đứng cạnh đê bê...") vẫn bị gắn `dont_know` dù là câu sai có nội dung. Câu strong mất điểm vì model coi thuật ngữ phiên âm là thiếu chính xác.

## 2. Hồi quy trên golden khác

| Golden | Chỉ số | v7 | v8 |
|---|---|---|---|
| Thường (51 mẫu) | ±1 band / MAE / lệch | 0.973 / 0.527 / −0.267 | 0.971 / 0.559 / −0.242 |
| | `answer_type` đúng / thứ tự / injection | 0.953 / 1.0 / 0.75 | 0.953 / 1.0 / 0.75 |
| Có tài liệu (47 mẫu) | `supported` P / R | 0.969 / 0.827 | 0.941 / 0.853 |
| | `contradicted` P / R | 1.0 / 0.533 | 1.0 / 0.6 |
| | `contradicted` qua `R` / qua snippet | 0.833 / 0.333 | 0.917 / 0.389 |
| | câu sai có `misconceptions` / `technical_accuracy` TB | 0.933 / 0.8 | 0.833 / 0.93 |
| | `R` chặn nhầm câu đúng | 0 | 0 |

Chênh trong mức nhiễu 3 vòng (~±0.1 ở nhóm `long_s`). Câu sai có `misconceptions` 0.933 → 0.833 là điểm cần theo dõi: v8 nhắc "đừng hạ điểm vì khó đọc", có thể làm model dễ dãi hơn với câu sai.

## 3. Thay đổi trong v8
- Đoạn sau luật 9: câu trả lời có thể là bản ghi nhận dạng giọng nói; chấm như thể thuật ngữ đã viết đúng, không hạ `technical_accuracy` / `relevance` vì chính tả, không gắn `dont_know` / `off_topic` vì khó đọc; `quote` vẫn chép nguyên văn.
- Trong `dont_know`: câu sai là `answered` có `misconceptions`.
- Một mẫu neo junior ghi từ giọng nói (chủ đề index, không trùng golden).
- Ví dụ phiên âm trong prompt cố ý **không** dùng thuật ngữ của bộ nhiễu (đã kiểm trùng cụm từ), để số đo không lạc quan.

## 4. Ngưỡng QUAL17 (đề xuất, chờ owner chốt)

| Chỉ số | Ngưỡng đề xuất | v8 |
|---|---|---|
| `same_answer_type` | ≥ 0.9 | 0.917 đạt |
| `|mean_diff|` | ≤ 0.5 | 1.18 chưa |
| `within_1` | ≥ 0.8 | 0.417 chưa |
| Golden thường ±1 band | không giảm quá 5 điểm % (D09 §10.3) | đạt |

Lý do: đổi `answer_type` làm hỏng luồng phiên nên phải gần như không xảy ra; chênh 0.5 điểm thang 10 bằng nửa band, nhỏ hơn sai số ±1 band giữa model và người.

## 5. Hướng tiếp theo
1. **Chuẩn hóa thuật ngữ trước Evaluator** (đề xuất): bảng phiên âm → thuật ngữ cho từ phổ biến, áp ở FE / interview-service trước `/answer` hoặc trong ai-service chỉ cho đầu vào Evaluator. Rẻ, deterministic, nhưng bảng không bao giờ đủ; cần bộ nhiễu riêng để đo, không lấy từ 12 mẫu này.
2. **Lặp prompt (v8b)**: thêm mẫu neo strong ghi từ giọng nói. Rủi ro khớp quá bộ 12 mẫu; ~$0.05–0.3 mỗi vòng.
3. **Đo bản ghi STT thật** khi DE có tài khoản STT (gate 22/11 điều kiện e): bộ nhiễu hiện do AIE tự viết, nặng hơn hoặc nhẹ hơn STT thật đều có thể.

## 6. Bảng tra thuật ngữ trước Evaluator (04/11, chiều)

**Cách làm:** `app/stt_terms.py` có ~150 thuật ngữ, mỗi thuật ngữ 1–4 dạng phiên âm ("đốc cơ" → Docker, "thờ rét" → thread, "con ca rừn hát mắp" → ConcurrentHashMap). `LlmEvaluator` đổi `answer` sau precheck (manipulation / dont_know vẫn chạy trên bản gốc), nên LLM, hậu kiểm `quote` và fallback mock cùng thấy một bản. Không gọi LLM, không đổi contract. Log `evaluator_stt_terms` khi có thay đổi (không ghi nội dung).

**Chặn đổi nhầm:**
- Mọi dạng phiên âm ≥ 2 âm tiết. Âm tiết đơn ("cát", "sét", "nốt", "ghét", "mít") trùng từ tiếng Việt nên không đổi. Đã bỏ "ăn mau", "đi bi", "chân kinh", "em bé đinh" vì là cụm tiếng Việt thường.
- Khớp nguyên từ, không phân biệt hoa thường, chịu NFD và nhiều khoảng trắng; dạng dài khớp trước.
- Quét 5 755 câu gõ tay có sẵn (117 golden, 5 494 câu trả lời trong log mô phỏng `plans/reports/*.json`, 144 từ `data-pipeline`): **0 câu bị đổi**. Test `test_typed_golden_answers_are_unchanged` giữ điều này cho golden. Vì câu sạch không đổi, golden thường và golden có tài liệu không cần chạy lại.

**Review độc lập (code-reviewer):** sửa lỗi `KeyError` khi `IGNORECASE` khớp ký tự `lower()` không trả về ("ſin cờ rô nai", "İn tơ phây"): lỗi nằm trước `try` nên làm `/next-turn` trả 500; nay giữ nguyên đoạn đó. Bỏ thêm dạng trùng tiếng Việt: "con bách" / "cô bách" ("nuôi con bách thú"), "gia va", "cu ki", "pai lai" (gõ không dấu), "dây sơn", "in đích". Cột "sau review" là bảng cuối cùng.

**Kết quả** (gpt-4o-mini, 3 vòng, ~$0.11 cho 3 lần chạy):

| Chỉ số | v7 | v8 | v7 + bảng | v8 + bảng | v8 + bảng sau review | Ngưỡng đề xuất |
|---|---|---|---|---|---|---|
| `same_answer_type` | 0.75 | 0.917 | 1.0 | 1.0 | **1.0** | ≥ 0.9 |
| `mean_diff` | −1.51 | −1.18 | −0.75 | −0.61 | **−0.67** | trị tuyệt đối ≤ 0.5 |
| `max_abs_diff` | 3.8 | 2.93 | 3.8 | 2.97 | 2.73 | |
| `within_1` | 0.333 | 0.417 | 0.667 | 0.75 | **0.75** | ≥ 0.8 |
| ±1 band (24 mẫu) | 0.861 | 0.893 | 0.927 | 0.934 | 0.924 | |

| Mẫu | Sạch → nhiễu (v8 + bảng) | Còn mất ở |
|---|---|---|
| q01-strong | 9.4 → 6.4 | tech 4 → 2.3, comp, exte, rele |
| q04-strong | 6.9 → 6.2 | tech 3 → 2 |
| q06-strong | 7.7 → 6.2 | tech 3 → 2, exte, rele |
| q11-strong | 9.4 → 7.5 | tech 4 → 2.3, exte |
| Còn lại (8 mẫu medium / weak) | lệch ≤ 0.6 | |

Đọc:
- Bảng sửa hết các lần đổi `answer_type` (q06-weak hết `dont_know`) và đưa medium / weak về gần bản sạch.
- Câu strong vẫn mất 0.7–3 điểm. Phần còn lại của câu strong là âm tiết đơn và tên API cụ thể không có trong bảng ("pút", "cát", "sét en ích", "com piu ịp áp sừn", "rít phai xinh", "diu dơ ai đi"), cộng với việc không có dấu câu. Đây là giới hạn thật của bảng tra: thêm các dạng này vào bảng sẽ khớp quá bộ 12 mẫu.
- v8 vẫn tốt hơn v7 khi có bảng (−0.61 so với −0.75; 0.75 so với 0.667), nên giữ cả hai.
- Chưa đổi: RAG theo lượt (`turn_snippets`) và `topic_turns` vẫn dùng câu gốc; `evidence.quote` chứa thuật ngữ đã đổi nên có thể không khớp chữ với câu `interview-service` lưu.

**Vì sao số lạc quan:** bảng lấy thuật ngữ từ topic catalog và từ vựng lập trình chung, không chép từ bộ nhiễu, nhưng người viết bảng đã đọc bộ nhiễu, và cả hai cùng một miền. Phần lớn thuật ngữ đa âm tiết trong bộ nhiễu có trong bảng ("bucket", "thread-safe", "refresh", "update", "delete" nằm trong nhóm từ vựng chung). STT thật có thể viết khác ("đốc kơ", "Đốc-cơ", hoặc ghi thẳng "Docker"). Cần đo lại trên bản ghi STT thật trước khi coi QUAL17 là đạt.

## 7. "STT tốt": thuật ngữ đúng, chỉ mất dấu câu (04/11)

`python -m evals.run_evaluator --stt plain` tạo từ 12 mẫu sạch một bản giống STT tốt (`spoken_plain`): giữ thuật ngữ đúng chính tả, bỏ dấu câu, viết thường (cả thuật ngữ: "hashmap", "useeffect"), thêm "à" đầu câu và "ừm" ở ranh giới câu thứ hai, "[]" đọc thành "mảng rỗng". Sinh bằng code nên không có thiên lệch của người viết. v8, 3 vòng, ~$0.03:

| Chỉ số | Bộ nhiễu phiên âm, v8 + bảng | STT tốt, v8 | Ngưỡng đề xuất |
|---|---|---|---|
| `same_answer_type` | 1.0 | **1.0** | ≥ 0.9 |
| `mean_diff` | −0.67 | **−0.10** | trị tuyệt đối ≤ 0.5 |
| `max_abs_diff` | 2.73 | **0.6** | |
| `within_1` | 0.75 | **1.0** | ≥ 0.8 |
| ±1 band (24 mẫu) | 0.924 | 0.986 | |

Lệch lớn nhất: q11-strong 9.4 → 8.8 (tech 4 → 3), q01-weak 3.1 → 2.5. Câu strong khác giữ nguyên điểm.

Đọc:
- Mất dấu câu, viết thường, từ đệm **không** làm Evaluator chấm sai: đạt cả ba ngưỡng đề xuất.
- Gần như toàn bộ phần mất điểm ở mục 1 và 6 là do thuật ngữ Anh bị phiên âm.
- Hệ quả cho việc chọn nhà cung cấp STT (QUAL16): chỉ số quan trọng nhất là **tỉ lệ ghi đúng thuật ngữ Anh** trong câu tiếng Việt, không phải tỉ lệ lỗi từ tổng. STT ghi đúng thuật ngữ thì QUAL17 gần như chắc đạt; bảng tra và đoạn prompt v8 chỉ còn là lưới an toàn.
- Chưa đo: lỗi nhận dạng ở từ tiếng Việt làm đổi nghĩa ("xóa" thành "đeo", mất "không"). Loại này Evaluator chấm sai là đúng; phải đo ở STT (QUAL16).

## Câu hỏi chưa giải quyết
- Owner chốt ngưỡng QUAL17 ở mục 4?
- Có chấp nhận v8 + bảng tra (gần ngưỡng, lạc quan) làm mốc cho tới khi có bản ghi STT thật không?
- RAG theo lượt và `topic_turns` có nên dùng câu đã đổi không (truy hồi BM25 theo thuật ngữ sẽ trúng hơn)?
- Ai duy trì bảng tra khi có bản ghi thật: AIE thêm dạng từ log STT (cần log chỉ lưu thuật ngữ, không lưu câu)?
- Có giữ v8 làm mặc định ngay (đang là mặc định trên nhánh) dù câu sai có `misconceptions` giảm 0.933 → 0.833?
