# Feature Specification: Staging Deploy & Monitoring

**Feature Branch**: `docs/staging-deploy-spec` (spec); branch code đặt ở plan (theo `docs/conventions.md`; thư mục spec
độc lập với branch)

**Created**: 2026-11-19 — **Updated**: 2026-11-28 (phạm vi mới sau #113: repo chỉ còn ai-service + voice-service +
data-pipeline; bỏ APISIX / NestJS / Redis / MinIO; image lên GHCR; host demo)

**Status**: Draft

**Owner**: DE — **Sprint**: 4 (23/11 → 07/12/2026); staging dùng tiếp cho Sprint 5 (E2E, báo cáo, 07/12 → 21/12)

**Covers**: S4-DE-3 (deploy staging, Bắt buộc), S4-DE-4 (monitoring, Stretch nhưng làm phần tối thiểu cùng deploy).
**Không** gồm S4-DE-2 (seed, đi theo 009 US4).

**Input**: User description: "Deploy staging S4-DE-3 + monitoring S4-DE-4 theo plan
`plans/261117-2137-devops-monitoring-eval/plan.md` Phase 1–2: một VM GCP chạy docker compose, TLS trước gateway,
giám sát và cảnh báo email bằng dịch vụ có sẵn của GCP; deploy những gì đã có trên `main` cộng cách thêm service sau."

**Nguồn thiết kế**: [plan 261117-2137](../../plans/261117-2137-devops-monitoring-eval/plan.md) Phase 1–2;
[constitution](../../.specify/memory/constitution.md) (Ràng buộc kỹ thuật & hạ tầng); `docker-compose.yml`;
[`docs/architecture/rag-design.md`](../../docs/architecture/rag-design.md) (kho `ai_db` dùng chung); spec 015
(voice-service, ADR-011). Spec chỉ ghi phần mới hoặc khác.

## Bối cảnh (kiểm tra 2026-11-28)

- **Chưa có môi trường chung nào ngoài máy dev.** Đề cương và sprint plan cam kết bản demo chạy trên cloud có HTTPS;
  Sprint 5 (E2E, quay demo, báo cáo) cần một địa chỉ cố định cả nhóm và GVHD mở được.
- **Repo này từ 2026-11-26 (#113)** chỉ còn `ai-service`, `voice-service`, `data-pipeline`. Nền tảng web (backend
  Express + MySQL, frontend Vite) của FSD nằm ở repo `hoangtunggg/final_recruitment_project` và FSD tự triển khai
  (compose + nginx riêng). APISIX, etcd, Redis, MinIO và 3 service NestJS đã bị gỡ khỏi repo này.
- **Đã có trên `main`**: ai-service (Dockerfile, `/api/health`, `/metrics`, token nội bộ fail-closed khi
  `APP_ENV=staging`, lưu phiên LangGraph `SESSION_STORE=memory|postgres`), voice-service (Dockerfile, health, token nội
  bộ fail-closed, key Blaze phía server). Compose dev ở gốc repo build từ source và mở cổng ra máy.
- **Bên gọi**: backend của FSD gọi ai-service và voice-service server-to-server (ADR-011), giữ hai token nội bộ. Tới
  2026-11-28 backend FSD chưa gọi ai-service; trang `/dev/interview` (PR #120) là giao diện phỏng vấn duy nhất có sẵn.
- **Kho RAG `ai_db`** nằm ở Supabase dùng chung (ngoài compose); ai-service staging đọc kho đó bằng vai trò chỉ đọc.
- **CI** hiện chỉ chạy pytest cho 3 app Python; chưa build image, chưa deploy.

## Quyết định (DE, 2026-11-17, 2026-11-19, 2026-11-28)

| Chủ đề | Chốt |
|---|---|
| Backend | Một VM Compute Engine (`asia-southeast1`) chạy Docker Compose; không tách Cloud Run trong S4 |
| Lớp vào | Caddy: TLS tự động + chọn upstream theo host; chỉ mở cổng 80/443. Không còn APISIX trong repo này |
| Host | `ai.<host>` → ai-service, `voice.<host>` → voice-service, `demo.<host>` → trang demo; `<host>` = `hireready.tuannm.app` (domain `tuannm.app` của DE, mua 2026-11-28; DNS: một bản ghi A wildcard `*.hireready` → IP tĩnh của VM) |
| Xác thực | Token nội bộ của từng service (header `X-Internal-Token`), chỉ backend FSD và Caddy (host demo) giữ; không JWT ở lớp vào |
| Rate limit | Theo người dùng: thuộc bên gọi (backend FSD); repo này không làm. Ghi là rủi ro (Edge Cases) |
| Lưu phiên | `SESSION_STORE=postgres` trên Postgres của VM (chỉ chứa checkpoint phiên); deploy lại không mất phiên |
| Host demo | Mở `/dev/interview` cho GVHD / mentor sau basic auth; Caddy gắn token phía server; chỉ các đường trang cần |
| Kho image | GHCR (`ghcr.io/minhtuann1102/ai-recruitment-platform/<service>`): CI đẩy bằng `GITHUB_TOKEN`, repo public → VM kéo không cần đăng nhập |
| Frontend | Thuộc FSD (repo riêng, Vercel); không nằm trong 014 |
| Giám sát | Dịch vụ có sẵn của GCP (agent trên VM → metrics + logs, uptime check, alert) thay vì tự dựng Prometheus / Grafana |
| Cảnh báo | Email |
| Ngân sách LLM | Không giới hạn cứng (vẫn tránh lãng phí) |
| Tài khoản | GCP project + billing đã có; domain `tuannm.app` (name.com, hạn 1 năm, gia hạn tay) |
| Ngoài phạm vi | Seed (S4-DE-2), eval hồi quy trong CI (plan 3.2), triển khai nền tảng web của FSD |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Staging chạy qua HTTPS với các service đang có (Priority: P1)

DE dựng một máy chủ staging, đưa ai-service và voice-service lên chạy sau Caddy, có HTTPS. Backend của FSD (ở bất kỳ
đâu) gọi được hai service bằng token nội bộ; GVHD / mentor mở được trang demo phỏng vấn bằng trình duyệt.

**Why this priority**: là cam kết Bắt buộc S4-DE-3 và điều kiện cho mọi việc sau (deploy tự động, giám sát, E2E ở
Sprint 5). Thiếu nó thì không có gì để demo.

**Independent Test**: từ một máy ngoài mạng nhóm, gọi health của hai service qua `https://ai.<host>` và
`https://voice.<host>`; với token nội bộ, chạy một phiên phỏng vấn AI đầy đủ (bắt đầu → vài lượt → kết thúc) và nhận
câu chữ dạng stream từng phần; cùng lời gọi đó không có token bị từ chối; mở `https://demo.<host>` bằng mật khẩu demo
và làm một phiên có giọng nói.

**Acceptance Scenarios**:

1. **Given** máy chủ staging mới dựng và file cấu hình bí mật đã đặt trên máy, **When** DE chạy lệnh khởi động
   staging, **Then** mọi service báo khỏe trong 5 phút và health công khai trả thành công qua HTTPS với chứng chỉ hợp
   lệ.
2. **Given** staging đang chạy, **When** bên gọi gọi một endpoint stream của ai-service qua HTTPS, **Then** phần chữ
   đầu tiên tới tay bên gọi ngay khi ai-service phát ra, không bị gom lại tới cuối.
3. **Given** staging đang chạy, **When** quét cổng IP công khai của máy từ bên ngoài, **Then** chỉ thấy cổng 80 và
   443; Postgres, `/metrics` và trang dev qua host API không truy cập được từ Internet.
4. **Given** một phiên phỏng vấn đang dở, **When** ai-service khởi động lại (deploy hoặc lỗi), **Then** lượt kế tiếp
   của phiên đó vẫn chạy tiếp (checkpoint trong Postgres).
5. **Given** host demo, **When** gọi mà không có mật khẩu demo hoặc gọi một đường ngoài danh sách trang cần, **Then**
   bị từ chối (401 / 404); trình duyệt không bao giờ nhận token nội bộ.

---

### User Story 2 - Deploy bản mới và quay lại bản cũ bằng một lệnh (Priority: P1)

Mỗi khi `main` có commit mới, bản build của từng service được tạo tự động và lưu ở kho image riêng. DE (hoặc thành viên
có quyền) đưa bản đó lên staging bằng một lệnh; nếu bản mới hỏng thì quay lại bản trước bằng một lệnh.

**Why this priority**: nhóm 3 người merge liên tục trong S4–S5; deploy tay từng bước dễ sai và tốn thời gian của DE.
Quay lại nhanh giữ cho staging luôn demo được.

**Independent Test**: merge một thay đổi nhỏ vào `main`, chờ build xong, chạy lệnh deploy, thấy phiên bản mới trong
health; chạy lệnh quay lại, thấy phiên bản cũ.

**Acceptance Scenarios**:

1. **Given** một commit mới trên `main` đã qua CI, **When** build tự động xong, **Then** GHCR có image của từng
   service, gắn nhãn theo mã commit, không cần khóa bí mật dài hạn nào lưu trong repo hay CI.
2. **Given** image mới đã có, **When** DE chạy lệnh deploy, **Then** staging kéo đúng phiên bản đó, tạo / nâng cấp
   bảng checkpoint phiên trước khi ai-service nhận traffic, và health cho thấy phiên bản mới.
3. **Given** bước tạo bảng checkpoint lỗi, **When** deploy, **Then** quá trình dừng, ai-service giữ phiên bản cũ đang
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

Dữ liệu trên Postgres staging (DB `ai_session`: checkpoint các phiên phỏng vấn demo) được sao lưu hằng ngày ra ngoài
máy; DE khôi phục được vào một DB trống theo hướng dẫn.

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

### User Story 5 - Nối backend FSD và thêm service mới (Priority: P3)

Backend của FSD (repo riêng, host riêng) gọi ai-service và voice-service trên staging theo một hướng dẫn cố định. Khi
repo này có service mới, người phụ trách đưa nó lên staging bằng một danh sách bước, không phải sửa logic lệnh deploy.

**Why this priority**: backend FSD chưa gọi ai-service; chỉ cần hướng dẫn và quy trình sẵn sàng trước khi họ nối.

**Independent Test**: làm theo hướng dẫn nối từ một máy ngoài (đóng vai backend FSD): đặt 2 URL + 2 token, gọi một
phiên phỏng vấn và một lần chuyển giọng nói thành chữ; dùng danh sách bước thêm service với `data-pipeline` (đóng vai
service mới, không cần chạy thật) và đếm số file phải đổi.

**Acceptance Scenarios**:

1. **Given** backend FSD có 2 URL + 2 token staging, **When** nó gọi ai-service / voice-service server-to-server,
   **Then** lời gọi thành công qua HTTPS; trình duyệt người dùng không gọi thẳng hai service (không cần CORS).
2. **Given** một service mới có Dockerfile và health endpoint, **When** làm theo danh sách bước, **Then** nó được
   build tự động, deploy cùng lệnh deploy chung, có host qua Caddy (nếu cần public), có trong giám sát và cảnh báo.

---

### Edge Cases

- **Domain là của cá nhân DE** (`tuannm.app`, dùng lại cho dự án khác): dự án nằm dưới `hireready.`; đổi domain
  (ví dụ sang domain riêng của sản phẩm) chỉ cần DNS + 3 biến host (FR-009). Domain hết hạn (tắt tự gia hạn) → staging
  mất HTTPS: gia hạn tay trước 11/2027. `.app` bắt buộc HTTPS ở trình duyệt (HSTS preload): mọi host phải có chứng chỉ
  (Caddy tự lấy Let's Encrypt), không có bản http.
- **Dự án khác dưới cùng `tuannm.app`** là cùng "site" với host demo: chặn CSRF theo `same-origin` (FR-006a).
- **Chứng chỉ không gia hạn được** (DNS sai, cổng 80 bị chặn): cảnh báo khi chứng chỉ còn < 14 ngày.
- **Stream bị gom**: reverse proxy (hoặc nén gzip) giữ toàn bộ phản hồi stream rồi mới trả → người dùng thấy câu hỏi
  hiện một lần sau nhiều giây; tắt gom và không nén trên host AI, kiểm bằng US1 kịch bản 2.
- **Đĩa đầy** do log hoặc image cũ: log container xoay vòng có giới hạn; image cũ dọn sau deploy, giữ phiên bản trước
  để quay lại; cảnh báo đĩa > 80%.
- **Postgres lưu phiên chết**: ai-service vẫn khỏe nhưng lượt cần đọc checkpoint trả 503
  `session_store_unavailable`; container Postgres tự chạy lại; cảnh báo #6.
- **Kho `ai_db` dùng chung**: DE index lại kho dev thì staging thấy ngay (cùng kho); không có kho riêng cho staging.
  Supabase hỏng → ai-service vẫn khỏe (RAG là tùy chọn, health báo trong trường hợp `rag`), câu hỏi vẫn ra từ phương
  án dự phòng.
- **Nhà cung cấp LLM lỗi hoặc hết hạn mức**: ai-service dùng phương án dự phòng; tỉ lệ dự phòng > 20% kích cảnh báo.
- **Vòng lặp tốn token** (lỗi code gọi LLM liên tục): cảnh báo khi token/ngày gấp 3 trung bình 7 ngày.
- **Máy khởi động lại** (bảo trì của GCP): mọi container tự chạy lại; staging khỏe lại không cần người.
- **Secret bị lộ** (commit nhầm): quét secret trong CI chặn; nếu lộ thì đổi khóa, không chỉ xóa commit.
- **Gọi LLM / Blaze ẩn danh**: URL staging công khai, ngân sách không giới hạn cứng → không có đường nào tới ai-service
  hay voice-service mà không có token nội bộ (trừ health); token chỉ nằm phía server.
- **Một người dùng gọi dồn dập** (rủi ro chấp nhận): lớp vào không có rate limit theo người dùng vì không biết người
  dùng là ai; backend FSD MUST tự giới hạn theo tài khoản trước khi gọi. Host demo không có giới hạn: mật khẩu demo chỉ
  đưa người được mời, đổi mật khẩu sau mỗi đợt demo; cảnh báo #7 (token / ngày) bắt trường hợp lạm dụng.
- **Lộ mật khẩu demo**: đổi hash trong `.env` rồi `docker compose up -d caddy` (`restart` không đọc lại `.env`); token nội bộ không lộ theo (Caddy gắn phía
  server).
- **Deploy khi đang có phiên phỏng vấn**: lượt đang stream có thể bị cắt; phiên vẫn đi tiếp ở lượt sau (checkpoint
  Postgres); deploy ngoài giờ demo.

## Requirements *(mandatory)*

### Functional Requirements

**Máy chủ và mạng**

- **FR-001**: Staging MUST chạy trên một máy chủ đặt ở khu vực Đông Nam Á, có IP tĩnh; tường lửa chỉ mở 80/443 ra
  Internet; truy cập quản trị (SSH) chỉ qua kênh có xác thực của nhà cung cấp, không mở cổng 22 công khai.
- **FR-002**: Postgres, `/metrics` của mọi service và trang dev qua host API MUST NOT truy cập được từ Internet; các
  thành phần chỉ dành cho dev (build từ source, cổng mở ra máy) MUST NOT chạy ở staging.
- **FR-003**: Mọi lưu lượng công khai MUST đi qua HTTPS với chứng chỉ hợp lệ tự gia hạn; http chuyển hướng sang
  https. Lớp vào (Caddy) chỉ kết thúc TLS và chọn upstream theo host; không xác thực thay service, trừ host demo
  (FR-006a).
- **FR-003a**: ai-service và voice-service staging MUST chạy chế độ bắt buộc token nội bộ (`APP_ENV=staging`: thiếu
  token → 503, sai token → 401). Token chỉ nằm ở backend FSD và Caddy (host demo), MUST NOT tới trình duyệt. Rate
  limit theo người dùng thuộc bên gọi (Quyết định).

**Đóng gói và chạy service**

- **FR-004**: ai-service và voice-service MUST có Dockerfile chỉ chép code chạy (không `.env`, không test), chạy bằng
  user không phải root, và image ai-service MUST chứa lệnh tạo bảng checkpoint phiên.
- **FR-005**: Staging MUST có file compose riêng chạy image từ kho (không build từ source); compose dev ở gốc repo
  không đổi. Service ứng dụng và DB có health check, mọi container chạy lâu dài tự khởi động lại khi chết hoặc khi máy khởi động lại, log xoay vòng có giới
  hạn dung lượng; biến dùng chung (token, `APP_ENV`, mật khẩu DB) đặt một chỗ và ghi đè file env của từng service.
- **FR-006**: Caddy MUST có 3 host: `ai.<host>` → ai-service (chặn `/dev/*`, `/metrics`; không gom, không nén stream),
  `voice.<host>` → voice-service (chặn `/metrics`; giới hạn thân request ≥ `VOICE_MAX_UPLOAD_MB` + phần multipart),
  `demo.<host>` (FR-006a).
- **FR-006a**: Host demo MUST đòi basic auth, chỉ chuyển các đường trang `/dev/interview` dùng (trang, file tĩnh,
  `/dev/voice/*`, `/api/start`, `/api/next-turn`, `/api/finalize`, `/api/cv/parse`, `/api/jd/parse`,
  `/api/stt/phrases`, `/api/health`), còn lại 404; Caddy gắn `X-Internal-Token` phía server, ghi đè giá trị client
  gửi. ai-service MUST có cờ bật trang dev ở `APP_ENV=staging` (mặc định tắt) — làm sau khi PR #120 merge.
- **FR-007**: ai-service staging MUST đọc kho `ai_db` dùng chung bằng vai trò chỉ đọc (`aie_reader`), không có quyền
  ghi; lưu phiên vào DB `ai_session` trên Postgres của VM (`SESSION_STORE=postgres`).

**Bí mật và cấu hình**

- **FR-008**: Bí mật staging (2 token nội bộ, mật khẩu DB, hash mật khẩu demo, khóa LLM, khóa Blaze, khóa Langfuse,
  chuỗi kết nối `ai_db`) MUST NOT nằm trong git; repo có file mẫu liệt kê mọi biến với giá trị giữ chỗ; file thật chỉ
  nằm trên máy staging với quyền đọc giới hạn.
- **FR-009**: Đổi tên host (ví dụ từ `hireready.tuannm.app` sang domain riêng của sản phẩm) MUST chỉ cần đổi biến cấu hình, không sửa code.

**Build và deploy**

- **FR-010**: Khi `main` có commit mới và CI xanh, MUST tự build image của mọi service có Dockerfile, gắn nhãn theo mã
  commit (và `main` cho bản mới nhất) và đẩy lên GHCR bằng `GITHUB_TOKEN` của workflow, không lưu khóa dài hạn. Package
  MUST để public (repo public) để VM kéo không cần đăng nhập.
- **FR-011**: MUST có một lệnh deploy: nhận mã commit (mặc định bản mới nhất), kéo image, tạo / nâng cấp bảng
  checkpoint phiên thành một bước riêng trước khi đụng tới service, khởi động lại service, chờ health xanh; lỗi bất kỳ → dừng, thoát khác 0, service chưa đổi
  giữ bản cũ.
- **FR-012**: MUST có một lệnh quay lại phiên bản đã deploy ngay trước đó; hệ thống MUST ghi lại phiên bản đang chạy và
  phiên bản trước.
- **FR-013**: Health của mỗi service MUST cho biết phiên bản (mã commit) đang chạy.

**Sao lưu**

- **FR-014**: DB `ai_session` trên Postgres staging MUST được sao lưu hằng ngày ra lưu trữ ngoài máy, giữ 7 bản gần
  nhất; đĩa máy chủ có ảnh chụp hằng ngày; có hướng dẫn khôi phục đã chạy thử ít nhất một lần.

**Giám sát và cảnh báo**

- **FR-015**: MUST thu về dịch vụ giám sát: tài nguyên máy (CPU, RAM, đĩa), log mọi container (tìm được theo service),
  metrics Prometheus của ai-service và voice-service (đọc trong mạng nội bộ); kiểm tra uptime định kỳ cho health công
  khai.
- **FR-016**: MUST có cảnh báo email (≤ 8 chính sách, mỗi sự cố một email, tự đóng khi hết):

  | # | Điều kiện | Ngưỡng mặc định |
  |---|---|---|
  | 1 | Health công khai không trả lời | > 2 phút |
  | 2 | Tỉ lệ 5xx của ai-service / voice-service (metrics service) | > 5% trong 5 phút |
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

- **FR-019**: MUST có danh sách bước "thêm service vào staging" (Dockerfile, health, khối compose, host Caddy nếu
  public, biến mẫu, build CI, metrics / log / cảnh báo) và hướng dẫn cho backend FSD (2 URL, 2 token, header, timeout
  stream, tự rate limit); lệnh deploy MUST tự nhận service mới từ cấu hình, không sửa logic.

**Tài liệu**

- **FR-020**: MUST có hướng dẫn dựng staging từ máy trống tới health xanh, deploy, quay lại, khôi phục sao lưu, xử lý
  cảnh báo thường gặp; tạo `docs/deployment-guide.md` (chưa có, CLAUDE.md liệt kê trong cấu trúc `docs/`).

### Key Entities

- **Phiên bản deploy**: mã commit + thời điểm + người chạy + kết quả; giữ bản hiện tại và bản trước để quay lại.
- **Image service**: một image mỗi service mỗi commit trên GHCR (public).
- **Bản sao lưu**: một bản mỗi DB mỗi ngày, có thời điểm, dung lượng; vòng đời 7 ngày.
- **Chính sách cảnh báo**: điều kiện, ngưỡng, kênh email, trạng thái mở / đóng.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Một thành viên dựng lại staging từ máy trống tới mọi health xanh theo hướng dẫn trong ≤ 60 phút làm
  việc, không phải hỏi DE.
- **SC-002**: Từ lúc merge `main` tới lúc phiên bản mới chạy trên staging ≤ 15 phút, chỉ một lệnh tay; quay lại bản
  trước ≤ 5 phút.
- **SC-003**: Một phiên phỏng vấn AI đầy đủ chạy qua HTTPS công khai; thời gian ra chữ đầu tiên p95 trên staging
  không chậm hơn chạy trực tiếp ai-service trên cùng máy quá 300 ms (lớp TLS không gom stream).
- **SC-004**: 5 phiên phỏng vấn đồng thời chạy hết không lỗi; RAM và CPU máy trong lúc đó < 80%.
- **SC-005**: Khi một service ngừng, email cảnh báo tới trong ≤ 5 phút; 0 email lặp cho cùng sự cố.
- **SC-006**: Quét cổng từ ngoài chỉ thấy 80/443; quét secret trên repo không ra bí mật thật nào.
- **SC-007**: Khôi phục một bản sao lưu vào DB trống thành công (số bản ghi khớp nguồn); dữ liệu mất tối đa 24 giờ.
- **SC-008**: Đưa một service theo danh sách bước FR-019 lên staging trong ≤ 1 giờ, không sửa logic lệnh deploy.
- **SC-009**: Staging sẵn sàng (US1) trước 30/11/2026; deploy một lệnh (US2) và giám sát + cảnh báo (US3) trước
  03/12/2026 (dời US2 từ 30/11 ngày 2026-11-28: spec phải làm lại phạm vi sau #113).

## Assumptions

- GCP project và billing đã có (DE xác nhận 2026-11-19); DE có quyền tạo máy, IP tĩnh, bucket, cảnh báo.
- Domain `tuannm.app` đã mua (2026-11-28); DE quản lý DNS ở name.com.
- Máy: 2 vCPU / 8 GB / SSD 50 GB (`e2-standard-2`) đủ cho Caddy, Postgres, ai-service (BM25 corpus trong RAM),
  voice-service; SC-004 kiểm lại, thiếu thì nâng `e2-standard-4` (chỉ đổi loại máy).
- Danh sách nhận email: DE; thêm thành viên khác bằng cấu hình.
- Langfuse tiếp tục dùng bản cloud như dev (khóa riêng cho staging nếu AIE muốn tách dữ liệu trace).
- Staging không có SLA; tắt máy để tiết kiệm không nằm trong phạm vi (ngân sách "không giới hạn", plan 11-17).
- Dữ liệu staging là dữ liệu thử / demo, không phải dữ liệu thật của người dùng.

## Phụ thuộc

- **FSD**: backend của họ gọi ai-service / voice-service bằng 2 URL + 2 token (US5), tự rate limit theo tài khoản; nginx
  của họ đang đặt `Permissions-Policy: microphone=()` → phải mở mic cho trang phỏng vấn giọng nói của họ (không chặn
  014, chặn chế độ giọng nói trên web FSD).
- **AIE**: mốc TTFT cho cảnh báo #3 lấy từ báo cáo eval đã có; AIE xác nhận danh sách metrics AI trên bảng theo dõi;
  review các thay đổi chạm ai-service: Dockerfile (chép lệnh tạo bảng checkpoint, user không phải root), FR-013
  (phiên bản trong `/api/health`), cờ trang dev ở staging (FR-006a).
- **PR #120** (`/dev/interview` + proxy `/dev/voice/*`) phải merge trước khi host demo có trang.

## Ngoài phạm vi

- Seed dữ liệu staging (S4-DE-2 → 009 US4, chờ DB phía FSD).
- Triển khai nền tảng web của FSD (backend, frontend, MySQL): FSD tự làm ở repo của họ.
- Rate limit theo người dùng ở lớp vào (thuộc bên gọi; Edge Cases).
- Eval hồi quy AI trong CI (plan 3.2) và đo trước / sau textbook (plan 3.1, AIE).
- Co giãn tự động, nhiều máy, Cloud Run / Kubernetes, môi trường production riêng.
- Tự dựng Prometheus / Grafana / ELK; metrics Postgres, phễu phiên phỏng vấn, Error Reporting (Stretch của
  S4-DE-4, chỉ làm khi phần bắt buộc xong).
