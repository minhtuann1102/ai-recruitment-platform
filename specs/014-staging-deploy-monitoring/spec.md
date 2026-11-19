# Feature Specification: Staging Deploy & Monitoring

**Feature Branch**: `docs/staging-deploy-spec` (spec); branch code đặt ở plan (theo `docs/conventions.md`; thư mục spec
độc lập với branch)

**Created**: 2026-11-19

**Status**: Draft

**Owner**: DE — **Sprint**: 4 (23/11 → 07/12/2026); staging dùng tiếp cho Sprint 5 (E2E, báo cáo, 07/12 → 21/12)

**Covers**: S4-DE-3 (deploy staging, Bắt buộc), S4-DE-4 (monitoring, Stretch nhưng làm phần tối thiểu cùng deploy).
**Không** gồm S4-DE-2 (seed, đi theo 009 US4).

**Input**: User description: "Deploy staging S4-DE-3 + monitoring S4-DE-4 theo plan
`plans/261117-2137-devops-monitoring-eval/plan.md` Phase 1–2: một VM GCP chạy docker compose, TLS trước gateway,
giám sát và cảnh báo email bằng dịch vụ có sẵn của GCP; deploy những gì đã có trên `main` cộng cách thêm service sau."

**Nguồn thiết kế**: [plan 261117-2137](../../plans/261117-2137-devops-monitoring-eval/plan.md) Phase 1–2;
[constitution](../../.specify/memory/constitution.md) (Ràng buộc kỹ thuật & hạ tầng); `docker-compose.yml`;
`config/apisix/conf/apisix-dev.yaml`; [`docs/architecture/rag-design.md`](../../docs/architecture/rag-design.md) (kho
`ai_db` dùng chung). Spec chỉ ghi phần mới hoặc khác.

## Bối cảnh (kiểm tra 2026-11-19)

- **Chưa có môi trường chung nào ngoài máy dev.** Đề cương và sprint plan cam kết bản demo chạy trên cloud có HTTPS;
  Sprint 5 (E2E, quay demo, báo cáo) cần một địa chỉ cố định cả nhóm và GVHD mở được.
- **Đã có trên `main`**: ai-service (có Dockerfile, `/api/health`, `/metrics`), hạ tầng compose (Postgres, Redis,
  MinIO, etcd + APISIX), 3 service NestJS `auth-service`, `user-service`, `notification-service` (có code, có route
  APISIX, **chưa có Dockerfile, chưa có health endpoint, chưa chạy trong compose**).
- **Chưa có**: web frontend (`apps/web`, spec 013 của FSD), `job-service`, `interview-service`. Không chờ chúng:
  staging lên với cái đang có và có quy trình thêm service sau.
- **Kho RAG `ai_db`** nằm ở Supabase dùng chung (ngoài compose); ai-service staging đọc kho đó bằng vai trò chỉ đọc.
- **CI** hiện chỉ lint + test; chưa build image, chưa deploy.

## Quyết định (DE, 2026-11-17 và 2026-11-19)

| Chủ đề | Chốt |
|---|---|
| Backend | Một VM Compute Engine (`asia-southeast1`) chạy Docker Compose, giống máy dev; không tách Cloud Run trong S4 |
| TLS | Reverse proxy có TLS tự động đứng trước APISIX; chỉ mở cổng 80/443 |
| Frontend | Vercel (khi 013 có code); domain mua trên Vercel, bản ghi `api` trỏ IP tĩnh của VM |
| Giám sát | Dịch vụ có sẵn của GCP (agent trên VM → metrics + logs, uptime check, alert) thay vì tự dựng Prometheus / Grafana |
| Cảnh báo | Email |
| Ngân sách LLM | Không giới hạn cứng (vẫn tránh lãng phí) |
| Tài khoản | GCP project + billing đã có; **domain chưa mua** (spec dùng `<domain>`) |
| Ngoài phạm vi | Seed (S4-DE-2), eval hồi quy trong CI (plan 3.2), voice (015) |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Staging chạy qua HTTPS với các service đang có (Priority: P1)

DE dựng một máy chủ staging, đưa toàn bộ service đang có trên `main` lên chạy sau gateway, có HTTPS. Thành viên nhóm và
GVHD gọi được API (đăng ký / đăng nhập qua auth + user, chạy một phiên phỏng vấn AI qua ai-service) từ trình duyệt
hoặc công cụ gọi API ở bất kỳ đâu.

**Why this priority**: là cam kết Bắt buộc S4-DE-3 và điều kiện cho mọi việc sau (deploy tự động, giám sát, E2E ở
Sprint 5). Thiếu nó thì không có gì để demo.

**Independent Test**: từ một máy ngoài mạng nhóm, gọi health của gateway và từng service qua `https://api.<domain>`,
đăng ký + đăng nhập một tài khoản thử, chạy một phiên phỏng vấn AI đầy đủ (bắt đầu → vài lượt → kết thúc) và nhận
câu chữ dạng stream từng phần.

**Acceptance Scenarios**:

1. **Given** máy chủ staging mới dựng và file cấu hình bí mật đã đặt trên máy, **When** DE chạy lệnh khởi động
   staging, **Then** mọi service báo khỏe trong 5 phút và health công khai của gateway trả thành công qua HTTPS với
   chứng chỉ hợp lệ.
2. **Given** staging đang chạy, **When** người dùng gọi một endpoint stream của ai-service qua HTTPS, **Then** phần chữ
   đầu tiên tới tay người dùng ngay khi ai-service phát ra, không bị gom lại tới cuối.
3. **Given** staging đang chạy, **When** quét cổng IP công khai của máy từ bên ngoài, **Then** chỉ thấy cổng 80 và
   443; cơ sở dữ liệu, cache, object storage, etcd, admin API của gateway không truy cập được từ Internet.
4. **Given** một service NestJS, **When** gọi health endpoint của nó, **Then** nó trả trạng thái khỏe khi phụ thuộc
   bắt buộc (DB nếu có) sẵn sàng và trả lỗi khi không.

---

### User Story 2 - Deploy bản mới và quay lại bản cũ bằng một lệnh (Priority: P1)

Mỗi khi `main` có commit mới, bản build của từng service được tạo tự động và lưu ở kho image riêng. DE (hoặc thành viên
có quyền) đưa bản đó lên staging bằng một lệnh; nếu bản mới hỏng thì quay lại bản trước bằng một lệnh.

**Why this priority**: nhóm 3 người merge liên tục trong S4–S5; deploy tay từng bước dễ sai và tốn thời gian của DE.
Quay lại nhanh giữ cho staging luôn demo được.

**Independent Test**: merge một thay đổi nhỏ vào `main`, chờ build xong, chạy lệnh deploy, thấy phiên bản mới trong
health; chạy lệnh quay lại, thấy phiên bản cũ.

**Acceptance Scenarios**:

1. **Given** một commit mới trên `main` đã qua CI, **When** build tự động xong, **Then** kho image có image của từng
   service đổi, gắn nhãn theo mã commit, không cần khóa bí mật dài hạn nào lưu trong repo hay CI.
2. **Given** image mới đã có, **When** DE chạy lệnh deploy, **Then** staging kéo đúng phiên bản đó, chạy migration
   của service cần migration trước khi service nhận traffic, và health cho thấy phiên bản mới.
3. **Given** migration của một service lỗi, **When** deploy, **Then** quá trình dừng, service đó giữ phiên bản cũ đang
   chạy, lệnh in lỗi và thoát khác 0.
4. **Given** phiên bản đang chạy bị lỗi, **When** DE chạy lệnh quay lại, **Then** staging chạy lại phiên bản ngay
   trước đó trong ≤ 5 phút.

---

### User Story 3 - Biết staging hỏng trước khi người dùng báo (Priority: P2)

DE nhận email khi staging không truy cập được, lỗi tăng vọt, máy sắp hết tài nguyên hoặc AI chậm / rơi vào phương án
dự phòng nhiều bất thường; mở một bảng theo dõi để xem tình trạng và log của từng service mà không phải SSH vào máy.

**Why this priority**: là S4-DE-4. Lúc demo và quay video ở S5, phát hiện sớm quan trọng hơn sửa nhanh; nhưng
staging vẫn dùng được khi chưa có phần này nên đứng sau US1, US2.

**Independent Test**: tắt một container trên staging; trong 5 phút có email cảnh báo; bật lại thì cảnh báo tự đóng.
Mở bảng theo dõi thấy CPU / RAM / đĩa của máy, tỉ lệ lỗi theo route và chỉ số AI.

**Acceptance Scenarios**:

1. **Given** health công khai không trả lời quá 2 phút, **When** kiểm tra định kỳ chạy, **Then** email cảnh báo gửi
   tới danh sách nhận và tự đóng khi health trở lại.
2. **Given** staging nhận traffic, **When** mở bảng theo dõi, **Then** thấy: tài nguyên máy (CPU, RAM, đĩa), số
   request / tỉ lệ lỗi 5xx / độ trễ p95 theo route, và chỉ số AI (thời gian ra chữ đầu tiên p95, tỉ lệ dùng phương án
   dự phòng theo agent, token theo ngày, lỗi / rỗng của truy hồi RAG).
3. **Given** log của mọi container, **When** tìm theo tên service và khoảng thời gian, **Then** thấy log dòng của
   service đó mà không cần SSH.
4. **Given** các ngưỡng cảnh báo đã đặt, **When** một ngưỡng bị vượt (bảng ngưỡng ở FR-016), **Then** có đúng một
   email cho sự cố đó, không lặp mỗi phút.

---

### User Story 4 - Không mất dữ liệu staging khi máy hỏng (Priority: P2)

Dữ liệu trên Postgres staging (tài khoản thử, phiên phỏng vấn demo khi có) được sao lưu hằng ngày ra ngoài máy; DE khôi
phục được vào một DB trống theo hướng dẫn.

**Why this priority**: một máy = một điểm chết. Dữ liệu demo S5 tạo bằng tay mất công; mất là phải làm lại trước hạn
nộp.

**Independent Test**: chờ (hoặc kích) một lần sao lưu, khôi phục bản đó vào một DB trống, đếm số bản ghi khớp với
nguồn.

**Acceptance Scenarios**:

1. **Given** staging chạy qua đêm, **When** tới giờ sao lưu, **Then** có một bản sao lưu mới của mọi DB của service
   lưu ngoài máy; bản cũ hơn 7 ngày tự xóa.
2. **Given** một bản sao lưu, **When** DE làm theo hướng dẫn khôi phục, **Then** DB trống nhận lại đủ dữ liệu.
3. **Given** sao lưu không chạy quá 24 giờ, **When** kiểm tra định kỳ, **Then** có email cảnh báo.

---

### User Story 5 - Thêm một service mới hoặc frontend vào staging (Priority: P3)

Khi FSD có service mới (`job-service`, `interview-service`) hoặc web frontend (013), người phụ trách đưa nó lên
staging bằng cách làm theo một danh sách bước cố định, không phải sửa logic của lệnh deploy.

**Why this priority**: các service này chưa tồn tại; chỉ cần quy trình sẵn sàng trước khi chúng xuất hiện.

**Independent Test**: dùng danh sách bước để đưa một service NestJS đang có (ví dụ `notification-service`) lên như
thể nó mới; đếm số file phải đổi và thời gian.

**Acceptance Scenarios**:

1. **Given** một service mới có Dockerfile và health endpoint, **When** làm theo danh sách bước, **Then** nó được
   build tự động, deploy cùng lệnh deploy chung, có route qua gateway, có trong giám sát và cảnh báo.
2. **Given** web frontend triển khai trên nền tảng frontend, **When** nó gọi `https://api.<domain>`, **Then** trình
   duyệt không chặn vì CORS hay nội dung lẫn http/https, cho cả domain chính và bản xem trước của PR.

---

### Edge Cases

- **Chưa có domain**: HTTPS cần tên miền. Tới khi mua, dùng tên miền suy ra từ IP tĩnh (dịch vụ wildcard DNS công
  khai kiểu `<ip>.sslip.io`) để có chứng chỉ thật; đổi sang `api.<domain>` chỉ bằng biến cấu hình.
- **Chứng chỉ không gia hạn được** (DNS sai, cổng 80 bị chặn): cảnh báo khi chứng chỉ còn < 14 ngày.
- **Stream bị gom**: gateway hoặc reverse proxy giữ toàn bộ phản hồi stream rồi mới trả → người dùng thấy câu hỏi
  hiện một lần sau nhiều giây; phải tắt gom cho route stream và kiểm bằng US1 kịch bản 2.
- **Đĩa đầy** do log hoặc image cũ: log container xoay vòng có giới hạn; image cũ dọn sau deploy, giữ phiên bản trước
  để quay lại; cảnh báo đĩa > 80%.
- **Kho `ai_db` dùng chung**: DE index lại kho dev thì staging thấy ngay (cùng kho); không có kho riêng cho staging.
  Supabase hỏng → ai-service vẫn khỏe (RAG là tùy chọn, health báo trong trường hợp `rag`), câu hỏi vẫn ra từ phương
  án dự phòng.
- **Nhà cung cấp LLM lỗi hoặc hết hạn mức**: ai-service dùng phương án dự phòng; tỉ lệ dự phòng > 20% kích cảnh báo.
- **Vòng lặp tốn token** (lỗi code gọi LLM liên tục): cảnh báo khi token/ngày gấp 3 trung bình 7 ngày.
- **Máy khởi động lại** (bảo trì của GCP): mọi container tự chạy lại; staging khỏe lại không cần người.
- **Secret bị lộ** (commit nhầm): quét secret trong CI chặn; nếu lộ thì đổi khóa, không chỉ xóa commit.
- **Deploy khi đang có phiên phỏng vấn**: phiên đang stream có thể bị cắt; chấp nhận ở staging, deploy ngoài giờ
  demo.
- **Service phụ thuộc chưa có** (ví dụ `interview-service` chưa tồn tại nên ai-service chỉ gọi trực tiếp): route
  gateway của service chưa có không được khai báo ở staging, tránh 502 rải rác.

## Requirements *(mandatory)*

### Functional Requirements

**Máy chủ và mạng**

- **FR-001**: Staging MUST chạy trên một máy chủ đặt ở khu vực Đông Nam Á, có IP tĩnh; tường lửa chỉ mở 80/443 ra
  Internet; truy cập quản trị (SSH) chỉ qua kênh có xác thực của nhà cung cấp, không mở cổng 22 công khai.
- **FR-002**: Cơ sở dữ liệu, cache, object storage, etcd, admin API của gateway, các trang quản trị (RedisInsight,
  trang chủ APISIX, console MinIO) MUST NOT truy cập được từ Internet; các thành phần chỉ dành cho dev MUST NOT chạy ở
  staging.
- **FR-003**: Mọi lưu lượng công khai MUST đi qua HTTPS với chứng chỉ hợp lệ tự gia hạn; http chuyển hướng sang
  https. Gateway (APISIX) vẫn là điểm vào duy nhất phía sau lớp TLS (constitution II).

**Đóng gói và chạy service**

- **FR-004**: `auth-service`, `user-service`, `notification-service` MUST có Dockerfile build nhiều tầng, chạy bằng
  user không phải root, và health endpoint kiểm phụ thuộc bắt buộc của chính nó (constitution: mọi service MUST có
  health endpoint).
- **FR-005**: Staging MUST có cấu hình compose riêng (kế thừa compose dev, không nhân bản toàn bộ): mọi service có
  health check, tự khởi động lại khi chết hoặc khi máy khởi động lại, log xoay vòng có giới hạn dung lượng.
- **FR-006**: Gateway MUST có cấu hình staging riêng (profile staging): chỉ khai báo route của service đang chạy;
  CORS cho phép domain frontend và bản xem trước của frontend; route stream của ai-service không gom phản hồi.
- **FR-007**: ai-service staging MUST đọc kho `ai_db` dùng chung bằng vai trò chỉ đọc (`aie_reader`), không có quyền
  ghi.

**Bí mật và cấu hình**

- **FR-008**: Bí mật staging (mật khẩu DB, khóa JWT, khóa LLM, khóa Langfuse, chuỗi kết nối `ai_db`) MUST NOT nằm
  trong git; repo có file mẫu liệt kê mọi biến với giá trị giữ chỗ; file thật chỉ nằm trên máy staging với quyền đọc
  giới hạn (hoặc trong kho bí mật của nhà cung cấp).
- **FR-009**: Đổi domain (từ tên suy ra IP sang `api.<domain>`) MUST chỉ cần đổi biến cấu hình, không sửa code.

**Build và deploy**

- **FR-010**: Khi `main` có commit mới và CI xanh, MUST tự build image của mọi service có Dockerfile, gắn nhãn theo mã
  commit và đẩy vào kho image riêng; CI xác thực với nhà cung cấp bằng danh tính liên kết, không lưu khóa dài hạn.
- **FR-011**: MUST có một lệnh deploy: nhận mã commit (mặc định bản mới nhất), kéo image, chạy migration của service
  có DB trước, khởi động lại service, chờ health xanh; lỗi bất kỳ → dừng, thoát khác 0, service chưa đổi giữ bản cũ.
- **FR-012**: MUST có một lệnh quay lại phiên bản đã deploy ngay trước đó; hệ thống MUST ghi lại phiên bản đang chạy và
  phiên bản trước.
- **FR-013**: Health của mỗi service MUST cho biết phiên bản (mã commit) đang chạy.

**Sao lưu**

- **FR-014**: Mọi DB của service trên Postgres staging MUST được sao lưu hằng ngày ra lưu trữ ngoài máy, giữ 7 bản gần
  nhất; đĩa máy chủ có ảnh chụp hằng ngày; có hướng dẫn khôi phục đã chạy thử ít nhất một lần.

**Giám sát và cảnh báo**

- **FR-015**: MUST thu về dịch vụ giám sát: tài nguyên máy (CPU, RAM, đĩa), log mọi container (tìm được theo service),
  metrics Prometheus của ai-service và của gateway; kiểm tra uptime định kỳ cho health công khai.
- **FR-016**: MUST có cảnh báo email (≤ 8 chính sách, mỗi sự cố một email, tự đóng khi hết):

  | # | Điều kiện | Ngưỡng mặc định |
  |---|---|---|
  | 1 | Health công khai không trả lời | > 2 phút |
  | 2 | Tỉ lệ 5xx tại gateway | > 5% trong 5 phút |
  | 3 | Thời gian ra chữ đầu tiên p95 của ai-service | > mốc trong `eval-261109-1648-ttft-breakdown` + 50% |
  | 4 | Tỉ lệ dùng phương án dự phòng của một agent | > 20% trong 15 phút |
  | 5 | Đĩa | > 80% |
  | 6 | Container khởi động lại lặp | ≥ 3 lần trong 10 phút |
  | 7 | Token LLM / ngày | gấp 3 trung bình 7 ngày (phát hiện vòng lặp, không phải ngân sách) |
  | 8 | Sao lưu quá hạn hoặc chứng chỉ sắp hết | sao lưu > 24 giờ; chứng chỉ < 14 ngày |

- **FR-017**: MUST có một bảng theo dõi gồm các nhóm ở US3 kịch bản 2.
- **FR-018**: Metrics MUST NOT gắn nhãn định danh phiên, người dùng hay nội dung (tránh nổ số chuỗi và lộ dữ liệu cá
  nhân); log MUST NOT ghi nội dung CV hay câu trả lời ứng viên ở mức log mặc định của staging.

**Thêm service**

- **FR-019**: MUST có danh sách bước "thêm service vào staging" (Dockerfile, health, khối compose, route gateway, biến
  mẫu, build CI, metrics / log / cảnh báo) và hướng dẫn nối web frontend vào `https://api.<domain>`; lệnh deploy MUST
  tự nhận service mới từ cấu hình, không sửa logic.

**Tài liệu**

- **FR-020**: MUST có hướng dẫn dựng staging từ máy trống tới health xanh, deploy, quay lại, khôi phục sao lưu, xử lý
  cảnh báo thường gặp; tạo `docs/deployment-guide.md` (chưa có, CLAUDE.md liệt kê trong cấu trúc `docs/`).

### Key Entities

- **Phiên bản deploy**: mã commit + thời điểm + người chạy + kết quả; giữ bản hiện tại và bản trước để quay lại.
- **Image service**: một image mỗi service mỗi commit, nằm trong kho image riêng của project.
- **Bản sao lưu**: một bản mỗi DB mỗi ngày, có thời điểm, dung lượng; vòng đời 7 ngày.
- **Chính sách cảnh báo**: điều kiện, ngưỡng, kênh email, trạng thái mở / đóng.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Một thành viên dựng lại staging từ máy trống tới mọi health xanh theo hướng dẫn trong ≤ 60 phút làm
  việc, không phải hỏi DE.
- **SC-002**: Từ lúc merge `main` tới lúc phiên bản mới chạy trên staging ≤ 15 phút, chỉ một lệnh tay; quay lại bản
  trước ≤ 5 phút.
- **SC-003**: Một phiên phỏng vấn AI đầy đủ chạy qua HTTPS công khai; thời gian ra chữ đầu tiên p95 trên staging
  không chậm hơn chạy trực tiếp ai-service trên cùng máy quá 300 ms (lớp TLS + gateway không gom stream).
- **SC-004**: 5 phiên phỏng vấn đồng thời chạy hết không lỗi; RAM và CPU máy trong lúc đó < 80%.
- **SC-005**: Khi một service ngừng, email cảnh báo tới trong ≤ 5 phút; 0 email lặp cho cùng sự cố.
- **SC-006**: Quét cổng từ ngoài chỉ thấy 80/443; quét secret trên repo không ra bí mật thật nào.
- **SC-007**: Khôi phục một bản sao lưu vào DB trống thành công (số bản ghi khớp nguồn); dữ liệu mất tối đa 24 giờ.
- **SC-008**: Đưa một service theo danh sách bước FR-019 lên staging trong ≤ 1 giờ, không sửa logic lệnh deploy.
- **SC-009**: Staging sẵn sàng (US1 + US2) trước 30/11/2026; giám sát + cảnh báo (US3) trước 03/12/2026.

## Assumptions

- GCP project và billing đã có (DE xác nhận 2026-11-19); DE có quyền tạo máy, IP tĩnh, kho image, bucket, cảnh báo.
- Domain chưa mua: dùng tên suy ra IP (Edge Cases) tới khi mua; mua trên Vercel cùng frontend (quyết định 11-17).
- Máy: 4 vCPU / 16 GB / SSD 100 GB (plan 1.3) đủ cho Postgres, Redis, MinIO, APISIX + etcd, ai-service, 3 service
  NestJS và các service FSD sắp có; SC-004 kiểm lại.
- Object storage staging dùng MinIO trên cùng máy (S3-compatible, constitution cho phép; chỉ đổi env nếu sau này
  chuyển sang dịch vụ lưu trữ của cloud).
- Kafka vẫn tắt như compose dev; không service nào trên `main` cần nó.
- Danh sách nhận email: DE; thêm thành viên khác bằng cấu hình.
- Langfuse tiếp tục dùng bản cloud như dev (khóa riêng cho staging nếu AIE muốn tách dữ liệu trace).
- Staging không có SLA; tắt máy để tiết kiệm không nằm trong phạm vi (ngân sách "không giới hạn", plan 11-17).
- Dữ liệu staging là dữ liệu thử / demo, không phải dữ liệu thật của người dùng.

## Phụ thuộc

- **FSD**: web frontend (013) và `job-service` / `interview-service` đi vào staging qua US5 khi có code; migration của
  `user-service` (và service sau) phải chạy được trên DB sạch (constitution VI).
- **AIE**: mốc TTFT cho cảnh báo #3 lấy từ báo cáo eval đã có; AIE xác nhận danh sách metrics AI trên bảng theo dõi.

## Ngoài phạm vi

- Seed dữ liệu staging (S4-DE-2 → 009 US4, chờ migration FSD).
- Eval hồi quy AI trong CI (plan 3.2) và đo trước / sau textbook (plan 3.1, AIE).
- Co giãn tự động, nhiều máy, Cloud Run / Kubernetes, môi trường production riêng.
- Tự dựng Prometheus / Grafana / ELK; metrics Postgres / Redis, phễu phiên phỏng vấn, Error Reporting (Stretch của
  S4-DE-4, chỉ làm khi phần bắt buộc xong).
- Voice mode (015).
