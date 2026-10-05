# Research: Platform Foundation

Mỗi mục: Decision / Rationale / Alternatives. Mục đánh dấu **VERIFY** cần kiểm chứng ngay lúc implement.

## R1. Thứ tự merge với `origin/feat/aie` và việc đổi import

- **Decision**: PR đổi tên (PR-1) làm atomic bằng script find/replace, merge đầu tiên trong Sprint 0 tuần 2.
  Nếu AIE merge được `feat/aie` trong ≤ 1 ngày thì merge nó trước, PR-1 đổi tên luôn container ai-service.
- **Rationale**: `@app/*` xuất hiện trong 62 file TS + `tsconfig.json` paths — chính các file FSD sửa cho
  S0-FSD-2 (gRPC→TCP). Merge sớm thì FSD chỉ rebase một lần. `feat/aie` chỉ đụng 1 block trong
  `docker-compose.yml` và thêm service trong `apisix-dev.yaml` → xung đột nhỏ.
- **Alternatives**: Giữ alias `@app/*` trong tsconfig, chỉ đổi tên package → không động 62 file nhưng vi phạm
  constitution VII (không giữ tên starter song song) và gây nhầm lẫn lâu dài. Bị loại.

## R2. Image database

- **Decision**: `pgvector/pgvector:pg16` cho service `db` (thay `postgres:16-alpine`).
- **Rationale**: `docs/architecture/data-model.md` yêu cầu; `ai_db` cần extension `vector`. Một image cho cả
  5 DB, không cần container riêng.
- **Alternatives**: `postgres:16` + cài pgvector bằng Dockerfile riêng → thêm build step, không cần thiết.
- **Lưu ý**: Volume `.docker/volumes/pgdata` cũ tạo bởi image alpine. Cùng major 16 nhưng khác libc
  (musl vs glibc) → có thể lệch collation. Khuyến nghị reset volume dev (dữ liệu dev, chấp nhận được).

## R3. Tạo database idempotent

- **Decision**: `scripts/init-databases.sh` mount vào `/docker-entrypoint-initdb.d/`, dùng
  `SELECT 'CREATE DATABASE x' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname='x')\gexec` cho từng DB,
  rồi `\c ai_db` + `CREATE EXTENSION IF NOT EXISTS vector`. Thêm `make db-ensure` chạy lại cùng script qua
  `docker compose exec db bash /docker-entrypoint-initdb.d/init-databases.sh` cho máy đã có volume.
- **Rationale**: entrypoint chỉ chạy init khi data dir rỗng → máy cũ thiếu DB (edge case 1). Script idempotent
  cho phép chạy lại an toàn mà không cần reset. AIE nối DDL `knowledge_chunks` (dùng `IF NOT EXISTS`) vào cuối
  cùng file theo thỏa thuận trong kickoff.
- **Alternatives**: `CREATE DATABASE` trơn như kickoff → lỗi khi chạy lại. Bị loại.

## R4. Đường dẫn volume đa nền tảng

- **Decision**: Thay `${PWD}/.docker/volumes/...` bằng `./.docker/volumes/...`.
- **Rationale**: Compose resolve đường dẫn tương đối theo thư mục chứa file compose; `PWD` không phải biến môi
  trường trong PowerShell → đường dẫn hỏng trên Windows (edge case 2).

## R5. Biến env cho DB và storage — tái dùng pattern có sẵn

- **Decision**:
  - DB: giữ pattern `{SERVICE}_SERVICE_DB_*` trong `.env.example` riêng của từng service (đang dùng trong
    `apps/user-service/src/config/database.config.ts`); đổi `*_DB_DATABASE` sang `<service>_db`. Không thêm
    `USER_DB_HOST`... vào root như kickoff gợi ý.
  - Storage: dùng `AWS_S3_*` + `STORAGE_TYPE=minio` (đã hỗ trợ trong `libs/core/src/aws-s3/aws-s3.service.ts`
    với `forcePathStyle`), `AWS_S3_URL=http://localhost:9000`. Không thêm `MINIO_*` cho service.
    `MINIO_ROOT_USER/PASSWORD` chỉ dùng cho container.
- **Rationale**: DRY, không cần sửa code config; FSD không phải đổi gì.
- **Alternatives**: Bộ biến `MINIO_*` + `USER_DB_*` theo kickoff → phải sửa config code + validation. Bị loại.

## R6. MinIO: bucket tự tạo, health check, version

- **Decision**: Service `minio` + one-shot `minio-init` (image `minio/mc`):
  `mc alias set local http://minio:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD && mc mb --ignore-existing local/$AWS_S3_BUCKET_NAME`.
  Health check `mc ready local` trong container minio. Pin tag cụ thể, không dùng `latest`.
- **Rationale**: FR-004 (bucket tự tạo), constitution V (tái lập được).
- **VERIFY**: Chính sách phát hành image Docker community của MinIO đã thay đổi trong 2025. Lúc implement cần
  xác nhận tag còn pull được; nếu không, chọn image S3-compatible thay thế và ghi lại tại đây.

## R7. Route APISIX

- **Decision**: Copy pattern `user-service` trong `config/apisix/conf/apisix-dev.yaml`: route public
  (priority 1: `/{svc}/api`, `/{svc}/swagger*`, health) tắt `jwt-auth`; route chính (priority 0: `/{svc}/*`)
  bật `jwt-auth` + `serverless-post-function` set `x-auth-user`; `proxy-rewrite` bỏ prefix. Upstream từ env
  `APISIX_{SVC}_SERVICE_HOST/PORT`. Route `/ai/*` lấy nguyên từ `feat/aie`.
- **Rationale**: Nhất quán (constitution II), ít rủi ro.
- **Ghi chú**: Lua của `x-auth-user` đang lặp ở mỗi route; `config/apisix/lua/jwt_claim_processor.lua` đã tồn
  tại. Gom về một chỗ là cải tiến sau, không làm trong feature này (YAGNI).

## R8. CI pipeline

- **Decision**: `.github/workflows/ci.yml`, trigger `pull_request` + `push` vào `main`, `develop`.
  - Job `node`: checkout → `pnpm/action-setup` (đọc `packageManager`) → `setup-node` 22 có cache pnpm →
    `pnpm install --frozen-lockfile` → `pnpm lint` → `pnpm check-types` → `pnpm test`.
  - Job `python` (matrix `app: [ai-service, data-pipeline]`): bỏ qua nếu thư mục không có
    `requirements.txt`; `setup-python` 3.11 → cài `requirements*.txt` → `pytest`.
  - `concurrency` hủy run cũ cùng ref; không dùng secret.
- **Rationale**: FR-009..011, SC-004. Turbo cache cục bộ trong runner là đủ, chưa cần remote cache.
- **VERIFY**: Root devDependencies có `@oxlint/binding-darwin-arm64` và `@turbo/darwin-arm64` (gói chỉ chạy trên
  macOS ARM). Nếu `pnpm install` trên Linux/Windows báo unsupported platform → gỡ khỏi `package.json`
  (oxlint/turbo tự kéo binary theo nền tảng qua optionalDependencies) và sinh lại lockfile trong PR-1.
  - **Kết quả T003 (2026-10-05)**: `pnpm install --frozen-lockfile` thành công trên Windows (pnpm 10.17.0) dù có
    2 gói darwin-arm64 → không gỡ (T004 N/A). Linux chưa thử (Docker tắt); job `node` của CI (T031) sẽ xác nhận.
- **VERIFY**: `turbo.json` `test` phụ thuộc `build` → CI build toàn bộ trước test; đo thời gian, nếu > 10 phút
  cân nhắc cache.

## R10. Ngưỡng coverage 60% (constitution VI)

- **Decision**: CI của 001 chạy `pnpm test`, chưa fail theo coverage. Mỗi owner bật jest `coverageThreshold`
  (60%) trong `package.json` của service khi feature của service đó hoàn thành (DoD: S1-FSD-7, S2-FSD-10,
  S3-FSD-7). Python dùng `pytest --cov --cov-fail-under=60` khi app đạt ngưỡng.
- **Rationale**: Code starter hiện chưa đạt 60%; enforce ngay ngày đầu làm CI đỏ cho mọi PR, phản tác dụng.
- **Alternatives**: Job coverage report không chặn build → thêm cấu hình mà chưa ai đọc (YAGNI).

## R11. Secret local trong `.env.example`

- **Decision**: `JWT_SECRET` và `APISIX_KEY` giữ giá trị mẫu, ghi chú `# LOCAL ONLY — MUST override khi deploy`;
  bind admin port APISIX (`9180`) vào `127.0.0.1` trong compose. Feature 014 bắt buộc sinh giá trị mới
  (`openssl rand -hex 32`) cho staging.
- **Rationale**: US5 yêu cầu copy env mẫu là chạy được; placeholder rỗng làm hỏng JWT/ADC. `APISIX_KEY` hiện có
  vẻ là admin key mặc định của APISIX → không được lộ ra mạng ngoài localhost.
- **Alternatives**: Placeholder + script sinh secret lúc setup → thêm một bước cho mỗi máy dev, lợi ích thấp ở local.

## R12. Baseline của `main` trước PR-1 (đo 2026-10-05)

- `build`, `check-types`: xanh. `lint`: 12 lỗi oxlint có sẵn → đã sửa trong PR-1 (commit riêng, không đổi
  behavior) vì husky pre-commit (lint-staged) chặn commit các file bị đổi import.
- `test`: đỏ vì jest "No tests found" (repo chưa có test). Đề xuất cho T031: thêm `--passWithNoTests` vào script
  `test` của từng app — không phải bỏ qua test, mà là chưa có test; test thật thêm theo DoD của từng feature.
- Lockfile khi đổi tên: `pnpm install` không frozen re-resolve peer webpack/esbuild (+102 dòng, ngoài phạm vi)
  → thay vào đó sửa tay 8 dòng tên package trong `pnpm-lock.yaml`, kiểm chứng bằng `--frozen-lockfile`.

## R9. Biến môi trường gRPC

- **Decision**: Không gỡ biến `GRPC_*` trong feature này; thêm `TCP_*` theo bảng port của
  `docs/architecture/services.md` (user 3411, job 3412, notification 3413). Gỡ `GRPC_*` thuộc S0-FSD-2.
- **Rationale**: Tránh làm hỏng code FSD đang chuyển transport.
