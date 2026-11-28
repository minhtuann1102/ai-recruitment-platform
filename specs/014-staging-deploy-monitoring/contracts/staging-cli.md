# Contract: lệnh vận hành staging (`infra/staging/scripts/`)

Sửa 2026-11-28: GHCR thay Artifact Registry + WIF; bỏ migrator NestJS và `issue-test-jwt.sh`.

Mọi lệnh: `set -euo pipefail`; in từng bước; thoát 0 = thành công, 1 = lỗi nghiệp vụ (đã dừng an toàn), 2 = thiếu cấu
hình / tham số. Biến dùng chung đọc từ env hoặc `infra/staging/.staging.local` (không commit): `GCP_PROJECT`,
`GCP_ZONE` (mặc định `asia-southeast1-b`), `VM_NAME` (mặc định `hireready-staging`).

| Lệnh | Chạy ở | Làm gì | Chạy lại |
|---|---|---|---|
| `provision-gcp.sh` | máy DE (gcloud đã login) | bật API; tạo IP tĩnh, firewall (80/443, 22 từ IAP), SA của VM + quyền (log, metric, ghi bucket), bucket sao lưu + lifecycle 7 ngày, snapshot schedule, VM `e2-standard-2` | an toàn: tài nguyên đã có thì bỏ qua, in "exists" |
| `bootstrap-vm.sh` | VM (qua IAP) | cài Docker + Compose, Ops Agent; tạo `/opt/ai-recruit/{env,state}`; cài cron sao lưu | an toàn |
| `deploy.sh [sha]` | máy DE | chép `infra/staging/{docker-compose.staging.yml,Caddyfile}` lên VM → IAP SSH → `deploy-on-vm.sh <sha>` (mặc định: tag `main`) | — |
| `deploy-on-vm.sh <sha>` | VM | kiểm `.env` + `env/*.env` đủ biến → kiểm image tồn tại trên GHCR → `pull` → `up -d db` → `run --rm ai-session-setup` (lỗi → thoát 1, `failed_step=session_setup`, chưa đụng ai-service) → `up -d` → chờ health có `build` = sha ≤ 5 phút (lỗi → thoát 1, ghi `failed_step`) → ghi `deploy-state.json` → prune image giữ 2 bản | cùng sha: không đổi gì, health xanh |
| `rollback.sh` | máy DE | IAP SSH → `deploy-on-vm.sh <previous>` | — |
| `backup-postgres.sh` | VM (cron 02:00) | `pg_dump -Fc ai_session` → GCS; log `backup_ok` / `backup_failed` | mỗi lần một object mới |
| `restore-postgres.sh <object> [--target <db_moi>]` | VM | tải bản sao lưu → `pg_restore` vào DB đích **trống** (không trống → thoát 1) → in số bản ghi mỗi bảng | — |
| `monitoring/apply-monitoring.sh` | máy DE | tạo / cập nhật kênh email, uptime check, 8 policy, dashboard theo `displayName` | an toàn |

Build image không phải lệnh tay: workflow `build-images.yml` chạy khi CI trên `main` xanh, đẩy
`ghcr.io/minhtuann1102/ai-recruitment-platform/<service>:<sha>` + `:main`.

`deploy-state.json`: [data-model §1](../data-model.md).
