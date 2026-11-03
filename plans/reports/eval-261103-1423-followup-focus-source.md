# Follow-up lấy focus từ đâu (Phase C mục 2), 2026-11-03

Đo lại trên log có sẵn, **không gọi LLM**: `eval-sim-interviewer-ab-v4c.json` (28 phiên, Interviewer v4, Evaluator v6), đối chiếu thêm `v3`, `v4`. Phát lại `app/focus.py` (`gap_focus`/`deepen_focus`) trên evaluation đã log. Script ở scratchpad, không commit (đọc câu kho DE).

## Kết quả
- 76 lượt follow-up/hint ở `technical`; 58 lượt ngay sau câu kho có đáp án chuẩn.
- **Focus nằm trong đáp án chuẩn: 33/58 (57%).** 25 lượt còn lại hỏi ý không có trong đáp án của câu vừa hỏi.
- Nguyên nhân chính: trên 67 lượt câu kho có đáp án, Evaluator trả 107 `missing_points`, **44 (41%) là key point catalog không có trong đáp án** (v3: 57/126, v4: 51/112, ổn định). Ví dụ: hỏi "đọc input từ console", missing là "Nêu cách resize và load factor" → follow-up hỏi resize HashMap.
- Lý do: prompt Evaluator v6 tự mâu thuẫn. Luật 11 nói có `reference_answer` thì `missing_points` là ý chính của đáp án; phần định dạng đầu ra nói `missing_points` là "ý trong key_points ứng viên chưa nêu".
- Phụ: 18/67 câu kho không chạm key point catalog nào của topic (câu lệch topic, Phase B remap sẽ sửa).
- Luật 10 (trả lời tốt) chỉ chạy 3 lần; mẫu `DEPTH` 0 lần. Không phải vấn đề chính.

## Mô phỏng sửa bằng code
Lọc `missing_points` chỉ giữ ý có trong đáp án chuẩn (`covers(ref, m)`, ≥ 50% từ nội dung) khi có đáp án: focus trong đáp án **33/58 → 47/58 (81%)**. Ý bị bỏ chuyển sang `follow_up_focus` của Evaluator hoặc key point catalog chưa nêu. Bộ lọc không bỏ nhầm ý nào lấy từ đáp án (nhóm "không phải key point, không có trong đáp án" = 0 ở v4c).

## Giới hạn
- Phát lại gần đúng: `used` của topic tính lại, so trùng bằng Jaccard 0.8 và phủ từ 50%, không phải focus thật đã log.
- Ứng viên giả lập LLM, 28 phiên. Chưa đo câu follow-up sinh ra có tốt hơn không, chưa có nhãn người.
- `missing_points` cũng vào báo cáo ("Còn thiếu: ..."), nên lỗi này ảnh hưởng cả Reporter.

## Lọc bằng code: bỏ, vì heuristic sai hai chiều
Đọc mẫu: giữ nhầm key point catalog vì đáp án dài 1.200–1.800 ký tự dễ trùng từ ("SOLID giúp mã dễ bảo trì" cho câu encapsulation); bỏ nhầm ý đúng của đáp án được diễn đạt lại (v3: "Phân biệt checked và unchecked" cho câu phân cấp Exception, PM2/CORS cho câu package Express). Con số 81% ở trên là lạc quan. Chọn sửa prompt.

## Evaluator v7 (nhánh `thang/evaluator-v7`, bản nháp, chưa đo)
- Phần đầu ra: `missing_points` khi có `reference_answer` chỉ lấy ý của đáp án (luật 11), không lấy key_points; không có đáp án thì như cũ. Đây là điểm review v6 đã nêu (câu hỏi mở 6 của `eval-261102-1109-evaluator-v6.md`).
- Thêm một mẫu neo trích nguồn: thiếu ý của `R` thì ghi ý đó, không ghi key point `R` không nói.
- Prompt dài thêm ~90 token (~+2.6% input mỗi lượt Evaluator). Test cập nhật bản mới nhất v7: 759 pass, 8 skip.

## Ước chi phí đo v7
Giá giả định gpt-4o-mini $0.15 / $0.60 mỗi 1M token (`evals/pricing.json`, chưa kiểm lại giá OpenRouter). Token lấy từ lần đo v6 ngày 02/11.

| Bước | Lấy số từ | Chi phí | Thời gian |
|---|---|---|---|
| Golden chính 51 × 3 | v6: 532k in, 27k out | ~$0.10 | vài phút |
| Golden có tài liệu 32 × 3 | v6: 376k in, 14k out | ~$0.07 | vài phút |
| Chạy v6 song song trên hai golden (đối chứng trôi model) | như trên | ~$0.17 | |
| Mô phỏng full matrix 28 phiên, giống v4c (so trực tiếp 41%) | v4c: $0.0112/phiên phía server | ~$0.31 | ~75–80 phút (concurrency 4) |
| Ứng viên giả lập trong mô phỏng | không ghi trong `cost_usd`; giả định ~$0.0015/phiên | ~$0.04 | |
| **Một vòng** | | **~$0.70** | ~1.5 giờ |

Nếu phải chỉnh prompt thêm (v6 cần 4 vòng): mỗi vòng thêm ~$0.50 (bỏ đối chứng v6). Xấu nhất 3 vòng ~$1.7. Judge `supported` không cần chạy lại vì v7 không đổi luật trích nguồn.

Ngưỡng đặt trước khi chạy:
- `missing_points` không có trong đáp án, trên lượt câu kho có đáp án: 41% → ≤ 15%.
- Focus follow-up/hint nằm trong đáp án: 57% → ≥ 80%.
- ±1 band tụt ≤ 0.02; `contradicted` qua `R` ≥ 0.9; chặn nhầm câu đúng 0.
- Chi phí phiên tăng ≤ 5%.

## Kết quả vòng 1 (LLM thật, 03/11)
JSON (gitignored): `eval-evaluator-{main,sourced}-{v6,v7}-261103.json`, `eval-sim-evaluator-v7-261103.json`. Golden chạy v6 và v7 cùng lúc; mô phỏng v7 so với v4c (02/11, cùng matrix full, cùng Interviewer v4). Lần mô phỏng đầu quên `AGENT_*_MODE=llm` nên chạy mock, đã bỏ, chạy lại.

| Chỉ số | v6 | v7 | Ngưỡng |
|---|---|---|---|
| `missing_points` không có trong đáp án (lượt câu kho có đáp án) | 44/107 (41%) | 31/98 (32%) | ≤ 15%: **trượt** |
| Focus follow-up/hint nằm trong đáp án | 33/58 (57%) | 36/55 (65%) | ≥ 80%: **trượt** |
| ±1 band (golden chính) | 0.961 | 0.970 | tụt ≤ 0.02: đạt |
| Lệch khoan dung | −0.283 | −0.280 | ±0.3: đạt |
| `answer_type`, thứ tự band, injection | 0.977, 1.0, 6/8 | 0.977, 1.0, 6/8 | |
| `supported` P / R (golden có tài liệu, 47 mẫu) | 0.953 / 0.836 | 0.968 / 0.813 | |
| `contradicted` qua `R` / qua `S` | 0.833 / 0.389 | 0.833 / 0.353 | ≥ 0.9: trượt ở **cả hai** |
| Chặn nhầm câu đúng có `R` | 0 | 0 | 0: đạt |
| Chi phí phiên (mô phỏng) | $0.01121 | $0.01082 | tăng ≤ 5%: đạt |

- v7 giảm lỗi nhưng không đủ. Còn lọt rõ ràng ở câu đúng topic: hỏi "Heap và Stack khác nhau" mà missing là "Tuning và đọc GC log", hỏi bean scope mà missing là "constructor vs field injection". 26/31 lượt lọt ở câu kho đúng topic, 5/31 ở câu lệch topic.
- `contradicted` qua `R` 0.833 thấp hơn 0.92 ngày 02/11 vì golden có tài liệu đã thêm mẫu (32 → 47); v6 chạy cùng lúc cũng 0.833, nên không phải do v7.
- Mô phỏng: phân biệt persona 8/8 nhóm (v4c 7/7), `gap_recall` 0.84 (0.87), tỉ lệ ý `supported` 0.19 (0.25), `low_confidence` 0.67 (0.63). Một lần chạy mỗi bản, chưa tách được khỏi nhiễu.
- Golden loại 1–3 lần chạy `degraded` mỗi bản do `LlmTimeoutError` (4 tiến trình chạy song song).
- Chi phí thực tế: ~$0.65 (golden ~$0.25 tính cả cached token, mô phỏng ~$0.31 theo giá chưa trừ cache, ứng viên giả lập ~$0.08 cho hai lần chạy).

## Hướng vòng 2
Model vẫn bám `key_points` vì chúng nằm trong đầu vào. Code không cần `key_points` khi có đáp án chuẩn (`app/agents/evaluator.py`: trần `completeness` lúc có `R` tính theo số ý có quote). Đề xuất: khi có `reference_answer`, không gửi `key_points` cho Evaluator (chỉ với v7). Cần thêm một vòng đo (~$0.50).

## Kết quả vòng 2: bỏ `key_points` khi có đáp án (03/11)
Thử `hides_key_points` (v7 trở lên) trong `app/agents/evaluator.py`, prompt ghi `topic` không có `key_points` khi có `reference_answer`. **Đã gỡ khỏi nhánh** sau khi chọn v7 vòng 1. JSON: `eval-evaluator-{main,sourced}-v7b-261103.json`, `eval-sim-evaluator-v7b-261103.json`. Chỉ chạy v7, so với v6 và v7 vòng 1 cùng ngày.

| Chỉ số | v6 | v7 vòng 1 | v7 vòng 2 | Ngưỡng |
|---|---|---|---|---|
| `missing_points` key point catalog không có trong đáp án | 41% | 32% | **9% (6/68)** | ≤ 15%: đạt |
| Focus follow-up/hint nằm trong đáp án | 57% | 65% | **80% (39/49)** | ≥ 80%: đạt (vừa chạm) |
| ±1 band, lệch khoan dung | 0.961, −0.283 | 0.970, −0.280 | 0.970, −0.276 | đạt |
| `answer_type` đúng | 0.977 | 0.977 | 0.953 | |
| `contradicted` P / qua `R` | 1.00 / 0.833 | 1.00 / 0.833 | 0.85 / 0.917 | |
| **Chặn nhầm câu đúng có `R`** | 0 | 0 | **1/8 mẫu (3/3 lần)** | 0: **trượt** |
| Chi phí phiên | $0.01121 | $0.01082 | $0.01058 | đạt |

- Mẫu bị chặn oan là `g25-nos-R-threadstate`: đáp án chuẩn dùng mô hình thread cũ (5 trạng thái), ứng viên trả lời đúng theo `Thread.State`. Khi còn `key_points` ("Dùng enum Thread.State để xem") model không bác; bỏ đi thì model chỉ còn đáp án sai làm căn cứ và bác 3/3, kéo `technical_accuracy` ≤ 1. Cùng kiểu lỗi với mục kho `cr-lz-python-basics-8979143a` (DE chưa sửa).
- Tức `key_points` vừa là nguồn lọt `missing_points`, vừa là đối trọng khi đáp án chuẩn sai hoặc lỗi thời.
- Mô phỏng: phân biệt persona 6/8 nhóm (vòng 1 8/8, v4c 7/7), `gap_recall` 0.87; mô phỏng không có lượt nào bị `R` bác (cả ba lần chạy). Một lần chạy, chưa tách khỏi nhiễu.
- Golden chính loại 4 lần `degraded` (`LlmTimeoutError`).
- Chi phí vòng 2 ~$0.48; tổng hai vòng ~$1.13.

## Đề xuất
Dùng **v7 vòng 1** (chỉ sửa prompt, không tụt chỉ số nào), bỏ thay đổi code vòng 2. Bỏ `key_points` khi có đáp án đổi một lỗi follow-up lấy một lỗi chấm điểm (điểm câu đúng bị ép ≤ 1). Làm lại sau Phase B, khi DE đã sửa đáp án lỗi thời: chạy lại riêng golden có tài liệu, g25 phải hết bị chặn.

## Câu hỏi còn mở
- Đã chọn v7 vòng 1 (03/11). Vòng 2 làm lại sau Phase B.
- Câu hỏi 3 của báo cáo v6 (có giữ luật `R` bác thì ép `technical_accuracy ≤ 1`) ảnh hưởng trực tiếp tới lựa chọn này.
- Mẫu neo vẫn dùng chủ đề index (gần mẫu golden g26, review v6 đã nêu rò rỉ); chưa đổi để giữ thay đổi nhỏ.
