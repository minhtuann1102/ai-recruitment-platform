# Contract: Environment Variables

Nguyên tắc: secret chỉ là placeholder; biến dùng trong NestJS phải có trong `turbo.json` > `globalEnv`
(trừ biến chỉ nằm trong `.env` riêng của service và được đọc qua `dotenv` của service đó).

## Root `.env.example` — thay đổi

| Nhóm | Biến | Giá trị mẫu | Hành động |
|---|---|---|---|
| Kong | `KONG_*`, `GW_HOST` | — | **Gỡ** |
| Secret local | `JWT_SECRET` | giữ giá trị hiện tại | Ghi chú `# LOCAL ONLY — MUST override khi deploy` (research R11) |
| Secret local | `APISIX_KEY` | giữ giá trị hiện tại | Như trên; bind port admin `9180` vào `127.0.0.1` trong compose |
| Postgres container | `DEFAULT_PG_USER`, `DEFAULT_PG_PASSWORD`, `DEFAULT_PG_DATABASE` | `postgres` / `secret` / `user_db` | Đổi DB mặc định từ `ai-agent` → `user_db` |
| Postgres port | `PG_HOST_PORT` | `5534` | Thêm (port map cấu hình được) |
| MinIO container | `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` | `minioadmin` / `minioadmin` (chỉ local) | Thêm |
| MinIO ports | `MINIO_API_PORT`, `MINIO_CONSOLE_PORT` | `9000` / `9001` | Thêm |
| Storage (service) | `STORAGE_TYPE` | `minio` | Đổi từ `s3` |
| Storage (service) | `AWS_S3_URL`, `AWS_S3_BUCKET_NAME`, `AWS_S3_REGION`, `AWS_S3_ACCESS_KEY_ID`, `AWS_S3_SECRET_ACCESS_KEY`, `AWS_S3_CREDENTIALS_REQUIRED` | `http://localhost:9000`, `ai-recruit-files`, `us-east-1`, `minioadmin`, `minioadmin`, `true` | Đổi giá trị mẫu sang MinIO local |
| Gateway upstream | `APISIX_JOB_SERVICE_HOST/PORT` | `host.docker.internal` / `3302` | Thêm |
| Gateway upstream | `APISIX_INTERVIEW_SERVICE_HOST/PORT` | `host.docker.internal` / `3304` | Thêm |
| Gateway upstream | `APISIX_AI_SERVICE_HOST/PORT` | `ai-service` / `8000` | Thêm (khớp `feat/aie`) |
| TCP | `TCP_USER_SERVICE_HOST/PORT`, `TCP_NOTIFICATION_SERVICE_HOST/PORT` | `0.0.0.0` / `3411`, `3413` | Bỏ comment (port theo `docs/service-communication.md`) |
| TCP | `TCP_JOB_SERVICE_HOST/PORT` | `0.0.0.0` / `3412` | Chỉ thêm nếu FSD chốt job-service là TCP server (`services.md` ghi 3412, `service-communication.md` ghi client only) |
| AI service | `AI_SERVICE_MOCK` | `true` | Thêm (DI swap Mock/Real, `ai-integration.md` §7); biến base URL do FSD đặt khi làm S2-AIE-5 |
| gRPC | `GRPC_*` | — | Giữ cho tới khi S0-FSD-2 xong |

## `.env.example` riêng của service

| File | Biến | Giá trị mẫu |
|---|---|---|
| `apps/user-service/.env.example` | `USER_SERVICE_DB_DATABASE` | `user_db` |
| `apps/notification-service/.env.example` | `NOTIFICATION_SERVICE_DB_DATABASE` | `notification_db` |
| `apps/job-service/.env.example` (FSD scaffold) | `JOB_SERVICE_DB_*` | `job_db` |
| `apps/interview-service/.env.example` (FSD scaffold) | `INTERVIEW_SERVICE_DB_*` | `interview_db` |
| `apps/ai-service/.env.example` (AIE) | `LLM_*`, `EMBEDDING_*` (+ `AI_DB_URL` khi có RAG) | placeholder |
| `apps/data-pipeline/.env.example` (feature 005) | `LLM_API_KEY`, `LLM_BASE_URL`, `AI_DB_URL` | placeholder |

Host DB: `db` + port `5432` khi service chạy trong Docker; `localhost` + `5534` khi chạy `pnpm dev` trên máy host.
