# Contract: host công khai của staging (Caddy, `infra/staging/Caddyfile`)

Thay `gateway-staging-routes.md` (APISIX, bỏ 2026-11-28). `<host>` = `hireready.tuannm.app` (DNS: A wildcard `*.hireready` → IP VM); tên host là
biến `AI_HOST`, `VOICE_HOST`, `DEMO_HOST` trong `.env` của compose (FR-009). http → https tự động.

| Host | Upstream | Ai gọi | Xác thực | Chặn (404) | Ghi chú |
|---|---|---|---|---|---|
| `ai.<host>` | `ai-service:8000` | backend FSD (server) | `X-Internal-Token` = `AI_SERVICE_INTERNAL_TOKEN`, ai-service tự kiểm | `/dev/*`, `/metrics` | SSE không gom (Caddy tự flush `text/event-stream`), không nén; thân request ≤ 12 MB |
| `voice.<host>` | `voice-service:8020` | backend FSD (server) | `X-Internal-Token` = `VOICE_SERVICE_INTERNAL_TOKEN`, voice-service tự kiểm | `/metrics` (service không đòi token cho đường này) | thân request ≤ 12 MB |
| `demo.<host>` | `ai-service:8000` | trình duyệt GVHD / mentor | basic auth (`DEMO_USER` + `DEMO_PASSWORD_HASH`); Caddy gắn `X-Internal-Token` ghi đè giá trị client | mọi đường ngoài danh sách dưới | `/` → `/dev/interview`; request ghi (không GET / HEAD) có `Sec-Fetch-Site` khác `same-origin` → 403 (CSRF qua basic auth đã nhớ; dự án khác dưới `tuannm.app` là `same-site` nên cũng chặn; thiếu header thì cho qua); bỏ header `Authorization` trước khi tới ai-service |

Danh sách đường của host demo (lấy từ `fetch` trong `apps/ai-service/app/static/interview/*.js`, PR #120):
`/dev/interview`, `/dev/interview/*`, `/dev/voice/*`, `/api/health`, `/api/start`, `/api/next-turn`, `/api/finalize`,
`/api/cv/parse`, `/api/jd/parse`, `/api/stt/phrases`. Trang đổi đường gọi → sửa danh sách này cùng PR.

## Mã trả về mong đợi

| Lời gọi | Mã |
|---|---|
| `GET https://ai.<host>/api/health`, `GET https://voice.<host>/api/health` | 200 |
| `POST https://ai.<host>/api/start` không token / sai token | 401 |
| `GET https://ai.<host>/metrics`, `GET https://voice.<host>/metrics`, `GET https://ai.<host>/dev/play` | 404 |
| `GET https://demo.<host>/dev/interview` không mật khẩu | 401 |
| `GET https://demo.<host>/docs` có mật khẩu | 404 |
| `POST https://demo.<host>/api/cv/parse` có mật khẩu + `Sec-Fetch-Site: cross-site` hoặc `same-site` | 403 |
| `GET https://demo.<host>/dev/interview` có mật khẩu, ai-service chưa bật trang dev | 404 (từ ai-service) |

## Token

- `AI_SERVICE_INTERNAL_TOKEN`: backend FSD, Caddy (host demo), ai-service.
- `VOICE_SERVICE_INTERNAL_TOKEN`: backend FSD, ai-service (proxy `/dev/voice/*`), voice-service.
- Không token nào tới trình duyệt. Đổi token: sửa `.env`, `docker compose up -d` (Caddy + service nạp lại), báo FSD.
