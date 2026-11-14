# 005 Phase B: over-trim check on 20 random trimmed halves

Input: `apps/data-pipeline/data/processed/crawl-review-admin/phaseb-261113/overtrim-sample-20.json` (20 items, 22 removed spans).
Machine-readable verdicts: `apps/data-pipeline/data/processed/crawl-review-admin/phaseb-261113/overtrim-verdicts.json`.

Test used: a span counts as `overtrim` only if it answers a clause the question names outright (vì sao / metric nào / tiến timers đúng / cái giá ...) and a strong answer would be expected to include it. Caveats and trade-offs the question never asks for count as `ok`. So does content that belongs to the sibling question.

## Verdicts

| qa_id | span (first ~60 chars) | verdict | reason |
|---|---|---|---|
| de-qa-1412 | ; denylist hoặc introspection cho thu hồi tức thì nhưng phụ thuộc | ok | Thu hồi tức thì là nội dung câu sibling hỏi; câu này chỉ hỏi thời hạn/rotation/lưu trữ |
| de-qa-1462 | **Kiểm soát**: open-weight cho fine-tune sâu, cố định phiên bản | ok | Chiều "kiểm soát" riêng, không thuộc dữ liệu/giấy phép/vận hành; "model mạnh sớm hơn" là chất lượng, câu hỏi loại trừ |
| de-qa-1319 | 4. Timer tự đặt lại hoặc retry vô hạn: runAllTimers có thể chạm | unclear | Ý 4 chạm "tiến fake timers đúng" nhưng chỉ là caveat (đáp án giữ đã có cách tiến đúng); ý 5 dọn dẹp thì không được hỏi |
| de-qa-1206 | **Đánh đổi:** Nhiều state đồng nghĩa với nhiều pipeline | ok | Câu hỏi chỉ hỏi ranh giới tách và cách chuyển resource, không hỏi cái giá |
| de-qa-1261 | **Next.js** có sẵn route announcer, lấy tên trang theo thứ tự | ok | Chi tiết riêng một framework; đáp án chung (title, live region, focus) đã đủ |
| de-qa-1261 | **Router khác** thì tự làm: - | ok | Mảnh tiêu đề cấu trúc, không có nội dung |
| de-qa-1205 | HPA còn bỏ qua dao động trong mức tolerance (mặc định 10%) | ok | Lý do chính (40% < 70% theo request) đã giữ; tolerance là chi tiết phụ |
| de-qa-1516 | - **Build once, promote:** cùng một artifact (cùng digest) | ok | Thực hành CD chung, không gắn với an toàn schema expand/contract; phần cái giá đã giữ |
| de-qa-1357 | Không bắt exception bên trong atomic rồi chạy tiếp, vì Django | ok | Tình huống không có nuốt exception; lỗi được hỏi là side effect trước commit, đã giữ on_commit |
| de-qa-1215 | 3. Dependency của ứng dụng** - Không vội nâng lên bản vừa phát | ok | Lời khuyên supply chain (chậm nâng cấp), không trả lời vì sao CVE tích tụ hay nhịp vá base image |
| de-qa-1204 | PID 1 là shell script không chuyển tiếp SIGTERM, nên app chỉ chết | unclear | Là một nguyên nhân (câu chỉ hỏi vì sao) nhưng yếu với "vài giây 502"; fixer giữ keep-alive mà cắt ý này |
| de-qa-1450 | Đánh đổi: bước xác nhận làm chậm luồng, nên áp theo mức rủi ro | ok | Câu hỏi không hỏi đánh đổi |
| de-qa-1410 | Spring áp dụng @Transactional qua proxy (mặc định): chỉ lời gọi | ok | Self-invocation/proxy là trọng tâm câu sibling; ở đây charge ở service khác nên đi qua proxy |
| de-qa-1410 | - REQUIRES_NEW giữ connection của transaction ngoài trong khi | ok | Caveat của một cách sửa, không được hỏi |
| de-qa-1555 | 4. **Phía server:** API nên idempotent theo giá trị đích | ok | Câu hỏi về thiết kế lại state client; thứ tự request về server gần câu sibling hơn |
| de-qa-1554 | Nếu trong effect có đoạn cần đọc giá trị mới nhất mà không được | ok | useEffectEvent là chi tiết nâng cao; "khi nào effect đúng" đã có danh sách đầy đủ |
| de-qa-1506 | - Không dùng `-target` cho vận hành thường xuyên; tài liệu | ok | -target không phải biện pháp phòng drift do sửa tay |
| de-qa-1054 | Thêm: background task chỉ hợp với việc nhẹ, chấp nhận mất khi | ok | Task queue và timeout httpx là lời khuyên thêm; nguyên nhân cạn kết nối và vòng đời đã giữ đủ |
| de-qa-1474 | Pipeline tự động cần data validation trước khi train và model | ok | Câu hỏi hỏi khi nào retrain, không hỏi kiểm định trong pipeline; chặn skew đã có feature store |
| de-qa-1213 | **Đánh đổi:** - Bỏ label làm mất một chiều phân tích; bù bằng | ok | Câu hỏi không hỏi đánh đổi; đáp án giữ đã có chuyển sang log/trace |
| de-qa-1191 | .\n- Chênh lệch vẫn còn với tokenizer được huấn luyện đa ngôn ngữ | ok | Fact bổ trợ; nguyên nhân chính (byte UTF-8, BPE cắt âm tiết) đã giữ |
| de-qa-1355 | - Tầng service trả về DTO/schema đã nạp đủ dữ liệu, không đẩy ORM | ok | Liên quan lazy load/MissingGreenlet, thuộc câu sibling |

Trade-off cross-check: of the 20 questions, only 1516 asks for "cái giá", and its trade-off section was kept. Every removed trade-off span (1206, 1450, 1213) comes from a question that does not ask about cost.

## Counts

- Spans: 22 total. `ok` 20, `unclear` 2, `overtrim` 0.
- Items with ≥1 `overtrim`: 0.
- Items with ≥1 `unclear`: 2 (de-qa-1319, de-qa-1204).
- **Over-trim rate: 0/20 = 0%.** Counting the unclear items as over-trim gives an upper bound of 2/20 = 10%.

## Notes (cosmetic, no effect on verdicts)

- Some kept answers have broken numbering after the cuts: 1357 starts at "Vấn đề 2", 1355 starts at "3.", 1215 has "**1.**/**2.**" with no 3, and 1410's removed span ends in a stray "2.". The cause is probably that content shared with the sibling was cut or excluded. Worth a renumbering pass, since the Evaluator sees the answer text.

## Unresolved questions

- 1204: should the PID 1 / SIGTERM cause go back in? The fixer kept the other secondary cause (keep-alive), so the cut is inconsistent. It is low-cost to restore if the team wants this half to list every cause.
