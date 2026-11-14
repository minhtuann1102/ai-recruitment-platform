## Tóm tắt

Phase B của spec 005 (T059–T066): làm sạch topic và độ khó của kho Q&A, bù câu hard đọc được cho senior.

- **Relabel** (`relabel`, `relabel-score`, `relabel-apply`): gpt-6-luna chấm lại topic, độ khó và `interview_style` cho 4.519 cặp crawl. Quyết định nằm ở `data/raw/relabel/decisions.json` và được áp lúc nạp. Không sửa `enriched_qa/`.
  - Bỏ 562 cặp: luna 509, duyệt 27/10 52, DE 1.
  - Chuyển topic 224 cặp.
  - `interview_style=false` 149 cặp.
- **Tách đôi câu hard dài** (B5): 131 câu > 200 ký tự tách thành 262 nửa ≤ 200 ký tự. Nửa a giữ `qa_id` cũ, nửa b có `qa_id` mới, cả hai có `split_from`.
- **Bù topic mỏng** (B6): 54 cặp easy/medium cho 12 topic, thêm 14 câu hard cho các topic senior còn thiếu.

## Kết quả

- `validate --strict`: 0 lỗi. Có 4.178 cặp hợp lệ: easy 2.478, medium 1.390, hard 310.
- Số topic có ≥ 3 câu đọc được qua bộ lọc ngân hàng câu hỏi (`spoken_ok` + có từ chung với topic):
  - senior **58/58** (trước đó 6/58);
  - middle 59/80, junior 51/63, fresher 31/37.
- SC-010: lấy 100 cặp crawl ngẫu nhiên sau khi áp relabel, worker Sonnet chấm mù, kèm 4 câu mồi và cả 4 đều bị bắt. Kết quả main 77, related 23, off 0. **Đạt** theo cách tính DE chốt (main + related ≥ 85%).
- `process` ra 8.356 bản ghi. Test data-pipeline: 397 pass.

## Việc cho AIE sau khi merge

1. **Golden set**: 54 `qa_id` hard đã bị tách đôi đang được dùng trong golden set trên `main` (`rag_golden.json` 23, `rag_golden_holdout.json` 31). Bảng ánh xạ câu cũ → 2 nửa nằm ở `apps/data-pipeline/data/reviews/qa-split-map.json`. Cần cập nhật `relevant`.
2. **Lọc `interview_style`**: ngân hàng câu hỏi nên bỏ cặp có `metadata.interview_style = false` (câu không hợp hỏi phỏng vấn).
3. **Khởi động lại ai-service** sau khi DE chạy `index` để nạp lại BM25. DE sẽ báo khi index xong; cần credit OpenAI cho phần embedding.

## Rủi ro đã biết

- 222/262 nửa câu tách đôi chưa ai đọc từng cặp. Đáp án của chúng chép từ đáp án đã duyệt, nên sai kiến thức ít khả năng xảy ra. Rủi ro chính: đáp án còn ý mà câu hỏi không hỏi. Mẫu 20 nửa có 5 nửa cần sửa, ước khoảng 55/222 nửa. Nếu Evaluator coi những ý này là bắt buộc, ứng viên có thể bị trừ điểm oan. NOTICE trong seed có ghi mức duyệt này.
- 23/100 cặp trong mẫu là "related": cùng mảng nhưng trọng tâm lệch topic. 9 trong số đó là câu JS cơ bản đang gán `fe.js.core-closure-this`, vì catalog không có topic JS chung. Nếu AIE thêm topic này thì lần relabel sau sẽ chuyển được các câu đó.
