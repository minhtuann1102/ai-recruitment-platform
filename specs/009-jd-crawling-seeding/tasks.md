---

description: "Task list for 009-jd-crawling-seeding"
---

# Tasks: JD Crawling & Seeding

**Input**: Design documents from `/specs/009-jd-crawling-seeding/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: constitution VI bắt buộc test cho logic chính của Python app → mỗi story có task pytest **offline** (không
mạng, không key, không DB; fixture HTML tự soạn, client HTTP / LLM giả). DB và crawl thật kiểm bằng
[quickstart.md](quickstart.md).

**Organization**: theo user story; phase theo **Delivery Sequence** của [plan.md](plan.md) (US1 → US2 → US5 → US4 →
US3), không theo thứ tự ưu tiên: US4 là P1 nhưng chờ migration 004 + 007 nên làm sau US5 (xem Dependencies). Mọi đường
dẫn code tương đối `apps/data-pipeline/`. Chạy lệnh trong `apps/data-pipeline/` bằng `python -m pipeline <lệnh>` /
`python -m pytest`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: chạy song song được (khác file, không phụ thuộc task chưa xong); task test `[P]` song song với các cặp module/test khác nhưng chạy sau module của chính nó
- **[Story]**: US1..US5 theo spec.md; mã `S2-DE-#` để truy vết về sprint plan

---

## Phase 1: Setup · PR `feat/data-pipeline/jd-crawl`

**Purpose**: branch và hằng đường dẫn dùng chung cho mọi lệnh JD

- [X] T001 Tạo branch `feat/data-pipeline/jd-crawl` từ `main` (sau khi PR #42 merge); kiểm `.gitignore` gốc đã có `apps/data-pipeline/data/raw/` và `apps/data-pipeline/data/processed/` (bao `data/raw/jd/` và mọi file processed của JD), có rồi thì không thêm dòng *(thực hiện: branch tạo từ `docs/jd-crawling-seeding-plan` vì PR #42 chưa merge; `.gitignore` đã đủ, không thêm dòng)*
- [X] T002 Thêm hằng vào `pipeline/settings.py` theo data-model.md: `JD_RAW_DIR = RAW_DIR / "jd"`, `SKILL_DICTIONARY_PATH = APP_DIR / "data" / "seeds" / "skill_dictionary.yaml"`, `JD_NORMALIZED_PATH = PROCESSED_DIR / "jd_normalized.jsonl"`, `JD_CHUNKS_PATH = PROCESSED_DIR / "jd_chunks.jsonl"`, `JD_SEED_MANIFEST_PATH = PROCESSED_DIR / "job-seed-manifest.jsonl"`

---

## Phase 2: Foundational (chặn US1, US2, US5)

**Purpose**: xóa PII theo phạm vi FR-009 cho raw, processed và synthetic

- [X] T003 Tạo `pipeline/jd_pii.py` (research R4): `scrub_jd_pii(text) -> str` = `pii_patterns.scrub_pii` (email + SĐT) + bỏ cả **dòng liên hệ** (dòng bắt đầu bằng "Liên hệ", "Contact", "Người liên hệ", "Hotline", hoặc "Mr./Ms./Mrs./Anh/Chị/A./C. + tên" đi kèm số điện thoại hay email) + xóa **URL hồ sơ cá nhân** (`linkedin.com/in/`, `facebook.com/`, `fb.com/`, `zalo.me/`, `t.me/`); `count_jd_pii(text) -> int` đếm cả ba loại (nguồn của `pii_remaining`). Không sửa `scrub_pii` của 005
- [X] T004 [P] `tests/test_jd_pii.py`: mỗi loại PII bị xóa; dòng "Liên hệ: Chị Lan 0912 345 678" bị bỏ cả dòng; dòng "Contact us to learn more" không kèm SĐT/email được giữ; tên công ty và URL công ty (`congty-gia.vn/careers`) được giữ; `count_jd_pii` = 0 sau scrub. PII cài vào test MUST dùng miền trông thật (vd `tuyendung@congty-gia.vn`), vì `pii_patterns` coi `.test`, `.example`, `example.com` không phải PII → test sẽ qua mà không kiểm gì

**Checkpoint**: `python -m pytest tests/test_jd_pii.py` xanh

---

## Phase 3: User Story 1 - Crawl JD IT có kiểm soát (Priority: P1) · S2-DE-1 · PR `jd-crawl` 🎯 MVP

**Goal**: `crawl-jd` lấy JD từ itviec, topdev, careerviet, careerlink qua JSON-LD `JobPosting`, tôn trọng robots, dừng
nguồn khi bị chặn, idempotent theo `(source, source_job_id)`, raw đã xóa PII nằm ngoài git

**Independent Test**: quickstart §1 (`crawl-jd --source careerviet --max-pages 2 --max-jobs 10`) + `pytest tests -k "jd_page_parser or polite_fetcher or jd_crawl"`

- [X] T005 [US1] Sửa `crawlers/polite_fetcher.py` (đang 136 dòng, giữ < 200; research R3): trong `_get_html` đếm phản hồi 403/429 **liên tiếp** và trang thử thách chống bot (HTML chứa "Attention Required" hoặc "Just a moment"); đủ 3 lần liên tiếp → `self.blocked = True`, log `source blocked: <origin>`, mọi `fetch` sau đó trả `None` mà không gửi request; phản hồi 2xx bình thường đặt lại bộ đếm; robots.txt trả 403/429 → `blocked` ngay từ đầu (không báo thành `empty`). Không retry, không đổi header/IP, không render để vượt thử thách (FR-004)
- [X] T006 [P] [US1] Thêm vào `tests/test_polite_fetcher.py` (dùng `httpx.MockTransport`, `sleep`/`clock` giả): 403, 403, 403 → `blocked` và 0 request thêm; 403, 200, 403 → không `blocked`; trang thử thách HTTP 200 tính là bị chặn; robots.txt trả 403 → `blocked` ngay, 0 request trang; robots `tests/fixtures/jd/robots_two_star_groups.txt` → `/subscriptions/new` bị cấm, `/it-jobs` được phép (giữ hành vi nhóm `*` đầu tiên của `urllib.robotparser`, FR-003)
- [X] T007 [P] [US1] Tạo fixture tự soạn trong `tests/fixtures/jd/` (công ty, người, nội dung đều bịa; FR-007): `robots_two_star_groups.txt` (nhóm 1 `User-Agent: *` + `Disallow: /subscriptions/new`, nhóm 2 `User-Agent: *` + `Allow: /`); mỗi nguồn một `<nguồn>_listing.html` có 2–3 link chi tiết đúng regex của nguồn; `itviec_detail.html` (`JobPosting` trong mảng JSON-LD, `baseSalary` dạng chữ "Sign in to view salary"); `careerviet_detail.html` (`@graph`, `baseSalary` số VND `minValue`/`maxValue`, mô tả có dòng "Liên hệ: Anh Minh - 0912 345 678 - hr@congty-gia.vn"); `topdev_detail.html` (`description` JSON-LD ~180 ký tự, mô tả đầy đủ trong HTML theo selector của nguồn); `careerlink_detail.html` (không có `skills`); `broken_jsonld.html` (một khối JSON lỗi + một khối hợp lệ); `no_jobposting.html`; `challenge.html` (tiêu đề "Attention Required")
- [X] T008 [P] [US1] Tạo `crawlers/jd_sources.py` (research R1): dataclass `JdSource(name, base_url, listing_url: Callable[[int], str], detail_link_re, job_id_re, description_selector: Optional[str] = None)` + `SOURCES` gồm đúng 4 nguồn `itviec`, `topdev`, `careerviet`, `careerlink` (Clarifications NC-3). itviec: danh sách `/it-jobs?page=N`, chi tiết `/it-jobs/<slug>-<id>`. Ba nguồn còn lại: mở 1 trang danh sách + 1 trang chi tiết qua `PoliteFetcher` (robots, delay ≥ 2 s) để chốt URL danh sách IT, tham số trang, regex link và regex id; ghi URL mẫu vào comment. Thêm nguồn = thêm một mục, không sửa code crawl *(thực hiện offline, không gửi request: cấu hình itviec theo spec; URL danh sách, tham số trang, regex link / id và selector của topdev, careerviet, careerlink là dự đoán, đánh dấu `DU DOAN` trong `crawlers/jd_sources.py`, chưa có URL mẫu. Chốt bằng request thật ở T016: sai thì nguồn báo `empty`, thoát 1)*
- [X] T009 [P] [US1] Tạo `crawlers/jd_page_parser.py` (research R2, contract Raw JD): `parse_job_page(html, source, url, crawled_at) -> Optional[dict]` đọc mọi `script[type="application/ld+json"]`, duyệt cả mảng lẫn `@graph`, bỏ khối JSON lỗi thay vì dừng; trả `None` khi không có `JobPosting`. Map: `title`, `hiringOrganization.name` → `company`, `skills` → `skills_raw` (careerlink: `[]`), `description` HTML → `description_text` bằng `get_text("\n")` giữ xuống dòng ở tiêu đề section (topdev: lấy thân mô tả từ HTML theo `description_selector`), `jobLocation[].address` (`addressRegion`/`addressLocality`) → `location_raw`, `experienceRequirements` → `experience_raw`, `employmentType` + `jobLocationType` → `employment_type_raw`, `baseSalary` → `salary_raw` (số: `{"currency", "min", "max", "text": null}`; chữ: `{"text", "min": null, "max": null}`), `datePosted`, `validThrough`, `"synthetic": false`. Trường bắt buộc: "`source`, `source_job_id`, `url` (synthetic: `null`), `crawled_at`, `title`, `company`, `description_text`"
- [X] T010 [P] [US1] `tests/test_jd_page_parser.py`: từng fixture chi tiết cho đúng trường; topdev lấy mô tả dài từ HTML; careerlink `skills_raw == []`; itviec lương chữ → `min`/`max` null; careerviet lương số; `broken_jsonld.html` vẫn ra record từ khối hợp lệ; `no_jobposting.html` → `None`
- [X] T011 [US1] Tạo `crawlers/jd_listing_crawler.py` (research R4): `crawl_source(source, fetcher, existing_ids, max_jobs, now) -> (records, stats)`: duyệt trang danh sách 1, 2, … tới khi trang không có link mới hoặc fetcher hết lượt; lấy link chi tiết theo `detail_link_re`, bỏ trùng, đổi sang URL tuyệt đối; id đã có trong `existing_ids` → bỏ qua **không request**; tải tối đa `max_jobs` trang chi tiết → `parse_job_page` → `scrub_jd_pii` trên mọi trường chuỗi trước khi trả. `stats`: `listing_pages`, `detail_pages`, `new_records`, `skipped_existing`, `errors`, `skipped_by_robots`, `delay`, `status` (`ok | blocked | empty`); `empty` chỉ khi trang danh sách cho 0 link hoặc trang chi tiết đã tải parse ra 0 record
- [X] T012 [US1] Tạo `pipeline/jd_crawl_command.py` (contract pipeline-cli-jd.md): `run_crawl_jd(args)` đọc id đã có từ `JD_RAW_DIR/<nguồn>/*.jsonl`; mỗi nguồn (mặc định cả 4, các nguồn sau vẫn chạy khi một nguồn lỗi) tạo `PoliteFetcher` mới (robots đọc lại mỗi lần chạy) với `delay=args.delay` và tổng lượt = `--max-pages` + `--max-jobs`; ghi `JD_RAW_DIR/<nguồn>/<UTC timestamp>.jsonl` (`ensure_ascii=False`) chỉ khi có record mới; in log bắt buộc (`robots checked: ...`, `robots disallow, bo qua: ...`, khối tổng theo contract). Mã thoát: 4 khi có nguồn `blocked`; ngược lại 1 khi có nguồn `empty` hoặc > 50% trang chi tiết đã tải thiếu trường bắt buộc; còn lại 0. **Mã 1 chỉ khi trang danh sách cho 0 link, hoặc trang chi tiết đã tải parse ra 0 record; chạy lại mà mọi id đã có là thoát 0**
- [X] T013 [US1] Sửa `pipeline/__main__.py`: thêm lệnh `crawl-jd [--source S ...] [--max-pages N] [--max-jobs N] [--delay 2]` (`--source` chọn trong 4 tên của `SOURCES`, lặp được), hằng `EXIT_SOURCE_BLOCKED = 4`, đăng ký `run_crawl_jd` trong `HANDLERS`; giữ file < 200 dòng (đang 118), quá thì tách đăng ký lệnh JD sang `pipeline/jd_cli.py`
- [X] T014 [US1] `tests/test_jd_crawl_command.py` (`MockTransport` phục vụ fixture cho 2 nguồn, `monkeypatch` `JD_RAW_DIR` sang `tmp_path`): (a) raw ghi đủ trường bắt buộc, `count_jd_pii` = 0 trên mọi record; (b) chạy lại → `record mới: 0`, 0 request trang chi tiết, thoát 0; (c) một nguồn trả 403 ba lần → thoát 4, nguồn kia vẫn ghi raw; (d) trang danh sách 0 link → thoát 1
- [X] T015 [US1] Cập nhật `docs/architecture/data-pipeline.md` §5 (4 nguồn itviec, topdev, careerviet, careerlink qua JSON-LD; không Playwright; topcv, jobsgo loại vì 403; itviec ẩn lương) và §10 (S3-DE-3 không còn chờ S2-DE-3), theo plan
- [X] T016 [US1] Trước tiên kiểm cấu hình còn đoán ở T008 (topdev, careerviet, careerlink trong `crawlers/jd_sources.py`: URL danh sách, tham số trang, regex link / id, selector mô tả) bằng `crawl-jd --source <tên> --max-pages 2 --max-jobs 3`; sai thì sửa `SOURCES` và fixture tương ứng. Rồi chạy quickstart §1 (careerviet, `--max-pages 2 --max-jobs 10`): đọc log robots + delay, chạy lại thấy `record mới: 0`; rồi quickstart §2 crawl đủ 4 nguồn, ghi số record + trạng thái từng nguồn vào mô tả PR; `python -m pytest` xanh; mở PR `jd-crawl`

**Checkpoint**: raw JD thật trong `data/raw/jd/`, 0 PII, chạy lại không request thừa

---

## Phase 4: User Story 2 - Xử lý JD: clean, trích kỹ năng, chunk theo section (Priority: P1) · S2-DE-2 · PR `jd-process`

**Goal**: `process-jd` offline biến raw (crawl + synthetic) thành Normalized JD + JD Chunk + báo cáo phân bố, không cần
DB hay key, output deterministic

**Independent Test**: quickstart §3 + `pytest tests -k "skill_dictionary or jd_normalizer or jd_sections or jd_record or jd_process"`

- [X] T017 [P] [US2] Tạo `data/seeds/skill_dictionary.yaml` (research R5, commit) ~100 kỹ năng, mỗi mục `slug`, `name`, `category` (giá trị cột `job_db.skills.category`, vd "Frontend, Backend, DevOps"), `group` (`backend | frontend | mobile_fullstack | devops | ai_data`; Database / System Design → `backend`), `aliases`. Luật: "`slug` duy nhất, chữ thường; bí danh so khớp không phân biệt hoa thường, không trùng giữa hai kỹ năng". Nếu `main` đã có seed skills của FSD (S2-FSD-1, ~50 skills) thì dùng đúng `slug` + `category` của FSD; chưa có thì ghi danh sách slug vào mô tả PR để FSD xác nhận (lệch slug, vd `nodejs` / `node-js`, sẽ thành hai kỹ năng ở US4) *(thực hiện: 103 kỹ năng; `main` chưa có seed skills của FSD → ghi danh sách slug vào mô tả PR `jd-process` ở T029)*
- [X] T018 [P] [US2] Tạo `pipeline/skill_dictionary.py`: nạp YAML từ `SKILL_DICTIONARY_PATH`, kiểm luật T017 (vi phạm → lỗi, `process-jd` thoát 1); `canonical(name) -> Optional[str]` qua bảng bí danh; `find_in_text(text) -> List[str]` khớp theo ranh giới từ, không phân biệt hoa thường, đúng với tên có ký tự đặc biệt (`c#`, `c++`, `.net`, `node.js`) bằng lookaround `(?<![\w])...(?![\w])`; `group_of(slugs)` = nhóm xuất hiện nhiều nhất, hòa thì theo thứ tự `backend, frontend, mobile_fullstack, devops, ai_data`
- [X] T019 [P] [US2] `tests/test_skill_dictionary.py`: file YAML thật qua luật; slug trùng / bí danh trùng giữa hai kỹ năng → lỗi; `ReactJS`, `React.js`, `react` → `react`; "c++" không khớp `c`; kỹ năng lạ trả về danh sách ngoài danh mục
- [X] T020 [P] [US2] Tạo `pipeline/jd_normalizer.py` (research R6): **cấp bậc** `Intern | Junior | Mid | Senior | Lead | Manager` hoặc `null`: từ khóa trong tiêu đề trước (Intern, Thực tập, Fresher → Junior, Junior, Middle/Mid, Senior, Lead/Trưởng nhóm, Manager/Quản lý), không có thì theo số năm kinh nghiệm (< 1 Intern, 1–2 Junior, 3–4 Mid, ≥ 5 Senior); **loại hình** `remote | onsite | hybrid` (`TELECOMMUTE` hoặc remote / từ xa → `remote`; hybrid → `hybrid`; còn lại `onsite`); **thành phố** về tên chuẩn (Hà Nội, Hồ Chí Minh, Đà Nẵng, …) qua bí danh (`Ho Chi Minh`, `HCM`, `TP.HCM`, `Hanoi`), nhiều địa điểm lấy địa điểm đầu; **lương** chỉ nhận số (số trong `baseSalary`, "9.000.000 VND - 20.000.000 VND", "15 - 25 triệu", "$1,000 - 2,000"), chữ ("thỏa thuận", "Sign in to view") → trống; `salary_currency` `VND | USD` chỉ khi có `salary_min` hoặc `salary_max`; **ngôn ngữ** `vi | en | mixed` theo tỉ lệ ký tự có dấu tiếng Việt (ngưỡng là hằng có tên trong module, test chốt giá trị)
- [X] T021 [P] [US2] `tests/test_jd_normalizer.py`: mỗi luật cấp bậc (tiêu đề thắng số năm; Fresher → Junior; không suy ra được → `null`), loại hình, bí danh thành phố, 4 dạng lương số + 3 dạng chữ, ngôn ngữ vi / en / mixed
- [X] T022 [P] [US2] Tạo `pipeline/jd_sections.py` (research R7, FR-012): tách `description_text` theo tiêu đề section Việt/Anh (Mô tả công việc / Job description, Yêu cầu / Requirements / Your skills, Trách nhiệm / Responsibilities, Quyền lợi / Benefits / Why you'll love working here) thành `sections` với khóa `summary | description | requirements | responsibilities | benefits` (không nhận ra → toàn bộ vào `description`; `summary` dựng từ tiêu đề, công ty, kỹ năng, cấp bậc); `build_chunks(jd)` = 1 chunk tóm tắt + 1 chunk mỗi section, section dài hơn `MAX_ANSWER_CHARS` (4000, `pipeline/collect_command.py`) chia theo đoạn, không cắt mất nội dung; chunk đúng trường contract `{"jd_id", "section", "content", "content_hash", "skills", "company", "language", "source_url"}`
- [X] T023 [P] [US2] `tests/test_jd_sections.py`: tiêu đề Việt và Anh, JD không có tiêu đề → `summary` + `description`, section 9.000 ký tự → ≥ 3 chunk và nối lại đủ nội dung
- [X] T024 [US2] Tạo `pipeline/jd_record_builder.py` *(tách thêm `jd_record_dedup.py`, `jd_salary.py`, `jd_process_report.py` để mỗi file < 200 dòng; mô tả < 200 ký tự sau làm sạch tính là `missing_field`)* (research R7, FR-008, FR-013, FR-028): raw → Normalized JD đúng các trường data-model.md (`jd_id = <source>:<source_job_id>`, `skills`, `skills_unknown`, `group`, `level`, `work_type`, `city`, `salary_*`, `date_posted`, `deadline`, `sections`, `language`, `content_hash`, `synthetic`, `source_url`) dùng `text_cleaning.clean_text`; kỹ năng = `canonical(skills_raw)` ∪ `find_in_text(tiêu đề + mô tả)`; loại với lý do `missing_field` (thiếu trường bắt buộc), `not_it` (giữ JD khi tiêu đề khớp ≥ 1 kỹ năng hoặc từ khóa nghề IT như developer, engineer, lập trình, tester, QA, DevOps, data, hoặc mô tả khớp ≥ 2 kỹ năng), `duplicate`; `content_hash` = SHA-256 của `công ty | tiêu đề | mô tả` sau NFC, chữ thường, gộp khoảng trắng; trùng hash → giữ bản có nhiều trường khác rỗng hơn; cùng (công ty, tiêu đề) nhưng khác hash → chỉ cảnh báo; kết quả sắp theo `jd_id`
- [X] T025 [US2] `tests/test_jd_record_builder.py`: JD ngoài IT (thiết kế đồ họa) → `not_it`; JD trùng giữa hai nguồn → giữ bản nhiều trường hơn; trùng gần đúng → cảnh báo, giữ cả hai; careerlink không có `skills` vẫn trích được kỹ năng từ mô tả; dấu tiếng Việt còn nguyên sau làm sạch
- [X] T026 [US2] Tạo `pipeline/jd_process_command.py` (contract "Thống kê `process-jd`", research R8): đọc mọi raw trong `JD_RAW_DIR` (crawl + `synthetic/`), nạp danh mục, build → ghi `JD_NORMALIZED_PATH`, `JD_CHUNKS_PATH`; báo cáo in ra màn hình + ghi `PROCESSED_DIR/jd-report-<UTC timestamp>.json` gồm `records_in` theo nguồn (crawl / synthetic), `rejected` theo lý do, `jd_out`, `dedup_ratio`, `chunks_out`, `with_skill_ratio` (chỉ JD crawl), `crawl_vs_synthetic`, `distribution` group / level / city / work_type, `unknown_skills` top 50, `pii_remaining` (`count_jd_pii` trên mọi output), và `cells` = số JD crawl / synthetic theo `(group, level, city)` cho US5. Thoát 1 khi không đọc được raw / danh mục hoặc `pii_remaining` > 0. Cùng input → file output giống hệt từng byte (FR-014)
- [X] T027 [US2] Sửa `pipeline/__main__.py` (hoặc `jd_cli.py`): thêm lệnh `process-jd`, đăng ký `run_process_jd`
- [X] T028 [US2] `tests/test_jd_process_command.py` (raw JSONL tự soạn trong `tmp_path`, có JD trùng giữa hai nguồn, JD ngoài IT, JD có dòng liên hệ): số `jd_out` / `rejected` đúng, `pii_remaining` = 0, chạy hai lần cho file giống hệt, báo cáo có đủ khóa của contract + `cells`
- [X] T029 [US2] Chạy quickstart §3 trên raw thật: `pii_remaining 0`, `with_skill_ratio ≥ 0.9` (SC-001), đọc tay 10 JD ngẫu nhiên không còn dòng liên hệ; bổ sung kỹ năng đáng thêm từ `unknown_skills` vào danh mục rồi chạy lại; mở PR `jd-process` *(2026-10-28: sửa theo review + spec Clarifications Session 2026-10-28 — cấp bậc (T020), lọc IT tách `jd_it_filter.py` + nhóm theo tiêu đề (T024), thành phố tách `jd_city.py` (T020), tiêu đề section careerlink / careerviet / topdev (T022), tách bí danh + thêm kỹ năng → 138 kỹ năng (T017); raw thật: 515 vào, 341 JD (not_it 174), `with_skill_ratio` 0.9853, `pii_remaining` 0, thành phố trống 8, cấp bậc trống 37, 56 ô; 215 JD có `requirements`, 186 JD đủ điều kiện seed của T041 (< 200 → US5 phải bù); chạy lại giống hệt từng byte. Còn: DE đọc tay 10 JD)*

**Checkpoint**: Normalized JD + báo cáo phân bố trên dữ liệu thật (đủ cho demo Sprint 2 phần "JD data đã xử lý")

---

## Phase 5: User Story 5 - Bù JD synthetic theo phần thiếu (Priority: P2) · S2-DE-1 (phần bù) · PR `jd-synthetic`

**Goal**: `synth-jd` chỉ sinh JD cho ô (nhóm kỹ năng × cấp bậc × thành phố) còn thiếu, công ty hư cấu, 0 PII, qua cùng
bước xử lý US2, để đạt ≥ 500 JD hợp lệ

**Independent Test**: quickstart §4 + `pytest tests -k "jd_gap or jd_synthetic or jd_synth"`

- [X] T030 [P] [US5] Tạo `pipeline/jd_gap_planner.py` (research R9): lưới 5 nhóm × 6 cấp bậc × 3 thành phố (Hà Nội, Hồ Chí Minh, Đà Nẵng) = 90 ô đọc từ `cells` của báo cáo mới nhất; `missing = max(0, target - crawled - synthetic)`. Bước 1 bù số lượng: `need_total = max(0, 500 - jd_hợp_lệ)` (500 = `--target`), mỗi lượt +1 JD cho ô ít JD nhất (hòa → thứ tự cố định group, level, city) tới khi hết `need_total`. Bước 2 bù sàn đa dạng (FR-022), tính trên số đã cộng bước 1: mỗi nhóm kỹ năng (5), mỗi cấp Junior / Mid / Senior, mỗi thành phố (3) cần ≥ `sàn` JD (mặc định 20); giá trị nào thiếu thì sinh phần thiếu vào ô ít JD nhất thuộc giá trị đó. Crawl đủ 500 và đủ sàn → kế hoạch rỗng
- [X] T031 [P] [US5] `tests/test_jd_gap_planner.py`: báo cáo đủ 500 và đủ sàn → 0 JD; báo cáo thiếu nhóm `ai_data` và cấp `Lead` → JD rơi vào đúng ô thiếu; tổng không vượt phần thiếu; hai lần gọi cho cùng kết quả (thứ tự hòa cố định)
- [X] T032 [P] [US5] Tạo `pipeline/jd_synthetic_generator.py` (research R9, FR-024, FR-025, FR-027): mỗi JD của một ô, code chọn kỹ năng từ danh mục của nhóm và tên công ty hư cấu ghép từ danh sách từ cố định (deterministic theo `(ô, số thứ tự)`, không trùng tên công ty nào trong JD crawl); LLM (client OpenAI-compatible + `LlmSettings` của 005, mặc định `openai/gpt-4o-mini`) chỉ viết tiêu đề + các section theo tham số ô, trả JSON; **không đưa nội dung JD crawl vào prompt**. Hậu kiểm bằng code: JSON đúng dạng, kỹ năng thuộc danh mục, `count_jd_pii` = 0, 0 URL, đủ section; lỗi → retry tối đa 2 lần rồi bỏ. Output đúng dạng Raw JD + `"cell": {"group", "level", "city"}`, `"synthetic": true`, `"source": "synthetic"`, `"url": null`, `source_job_id = syn-<group>-<level>-<city>-<n>` với `n` đánh tiếp từ số lớn nhất đã có của ô (JD synthetic bị `process-jd` loại thì lần sau sinh số mới, ô thiếu vẫn được lấp) *(thực hiện: tham số + prompt tách sang `pipeline/jd_synthetic_prompt.py` để file < 200 dòng; hậu kiểm thêm round trip qua `build_record` của `process-jd`: (group, level, city) suy lại phải trùng ô, đủ section mô tả / yêu cầu / quyền lợi; cấm cụm "Khoa học máy tính", "TS", "worker node" ngoài DevOps)*
- [X] T033 [P] [US5] `tests/test_jd_synthetic_generator.py` (client LLM giả): JSON lỗi / có email / kỹ năng lạ → bị loại sau retry; JD hợp lệ có đủ trường Raw JD + cờ synthetic; tên công ty không nằm trong danh sách công ty crawl; prompt không chứa chuỗi nào lấy từ raw crawl; cùng `(ô, n)` cho cùng công ty và id
- [X] T034 [US5] Tạo `pipeline/jd_synth_command.py` (contract `synth-jd [--target 500] [--limit N] [--dry-run]`): đọc báo cáo `process-jd` mới nhất (không có → thoát 1; file synthetic raw mới nhất mới hơn báo cáo → thoát 1 "chạy process-jd trước", tránh sinh trùng khi chạy `synth-jd` hai lần liền); `--dry-run` chỉ in ô thiếu, không gọi LLM, không cần key; còn lại `require_llm_settings()` (thiếu key → thoát 2 trước mọi lời gọi); bỏ qua id đã có trong `JD_RAW_DIR/synthetic/*.jsonl`; sinh tối đa `--limit` JD; ghi `JD_RAW_DIR/synthetic/<UTC timestamp>.jsonl`; in số đã sinh theo ô; còn JD lỗi sau retry → thoát 3
- [X] T035 [US5] Sửa `pipeline/__main__.py` (hoặc `jd_cli.py`): thêm lệnh `synth-jd`, đăng ký `run_synth_jd`
- [X] T036 [US5] `tests/test_jd_synth_command.py`: `--dry-run` 0 lời gọi LLM; thiếu key → thoát 2; chạy lại khi không còn ô thiếu → 0 lời gọi LLM; chạy `synth-jd` hai lần liền không qua `process-jd` → lần 2 thoát 1, không sinh thêm; JD synthetic bị loại ở `process-jd` → lần sau sinh id mới cho đúng ô đó; JD synthetic đi qua `process-jd` (T026) và được đếm vào `crawl_vs_synthetic`
- [X] T037 [US5] Chạy quickstart §4: `--dry-run`, `--limit 10` rồi đọc kỹ 10 JD, sinh đủ, `process-jd` lần 2 → ≥ 500 JD hợp lệ (SC-001), ghi tỉ lệ crawl / synthetic và chi phí (SC-008 < 1 USD) vào mô tả PR; mở PR `jd-synthetic` *(2026-10-28, theo Clarifications "chỉ bù sàn": key LLM (DeepSeek) trả 402 hết số dư → 24 JD synthetic (`--target 0`: frontend +12, mobile_fullstack +9, backend +3; Đà Nẵng lên 20) do Claude viết trong phiên DE, qua cùng hậu kiểm `generate_one`, 24/24 đạt lần đầu, ghi `data/raw/jd/synthetic/20261028T063322Z.jsonl`. `process-jd` lần 2: 365 JD (341 crawl + 24 synthetic, 6.6%), `pii_remaining` 0, mọi nhóm / Junior–Mid–Senior / 3 thành phố ≥ 20; kế hoạch bù sau đó = 0 JD; đủ điều kiện seed T041: 210 JD (191 nếu `experience_levels` không có Manager); chi phí LLM 0)*

**Checkpoint**: ≥ 500 JD chuẩn hóa, đủ sàn đa dạng; FSD có thể dùng file chuẩn hóa nếu cần seed tay trước khi có US4

---

## Phase 6: User Story 4 - Seed 200 job posting vào job_db (Priority: P1 — chờ migration 004, 007) · S2-DE-4 · PR `jd-seed`

**Goal**: `seed-jobs` tạo Employer seed + `company_profiles` cho mỗi công ty rồi nạp 200 posting đa dạng vào `job_db`
theo contract `docs/architecture/data-model.md` §1–§2, idempotent, dọn riêng được

**Independent Test**: quickstart §5 trên DB đã chạy migration user-service (004) + job-service (007) + `pytest tests -k "job_seed or job_db_seed"`

- [ ] T038 [US4] **Gate:** kiểm `main` đã có migration `company_profiles` (user-service, 004) và job-service (007) với các bảng `users`, `company_profiles`, `job_postings`, `job_skills`, `skills`, `experience_levels`; chưa có → dừng phase, báo FSD (plan: US4 chuyển S3 nếu 007 chưa có, không seed vào schema tự đoán). Có rồi: đối chiếu tên cột thật với bảng Mapping của data-model.md (cột NOT NULL không có default phải có nguồn giá trị); kiểm `experience_levels` có đủ 6 tên `Intern | Junior | Mid | Senior | Lead | Manager` (contract ví dụ chỉ có Intern…Lead): tên nào thiếu thì JD cấp đó không được chọn vào seed, ghi vào mô tả PR
- [ ] T039 [US4] **Quyết định (DE + FSD) trước T045:** cách tạo password Employer seed theo FR-021 ("bcrypt của chuỗi ngẫu nhiên không lưu"); `requirements.txt` chưa có `bcrypt` và Python 3.11 trên Windows không có `crypt`. Chọn một: (a) thêm `bcrypt` vào `requirements.txt` (sửa dòng "Không thêm dependency" trong plan.md); (b) `crypt(gen_random_uuid()::text, gen_salt('bf'))` của pgcrypto nếu `user_db` có extension; (c) chuỗi đúng định dạng bcrypt sinh ngẫu nhiên, chỉ khi FSD xác nhận API đăng nhập trả 401 sạch (không 500) với hash đó. Ghi lựa chọn vào research.md R10
- [x] T040 [P] [US4] (2026-10-28 xong) Thêm `USER_DB_URL=postgresql://postgres:secret@localhost:5534/user_db` và `JOB_DB_URL=postgresql://postgres:secret@localhost:5534/job_db` vào `.env.example` (contract Env); thêm `require_seed_settings()` vào `pipeline/settings.py` (thiếu biến → `ConfigError`, lệnh thoát 2)
- [x] T041 [P] [US4] (2026-10-28 xong: dữ liệu thật 210 JD đủ điều kiện với 6 cấp → 200 posting, 176 crawl + 24 synthetic, bỏ 1 JD trùng khóa posting; chỉ 5 cấp Intern…Lead → 191 < 200, thoát 1; frontend 17, mobile 18, Đà Nẵng 19 dưới sàn 20 → cảnh báo) Tạo `pipeline/job_seed_selector.py` (FR-018, FR-022): từ `JD_NORMALIZED_PATH` chỉ nhận JD có tiêu đề, mô tả, yêu cầu, thành phố, loại hình, `level` có trong `experience_levels` và ≥ 1 kỹ năng; chọn `--count` (mặc định 200) posting **JD crawl trước, synthetic chỉ lấp phần thiếu**, phủ ≥ 5 nhóm kỹ năng, ≥ 3 cấp bậc, ≥ 3 thành phố; deterministic; không đủ JD đạt điều kiện → trả lý do (lệnh thoát 1)
- [x] T042 [P] [US4] (2026-10-28 xong) `tests/test_job_seed_selector.py`: đủ crawl → 0 synthetic được chọn; crawl thiếu nhóm `devops` → synthetic `devops` lấp; kết quả phủ đủ sàn đa dạng; JD không có `level` không được chọn; chạy hai lần cùng kết quả
- [x] T043 [P] [US4] (2026-10-28 xong; thêm kiểm cột NOT NULL không default ngoài Mapping) Tạo `pipeline/job_db_seed_preflight.py` (FR-019): danh sách bảng/cột cần theo bảng Mapping của data-model.md; đọc `information_schema.columns` của `user_db` và `job_db`; hàm thuần `missing_columns(expected, actual)`; thiếu bảng/cột → báo tên và thoát 2 **trước mọi lệnh ghi**; MUST NOT tạo/sửa bảng
- [x] T044 [P] [US4] (2026-10-28 xong) `tests/test_job_db_seed_preflight.py` (hàm thuần, không DB): đủ cột → rỗng; thiếu `company_profiles.company_name` hoặc bảng `job_skills` → báo đúng tên
- [x] T045 [US4] (2026-10-28 xong trừ hash password: `SEED_PASSWORD_HASH = None` trong `jd_seed_command.py` → seed thoát 2 tới khi T039 chốt; `skills` tra slug rồi tra `name` trước khi thêm (không cần UNIQUE, trùng tên khác slug thì dùng lại); sửa theo code review (H1, M1, M3, M6) (test lệnh trên DB giả `tests/jd_seed_fake_db.py`); thử trên cluster Postgres tạm dựng theo contract: lần 1 200 posting / 123 Employer, lần 2 0 posting mới, `--clean` chỉ xóa dữ liệu seed, schema lệch → thoát 2 không ghi) Tạo `pipeline/job_db_seed_writer.py` (research R10, bảng Mapping data-model.md; dùng lựa chọn T039): Employer seed mỗi công ty `users` (`role = Employer`, email `seed-<slug công ty>@seed.ai-recruit.test`, `email_verified = true`, MUST NOT chứa tên hay liên hệ người thật) + `company_profiles.company_name`, đã có theo email thì dùng lại; posting: `employer_id`, `title`, `location` = `city`, `work_type`, `deadline` (trống → `date_posted` + 30 ngày), `description` = `summary` + `description` + `responsibilities` + `benefits`, `requirements`, `salary_min` / `salary_max` / `salary_currency` chỉ khi là số, `experience_level_id` tra theo tên, `status = open`; khóa idempotent `(employer_id, title, md5(description))` kiểm trong DB; `job_skills` tra `skills.slug`, thiếu thì thêm từ danh mục `ON CONFLICT (slug) DO NOTHING`; mỗi DB một transaction, ghi `user_db` trước; ghi manifest `JD_SEED_MANIFEST_PATH` (`jd_id`, id posting, id Employer, `synthetic`); `clean()` xóa `job_skills` + `job_postings` của Employer seed rồi `company_profiles` + `users` có email miền `seed.ai-recruit.test`, không đụng dữ liệu khác. Tách hàm thuần `posting_row(jd, employer_id, level_id)` để test offline; giữ < 200 dòng
- [x] T046 [US4] (2026-10-28 xong) `tests/test_job_db_seed_writer.py` (hàm thuần): thứ tự ghép `description`, lương chữ → `None`, `deadline` dự phòng, email Employer đúng dạng slug công ty và thuộc miền seed
- [x] T047 [US4] (2026-10-28 xong) Tạo `pipeline/jd_seed_command.py` + đăng ký lệnh `seed-jobs [--count 200] [--clean]` trong `pipeline/__main__.py` (hoặc `jd_cli.py`): preflight → chọn → ghi → manifest; mã thoát 0 · 1 thiếu JD đủ điều kiện · 2 preflight lỗi / thiếu `USER_DB_URL`, `JOB_DB_URL`
- [ ] T048 [US4] Chạy quickstart §5 trên Postgres local đã migrate: ≥ 200 posting đạt FR-022; chạy lại 0 posting mới; Employer seed không đăng nhập được; tìm kiếm của 007 trả kết quả cho "NodeJS", "React", "DevOps", "Senior", "Hà Nội" (SC-005); `--clean` chỉ xóa dữ liệu seed; mở PR `jd-seed`

**Checkpoint**: `job_db` có 200 posting thật cho demo "full job lifecycle"

---

## Phase 7: User Story 3 - Index chunk JD (Priority: P3 — Stretch, ngoài Sprint 2) · S2-DE-3

**Goal**: chỉ làm khi AIE cần JD trong truy hồi (Clarifications NC-2); chunk của US2 đã sẵn

- [ ] T049 [US3] (Stretch) Lệnh `index-jd`: ghi `JD_CHUNKS_PATH` qua đường ghi của 005 (`pipeline/knowledge_chunk_writer.py`, `embedding_client.py`) với `source_type = job_description`, `dataset` riêng cho JD, `category` theo nhóm kỹ năng chính (không xác định → trống), `topic_id` / `difficulty` trống (FR-015); idempotent, JD bị loại thì gỡ chunk, phạm vi dọn giới hạn trong `dataset` JD, MUST NOT đụng `interview_qa` / `textbook` (FR-016); in thống kê FR-017
- [ ] T050 [US3] (Stretch) Test offline cho kế hoạch ghi (theo mẫu `tests/test_knowledge_chunk_writer_plan.py`) + kiểm SC-004 trên `ai_db`

---

## Phase 8: Polish & Cross-Cutting

- [x] T051 [P] (2026-10-28: mọi file `crawlers/`, `pipeline/` < 200 dòng, lớn nhất `crawlers/jd_page_parser.py` 173) Kiểm mọi file mới/sửa trong `crawlers/` và `pipeline/` < 200 dòng (constitution VII); quá thì tách module
- [ ] T052 [P] Cập nhật dòng 009 trong `specs/README.md` mỗi khi một PR merge (jd-crawl, jd-process, jd-synthetic, jd-seed)
- [x] T053 (2026-10-28: `git status` data rỗng; 12 fixture JD tự soạn, ≤ 1,9 KB, công ty giả) Chạy quickstart §6: `git status --porcelain apps/data-pipeline/data/raw apps/data-pipeline/data/processed` rỗng; `git ls-files apps/data-pipeline/tests/fixtures/jd` chỉ có file tự soạn (SC-003)
- [ ] T054 `python -m pytest` + job `python` của CI xanh trước mỗi PR (constitution VI)
- [ ] T055 [P] Chia sẻ riêng `data/processed/jd_normalized.jsonl` cho FSD nếu FSD cần dữ liệu trước khi có US4 (research R11, plan Rủi ro); không đưa vào git hay kênh công khai

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** → **Foundational (Phase 2)** → các story
- **US1 (Phase 3)**: sau Phase 2
- **US2 (Phase 4)**: cần raw từ US1 cho T029 (quickstart thật); code + test T017–T028 viết song song với US1 được vì dùng fixture
- **US5 (Phase 5)**: cần báo cáo `process-jd` trên dữ liệu crawl thật (T029)
- **US4 (Phase 6)**: P1 nhưng chờ migration 004 + 007 trên `main` (T038) và quyết định T039; dùng JD crawl, synthetic chỉ lấp phần thiếu, nên chạy sau US5 khi crawl không đủ. T040–T044, T046 viết trước được (không cần DB)
- **US3 (Phase 7)**: Stretch, chỉ khi AIE yêu cầu
- **Polish (Phase 8)**: T051, T053, T054 trước mỗi PR; T052 sau mỗi merge

### Within Each Story

- Fixture + module thuần trước, command sau, đăng ký CLI sau command, quickstart thật cuối cùng
- Mọi task sửa `pipeline/__main__.py` (T013, T027, T035, T047) chạy tuần tự

### Parallel Opportunities

- Phase 3: T006, T007, T008, T009, T010 song song (khác file); T011 → T012 → T013 → T014 tuần tự
- Phase 4: T017–T023 song song; T024 → T026 → T027 → T028
- Phase 5: T030–T033 song song; T034 → T035 → T036
- Phase 6: T040–T044 song song (sau T038); T045 sau T039

## Parallel Example: User Story 2

```text
T017 data/seeds/skill_dictionary.yaml
T018 pipeline/skill_dictionary.py         + T019 tests/test_skill_dictionary.py
T020 pipeline/jd_normalizer.py            + T021 tests/test_jd_normalizer.py
T022 pipeline/jd_sections.py              + T023 tests/test_jd_sections.py
→ sau đó T024 jd_record_builder.py → T026 jd_process_command.py
```

## Implementation Strategy

### MVP (US1 + US2)

1. Phase 1–2 → Phase 3 (US1): crawl thật, raw 0 PII
2. Phase 4 (US2): JD chuẩn hóa + báo cáo phân bố → đủ cho phần "JD data đã xử lý" của demo Sprint 2
3. **Dừng và kiểm**: quickstart §1–§3

### Incremental Delivery

1. PR `jd-crawl` (US1) → PR `jd-process` (US2) → PR `jd-synthetic` (US5, ≥ 500 JD) → PR `jd-seed` (US4, khi có migration)
2. Kiểm tiến độ thứ Năm 05/11. Trễ thì cắt theo plan: giảm nguồn crawl (giữ itviec + careerviet) → synthetic bù nhiều hơn → US4 sang S3 nếu 007 chưa có migration

## Notes

- Không commit nội dung crawl; fixture là HTML tự soạn mô phỏng cấu trúc `JobPosting` (FR-007)
- Không đăng nhập, không né chặn; site chặn thì nguồn dừng với mã 4 (FR-004)
- Commit theo conventional commits, mỗi task hoặc nhóm task liên quan một commit
