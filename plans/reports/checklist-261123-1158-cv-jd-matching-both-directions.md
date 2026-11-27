# Checklist: gợi ý 2 chiều CV ↔ JD (017 GĐ2), 2026-11-23

Mục tiêu: ứng viên xem việc phù hợp với CV; nhà tuyển dụng xem ứng viên phù hợp với tin (không điểm, không thứ hạng,
FR-018). Hiện trạng `main`: chỉ có ai-service (`POST /api/match/jobs`, 356 JD crawl đã index) và user-service (bảng
`users`). **Chưa có job-service, chưa có bảng CV / hồ sơ ứng viên, chưa có web.**

## 0. Chốt trước (cả nhóm, 1 buổi)

- [ ] FR-027: vector CV lưu ở đâu: `job_db` / DB của service giữ CV (đề xuất) hay ai_db (cần sửa constitution IV + ADR)
- [ ] Ai giữ CV: service nào lưu file CV + `cv_profile` + cờ CV mặc định + `is_open_to_work`
- [ ] Demo dùng ứng viên tổng hợp (seed) được không; số lượng (đề xuất 60–100)

## 1. Dữ liệu (DE)

- [x] 356 JD crawl đã embed (`knowledge_chunks`, `job_description`)
- [x] 24 CV tổng hợp dạng `CvProfile` (bộ đánh giá)
- [ ] Sinh thêm CV ứng viên tổng hợp cho demo (60–100, đủ 6 track × 4 level, tiếng Việt, không PII), có `is_open_to_work`
- [ ] Seed tin tuyển dụng vào `job_db` (PR #50, chờ migration của FSD)
- [ ] Seed ứng viên (user + CV + `cv_profile`) vào DB của FSD (chờ bảng ở mục 3)

## 2. AI (AIE)

- [x] Ứng viên → việc: `POST /api/match/jobs` (#109)
- [ ] Nhà tuyển dụng → ứng viên: endpoint đảo chiều (JD → danh sách ứng viên + kỹ năng khớp / thiếu), dùng lại
      `app/matching/scorer.py`
- [ ] Đường ghi vector CV: embed `cv_profile` khi CV được parse / đặt mặc định, lưu theo quyết định FR-027
- [ ] Thêm / gỡ JD trong chỉ mục khi tin trên nền tảng được duyệt / đóng (hiện chỉ mục chỉ có JD crawl)

## 3. Backend + web (FSD)

- [ ] job-service + migration `jobs`, `company_profiles` (007), kéo theo mở khóa seed #50
- [ ] Upload CV, gọi CV Parser, lưu `cv_profile`, CV mặc định; cờ `is_open_to_work` (004 / 008)
- [ ] Route public qua APISIX + RBAC: `GET /api/v1/jobs/recommended` (Candidate),
      `GET /api/v1/jobs/{jobId}/matched-candidates` (Employer, chủ tin) — contract nháp `specs/017-cv-jd-matching/contracts/gd2-job-service-draft.md`
- [ ] Màn hình: "Việc phù hợp" (ứng viên), "Ứng viên phù hợp" của từng tin (nhà tuyển dụng)

## Đường găng

Mục 3 (job-service + lưu CV) chặn mọi thứ phía nhà tuyển dụng và chặn seed. Mục 1 (sinh CV demo) và mục 2 (endpoint đảo
chiều, chạy được với dữ liệu giả trong test) làm song song ngay được.
