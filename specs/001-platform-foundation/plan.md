# Implementation Plan: Platform Foundation

**Branch**: `chore/rename-project-scope` → `chore/docker-multi-db-minio` → `chore/apisix-routes-ci` | **Date**: 2026-10-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-platform-foundation/spec.md`

## Summary

Dựng nền tảng Sprint 0 cho DE: (1) đổi tên toàn monorepo sang `@ai-recruit/*` / `ai_recruit_*` và gỡ Kong,
(2) một PostgreSQL 16 + pgvector chứa 5 database tạo bằng init script idempotent, (3) MinIO với bucket tự tạo,
(4) route APISIX cho job / interview / ai, (5) GitHub Actions chạy lint + check-types + test (Node) và pytest
(Python apps), (6) env mẫu đầy đủ. Cách làm: tái dùng tối đa pattern có sẵn (route user-service, biến
`{SERVICE}_SERVICE_DB_*`, biến `AWS_S3_*` + `STORAGE_TYPE=minio`), chia 3 PR nhỏ, PR đổi tên merge đầu tiên.

## Technical Context

**Language/Version**: YAML (Docker Compose v2, GitHub Actions, APISIX ADC), Bash (init script), TypeScript
(chỉ đổi import), Python 3.11 (chạy test ai-service / data-pipeline trong CI)

**Primary Dependencies**: `pgvector/pgvector:pg16`, Redis 8, APISIX 3.14 + etcd + ADC 0.23.1, MinIO + `mc`,
Turborepo, pnpm 10.17, Node 22, GitHub Actions (`pnpm/action-setup`, `actions/setup-node`, `actions/setup-python`)

**Storage**: 1 PostgreSQL instance / 5 DB (`user_db`, `job_db`, `interview_db`, `notification_db`, `ai_db`);
MinIO bucket `ai-recruit-files`

**Testing**: smoke checks trong [quickstart.md](quickstart.md) (DB list, extension, upload/download checksum,
gateway 401/200); CI tự kiểm chứng bằng PR thử; jest/pytest hiện có

**Target Platform**: laptop dev Windows / macOS / Linux (Docker Desktop); GitHub-hosted `ubuntu-latest`

**Project Type**: hạ tầng / DevOps cho monorepo microservices

**Performance Goals**: hạ tầng healthy ≤ 2 phút (SC-002); CI ≤ 10 phút (SC-004)

**Constraints**: CI không dùng secret thật; compose không phụ thuộc `${PWD}`; giữ nguyên thay đổi của
`origin/feat/aie`; không đụng logic gRPC→TCP (S0-FSD-2)

**Scale/Scope**: 3 dev, 6 app (4 NestJS hiện/sắp có + ai-service + data-pipeline), ~62 file TS đổi import

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Đánh giá | Ghi chú |
|---|---|---|
| I. DB-per-Service | ✅ | 5 DB tách biệt; init script chỉ tạo DB + extension `vector`; DDL `knowledge_chunks` thuộc AIE (ngoại lệ đã ghi trong constitution) |
| II. Gateway & Transport | ✅ | Route mới qua APISIX, JWT + `x-auth-user` theo pattern user-service; chỉ thêm biến TCP, không thêm gRPC |
| III. Contract-First | ✅ | Bảng route và env chốt trong [contracts/](contracts/); không đổi API contract nghiệp vụ |
| IV. AI Stateless | ✅ N/A | Chỉ đổi tên container ai-service do AIE tạo |
| V. Data Pipeline tái lập | ✅ | `ai_db` + `vector` sẵn sàng cho feature 005; CI có slot pytest cho `apps/data-pipeline` |
| VI. Quality Gates | ✅ (một phần) | Feature này **tạo ra** gate CI lint/types/test, không cần secret. Ngưỡng coverage 60% chưa enforce trong CI ngày đầu — xem research R10 |
| VII. Đơn giản & phạm vi | ✅ | Gỡ Kong và tên starter; không thêm dashboard, không build image trong CI (để 014) |

Post-design re-check (sau Phase 1): ✅ không phát sinh vi phạm; không cần Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/001-platform-foundation/
├── plan.md              # File này
├── research.md          # Phase 0: các quyết định kỹ thuật + rủi ro
├── data-model.md        # Phase 1: inventory DB / bucket / env (link tới docs/architecture/data-model.md)
├── quickstart.md        # Phase 1: các bước kiểm chứng = kịch bản demo Sprint 0
├── contracts/
│   ├── gateway-routes.md
│   ├── env-variables.md
│   └── ci-pipeline.md
├── checklists/requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
package.json                         # name → @ai-recruit/root; gỡ binding darwin-arm64 nếu chặn cài đặt
pnpm-lock.yaml                       # sinh lại sau đổi tên
tsconfig.json                        # paths @app/* → @ai-recruit/*
apps/{auth,user,notification}-service/
├── package.json                     # name + deps @ai-recruit/*
├── .env.example                     # *_SERVICE_DB_DATABASE → <service>_db
└── src/**/*.ts                      # import @app/* → @ai-recruit/*
libs/{common,core,email-template}/package.json
docker-compose.yml                   # prefix ai_recruit_*, network ai-recruit-network, ./ thay ${PWD},
                                     # db → pgvector/pgvector:pg16 + init script, + minio + minio-init
docker-compose-kong.yml              # XÓA
config/kong/  .docker/compose/kong/  # XÓA
scripts/init-databases.sh            # MỚI: tạo 5 DB idempotent + CREATE EXTENSION vector trong ai_db
config/apisix/conf/apisix-dev.yaml   # + job-service, interview-service (ai-service lấy từ feat/aie)
.env.example                         # gỡ Kong; + MinIO qua AWS_S3_*; + upstream job/interview/ai; + TCP ports
turbo.json                           # globalEnv: gỡ Kong/gRPC khi FSD xong; thêm biến mới
Makefile                             # gỡ deckSync; + db-ensure, minio-check
.github/workflows/ci.yml             # MỚI
README.md                            # cập nhật tên, lệnh, reset volume
```

**Structure Decision**: Không tạo thư mục code mới ngoài `scripts/` và `.github/workflows/`. Mọi thay đổi nằm
trong file hạ tầng mà DE sở hữu (`docs/sprint-0-kickoff.md` → "File ownership DE"), cộng với đổi import hàng
loạt bằng script (thay đổi cơ học, không đổi logic).

## Delivery Sequence

| PR | Nội dung | Story | Merge điều kiện |
|---|---|---|---|
| PR-1 `chore/rename-project-scope` | Đổi tên package/import/container/network, gỡ Kong, sửa `${PWD}` | US2 | `pnpm install` + `pnpm build` xanh; báo FSD/AIE rebase ngay |
| PR-2 `chore/docker-multi-db-minio` | pgvector image, init script, MinIO + bucket, env mẫu, Makefile, README | US1, US5 | quickstart §1–3 pass trên máy sạch |
| PR-3 `chore/apisix-routes-ci` | Route job/interview (+ ai sau khi feat/aie merge), CI workflow | US3, US4 | PR thử đỏ/xanh đúng; quickstart §4 pass |

Phối hợp: hỏi AIE merge `origin/feat/aie` trước PR-1 nếu sẵn sàng trong ≤ 1 ngày; nếu không, PR-1 merge trước
và AIE resolve xung đột nhỏ ở `docker-compose.yml` (1 block). Chi tiết: [research.md](research.md) R1.

## Complexity Tracking

Không có vi phạm constitution cần biện minh.
