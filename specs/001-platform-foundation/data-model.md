# Data Model: Platform Foundation

Feature này không tạo bảng nghiệp vụ. Schema từng DB: xem
[docs/architecture/data-model.md](../../docs/architecture/data-model.md). File này chỉ liệt kê inventory hạ tầng.

## Service Databases

| Database | Service sở hữu | Extension | Ai tạo schema |
|---|---|---|---|
| `user_db` | user-service | — | migration MikroORM của user-service |
| `job_db` | job-service | — | migration MikroORM của job-service (S0-FSD-6) |
| `interview_db` | interview-service | — | migration MikroORM của interview-service |
| `notification_db` | notification-service | — | migration MikroORM của notification-service |
| `ai_db` | ai-service | `vector` | DDL trong `scripts/init-databases.sh` (phần AIE, S0-AIE-2) |

Tất cả nằm trên một instance `ai_recruit_db` (`pgvector/pgvector:pg16`), port host `5534`.
Validation: init script idempotent; `make db-ensure` cho volume cũ.

## Storage Buckets

| Bucket | Mục đích | Quyền | Tạo bởi |
|---|---|---|---|
| `ai-recruit-files` | CV (S2-FSD-5), avatar/logo (S1-FSD-5) | private, truy cập qua service | `minio-init` |

## Env Variables / Gateway Routes / CI Checks

Xem [contracts/env-variables.md](contracts/env-variables.md), [contracts/gateway-routes.md](contracts/gateway-routes.md),
[contracts/ci-pipeline.md](contracts/ci-pipeline.md).
