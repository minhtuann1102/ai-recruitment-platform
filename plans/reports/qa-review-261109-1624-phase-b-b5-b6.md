# Duyệt Phase B: B6 (54 câu mới) + B5 (mẫu 40 nửa câu tách đôi), 2026-11-09

Spec 005 T065, T066. Reviewer: 3 subagent Opus (rubric `interview-qa-review` v2), mỗi lô 1 câu mồi cài lỗi (khóa
chỉ ở máy DE). Kết quả gốc: scratchpad `review/results-r1|r2|r3.json`.

## Câu mồi: 3/3 bị bắt
| Lô | Câu mồi | Lỗi cài | Reviewer |
|---|---|---|---|
| R1 (30 câu B6 AI) | b6-1-18 | MCP: 1 client nối nhiều server (spec: 1:1) | fix, critical, trích đúng spec |
| R2 (24 câu B6 AI/Java/Python) | b6-3-00 | Spring: checked exception rollback mặc định | fix, critical, trích đúng docs Spring |
| R3 (42 nửa câu B5) | de-qa-1173 a/b | tráo câu hỏi hai nửa | fix cả hai, nêu đúng lỗi |

## Trích dẫn (tải lại trang, `verify_quotes.py`)
- Bản nháp B6: 317/317 found.
- Reviewer: R1 203 found, 4 unreadable (PDF arXiv); R2 160 found, 2 unreadable (blog Hugging Face, PDF). 0 not_found.

## B6: 52 câu thật (trừ câu mồi)
- ok 44, fix 8, drop 0. Độ khó: mọi nhãn easy/medium đúng.
- Fix:
  - b6-1-14 (major, độ tin cậy thấp): lời khuyên đặt tài liệu trước, câu hỏi sau là của Anthropic nhưng viết như quy tắc chung; OpenAI GPT-4.1 khuyên khác.
  - b6-1-22 (major, outdated): hủy request khi đóng stream Streamable HTTP chỉ đúng từ MCP 2026-07-28; bản 2025-11-25 ngược lại; đáp án không nêu revision.
  - b6-1-26 (major): bắt đọc thuộc 10 mục OWASP LLM Top 10, không chấm được; có câu hỏi thay thế.
  - b6-1-00, -01, -08, -13 (major, interview fit): đáp án có phần câu hỏi không hỏi; b6-1-08 thêm `budget_tokens` đã cũ trên Claude mới.
  - b6-2-02 (major, outdated): chế độ ép gọi tool không áp dụng cho mọi model.
- Minor (ý phụ không được hỏi, vendor-specific): khoảng 15 câu, sửa cùng lúc.

## B5: 40 nửa câu thật (trừ câu mồi)
| Nhóm | ok | fix | hạ medium |
|---|---|---|---|
| 20 nửa luna gắn cờ | 2 | 12 | 6 |
| 20 nửa ngẫu nhiên | 15 | 5 | 0 |
- Cờ luna dự báo tốt (18/20 cần xử lý). Nhóm ngẫu nhiên 25% cần sửa → ước ~55/222 nửa chưa duyệt cần sửa.
- Fix chủ yếu: thêm ý vào câu hỏi, chuyển/cắt khối đáp án giữa hai nửa (1006/b, 1060/b, 1054/b, 1003/b), làm rõ ngữ
  cảnh (1158/b). Reviewer đề xuất hạ medium 13 nửa (6 chỉ hạ + 7 hạ sau khi sửa, gồm 1173/a là câu mồi → 12 thật);
  worker đã sửa và hạ đúng 12 nửa.

## Cập nhật sau duyệt (2026-11-09)
- DE chốt: không duyệt thêm 222 nửa; worker Sonnet áp sửa (B5 26 nửa, B6 38 cặp, trích dẫn 306/306 found).
- Câu hỏi 2 đã chốt: đáp án MCP nêu cả revision 2025-11-25 và 2026-07-28 khi hành vi khác nhau.

## Câu hỏi còn mở
1. B5: duyệt nốt 222 nửa còn lại bằng reviewer Opus, hay chỉ sửa 40 nửa đã duyệt? (DE)
2. MCP: kho nhắm revision 2026-07-28 hay chấp nhận cả 2025-11-25? (DE)
3. Evaluator có coi một số ý của đáp án là ý cộng điểm (không bắt buộc) được không? Nếu được, nhiều lỗi "ý không được
   hỏi" hạ xuống minor. (AIE)
