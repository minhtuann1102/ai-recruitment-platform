# Vì sao Evaluator v6 trượt recall 0.58 (2026-11-02)

Nối tiếp `eval-261102-1109-evaluator-v6.md`. Dữ liệu: 106 lượt technical có tài liệu của `eval-sim-06-v6-r5/r6`. Replay Evaluator trên lượt đã lưu, cùng input, gpt-4o-mini, đo bằng `judge_support` v2. Không đổi code hay prompt sản phẩm. Script thử nghiệm không đưa vào repo; số thô: `plans/reports/eval-recall-*-261102.json` (gitignored).

## Kết luận
- **Recall thấp là thật**, không phải judge chấm dễ. Một người chấm mù độc lập (LLM khác, 70 ý) cho 0.51–0.61 tùy cách tính.
- **Trượt ở tài liệu `S`, không phải ở `R`:** recall qua `R` 0.80–0.84, qua `S` 0.16–0.35.
- **Sửa prompt không tới được 0.80:** biến thể tốt nhất đạt 0.64 và đánh đổi precision 0.96 → 0.88. Thêm `source_quote` còn tệ hơn.
- **Thứ thực sự nâng recall là tách việc:** một call riêng chỉ để tìm câu căn cứ, cùng model, đạt recall ~0.90, chi phí +5%.
- **Đề xuất: chưa làm gì ở đường nóng.** 0.80 là ngưỡng tôi tự đặt ở vòng 3, không nằm trong Success Criteria Phase 05, và recall không ảnh hưởng điểm. Nên làm ngay 2 việc rẻ (golden, `confidence`). Bước kiểm tra lần hai chỉ làm nếu sản phẩm cần trích nguồn theo từng ý.

## Con số 0.58 có đáng tin không
Người chấm không biết nhãn của model và judge. Mẫu: 38 ý `no_source` judge nói có căn cứ, 16 ý `no_source` judge nói không, 16 ý `supported`.

| Nhóm | n | Cùng nghĩa | Một phần | Chỉ cùng chủ đề | Không có khẳng định |
|---|---|---|---|---|---|
| `no_source`, judge `entailed` | 38 | 22 | 11 | 3 | 2 |
| `no_source`, judge không | 16 | 1 | 4 | 10 | 1 |
| `supported` | 16 | 12 | 3 | 1 | 0 |

- Judge đúng ở 33/38 ca nếu tính cả "một phần", nên 39 ý bị bỏ sót phần lớn là bỏ sót thật.
- Quy về toàn bộ: recall 0.61 (chỉ "cùng nghĩa"), 0.51 (tính cả "một phần"). Precision `supported` 0.75 và 0.94, n = 16 nên khoảng rất rộng.
- 46/86 `no_source` là đúng: tài liệu truy hồi không nói ý đó. Phần này là giới hạn của kho và retrieval, không phải lỗi nhãn.

## Nguyên nhân
1. **`S` khó hơn `R`.** `R` là đáp án của đúng câu vừa hỏi. `S` là chunk nhiều ý, trung vị 830–900 ký tự, p90 ~1.800. Lượt không có `R` recall 0.39, có `R` 0.66. Lượt `hint` 0/10 `supported`.
2. **Mẫu neo dạy sai.** Trong prompt v6, cả 2 mẫu `supported` đều trích `R`, còn mọi mẫu có `S` đều là `no_source`. Thêm 2 mẫu `S` được `supported` nâng recall `S` từ 0.17 lên 0.31 ở 3 lần chạy. Đây là nguyên nhân thật nhưng chưa phải toàn bộ.
3. **Một call làm quá nhiều việc.** Evaluator vừa chấm 4 tiêu chí, vừa tìm quote, vừa trích nguồn trong ~143 token đầu ra. Cùng gpt-4o-mini, call chỉ làm việc tìm câu căn cứ nhận lại 43/80 ý. Giới hạn nằm ở nhiệm vụ gộp, không phải ở năng lực model.
4. **Golden không thấy lỗi này.** Tài liệu golden `supported` trung vị 252 ký tự so với 830–900 thật, nên golden báo recall 0.94 còn mô phỏng 0.58. Nhóm g29–g32 thêm hôm nay vẫn ngắn hơn thật. Đã xử lý, xem mục "Cập nhật: sửa golden"; độ dài tài liệu hóa ra không phải yếu tố chính.

Đã loại: model gán nhãn theo cả lượt. Nhãn đồng nhất trong lượt 35/43, judge cũng 32/43; 63 lượt nhìn như chia hai cực chủ yếu vì có hay không có `R`. Judge lệch vì `claim` chép từ `R`: chỉ 3/39 ca.

## Thử nghiệm

| Cách | Precision | Recall | Recall `S` | Giá phải trả |
|---|---|---|---|---|
| v6 chạy gốc | 0.96 | 0.58 | 0.35 | |
| v6 replay, 3 lần | 0.957 ± 0.008 | 0.56 ± 0.03 | 0.17 | |
| Thêm mẫu neo `S`, 3 lần | 0.884 ± 0.011 | 0.644 ± 0.004 | 0.31 | input +1.6% |
| Mẫu neo + `source_quote` (ghi câu căn cứ trước nhãn), 1 lần | 0.962 | 0.51 | 0.39 | output +12%, p50 +0.5 s, recall `R` tụt 0.66 |
| Luật từ vựng: quote trùng ≥ 60% từ khóa một câu | không giảm | +5/39 ý | | gần như không đáng |
| **Call kiểm tra thứ hai cho ý `no_source`** | 0.86 theo judge; 0.93 theo người chấm (0.64 nếu chỉ tính "cùng nghĩa") | **~0.90** | | +$0.00054 mỗi phiên (+5%), 42 call cho 20 phiên, p50 2.0 s, p95 3.5 s |

- Replay tái hiện số gốc: recall 0.56 so với 0.58, nên so sánh tin được. Recall `S` gốc 0.35 cao hơn replay 0.17; chưa rõ lý do, tổng recall không đổi.
- Mẫu neo `S` chỉ dịch dọc đường đánh đổi: +0.08 recall, −0.07 precision. Không tệ, nhưng không thay đổi bức tranh.
- `source_quote` trái với dự đoán của tôi ở câu hỏi mở số 4 báo cáo trước. Hiệu ứng recall chỉ có 1 lần chạy, nhưng chi phí và độ trễ không cần lặp.
- Call thứ hai dùng cùng tiêu chí với judge nên số theo judge có phần vòng tròn; số người chấm là độc lập nhưng mẫu nhỏ. Vài ca nâng nhãn rõ là sai, ví dụ quote "Unhandled rejection là..." ghép với định nghĩa Promise.

## Recall thấp ảnh hưởng gì
- **Điểm:** không. `no_source` không vào `apply_caps`, ±1 band 0.961–0.965 như v5.
- **Tài liệu trong báo cáo:** số lượng gần như không đổi, 3.5 so với 3.75 mỗi phiên, vì `report_resources` bù bằng nguồn của plan. Lượt có `sources` giảm từ ~34 xuống ~15 mỗi vòng, tức tài liệu cuối phiên ít gắn với điều ứng viên đã nói hơn. Chưa đo tỉ lệ tài liệu bù.
- **`confidence`:** `low` ở 60% lượt, gần như không còn mang tín hiệu. Hiện chỉ xuất qua API, nhưng ai đọc sẽ hiểu sai.
- **`contradicted` qua `S`:** 0.67 so với 1.00, cùng gốc đọc `S` kém. Đây mới là phần có thể chạm tới chấm điểm, và cần xem riêng.

## Đề xuất, theo thứ tự
1. **Giữ v6, bỏ 0.80 khỏi điều kiện.** Ghi rõ `no_source` nghĩa là "Evaluator không tìm thấy", không phải "kho không có".
2. **Sửa golden:** xong, nhóm `long_s`. Không chép chunk thật được, xem mục "Cập nhật: sửa golden".
3. **Xử lý `confidence` trước khi interview-service đọc:** bỏ khỏi API, hoặc đổi định nghĩa, ví dụ theo việc lượt đó có tài liệu hay không.
4. **Mẫu neo `S`:** gộp vào lần sửa prompt tới, cùng các điểm Low của review, sau khi có golden mới. Chỉ nhận nếu precision judge còn ≥ 0.85.
5. **Call kiểm tra thứ hai:** chỉ làm khi cần trích nguồn đáng tin theo từng ý. `next_turn` không dùng `support` để quyết định hành động, nên về nguyên tắc chạy song song với stream câu hỏi được và không cộng vào TTFT; chưa thiết kế chi tiết. Cần đo lại bằng mô phỏng trước khi nhận.

Không nên: `source_quote` và luật từ vựng.

## Giới hạn
- Người chấm là LLM (Sonnet), 1 người, 70 ý; chưa có nhãn người. Các ca `Runnable` so với `ready` là ranh giới.
- Replay chỉ trên 2 vòng mô phỏng, cùng dữ liệu đã dùng để chẩn đoán. Biến thể chưa chạy lại golden chính nên chưa biết ảnh hưởng ±1 band.
- Call thứ hai đo trên output đã lưu, chưa qua luồng thật.

## Cập nhật: sửa golden (02/11, sau báo cáo trên)
**Đổi đề xuất:** không chép chunk thật vào golden. Repo public, giấy phép tài liệu DE chưa chốt (`support_set.py`, `copy_corpus.py`). 15 mẫu g33–g47 (`cohort: long_s`) có tài liệu tự viết theo hình dạng 240 chunk của lượt không `R` ở r7/r8, 2 vòng chưa dùng để chẩn đoán: mở đầu bằng câu hỏi, list, code, 665–1.655 ký tự (thật: trung vị 964, p90 ~1.800), 2–5 tài liệu mỗi lượt, follow_up hoặc hint, có `topic_turns`. Câu trả lời 161–466 ký tự, ngắn hơn thật (trung vị 549). 8 `supported`, 3 `contradicted`, 4 `no_source`. Người chấm mù (Sonnet) khớp nhãn 15/15 và không thấy lỗi kỹ thuật trong tài liệu; họ chấm bản trước khi thêm lịch sử, sau đó tôi sửa 1 câu của g47 cho rõ `no_source`.

Tất cả số dưới đây 0 degraded. Recall tính theo mẫu.

| Prompt, nhóm | Lần chạy | `supported` P / R | `contradicted` R | `no_source` R |
|---|---|---|---|---|
| v5, `short` | 3 | 0.80 / 0.77 | 0.43 | 0.58 |
| v6, `short` | 3 | 0.96 / 0.92 | 0.76 | 1.00 |
| v5, `long_s` | 3 | 0.56 / 0.96 | 0.33 | 0 |
| **v6, `long_s`** | 3 + 5 | **0.80–0.93 / 0.50–0.63** | **0.11–0.20** | 0.92–0.95 |

- **Golden thấy lỗi nhưng vẫn lạc quan hơn thực tế:** recall 0.50–0.63 so với 0.27–0.48 trên lượt thật. Trên 67 lượt không `R` ở r7/r8, chỉ 19% lượt có ý `supported`, và 49/67 lượt không có ý nào dù có hay không có lịch sử (chưa tách được bao nhiêu lượt thật sự không có căn cứ).
- **v6 hơn v5 rõ ở nhóm mới:** v5 gán `supported` cho cả tài liệu không liên quan (`no_source` recall 0).
- **Độ dài, số tài liệu không phải yếu tố chính:** giữ đúng một tài liệu không đổi kết quả (0.45 so với 0.48, 14 lượt ×3).

**Lịch sử không giải thích được recall thấp.** Mức tụt 0.33 báo trước đó phần lớn là nhiễu: 2 lần đo 3 vòng chạy nối tiếp, 8 mẫu. Chạy lại 7 biến thể cùng lúc, trộn thứ tự, 15 mẫu ×5:

| Biến thể | `supported` P / R | `contradicted` R | Câu sai có misconception | TA câu sai |
|---|---|---|---|---|
| Không lịch sử | 0.91 / 0.73 | 0.67 | 10/15 | 1.27 |
| Có lịch sử | 0.93 / 0.63 | 0.20 | 10/15 | 1.13 |
| Lịch sử cực ngắn | 0.96 / 0.68 | 0.27 | 9/15 | 1.40 |
| Lịch sử khác topic | 1.00 / 0.68 | 0.53 | 10/15 | 1.27 |
| Lịch sử đặt sau `answer` | 1.00 / 0.73 | 0.13 | 10/15 | 1.27 |
| Có lịch sử, `turn_kind` main | 1.00 / 0.48 | 0 | 10/15 | 1.33 |
| Có lịch sử, thêm mẫu neo `S` | 0.90 / 0.70 | 0.07 | 11/15 | 1.07 |

- **`supported`:** chênh 0.10, khoảng bootstrap theo mẫu 0–0.25. Lượt thật, không chọn lọc (67 lượt ×3): 38/201 lượt `supported` ở cả hai điều kiện, số ý tăng 57 → 77, chênh mỗi lượt 0.10, khoảng −0.05 đến 0.29, chưa thấy khác biệt chắc chắn. Chưa judge 20 ý tăng thêm.
- **`contradicted`:** tụt rõ hơn (0.67 → 0.20) và 2 lần đo cùng chiều, nhưng chỉ 3 mẫu, khoảng 0–0.80. Không phụ thuộc độ dài hay vị trí lịch sử. Ở câu sai, lịch sử đẩy ý về `no_source` cả từ `supported` lẫn `contradicted`: ý có nguồn 31/35 → 7/26. Chưa rõ cơ chế; prompt không có luật nào về việc này.
- **Không ảnh hưởng điểm:** misconception 10/15 và TA câu sai gần như giữ nguyên, nên số 4/9 báo trước đó cũng là nhiễu. Trên 730 ý của lượt thật không có `contradicted` nào ở cả hai điều kiện.
- **Mẫu neo `S` chưa có bằng chứng tốt hơn trên golden:** recall +0.07, trong nhiễu, `contradicted` thấp hơn.
- **Lỗi riêng:** g38 (đảo thứ tự thread pool) 0/5 ở mọi biến thể; câu sai dùng đúng thuật ngữ của tài liệu thì v6 không bắt được. g39, g40 cũng thấp ở hầu hết biến thể.
- **Độ nhiễu của golden:** cùng cấu hình, 3 vòng cho 0.50 và 5 vòng cho 0.63. So sánh `long_s` cần ≥ 5 vòng chạy cùng lúc, chênh dưới ~0.15 chưa nói được gì.

**Quyết định:** không đổi prompt hay luồng lịch sử; không áp ngưỡng `contradicted` ≥ 0.70 cho `long_s` vì 3 mẫu không đủ làm ngưỡng.

Nguyên nhân còn lại của khoảng cách golden và thực tế chưa tách được. Giả thuyết chưa kiểm chứng: văn phong chunk thật (gạch đầu dòng cụt, nhiều thuật ngữ) khác tài liệu tự viết. Số thô: `eval-recall-history-*-261102.json`, `eval-evaluator-sourced-{v5,v6}-long-final-261102.json`.

## Câu hỏi còn mở
0. Có cần thêm mẫu `contradicted` cho `long_s` không? 3 mẫu chưa đủ đặt ngưỡng.
1. Owner có cần trích nguồn đáng tin theo từng ý không? Câu này quyết định có làm mục 5 hay không.
2. `confidence`: bỏ hay định nghĩa lại? Cần hỏi interview-service có định dùng không.
3. Có xem riêng `contradicted` qua `S` không?
