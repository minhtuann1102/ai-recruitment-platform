# Giảm độ trễ: Evaluator gọn, Planner nhanh, 2026-10-22

So sánh 3 lần chạy harness tầng 3 với LLM thật, cùng cấu hình: ma trận quick (9 persona), simulator LLM, `gpt-4o-mini` qua OpenRouter, in-process, phiên 20 phút, RAG tắt. Lần 1 là số đo gốc ([eval-sim-20261022-llm-quick.md](eval-sim-20261022-llm-quick.md)).

| Lần | Thay đổi |
|---|---|
| 1 | Gốc: Evaluator v1 (`max_tokens` 350), Planner v1 (`max_tokens` 2500) |
| 2 | Evaluator v2: bỏ tag (code sinh), quote 3–12 từ, `covered ≤ 3`, `missing ≤ 2`, `max_tokens` 250. Planner v2: code sinh `opening_hint`, `backup_question`, `key_points` 3–4 ý, `max_tokens` 1500 |
| 3 | Như lần 2, thêm: Planner bỏ trống `key_points` thì code bù từ catalog thay vì gọi lại LLM; Evaluator `max_tokens` 300 (đo lần 2: output tối đa 219) |

## Kết quả (đã đo)

| Chỉ số | Lần 1 | Lần 2 | Lần 3 | Mục tiêu |
|---|---|---|---|---|
| Một lượt tới token đầu, P50 / P95 | 6.0 / 9.7 s | 5.0 / 8.8 s | **5.0 / 7.7 s** | 3.5 / 6 s (chưa đạt) |
| Evaluator P50 / P95 | 4.8 / 7.5 s | 3.4 / 5.6 s | **3.6 / 5.2 s** | — |
| Output Evaluator P50 / P95 / max (token) | 186 / 247 / 270 | 147 / 172 / 219 | 144 / 197 / 249 | ≤ 300 |
| Interviewer P50 | 2.0 s | 1.8 s | 2.0 s | — |
| Planner P50 / P95 | 13.0 / 17.0 s | 14.3 / 18.0 s | **8.2 / 9.6 s** | hạn 22 s |
| Phiên dùng plan dự phòng | 2/9 (quá hạn) | 5/9 (`key_points` rỗng) | **0/9** | — |
| Tỉ lệ call có fallback | 2.7% | 4.4% | **0%** | < 2% |
| Reporter P50 / P95 | 16.5 / 30.0 s | 20.0 / 25.2 s | 15.9 / 20.4 s | 60 s |
| Chi phí mỗi phiên (giá giả định) | $0.0073 | $0.0075 | $0.0071 | cảnh báo > $0.10 |

Hành vi không xấu đi: câu lặp 0%, recall lỗ hổng 100%, điểm mạnh sai 0, injection không tăng điểm ở cả 3 lần. Điểm persona giỏi Java junior 6.2 / 5.7 / 5.7, yếu 1.5 / 1.3 / 1.1 (khoảng cách 4.7 / 4.4 / 4.6). Tỉ lệ quỹ đạo độ khó đúng chiều 67% / 33% / 33% là trên 3 phiên nên chưa kết luận được.

## Nhận xét
- Bỏ phần LLM tự viết những gì code làm được (tag, câu hỏi dự phòng, gợi ý mở đầu) giảm ~25% thời gian Evaluator và ~37% thời gian Planner mà không thấy giảm chất lượng ở cỡ mẫu này.
- Lần 2 cho thấy rút gọn prompt có thể làm LLM bỏ trống trường bắt buộc; sửa bằng code bù (rẻ hơn gọi lại LLM).
- Vẫn chưa đạt PERF01 (P50 3.5 s). Bước tiếp theo theo D08 §9.2: cho Interviewer chạy song song với Evaluator ở lượt mà policy không cần điểm mới, hoặc thử model nhanh hơn cho Evaluator (phải chạy lại golden set trước khi đổi).

## Câu hỏi chưa giải quyết
- Chấp nhận P50 ~5 s cho giai đoạn 1 (D4: cải thiện dần) hay ưu tiên làm song song Evaluator và Interviewer ngay?
- Chất lượng chấm của Evaluator v2 so với v1 cần đo trên golden set có nhãn người (chưa có nhãn).
