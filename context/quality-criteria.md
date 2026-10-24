# Tiêu chí chất lượng và golden set (cập nhật 2026-10-24)

## Golden set hiện có

| Bộ | Đo gì | Kích thước | Trạng thái |
|---|---|---|---|
| `evals/evaluator_golden.jsonl` | Evaluator chấm đúng band (mốc ±1 band ≥ 80%, tuần 09–15/11) | 48 mẫu (12 câu × 3 mức + 12 adversarial) | **Chưa có nhãn người** (0/48). `intended_tier` chỉ là ý định người soạn, không phải nhãn. Cần 2 người chấm qua `python -m evals.label_sheet`, rồi `python -m evals.run_evaluator --runs 3` |
| `evals/rag_golden.json` + `rag_golden_holdout.json` | Truy hồi đúng tài liệu (recall@5) | 24 + 32 truy vấn | AIE gán nhãn; **DE chưa duyệt**. Số đo: 1.000 / 0.938 (sau viết lại truy vấn) |
| Câu hỏi của AI (đúng level, tự nhiên) | Interviewer (Q5 trong `docs/ai-service/09`) | **Chưa có** | Chưa có bộ mẫu, chưa có LLM-as-judge |

Hệ quả: hiện **chưa đo được** Evaluator chấm có đúng không, và câu hỏi có hợp level và tự nhiên không. Harness tầng 3 chỉ đo gián tiếp: phân biệt strong/average/weak, lặp câu, ngôn ngữ, độ trễ, chi phí.

## Câu hỏi khớp trình độ ứng viên: hiện dựa vào gì

Toàn bộ là **luật bằng code**, chưa có đo chất lượng:

1. **Chọn topic theo level:** catalog gắn `levels` cho từng topic; Planner chỉ chọn topic hợp level (`topics_for(level)`).
2. **Biên độ độ khó theo level** (`docs/ai-service/01` §2.1): Fresher 1–3, Junior 1–4, Middle 2–4, Senior 2–5; bắt đầu theo `start_difficulty` của plan.
3. **Thích nghi theo câu trả lời:** policy (11 luật, `app/policy.py`) tăng độ khó +1 khi trả lời tốt, giảm −1 khi yếu hoặc "không biết"; có hint, clarify, follow-up có giới hạn theo level.
4. **Câu từ kho DE** (`RAG_QUESTION_BANK`): chọn câu có nhãn độ khó gần độ khó hiện tại (1–2 easy, 3 medium, 4–5 hard), bỏ câu lệch 2 bậc.
5. **Interviewer** nhận `difficulty` (1–5) và diễn đạt; không có kiểm tra sau để biết câu ra có thật sự ở mức đó không.

Điểm yếu đã đo:
- Nhãn độ khó trong kho lệch: LLM chấm lại 150 câu, đồng ý với nhãn DE **69%**, nhãn DE thiên về dễ (46/75 câu "easy" được chấm lại là "medium").
- Kho chỉ 4% câu `hard`: senior thường bị hỏi câu `medium` (xem `context/de-data-assessment.md`).
- Câu trong kho cơ bản hơn câu AI tự đặt: phân biệt ứng viên cấp phiên giảm (thứ tự đúng 8/8 → 5/8), xem `plans/reports/eval-261024-1614-rag-question-bank.md`.

## Interviewer chưa tự nhiên: số đo (286 câu, lần chạy `eval-sim-bank-after2`)

| Dấu hiệu | Tỉ lệ |
|---|---|
| Khuôn "Bạn có thể ... không?" | 78% |
| Mở đầu "Giờ mình sang phần ..." | 21% |
| Mở đầu "Mình muốn hỏi ..." | 16% |
| Nhắc lại câu ứng viên vừa nói ("Bạn đã/vừa nêu ...") | 23% |
| Độ dài trung bình | 31.5 từ (văn nói nên ≤ 25) |

Thêm: lượt `hint` thường là **câu hỏi mới** chứ không phải gợi ý cho câu cũ.

## Tiêu chí đề xuất (giai đoạn tiếp theo, xem `context/next-phase-plan.md`)

| Tiêu chí | Cách đo | Ngưỡng |
|---|---|---|
| Evaluator đúng band | Golden set 48 (+12 câu từ kho có đáp án chuẩn), 2 người chấm | ±1 band ≥ 80%, Cohen κ giữa 2 người ≥ 0.6 |
| Câu hỏi đúng level | Bộ 60 câu từ transcript, người chấm "dễ quá / vừa / khó quá" theo level; LLM-judge hiệu chỉnh theo người | "vừa" ≥ 75%; judge đồng ý người ≥ 0.7 |
| Câu hỏi tự nhiên (Q5) | LLM-judge 1–5 + người xem mẫu | TB ≥ 4.0 |
| Văn phong (code, chạy mỗi lần harness) | Tỉ lệ khuôn "Bạn có thể ... không?", độ dài, độ đa dạng câu mở đầu | ≤ 40%; ≤ 25 từ; không câu mở đầu nào > 15% |
| Hint đúng nghĩa | Judge: lượt hint có gợi ý cho câu trước, không đổi câu | ≥ 90% |
