# Danh mục Service

## Tổng quan

| # | Service | Tech | DB | Port HTTP | Port TCP | Trạng thái |
|---|---|---|---|---|---|---|
| 1 | auth-service | NestJS | — (stateless) | 3300 | — (client only) | Có sẵn |
| 2 | user-service | NestJS | `user_db` | 3301 | 3411 | Có sẵn, cần mở rộng |
| 3 | job-service | NestJS | `job_db` | 3302 | 3412 | Mới |
| 4 | interview-service | NestJS | `interview_db` | 3304 | — | Mới |
| 5 | notification-service | NestJS | `notification_db` | 3303 | 3413 | Có sẵn, defer |
| 6 | ai-service | FastAPI | `ai_db` (tương lai) | 8000 | — | Mock |

> **Ghi chú port:** HTTP port là external (qua APISIX hoặc direct). TCP port là internal (NestJS microservice transport). Interview-service không cần TCP vì không có service nào gọi nó qua TCP — nó là consumer (gọi AI qua REST).

---

## 1. auth-service

**Trạng thái:** Có sẵn trong starter, cần mở rộng Role.

**Trách nhiệm:**
- Đăng ký tài khoản (Candidate / Employer)
- Đăng nhập, trả JWT access + refresh token
- Refresh token
- Quên mật khẩu, đặt lại mật khẩu
- Phân quyền theo vai trò (RBAC)

**DB:** Không sở hữu DB riêng. Stateless JWT. Gọi `user-service` qua TCP để:
- Tạo user khi sign-up
- Tìm user theo email khi login
- Verify credentials

**Giao tiếp:**
- HTTP (client → APISIX → auth)
- TCP client → user-service
- TCP client → notification-service (gửi email reset password)

**API chính:**

| Method | Endpoint | Auth | Mô tả |
|---|---|---|---|
| POST | /api/sign-up | Public | Đăng ký |
| POST | /api/login | Public | Đăng nhập |
| POST | /api/refresh-token | Refresh token | Làm mới JWT |
| POST | /api/forgot-password | Public | Gửi email reset |
| POST | /api/forgot-password/verify | Public | Verify OTP |
| POST | /api/reset-password | Public | Đặt lại mật khẩu |
| POST | /api/change-password | JWT | Đổi mật khẩu |

**Cần làm:**
- Mở rộng Role enum: `Admin`, `Candidate`, `Employer`
- Sign-up phân biệt role (Candidate vs Employer)
- RBAC decorator kiểm tra role

---

## 2. user-service

**Trạng thái:** Có sẵn, cần mở rộng thêm candidate/company profiles.

**Trách nhiệm:**
- Quản lý hồ sơ người dùng (CRUD)
- Hồ sơ ứng viên (candidate profile): kinh nghiệm, kỹ năng, mong muốn lương
- Hồ sơ công ty (company profile): tên, mô tả, logo, ngành nghề
- Upload avatar

**DB:** `user_db`
- `users` — thông tin cơ bản, role, auth
- `candidate_profiles` — thông tin chi tiết ứng viên
- `company_profiles` — thông tin công ty của employer

**Giao tiếp:**
- HTTP (client → APISIX → user)
- TCP server — phục vụ auth-service, job-service, notification-service

**API chính:**

| Method | Endpoint | Auth | Mô tả |
|---|---|---|---|
| GET | /api/users/me | JWT | Xem profile bản thân |
| PUT | /api/users/me | JWT | Cập nhật profile |
| GET | /api/users/:id | JWT | Xem profile (Admin/Employer) |
| GET | /api/users | JWT (Admin) | Danh sách users |
| POST | /api/candidate-profile | JWT (Candidate) | Tạo/cập nhật profile ứng viên |
| GET | /api/candidate-profile | JWT (Candidate) | Xem profile ứng viên |
| POST | /api/company-profile | JWT (Employer) | Tạo/cập nhật profile công ty |
| GET | /api/company-profile/:id | JWT | Xem profile công ty |

**TCP handlers (internal):**
- `GetUser` — trả về user theo ID
- `FindUserByEmail` — trả về user theo email
- `CreateUser` — tạo user mới (gọi từ auth sign-up)
- `UpdateUser` — cập nhật user
- `GetUsersByIds` — batch get users (cho job-service hiển thị employer info)

---

## 3. job-service

**Trạng thái:** Mới. Bao gồm cả module ứng tuyển (merged từ application-service, xem [ADR-006](adr/adr-006-gop-application-vao-job-service.md)).

**Trách nhiệm:**
- CRUD tin tuyển dụng (Employer)
- Quản lý danh mục: kỹ năng (skills), vị trí (positions), cấp bậc (experience levels)
- Tìm kiếm và lọc tin tuyển dụng (Candidate)
- Ứng tuyển (Candidate): nộp CV, cover letter
- Theo dõi trạng thái ứng tuyển
- Lưu việc làm (saved jobs)
- Upload CV lên MinIO

**DB:** `job_db`
- `job_postings` — tin tuyển dụng
- `skills` — danh mục kỹ năng CNTT
- `job_skills` — many-to-many job ↔ skill
- `experience_levels` — junior, mid, senior, lead, manager
- `applications` — hồ sơ ứng tuyển
- `application_events` — lịch sử đổi trạng thái
- `saved_jobs` — việc làm đã lưu

**Giao tiếp:**
- HTTP (client → APISIX → job)
- TCP client → user-service (lấy thông tin employer/candidate)
- S3 API → MinIO (upload/download CV)

**API chính:**

| Method | Endpoint | Auth | Mô tả |
|---|---|---|---|
| POST | /api/jobs | JWT (Employer) | Đăng tin tuyển dụng |
| GET | /api/jobs | Public | Danh sách + tìm kiếm + lọc |
| GET | /api/jobs/:id | Public | Chi tiết tin |
| PUT | /api/jobs/:id | JWT (Employer, owner) | Sửa tin |
| PATCH | /api/jobs/:id/status | JWT (Employer, owner) | Đóng/mở tin |
| GET | /api/jobs/my | JWT (Employer) | Tin của tôi |
| POST | /api/applications | JWT (Candidate) | Ứng tuyển |
| GET | /api/applications/my | JWT (Candidate) | Hồ sơ ứng tuyển của tôi |
| GET | /api/applications/job/:jobId | JWT (Employer, owner) | Ứng viên của tin |
| PATCH | /api/applications/:id/status | JWT (Employer) | Đổi trạng thái |
| POST | /api/saved-jobs/:jobId | JWT (Candidate) | Lưu việc |
| DELETE | /api/saved-jobs/:jobId | JWT (Candidate) | Bỏ lưu |
| GET | /api/saved-jobs | JWT (Candidate) | Danh sách đã lưu |
| GET | /api/skills | Public | Danh sách kỹ năng |
| POST | /api/skills | JWT (Admin) | Thêm kỹ năng |
| GET | /api/experience-levels | Public | Danh sách cấp bậc |

---

## 4. interview-service

**Trạng thái:** Mới. Xem [ADR-004](adr/adr-004-interview-data-ownership.md) về data ownership.

**Trách nhiệm:**
- Tạo phiên phỏng vấn luyện tập
- Quản lý từng lượt hỏi đáp (turn)
- Lưu điểm theo tiêu chí (JSONB)
- Gọi AI service qua REST (hiện tại mock)
- Lưu quyết định của agent (deepen / switch_topic / keep_difficulty)
- Xem lại lịch sử phỏng vấn
- Quản lý bộ câu hỏi (Admin)

**DB:** `interview_db`
- `question_bank` — kho câu hỏi phỏng vấn
- `interview_sessions` — phiên phỏng vấn
- `interview_turns` — từng lượt hỏi đáp
- `interview_results` — tổng hợp kết quả

**Giao tiếp:**
- HTTP (client → APISIX → interview)
- REST client → ai-service (evaluate answer, get next question)

**API chính:**

| Method | Endpoint | Auth | Mô tả |
|---|---|---|---|
| POST | /api/sessions | JWT (Candidate) | Bắt đầu phiên phỏng vấn |
| POST | /api/sessions/:id/answer | JWT (Candidate) | Gửi câu trả lời |
| POST | /api/sessions/:id/end | JWT (Candidate) | Kết thúc phiên |
| GET | /api/sessions | JWT (Candidate) | Lịch sử phiên của tôi |
| GET | /api/sessions/:id | JWT (Candidate/Employer) | Chi tiết phiên + turns |
| GET | /api/sessions/candidate/:candidateId | JWT (Employer) | Xem kết quả của ứng viên |
| GET | /api/question-bank | JWT (Admin) | Danh sách câu hỏi |
| POST | /api/question-bank | JWT (Admin) | Thêm câu hỏi |
| PUT | /api/question-bank/:id | JWT (Admin) | Sửa câu hỏi |
| DELETE | /api/question-bank/:id | JWT (Admin) | Xóa câu hỏi |

---

## 5. notification-service

**Trạng thái:** Có sẵn trong starter. Defer enhancement sang sprint sau.

**Trách nhiệm:**
- Gửi email (SMTP / AWS SES) — đã có
- Thông báo in-app (thêm sau)
- Queue xử lý email bất đồng bộ

**DB:** `notification_db`
- `notifications` — thông báo in-app (thêm sau)

**Giao tiếp:**
- TCP server — nhận lệnh gửi email từ auth-service, job-service
- SMTP/SES — gửi email ra ngoài

**API chính (tương lai):**

| Method | Endpoint | Auth | Mô tả |
|---|---|---|---|
| GET | /api/notifications | JWT | Thông báo của tôi |
| PATCH | /api/notifications/:id/read | JWT | Đánh dấu đã đọc |
| PATCH | /api/notifications/read-all | JWT | Đọc tất cả |

---

## 6. ai-service (Mock)

**Trạng thái:** Mock. Chỉ có stub FastAPI để kiểm chứng gateway và network.

**Trách nhiệm (mock):**
- Nhận request từ interview-service
- Trả về response cố định (scores, next question, agent decision)

**Trách nhiệm (tương lai):**
- RAG: truy vấn knowledge base (pgvector)
- LLM: đánh giá câu trả lời (Claude / GPT API)
- Agent logic: quyết định đào sâu / chuyển hướng / giữ độ khó
- Sinh câu hỏi tiếp theo dựa trên context

**DB:** `ai_db` (pgvector/pgvector:pg16) — tương lai

**API (OpenAPI contract):**

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | /api/evaluate | Đánh giá câu trả lời, trả về scores + next question |
| GET | /api/health | Health check |

Xem chi tiết contract tại [ai-integration.md](ai-integration.md).

---

## Đánh giá cách chia service

### Tại sao gộp application vào job-service?

Brief đề xuất 7 service riêng biệt. Sau khi đánh giá, gộp `application-service` vào `job-service` vì:

1. **Tight coupling:** application luôn reference job_posting — tách ra thì mọi query cần cross-service call
2. **Team 3 người:** giảm 1 DB + 1 Dockerfile + 1 migration set + 1 APISIX route config = tiết kiệm ~2-3 ngày setup
3. **Reversible:** có thể extract ra service riêng sau nếu cần scale

### Tại sao giữ notification-service riêng?

- Đã có sẵn trong starter, không mất thời gian tạo
- Trách nhiệm rõ ràng (gửi email) không overlap service khác
- Defer enhancement — chỉ cần làm skeleton, tăng dần

### Bảng tóm tắt

| Nguyên bản (brief) | Quyết định | Lý do |
|---|---|---|
| auth-service | Giữ nguyên | Đã có, responsibility rõ |
| user-service | Mở rộng | Thêm candidate/company profiles |
| job-service | Giữ + merge application | Tight coupling, giảm overhead |
| application-service | Gộp vào job-service | Xem [ADR-006](adr/adr-006-gop-application-vao-job-service.md) |
| interview-service | Giữ nguyên | Domain riêng biệt |
| notification-service | Defer enhancement | Đã có skeleton |
| ai-service | Mock | FastAPI stub trong Docker |
