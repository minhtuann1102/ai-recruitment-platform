# Contract: health endpoints

Sửa 2026-11-28: bỏ phần NestJS (đã gỡ khỏi repo ở #113).

## ai-service `GET /api/health` — thêm một trường

Giữ nguyên các trường hiện có (`status`, `version` = model, `model_loaded`, `rag`, `agents`); thêm `build` =
`APP_VERSION` (mặc định `"dev"`). Không đổi ý nghĩa `version` để không vỡ client hiện có.

## voice-service `GET /api/health` — thêm một trường

Giữ nguyên các trường hiện có; thêm `build` = `APP_VERSION` (mặc định `"dev"`).

## `APP_VERSION`

Build image truyền `--build-arg APP_VERSION=<sha>` → `ENV APP_VERSION` trong image; lệnh deploy so `build` với sha
vừa deploy để biết bản mới đã chạy.

## `/metrics`

Không đổi: ai-service đòi token, voice-service không; cả hai bị Caddy chặn từ ngoài
([staging-hosts.md](staging-hosts.md)). Ops Agent đọc trong mạng nội bộ (gửi `X-Internal-Token` cho ai-service).
