# Đo: câu hỏi từ kho interview_qa + đáp án chuẩn (2026-10-24)

Harness tầng 3, ma trận full (24 persona + 5 adversarial), simulator LLM, agent LLM, RAG bật (ai_db Supabase).
File: `eval-sim-bank-before.json` (nhánh `thang/vi-en-language-guard`), `eval-sim-bank-after.json` (bản đầu),
`eval-sim-bank-after2.json` (bản cuối: ưu tiên đúng độ khó, bỏ câu lệch 2 bậc). JSON không commit.

## Kết quả

| Chỉ số | Trước | Sau (bản đầu) | Sau (bản cuối) |
|---|---|---|---|
| Phiên OK | 28/29 (1 lỗi simulator max_tokens) | 29/29 | 29/29 |
| Câu chính technical từ kho | 0 | 72/72 | 72/72 |
| Fallback / lặp câu / sai ngôn ngữ | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| TTFT p50 / p95 (s) | 3.87 / 5.49 | 3.86 / 6.13 | 3.79 / 6.01 |
| Chi phí TB / phiên (USD) | 0.0082 | 0.0082 | 0.0080 |
| Thứ tự strong > average > weak | 8/8 | 7/8 | 5/8 |
| Khoảng cách strong − weak | 4.42 | 4.00 | 4.10 |
| gap_recall (topic không biết vào improvements) | 0.955 | 0.875 | 0.75 |
| Điểm lượt chính, persona biết rõ / một phần / không biết | 4.89 / 4.30 / 0.10 | 5.12 / 4.38 / 1.22 | 5.29 / 4.28 / 1.79 |

Độ khó câu từ kho (bản cuối): fresher 18/18 easy; junior 28/28 easy; middle 13/14 medium; senior: 1 hard, 10 medium,
1 easy ở độ khó 2. Kho chỉ có 186/4.503 câu `hard` (4%).

Interviewer đổi ý câu trong kho: 2/72 (bản đầu), 3/72 (bản cuối), đều là câu "các package Express.js" bị hỏi thành
"middleware". Đã thêm `kept_meaning` (≥ 50% từ của câu gốc còn trong câu hỏi): lượt đó coi là câu AI tự đặt, không chấm
theo đáp án chuẩn; kiểm trên 72 cặp bắt đúng 2–3 câu đó, không bắt nhầm.

## Tách tác động của đáp án chuẩn (cùng câu trả lời, chấm 2 lần)

60 lượt chính lấy từ kho trong `after2`, Evaluator v3 chấm lại có và không có `reference_answer`:

| Persona | Điểm có đáp án | Không có | completeness có / không |
|---|---|---|---|
| biết rõ (20) | 5.13 | 4.79 | 4.62 / 2.75 |
| một phần (19) | 4.32 | 4.24 | 3.95 / 2.37 |
| không biết (21) | 1.59 | 1.16 | 1.55 / 0.71 |
| Khoảng cách biết rõ − không biết | 3.54 | 3.62 | |

## Kết luận

- Đáp án chuẩn **không làm giảm** khả năng phân biệt (3.54 so với 3.62), chỉ nâng `completeness` vì trần mới tính theo
  số ý có quote thay vì tỉ lệ `key_points` của cả topic (trần cũ ép câu trả lời đủ ý của một câu hỏi hẹp xuống thấp).
- Phân biệt ở cấp phiên giảm chủ yếu do **câu trong kho cơ bản, phổ biến** (int vs Integer, JDK/JRE/JVM): persona
  "không biết" do LLM đóng vai vẫn trả lời đúng một phần (1.16 điểm ngay cả khi không có đáp án chuẩn, so với 0.10 khi
  Interviewer tự đặt câu). Một phần là giới hạn của simulator, một phần là thật: câu cơ bản phân biệt kém hơn.
- 8 nhóm so sánh là mẫu nhỏ, dao động giữa hai lần chạy (7/8 rồi 5/8).

## Câu hỏi chưa giải quyết

- Có nên hỏi câu kho cao hơn một bậc so với độ khó hiện tại (junior hỏi medium) để tăng phân biệt?
- Cần người chấm (golden set) để biết chấm theo đáp án chuẩn có sát hơn không; harness chỉ đo được phân biệt.
- DE: gán `topic_id` còn rộng (vd "Route 53" trong topic Linux); kho thiếu câu `hard` cho senior.
