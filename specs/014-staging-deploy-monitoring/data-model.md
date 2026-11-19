# Data Model: Staging Deploy & Monitoring

Feature hạ tầng: không có bảng nghiệp vụ mới. Các "thực thể" là file / tài nguyên vận hành.

## 1. Trạng thái deploy — `/opt/ai-recruit/deploy-state.json` (trên VM)

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `current` | string | mã commit (40 ký tự) đang chạy |
| `previous` | string \| null | bản trước, dùng cho rollback |
| `history` | mảng ≤ 20 | `{sha, at (ISO-8601 UTC), by, action: deploy\|rollback, result: ok\|failed, failed_step?}` |

- Ghi **sau** khi mọi health xanh (deploy thành công) → `previous = current cũ`, `current = sha mới`.
- Deploy lỗi: chỉ thêm `history` với `result: failed`, không đổi `current` / `previous`.
- Rollback: `current ↔ previous` hoán đổi; `action: rollback`.

## 2. Image

`asia-southeast1-docker.pkg.dev/<project>/ai-recruit/<service>:<sha>`; `<service>` ∈ {`ai-service`,
`auth-service`, `user-service`, `notification-service`} + `user-service-migrator` (service có DB). Thêm tag `main` cho
bản mới nhất. Dọn trong registry: giữ 20 tag gần nhất / service (cleanup policy).

## 3. Cấu hình bí mật — `/opt/ai-recruit/.env` (trên VM, `600`)

Danh sách biến = `infra/staging/.env.staging.example` (gồm biến của `.env.example` gốc cần cho service đang chạy +
`STAGING_API_HOST`, `REGISTRY`, `APP_VERSION` do deploy ghi, `AI_SERVICE_INTERNAL_TOKEN`, `APP_ENV=staging`,
`ALERT_EMAIL`, `BACKUP_BUCKET`). Thiếu biến bắt buộc → `deploy-on-vm.sh` dừng trước khi `pull`.

## 4. Bản sao lưu

`gs://<project>-staging-backup/pg/<db>/<YYYYMMDD-HHMM>.dump` (`pg_dump -Fc`); lifecycle xóa sau 7 ngày. Mỗi lần
chạy ghi một dòng log có cấu trúc `backup_ok db=<db> bytes=<n> object=<path>` hoặc `backup_failed db=<db>
reason=<…>` → log-based metric cho cảnh báo #8.

## 5. Chính sách cảnh báo

Một file JSON / chính sách trong `infra/staging/monitoring/alerts/`, `displayName` = `staging-<nn>-<slug>` (khóa để
`apply-monitoring.sh` cập nhật thay vì tạo trùng). Trạng thái mở / đóng do Cloud Monitoring giữ; kênh email đọc từ
`ALERT_EMAIL`.
