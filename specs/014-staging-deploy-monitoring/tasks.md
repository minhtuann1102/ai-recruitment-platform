# Tasks: Staging Deploy & Monitoring (014)

**Input**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md) (mục "Cập nhật 2026-11-28"),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Phạm vi** (2026-11-28): một VM GCP chạy Caddy + ai-service + voice-service + Postgres (`ai_session`, lưu phiên);
image trên GHCR; 3 host `ai.` / `voice.` / `demo.`. Code staging ở `infra/staging/`; VM giữ bản sao ở `/opt/ai-recruit`.

**Tests**: pytest cho mọi thay đổi code Python (constitution VI); script Bash qua `shellcheck`; hạ tầng kiểm theo
quickstart trên máy (`*.localhost`) rồi trên staging thật. Sửa ai-service → AIE review trong PR.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: chạy song song được (khác file, không phụ thuộc task chưa xong)
- **[Story]**: US1–US5 theo spec.md

---

## Phase 1: Setup (compose staging, chạy được trên máy)

- [x] T001 Tạo `infra/staging/docker-compose.staging.yml`: `caddy` (cổng `${HTTP_PORT:-80}`/`${HTTPS_PORT:-443}`
  duy nhất publish), `db` (`postgres:16-alpine`, DB `ai_session`, không cổng), `ai-session-setup` (chạy
  `python -m scripts.setup_session_checkpoint_tables` một lần), `ai-service` (`depends_on` setup
  `service_completed_successfully`), `voice-service`; image `${IMAGE_REGISTRY}/<service>:${IMAGE_TAG}`; `environment:`
  ép `APP_ENV=staging`, 2 token, `SESSION_STORE=postgres`, `SESSION_DB_URL`, `VOICE_SERVICE_URL`; `restart:
  unless-stopped`; log `json-file` 10 MB × 5
- [x] T002 [P] Tạo `infra/staging/Caddyfile` theo [contracts/staging-hosts.md](contracts/staging-hosts.md): 3 host,
  không `encode`, không `flush_interval`, HTTP/3 tắt, chặn `/dev/*` + `/metrics` (ai), `/metrics` (voice), body ≤ 12 MB, host demo
  basic auth + chặn request ghi không same-origin (CSRF) + `header_up X-Internal-Token` + bỏ
  `Authorization` + danh sách đường, còn lại 404
- [x] T003 [P] Tạo `infra/staging/.env.staging.example` (mọi biến của compose, giữ chỗ; hash bcrypt trong nháy đơn)
- [x] T004 [P] `.gitignore`: thêm `infra/staging/env/` (env thật của từng service trên VM)
- [x] T005 [P] `apps/ai-service/Dockerfile`: `COPY scripts/__init__.py scripts/setup_session_checkpoint_tables.py
  ./scripts/` (AIE review)
- [x] T006 Chạy thử trên máy theo quickstart §0: build 2 image tag `local`, `infra/staging/.env` với host `*.localhost`
  + agent mock, `env/*.env` tối thiểu; kiểm `docker compose config`, `caddy validate`, mã trả về ở bảng staging-hosts,
  SSE ra từng phần (`MOCK_STREAM_DELAY_MS=300`, `curl -N`), `ai-session-setup` thoát 0, log `session_store
  kind=postgres`, phiên đi tiếp sau `docker compose restart ai-service`; ghi kết quả ngắn vào research.md (mục U)

**Checkpoint**: compose staging chạy đúng trên máy, chưa đụng cloud.

---

## Phase 2: Foundational (chặn mọi story trên cloud)

- [x] T007 [P] `apps/ai-service/Dockerfile` + `apps/voice-service/Dockerfile`: tạo user không phải root (`useradd
  --uid 10001`), `USER` trước `CMD`; `ARG APP_VERSION=dev` → `ENV APP_VERSION=$APP_VERSION`; kiểm `docker run --rm
  <img> id -u` ≠ 0 (AIE review phần ai-service)
- [ ] T008 [P] ai-service `/api/health` thêm `build` = `APP_VERSION` (mặc định `"dev"`), giữ nguyên `version` và các
  trường cũ, trong `apps/ai-service/app/main.py`; test trong `apps/ai-service/tests/`; cập nhật contract health của
  ai-service ở `docs/ai-service/06-api-contract.md` (AIE review)
- [ ] T009 [P] voice-service `/api/health` thêm `build` trong `apps/voice-service/app/` + test; ghi vào
  `specs/015-voice-mode/contracts/voice-service-api.md`
- [x] T010 Tạo `.github/workflows/build-images.yml`: chạy khi workflow `CI` trên `main` xong và xanh
  (`workflow_run`, `conclusion == success`) + `workflow_dispatch`; `permissions: contents: read, packages: write`;
  matrix `ai-service`, `voice-service`; `docker/login-action` với `GITHUB_TOKEN`; `docker/build-push-action` context
  `apps/<service>`, `build-args: APP_VERSION=<sha>`, tag `ghcr.io/minhtuann1102/ai-recruitment-platform/<service>:<sha>`
  + `:main`
- [ ] T011 Sau lần chạy đầu của T010: `docker logout ghcr.io; docker pull ghcr.io/.../ai-service:main` ẩn danh; lỗi
  thì đổi visibility 2 package sang public trên GitHub (Package settings), ghi bước này vào `docs/deployment-guide.md`
- [ ] T012 [P] `.github/workflows/ci.yml`: thêm job `gitleaks` (`gitleaks/gitleaks-action`, quét toàn repo; SC-006)
- [x] T013 [P] `infra/staging/scripts/provision-gcp.sh` theo [contracts/staging-cli.md](contracts/staging-cli.md):
  bật API, IP tĩnh, firewall 80/443 + 22 chỉ từ dải IAP `35.235.240.0/20`, SA của VM (logging.logWriter,
  monitoring.metricWriter, ghi bucket sao lưu), bucket + lifecycle 7 ngày, snapshot schedule hằng ngày, VM
  `e2-standard-2` Ubuntu 24.04 `asia-southeast1-b` 50 GB; tài nguyên đã có → in "exists"
- [ ] T014 [P] `infra/staging/scripts/bootstrap-vm.sh`: cài Docker Engine + Compose plugin, Ops Agent; tạo
  `/opt/ai-recruit/{env,state}` quyền 700; idempotent

**Checkpoint**: image tự lên GHCR khi `main` xanh; có script dựng máy.

---

## Phase 3: User Story 1 — Staging chạy qua HTTPS (P1) 🎯 MVP

**Goal**: ai-service + voice-service chạy sau Caddy, HTTPS hợp lệ, chỉ 80/443 mở; host demo cho GVHD / mentor.

**Independent Test**: quickstart §1–§3 từ một máy ngoài mạng nhóm.

- [ ] T015 [US1] Chạy `provision-gcp.sh` (2 lần, lần 2 toàn "exists") + `bootstrap-vm.sh` qua IAP; ghi IP tĩnh vào
  `infra/staging/.staging.local` (không commit)
- [ ] T016 [US1] Deploy tay lần đầu: chép `docker-compose.staging.yml`, `Caddyfile` vào `/opt/ai-recruit`; tạo `.env`
  (host `ai.hireready.tuannm.app` …, token `openssl rand -hex 32`, `IMAGE_TAG` = sha của T010) và `env/ai-service.env`,
  `env/voice-service.env` (key LLM, `AGENT_<agent>_MODE=llm` theo danh sách AIE chốt — mặc định là mock, Langfuse,
  `AI_DB_URL` role `aie_reader`, Blaze), `chmod 600`; `docker compose up
  -d`
- [ ] T017 [US1] DNS ở name.com: bản ghi A `*.hireready` (domain `tuannm.app`) → IP tĩnh của T015, TTL 300; chờ
  `nslookup ai.hireready.tuannm.app` ra IP rồi mới `up` (Let's Encrypt cần DNS đúng); kiểm log Caddy có `certificate
  obtained` cho 3 host, `curl -v` không cần `-k`
- [ ] T018 [US1] Kiểm quickstart §1–§2 trên staging: health 200 (`agents` không còn mock / `*_config_error`), 401 không token, 404 cho `/metrics` + `/dev/play`, SSE
  từng phần, TTFT qua Caddy vs trực tiếp ≤ +300 ms (SC-003), phiên đi tiếp sau restart ai-service, `nmap -Pn <IP>` chỉ
  80/443 (SC-006)
- [ ] T019 [US1] Đo 5 phiên đồng thời (SC-004): RAM / CPU < 80% (`docker stats`, Cloud Monitoring); vượt → đổi máy
  `e2-standard-4`, ghi vào spec Assumptions
- [ ] T020 [US1] (sau PR #120 merge) ai-service: cờ `DEV_PAGES_ENABLED` (mặc định `false`) cho phép `/dev/play`,
  `/dev/interview`, `/dev/voice/*` chạy khi `APP_ENV=staging` (sửa `ensure_dev` trong
  `apps/ai-service/app/dev_play_page.py` và guard trong `apps/ai-service/app/dev_voice_proxy.py`); API vẫn đòi token;
  test cờ tắt / bật; thêm biến vào `apps/ai-service/.env.example`; đặt `DEV_PAGES_ENABLED: "true"` trong `environment:`
  của ai-service ở `infra/staging/docker-compose.staging.yml` (AIE review)
- [ ] T021 [US1] Bật host demo: hash mật khẩu bằng `caddy hash-password`, đặt `DEMO_PASSWORD_HASH` trên VM; kiểm
  quickstart §3 (401 không mật khẩu, `/docs` 404, phiên có giọng nói chạy, DevTools không thấy token)

**Checkpoint**: staging dùng được qua HTTPS (mốc 30/11).

---

## Phase 4: User Story 2 — Deploy / rollback một lệnh (P1)

**Goal**: merge `main` → image GHCR → một lệnh deploy, một lệnh rollback.

**Independent Test**: quickstart §4.

- [ ] T022 [US2] `infra/staging/scripts/deploy-on-vm.sh <sha>` theo staging-cli: kiểm `.env` + `env/*.env` có đủ biến
  → `docker manifest inspect` image → ghi `IMAGE_TAG=<sha>` → `pull` → `up -d db` → `docker compose run --rm ai-session-setup` (lỗi → thoát
  1, `failed_step=session_setup`; KHÔNG dựa vào `depends_on`: compose gỡ ai-service cũ trước khi biết setup lỗi) → `up
  -d` → chờ `build` = sha trên cả 2 health ≤ 5 phút → ghi `/opt/ai-recruit/state/deploy-state.json` theo
  [data-model §1](data-model.md) (`current`, `previous`, `history` ≤ 20 với `{sha, at, by, action: deploy|rollback,
  result: ok|failed, failed_step?}`; lỗi chỉ thêm `history`) → `docker image prune` giữ 2 bản
- [ ] T023 [P] [US2] `infra/staging/scripts/deploy.sh [sha]` (máy DE): mặc định sha của tag `main`; chép compose +
  Caddyfile lên VM qua `gcloud compute scp --tunnel-through-iap`; chạy `deploy-on-vm.sh` qua IAP SSH; thoát theo mã
  của VM
- [ ] T024 [P] [US2] `infra/staging/scripts/rollback.sh`: đọc `previous` trong `deploy-state.json` → `deploy-on-vm.sh
  <previous>` với `action: rollback`; không có `previous` → thoát 1
- [ ] T025 [US2] Kiểm quickstart §4: deploy bản mới, rollback ≤ 5 phút, deploy với `SESSION_DB_URL` sai trên branch
  thử thoát 1 và ai-service cũ vẫn chạy (SC-002)

---

## Phase 5: User Story 3 — Giám sát + cảnh báo (P2)

**Goal**: email khi staging hỏng; dashboard không cần SSH.

**Independent Test**: quickstart §6.

- [ ] T026 [US3] Uptime check `https://ai.<host>/api/health` + cảnh báo #1 (> 2 phút) ngay sau T018 (bảo vệ demo sớm)
  trong `infra/staging/monitoring/alerts/01-health-down.json`
- [ ] T027 [US3] `infra/staging/monitoring/ops-agent.yaml`: log mọi container (`/var/lib/docker/containers/*/*.log`,
  nhãn theo tên container), receiver Prometheus đọc ai-service + voice-service; Ops Agent chạy trên host nên publish
  `/metrics` chỉ trên `127.0.0.1` (`127.0.0.1:18000:8000`, `127.0.0.1:18020:8020`) trong
  `infra/staging/docker-compose.staging.yml`; ai-service `/metrics` đòi token → nếu receiver không gửi được header thì
  đề xuất AIE đưa `/metrics` vào `OPEN_PATHS` (Caddy đã chặn từ ngoài)
- [ ] T028 [P] [US3] 7 chính sách còn lại (FR-016 #2–#8) trong `infra/staging/monitoring/alerts/0<n>-<slug>.json`,
  `displayName` = `staging-<nn>-<slug>`, ngưỡng đúng bảng FR-016 (TTFT #3 lấy từ
  `plans/reports/eval-261109-1648-ttft-breakdown*`), tự đóng, kênh email `ALERT_EMAIL`
- [ ] T029 [P] [US3] `infra/staging/monitoring/dashboard-staging.json`: CPU / RAM / đĩa; request, 5xx, p95 theo route;
  TTFT p95, tỉ lệ fallback theo agent, token / ngày, lỗi RAG; metrics không gắn nhãn phiên / người dùng (FR-018)
- [ ] T030 [US3] `infra/staging/monitoring/apply-monitoring.sh`: tạo / cập nhật kênh email, uptime, policy, dashboard
  theo `displayName` (chạy 2 lần không trùng); chạy và kiểm quickstart §6 (SC-005)

---

## Phase 6: User Story 4 — Sao lưu (P2)

**Goal**: `ai_session` sao lưu hằng ngày ra GCS, khôi phục được.

**Independent Test**: quickstart §5.

- [ ] T031 [P] [US4] `infra/staging/scripts/backup-postgres.sh`: `docker compose exec -T db pg_dump -Fc ai_session` →
  `gs://<project>-staging-backup/pg/ai_session/<YYYYMMDD-HHMM>.dump`; log một dòng `backup_ok db=ai_session bytes=<n>
  object=<path>` hoặc `backup_failed db=ai_session reason=<…>` (log-based metric cho cảnh báo #8)
- [ ] T032 [P] [US4] `infra/staging/scripts/restore-postgres.sh <object> [--target <db_moi>]`: DB đích không trống →
  thoát 1; `pg_restore`; in số bản ghi mỗi bảng
- [ ] T033 [US4] Cron 02:00 cho `backup-postgres.sh` trong `infra/staging/scripts/bootstrap-vm.sh`; chạy quickstart §5
  (SC-007)

---

## Phase 7: User Story 5 — Backend FSD + thêm service (P3)

**Goal**: FSD nối được theo hướng dẫn; service mới vào staging không sửa logic deploy.

**Independent Test**: quickstart §7.

- [ ] T034 [US5] Tạo `docs/deployment-guide.md` (FR-020): dựng từ máy trống, deploy, rollback, khôi phục, xử lý cảnh
  báo thường gặp, đổi token / mật khẩu demo, đổi domain; mục "Cho backend FSD" (2 URL, header `X-Internal-Token`, timeout
  đọc SSE ≥ 60 s, tự rate limit theo tài khoản, mở `Permissions-Policy microphone` cho trang giọng nói); mục "Thêm
  service" (Dockerfile + health + `build`, khối compose, host Caddy nếu public, biến mẫu, matrix `build-images.yml`,
  metrics / log / cảnh báo)
- [ ] T035 [US5] Kiểm quickstart §7 (đóng vai backend FSD từ máy ngoài; thử danh sách bước với `data-pipeline` trên
  branch thử, SC-008)
- [ ] T036 [US5] Gửi FSD: link `docs/deployment-guide.md`, 2 URL; 2 token qua kênh riêng (không ghi vào repo / issue)

---

## Phase 8: Polish

- [ ] T037 [P] (hàng đã cập nhật 2026-11-28, cập nhật tiếp theo tiến độ) `specs/README.md` hàng 014: trạng thái theo tiến độ (tasks có, phạm vi mới, Đợt A/B)
- [ ] T038 [P] Đề xuất sửa constitution II (APISIX → "mỗi repo một điểm vào public; repo AI dùng Caddy") ở PR riêng qua
  `/speckit-constitution`, sau khi team đồng ý
- [ ] T039 [P] `docs/system-architecture.md` + `docs/project-changelog.md`: sơ đồ staging (Caddy → 2 service, Postgres,
  Supabase `ai_db`, GHCR)
- [ ] T040 `shellcheck infra/staging/scripts/*.sh infra/staging/monitoring/*.sh` sạch

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → US1 (T015–T019) → US2; US3 T026 ngay sau T018; US3 phần còn lại, US4, US5 sau US1, song song
  được với US2.
- T020–T021 chờ PR #120 merge (không chặn mốc US1 30/11).
- T011 chờ lần chạy đầu của T010; T016 cần image từ T010.
- T022 → T023, T024 → T025. T027 → T028–T030. T031–T032 → T033.

## Parallel Example

```text
Phase 2: T007, T008, T009, T012, T013, T014 cùng lúc (khác file); T010 sau T007 (build-arg APP_VERSION)
US3: T028 + T029 song song sau T027
US4: T031 + T032 song song
```

## Implementation Strategy

1. **MVP (mốc 30/11)**: Phase 1 + T010–T011, T013–T014 + T015–T018 + T026 → staging HTTPS có cảnh báo health.
2. **03/12**: US2 (deploy một lệnh), US3 đủ, US4.
3. **Khi #120 merge**: T020–T021 (host demo chạy thật).
4. **Trước S5**: US5 + Polish.
