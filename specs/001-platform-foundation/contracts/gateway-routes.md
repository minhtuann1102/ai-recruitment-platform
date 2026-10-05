# Contract: Gateway Routes (APISIX)

File cấu hình: `config/apisix/conf/apisix-dev.yaml` (sync bằng `make adcSync environment=dev`).
Pattern: copy service `user-service` (xem research R7).

| Service | Prefix | Upstream env (host / port mặc định) | Public (không JWT) | Bảo vệ (JWT + `x-auth-user`) | Trạng thái |
|---|---|---|---|---|---|
| auth-service | `/auth/*` | `APISIX_AUTH_SERVICE_HOST` / 3300 | có sẵn | có sẵn | giữ nguyên |
| user-service | `/user/*` | `APISIX_USER_SERVICE_HOST` / 3301 | `/user/api`, `/user/swagger*` | `/user/*` | giữ nguyên |
| job-service | `/job/*` | `APISIX_JOB_SERVICE_HOST` / 3302 | `/job/api`, `/job/swagger*` | `/job/*` | **mới** |
| notification-service | `/notification/*` | `APISIX_NOTIFICATION_SERVICE_HOST` / 3303 | có sẵn | có sẵn | giữ nguyên |
| interview-service | `/interview/*` | `APISIX_INTERVIEW_SERVICE_HOST` / 3304 | `/interview/api`, `/interview/swagger*` | `/interview/*` | **mới** |
| ai-service | `/ai/*` | `APISIX_AI_SERVICE_HOST` / 8000 | `/ai/api/health` | `/ai/*` (GET, POST) | từ `feat/aie` |

## Hành vi bắt buộc

- `proxy-rewrite` bỏ prefix: `^/{svc}/(.*)` → `/$1`.
- Route bảo vệ không có token hợp lệ → `401`.
- Route bảo vệ có token → header `x-auth-user` = JSON claims của JWT.
- Upstream không chạy → lỗi upstream (`502`/`503`), không ảnh hưởng route khác.
- Timeout upstream: `connect 6s`, `read/send 6s`; riêng ai-service `read/send 30s` (theo `feat/aie`).
