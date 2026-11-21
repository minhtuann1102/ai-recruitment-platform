# Contract nháp GĐ2: gợi ý qua job-service (giao FSD, chưa chốt)

Trạng thái: **nháp**. Chờ FSD có 007 (job postings), 008 (applications + CV) và 013 (web). Spec liên quan: FR-018,
FR-022 đến FR-027.

## Endpoint public (qua APISIX, JWT, `@Roles`)

| Method | Path | Role | Mô tả |
|---|---|---|---|
| GET | `/api/v1/jobs/recommended?page=&limit=` | Candidate | Việc phù hợp với CV mặc định của mình; mỗi tin có `score`, `components`, `matchedSkills`, `missingSkills` |
| GET | `/api/v1/jobs/{jobId}/matched-candidates?page=&limit=` | Employer (chủ tin) | Ứng viên đã ứng tuyển + ứng viên `is_open_to_work`; mỗi người có `matchedSkills`, `missingSkills`; **không** có điểm hay thứ hạng; sắp xếp theo thời gian ứng tuyển / cập nhật hồ sơ |

Response theo `{data, meta}` của `docs/conventions.md`. Chủ tin khác gọi → 403. Ứng viên chưa có CV mặc định → 200 với
danh sách rỗng và `meta.reason = "no_default_cv"`.

## Luồng

1. **Tin đổi trạng thái** (duyệt, sửa, đóng, hết hạn, gỡ duyệt): job-service gọi ai-service để upsert hoặc gỡ tin trong
   chỉ mục. Endpoint upsert / delete của ai-service sẽ viết ở GĐ2. Đến lúc đó ai-service ghi vào `knowledge_chunks`,
   cần AIE đồng ý (ai-service hiện chỉ đọc ai_db).
2. **Candidate**: job-service lấy `cv_profile` của CV mặc định (đã parse lúc upload), gọi `POST /api/match/jobs`, rồi
   lọc thêm theo trạng thái tin trong `job_db`.
3. **Employer**: cần vector CV lưu sẵn (FR-027). Nơi lưu chốt ở plan GĐ2: `job_db` (pgvector) hoặc ai_db kèm amendment
   constitution IV và ADR.
4. **Cache**: Redis, khóa `match:cand:{userId}` / `match:job:{jobId}`, TTL 10 phút. Xóa khi CV mặc định đổi, khi tin
   đổi, hoặc khi `is_open_to_work` đổi.

## Phía FSD cần thêm

- "CV mặc định" cho ứng viên (004 / 008) và `cv_profile` lưu lúc upload.
- Sự kiện đổi trạng thái tin (007) để đồng bộ chỉ mục.
- Route APISIX trong `config/apisix/conf/apisix-*.yaml`.
