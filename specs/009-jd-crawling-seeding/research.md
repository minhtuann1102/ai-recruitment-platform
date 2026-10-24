# Research: JD Crawling & Seeding

Phase 0 của [plan.md](plan.md). Dữ liệu đo tại "Kiểm tra nguồn bổ sung (2026-10-24)" trong [spec.md](spec.md); không gửi
thêm request nghiên cứu, lần crawl thật đầu tiên với `--max-pages` nhỏ sẽ đo sản lượng.

## R1. Nguồn và cách tìm JD

- **Decision**: 4 nguồn itviec, topdev, careerviet, careerlink. Mỗi nguồn: trang danh sách IT phân trang → link chi tiết
  (regex theo nguồn) → trang chi tiết → khối JSON-LD `JobPosting`. Cấu hình nguồn (URL danh sách, tham số trang, regex
  link, id JD) nằm ở một module, thêm nguồn không sửa code crawl.
- **Rationale**: cả 4 nguồn trả HTML tĩnh có `JobPosting` (schema.org) nên dùng chung một parser; trang danh sách cho
  ~15–50 link/trang, đủ để vượt 500 JD trước khi cần synthetic.
- **Alternatives considered**: sitemap (itviec, careerviet có) — nhiều URL hết hạn, khó lọc IT, bỏ; vietnamworks — danh
  sách render phía client, cần JS (FR-005) hoặc đọc `__NEXT_DATA__`, để sau nếu thiếu JD; joboko — mục IT lẫn 8/10 việc
  ngoài IT, bỏ; topcv, jobsgo — 403, loại.

## R2. Trường lấy từ `JobPosting` và chỗ khác nhau giữa nguồn

| Trường raw | JSON-LD | Ghi chú theo nguồn |
|---|---|---|
| `title`, `company` | `title`, `hiringOrganization.name` | đủ ở cả 4 |
| `skills_raw` | `skills` | itviec, topdev, careerviet có; **careerlink không có** → trích từ mô tả bằng danh mục (R5) |
| `description_text` | `description` (HTML) | topdev: JSON-LD chỉ ~180 ký tự → lấy thân mô tả từ HTML trang (selector theo nguồn) |
| `location_raw` | `jobLocation[].address` | thành phố ở `addressRegion` / `addressLocality` |
| `experience_raw` | `experienceRequirements` | dạng số tháng hoặc chữ, khác nhau theo nguồn |
| `employment_type_raw` | `employmentType`, `jobLocationType` | `TELECOMMUTE` → remote |
| `salary_raw` | `baseSalary` | itviec: chữ thay số (ẩn sau đăng nhập) → trống; careerviet: số VND `minValue`/`maxValue`; topdev, careerlink: chữ hoặc "thỏa thuận" |
| `date_posted`, `valid_through` | cùng tên | |

`JobPosting` có thể nằm trong mảng hoặc `@graph`; parser duyệt cả hai, bỏ khối JSON lỗi thay vì dừng.

## R3. Lịch sự khi crawl (FR-003, FR-004)

- **Decision**: dùng lại `crawlers/polite_fetcher.py` (005). Bổ sung: dừng nguồn sau **3 phản hồi 403/429 liên tiếp**
  (hoặc trang thử thách chống bot), mặc định `--delay 2`, giới hạn `--max-pages` cho trang danh sách và trang chi tiết.
  Robots đọc lại ở đầu mỗi lần chạy (fetcher tạo mới mỗi lần chạy).
- **Rationale**: fetcher hiện có đã đọc robots, nghỉ giữa request, giới hạn trang, nhưng chưa dừng khi bị chặn, trong
  khi FR-004 bắt buộc dừng.
- **robots có 2 nhóm `*`** (itviec): `urllib.robotparser` giữ nhóm `*` **đầu tiên** làm mặc định (`Disallow:
  /subscriptions/new`), tức là cách hiểu chặt hơn như FR-003 yêu cầu. Thêm test để giữ hành vi này.
- **Alternatives considered**: Scrapy (AutoThrottle, robots có sẵn) — thêm framework cho 4 nguồn HTML tĩnh, không cần
  (constitution VII); Playwright — không nguồn nào được dùng cần JS.

## R4. Lưu raw, idempotent khi crawl (FR-006, FR-007, FR-009)

- **Decision**: `data/raw/jd/<nguồn>/<UTC timestamp>.jsonl`, khóa `(source, source_job_id)`. Trước khi tải trang chi
  tiết, đọc các file raw cũ của nguồn và **bỏ qua id đã có** (không request lại). Scrub PII ngay trước khi ghi raw, phạm
  vi đủ FR-009: (1) email + số điện thoại (`pii_patterns.py` của 005); (2) **dòng liên hệ**: dòng bắt đầu bằng "Liên
  hệ", "Contact", "Người liên hệ", "Hotline", hoặc "Mr./Ms./Mrs./Anh/Chị/A./C. + tên" đi kèm số điện thoại hay email →
  bỏ cả dòng; (3) **URL hồ sơ cá nhân**: `linkedin.com/in/`, `facebook.com/`, `fb.com/`, `zalo.me/`, `t.me/`. Bộ kiểm
  `pii_remaining` đếm cả ba loại trên output; > 0 → lệnh thất bại. Thư mục raw đã nằm trong `.gitignore` (005).
- **Rationale**: chạy lại không tạo trùng và không gửi request thừa; FR-009 đòi xóa PII trước mọi output, kể cả raw.
- **Alternatives considered**: lưu HTML gốc để parse lại — tăng dung lượng và chứa PII, bỏ.

## R5. Danh mục kỹ năng (FR-010)

- **Decision**: `data/seeds/skill_dictionary.yaml` commit (danh mục tự soạn, không phải nội dung crawl): mỗi kỹ năng có
  `slug`, `name`, `category` (giá trị cột `skills.category` của `job_db`), `group` (một trong 5 nhóm FR-022), `aliases`.
  Bắt đầu ~100 kỹ năng, bổ sung theo danh sách "ngoài danh mục" của báo cáo. Khớp: `skills_raw` qua bảng bí danh; với
  tiêu đề + mô tả, khớp theo ranh giới từ, không phân biệt hoa thường (`ReactJS`, `React.js`, `react` → `react`).
- **Rationale**: một nguồn sự thật cho chuẩn hóa, cho lọc IT (R7) và cho lưới synthetic (R9). Đề xuất FSD dùng file này
  làm seed ~50 skills của S2-FSD-1 để `job_db.skills` không lệch danh mục (NC-1).
- **Alternatives considered**: LLM trích kỹ năng — tốn tiền, không deterministic (FR-014 cần chạy không key), bỏ.

## R6. Chuẩn hóa cấp bậc, loại hình, thành phố, lương, ngôn ngữ (FR-011)

- **Cấp bậc** (`Intern | Junior | Mid | Senior | Lead | Manager`, theo S2-FSD-2): từ khóa trong tiêu đề trước (Intern,
  Thực tập, Fresher → Junior, Junior, Middle/Mid, Senior, Lead/Trưởng nhóm, Manager/Quản lý); không có thì theo số năm
  kinh nghiệm (< 1 Intern, 1–2 Junior, 3–4 Mid, ≥ 5 Senior); không suy ra được → trống, báo cáo.
- **Loại hình**: `TELECOMMUTE` hoặc từ khóa remote / từ xa → `remote`; hybrid → `hybrid`; còn lại `onsite`.
- **Thành phố**: bảng tên chuẩn (Hà Nội, Hồ Chí Minh, Đà Nẵng, …) + bí danh (`Ho Chi Minh`, `HCM`, `TP.HCM`, `Hanoi`);
  nhiều địa điểm → lấy địa điểm đầu.
- **Lương**: chỉ nhận số thật: số trong `baseSalary` hoặc chuỗi dạng "9.000.000 VND - 20.000.000 VND" / "15 - 25
  triệu" / "$1,000 - 2,000"; chữ ("thỏa thuận", "You'll love it", "Sign in to view") → trống (FR-018).
- **Ngôn ngữ**: tỉ lệ ký tự có dấu tiếng Việt → `vi | en | mixed`.

## R7. Lọc JD ngoài IT, section, dedup (FR-012, FR-013, FR-028)

- **Lọc IT**: giữ JD khi tiêu đề khớp ≥ 1 kỹ năng hoặc từ khóa nghề IT (developer, engineer, lập trình, tester, QA,
  DevOps, data, …) hoặc mô tả khớp ≥ 2 kỹ năng; còn lại loại với lý do `not_it`, đếm theo nguồn.
- **Section**: nhận tiêu đề section Việt/Anh (Mô tả công việc / Job description, Yêu cầu / Requirements / Your skills,
  Trách nhiệm / Responsibilities, Quyền lợi / Benefits / Why you'll love working here); không nhận ra → `description`.
  Section là đầu vào cột `description` / `requirements` của posting; chunk (FR-012) sinh offline cùng bước, chưa index.
- **Dedup**: hash SHA-256 của `công ty | tiêu đề | mô tả` sau NFC, chữ thường, gộp khoảng trắng; trùng → giữ bản nhiều
  trường hơn. Cùng (công ty, tiêu đề) nhưng khác hash → chỉ cảnh báo trùng gần đúng.

## R8. Báo cáo phân bố (đầu vào US5)

`process-jd` in và ghi `data/processed/jd-report-<timestamp>.json`: JD vào / ra theo nguồn, bị loại theo lý do, trùng,
phân bố theo nhóm kỹ năng / cấp bậc / thành phố / loại hình, tỉ lệ JD có ≥ 1 kỹ năng (riêng JD crawl), kỹ năng ngoài
danh mục (top 50), tỉ lệ crawl / synthetic.

## R9. JD synthetic (FR-023–FR-027)

- **Decision**: lưới ô = nhóm kỹ năng (5) × cấp bậc (6) × thành phố (Hà Nội, Hồ Chí Minh, Đà Nẵng) = 90 ô. Số JD
  synthetic **không** chia đều cho 90 ô (sẽ sinh cả khi crawl đã đủ, trái SC-008). Công thức:
  1. **Bù số lượng**: `need_total = max(0, 500 - jd_hợp_lệ)`; phân cho các ô theo thứ tự ít JD nhất trước (hòa → theo
     thứ tự cố định group, level, city), mỗi lượt +1 JD cho một ô, tới khi hết `need_total`.
  2. **Bù sàn đa dạng** (FR-022), tính trên số đã cộng bước 1: mỗi nhóm kỹ năng (5), mỗi cấp Junior / Mid / Senior, mỗi
     thành phố (3) cần ≥ `sàn` JD hợp lệ (mặc định 20, đủ để chọn 200 posting đa dạng); giá trị nào thiếu thì sinh phần
     thiếu vào ô ít JD nhất thuộc giá trị đó.
  Crawl đủ 500 và đủ sàn → 0 JD synthetic. Mỗi JD synthetic: code chọn kỹ
  năng từ danh mục của nhóm và tên công ty hư cấu (ghép từ danh sách từ cố định, kiểm không trùng tên công ty crawl);
  LLM chỉ viết tiêu đề + các section theo tham số đó, trả JSON. Code hậu kiểm: kỹ năng thuộc danh mục, 0 PII, 0 URL,
  đủ section. Id `syn-<group>-<level>-<city>-<n>` → chạy lại bỏ qua id đã có.
- **LLM**: dùng `LlmSettings` + client OpenAI-compatible của 005 (`LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, mặc định
  `openai/gpt-4o-mini`); retry giới hạn; `--limit` mỗi lần chạy.
- **Chi phí**: ~600 token vào + ~900 token ra / JD; 300 JD ≈ 0,2 USD với gpt-4o-mini (SC-008 < 1 USD).
- **Rationale**: sinh từ tham số ô, không từ nội dung crawl (FR-024), nên không "rửa" nội dung bị hạn chế và bù đúng chỗ
  thiếu.
- **Alternatives considered**: viết lại JD crawl — vi phạm FR-024; template không LLM — JD giống nhau, demo kém; dataset
  JD công khai — license từng bộ phải kiểm, đa số tiếng Anh/nước ngoài.

## R10. Seed `job_db` (US4, chờ NC-1)

- **Decision (đề xuất gửi FSD)**: phương án (b) của NC-1: viết mapping theo `data-model.md` §2, chạy preflight đọc
  `information_schema` của `job_db` và **dừng** khi thiếu bảng/cột (FR-019); ghi bằng `psycopg` qua `JOB_DB_URL`, một
  transaction. Cần FSD chốt: (1) cột đánh dấu seed + khóa idempotent + cờ synthetic (vd `source`, `source_ref`,
  `is_synthetic` trong migration 007) hay quy ước khác; (2) `employer_id` cho posting seed; (3) chỗ lưu tên công ty
  (`company_profiles` ở `user_db`); (4) `status` mặc định; (5) danh mục kỹ năng R5 làm seed `skills`.
- **Rationale**: constitution I cho phép script seed ghi DB khác khi bám đúng schema migration; preflight giữ an toàn khi
  007 đổi schema.
- **Alternatives considered**: seed qua API/TCP job-service — đúng ranh giới service hơn nhưng phụ thuộc job-service
  chạy + auth Employer, chưa có trên `main`; FSD có thể chọn ở NC-1.

## R11. Dữ liệu và chia sẻ

Raw / processed chỉ ở máy DE (gitignore), chia sẻ riêng như dump 005; không công bố lại. `skill_dictionary.yaml` và
fixture test (HTML tự soạn mô phỏng cấu trúc `JobPosting`, không chép JD thật) là thứ duy nhất được commit (FR-007).
