---

description: "Task list for 001-platform-foundation"
---

# Tasks: Platform Foundation

**Input**: Design documents from `/specs/001-platform-foundation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Spec không yêu cầu test code mới. Mỗi story kiểm chứng bằng mục tương ứng trong
[quickstart.md](quickstart.md); CI (US3) là gate tự động cho các thay đổi sau.

**Organization**: Nhóm theo user story. US2 (đổi tên) chạy **trước** US1 dù cùng P1 vì nó chặn merge của cả
team (research R1).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: chạy song song được (khác file, không phụ thuộc)
- **[Story]**: US1..US5 theo spec.md; mã `S0-DE-#` để truy vết về sprint plan

---

## Phase 1: Setup

**Purpose**: phối hợp và kiểm chứng giả định trước khi sửa file dùng chung

- [ ] T001 Hỏi AIE: `origin/feat/aie` merge được trong ≤ 1 ngày không? Báo FSD lịch merge PR-1 → chốt thứ tự merge (research R1)
- [ ] T002 Tạo branch `chore/rename-project-scope` từ `main`
- [ ] T003 [P] Kiểm tra `pnpm install` trên Windows và Linux (container `node:22`) với root devDependencies hiện tại; ghi kết quả vào `specs/001-platform-foundation/research.md` R8

---

## Phase 2: Foundational

**Purpose**: sửa lỗi chặn mọi story trên mọi nền tảng

- [ ] T004 Nếu T003 lỗi unsupported platform: gỡ `@oxlint/binding-darwin-arm64`, `@turbo/darwin-arm64` khỏi `package.json`, sinh lại `pnpm-lock.yaml`
- [ ] T005 Thay `${PWD}/.docker/volumes/` bằng `./.docker/volumes/` trong `docker-compose.yml` (research R4)
- [ ] T006 [P] Thêm `.gitattributes` với `*.sh text eol=lf` (tránh CRLF làm hỏng init script trong container khi commit từ Windows)

**Checkpoint**: `pnpm install` chạy được trên Windows/Linux; compose resolve đúng đường dẫn volume

---

## Phase 3: User Story 2 — Định danh dự án thống nhất (P1) · S0-DE-1 · PR-1

**Goal**: `@ai-recruit/*`, `ai_recruit_*`, `ai-recruit-network`; không còn Kong / tên starter

**Independent Test**: quickstart §0 (`pnpm install && pnpm build` xanh) + §5 (grep tên cũ = 0)

- [ ] T007 [US2] Đổi `name` trong `package.json` root → `@ai-recruit/root`, cập nhật `description`
- [ ] T008 [P] [US2] Đổi `name` và dependency `@app/*` → `@ai-recruit/*` trong `libs/common/package.json`, `libs/core/package.json`, `libs/email-template/package.json`
- [ ] T009 [P] [US2] Đổi `name` → `@ai-recruit/<service>` và dependency `@app/*` trong `apps/auth-service/package.json`, `apps/user-service/package.json`, `apps/notification-service/package.json`
- [ ] T010 [US2] Đổi `paths` `@app/*` trong `tsconfig.json`; grep thêm `@app/` trong `apps/*/tsconfig*.json`, `apps/*/webpack.config.js`, cấu hình jest `moduleNameMapper`, `nest-cli.json`, `ecosystem.config.js`
- [ ] T011 [US2] Script thay import `@app/` → `@ai-recruit/` trong `apps/*/src`, `apps/*/test`, `libs/*/src` (~62 file); chỉ thay chuỗi import, không đổi logic
- [ ] T012 [US2] Đổi container `nest_turbo_*` → `ai_recruit_*` và network → `ai-recruit-network` trong `docker-compose.yml` (gồm block `ai-service` nếu `feat/aie` đã merge)
- [ ] T013 [P] [US2] Xóa `docker-compose-kong.yml`, `config/kong/`, `.docker/compose/kong/`; gỡ target `deckSync` trong `Makefile`; gỡ `KONG_*`, `GW_HOST` trong `.env.example`
- [ ] T014 [US2] `pnpm install` (sinh lại `pnpm-lock.yaml`) → `pnpm build`, `pnpm check-types`, `pnpm test` đều xanh
- [ ] T015 [US2] Chạy quickstart §5; mở PR-1 `[root] chore: rename project scope to @ai-recruit`; sau merge báo FSD/AIE rebase

**Checkpoint**: PR-1 merged — team rebase lên tên mới

---

## Phase 4: User Story 1 — Một lệnh dựng hạ tầng (P1) 🎯 MVP · S0-DE-2, S0-DE-3 · PR-2

**Goal**: 5 DB (ai_db có `vector`), MinIO + bucket, mọi thành phần healthy

**Independent Test**: quickstart §1, §2, §3

- [ ] T016 [US1] Tạo branch `chore/docker-multi-db-minio`; tạo `scripts/init-databases.sh`: tạo idempotent `user_db`, `job_db`, `interview_db`, `notification_db`, `ai_db` bằng `\gexec`; `\c ai_db` + `CREATE EXTENSION IF NOT EXISTS vector`; chừa chỗ cho DDL của AIE ở cuối file (research R3)
- [ ] T017 [US1] Service `db` trong `docker-compose.yml` và `.docker/compose/postgresql/postgresql.yml`: image `pgvector/pgvector:pg16`, mount `./scripts/init-databases.sh:/docker-entrypoint-initdb.d/init-databases.sh`, port `${PG_HOST_PORT:-5534}:5432`, healthcheck `pg_isready`
- [ ] T018 [US1] Service `minio` trong `docker-compose.yml`: pin tag (VERIFY research R6), ports `${MINIO_API_PORT:-9000}`/`${MINIO_CONSOLE_PORT:-9001}`, volume `./.docker/volumes/minio_data`, healthcheck `mc ready local`
- [ ] T019 [US1] Service `minio-init` (image `minio/mc`, `depends_on: minio: service_healthy`, `restart: "no"`, `entrypoint: ["/bin/sh", "-c"]` vì entrypoint mặc định của image là `mc`; `environment` gồm `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `AWS_S3_BUCKET_NAME`) tạo bucket bằng `mc mb --ignore-existing`
- [ ] T020 [P] [US1] Healthcheck cho `redis` (`redis-cli ping`), `etcd`, `apisix`; bind port admin APISIX vào `127.0.0.1` (research R11) trong `docker-compose.yml`
- [ ] T021 [P] [US1] Thêm target `db-ensure` (chạy lại init script qua `docker compose exec db`) trong `Makefile`
- [ ] T022 [US1] Chạy quickstart §1–3 hai lần: volume sạch và volume cũ + `make db-ensure`; ghi kết quả vào PR

**Checkpoint**: hạ tầng local dựng được bằng một lệnh — FSD/AIE bắt đầu dùng DB riêng

---

## Phase 5: User Story 5 — Env mẫu đầy đủ (P3) · S0-DE-6 · PR-2

**Goal**: copy env mẫu nguyên trạng là chạy được; không secret thật

**Independent Test**: `docker compose config` không cảnh báo biến thiếu; quickstart §1 chạy với env copy nguyên trạng

- [ ] T023 [US5] Cập nhật `.env.example` theo `contracts/env-variables.md` (Postgres, MinIO, `STORAGE_TYPE=minio` + `AWS_S3_*`, upstream job/interview/ai, TCP, `AI_SERVICE_MOCK`) kèm comment nhóm
- [ ] T024 [P] [US5] `apps/user-service/.env.example`, `apps/notification-service/.env.example`: `*_SERVICE_DB_DATABASE` → `user_db` / `notification_db`; comment host `db:5432` (Docker) vs `localhost:5534` (host)
- [ ] T025 [US5] Thêm biến mới mà NestJS đọc vào `turbo.json` > `globalEnv` (vd `AI_SERVICE_MOCK`)
- [ ] T026 [US5] Kiểm chứng: env copy nguyên trạng → `docker compose config` sạch cảnh báo; rà soát không còn secret thật; mở PR-2

**Checkpoint**: PR-2 merged

---

## Phase 6: User Story 4 — Gateway route mới (P2) · S0-DE-4 · PR-3

**Goal**: `/job/*`, `/interview/*`, `/ai/*` theo `contracts/gateway-routes.md`

**Independent Test**: quickstart §4

- [ ] T027 [US4] Tạo branch `chore/apisix-routes-ci`; thêm service `job-service` (public + protected, upstream `APISIX_JOB_SERVICE_*`) vào `config/apisix/conf/apisix-dev.yaml` theo pattern user-service
- [ ] T028 [US4] Thêm service `interview-service` (upstream `APISIX_INTERVIEW_SERVICE_*`) vào `config/apisix/conf/apisix-dev.yaml`
- [ ] T029 [US4] Đảm bảo service `ai-service` từ `origin/feat/aie` có trong `config/apisix/conf/apisix-dev.yaml` sau merge; khớp `APISIX_AI_SERVICE_*` trong `.env.example`
- [ ] T030 [US4] `make adcSync environment=dev` → quickstart §4 (401 không token, 200 health)

---

## Phase 7: User Story 3 — CI cho mọi PR (P2) · S0-DE-5 · PR-3

**Goal**: lint + check-types + test (Node) và pytest (Python apps) trên mọi PR

**Independent Test**: quickstart §6

- [ ] T031 [US3] Tạo `.github/workflows/ci.yml` job `node` theo `contracts/ci-pipeline.md` (pnpm theo `packageManager`, Node 22, cache, `--frozen-lockfile`, concurrency)
- [ ] T032 [US3] Thêm job `python` matrix `[ai-service, data-pipeline]` có guard `requirements.txt`, Python 3.11, `pytest` trong `.github/workflows/ci.yml`
- [ ] T033 [US3] PR thử có lỗi lint → đỏ; sửa → xanh; ghi thời gian chạy (mục tiêu ≤ 10 phút); mở PR-3
- [ ] T034 [US3] Nhờ admin repo bật branch protection "CI xanh mới merge" cho `main` (và `develop` khi có)

**Checkpoint**: PR-3 merged — mọi PR sau đều qua gate

---

## Phase 8: Polish & Cross-Cutting

- [ ] T035 [P] Cập nhật `README.md`: tên mới, `docker compose up -d`, reset volume / `make db-ensure`, MinIO console, bảng truy cập (FR-016)
- [ ] T036 [P] Cập nhật `docs/sprint-0-kickoff.md`: tick checklist DE; ghi các điểm khác kickoff (image pgvector, biến `AWS_S3_*`, `{SERVICE}_SERVICE_DB_*`) kèm link research
- [ ] T037 Chạy toàn bộ quickstart trên máy sạch, bấm giờ (SC-001 ≤ 15 phút, ≤ 5 lệnh); xác nhận 7/7 mục DE trước 2026-10-12 (SC-007)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (P1)** → **Foundational (P2)** → **US2 / PR-1** (chặn mọi story vì đổi tên file dùng chung)
- Sau PR-1: **PR-2 (US1 + US5)** và **PR-3 (US4 + US3)** độc lập nhau; một người làm thì đi tuần tự PR-2 → PR-3
- **US4** cần thêm `origin/feat/aie` đã merge cho phần `/ai/*` (T029); `/job`, `/interview` không chờ
- **Polish** sau khi 3 PR merge

### Timeline đề xuất (hạn 12/10)

| Ngày | Việc |
|---|---|
| T2 05/10 | T001–T015 (PR-1) |
| T3–T4 06–07/10 | T016–T026 (PR-2) |
| T5–T6 08–09/10 | T027–T034 (PR-3) |
| T7–CN 10–11/10 | T035–T037, buffer review |

### Parallel Opportunities

- T003 ∥ T001–T002; T006 ∥ T004–T005
- T008 ∥ T009 ∥ T013 (khác file)
- T020 ∥ T021; T024 ∥ T023
- T035 ∥ T036

---

## Parallel Example: User Story 2

```bash
Task: "Đổi name + deps trong libs/*/package.json"            # T008
Task: "Đổi name + deps trong apps/*-service/package.json"     # T009
Task: "Xóa Kong: docker-compose-kong.yml, config/kong/, ..."  # T013
```

---

## Implementation Strategy

### MVP

PR-1 (US2) + PR-2 (US1) = team có tên mới và hạ tầng local đủ DB → FSD/AIE không bị chặn. Dừng, kiểm chứng
quickstart §0–§3, rồi mới làm PR-3.

### Incremental Delivery

PR-1 → PR-2 → PR-3; mỗi PR tự kiểm chứng bằng quickstart và không làm hỏng PR trước.

---

## Notes

- Commit theo Conventional Commits, scope `docker`, `ci`, `apisix`, `root` (vd `chore(docker): add MinIO to docker-compose`)
- Không commit `.env`; không có secret thật trong `.env.example`
- Thay đổi ngoài file DE sở hữu (import 62 file TS) là cơ học — báo trước cho FSD
