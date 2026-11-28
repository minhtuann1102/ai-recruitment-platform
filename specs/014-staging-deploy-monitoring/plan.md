# Implementation Plan: Staging Deploy & Monitoring

**Branch**: `chore/staging-compose-014` (cập nhật phạm vi + compose staging); code sau theo phần: `chore/staging-*`,
`feat/ai-service/<...>` | **Date**: 2026-11-19, cập nhật 2026-11-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/014-staging-deploy-monitoring/spec.md`

## Summary

Dựng staging trên một VM Compute Engine chạy Docker Compose: Caddy (TLS + chọn upstream theo host) → ai-service +
voice-service, Postgres trên VM chỉ để lưu checkpoint phiên (`SESSION_STORE=postgres`); kho RAG vẫn là `ai_db` trên
Supabase. Ba host: `ai.<host>`, `voice.<host>` (backend FSD gọi bằng token nội bộ), `demo.<host>` (basic auth, Caddy
gắn token, chỉ các đường trang `/dev/interview` cần). CI build image lên GHCR bằng `GITHUB_TOKEN`; một lệnh deploy /
rollback qua IAP SSH, bước tạo bảng checkpoint chạy trước ai-service. Ops Agent → Cloud Monitoring / Logging, 8 cảnh
báo email, sao lưu `ai_session` hằng ngày ra GCS. Quyết định chi tiết: [research.md](research.md) (mục "Cập nhật
2026-11-28" thay R1, R4–R9).

## Technical Context

**Language/Version**: Bash (script hạ tầng), YAML (compose, Ops Agent, GitHub Actions), Caddyfile, JSON (policy cảnh
báo, dashboard); Python 3.12 (ai-service, thay đổi nhỏ)
**Primary Dependencies**: Docker Engine + Compose v2, Caddy 2.10, Postgres 16, Google Cloud CLI, Ops Agent, GitHub
Actions (`docker/login-action`, `docker/build-push-action`), gitleaks
**Storage**: Postgres 16 trên VM (DB `ai_session`, bảng checkpoint LangGraph); GCS bucket sao lưu; GHCR (image);
`ai_db` ở Supabase (đọc, role `aie_reader`)
**Testing**: pytest cho thay đổi ai-service; `shellcheck` cho script; `docker compose config` + `caddy validate` + chạy
thử cả stack trên máy với host `*.localhost`; kiểm chấp nhận theo [quickstart.md](quickstart.md) trên staging thật
**Target Platform**: Ubuntu 24.04 LTS, `e2-standard-2`, `asia-southeast1-b`
**Project Type**: hạ tầng / vận hành cho 2 service Python
**Performance Goals**: TTFT p95 qua Caddy ≤ trực tiếp + 300 ms (SC-003); 5 phiên đồng thời, RAM / CPU < 80%
(SC-004); merge → live ≤ 15 phút, rollback ≤ 5 phút (SC-002)
**Constraints**: chỉ 80/443 công khai; không secret trong git; không khóa dài hạn trong CI; compose dev không đổi;
US1 trước 30/11, US2 + US3 trước 03/12 (SC-009)
**Scale/Scope**: 1 máy, 2 service ứng dụng + Caddy + Postgres

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Nguyên tắc | Đánh giá | Ghi chú |
|---|---|---|
| I. DB-per-service | Đạt | `ai_session` chỉ ai-service dùng; voice-service không có DB |
| II. Gateway duy nhất | Lệch, ghi ở Complexity Tracking | APISIX đã gỡ khỏi repo (#113); Caddy là điểm vào duy nhất của repo này. Sửa constitution ở PR riêng (`/speckit-constitution`) |
| III. Contract-first | Đạt | Không đổi API nghiệp vụ; host + chặn đường ghi ở [contracts/staging-hosts.md](contracts/staging-hosts.md); trường `build` của health ghi ở [contracts/health-endpoints.md](contracts/health-endpoints.md) |
| IV. AI stateless | Lệch đã có từ trước | Lưu phiên LangGraph (#118, đề xuất option B) đã đảo nguyên tắc này; 014 chỉ cấp Postgres cho nó |
| V. Data pipeline | Không áp | Không ghi `ai_db` |
| VI. Quality gates | Đạt | CI giữ pytest; thêm gitleaks; mọi env mới vào file mẫu |
| VII. Đơn giản | Đạt | Không Terraform / Kubernetes / Prometheus tự dựng; Caddy image chính thức, không plugin; script gcloud |
| Ràng buộc hạ tầng | Đạt | "Staging: Docker Compose trên VPS/cloud, có HTTPS"; mọi service có health endpoint |
| Quy trình | Đạt | Spec Kit (feature DE); link `docs/` thay vì chép |

**Re-check 2026-11-28**: đạt với 2 lệch đã ghi. Sửa code ai-service của AIE qua PR có AIE review (spec "Phụ thuộc").

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
│   ├── staging-hosts.md            # host công khai, upstream, chặn, ai giữ token nào
│   └── health-endpoints.md         # trường build của health
├── checklists/requirements.md
└── tasks.md                        # /speckit-tasks
```

### Source Code (repository root)

```text
.github/workflows/
├── ci.yml                                 # SỬA: thêm job gitleaks
└── build-images.yml                       # MỚI: build + push GHCR khi CI main xanh
apps/ai-service/Dockerfile                 # SỬA: chép lệnh tạo bảng checkpoint (xong), user không phải root, ARG APP_VERSION
apps/voice-service/Dockerfile              # SỬA: user không phải root, ARG APP_VERSION
apps/ai-service/app/{dev_play_page,main}.py  # SỬA: cờ DEV_PAGES_ENABLED cho host demo; health thêm build (AIE review)
apps/voice-service/app/...                 # SỬA: health thêm build
infra/staging/
├── docker-compose.staging.yml             # MỚI (xong): caddy, db, ai-session-setup, ai-service, voice-service
├── Caddyfile                              # MỚI (xong): 3 host
├── .env.staging.example                   # MỚI (xong): biến compose; key service ở env/<service>.env (gitignore)
├── scripts/
│   ├── provision-gcp.sh                   # VM, IP, firewall, bucket, snapshot, SA
│   ├── bootstrap-vm.sh                    # Docker, Ops Agent, /opt/ai-recruit, cron
│   ├── deploy.sh / rollback.sh            # chạy ở máy DE → IAP SSH
│   ├── deploy-on-vm.sh                    # chạy trên VM
│   └── backup-postgres.sh / restore-postgres.sh
└── monitoring/
    ├── ops-agent.yaml
    ├── alerts/*.json                      # 8 chính sách
    ├── dashboard-staging.json
    └── apply-monitoring.sh
docs/deployment-guide.md                   # MỚI (FR-020): dựng, deploy, rollback, khôi phục, hướng dẫn backend FSD
```

**Structure Decision**: mọi thứ riêng staging nằm ở `infra/staging/` (thư mục `infra/` đầu tiên của repo); VM giữ một
bản của thư mục này ở `/opt/ai-recruit`.

## Thứ tự làm (map user story)

| Đợt | Nội dung | Story | Mục tiêu |
|---|---|---|---|
| A | compose staging + Caddy + env mẫu, chạy thử trên máy (xong 28/11); provision + bootstrap VM; DNS wildcard `*.hireready.tuannm.app` + chứng chỉ Let's Encrypt; deploy tay lần đầu; uptime + cảnh báo #1 | US1 (+ một phần US3) | 29–30/11 |
| B | build-images GHCR; deploy / rollback; `build` trong health; user không phải root | US2 | 01–02/12 |
| C | cờ trang dev + host demo chạy thật (sau PR #120) | US1 kịch bản 5 | khi #120 merge |
| D | Ops Agent đủ, dashboard, 7 cảnh báo còn lại; sao lưu + khôi phục thử | US3, US4 | 02–03/12 |
| E | hướng dẫn backend FSD, danh sách bước thêm service, `docs/deployment-guide.md` | US5, FR-020 | 03/12 |

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Caddy thay APISIX làm điểm vào (constitution II: APISIX là entry point public duy nhất) | APISIX + etcd đã gỡ khỏi repo ở #113; repo chỉ còn 2 service gọi server-to-server bằng token, không cần JWT / route động | Dựng lại APISIX + etcd cho 2 upstream: thêm 2 container, cấu hình ADC, không thêm bảo vệ nào so với token nội bộ |
| Host demo: Caddy xác thực (basic auth) và gắn token thay bên gọi | Chưa có UI phía FSD; GVHD / mentor cần thử phỏng vấn giọng nói trên staging | Đưa token vào trình duyệt: ai mở trang cũng lấy được token gọi mọi endpoint; chỉ demo ở máy local: GVHD không tự thử được |
| Không rate limit ở lớp vào | Lớp vào không biết người dùng (token là của service); Caddy chuẩn không có rate limit | Image Caddy tự build với plugin rate limit theo IP: thêm image phải bảo trì, giới hạn theo IP sai khi mọi lời gọi đến từ một backend FSD |
