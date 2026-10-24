# Data Model: JD Crawling & Seeding

Phase 1 của [plan.md](plan.md). Chỉ ghi dữ liệu mới của 009. Schema `job_db` thuộc job-service
([`docs/architecture/data-model.md`](../../docs/architecture/data-model.md) §2), `knowledge_chunks` thuộc AIE; 009
không tạo/sửa bảng. Định dạng file chi tiết: [contracts/jd-record-formats.md](contracts/jd-record-formats.md).

## Thực thể

| Thực thể | Lưu ở | Khóa | Trường chính | Luật |
|---|---|---|---|---|
| **Crawl Source** | `crawlers/jd_sources.py` (code) | `name` | URL danh sách + tham số trang, regex link chi tiết, cách lấy id JD, selector mô tả HTML (topdev) | chỉ 4 nguồn ở Clarifications NC-3; robots đọc lại mỗi lần chạy |
| **Raw JD** | `data/raw/jd/<nguồn>/<ts>.jsonl` (gitignore) | `(source, source_job_id)` | `url`, `crawled_at`, `title`, `company`, `skills_raw`, `description_text`, `location_raw`, `experience_raw`, `employment_type_raw`, `salary_raw`, `date_posted`, `valid_through`, `synthetic` | PII đã xóa trước khi ghi (FR-009); id đã có thì không crawl lại (FR-006) |
| **Synthetic JD** | `data/raw/jd/synthetic/<ts>.jsonl` (gitignore) | `source_job_id = syn-<group>-<level>-<city>-<n>` | như Raw JD + `cell`, `synthetic = true`, `source = "synthetic"` | công ty hư cấu, 0 PII / URL, kỹ năng thuộc danh mục (FR-024, FR-025) |
| **Skill Dictionary** | `data/seeds/skill_dictionary.yaml` (commit) | `slug` | `name`, `category`, `group`, `aliases[]` | `slug` duy nhất; bí danh không trùng giữa hai kỹ năng; `group` ∈ 5 nhóm FR-022 |
| **Normalized JD** | `data/processed/jd_normalized.jsonl` (gitignore) | `jd_id = <source>:<source_job_id>` | `title`, `company`, `skills[]` (slug), `skills_unknown[]`, `group`, `level`, `work_type`, `city`, `salary_min/max/currency`, `date_posted`, `deadline`, `sections{}`, `language`, `content_hash`, `synthetic`, `source_url` | sắp theo `jd_id` (deterministic, FR-014); `content_hash` duy nhất (FR-013) |
| **JD Chunk** | `data/processed/jd_chunks.jsonl` (gitignore) | `content_hash` | `jd_id`, `section`, `content`, `skills`, `company`, `language`, `source_url` | sinh offline; chỉ index khi làm US3 (Stretch) |
| **Gap Cell** | trong `jd-report-<ts>.json` | `(group, level, city)` | `crawled`, `synthetic`, `target`, `missing` | `missing = max(0, target - crawled - synthetic)` |
| **Seed Employer** | `user_db.users` + `company_profiles` | email `seed-<slug>@seed.ai-recruit.test` | `role = Employer`, `company_name` | không đăng nhập được; chỉ tạo cho công ty có posting seed (FR-021) |
| **Seed Manifest** | `data/processed/job-seed-manifest.jsonl` (gitignore) | `jd_id` | id posting, id Employer, `synthetic` | nơi giữ cờ synthetic (contract không có cột, FR-026) |
| **Pipeline Run Report** | `data/processed/jd-report-<ts>.json` | thời điểm chạy | xem research R8 | in ra màn hình + ghi file mỗi lần chạy (constitution V) |

## Giá trị chuẩn

- `level`: `Intern | Junior | Mid | Senior | Lead | Manager` (S2-FSD-2) hoặc `null`.
- `work_type`: `remote | onsite | hybrid` (`job_postings.work_type`).
- `group`: `backend | frontend | mobile_fullstack | devops | ai_data` (FR-022); kỹ năng Database / System Design gán
  vào `backend`.
- `sections`: khóa `summary | description | requirements | responsibilities | benefits`; thiếu section thì khóa vắng.
- `salary_currency`: `VND | USD`; chỉ có khi `salary_min` hoặc `salary_max` là số.

## Vòng đời một JD

```text
crawl-jd ──► Raw JD ─┐
synth-jd ──► Synthetic JD ─┴─► process-jd ──► Normalized JD (+ JD Chunk, Report)
                                               │ loại: not_it | missing_field | duplicate
                                               ▼
                                         seed-jobs ──► user_db (Employer seed) + job_db.job_postings + job_skills
```

## Mapping theo contract (`data-model.md` §1–§2, NC-1)

| Bảng.cột | Từ Normalized JD / quy ước |
|---|---|
| `users` (Employer seed) | `email = seed-<slug công ty>@seed.ai-recruit.test`, `role = Employer`, password bcrypt ngẫu nhiên không lưu |
| `company_profiles.company_name` | `company` |
| `job_postings.employer_id` | id Employer seed của công ty |
| `title`, `location`, `work_type`, `deadline` | `title`, `city`, `work_type`, `deadline` (trống → `date_posted` + 30 ngày) |
| `description` | `summary` + `description` + `responsibilities` + `benefits` |
| `requirements` | `requirements` |
| `salary_min`, `salary_max`, `salary_currency` | như tên, chỉ khi là số |
| `experience_level_id` | tra `experience_levels.name = level`; JD không có `level` → không chọn vào seed |
| `status` | `open` |
| `job_skills` | tra `skills.slug ∈ skills[]`; thiếu thì thêm từ danh mục |
| (không có cột) | `jd_id`, `synthetic` → Seed Manifest |
