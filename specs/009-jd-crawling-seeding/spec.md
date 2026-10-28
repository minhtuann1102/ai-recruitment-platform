# Feature Specification: JD Crawling & Seeding

**Feature Branch**: `docs/jd-crawling-seeding-spec` (spec), `docs/jd-crawling-seeding-plan` (clarify + plan); branch
code đặt ở plan (theo `docs/conventions.md`; thư mục spec độc lập với branch)

**Created**: 2026-10-23

**Status**: Clarified 2026-10-24 — NC-1, NC-2, NC-3 đã chốt; US4 chờ migration `company_profiles` (004) và job-service (007)

**Owner**: DE — **Sprint**: 2 (26/10 → 09/11/2026)

**Covers**: S2-DE-1, S2-DE-2, S2-DE-3, S2-DE-4

**Input**: User description: "Feature 009 jd-crawling-seeding (S2-DE-1..4, owner DE): crawl 500+ JD IT từ topcv.vn,
itviec.com (title, company, skills, description); clean, extract skills, chunk theo section; index JD chunks vào ai_db
source_type=job_description; seed 200 job postings vào job_db từ JD crawl. Tôn trọng robots.txt, rate limit, xóa PII,
không commit nội dung crawl."

**Nguồn thiết kế**: [`docs/architecture/data-pipeline.md`](../../docs/architecture/data-pipeline.md) §5, §10, §11;
[`rag-design.md`](../../docs/architecture/rag-design.md) §3 (schema `knowledge_chunks`);
[`data-model.md`](../../docs/architecture/data-model.md) §2 (`job_db`, bản thiết kế, chưa có migration);
pipeline ghi của [spec 005](../005-rag-knowledge-base-qa/spec.md) (FR-006–FR-016, FR-022–FR-025). Spec chỉ ghi phần
mới hoặc khác.

## Kiểm tra nguồn crawl (2026-10-23)

Kiểm tra bằng HTTP từ môi trường cloud (IP datacenter) và WebFetch. Kết quả là ảnh chụp tại ngày kiểm tra; plan MUST
kiểm tra lại robots.txt ngay trước lần crawl thật (FR-003).

### itviec.com

- **robots.txt** (`https://itviec.com/robots.txt`): hai nhóm `User-Agent: *`; nhóm 1 `Disallow: /subscriptions/new`,
  nhóm 2 `Allow: /`. Không có `Crawl-delay`. Sitemap: `https://itviec.com/dunggiatminh.xml` (sitemap index, truy cập
  được).
  - **Được phép**: `/it-jobs` (trang danh sách, phân trang `?page=N`, lúc kiểm tra tới `page=33`),
    `/it-jobs/<slug>-<id>` (trang chi tiết), sitemap.
  - **Bị cấm**: `/subscriptions/new`. Hai nhóm `*` trùng nhau có thể bị parser hiểu khác nhau → crawler MUST áp dụng
    cách hiểu chặt hơn (giữ `Disallow`).
- **Có cần render JavaScript không**: **Không** cho dữ liệu cần lấy. Trang danh sách trả HTML tĩnh (HTTP 200, có
  slug job trong HTML). Trang chi tiết có khối JSON-LD `JobPosting` trong HTML tĩnh với `title`, `hiringOrganization`,
  `skills`, `description` (~8.500 ký tự ở mẫu), `datePosted`, `validThrough`, `employmentType`,
  `experienceRequirements`, `jobLocation`, `baseSalary`, `jobBenefits`. Lương hiển thị "Sign in to view salary" /
  `baseSalary.value` không phải số → không lấy được lương thật khi không đăng nhập (crawler MUST NOT đăng nhập).
- **Điều khoản** (`https://itviec.com/blog/terms-and-conditions/`, hiệu lực 01/07/2023, cập nhật 08/12/2025) mục 2.2:
  *"Other than insofar as necessary for reasonable personal use of the website, its content may not be retrieved,
  displayed, modified, copied, printed, sold, downloaded, ... or transmitted in any way without our prior written
  consent."* Không có điều khoản riêng về bot/crawl, nhưng 2.2 hạn chế sao chép nội dung ngoài mục đích cá nhân khi
  chưa có đồng ý bằng văn bản. → Rủi ro điều khoản, xem NC-3.

### topcv.vn

- **robots.txt** (`https://www.topcv.vn/robots.txt`, đọc được): một nhóm `User-agent: *`, không có `Allow`, không có
  `Crawl-delay`. Sitemap: `https://www.topcv.vn/sitemap.xml`.
  - **Bị cấm**: `/cv/get-private-url/`, `/private/`, `/xem-cv/`, `/xem-cv-draft/`, `/sua-cv/`, `/viet-cv/`,
    `/edit/cv/`, `/cv-ung-vien/`, `/cv-ung-tuyen/`, `/p/`, `/v4/image/cv-template/cv-sample/toppy-list-mau-cv.png`.
  - **Không cấm theo robots.txt**: trang danh sách (`/tim-viec-lam-it`), trang chi tiết (`/viec-lam/<slug>/<id>.html`).
- **Truy cập thực tế**: mọi trang ngoài robots.txt (trang chủ, `/tim-viec-lam-it`, `sitemap.xml`, trang điều khoản)
  trả **HTTP 403 "Attention Required! | Cloudflare — Sorry, you have been blocked"** từ cả curl lẫn WebFetch. Robots
  cho phép không có nghĩa là site cho phép bot: site đang chặn truy cập tự động bằng tường bảo vệ.
- **Có cần render JavaScript không**: **chưa xác định** — không tải được trang nào ngoài robots.txt. Vượt qua thử
  thách Cloudflare (headless browser giả người dùng, đổi IP, giải captcha) là né cơ chế chặn của site → MUST NOT làm
  (FR-004).
- **Điều khoản** (`https://topcv.vn/terms-of-service`, theo kết quả tìm kiếm cập nhật 01/04/2025): **không đọc được**
  (403). Trang "Điều kiện giao dịch chung" theo kết quả tìm kiếm cấm "truy cập trái phép, sử dụng sai mục đích". Chưa
  xác nhận có điều khoản riêng về crawl.

## Kiểm tra nguồn bổ sung (2026-10-24, IP cá nhân)

Kiểm tra từ máy DE (IP dân dụng) bằng httpx, User-Agent của pipeline, nghỉ 3 giây giữa request, mỗi site 1 trang danh
sách + 1–2 trang chi tiết; chỉ ghi nhận cấu trúc, không lưu nội dung. Điều khoản từng site chưa đọc (rủi ro điều khoản
DE đã chấp nhận, xem Clarifications).

| Site | robots.txt (trang job) | Truy cập | JSON-LD `JobPosting` | `skills` | Lương công khai | Kết luận |
|---|---|---|---|---|---|---|
| itviec.com | Cho phép | 200 | Có | Có | Không (ẩn sau đăng nhập) | Dùng |
| topdev.vn | Cho phép | 200 | Có (`description` ~180 ký tự, mô tả đầy đủ nằm trong HTML) | Có | Có trường, mẫu ghi "thỏa thuận" | Dùng |
| careerviet.vn | Cho phép | 200 | Có | Có | Có, số VND min/max | Dùng |
| careerlink.vn | Cho phép | 200 | Có | Không | Có trường | Dùng |
| vn.joboko.com | Cho phép | 200 | Có | Không | Có, dạng chữ "9.000.000 VND - 20.000.000 VND" | Không dùng: mục "IT phần mềm" lẫn đa số việc ngoài IT (8/10 mẫu) |
| vietnamworks.com | Cho phép | 200 | Danh sách render phía client (Next.js) | — | — | Không dùng ở S2 (cần render JS; FR-005) |
| jobsgo.vn | Cho phép | **403** | — | — | — | Loại (site chặn) |
| topcv.vn | Cho phép | **403 cả từ IP cá nhân** | — | — | — | Loại (site chặn) |
| facebook.com (group) | `User-agent: *` → `Disallow: /` + thông báo cấm thu thập tự động | — | — | — | — | Loại |

## Clarifications

### Session 2026-10-24

- Q: NC-2 — S2-DE-3 "Index JD vào ai_db" còn Bắt buộc không? → A: **Không. Hạ xuống Stretch, ngoài phạm vi Sprint 2.**
  JD đi đường JD Parser → `jd_profile` → Planner (S2-AIE-6, AIE đồng ý 2026-10-15), không qua RAG; ai-service chỉ truy
  hồi `interview_qa` và `textbook` (`apps/ai-service/app/rag/models.py`, `source_types`); `rag-design.md` §3 ghi
  `job_description` là Stretch. Quality Gate S2 1500 chunk đã đạt bằng `interview_qa` (9.006 chunk trên ai_db dùng chung,
  2026-10-23). US3, FR-015–FR-017, SC-004 giữ lại làm Stretch. DE chốt.
- Q: NC-3 — nguồn JD và mục tiêu số lượng? → A: **Crawl tối đa từ các site tuyển dụng IT cho phép (bảng "Kiểm tra nguồn
  bổ sung": itviec, topdev, careerviet, careerlink), phần thiếu bù bằng JD synthetic.** Giữ mục tiêu ≥ 500 JD hợp lệ và
  200 posting seed. DE chấp nhận rủi ro điều khoản (itviec §2.2) cho mục đích học thuật nội bộ, không công bố lại nội
  dung; theo DE, giảng viên không yêu cầu nguồn cụ thể. Ràng buộc an toàn giữ nguyên: robots.txt, giới hạn tốc độ, không
  đăng nhập, không né chặn (topcv, jobsgo, Facebook loại), xóa PII, không commit nội dung crawl. JD synthetic sinh
  **sau** khi crawl + xử lý, theo báo cáo phân bố, để lấp phần thiếu (FR-023–FR-027). DE chốt.
- Q: NC-1 — seed `job_db` bám schema nào, công ty / `employer_id` / dấu seed lấy từ đâu? → A: **Bám contract đã có**
  ([`data-model.md`](../../docs/architecture/data-model.md) §1 `users` + `company_profiles`, §2 `job_db`), không cần FSD
  thêm cột. Theo contract, công ty của posting là `company_profiles` của Employer sở hữu → seed tạo một **Employer seed**
  + `company_profiles` cho mỗi công ty (theo schema migration của user-service), posting gắn `employer_id` đó (FR-021).
  Dọn / idempotent qua Employer seed (FR-020); cờ synthetic giữ ở manifest ngoài git (FR-026); `status = open`; kỹ năng
  khớp `skills.slug`, thiếu thì thêm từ danh mục (FR-010). Chỉ còn chờ migration có trên `main`: `company_profiles`
  (user-service, 004) và job-service (007) — không phải quyết định cần chốt. DE chốt.

### Session 2026-10-28

Sau review `jd-process` và chạy `process-jd` trên 515 JD crawl thật (2026-10-27/28). DE chốt cả mục dưới.

- Q: Cấp bậc khi tiêu đề không ghi cấp (FR-011, R6)? → A: **Dưới 12 tháng kinh nghiệm = fresher → `Junior`; `Intern`
  chỉ suy từ tiêu đề (intern / thực tập / trainee).** Riêng itviec, `experience_raw` không phải số năm thật (chỉ có 4
  giá trị "10 months", "37 months", "61 months", "No requirements" do itviec tự gán; 67 JD "10 months" có tiêu đề
  Middle/Senior/Architect và mô tả ghi 1–5 năm) nên bỏ qua. Nguồn nào không có số năm dùng được thì lấy số năm đầu tiên
  đi kèm "kinh nghiệm" / "experience" trong mô tả (bỏ số > 10 năm, thường là tuổi công ty); không có thì `null`.
- Q: Phạm vi lọc IT (FR-028)? → A: **Mở rộng từ khóa và tính thẻ kỹ năng; loại vai trò ngoài 5 nhóm.** Thêm "IT" (viết
  hoa), kỹ sư phần mềm / hệ thống / mạng / dữ liệu, security / an toàn thông tin / an ninh mạng, pentest, QA/QC /
  kiểm thử, vận hành / quản trị hệ thống, network administrator, DBA. JD có ≥ 1 thẻ `skills_raw` thuộc danh mục cũng là
  IT. Kỹ năng chung chung (cơ sở dữ liệu, bảo mật thông tin, network, cloud, QA/QC, IT support, hạ tầng) vẫn ghi vào
  `skills` nhưng không tự làm JD thành IT (hay gặp ở JD ngân hàng / sản xuất / kinh doanh). Tiêu đề bán hàng / tư vấn
  (tiếng Việt) / presale, giảng dạy, hành chính, phiên dịch / comtor, kiểm toán viên, field service → `not_it` dù có từ
  khóa IT (so trên tiêu đề đã bỏ dấu); "consultant" tiếng Anh không loại vì phần lớn là vai trò kỹ thuật. **BA, PO,
  PM, Scrum Master** → `not_it` ở bản này (không thuộc 5 nhóm, AIE chưa có hướng phỏng vấn); dữ liệu thô vẫn giữ, bổ
  sung sau chỉ cần chạy lại `process-jd`. Data Engineer (nhóm `ai_data`) và QA/QC (nhóm `devops`, theo danh mục) là IT.
- Q: Thành phố khi nguồn chỉ ghi quận (careerviet "Quận Cầu Giấy", "Quận 3")? → A: **Sửa ở chuẩn hóa, không crawl
  lại.** Thứ tự: tên thành phố trong `location_raw` → dòng "Địa điểm:" / "Nơi làm việc:" / "Location:" của mô tả →
  bảng quận/huyện → thành phố (chỉ quận thuộc riêng Hà Nội, Hồ Chí Minh, Đà Nẵng).
- Q: Nhóm kỹ năng của JD (FR-010)? → A: **Kỹ năng trong tiêu đề quyết định nhóm** (hòa thì xét toàn JD); tiêu đề không
  có kỹ năng thì lấy nhóm xuất hiện nhiều nhất của toàn JD như cũ. Lý do: "Angular Developer" có mô tả nhắc AWS/Nginx
  bị xếp `devops`.
- Q: Danh mục kỹ năng (R5)? → A: Bí danh gộp nhầm sản phẩm khác nhau được tách thành kỹ năng riêng (vite ≠ webpack,
  grafana ≠ prometheus, jest/junit/pytest ≠ unit-testing, rag/genai ≠ llm, tableau/looker ≠ power-bi, ...); thêm kỹ năng
  hạ tầng / bảo mật / kiểm thử / dữ liệu (IT support, information security, software testing, cloud, data engineering,
  ...). "TS" và "ai" chỉ nhận khi là thẻ (TS. = tiến sĩ, "ai" = who); "học máy" trong "Khoa học máy tính" không tính là
  machine learning.
- Q: Mô tả quá ngắn? → A: Giữ luật của bản cài đặt: mô tả sau làm sạch < 200 ký tự → `missing_field` (topdev có tin
  ~180 ký tự). DE chấp nhận.

## User Scenarios & Testing *(mandatory)*

Người dùng trực tiếp: **DE** (vận hành crawl, xử lý, index, seed), **FSD** (cần `job_db` có dữ liệu thật để demo tìm
kiếm/lọc/ứng tuyển ở 007/008 và frontend 013), **AIE** (JD của job đã seed là đầu vào JD Parser khi luyện tập theo
job; không cần index). Người dùng cuối hưởng lợi gián tiếp: danh sách việc làm demo trông thật, đa dạng kỹ năng/cấp
bậc/địa điểm. Hội đồng demo Sprint 2 cần thấy: JD data đã xử lý + seed và full job lifecycle trên dữ liệu thật.

### User Story 1 - Crawl JD IT có kiểm soát (Priority: P1) · S2-DE-1

DE chạy một lệnh crawl các nguồn đã duyệt (theo NC-3), thu về ≥ mục tiêu JD thô với các trường: tiêu đề, công ty, kỹ
năng, mô tả (yêu cầu, trách nhiệm, quyền lợi), địa điểm, cấp bậc/kinh nghiệm, loại hình, khoảng lương (nếu công khai),
ngày đăng/hạn, URL nguồn, thời điểm crawl. Dữ liệu thô lưu ngoài git.

**Why this priority**: Mọi story khác dùng output này. Có thể tái dùng bộ crawler của 005 (US5).

**Independent Test**: Chạy crawler với giới hạn nhỏ (vd 2 trang) → nhận file thô, log cho thấy robots.txt được đọc,
khoảng cách request ≥ cấu hình, 0 truy cập đường dẫn bị cấm, 0 email/số điện thoại trong output.

**Acceptance Scenarios**:

1. **Given** nguồn đã duyệt và giới hạn N trang, **When** chạy crawl, **Then** lưu record thô kèm URL + thời điểm
   crawl, không vượt N trang, in thống kê (trang đã tải, record, lỗi, bị bỏ qua theo robots).
2. **Given** URL thuộc danh sách `Disallow` (vd `/subscriptions/new`, `/cv-ung-vien/`), **When** crawler gặp,
   **Then** bỏ qua và ghi log, không gửi request.
3. **Given** site trả 403/429/thử thách chống bot, **When** crawl, **Then** dừng nguồn đó (backoff, không retry vô hạn,
   không né cơ chế chặn) và báo rõ trong thống kê.
4. **Given** chạy lại khi đã có dữ liệu thô, **When** crawl, **Then** không tạo record trùng cho cùng JD (khóa theo
   nguồn + id JD của nguồn).
5. **Given** cấu trúc HTML/khối dữ liệu có cấu trúc của nguồn đổi làm 0 record hoặc thiếu trường bắt buộc hàng loạt,
   **When** crawl, **Then** lệnh báo lỗi, không lặng lẽ thành công.

---

### User Story 2 - Xử lý JD: clean, trích kỹ năng, chunk theo section (Priority: P1) · S2-DE-2

DE chạy bước xử lý offline biến JD thô thành JD chuẩn hóa (trường sạch, kỹ năng chuẩn hóa về danh mục, cấp bậc, địa
điểm, lương) và danh sách chunk theo section (tóm tắt, yêu cầu, trách nhiệm, quyền lợi). Không cần DB hay API key.

**Why this priority**: Đầu vào chung cho index (US3) và seed (US4).

**Independent Test**: Chạy chế độ chỉ xử lý trên file thô mẫu → nhận JD chuẩn hóa + chunk + báo cáo (JD vào/ra, bị
loại kèm lý do, trùng, phân bố kỹ năng/cấp bậc/địa điểm, tỉ lệ JD trích được ≥ 1 kỹ năng).

**Acceptance Scenarios**:

1. **Given** JD có HTML, khoảng trắng thừa, ký tự điều khiển, **When** xử lý, **Then** nội dung sạch, giữ dấu tiếng
   Việt và thuật ngữ tiếng Anh.
2. **Given** JD chứa email/số điện thoại/tên người liên hệ, **When** xử lý, **Then** các thông tin đó bị xóa trước khi
   ghi output.
3. **Given** JD có các tiêu đề section (Việt hoặc Anh), **When** chunk, **Then** mỗi section thành chunk riêng có nhãn
   section; JD không nhận ra section vẫn có chunk tóm tắt + chunk mô tả.
4. **Given** kỹ năng viết khác nhau (`ReactJS`, `React.js`, `react`), **When** chuẩn hóa, **Then** quy về cùng một kỹ
   năng; kỹ năng ngoài danh mục được báo, không mất.
5. **Given** cùng JD đăng lại (khác URL, nội dung trùng sau chuẩn hóa) hoặc chạy lại cùng input, **When** xử lý,
   **Then** chỉ giữ một bản; output deterministic.

---

### User Story 3 - Index chunk JD vào kho tri thức (Priority: P3 — Stretch, ngoài Sprint 2) · S2-DE-3

DE chạy pipeline đầy đủ: chunk JD được embed và ghi vào kho tri thức với nguồn `job_description`, dùng chung đường ghi
của 005. AIE truy hồi được đoạn JD theo truy vấn kỹ năng.

**Why this priority**: Stretch theo Clarifications 2026-10-24 (NC-2): AI không đọc JD từ RAG. Chỉ làm khi AIE cần JD
trong truy hồi; chunk của US2 đã sẵn nên index lại nhanh.

**Independent Test**: Hạ tầng local chạy + API key → index → đếm bản ghi `job_description` → chạy lại → không đổi → 3
truy vấn kỹ năng mẫu trả chunk JD liên quan.

**Acceptance Scenarios**:

1. **Given** kho rỗng phần JD, **When** index, **Then** số bản ghi `job_description` ≈ số chunk sau dedup, ≥ 99% có
   vector, thống kê in số embedding lỗi.
2. **Given** đã index, **When** chạy lại cùng input, **Then** 0 bản ghi mới, 0 lời gọi embed.
3. **Given** một JD bị loại khỏi tập dữ liệu (hết hạn, bị xóa), **When** chạy lại, **Then** chunk cũ của JD đó không
   còn truy hồi được; MUST NOT đụng bản ghi `interview_qa`/`textbook`.
4. **Given** thiếu API key hoặc kho chưa sẵn sàng, **When** index, **Then** dừng trước khi ghi, báo rõ nguyên nhân.

---

### User Story 4 - Seed 200 job posting vào job_db (Priority: P1 — chờ migration 004, 007) · S2-DE-4

DE chạy một lệnh lấy ≥ 200 JD chuẩn hóa, map sang job posting theo schema của job-service (007) và nạp vào `job_db`,
để FSD demo tìm kiếm, lọc, ứng tuyển trên dữ liệu thật.

**Why this priority**: Demo Sprint 2 "full job lifecycle" cần dữ liệu job; 013 và S4-DE-2 dùng lại.

**Independent Test**: DB sạch đã chạy migration job-service → seed → đếm posting, kiểm tra phân bố kỹ năng/cấp
bậc/địa điểm/loại hình → chạy lại → số posting không đổi → tìm kiếm full-text của 007 trả kết quả cho 5 từ khóa mẫu.

**Acceptance Scenarios**:

1. **Given** `job_db` đã migrate, rỗng, **When** seed, **Then** có ≥ 200 posting hợp lệ, mỗi posting gắn ≥ 1 kỹ năng
   và một cấp bậc, ràng buộc của schema đều thỏa.
2. **Given** đã seed, **When** chạy lại, **Then** không tạo posting trùng (khóa theo nguồn + id JD gốc).
3. **Given** schema `job_db` chưa có hoặc khác bản mapping, **When** seed, **Then** dừng trước khi ghi, báo bảng/cột
   thiếu; MUST NOT tạo/sửa bảng.
4. **Given** lương JD không công khai hoặc không phải số, **When** map, **Then** để trống trường lương (không bịa số).
5. **Given** cần dọn dữ liệu seed, **When** chạy lệnh dọn, **Then** chỉ xóa posting do seed tạo, không đụng posting do
   người dùng tạo.
6. **Given** đủ JD crawl cho 200 posting đạt FR-022, **When** seed, **Then** chọn JD crawl trước; JD synthetic chỉ lấp
   phần thiếu, mỗi posting synthetic có cờ phân biệt (FR-026).

---

### User Story 5 - Bù JD synthetic theo phần thiếu (Priority: P2) · S2-DE-1 (phần bù)

Sau khi crawl + xử lý, DE xem báo cáo phân bố (US2) và chạy một lệnh sinh JD synthetic để đạt mục tiêu số lượng và lấp
nhóm kỹ năng / cấp bậc / thành phố còn thiếu. JD synthetic đi qua cùng bước xử lý như JD crawl.

**Why this priority**: Các nguồn crawl có thể không đủ 500 JD hoặc lệch phân bố (vd ít AI/DevOps, ít Intern/Lead).
Không chặn US1, US2; chạy sau chúng.

**Independent Test**: Cho báo cáo phân bố mẫu thiếu nhóm AI và cấp Lead → sinh với giới hạn nhỏ (vd 10 JD) → JD ra
đúng ô thiếu, đều có cờ synthetic, tên công ty hư cấu, qua được bước xử lý; chạy lại cùng tham số → không sinh trùng.

**Acceptance Scenarios**:

1. **Given** báo cáo phân bố và mục tiêu, **When** sinh, **Then** chỉ sinh cho các ô (nhóm kỹ năng × cấp bậc × thành
   phố) còn thiếu, tổng không vượt phần thiếu so với mục tiêu, in số đã sinh theo ô.
2. **Given** JD synthetic, **When** xử lý (US2), **Then** qua cùng luật làm sạch, chuẩn hóa kỹ năng, dedup; JD hỏng
   schema bị loại kèm lý do.
3. **Given** thiếu API key LLM, **When** sinh, **Then** dừng trước khi gọi, báo rõ; US1, US2 vẫn chạy không cần key.
4. **Given** mọi JD synthetic, **When** kiểm tra, **Then** 0 tên công ty thật trong danh sách công ty của JD crawl, 0
   email/số điện thoại.

---

### Edge Cases

- **Site chặn bot** (topcv: Cloudflare 403 lúc kiểm tra): crawler dừng nguồn đó, báo lỗi; không đổi IP, không giả lập
  người dùng, không giải captcha.
- **robots.txt mơ hồ** (itviec có 2 nhóm `*` mâu thuẫn): áp dụng `Disallow` chặt hơn.
- **robots.txt đổi giữa các lần chạy**: đọc lại mỗi lần chạy, không cache qua ngày.
- **Lương ẩn sau đăng nhập** ("Sign in to view salary"): để trống; crawler MUST NOT đăng nhập.
- **JD tiếng Anh/Việt/trộn**: giữ nguyên ngôn ngữ gốc, gắn nhãn ngôn ngữ.
- **JD rất dài** hoặc section không tiêu đề: chia nhỏ theo giới hạn độ dài, không cắt mất nội dung im lặng.
- **JD trùng giữa hai nguồn** (cùng công ty + tiêu đề + nội dung gần giống): dedup tuyệt đối theo hash; trùng gần đúng
  chỉ cảnh báo.
- **Tên công ty là dữ liệu tổ chức, không phải PII**; nhưng tên/email/SĐT người liên hệ (HR) trong mô tả là PII → xóa.
- **Prompt injection trong JD** ("bỏ qua hướng dẫn trước"): lưu nguyên văn như dữ liệu; cách ly khi đưa vào prompt là
  việc của AIE.
- **Kỹ năng không có trong danh mục** (vd framework mới): báo danh sách để bổ sung, không tự tạo kỹ năng rác.
- **Seed khi job-service đã có dữ liệu demo tay**: không ghi đè, không xóa dữ liệu không do seed tạo.
- **JD ngoài IT trong mục IT của nguồn** (vd thiết kế đồ họa, kỹ thuật viên điện): loại ở bước xử lý (FR-028), báo theo
  nguồn.
- **Cùng JD đăng trên nhiều nguồn**: dedup theo hash nội dung chuẩn hóa; giữ bản có nhiều trường hơn.
- **JD synthetic trùng ý JD crawl**: chấp nhận được vì sinh từ tham số ô, không từ nội dung crawl (FR-024).

## Requirements *(mandatory)*

### Functional Requirements

**Crawl (US1 · S2-DE-1)**

- **FR-001**: Crawler MUST thu thập từ các nguồn được duyệt ở NC-3 các trường: tiêu đề, công ty, kỹ năng, mô tả đầy đủ
  (gồm yêu cầu, trách nhiệm, quyền lợi nếu có), địa điểm, cấp bậc/số năm kinh nghiệm, loại hình làm việc, lương (chỉ khi
  công khai), ngày đăng, hạn nộp, URL nguồn, id JD của nguồn, thời điểm crawl.
- **FR-002**: Mục tiêu ≥ 500 JD hợp lệ sau dedup, tính chung JD crawl + JD synthetic (NC-3); crawl lấy tối đa từ các
  nguồn được duyệt trong giới hạn FR-003, FR-004, synthetic chỉ bù phần thiếu (FR-023).
- **FR-003**: Crawler MUST đọc robots.txt của mỗi nguồn ở đầu mỗi lần chạy và MUST NOT request đường dẫn bị cấm (danh
  sách tại "Kiểm tra nguồn crawl"); khi nhóm quy tắc mâu thuẫn, áp dụng quy tắc chặt hơn.
- **FR-004**: Crawler MUST có giới hạn tốc độ cấu hình được (mặc định ≥ 2 giây giữa hai request tới cùng host, 1 kết nối
  đồng thời/host), giới hạn số trang, User-Agent nêu tên dự án + liên hệ; MUST dừng nguồn khi gặp 403/429/thử thách chống
  bot liên tiếp; MUST NOT né cơ chế chặn (đổi IP, giả lập trình duyệt để qua thử thách, giải captcha) và MUST NOT đăng
  nhập.
- **FR-005**: Crawler SHOULD ưu tiên dữ liệu có cấu trúc trong HTML tĩnh (vd khối `JobPosting` của itviec) và chỉ render
  JavaScript khi nguồn được duyệt thật sự cần.
- **FR-006**: Crawl MUST idempotent theo (nguồn, id JD của nguồn); 0 record hoặc thiếu trường bắt buộc hàng loạt MUST
  làm lệnh thất bại (kế thừa 005 FR-025).
- **FR-007**: Dữ liệu thô và đã xử lý MUST nằm ngoài git; MUST NOT commit nội dung crawl (kể cả mẫu nhỏ để test — fixture
  test dùng JD tự soạn) (constitution V, cùng quyết định 005 FR-024).

**Xử lý (US2 · S2-DE-2)**

- **FR-008**: Bước xử lý MUST làm sạch nội dung (HTML, khoảng trắng, ký tự điều khiển) không mất dấu tiếng Việt.
- **FR-009**: MUST xóa PII trước khi ghi bất kỳ output nào (kể cả file thô): email, số điện thoại, tên/liên hệ cá nhân
  của người tuyển dụng, link hồ sơ cá nhân; giữ tên công ty. Bước kiểm tra MUST báo 0 PII còn sót, nếu còn → thất bại.
- **FR-010**: MUST trích và chuẩn hóa kỹ năng về một danh mục kỹ năng (bí danh → tên chuẩn); kỹ năng ngoài danh mục MUST
  được báo cáo. Seed khớp bảng `skills` của `job_db` theo `slug`; kỹ năng thiếu thì thêm từ danh mục, không ghi đè bản ghi có sẵn.
- **FR-011**: MUST chuẩn hóa cấp bậc về tập `experience_levels` của `job_db`, loại hình về `remote | onsite | hybrid`,
  địa điểm về tên thành phố; lương về min/max/đơn vị tiền khi là số, nếu không thì để trống.
- **FR-012**: MUST chunk mỗi JD thành: 1 chunk tóm tắt (tiêu đề, công ty, kỹ năng, cấp bậc) + 1 chunk mỗi section nhận
  ra (yêu cầu, trách nhiệm, quyền lợi); section quá dài MUST chia theo giới hạn độ dài; mỗi chunk MUST có nhãn section,
  id JD nguồn, URL nguồn, công ty, ngôn ngữ, danh sách kỹ năng.
- **FR-013**: MUST dedup theo hash nội dung đã chuẩn hóa (JD và chunk) trước embed; trùng gần đúng chỉ cảnh báo.
- **FR-014**: Chế độ chỉ xử lý MUST chạy không cần DB và API key; output deterministic.

- **FR-028**: Bước xử lý MUST loại JD ngoài IT (tiêu đề và mô tả không khớp kỹ năng/từ khóa IT nào trong danh mục) và
  báo số bị loại theo nguồn; danh mục nghề của nguồn (vd "CNTT") không đủ làm bằng chứng.

**Index (US3 · S2-DE-3 — Stretch, ngoài Sprint 2 theo NC-2)**

- **FR-015**: Index MUST dùng đường ghi của 005 (một bản hiện thực, 005 FR-010), ghi theo schema `knowledge_chunks` do
  AIE sở hữu với `source_type = job_description`, MUST NOT tạo/sửa bảng. Cột `category` gán theo nhóm kỹ năng chính
  của JD nếu xác định được, không thì để trống; `topic_id`, `difficulty` để trống.
- **FR-016**: Index MUST idempotent; JD bị loại khỏi tập dữ liệu MUST bị gỡ khỏi kết quả truy hồi; phạm vi dọn MUST giới
  hạn trong `dataset` JD (kế thừa 005 FR-012, FR-013).
- **FR-017**: Mỗi lần chạy MUST in thống kê: record vào, JD hợp lệ, chunk, tỉ lệ dedup, embedding lỗi, thêm/bỏ qua/gỡ
  (constitution V).

**Seed `job_db` (US4 · S2-DE-4 — theo contract `data-model.md` §1–§2)**

- **FR-018**: Seed MUST nạp ≥ 200 job posting từ JD chuẩn hóa, mỗi posting có tiêu đề, mô tả, yêu cầu, địa điểm, loại
  hình, cấp bậc, ≥ 1 kỹ năng; lương chỉ khi có số thật.
- **FR-019**: Seed MUST bám đúng schema do migration của job-service tạo; MUST NOT tạo/sửa bảng; schema thiếu/khác MUST
  dừng trước khi ghi (constitution I).
- **FR-020**: Seed MUST idempotent và dọn riêng được mà không thêm cột ngoài contract: mọi posting seed thuộc Employer
  seed (email miền `seed.ai-recruit.test`); khóa idempotent `(employer_id, title, md5(description))` (cùng công ty + tiêu đề nhưng khác nội dung vẫn là hai
  posting, khớp dedup FR-013); manifest ngoài git ghi `jd_id` ↔ id posting, chỉ để bỏ qua nhanh, không thay khóa; dọn = xóa posting của Employer seed, không đụng dữ liệu khác.
- **FR-021**: Mỗi công ty MUST có một Employer seed (`users.role = Employer`) + `company_profiles.company_name`, ghi theo
  schema migration user-service; posting gắn `employer_id` của Employer đó. Tài khoản seed MUST NOT đăng nhập được
  (password là bcrypt của chuỗi ngẫu nhiên không lưu), email `seed-<slug công ty>@seed.ai-recruit.test`, MUST NOT chứa
  tên hay liên hệ người thật.
- **FR-022**: Seed SHOULD chọn 200 posting đa dạng: phủ ≥ 5 nhóm kỹ năng chính (Backend, Frontend, Mobile/Fullstack,
  DevOps, AI/Data), ≥ 3 cấp bậc, ≥ 3 thành phố; MUST ưu tiên JD crawl, JD synthetic chỉ lấp phần thiếu.

**JD synthetic (US5 · bù cho S2-DE-1)**

- **FR-023**: Lệnh sinh MUST chạy sau xử lý JD crawl, đọc báo cáo phân bố (US2) và chỉ sinh cho ô nhóm kỹ năng × cấp
  bậc × thành phố còn thiếu so với mục tiêu FR-002, FR-022; có giới hạn số JD mỗi lần chạy.
- **FR-024**: JD synthetic MUST sinh từ tham số ô (kỹ năng, cấp bậc, thành phố, loại hình) và danh mục kỹ năng; MUST NOT
  đưa nội dung JD crawl vào prompt (không viết lại JD thật thành synthetic).
- **FR-025**: JD synthetic MUST dùng tên công ty hư cấu, không trùng tên công ty nào trong JD crawl; MUST NOT chứa
  email, số điện thoại, URL thật. Lương MAY có khoảng số hợp lý theo cấp bậc.
- **FR-026**: Mỗi JD synthetic MUST mang cờ `synthetic` từ output sinh tới JD chuẩn hóa và posting seed (contract không có cột
  này: lưu ở manifest seed ngoài git; công ty synthetic là Employer seed hư cấu); báo cáo mỗi lần chạy MUST in tỉ lệ crawl / synthetic.
- **FR-027**: JD synthetic MUST qua cùng bước xử lý US2 (FR-008–FR-014, FR-028); lời gọi LLM dùng cấu hình LLM sẵn có
  của pipeline (005), lỗi có retry giới hạn; deterministic theo (ô, số thứ tự) để chạy lại không sinh trùng.

### Key Entities

- **Crawl Source**: tên, URL gốc, kết quả robots.txt (đường cho phép/cấm), điều khoản + trạng thái duyệt (NC-3), giới
  hạn tốc độ, trạng thái truy cập (OK / bị chặn).
- **Raw JD**: dữ liệu thô của một JD (đã xóa PII), nguồn, id JD của nguồn, URL, thời điểm crawl.
- **Normalized JD**: tiêu đề, công ty, kỹ năng chuẩn hóa, cấp bậc, loại hình, địa điểm, lương (tùy chọn), ngày
  đăng/hạn, các section, ngôn ngữ, hash nội dung.
- **Skill Dictionary**: tên chuẩn, bí danh, nhóm; đồng bộ với `job_db.skills`.
- **JD Chunk**: một bản ghi `knowledge_chunks` nguồn `job_description`; nội dung, nhãn section, id JD nguồn, `dataset`.
- **Seed Employer**: một `users` (Employer) + `company_profiles` cho một công ty JD, không đăng nhập được.
- **Seeded Job Posting**: một bản ghi `job_postings` + `job_skills` sinh từ Normalized JD, thuộc một Seed Employer.
- **Synthetic JD**: JD do LLM sinh cho một ô thiếu (kỹ năng × cấp bậc × thành phố), tên công ty hư cấu, cờ `synthetic`;
  sau sinh có cùng dạng Raw JD để đi chung bước xử lý.
- **Pipeline Run Report**: thống kê crawl/xử lý/index/seed của một lần chạy.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: ≥ 500 JD hợp lệ sau dedup (crawl + synthetic, báo tỉ lệ); ≥ 90% JD có tiêu đề, công ty, mô tả và ≥ 1 kỹ
  năng (đo riêng cho JD crawl, vì careerlink không có trường `skills` và phải trích từ mô tả).
- **SC-002**: 0 request tới đường dẫn robots.txt cấm; khoảng cách request ≥ cấu hình ở 100% request; 0 lần đăng nhập
  hoặc né chặn (kiểm chứng qua log).
- **SC-003**: 0 email/số điện thoại/liên hệ cá nhân trong dữ liệu thô, đã xử lý, kho tri thức và `job_db`; 0 file nội
  dung crawl trong git.
- **SC-004**: (Stretch, chỉ khi làm US3) ≥ 1500 chunk `job_description` (≈ 3 chunk/JD × 500), ≥ 99% có vector, dedup < 5%;
  chạy lại: 0 bản ghi mới, 0 lời gọi embed.
- **SC-005**: `job_db` có ≥ 200 posting seed đạt độ đa dạng FR-022; chạy lại: 0 posting mới; tìm kiếm của 007 trả kết
  quả cho ≥ 5/5 từ khóa mẫu (vd "NodeJS", "React", "DevOps", "Senior", "Hà Nội").
- **SC-006**: Toàn bộ xử lý + seed (không tính thời gian crawl bị giới hạn tốc độ) chạy ≤ 10 phút trên máy dev; chi phí
  embed < 0,1 USD.
- **SC-007**: Thành viên khác chạy lại xử lý + index + seed trên máy họ theo hướng dẫn, ≤ 5 lệnh, không cần hỏi DE (dữ
  liệu thô chia sẻ ngoài git).
- **SC-008**: 100% JD synthetic có cờ `synthetic`, tên công ty hư cấu, 0 PII; JD crawl chiếm phần lớn nhất có thể (báo
  tỉ lệ); 200 posting seed dùng JD crawl trước; chi phí sinh synthetic < 1 USD.

## Assumptions

- **Phụ thuộc 005**: tái dùng crawler mẫu (005 US5, `crawlers/polite_fetcher.py`), làm sạch, scrub PII, client LLM và
  đường ghi clean → chunk → dedup → embed → upsert (005 US2, US3); đã có trên `main` từ 2026-10-23 (PR #28, #29, #31).
- **Phụ thuộc 001**: `ai_db` + pgvector + DDL `knowledge_chunks` (AIE) đã có; chỉ cần cho US3 (Stretch).
- **Phụ thuộc 004, 007 (FSD)**: contract có ở `data-model.md` §1–§2; trên `main` chưa có migration `company_profiles`
  (user-service) và job-service. US4 viết theo contract, chạy được khi hai migration có trên `main`; preflight dừng nếu
  schema lệch contract (FR-019). US1, US2, US5 làm ngay được.
- **Mục đích sử dụng**: dữ liệu JD chỉ dùng nội bộ cho đồ án học thuật (demo, đánh giá), không công bố lại, không
  thương mại; môi trường staging (014) cần quyết định riêng có hiển thị posting seed công khai hay không.
- **Lương**: itviec ẩn lương khi không đăng nhập; careerviet công khai số VND min/max, topdev và careerlink có trường
  lương (định dạng khác nhau) → một phần posting có lương, phần còn lại để trống; FSD/UI phải chấp nhận lương trống.
- **Truy cập bị chặn**: topcv trả 403 cả từ IP datacenter (2026-10-23) lẫn IP cá nhân (2026-10-24), jobsgo trả 403 →
  loại; khi site chặn thì crawler dừng (FR-004), không thử né.
- **Ngoài phạm vi**: JD Parser/`jd_profile` (S2-AIE-6, AIE); TCP lấy JD theo application (S2-FSD-11); seed ứng viên,
  question bank, công ty ngoài các công ty của posting seed (S4-DE-2); textbook (012); crawl định kỳ/cập nhật liên tục.
- **Lệch phát hiện khi viết spec (báo người sở hữu, 009 không sửa file của họ)**:
  1. `rag-design.md` §3 (AIE): `job_description` là Stretch; `docs/sprint-plan.md` S2-DE-3: Bắt buộc; S2-AIE-6: "JD
     không vào RAG" → NC-2, đã chốt 2026-10-24; `docs/sprint-plan.md` S2-DE-1, S2-DE-3 sửa cùng PR clarify.
  2. `data-pipeline.md` §5 ghi `https://www.topcv.vn/tim-viec-lam-it` + `max_pages: 50` cho cả hai site và dùng
     Playwright: không khớp kết quả kiểm tra (topcv chặn; các nguồn được dùng không cần JS) — cập nhật ở plan.
  3. `data-pipeline.md` §5 lấy `salary_range`: itviec ẩn lương khi chưa đăng nhập.
  4. `data-model.md` §2 `job_postings` không có cột nguồn / id JD gốc / cờ seed → giải bằng Employer seed + manifest
     (FR-020, FR-026), không cần FSD thêm cột.
  5. Tên công ty nằm ở `company_profiles` (`user_db`) → seed tạo Employer seed + `company_profiles` theo contract (FR-021).
