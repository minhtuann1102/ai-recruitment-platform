# Feature Specification: JD Crawling & Seeding

**Feature Branch**: `docs/jd-crawling-seeding-spec` (spec); branch code đặt ở plan
(theo `docs/conventions.md`; thư mục spec độc lập với branch)

**Created**: 2026-10-23

**Status**: Draft — chờ DE duyệt; còn 3 điểm `[NEEDS CLARIFICATION]` (chưa chạy `/speckit-clarify`, `/speckit-plan`)

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

## Clarifications

Chưa chạy `/speckit-clarify`. Ba điểm phụ thuộc người khác hoặc chưa chốt, DE không tự quyết:

- **NC-1 (schema `job_db`)**: [NEEDS CLARIFICATION: Schema `job_postings`/`skills`/`job_skills`/`experience_levels`
  do migration của job-service (feature 007, FSD) tạo — trên `main` chưa có job-service và chưa có migration nào.
  Seed (US4) bám theo bản nào: (a) chờ migration 007 merge rồi mới viết mapping; (b) viết mapping theo
  `data-model.md` §2 và sửa khi 007 chốt; (c) seed qua API/TCP của job-service thay vì ghi DB? Kèm: `employer_id`
  (UUID user Employer bên `user_db`) lấy từ đâu — tạo tài khoản Employer seed hay dùng một UUID cố định? Bản ghi seed
  để `status` gì (`open`/`draft`)? Ai duyệt mapping — FSD?]
- **NC-2 (S2-DE-3 Bắt buộc hay Stretch)**: [NEEDS CLARIFICATION: `docs/sprint-plan.md` ghi S2-DE-3 "Index JD vào
  ai_db" là **Bắt buộc**, nhưng `rag-design.md` §3 ghi `job_description` là **Stretch, AI không dùng**, và S2-AIE-6
  ghi "JD không vào RAG" (JD đi qua JD Parser → `jd_profile`). Index JD có còn cần không? Nếu Stretch: SC-004 chỉ còn
  1500 chunk tổng của Quality Gate S2 (data-pipeline §9) — đạt bằng nguồn nào? AIE + DE chốt.]
- **NC-3 (500 JD khả thi + nguồn hợp lệ)**: [NEEDS CLARIFICATION: topcv.vn chặn truy cập tự động (Cloudflare 403),
  itviec.com cho phép theo robots.txt nhưng điều khoản 2.2 hạn chế sao chép ngoài mục đích cá nhân khi chưa có đồng ý
  bằng văn bản; itviec lúc kiểm tra có ~33 trang danh sách IT (ước tính vài trăm tới ~800 JD, chưa đếm chính xác). Chọn
  hướng nào: (a) chỉ itviec, hạ mục tiêu (vd ≥ 300 JD) và chấp nhận rủi ro ToS cho mục đích học thuật, không công bố
  lại nội dung; (b) xin đồng ý bằng văn bản của itviec/topcv trước khi crawl; (c) thay/bổ sung nguồn có giấy phép rõ
  (dataset JD công khai, API chính thức, JD tự soạn/synthetic như 005); (d) kết hợp. Mục tiêu 500 JD và 200 posting
  giữ hay đổi? Team + giảng viên hướng dẫn chốt.]

## User Scenarios & Testing *(mandatory)*

Người dùng trực tiếp: **DE** (vận hành crawl, xử lý, index, seed), **FSD** (cần `job_db` có dữ liệu thật để demo tìm
kiếm/lọc/ứng tuyển ở 007/008 và frontend 013), **AIE** (nếu NC-2 giữ index: truy hồi đoạn JD theo kỹ năng). Người
dùng cuối hưởng lợi gián tiếp: danh sách việc làm demo trông thật, đa dạng kỹ năng/cấp bậc/địa điểm. Hội đồng demo
Sprint 2 cần thấy: "JD data indexed" và full job lifecycle trên dữ liệu thật.

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

### User Story 3 - Index chunk JD vào kho tri thức (Priority: P2 — phụ thuộc NC-2) · S2-DE-3

DE chạy pipeline đầy đủ: chunk JD được embed và ghi vào kho tri thức với nguồn `job_description`, dùng chung đường ghi
của 005. AIE truy hồi được đoạn JD theo truy vấn kỹ năng.

**Why this priority**: Sprint plan ghi Bắt buộc, nhưng rag-design và S2-AIE-6 cho rằng AI không dùng JD trong RAG
(NC-2). Ưu tiên chốt sau khi NC-2 có kết luận.

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

### User Story 4 - Seed 200 job posting vào job_db (Priority: P1 — phụ thuộc NC-1) · S2-DE-4

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

## Requirements *(mandatory)*

### Functional Requirements

**Crawl (US1 · S2-DE-1)**

- **FR-001**: Crawler MUST thu thập từ các nguồn được duyệt ở NC-3 các trường: tiêu đề, công ty, kỹ năng, mô tả đầy đủ
  (gồm yêu cầu, trách nhiệm, quyền lợi nếu có), địa điểm, cấp bậc/số năm kinh nghiệm, loại hình làm việc, lương (chỉ khi
  công khai), ngày đăng, hạn nộp, URL nguồn, id JD của nguồn, thời điểm crawl.
- **FR-002**: Mục tiêu số JD hợp lệ sau dedup: ≥ 500 (sprint plan); con số cuối theo kết luận NC-3.
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
  được báo cáo. Danh mục kỹ năng dùng chung với bảng `skills` của `job_db` (NC-1).
- **FR-011**: MUST chuẩn hóa cấp bậc về tập `experience_levels` của `job_db`, loại hình về `remote | onsite | hybrid`,
  địa điểm về tên thành phố; lương về min/max/đơn vị tiền khi là số, nếu không thì để trống.
- **FR-012**: MUST chunk mỗi JD thành: 1 chunk tóm tắt (tiêu đề, công ty, kỹ năng, cấp bậc) + 1 chunk mỗi section nhận
  ra (yêu cầu, trách nhiệm, quyền lợi); section quá dài MUST chia theo giới hạn độ dài; mỗi chunk MUST có nhãn section,
  id JD nguồn, URL nguồn, công ty, ngôn ngữ, danh sách kỹ năng.
- **FR-013**: MUST dedup theo hash nội dung đã chuẩn hóa (JD và chunk) trước embed; trùng gần đúng chỉ cảnh báo.
- **FR-014**: Chế độ chỉ xử lý MUST chạy không cần DB và API key; output deterministic.

**Index (US3 · S2-DE-3 — phạm vi theo NC-2)**

- **FR-015**: Index MUST dùng đường ghi của 005 (một bản hiện thực, 005 FR-010), ghi theo schema `knowledge_chunks` do
  AIE sở hữu với `source_type = job_description`, MUST NOT tạo/sửa bảng. Cột `category` gán theo nhóm kỹ năng chính
  của JD nếu xác định được, không thì để trống; `topic_id`, `difficulty` để trống.
- **FR-016**: Index MUST idempotent; JD bị loại khỏi tập dữ liệu MUST bị gỡ khỏi kết quả truy hồi; phạm vi dọn MUST giới
  hạn trong `dataset` JD (kế thừa 005 FR-012, FR-013).
- **FR-017**: Mỗi lần chạy MUST in thống kê: record vào, JD hợp lệ, chunk, tỉ lệ dedup, embedding lỗi, thêm/bỏ qua/gỡ
  (constitution V).

**Seed `job_db` (US4 · S2-DE-4 — phụ thuộc NC-1)**

- **FR-018**: Seed MUST nạp ≥ 200 job posting từ JD chuẩn hóa, mỗi posting có tiêu đề, mô tả, yêu cầu, địa điểm, loại
  hình, cấp bậc, ≥ 1 kỹ năng; lương chỉ khi có số thật.
- **FR-019**: Seed MUST bám đúng schema do migration của job-service tạo; MUST NOT tạo/sửa bảng; schema thiếu/khác MUST
  dừng trước khi ghi (constitution I).
- **FR-020**: Seed MUST idempotent theo (nguồn, id JD gốc) và MUST đánh dấu được bản ghi do seed tạo để dọn riêng.
- **FR-021**: Posting seed MUST gắn với một chủ sở hữu Employer hợp lệ theo quy ước chốt ở NC-1; MUST NOT tạo tài khoản
  với thông tin cá nhân thật.
- **FR-022**: Seed SHOULD chọn 200 posting đa dạng: phủ ≥ 5 nhóm kỹ năng chính (Backend, Frontend, Mobile/Fullstack,
  DevOps, AI/Data), ≥ 3 cấp bậc, ≥ 3 thành phố.

### Key Entities

- **Crawl Source**: tên, URL gốc, kết quả robots.txt (đường cho phép/cấm), điều khoản + trạng thái duyệt (NC-3), giới
  hạn tốc độ, trạng thái truy cập (OK / bị chặn).
- **Raw JD**: dữ liệu thô của một JD (đã xóa PII), nguồn, id JD của nguồn, URL, thời điểm crawl.
- **Normalized JD**: tiêu đề, công ty, kỹ năng chuẩn hóa, cấp bậc, loại hình, địa điểm, lương (tùy chọn), ngày
  đăng/hạn, các section, ngôn ngữ, hash nội dung.
- **Skill Dictionary**: tên chuẩn, bí danh, nhóm; đồng bộ với `job_db.skills`.
- **JD Chunk**: một bản ghi `knowledge_chunks` nguồn `job_description`; nội dung, nhãn section, id JD nguồn, `dataset`.
- **Seeded Job Posting**: một bản ghi `job_postings` + `job_skills` sinh từ Normalized JD, có dấu "do seed tạo".
- **Pipeline Run Report**: thống kê crawl/xử lý/index/seed của một lần chạy.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: ≥ 500 JD hợp lệ sau dedup (hoặc mục tiêu chốt ở NC-3); ≥ 90% JD có tiêu đề, công ty, mô tả và ≥ 1 kỹ
  năng.
- **SC-002**: 0 request tới đường dẫn robots.txt cấm; khoảng cách request ≥ cấu hình ở 100% request; 0 lần đăng nhập
  hoặc né chặn (kiểm chứng qua log).
- **SC-003**: 0 email/số điện thoại/liên hệ cá nhân trong dữ liệu thô, đã xử lý, kho tri thức và `job_db`; 0 file nội
  dung crawl trong git.
- **SC-004**: (Nếu NC-2 giữ index) ≥ 1500 chunk `job_description` (≈ 3 chunk/JD × 500), ≥ 99% có vector, dedup < 5%;
  chạy lại: 0 bản ghi mới, 0 lời gọi embed.
- **SC-005**: `job_db` có ≥ 200 posting seed đạt độ đa dạng FR-022; chạy lại: 0 posting mới; tìm kiếm của 007 trả kết
  quả cho ≥ 5/5 từ khóa mẫu (vd "NodeJS", "React", "DevOps", "Senior", "Hà Nội").
- **SC-006**: Toàn bộ xử lý + seed (không tính thời gian crawl bị giới hạn tốc độ) chạy ≤ 10 phút trên máy dev; chi phí
  embed < 0,1 USD.
- **SC-007**: Thành viên khác chạy lại xử lý + index + seed trên máy họ theo hướng dẫn, ≤ 5 lệnh, không cần hỏi DE (dữ
  liệu thô chia sẻ ngoài git).

## Assumptions

- **Phụ thuộc 005**: tái dùng crawler mẫu (005 US5) và đường ghi clean → chunk → dedup → embed → upsert (005 US2, US3).
  005 chưa có plan/code trên `main` (`apps/data-pipeline/` chưa tồn tại); nếu 005 chưa xong khi bắt đầu 009, US3 bị chặn.
- **Phụ thuộc 001**: `ai_db` + pgvector + DDL `knowledge_chunks` (AIE) phải có trên `main` trước US3.
- **Phụ thuộc 007 (FSD)**: `job_db` chỉ có bản thiết kế ở `data-model.md` §2, chưa có job-service/migration. US4 bị chặn
  tới khi 007 có migration (NC-1). US1, US2 làm ngay được.
- **Mục đích sử dụng**: dữ liệu JD chỉ dùng nội bộ cho đồ án học thuật (demo, đánh giá), không công bố lại, không
  thương mại; môi trường staging (014) cần quyết định riêng có hiển thị posting seed công khai hay không.
- **Lương**: itviec không công khai lương khi không đăng nhập → đa số posting seed không có lương; FSD/UI phải chấp nhận
  lương trống.
- **Kiểm tra từ IP datacenter**: kết quả topcv (403) có thể khác khi chạy từ máy cá nhân; dù vậy, khi site chặn thì
  crawler dừng (FR-004), không thử né.
- **Ngoài phạm vi**: JD Parser/`jd_profile` (S2-AIE-6, AIE); TCP lấy JD theo application (S2-FSD-11); seed công ty,
  ứng viên, question bank (S4-DE-2); textbook (012); crawl định kỳ/cập nhật liên tục.
- **Lệch phát hiện khi viết spec (báo người sở hữu, 009 không sửa file của họ)**:
  1. `rag-design.md` §3 (AIE): `job_description` là Stretch; `docs/sprint-plan.md` S2-DE-3: Bắt buộc; S2-AIE-6: "JD
     không vào RAG" → NC-2.
  2. `data-pipeline.md` §5 ghi `https://www.topcv.vn/tim-viec-lam-it` + `max_pages: 50` cho cả hai site và dùng
     Playwright: không khớp kết quả kiểm tra (topcv chặn; itviec không cần JS; itviec ~33 trang) — cập nhật ở plan.
  3. `data-pipeline.md` §5 lấy `salary_range`: itviec ẩn lương khi chưa đăng nhập.
  4. `data-model.md` §2 `job_postings` không có cột lưu nguồn/id JD gốc hoặc cờ "do seed tạo" → idempotent/dọn seed
     (FR-020) cần FSD thêm cột hoặc quy ước khác (NC-1).
  5. `data-model.md` `company_profiles` nằm ở `user_db`; `job_postings` chỉ có `employer_id` → tên công ty JD không có
     chỗ lưu trong `job_db` nếu không tạo Employer/company tương ứng (NC-1).
