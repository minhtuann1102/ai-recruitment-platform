# Báo cáo DE — 2026-10-28

## Tóm tắt
- Merged hôm nay: #43 (đóng S1 spec 005), #44 (spec 016 draft), #45 (009 US1 crawl JD), #46 (nhãn golden set, 1 người chấm), #47 (009 US2 `process-jd`).
- Mở: **#48 draft** (009 US5 `synth-jd`) — code + test xong, **T037 bị chặn: key LLM hết số dư (HTTP 402)**.
- Dữ liệu JD thật: 515 crawl → **341 JD hợp lệ**, `with_skill_ratio` 0.9853, `pii_remaining` 0. Cần +159 synthetic để đạt 500.

## Golden set (005 / AIE)
- FSD (rater_b) chấm xong 60 + 43 nhưng nhãn Evaluator sai nội dung (nhồi keyword được 4-4-4-3, câu lạc đề thành answered, ~8 giây/mẫu). Trang chấm ghép id đúng → lỗi do người chấm. Báo cáo: `golden-label-check-261028-0412-rater-b-quality.md`.
- DE chốt bỏ nhãn FSD. #46: `question_labels/rater_a.json`, `evaluator_labels/rater_a.json` + `final.json` (bản sao), doc 09 ghi "1 người chấm, không có kappa". Thắng đồng ý; Thắng chạy `run_evaluator` / `judge_interviewer`.

## 009 US2 `jd-process` (#47)
- Code cloud (T017–T028) đã review 10-27; sửa theo review + quyết định DE (spec Clarifications Session 2026-10-28):
  - Cấp bậc: < 12 tháng → Junior; Intern chỉ từ tiêu đề; itviec `experience_raw` (4 giá trị nhóm) bỏ qua, lấy số năm trong mô tả.
  - Lọc IT (`jd_it_filter.py`): thêm IT / kỹ sư hệ thống / security / QA-QC / DBA; thẻ kỹ năng cụ thể tính; kỹ năng chung chung không tự làm JD thành IT; loại sales / tư vấn / giảng dạy / hành chính / phiên dịch / kiểm toán viên, BA / PO / PM / Scrum Master (để sau, raw giữ nguyên).
  - Thành phố (`jd_city.py`): dòng "Địa điểm:" + bảng quận → thành phố; không crawl lại.
  - Nhóm theo kỹ năng trong tiêu đề; 138 kỹ năng (tách bí danh gộp nhầm, thêm hạ tầng / bảo mật / kiểm thử / dữ liệu).
- Kết quả thật: 341 JD, thành phố trống 8, cấp bậc trống 37, 56 ô; 215 JD có `requirements`, **186 JD đủ điều kiện seed T041** (< 200). Chạy lại giống hệt từng byte. T029: DE đã đọc 10 JD, ổn.

## 009 US5 `jd-synthetic` (#48 draft)
- Code cloud (Gói 5, T030–T036) rebase lên bản sửa, đổi tác giả; sửa 1 lỗi review (kỹ năng chung chung nhóm khác làm JD synthetic bị loại). 368 test đạt.
- Dry-run trên báo cáo thật: +159 JD / 63 ô — frontend +46, mobile_fullstack +46, backend +26, devops +24, ai_data +17; Intern +39, Lead +34, Manager +28; Đà Nẵng +76.
- `synth-jd --limit 10` chạy 2 lần: provider trả **402 Insufficient Balance**, 0 token, không ghi file → dữ liệu sạch, chạy lại được.

## Trạng thái máy
- Repo chính ở `main` (62cc0a9). Worktree còn: `arp-jd-synthetic` (#48), `ai-recruitment-platform-qa-review`. Đã gỡ `arp-jd-process`, `arp-jd-crawl`, `...-golden-labels`.
- Dữ liệu thật trong `apps/data-pipeline/data/processed/` của repo chính (gitignore): `jd_normalized.jsonl`, `jd_chunks.jsonl`, `jd-report-20261028T060354Z.json`.

## Việc tiếp theo
1. **DE**: nạp số dư cho tài khoản **DeepSeek** (`.env`: `LLM_BASE_URL=https://api.deepseek.com`, model `deepseek-chat`) — khác credit Claude cloud; ~1–2 USD là đủ. Chi phí `synth-jd` in ra tính theo giá gpt-4o-mini (hằng `PRICE_IN/PRICE_OUT`), chi phí thật xem dashboard DeepSeek.
2. Chạy T037 từ repo chính (cần checkout code #48): `synth-jd --limit 1` (thử key) → `--limit 10` → DE đọc 10 JD → `process-jd` → `synth-jd` → `process-jd` (≥ 500 JD) → `synth-jd` lần nữa = 0 lời gọi; ghi số + chi phí vào #48, bỏ draft, merge.
3. **FSD**: migration `company_profiles` (004) + job-service (007) để mở US4 seed; xác nhận 138 slug kỹ năng (mô tả #47); chốt T039 (mật khẩu Employer seed).
4. Polish 009: T051–T055 (kích thước file, `git status` sạch data, CI, chia sẻ `jd_normalized.jsonl` cho FSD nếu cần).
5. Dọn nhánh remote đã merge (DE chạy, auto-mode chặn xóa nhánh remote):
   `! git push origin --delete chore/golden-labels-rater-a feat/data-pipeline/jd-crawl feat/data-pipeline/jd-process docs/jd-crawling-seeding-plan docs/rag-qa-sprint1-closeout docs/interview-learning-roadmap-spec`

## Câu hỏi còn mở
- Có cần nhờ người chấm thứ hai cho Evaluator sau này để có kappa người–người không?
- BA / PO / PM: khi nào bổ sung nhóm thứ 6 (cần AIE có hướng phỏng vấn)?

## Cập nhật 06:35
- DE chốt chỉ bù sàn đa dạng, sinh trong phiên Claude (key DeepSeek hết số dư): 24 JD synthetic, 24/24 qua hậu kiểm.
- `process-jd`: **365 JD** (341 crawl + 24 synthetic), frontend / mobile / Đà Nẵng = 20, `pii_remaining` 0; 210 JD đủ điều kiện seed (191 nếu không có Manager).
- #48 ready (CI xanh trước đó), chờ merge. Seed vẫn chờ migration FSD + code US4 (T040–T048) + T039.
- File đọc tay: `apps/data-pipeline/data/processed/t037-read-24-synthetic.txt` (gitignore).
