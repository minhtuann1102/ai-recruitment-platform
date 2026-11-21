# Contract: lệnh vận hành staging (`infra/staging/scripts/`)

Mọi lệnh: `set -euo pipefail`; in từng bước; thoát 0 = thành công, 1 = lỗi nghiệp vụ (đã dừng an toàn), 2 = thiếu cấu
hình / tham số. Biến dùng chung đọc từ env hoặc `infra/staging/.staging.local` (không commit): `GCP_PROJECT`,
`GCP_ZONE` (mặc định `asia-southeast1-b`), `VM_NAME` (mặc định `ai-recruit-staging`).

| Lệnh | Chạy ở | Làm gì | Chạy lại |
|---|---|---|---|
| `provision-gcp.sh` | máy DE (gcloud đã login) | bật API; tạo IP tĩnh, firewall (80/443, 22 từ IAP), SA của VM + quyền, Artifact Registry `ai-recruit` + cleanup policy, bucket sao lưu + lifecycle 7 ngày, snapshot schedule, WIF pool / provider cho GitHub, VM | an toàn: tài nguyên đã có thì bỏ qua, in "exists" |
| `bootstrap-vm.sh` | VM (qua IAP) | cài Docker + Compose, Ops Agent; tạo `/opt/ai-recruit/{bin,state}`; cài cron sao lưu; đăng nhập registry bằng SA | an toàn |
| `deploy.sh [sha]` | máy DE | IAP SSH → `deploy-on-vm.sh <sha>` (mặc định: tag `main` mới nhất) | — |
| `deploy-on-vm.sh <sha>` | VM | kiểm `.env` đủ biến → kiểm image tồn tại → pull → migrator (lỗi → thoát 1, không đổi service) → `up -d` hạ tầng rồi ứng dụng → ADC sync → chờ health ≤ 5 phút (lỗi → thoát 1, ghi `failed_step`) → ghi `deploy-state.json` → prune image giữ 2 bản | cùng sha: không đổi gì, health xanh |
| `rollback.sh` | máy DE | IAP SSH → `deploy-on-vm.sh <previous> --no-migrate` | — |
| `backup-postgres.sh` | VM (cron 02:00) | `pg_dump -Fc` từng DB service → GCS; log `backup_ok` / `backup_failed` | mỗi lần một object mới |
| `restore-postgres.sh <db> <object> [--target <db_moi>]` | VM | tải bản sao lưu → `pg_restore` vào DB đích **trống** (không trống → thoát 1) → in số bản ghi mỗi bảng | — |
| `issue-test-jwt.sh <sub> [ttl]` | VM | ký JWT thử bằng `JWT_SECRET` + `key: ai-agent`; in ra stdout | — |
| `monitoring/apply-monitoring.sh` | máy DE | tạo / cập nhật kênh email, uptime check, 8 policy, dashboard theo `displayName` | an toàn |

`deploy-state.json`: [data-model §1](../data-model.md).
