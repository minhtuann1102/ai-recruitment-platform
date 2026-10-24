# Chia việc cho 100$ credit Claude Code (hết hạn 04/11/2026)

Mục tiêu: chạy song song với phiên local các việc tốn nhiều model nhưng chỉ cần nội dung trên GitHub.
Prompt từng phiên: [cloud-session-prompts.md](cloud-session-prompts.md).

## Nguyên tắc

- **Cổng 1, lô thử frontend:** chưa chi credit cho tới khi lô thử local bắt được 2/2 cặp mồi.
- **Cổng 2, đo giá thật:** chạy **1 phiên** (devops, 18 + 1 cặp) trước. Ghi số dư credit trước và sau phiên đó, chia
  cho 19 để ra chi phí mỗi cặp, rồi mới mở các phiên còn lại. Không có bảng giá: credit tính theo token, chưa đo được.
- Mỗi lô cloud có 1 cặp mồi riêng (khóa giữ ở máy local). Lô nào để lọt cặp mồi thì bỏ kết quả lô đó.
- Nhánh kết quả `qa-review/results-*` là nhánh tạm trên repo public: xóa sau khi gộp xong.

## Gói việc (theo thứ tự ưu tiên)

| # | Gói | Phiên | Tỷ lệ credit (trần) | Hạn |
|---|---|---|---|---|
| A | Duyệt cặp hard (T057): devops 18, java 22, nodejs 22, python 22, ai-1 24, ai-2 23 (+1 mồi/lô) | 6 | ~65% | 25/10 |
| B | 005 US5 crawler mẫu (T042–T046, S1-DE-2), nhánh `feat/data-pipeline/sample-crawler` | 1 | ~15% | 26/10 |
| C | Bản nháp spec 009 jd-crawling-seeding (chỉ spec, chưa plan) | 1 | ~10% | 27/10 |
| — | Dự phòng: chạy lại lô lint lỗi / lô lọt mồi | — | ~10% | 04/11 |

Gói B mặc định S1-DE-2 làm theo lựa chọn (a): làm crawler mẫu chứ không hoãn. DE chưa chốt điều này; muốn hoãn thì
bỏ gói B và dồn phần credit đó sang gói A.

Sau cổng 2: nếu chi phí mỗi cặp × 118 cặp còn lại (131 cặp thật + 6 mồi, trừ 19 cặp của lô devops) vượt ~65$ thì cắt theo thứ tự: chuyển phiên sang model rẻ hơn
(cặp mồi vẫn kiểm chứng chất lượng), giảm số fetch mỗi cặp, rồi mới bỏ gói C.

## Việc ở lại phiên local (không tốn credit)

- Dựng báo cáo gộp từ các nhánh kết quả, chấm cặp mồi, đẩy gợi ý lên trang duyệt.
- T053 review mẫu bản dịch: dữ liệu crawl bị gitignore, cloud không có.
- `approve-seed` sau khi DE chọn cách ghi `reviewed_by` (a/b). Tạo `.venv`, chạy lại `index` để đưa cặp hard vào `ai_db`.
- Duyệt nhãn golden set của Thắng, mục Clarifications 2026-10-22 trong spec 005, báo Thắng về giới hạn 600 token.

## Chuẩn bị (phiên local, cần DE đồng ý push)

1. Nhánh `chore/qa-review-skill` tách từ `feat/data-pipeline/qa-offline`: chỉ commit `.claude/skills/interview-qa-review/`
   và 6 file `plans/reports/qa-review/batch-*.json`. Không đưa file 016 và `scripts/` lạc vào commit.
2. Push nhánh lên origin.
3. Ở claude.ai/code: chọn repo, môi trường có quyền truy cập Internet (WebFetch phải mở được trang tài liệu).

## Câu hỏi còn mở

- Credit có áp dụng cho phiên cloud tạo từ CLI (`--remote`) hay chỉ phiên mở trên web? Kiểm tra số dư sau phiên đầu.
- Model mặc định của phiên cloud là gì? Cặp mồi sẽ cho biết model đó duyệt có đủ tin cậy không.

## Kết quả (2026-10-23)

- 8 phiên cloud (6 lô duyệt + gói B + gói C) dùng hết **22$**, còn 78$. Không tách được giá riêng lô devops; trần
  ước tính gói A ≤ 22$ / 137 cặp ≈ 0,16$/cặp.
- 6/6 cặp mồi cloud bị bắt đúng lỗi cài sẵn; lint 0 ở mọi lô. Kết quả gộp vào `chore/qa-review-skill` (`27d1b22`).
- Rubric v2 (đếm ý liên kết một lần, chỉ tính giờ cho ý bắt buộc) chấm lại tại máy, không tốn credit (`ab61490`):
  Đạt 104 · Cần sửa 40 · Bỏ 0; 27 cặp phải đọc.
