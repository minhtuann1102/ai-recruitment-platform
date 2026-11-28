# Data Model: Staging Deploy & Monitoring

Feature hạ tầng: không có bảng nghiệp vụ mới. Các "thực thể" là file / tài nguyên vận hành.

## 1. Trạng thái deploy — `/opt/ai-recruit/state/deploy-state.json` (trên VM)

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `current` | string | mã commit (40 ký tự) đang chạy |
| `previous` | string \| null | bản trước, dùng cho rollback |
| `history` | mảng ≤ 20 | `{sha, at (ISO-8601 UTC), by, action: deploy\|rollback, result: ok\|failed, failed_step?}` |

- Ghi **sau** khi mọi health xanh (deploy thành công) → `previous = current cũ`, `current = sha mới`.
- Deploy lỗi: chỉ thêm `history` với `result: failed`, không đổi `current` / `previous`.
- Rollback: `current ↔ previous` hoán đổi; `action: rollback`.

## 2. Image

`ghcr.io/minhtuann1102/ai-recruitment-platform/<service>:<sha>` (sửa 2026-11-28: GHCR thay Artifact Registry);
`<service>` ∈ {`ai-service`, `voice-service`}. Thêm tag `main` cho bản mới nhất. Package public. Dọn image cũ trên
GHCR: không bắt buộc (repo public không tính dung lượng); trên VM giữ 2 bản.

## 3. Cấu hình bí mật — trên VM, `/opt/ai-recruit/`, quyền `600`

- `.env` (biến của compose) = `infra/staging/.env.staging.example`: `IMAGE_REGISTRY`, `IMAGE_TAG` (deploy ghi), 3 tên
  host, `ACME_EMAIL`, 2 token nội bộ, `POSTGRES_PASSWORD`, `DEMO_USER`, `DEMO_PASSWORD_HASH`; thêm `ALERT_EMAIL`,
  `BACKUP_BUCKET` khi có đợt D.
- `env/ai-service.env`, `env/voice-service.env` = `apps/<service>/.env.example` điền key (LLM, Langfuse, `AI_DB_URL`,
  Blaze). Compose ghi đè `APP_ENV`, token, `SESSION_*`, `VOICE_SERVICE_URL` nên các biến đó trong file này không có tác
  dụng.
- Thiếu biến bắt buộc → `docker compose` báo lỗi (`${VAR:?}`) trước khi chạy gì; `deploy-on-vm.sh` dừng trước `pull`.

## 4. Bản sao lưu

`gs://<project>-staging-backup/pg/ai_session/<YYYYMMDD-HHMM>.dump` (`pg_dump -Fc`); lifecycle xóa sau 7 ngày. Mỗi lần
chạy ghi một dòng log có cấu trúc `backup_ok db=<db> bytes=<n> object=<path>` hoặc `backup_failed db=<db>
reason=<…>` → log-based metric cho cảnh báo #8.

## 5. Chính sách cảnh báo

Một file JSON / chính sách trong `infra/staging/monitoring/alerts/`, `displayName` = `staging-<nn>-<slug>` (khóa để
`apply-monitoring.sh` cập nhật thay vì tạo trùng). Trạng thái mở / đóng do Cloud Monitoring giữ; kênh email đọc từ
`ALERT_EMAIL`.
