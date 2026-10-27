# Implementation Plan: JD Crawling & Seeding

**Branch**: `docs/jd-crawling-seeding-plan` (clarify + plan + tasks) → `feat/data-pipeline/jd-crawl` →
`feat/data-pipeline/jd-process` → `feat/data-pipeline/jd-synthetic` → `feat/data-pipeline/jd-seed` |
**Date**: 2026-10-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/009-jd-crawling-seeding/spec.md`

## Summary

Mở rộng `apps/data-pipeline/` (005) bằng 4 lệnh: `crawl-jd` (US1) crawl JD IT từ itviec, topdev, careerviet, careerlink
qua khối JSON-LD `JobPosting` trong HTML tĩnh, dùng lại `PoliteFetcher` (thêm luật dừng khi bị chặn); `process-jd` (US2)
offline: làm sạch, xóa PII, chuẩn hóa kỹ năng theo danh mục tự soạn, cấp bậc / thành phố / lương, lọc JD ngoài IT, tách
section, dedup, báo cáo phân bố; `synth-jd` (US5) sinh JD synthetic bằng LLM chỉ cho ô nhóm kỹ năng × cấp bậc × thành
phố còn thiếu; `seed-jobs` (US4) theo contract `data-model.md` §1–§2: tạo Employer seed + `company_profiles` cho mỗi công ty rồi nạp
200 posting vào `job_db`, chạy được khi có migration `company_profiles` (004) và job-service (007). Index JD (US3) là Stretch,
không làm ở Sprint 2 (Clarifications 2026-10-24). Quyết định kỹ thuật: [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.11 (như 005)

**Primary Dependencies**: có sẵn từ 005: `httpx`, `beautifulsoup4`, `openai` (client OpenAI-compatible), `psycopg[binary]`
3, `pyyaml`, `python-dotenv`; dev: `pytest`. Không thêm dependency.

**Storage**: file `data/raw/jd/`, `data/processed/` (gitignore); seed commit `data/seeds/skill_dictionary.yaml`; ghi
`job_db` (PostgreSQL 16) ở US4 theo schema migration của job-service

**Testing**: `pytest` offline với fixture HTML tự soạn (FR-007) và client HTTP / LLM giả; DB kiểm bằng
[quickstart.md](quickstart.md) §5

**Target Platform**: máy dev Windows/macOS/Linux (crawl từ máy DE); CI `ubuntu-latest` job `python` (đã có)

**Project Type**: CLI / batch data pipeline trong monorepo

**Performance Goals**: xử lý + seed ≤ 10 phút (SC-006, không tính thời gian crawl bị giới hạn tốc độ); crawl ~600 trang
chi tiết với delay 2 giây ≈ 20–25 phút; synthetic < 1 USD (SC-008)

**Constraints**: robots.txt + delay ≥ 2 giây + dừng khi bị chặn, không đăng nhập, không né chặn (FR-003, FR-004); 0 PII
trong mọi output (FR-009); không commit nội dung crawl (FR-007); không tạo/sửa bảng (FR-019); file code < 200 dòng
(constitution VII)

**Scale/Scope**: ≥ 500 JD hợp lệ (crawl + synthetic), ~100 kỹ năng trong danh mục, 200 posting seed

**Phụ thuộc**: không còn điểm cần chốt; US4 chỉ chờ migration có trên `main` (004, 007). Mapping ở
[data-model.md](data-model.md), research R10.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Đánh giá | Ghi chú |
|---|---|---|
| I. DB-per-Service | ✅ | US4 ghi `user_db` (Employer seed) và `job_db` theo schema migration của user-service / job-service, preflight dừng khi lệch, không DDL (FR-019); US3 Stretch không đụng `knowledge_chunks` ở S2 |
| II. Gateway & Transport | ✅ N/A | Không có endpoint mới |
| III. Contract-First | ✅ | CLI + định dạng file ở [contracts/](contracts/); mapping theo contract `data-model.md` §1–§2, không đổi contract |
| IV. AI Stateless | ✅ | `synth-jd` gọi LLM qua `LLM_BASE_URL` / key / model của 005 (mặc định gpt-4o-mini), retry giới hạn; không embedding ở S2 |
| V. Data Pipeline tái lập | ✅ | Robots + rate limit + dừng khi bị chặn; xóa PII trước khi ghi raw; idempotent theo `(source, source_job_id)` và `content_hash`; raw/processed gitignore; thống kê mỗi lần chạy. Quality gate S2 (1500 chunk) đã đạt bằng `interview_qa` |
| VI. Quality Gates | ✅ | pytest cho parser, fetcher, chuẩn hóa, lọc, dedup, ô thiếu, hậu kiểm synthetic; không secret; `JOB_DB_URL` vào `.env.example` khi làm US4 |
| VII. Đơn giản & phạm vi | ✅ | Không Scrapy, không Playwright cho JD, không index JD (Stretch), không dependency mới; mỗi module < 200 dòng |

Post-design re-check (sau Phase 1): ✅ không phát sinh vi phạm. Rủi ro điều khoản site (itviec §2.2) là quyết định của DE
ở NC-3, không thuộc nguyên tắc nào của constitution; ghi ở Rủi ro.

## Project Structure

### Documentation (this feature)

```text
specs/009-jd-crawling-seeding/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/
│   ├── pipeline-cli-jd.md       # lệnh, mã thoát, log, thống kê, env
│   └── jd-record-formats.md     # raw / normalized / chunk / skill dictionary
├── checklists/requirements.md
└── tasks.md                     # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
apps/data-pipeline/
├── crawlers/
│   ├── polite_fetcher.py            # SỬA: đếm 403/429 liên tiếp → báo nguồn bị chặn (R3)
│   ├── jd_sources.py                # cấu hình 4 nguồn (R1)
│   ├── jd_page_parser.py            # JSON-LD JobPosting (mảng/@graph) + mô tả HTML topdev → raw (R2)
│   └── jd_listing_crawler.py        # danh sách → link chi tiết → bỏ id đã có → raw record (R4)
├── pipeline/
│   ├── __main__.py                  # SỬA: thêm crawl-jd | process-jd | synth-jd | seed-jobs
│   ├── settings.py                  # SỬA: đường dẫn JD, require_seed_settings (US4)
│   ├── jd_pii.py                    # scrub_pii của 005 + dòng liên hệ + URL hồ sơ cá nhân (R4)
│   ├── jd_crawl_command.py          # US1
│   ├── skill_dictionary.py          # nạp YAML, bí danh → slug, khớp trong text (R5)
│   ├── jd_normalizer.py             # cấp bậc, loại hình, thành phố, lương, ngôn ngữ (R6)
│   ├── jd_sections.py               # tách section + chunk offline (R7)
│   ├── jd_record_builder.py         # raw → Normalized JD, lọc IT, dedup (R7)
│   ├── jd_process_command.py        # US2 + báo cáo phân bố (R8)
│   ├── jd_gap_planner.py            # ô thiếu từ báo cáo (R9)
│   ├── jd_synthetic_generator.py    # prompt + hậu kiểm + công ty hư cấu (R9)
│   ├── jd_synth_command.py          # US5
│   ├── job_seed_selector.py         # US4: chọn 200 posting đa dạng, crawl trước (FR-022)
│   ├── job_db_seed_preflight.py     # US4: đối chiếu information_schema (FR-019)
│   ├── job_db_seed_writer.py        # US4: Employer seed + posting theo contract (R10)
│   └── jd_seed_command.py           # US4: lệnh seed-jobs (tách để mỗi file < 200 dòng)
├── data/seeds/skill_dictionary.yaml # commit
└── tests/                           # + fixtures/jd/*.html tự soạn
docs/architecture/data-pipeline.md   # §5 nguồn JD + §10 phụ thuộc S3-DE-3 (không còn chờ S2-DE-3), cập nhật trong PR jd-crawl
```

**Structure Decision**: theo hướng 005 đã chốt: module `jd_*` đặt cạnh module `qa_*`, dùng lại `text_cleaning`,
`pii_patterns`, `run_report`, `settings` (`RAW_DIR`, `LlmSettings`). Không tạo thư mục `processors/` riêng.

## Delivery Sequence

| PR | Nội dung | Story | Phụ thuộc | Merge khi |
|---|---|---|---|---|
| `docs/jd-crawling-seeding-plan` | clarify + plan + tasks, sprint-plan S2-DE-1/S2-DE-3 | — | — | team review |
| `jd-crawl` | fetcher dừng khi bị chặn, nguồn, parser, `crawl-jd`, tests | US1 | — | CI xanh + quickstart §1 |
| `jd-process` | danh mục kỹ năng, chuẩn hóa, section, lọc IT, dedup, `process-jd`, tests | US2 | `jd-crawl` | quickstart §3 trên dữ liệu crawl thật |
| `jd-synthetic` | ô thiếu, sinh + hậu kiểm, `synth-jd`, tests | US5 | `jd-process` + báo cáo crawl thật | quickstart §4, ≥ 500 JD |
| `jd-seed` | preflight, mapping, `seed-jobs`, `--clean` | US4 | migration 004 (`company_profiles`) + 007 trên `main` | quickstart §5 |

Kiểm tiến độ thứ Năm 05/11. Thứ tự cắt khi trễ: giảm số nguồn crawl (giữ itviec + careerviet) → synthetic bù nhiều hơn
→ US4 chuyển sang S3 nếu 007 chưa có migration (báo FSD, không seed vào schema tự đoán).

## Rủi ro

- **Điều khoản site** (itviec §2.2; điều khoản các nguồn khác chưa đọc): DE chấp nhận cho mục đích học thuật nội bộ,
  không công bố lại, không đưa nội dung crawl vào git, staging (014) quyết định riêng có hiển thị posting crawl không.
- **Cấu trúc trang đổi**: 0 record hoặc thiếu trường hàng loạt → lệnh thất bại (FR-006); parser có fixture cho từng nguồn.
- **Sản lượng thấp hơn dự kiến**: synthetic bù (US5); nếu cần thêm nguồn, vietnamworks là ứng viên tiếp theo (R1).
- **Migration 004 / 007 trễ**: US4 bị chặn; US1, US2, US5 vẫn cho ra JD chuẩn hóa để FSD seed tay hoặc dùng khi 007 xong.

## Complexity Tracking

Không có vi phạm constitution cần biện minh.
