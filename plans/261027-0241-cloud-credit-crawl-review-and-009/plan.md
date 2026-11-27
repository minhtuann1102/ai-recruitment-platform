# Dùng nốt credit cloud (~70$, hết hạn 04/11/2026)

DE đồng ý 2026-10-27. Prompt từng phiên: [cloud-session-prompts.md](cloud-session-prompts.md).

## Gói việc (thứ tự ưu tiên)

| # | Gói | Repo | Phiên | Trạng thái |
|---|---|---|---|---|
| 1 | Duyệt 11 lô crawl (10 lô chưa chạy + py-2 chạy lại), 173 cặp | `ai-recruit-crawl-review` (private) | 11 | Xong 25/25 lô, qua kiểm ở máy. java-3 Opus 3$; 10 lô Sonnet 36$ (0,23$/cặp). Còn 33$ |
| 2 | 009 PR `jd-crawl` (T001–T015), offline | `ai-recruitment-platform` | 1 | Xong, PR #45 merged 2026-10-28 |
| 4 | Kiểm trước nhãn golden set (005 T041), chỉ báo cáo | `ai-recruitment-platform` | 1 | Xong (báo cáo golden-label-precheck-261027) |
| 3 | 009 PR `jd-process` (T017–T028) | `ai-recruitment-platform` | 1 | Xong, PR #47 merged 2026-10-28 |
| 5 | 009 PR `jd-synthetic` (T030–T036), offline | `ai-recruitment-platform` | 1 | Code xong, PR #48 draft; T037 chờ nạp DeepSeek |

## Nguyên tắc

- Repo crawl phải private (nội dung crawl chưa rõ giấy phép, có NC-ND). Đã kiểm `visibility = PRIVATE`.
- Mỗi lô một nhánh `batch/<lô>`, nên phiên cloud không thấy lô khác (canary cùng track dùng chung nội dung).
- Khóa canary, `progress.json`, script kiểm và `.quote-cache` chỉ ở máy DE. Đã grep cây push: 0 lần nhắc canary.
- Kết quả cloud chỉ tin sau khi kiểm lại ở máy: `verify_quotes.py` (cache local), `check_crawl_batches.py`,
  `update_progress.py`.
- Mỗi lô chỉ chạy ở một nơi: 3 lô ai-3, devops-3, fe-3 chạy local; 11 lô còn lại chạy cloud.
- Đo giá: ghi số dư trước và sau phiên java-3. Chi phí đợt cặp hard (0,16$/cặp) chỉ là mức sàn, vì lô crawl
  fetch nhiều hơn. Nếu 173 cặp vượt khoảng 45$ thì bỏ gói 3 trước, rồi đến gói 4.

## Câu hỏi còn mở

- ~~Hai cặp node-2 sai topic~~: DE chọn bỏ (2026-10-27), ghi trong `crawl-review-admin/de-overrides.json`.
- Danh sách cặp NC-ND đã dịch máy: đưa vào báo cáo cuối để lọc trước khi lên staging công khai.
