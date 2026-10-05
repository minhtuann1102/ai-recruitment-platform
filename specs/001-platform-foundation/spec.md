# Feature Specification: Platform Foundation (hạ tầng local, định danh dự án, gateway, CI)

**Feature Branch**: 3 PR — `chore/rename-project-scope`, `chore/docker-multi-db-minio`, `chore/apisix-routes-ci`
(theo `docs/conventions.md`; thư mục spec độc lập với branch)

**Created**: 2026-10-05

**Status**: Draft

**Owner**: DE (Data Engineer + DevOps) — **Sprint**: 0 (28/09 → 12/10/2026)

**Covers**: S0-DE-1, S0-DE-2, S0-DE-3, S0-DE-4, S0-DE-5, S0-DE-6

**Input**: User description: "Nhiệm vụ của tôi là phần data + devops. Áp dụng Spec Kit cho toàn dự án; feature đầu
tiên là nền tảng Sprint 0 của DE: đổi tên project, Docker multi-DB, MinIO, APISIX routes, CI pipeline, `.env.example`."

## User Scenarios & Testing *(mandatory)*

Người dùng của feature này là **3 thành viên dev** (FSD, AIE, DE) và **hội đồng chấm/demo**. Giá trị: mọi người
dựng được cùng một môi trường bằng một lệnh, code được kiểm tra tự động, và 3 workstream không chặn nhau.

### User Story 1 - Một lệnh dựng toàn bộ hạ tầng local (Priority: P1)

Thành viên vừa clone repo copy file env mẫu, chạy một lệnh, và có đủ hạ tầng: database riêng cho từng service
(trong đó DB tri thức hỗ trợ tìm kiếm vector), cache, gateway, object storage. Tất cả báo healthy.

**Why this priority**: Mọi task khác của cả 3 role (scaffold job/interview-service, ai_db, migration) đều chờ
hạ tầng này (xem dependency graph trong `docs/sprint-0-kickoff.md`).

**Independent Test**: Trên máy chưa có volume cũ: clone → copy env mẫu → một lệnh khởi động → liệt kê
database và kiểm tra trạng thái các thành phần.

**Acceptance Scenarios**:

1. **Given** máy sạch đã cài Docker, **When** chạy lệnh khởi động hạ tầng, **Then** có đủ 5 database
   `user_db`, `job_db`, `interview_db`, `notification_db`, `ai_db` và mọi thành phần hạ tầng ở trạng thái healthy.
2. **Given** hạ tầng đang chạy, **When** kiểm tra `ai_db`, **Then** extension tìm kiếm vector khả dụng.
3. **Given** hạ tầng đang chạy, **When** upload một file thử vào bucket mặc định rồi tải về, **Then** file tải
   về giống hệt bản gốc, và console quản trị storage truy cập được.
4. **Given** đã khởi động một lần, **When** chạy lại lệnh khởi động, **Then** không lỗi và không mất dữ liệu.

---

### User Story 2 - Định danh dự án thống nhất, sạch phần thừa của starter (Priority: P1)

Mọi package, container, network mang tên dự án (`@ai-recruit/*`, `ai_recruit_*`). Không còn cấu hình Kong hay
tên `nest-turbo`/`@app` trong code và config đang dùng.

**Why this priority**: Đổi tên chạm vào nhiều file dùng chung (62 file TS import lib nội bộ). Làm càng muộn,
xung đột merge với nhánh FSD/AIE càng lớn — phải xong và merge đầu tiên.

**Independent Test**: Cài dependency + build toàn bộ monorepo thành công; tìm chuỗi tên cũ trong file được
track (trừ tài liệu lịch sử/ADR) trả về 0 kết quả.

**Acceptance Scenarios**:

1. **Given** đã đổi tên, **When** cài dependency và build toàn bộ, **Then** thành công không lỗi.
2. **Given** đã đổi tên, **When** khởi động hạ tầng, **Then** mọi container mang prefix `ai_recruit_` và cùng
   network của dự án.
3. **Given** đã dọn, **When** tìm `kong`, `nest-turbo`, `nest_turbo`, `@app/` trong code/config được track,
   **Then** không còn kết quả (ngoại trừ `docs/` mô tả lịch sử và lockfile tự sinh lại).

---

### User Story 3 - Mọi PR được kiểm tra tự động (Priority: P2)

Mỗi push/PR tự động chạy lint, kiểm tra kiểu, và test cho toàn monorepo (cả phần Node và phần Python). PR có
lỗi bị đánh dấu thất bại.

**Why this priority**: Hiện thực hóa principle VI (Quality Gates) của constitution. Cần hạ tầng đổi tên xong để
pipeline chạy trên tên mới, nên đứng sau US1/US2.

**Independent Test**: Mở PR thử có lỗi lint cố ý → pipeline đỏ; sửa lỗi → pipeline xanh.

**Acceptance Scenarios**:

1. **Given** một PR sạch, **When** pipeline chạy, **Then** lint, type check, test đều qua và báo xanh.
2. **Given** một PR có lỗi lint/type/test, **When** pipeline chạy, **Then** báo đỏ và chỉ rõ bước lỗi.
3. **Given** repo có app Python (ai-service, data-pipeline), **When** pipeline chạy, **Then** test Python của
   app đó cũng được chạy.
4. **Given** pipeline chạy trên PR, **When** không có secret thật nào được cấu hình, **Then** pipeline vẫn chạy
   được (không phụ thuộc API key thật).

---

### User Story 4 - Gateway định tuyến tới các service mới (Priority: P2)

Client gọi `/job/*`, `/interview/*`, `/ai/*` qua gateway như với `/auth/*`, `/user/*`: route được bảo vệ cần
token hợp lệ, health check công khai.

**Why this priority**: FSD/AIE cần route để test end-to-end qua gateway, nhưng có thể test trực tiếp service
trong lúc chờ.

**Independent Test**: Sync cấu hình gateway → gọi route bảo vệ không token nhận 401; gọi health công khai
nhận phản hồi từ service (hoặc lỗi upstream rõ ràng nếu service chưa chạy).

**Acceptance Scenarios**:

1. **Given** cấu hình gateway đã sync, **When** gọi `/job/api/...` không token, **Then** nhận 401.
2. **Given** token hợp lệ và service đang chạy, **When** gọi route được bảo vệ, **Then** request tới đúng service
   với thông tin user được gateway gắn kèm.
3. **Given** một service chưa chạy, **When** gọi route của nó, **Then** gateway trả lỗi upstream, các route khác
   không bị ảnh hưởng.

---

### User Story 5 - File env mẫu đầy đủ, không chứa secret (Priority: P3)

File env mẫu liệt kê mọi biến mà hạ tầng và các service cần (kết nối DB riêng từng service, object storage,
LLM provider dạng placeholder, port TCP, host/port upstream của gateway), có ghi chú, không chứa secret thật.

**Why this priority**: Giảm lỗi "chạy được trên máy tôi"; phần lớn biến được thêm dần trong US1–US4, story này
chốt lại và dọn biến thừa.

**Independent Test**: Copy env mẫu nguyên trạng → khởi động hạ tầng + sync gateway thành công mà không phải
thêm biến nào.

**Acceptance Scenarios**:

1. **Given** env mẫu được copy nguyên trạng, **When** khởi động hạ tầng và sync gateway, **Then** không có cảnh
   báo biến thiếu.
2. **Given** env mẫu, **When** rà soát, **Then** không có giá trị secret thật; biến Kong đã bị gỡ.

---

### Edge Cases

- Máy đã có volume DB cũ (từ setup 1 DB của starter): script tạo DB không chạy lại → thiếu DB. Cần cách
  đảm bảo DB tồn tại hoặc hướng dẫn reset volume rõ ràng.
- Máy Windows (PowerShell) không có biến `PWD`: đường dẫn volume dạng `${PWD}/...` bị sai → phải chạy được trên
  Windows, macOS, Linux.
- Port đã bị chiếm (DB 5534, storage 9000/9001, gateway 9080/9180): lỗi phải dễ nhận biết, port cấu hình được qua env.
- Nhánh `origin/feat/aie` đã sửa compose (thêm ai-service) và gateway (route `/ai/*`) theo tên cũ: đổi tên phải
  không làm mất thay đổi đó khi merge.
- Dependency chỉ dành cho macOS ARM trong root devDependencies (`@oxlint/binding-darwin-arm64`,
  `@turbo/darwin-arm64`) có thể làm hỏng cài đặt trên CI Linux/Windows.
- PR từ fork không có secret: pipeline vẫn phải chạy.

## Requirements *(mandatory)*

### Functional Requirements

**Hạ tầng local (US1)**

- **FR-001**: Một lệnh duy nhất MUST khởi động toàn bộ hạ tầng local: database server, cache, gateway (kèm kho
  cấu hình), object storage, và mock ai-service khi đã có.
- **FR-002**: Database server MUST cung cấp 5 database tách biệt `user_db`, `job_db`, `interview_db`,
  `notification_db`, `ai_db`; `ai_db` MUST hỗ trợ extension vector.
- **FR-003**: Việc tạo database MUST idempotent; MUST có cách được tài liệu hóa để áp dụng cho máy đã có volume cũ.
- **FR-004**: Object storage MUST có console quản trị, bucket mặc định được tạo tự động, và upload/download kiểm
  chứng được.
- **FR-005**: Mọi thành phần hạ tầng MUST có health check; lệnh khởi động MUST chạy được trên Windows, macOS, Linux.

**Định danh dự án (US2)**

- **FR-006**: Mọi package MUST mang scope `@ai-recruit/*`; mọi import lib nội bộ MUST dùng tên mới; container
  MUST có prefix `ai_recruit_`; network MUST là `ai-recruit-network`.
- **FR-007**: Cấu hình Kong (compose, config, biến env, lệnh make) MUST bị gỡ bỏ.
- **FR-008**: Thay đổi đổi tên MUST giữ nguyên các thay đổi hạ tầng của nhánh `origin/feat/aie` khi hợp nhất.

**CI (US3)**

- **FR-009**: Pipeline MUST chạy trên mọi pull request và mọi push vào nhánh chính/nhánh tích hợp: cài dependency
  theo lockfile, lint, type check, test cho phần Node.
- **FR-010**: Pipeline MUST chạy test cho từng app Python có mặt trong repo.
- **FR-011**: Pipeline MUST NOT cần secret thật; lỗi ở bất kỳ bước nào MUST làm pipeline thất bại.

**Gateway (US4)**

- **FR-012**: Gateway MUST có route `/job/*`, `/interview/*`, `/ai/*` theo cùng mẫu với route hiện có: yêu cầu
  token trừ health check, gắn thông tin user cho service phía sau.
- **FR-013**: Host/port upstream của mỗi service MUST cấu hình qua env.

**Env & tài liệu (US5)**

- **FR-014**: File env mẫu MUST liệt kê đủ biến cho hạ tầng và mọi service, kèm ghi chú, chỉ dùng placeholder
  cho secret.
- **FR-015**: Mọi biến env mà service NestJS dùng MUST được đăng ký trong cấu hình biến toàn cục của build tool.
- **FR-016**: README MUST phản ánh tên mới, lệnh khởi động, cách reset volume, và cách kiểm chứng hạ tầng.

### Key Entities

- **Service Database**: database của một service; thuộc tính: tên, service sở hữu, extension yêu cầu.
- **Env Variable**: tên, phạm vi (hạ tầng / service nào), là secret hay không, giá trị mẫu.
- **Gateway Route**: prefix, service upstream, chính sách auth (bảo vệ / công khai), rewrite.
- **Storage Bucket**: tên, quyền truy cập, mục đích (CV, avatar, logo).
- **CI Check**: tên bước, phạm vi (Node / Python app), điều kiện thất bại.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Thành viên mới đi từ clone tới hạ tầng healthy trong ≤ 15 phút, với ≤ 5 lệnh theo README.
- **SC-002**: 100% thành phần hạ tầng báo healthy trong ≤ 2 phút sau lệnh khởi động (đã có image).
- **SC-003**: 0 kết quả khi tìm tên cũ (`kong`, `nest-turbo`, `nest_turbo`, `@app/`) trong code/config được track
  (trừ `docs/` lịch sử).
- **SC-004**: 100% PR có kết quả pipeline trong ≤ 10 phút; 100% PR cố ý chứa lỗi bị đánh đỏ.
- **SC-005**: 100% request không token tới route được bảo vệ nhận 401; health check công khai trả thành công.
- **SC-006**: File upload thử và file tải về có checksum trùng khớp.
- **SC-007**: 7/7 mục DE trong "Checklist Sprint 0 Done" (`docs/sprint-0-kickoff.md`) hoàn thành trước 2026-10-12.

## Assumptions

- Môi trường local dùng một database server chứa nhiều database (ADR-002 cho phép); tách instance cho
  production thuộc feature 014-staging-deploy-monitoring.
- Mock ai-service, route `/ai/*`, và DDL bảng `knowledge_chunks` do AIE làm trên `origin/feat/aie` (S0-AIE-1/2).
  Feature này chỉ đổi tên/hợp nhất các phần đó và đảm bảo `ai_db` + extension vector tồn tại.
- Chuyển gRPC → TCP là S0-FSD-2 (FSD). Feature này chỉ thêm biến port TCP vào env mẫu; biến gRPC được gỡ khi
  FSD hoàn tất.
- job-service và interview-service do FSD scaffold (S0-FSD-3/4); route gateway có thể tồn tại trước khi service chạy.
- Dữ liệu local là dữ liệu dev, reset volume được chấp nhận.
- Kafka/RabbitMQ (đang comment trong compose) giữ nguyên trạng, không thuộc phạm vi.
- Pipeline chưa build/push image Docker; việc đó thuộc feature 014.
- Nhánh `develop` chưa có trên origin (TODO(DEVELOP_BRANCH) trong constitution); pipeline cấu hình cho cả `main`
  và `develop`.
