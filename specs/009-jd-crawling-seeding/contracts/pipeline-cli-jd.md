# Contract: lệnh JD của CLI `python -m pipeline` (chạy trong `apps/data-pipeline/`)

Bổ sung cho [005 pipeline-cli.md](../../005-rag-knowledge-base-qa/contracts/pipeline-cli.md); lệnh 005 không đổi.

| Lệnh | Story | Cần DB | Cần key | Việc | Mã thoát |
|---|---|---|---|---|---|
| `crawl-jd [--source S ...] [--max-pages N] [--max-jobs N] [--delay 2]` | US1 | không | không | mỗi nguồn (mặc định cả 4): đọc robots → trang danh sách → trang chi tiết chưa có trong raw → parse `JobPosting` → xóa PII → `data/raw/jd/<nguồn>/<ts>.jsonl` | 0 · 1 có nguồn mà trang danh sách cho 0 link, trang chi tiết đã tải parse ra 0 record, hoặc thiếu trường bắt buộc hàng loạt (FR-006); chạy lại mà mọi id đã có là thoát 0 · 4 có nguồn bị chặn (3 lần 403/429 liên tiếp, hoặc robots.txt trả 403/429); các nguồn còn lại vẫn chạy hết |
| `process-jd` | US2 | không | không | đọc mọi raw (crawl + synthetic) → làm sạch, chuẩn hóa, lọc IT, section, dedup → `jd_normalized.jsonl`, `jd_chunks.jsonl`, báo cáo | 0 · 1 không đọc được raw / danh mục, hoặc còn PII sau scrub (FR-009) |
| `synth-jd [--target 500] [--limit N] [--dry-run]` | US5 | không | có | đọc báo cáo `process-jd` mới nhất → tính ô thiếu → sinh tối đa `N` JD → hậu kiểm → `data/raw/jd/synthetic/<ts>.jsonl`; `--dry-run` chỉ in ô thiếu, không gọi LLM | 0 · 1 chưa có báo cáo, hoặc file synthetic mới nhất mới hơn báo cáo (chạy `process-jd` trước) · 2 thiếu key · 3 còn JD lỗi sau retry |
| `seed-jobs [--count 200] [--clean]` | US4 | có (`user_db`, `job_db`) | không | preflight schema theo contract → chọn posting (crawl trước) → Employer seed + `company_profiles` → `job_postings` + `job_skills` idempotent → manifest; `--clean` chỉ xóa dữ liệu của Employer seed | 0 · 1 thiếu JD đủ điều kiện · 2 preflight lỗi (schema thiếu/khác) |

Thứ tự chạy chuẩn: `crawl-jd` → `process-jd` → `synth-jd` → `process-jd` (lần 2, gộp synthetic) → `seed-jobs`.

## Log bắt buộc của `crawl-jd` (SC-002)

Mỗi nguồn in: `robots checked: <url> [status] <verdict>`, mỗi URL bị robots cấm `robots disallow, bo qua: <url>`, và
khối tổng: trang danh sách / chi tiết đã tải, record mới, id đã có bỏ qua, lỗi, bỏ qua theo robots, delay thực tế, trạng
thái nguồn (`ok | blocked | empty`).

## Thống kê `process-jd` (constitution V)

```text
records_in          theo nguồn (crawl / synthetic)
rejected            theo lý do: not_it | missing_field | duplicate
jd_out              JD chuẩn hóa sau dedup
dedup_ratio         JD trùng / JD trước dedup
chunks_out          chunk sinh offline (chưa index)
with_skill_ratio    tỉ lệ JD crawl có ≥ 1 kỹ năng (SC-001)
crawl_vs_synthetic  số và tỉ lệ (FR-026)
distribution        group / level / city / work_type
unknown_skills      top 50 kỹ năng ngoài danh mục
pii_remaining       email + SĐT + dòng liên hệ + URL hồ sơ cá nhân (research R4), phải = 0
cells               số JD crawl / synthetic theo (group, level, city), đầu vào synth-jd (Gap Cell, data-model)
```

## Env (thêm vào `apps/data-pipeline/.env.example`)

| Biến | Mẫu | Dùng bởi |
|---|---|---|
| `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` | như 005 | `synth-jd` |
| `USER_DB_URL` | `postgresql://postgres:secret@localhost:5534/user_db` | `seed-jobs` (thêm khi làm US4) |
| `JOB_DB_URL` | `postgresql://postgres:secret@localhost:5534/job_db` | `seed-jobs` (thêm khi làm US4) |
