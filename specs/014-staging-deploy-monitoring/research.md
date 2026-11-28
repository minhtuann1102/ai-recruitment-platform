# Research: Staging Deploy & Monitoring

Kiểm trong repo ngày 2026-11-19 (branch `docs/staging-deploy-spec`, `main` = `b8493eb`). Mỗi mục: Decision /
Rationale / Alternatives.

## Cập nhật 2026-11-28 (thay R1, R4–R9; R2, R3, R10–R12 còn dùng trừ chỗ nhắc APISIX / NestJS / Redis / MinIO)

Kiểm trên `main` = `91ef5e5`. #113 gỡ APISIX, etcd, Redis, MinIO và 3 service NestJS khỏi repo; nền tảng web của FSD
ở repo riêng. Chạy thử compose staging trên máy (Docker Desktop, host `*.localhost`) ngày 2026-11-28.

- **U1. Lớp vào = Caddy, không APISIX** (thay R1, R5, R7). Decision: Caddy 2.10 image chính thức, 3 site theo host;
  không `encode` trên host có SSE; không đặt `flush_interval` (Caddy tự flush `text/event-stream` và body không có
  Content-Length; `-1` còn giữ request tới service khi client đóng tab → tốn credit LLM); tắt HTTP/3 (chỉ mở TCP 443). Rationale: chỉ còn 2 upstream gọi server-to-server; APISIX
  không thêm bảo vệ nào so với token nội bộ. Alternatives: dựng lại APISIX + etcd (thừa); nginx + certbot (gia hạn
  chứng chỉ phải tự lo).
- **U2. Host thay vì tiền tố đường** (thay R5). Decision: `ai.<host>`, `voice.<host>`, `demo.<host>`, `<host>` = `hireready.tuannm.app` (U10). Rationale: hai service đều có `/api/*`, theo host thì không phải viết
  lại đường. Alternatives: `/ai/*`, `/voice/*` + `uri strip` (mỗi client phải biết tiền tố).
- **U3. Xác thực = token nội bộ sẵn có** (thay R6). Decision: không JWT ở lớp vào; `APP_ENV=staging` ép trong compose
  nên hai service fail-closed; token đặt một chỗ (`.env` của compose) và đi vào service qua `environment:` (ghi đè
  `env_file`). Rate limit theo người dùng thuộc backend FSD. Rationale: bên gọi duy nhất là backend FSD; JWT người
  dùng không tới được repo này. Alternatives: Caddy + plugin `caddy-ratelimit` (image tự build; giới hạn theo IP vô
  nghĩa khi mọi lời gọi từ một backend).
- **U4. Host demo** (mới). Decision: basic auth (hash bcrypt trong `.env`, đặt trong nháy đơn vì có `$`), danh sách
  đường lấy từ các `fetch` trong `static/interview/*.js` của PR #120, `header_up X-Internal-Token` ghi đè giá trị client;
  `/` chuyển tới `/dev/interview`. ai-service cần cờ bật trang dev ở staging (đang trả 404 khi `APP_ENV` strict).
  Rationale: GVHD / mentor thử được giọng nói mà token không tới trình duyệt. Alternatives: không có demo (chỉ demo
  local); đưa token vào trang (lộ).
- **U5. Lưu phiên trên Postgres của VM** (mới). Decision: `postgres:16-alpine`, DB `ai_session`; service một lần
  `ai-session-setup` chạy `python -m scripts.setup_session_checkpoint_tables` (idempotent) và ai-service
  `depends_on: service_completed_successfully` → bảng có trước khi nhận traffic ở lần `up` đầu. Khi deploy thì không
  đủ: thử 2026-11-28 (review) cho thấy compose tạo lại container ai-service trước khi biết setup lỗi → bản cũ bị gỡ,
  bản mới nằm ở `Created`, host `ai.` 502. Nên lệnh deploy chạy `docker compose run --rm ai-session-setup` thành bước
  riêng sau `up -d db`, lỗi thì dừng trước `up -d` (ai-service cũ giữ nguyên). Dockerfile ai-service chép 2 file `scripts/` cần. Rationale: `SESSION_STORE=memory` mất phiên mỗi lần deploy;
  Supabase thêm độ trễ mạng mỗi lượt. Alternatives: Supabase schema riêng; memory.
- **U6. Kho image = GHCR** (thay R9 phần Artifact Registry + WIF). Decision: `ghcr.io/minhtuann1102/ai-recruitment-platform/<service>:<sha>` + tag
  `main`; đẩy bằng `GITHUB_TOKEN` (`permissions: packages: write`); package để public → VM kéo không cần đăng nhập.
  Package mới trên GHCR có thể mặc định private: sau lần đẩy đầu, thử `docker pull` ẩn danh; không được thì đổi
  visibility một lần. Rationale: không cần WIF / service account cho CI, không khóa dài hạn, miễn phí cho repo public.
  Alternatives: Artifact Registry + WIF (dựng lâu hơn, VM kéo bằng SA); Docker Hub (thêm tài khoản + token, giới hạn
  pull).
- **U7. Compose staging là file riêng** (thay R4). Decision: `infra/staging/docker-compose.staging.yml` chỉ chạy image,
  không `extends` compose dev. Rationale: compose dev build từ source và mở cổng `8000`, `5534`; gộp file thì danh sách
  `ports` cộng dồn, phải dùng `!reset` dễ sai. Alternatives: override + `!reset`.
- **U8. Máy nhỏ hơn** (sửa R3). `e2-standard-2` (2 vCPU / 8 GB) thay `e2-standard-4`: không còn APISIX, etcd, Redis,
  MinIO, NestJS.
- **U9. Kết quả chạy thử trên máy (T006, 2026-11-28)**, Docker Desktop, image build từ branch, agent mock, RAG tắt,
  host `*.localhost` cổng 8443:
  - `docker compose config` đạt; Caddy nạp Caddyfile, tự cấp chứng chỉ nội bộ cho `*.localhost`.
  - Chỉ Caddy publish cổng; `db`, `ai-service`, `voice-service` chỉ có cổng trong mạng nội bộ.
  - Mã trả về khớp bảng [staging-hosts](contracts/staging-hosts.md): health 200 ×2; `/api/start` không / sai token 401;
    voice `/api/voice/speak` không token 401; `/metrics` ×2 và `ai./dev/play` 404; demo không mật khẩu 401; demo có mật khẩu:
    `/api/health` 200, `/docs` 404, `/` 302; `/dev/interview` và `/dev/voice/health` 404 vì `main` chưa có PR #120.
  - Host demo không gửi token vẫn chạy `/api/start` + `/api/next-turn` 200 → Caddy gắn token đúng.
  - SSE qua Caddy ra từng phần (`MOCK_STREAM_DELAY_MS=300`: token cách nhau ~0,25 s, không dồn cuối).
  - `ai-session-setup` in `session checkpoint tables ready`, thoát 0; ai-service log `session_store kind=postgres`.
  - `docker compose restart ai-service` giữa phiên → lượt 2 vẫn 200; bảng `checkpoints` có 3 dòng cho phiên thử.
  - Chạy lại sau review (bỏ `flush_interval`, chặn CSRF, tắt HTTP/3): mã trả về như trên; SSE vẫn ra từng phần;
    demo `POST` có `Sec-Fetch-Site` `cross-site` / `same-site` → 403, `GET` cross-site → 200, `POST` same-origin và
    không header → tới ai-service.
- **U10. Domain riêng thay sslip.io** (2026-11-28). sslip.io không nằm trong Public Suffix List → hạn mức Let's
  Encrypt dùng chung với mọi người dùng sslip.io (dễ bị từ chối) và mọi `*.sslip.io` cùng "site". DE mua `tuannm.app`
  (domain cá nhân, dùng lại cho dự án khác); dự án dùng `hireready.tuannm.app`: `ai.`, `voice.`, `demo.` + một bản ghi
  A wildcard `*.hireready`. Chặn CSRF vẫn theo `same-origin` vì dự án khác dưới `tuannm.app` cũng cùng "site". R2 chỉ
  còn là lịch sử.

## R1. Lớp TLS trước APISIX (thay bởi U1)

- **Decision**: Caddy 2 (container) nghe 80/443, tự lấy và gia hạn chứng chỉ Let's Encrypt, `reverse_proxy` toàn bộ
  sang `apisix:9080`. Caddyfile chỉ có một site block, không route, không auth, không header nghiệp vụ (ngoài
  `X-Forwarded-*` mặc định).
- **Rationale**: APISIX tự lấy chứng chỉ ACME cần plugin / quy trình riêng (không có sẵn trong bản đang dùng); Caddy
  làm đúng một việc, cấu hình vài dòng. Caddy tự flush khi phản hồi là `text/event-stream`, không gom stream.
- **Constitution II** ("APISIX là entry point public duy nhất"): Caddy là lớp TLS trong suốt, không phải gateway thứ
  hai — ghi ở Complexity Tracking.
- **Alternatives**: APISIX + cert thủ công (certbot cron + nạp SSL qua admin API): nhiều bước, dễ quên gia hạn.
  Load balancer HTTPS của GCP + chứng chỉ managed: tốn thêm tiền, cần domain thật, thêm thành phần.

## R2. Tên miền khi chưa mua domain (thay bởi U10)

- **Decision**: biến `STAGING_API_HOST`; tới khi mua domain đặt `api.<IP-gạch-ngang>.sslip.io` (sslip.io trả về IP
  nhúng trong tên). Mua domain → đổi biến thành `api.<domain>`, thêm bản ghi `A api` trong Vercel DNS, Caddy tự lấy
  chứng chỉ mới.
- **Chưa kiểm chứng**: Let's Encrypt tính hạn mức theo "registered domain" dựa trên Public Suffix List; nếu sslip.io
  không nằm trong PSL thì mọi người dùng sslip.io chung một hạn mức 50 chứng chỉ / 7 ngày và có thể bị từ chối
  ([LE rate limits](https://letsencrypt.org/docs/rate-limits/)). Kiểm ở bước dựng máy bằng ACME staging của LE trước.
- **Fallback**: mua domain ngay (rẻ, đằng nào cũng mua cho Vercel); không dùng chứng chỉ tự ký (trình duyệt và Vercel
  frontend chặn).
- **Alternatives**: chứng chỉ cho địa chỉ IP (LE có hỗ trợ, đời ngắn): phụ thuộc phiên bản Caddy, bỏ.

## R3. Máy chủ và hạ tầng GCP

- **Decision**: Compute Engine `e2-standard-4` (4 vCPU / 16 GB), Ubuntu 24.04 LTS, SSD 100 GB, `asia-southeast1-b`,
  IP tĩnh. Firewall: 80/443 từ `0.0.0.0/0`; 22 chỉ từ dải IAP `35.235.240.0/20`. Service account riêng cho VM: đọc
  Artifact Registry, ghi bucket sao lưu, ghi log / metrics. Dựng bằng script `gcloud` có thể chạy lại (kiểm tồn tại
  trước khi tạo), không Terraform.
- **Rationale**: theo plan 11-17; script gcloud đủ cho một máy, không thêm công cụ cho nhóm 3 người (constitution VII).
- **Alternatives**: Terraform (thêm state, học thêm), Cloud Run (đã loại 11-19).

## R4. Compose staging (thay bởi U7)

- **Decision**: file riêng `infra/staging/docker-compose.staging.yml`; hạ tầng dùng `extends` từ `docker-compose.yml`
  (db, redis, minio, storage-init, etcd, apisix) rồi thêm `restart: unless-stopped`, `logging` json-file
  (`max-size: 10m`, `max-file: 3`), healthcheck; service ứng dụng chạy image từ Artifact Registry
  (`${REGISTRY}/<service>:${APP_VERSION}`), không `build`. Không publish cổng nào ra host trừ Caddy 80/443. Không có
  redisinsight, apisix-homepage, kafka. ADC chạy như job một lần trong lệnh deploy.
- **Rationale**: không đổi hành vi `docker compose up` của dev; một nguồn cho định nghĩa hạ tầng (DRY).
- **Alternatives**: profiles trong compose dev (đổi thói quen dev, dễ quên `--profile`); file override `-f a -f b`
  (không gỡ được service dev-only).

## R5. Gateway profile staging (thay bởi U1, U2)

- Hiện trạng: APISIX `traditional` + etcd, route khai báo trong `config/apisix/conf/apisix-<profile>.yaml` và đồng bộ
  bằng ADC (thay `${VAR}` từ env); một consumer `auth` dùng chung (`jwt-auth`, `key: ai-agent`, secret `JWT_SECRET`);
  CORS global `allow_origins: '*'`; admin `allow_admin: 0.0.0.0/0`, admin UI bật.
- **Decision** (`APISIX_PROFILE=staging`):
  - `config-staging.yaml`: admin UI tắt, `allow_admin` chỉ dải mạng docker nội bộ, cổng 9180 không publish;
    `nginx_config.http.real_ip_header: X-Forwarded-For` + `real_ip_from` = dải mạng docker (để thấy IP thật sau Caddy).
  - `apisix-staging.yaml`: chép từ dev, bỏ route homepage và route của service chưa có (job, interview); CORS
    `allow_origins_by_regex` cho `https://app.<domain>` và `https://<project>-*.vercel.app`, `allow_credential` theo
    nhu cầu frontend (mặc định false).
- **Rationale**: FR-002, FR-006; giữ cơ chế profile sẵn có.

## R6. Bảo vệ đường tới ai-service (FR-003a) (thay bởi U3)

- Hiện trạng: route `/ai/*` đã bắt `jwt-auth`, riêng `/ai/api/health` mở. ai-service có middleware token nội bộ
  (`X-Internal-Token`), `APP_ENV=staging` thiếu token → 503 (fail closed); `/dev/play` tự 404 ở staging. `/metrics`
  **không** nằm trong `OPEN_PATHS` → cũng đòi token.
- **Decision**:
  - Route `/ai/*` staging thêm `proxy-rewrite.headers.set.X-Internal-Token: ${AI_SERVICE_INTERNAL_TOKEN}` — gateway
    ghi đè (client gửi header này cũng bị thay), token không bao giờ trong phản hồi.
  - Chặn tại gateway: `/ai/metrics`, `/ai/dev/*`, `/ai/docs`, `/ai/openapi.json` (route trả 404, priority cao hơn).
  - Giới hạn tốc độ: `limit-count` theo `remote_addr` (IP thật nhờ R5): `/ai/api/start` + `/ai/api/cv/parse` +
    `/ai/api/jd/parse` 10 / phút; `/ai/api/next-turn` + `/ai/api/finalize` 60 / phút; vượt → 429. Một consumer dùng
    chung nên không giới hạn theo consumer được.
  - Ops Agent lấy `/metrics` trực tiếp `ai-service:8000` trong mạng docker → cần ai-service cho `/metrics` qua không
    token (thêm vào `OPEN_PATHS`; cổng 8000 không publish nên chỉ mạng nội bộ thấy). Thay đổi code của AIE.
- **Hệ quả**: khi `interview-service` có, route AI công khai nên thu về chỉ cho service đó gọi (ghi ở contract gateway).
- **Alternatives**: browser gửi token nội bộ (lộ bí mật, loại); thêm consumer per user (auth-service không phát hành
  theo consumer, ngoài phạm vi).

## R7. Stream (SSE) qua Caddy + APISIX (thay bởi U1)

- ai-service đã trả `X-Accel-Buffering: no` + `Cache-Control: no-cache` → nginx của APISIX không gom; Caddy flush
  ngay với `text/event-stream`.
- Upstream `ai-upstream` hiện `timeout.read: 30` giây: lượt sinh dài có thể bị cắt. **Decision**: staging đặt
  `read: 120`, `send: 30`, `connect: 6`. Kiểm bằng SC-003 (đo TTFT qua gateway vs trực tiếp).

## R8. Đóng gói NestJS (FR-004) (bỏ: NestJS đã gỡ)

- Hiện trạng: `auth-service` (Redis, không DB), `user-service` (MikroORM + Redis, migration TS ở
  `src/database/migrations`), `notification-service` (Redis + BullMQ). Không có health, không terminus. Kafka đã
  comment; user / notification vẫn `connectMicroservice(grpcConfig)` (đồ thừa starter, khác ADR-003 — việc của FSD;
  staging chỉ cần cổng gRPC nằm trong mạng nội bộ).
- **Decision**:
  - Một Dockerfile mẫu dùng chung tham số `SERVICE` (`.docker/node-service.Dockerfile`): `turbo prune @ai-recruit/<svc>
    --docker` → `pnpm install --frozen-lockfile` → `turbo run build --filter` → stage `runtime` (node:22-slim, user
    `node`, chỉ deps prod + `dist`); stage `migrator` (giữ deps dev để chạy `mikro-orm migration:up`) chỉ build cho
    service có DB.
  - Health: `HealthModule` dùng chung trong `libs/core` (không thêm terminus): `GET /health` → `{status, version,
    checks: {db?, redis?}}`, 503 khi phụ thuộc bắt buộc lỗi; mỗi service import và khai báo phụ thuộc của nó; route
    APISIX public `/<svc>/health` không JWT.
- **Cần kiểm trước khi viết migrator**: `user-service` đặt `mikro-orm.useTsNode: false`, `configPaths` gồm
  `mikro-orm.config.ts` rồi `dist/mikro-orm.config.js`; migration là file TS ở `src/database/migrations`. Chạy
  `pnpm --filter @ai-recruit/user-service migration:up` trên DB sạch để biết CLI đang nạp TS bằng gì (MikroORM 7 + `tsx`
  ở root, hay bản JS trong `dist`). Stage `migrator` theo đúng cách đó (giữ `tsx` hoặc build migration ra `dist`).
- **Owner**: code trong `apps/*-service` và `libs/core` là của FSD → DE mở PR, FSD review (hỏi trước khi làm).
- **Alternatives**: một Dockerfile mỗi service (lặp, DRY); `@nestjs/terminus` (thêm dependency cho 2 check đơn giản).

## R9. Build và deploy (FR-010–FR-013) (kho image thay bởi U6; bước setup theo U5)

- **Build**: workflow `build-images.yml`, chạy khi push `main` (sau job CI xanh, `workflow_run`), matrix service có
  Dockerfile; xác thực GCP bằng Workload Identity Federation (`google-github-actions/auth`, provider giới hạn repo
  `minhtuann1102/ai-recruitment-platform` + ref `main`); đẩy `asia-southeast1-docker.pkg.dev/<project>/ai-recruit/
  <service>:<sha>`. Image nhận `APP_VERSION=<sha>` qua build-arg.
- **Deploy**: `infra/staging/scripts/deploy.sh [sha]` chạy ở máy DE → `gcloud compute ssh --tunnel-through-iap` →
  `/opt/ai-recruit/bin/deploy-on-vm.sh <sha>` trên VM: kiểm image tồn tại → `pull` → chạy migrator (lỗi → dừng, thoát
  1) → `up -d` từng service → chờ health (≤ 5 phút) → ghi `deploy-state.json` (current / previous) → `docker image
  prune` giữ 2 bản. ADC sync route sau khi APISIX khỏe.
- **Rollback**: `rollback.sh` = `deploy-on-vm.sh <previous>` không chạy migrator (migration chỉ thêm, không down
  tự động; cần down thì làm tay theo hướng dẫn).
- **Version**: env `APP_VERSION` vào mọi container; NestJS health trả `version`; ai-service health thêm trường
  `build` (giữ `version` = model hiện có để không vỡ contract) — thay đổi code AIE.
- **Alternatives**: deploy tự động khi merge (rủi ro lúc demo; spec chọn một lệnh tay); GitHub Actions SSH bằng khóa
  (khóa dài hạn, loại).

## R10. Bí mật (FR-008)

- **Decision**: `infra/staging/.env.staging.example` trong git (placeholder); file thật `/opt/ai-recruit/.env` trên
  VM, `chmod 600`, chủ `root`. Secret Manager không dùng ở S4 (thêm bước, lợi ích nhỏ với một máy). CI thêm bước quét
  secret (gitleaks) cho PR.
- `AI_DB_URL` dùng role `aie_reader` (chỉ đọc) của Supabase — FR-007.

## R11. Sao lưu (FR-014)

- **Decision**: cron 02:00 (giờ VN) trên VM chạy `backup-postgres.sh`: `pg_dump -Fc` từng DB của service (hiện
  `user_db`; tự lấy danh sách DB trừ template / postgres) qua `docker exec` → `gcloud storage cp` lên
  `gs://<project>-staging-backup/pg/<db>/<date>.dump`; bucket lifecycle xóa sau 7 ngày; ghi metric "lần sao lưu cuối"
  bằng log có cấu trúc (`backup_ok db=… size=…`) để cảnh báo #8 dùng log-based metric. Snapshot schedule hằng ngày
  cho đĩa, giữ 7 ngày. `restore-postgres.sh <db> <date>` khôi phục vào DB trống.

## R12. Giám sát và cảnh báo (FR-015–FR-018)

- **Decision**: Ops Agent trên VM; cấu hình `infra/staging/monitoring/ops-agent.yaml`: receiver `hostmetrics`;
  receiver `prometheus` scrape ai-service `/metrics` và APISIX `/apisix/prometheus/metrics` (bật plugin `prometheus`
  global). Ops Agent chạy trên host nên scrape qua cổng chỉ bind `127.0.0.1` (`127.0.0.1:18000→8000`,
  `127.0.0.1:19091→9091`), không ra Internet. APISIX mặc định export ở `127.0.0.1:9091` **trong** container → đặt
  `plugin_attr.prometheus.export_addr.ip: 0.0.0.0` trong `config-staging.yaml` thì ánh xạ cổng mới tới được.
- **Log theo tên service** (FR-015, US3 kịch bản 3): file json-file của Docker mang id container, không mang tên. Chọn
  log driver `json-file` + `labels: com.docker.compose.service` (Docker ghi nhãn vào mỗi dòng `attrs`) rồi Ops Agent
  receiver `files` (`/var/lib/docker/containers/*/*-json.log`) + processor `parse_json` để đưa `attrs` thành nhãn.
  **Kiểm ở Đợt D**; không được thì dùng driver `gcplogs` (gửi thẳng Cloud Logging, có tên container, nhưng mất
  `docker logs` tại máy → chỉ dùng nếu cách đầu hỏng).
- **Container restart lặp** (cảnh báo #6): daemon không ghi log restart ổn định → cron mỗi phút đọc
  `docker inspect -f '{{.Name}} {{.RestartCount}}'`, ghi dòng log có cấu trúc `container_restarts name=… count=…`
  → log-based metric (cùng kiểu với sao lưu ở R11).
- Uptime check: `https://${STAGING_API_HOST}/ai/api/health` 1 phút / 3 vùng; check chứng chỉ có sẵn trong uptime.
- Cảnh báo: 8 chính sách JSON trong `infra/staging/monitoring/alerts/`, áp bằng `apply-monitoring.sh`
  (`gcloud monitoring policies create/update` theo `displayName`); kênh email. Dashboard JSON
  (`dashboard-staging.json`). Container restart lặp: log-based metric từ log Docker daemon / sự kiện `restart`.
  Token / ngày: metric token của ai-service. Mốc TTFT p95: lấy từ
  `plans/reports/eval-261109-1648-ttft-breakdown.md` (+ 50%).
- **Alternatives**: Prometheus + Grafana + Alertmanager tự dựng (thêm 3 container, tự lo lưu trữ / email) — loại theo
  quyết định 11-17.

## R13. Thứ tự làm và voice (015)

- US1 + US2 trước (≈ 23/11 → 28/11), cùng lúc bật uptime check + cảnh báo #1 (rẻ, bảo vệ demo). Sau đó US4, rồi
  phần còn lại của US3 và US5. S4-DE-4 (monitoring) và S4-DE-5 (voice) đều là Stretch: khi US1 + US2 xong, voice có
  thể bắt đầu song song với phần giám sát còn lại.

## Câu hỏi còn mở (không chặn tasks)

1. ~~FSD đồng ý Dockerfile / `HealthModule`~~ (bỏ: NestJS đã gỡ). AIE đồng ý trường `build` ở health, cờ trang dev ở
   staging, Dockerfile chép `scripts/` + user không phải root? (`/metrics` không cần vào `OPEN_PATHS`: Ops Agent đọc
   trong mạng nội bộ có gửi token, hoặc giữ như hiện tại.)
2. ~~sslip.io có lấy được chứng chỉ LE không~~ (bỏ: đã mua `tuannm.app`, U10).
3. Danh sách email nhận cảnh báo ngoài DE.
4. Constitution II còn ghi APISIX là điểm vào duy nhất: sửa ở PR riêng (`/speckit-constitution`).
