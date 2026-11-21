# Implementation Plan: Staging Deploy & Monitoring

**Branch**: `docs/staging-deploy-spec` (spec + plan); code theo phần: `chore/infra/staging-*`, `feat/<service>/health`
| **Date**: 2026-11-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/014-staging-deploy-monitoring/spec.md`

## Summary

Dựng staging trên một VM Compute Engine chạy Docker Compose: Caddy (chỉ TLS) → APISIX (profile `staging`, JWT, token
nội bộ tới ai-service, rate limit, CORS cho Vercel) → ai-service + 3 service NestJS (Dockerfile mới, health chung) +
Postgres / Redis / MinIO / etcd. CI build image vào Artifact Registry bằng Workload Identity Federation; một lệnh
deploy / rollback qua IAP SSH, migration chạy trước. Ops Agent → Cloud Monitoring / Logging, 8 cảnh báo email, sao
lưu Postgres hằng ngày ra GCS. Quyết định chi tiết: [research.md](research.md).

## Technical Context

**Language/Version**: Bash (script hạ tầng), YAML (compose, APISIX, Ops Agent, GitHub Actions), JSON (policy
cảnh báo, dashboard); TypeScript / NestJS 11 cho `HealthModule`; Python (ai-service, thay đổi nhỏ)
**Primary Dependencies**: Docker Engine + Compose v2, Caddy 2, APISIX 3.14 + ADC, Google Cloud CLI, Ops Agent,
GitHub Actions (`google-github-actions/auth`, `docker/build-push-action`), Turborepo `prune`, gitleaks
**Storage**: Postgres 16 (pgvector image) trên VM cho DB của service; GCS bucket sao lưu; Artifact Registry; `ai_db`
ở Supabase (đọc, role `aie_reader`)
**Testing**: Jest cho `HealthModule` (unit: 200 / 503 theo phụ thuộc); pytest cho thay đổi ai-service; `shellcheck`
cho script; kiểm chấp nhận theo [quickstart.md](quickstart.md) trên staging thật
**Target Platform**: Ubuntu 24.04 LTS, `e2-standard-4`, `asia-southeast1-b`
**Project Type**: hạ tầng / vận hành cho monorepo web-service
**Performance Goals**: TTFT p95 qua gateway ≤ trực tiếp + 300 ms (SC-003); 5 phiên đồng thời, RAM / CPU < 80%
(SC-004); merge → live ≤ 15 phút, rollback ≤ 5 phút (SC-002)
**Constraints**: chỉ 80/443 công khai; không secret trong git; không khóa dài hạn trong CI; dev `docker compose up`
không đổi hành vi; xong US1 + US2 trước 28/11 để Stretch (voice 015) bắt đầu
**Scale/Scope**: 1 máy, 4 service ứng dụng + 6 thành phần hạ tầng; thêm ~2 service FSD sau qua US5

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc | Đánh giá | Ghi chú |
|---|---|---|
| I. DB-per-service | Đạt | Postgres một instance, mỗi service DB riêng như dev; sao lưu theo từng DB |
| II. Gateway duy nhất | Đạt có ghi chú | Caddy chỉ TLS trong suốt (Complexity Tracking); route mới khai báo ở `apisix-staging.yaml`; JWT verify tại gateway giữ nguyên |
| II. Transport | Không đổi | gRPC còn trong user / notification là đồ thừa starter (FSD), không thêm transport mới |
| III. Contract-first | Đạt | Không đổi API nghiệp vụ; health NestJS mới + trường `build` ở health ai-service ghi trong [contracts/](contracts/) và `docs/architecture/api-contracts.md` cùng PR |
| IV. AI stateless | Đạt | ai-service không lưu phiên; chỉ đọc `ai_db` |
| V. Data pipeline | Không áp | Không ghi `ai_db` |
| VI. Quality gates | Đạt | CI giữ lint / check-types / test; thêm gitleaks; `HealthModule` có test; mọi env mới vào `.env.example` + `turbo.json` `globalEnv` (`APP_VERSION`) |
| VII. Đơn giản | Đạt | Không Terraform / Kubernetes / Prometheus tự dựng; 1 Dockerfile mẫu cho NestJS; script gcloud |
| Ràng buộc hạ tầng | Đạt | "Staging: Docker Compose trên VPS/cloud, có HTTPS"; "mọi service MUST có health endpoint" — bổ sung cho 3 NestJS; object storage MinIO (S3-compatible) |
| Quy trình | Đạt | Spec Kit (feature DE); link `docs/` thay vì chép; không đổi kiến trúc → không cần ADR mới |

**Re-check sau Phase 1**: đạt; không vi phạm mới. Sửa code của FSD (`apps/*-service`, `libs/core`) và AIE
(`apps/ai-service`) qua PR có owner review (spec "Phụ thuộc").

## Project Structure

### Documentation (this feature)

```text
specs/014-staging-deploy-monitoring/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── staging-cli.md              # lệnh provision / deploy / rollback / backup / restore
│   ├── gateway-staging-routes.md   # route công khai, auth, rate limit, CORS, chặn
│   └── health-endpoints.md         # health NestJS + trường build của ai-service
├── checklists/requirements.md
└── tasks.md                        # /speckit-tasks
```

### Source Code (repository root)

```text
.docker/node-service.Dockerfile            # MỚI: Dockerfile mẫu NestJS (ARG SERVICE; target runtime, migrator)
.github/workflows/
├── ci.yml                                 # SỬA: thêm job gitleaks
└── build-images.yml                       # MỚI: build + push image khi main xanh (WIF)
config/apisix/conf/
├── apisix-staging.yaml                    # MỚI: route staging
├── config-staging.yaml                    # MỚI: admin khóa nội bộ, real_ip, prometheus export
└── debug-staging.yaml                     # MỚI: chép debug-dev, tắt
libs/core/src/health/                      # MỚI: HealthModule dùng chung (FSD review)
apps/{auth,user,notification}-service/src/ # SỬA: import HealthModule (FSD review)
apps/ai-service/app/{security,main}.py     # SỬA: /metrics vào OPEN_PATHS, health thêm build (AIE review)
apps/ai-service/Dockerfile                 # SỬA: user không phải root, ARG APP_VERSION
infra/staging/
├── docker-compose.staging.yml             # MỚI
├── Caddyfile                              # MỚI
├── .env.staging.example                   # MỚI
├── scripts/
│   ├── provision-gcp.sh                   # VM, IP, firewall, AR, bucket, snapshot, SA, WIF
│   ├── bootstrap-vm.sh                    # Docker, Ops Agent, thư mục /opt/ai-recruit, cron
│   ├── deploy.sh / rollback.sh            # chạy ở máy DE → IAP SSH
│   ├── deploy-on-vm.sh                    # chạy trên VM
│   ├── backup-postgres.sh / restore-postgres.sh
│   └── issue-test-jwt.sh                  # JWT thử khi luồng login FSD chưa xong (chỉ trên VM)
└── monitoring/
    ├── ops-agent.yaml
    ├── alerts/*.json                      # 8 chính sách
    ├── dashboard-staging.json
    └── apply-monitoring.sh
docs/deployment-guide.md                   # MỚI (FR-020)
```

**Structure Decision**: mọi thứ riêng staging nằm ở `infra/staging/` (đây là thư mục `infra/` đầu tiên của repo);
cấu hình gateway theo cơ chế profile sẵn có ở `config/apisix/conf/`; Dockerfile NestJS dùng chung ở `.docker/` cạnh
các file compose phụ trợ đang có.

## Thứ tự làm (map user story)

| Đợt | Nội dung | Story | Mục tiêu |
|---|---|---|---|
| A | provision GCP + bootstrap VM; compose staging + Caddy + APISIX staging; ai-service lên với HTTPS; uptime + cảnh báo #1 | US1 (+ một phần US3) | 24–25/11 |
| B | Dockerfile mẫu + HealthModule cho 3 NestJS; build-images + deploy / rollback | US1, US2 | 26–28/11 |
| — | **Mốc**: US1 + US2 xong → Stretch (voice 015) được bắt đầu song song | | 28/11 |
| C | sao lưu + khôi phục thử | US4 | 29–30/11 |
| D | Ops Agent đủ, dashboard, 7 cảnh báo còn lại | US3 | 01–03/12 |
| E | danh sách bước thêm service, nối Vercel khi 013 có, `docs/deployment-guide.md` | US5, FR-020 | khi FSD có code |

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Caddy đứng trước APISIX (constitution II: APISIX là entry point public duy nhất) | Cần HTTPS tự gia hạn; Caddy chỉ kết thúc TLS và chuyển tiếp mọi request sang APISIX, không route / auth | ACME trong APISIX cần plugin / cron certbot + nạp SSL qua admin API, dễ hỏng gia hạn; LB HTTPS của GCP tốn tiền và cần domain thật ngay |
| Route `/ai/*` công khai (kiến trúc đích: chỉ interview-service gọi ai-service) | `interview-service` chưa tồn tại; demo AI cần gọi được qua gateway | Chờ FSD → không demo được S4; đã bù bằng JWT + token nội bộ do gateway gắn + rate limit; thu hồi khi interview-service có |
