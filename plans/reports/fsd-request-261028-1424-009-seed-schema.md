# Gửi FSD — seed 200 job posting (009 US4) cần gì từ migration

Code `seed-jobs` đã xong trên nhánh `feat/data-pipeline/jd-seed` (chưa chạy vào DB thật). Seed chạy được khi các mục
dưới có trên `main`. Seed **không tạo / sửa bảng**: thiếu bảng / cột → dừng, không ghi (FR-019).

## 1. Migration cần có (theo `docs/architecture/data-model.md` §1–§2)

| DB | Bảng | Cột seed ghi / đọc |
|---|---|---|
| `user_db` | `users` (đã có) | `id, email, password, role, email_verified, created_at, updated_at` |
| `user_db` | `company_profiles` (004) | `id, user_id, company_name, created_at, updated_at` |
| `job_db` | `job_postings` (007) | `id, employer_id, title, description, requirements, salary_min, salary_max, salary_currency, location, work_type, experience_level_id, status, deadline, created_at, updated_at` |
| `job_db` | `job_skills` | `job_id, skill_id` |
| `job_db` | `skills` | `id, name, slug, category, created_at` |
| `job_db` | `experience_levels` | `id, name` |

- Cột khác ngoài bảng trên: để **nullable hoặc có default**. Cột NOT NULL không default mà seed không biết → preflight
  dừng.
- Seed tự sinh `id` (uuid4) và `created_at` / `updated_at` vì bảng MikroORM không có default (giống `users`).
- `work_type`: `remote | onsite | hybrid`; `status`: `open`; `salary_currency`: `VND | USD`.

## 2. Cần FSD chốt

1. **`Role.Employer`**: enum `Role` ở `libs/common/src/enums/app.enum.ts` hiện chỉ có `Admin | User`. Seed ghi
   `role = 'Employer'` đúng chữ hoa / thường đó. Nếu tên khác, báo DE.
2. **`experience_levels` đủ 6 tên**: `Intern, Junior, Mid, Senior, Lead, Manager`. Dữ liệu thật: 6 cấp → 210 JD đủ
   điều kiện; **bỏ Manager → 191 < 200, seed không chạy** (DE phải sinh thêm JD synthetic). Contract ví dụ chỉ tới Lead.
3. **Slug kỹ năng**: seed thêm skill còn thiếu từ `apps/data-pipeline/data/seeds/skill_dictionary.yaml` (138 slug). Nếu
   FSD seed sẵn `skills`, nên dùng **đúng slug của danh mục**. Trùng `name` khác `slug` (vd `Node.js` / `node-js`) thì
   seed dùng lại skill của FSD, nhưng tìm theo slug của danh mục (`nodejs`) sẽ không ra. `skills.name` và `skills.slug`
   có UNIQUE không?
4. **T039 — password Employer seed** (FR-021: tài khoản seed không đăng nhập được). Backend dùng `bcryptjs` v3. DE đã thử:
   hash `$2b$` của chuỗi khác → `compareSync` trả `false`; chuỗi không phải hash → `false`, không throw. Chọn một:
   - (a) DE thêm gói `bcrypt` (Python), hash một chuỗi ngẫu nhiên rồi bỏ. Đúng nghĩa FR-021.
   - (c) chuỗi ngẫu nhiên đúng định dạng bcrypt, không thêm dependency. Cần FSD xác nhận API login trả 401, không phải 500.
5. **Tìm kiếm job (SC-005)** phải trả kết quả cho "NodeJS", "React", "DevOps", "Senior", "Hà Nội". Trên DB thử: 15 / 29 /
   45 / 57 / 101 posting. Tìm theo `title` + `job_skills.slug` + `experience_levels.name` + `location` là đủ.

## 3. Lưu ý

- `deadline` lấy theo JD gốc: 9 / 200 posting đã quá hạn hôm nay, mọi deadline ≤ 2026-12-01. Nếu tìm kiếm lọc theo
  `deadline >= hôm nay`, sau tháng 12 sẽ không còn posting nào (DE đang hỏi lại cách xử lý).
- `--clean` chỉ xóa posting + Employer có email `@seed.ai-recruit.test`. FK từ `applications`, `saved_jobs`,
  `application_events` tới `job_postings` (008) nên là **RESTRICT, không CASCADE**: CASCADE sẽ xóa luôn hồ sơ ứng tuyển
  thật của ứng viên khi DE dọn seed. Với RESTRICT, `--clean` báo lỗi và không xóa gì khi đã có hồ sơ.
- `experience_levels`, `job_skills` có `created_at` / `updated_at` NOT NULL không default không? Có thì báo DE (preflight
  sẽ báo thiếu nguồn giá trị cho `job_skills`).
