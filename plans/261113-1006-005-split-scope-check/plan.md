# Plan: rà soát "đáp án có ý câu hỏi không hỏi" cho nửa câu tách đôi (spec 005 FR-030, T067)

Status: in progress (2026-11-13). Owner: DE. Feature tool: Spec Kit (spec 005), this file = working notes.

## Vấn đề
222/262 nửa câu tách đôi (B5) chưa ai đọc. Mẫu 20 nửa: 5 cần sửa → ước ~55 nửa có ý trong đáp án mà câu hỏi không
hỏi; Evaluator chấm theo mọi ý của đáp án → ứng viên bị trừ oan.

## Cách làm
1. `scope-check-prepare` (repo, tất định): chọn nửa có `split_from`, trừ `data/reviews/qa-split-reviewed.json`,
   assert = 222; tách đáp án thành ý (p1..pn: mỗi bullet / đoạn; dòng chỉ in đậm là tiêu đề, gắn vào ý sau); kèm câu
   hỏi nửa anh em (qua `qa-split-map.json`) và câu gốc (tùy chọn `--originals`). Ghi lô JSON cho judge.
2. Judge = worker Sonnet (subagent, không gọi API trong repo), mỗi ý: `asked` | `sibling` | `unasked`; ghi
   `.jsonl` theo schema chung → sau thêm luna (cần key OpenAI mới) không đổi code.
3. `scope-check-score` (repo, tất định): gộp nhiều judge, cờ = có ý ≠ asked ở ≥ 1 judge (ưu tiên recall), tin cậy
   cao khi mọi judge đồng ý; chấm câu mồi (`--canary-key`) và hiệu chỉnh (`--truth`: recall/precision).
4. Hiệu chỉnh trước: 42 nửa đã duyệt 09/11 (bản trước sửa, verdict reviewer làm chuẩn) → recall phải đủ cao mới tin
   kết quả 222. Câu mồi: nửa sạch + chép 1 khối từ nửa anh em (khóa ở `crawl-review-admin/`).
5. Sửa (worker Sonnet, theo thứ tự ưu tiên): chuyển khối sang nửa anh em → cắt khối không được hỏi (chữ chỉ lấy từ
   đáp án gốc) → mở rộng câu hỏi (≤ 200 ký tự, giữ từ của topic). Sau sửa: chấm lại nửa đã sửa, `validate --strict`,
   senior 58/58, `process`.

## Việc
- [ ] FR-030 + T067 trong spec/tasks 005
- [ ] Code + test (worker Sonnet), review code (Opus)
- [ ] Hiệu chỉnh 42 nửa
- [ ] Chạy 222 + câu mồi
- [ ] Sửa + kiểm lại, commit, cập nhật NOTICE / PR #87

## Câu hỏi mở
- Key OpenAI mới (đã hết hạn 2026-11-13): cần cho judge thứ hai (luna) và cho `index`.
- AIE: Evaluator có coi một số ý là cộng điểm (không bắt buộc) được không? Nếu được, nhiều cờ hạ xuống minor.
