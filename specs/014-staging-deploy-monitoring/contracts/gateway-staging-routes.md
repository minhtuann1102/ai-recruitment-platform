# Contract: route công khai của staging (`apisix-staging.yaml`)

Gốc: `https://${STAGING_API_HOST}` (Caddy → APISIX). Bảng là toàn bộ bề mặt công khai; route không có trong bảng →
404 từ APISIX. Chi tiết quyết định: [research R5–R7](../research.md).

| Prefix | Upstream | JWT | Ghi chú |
|---|---|---|---|
| `/auth/api/login`, `/auth/api` (đăng ký / refresh theo dev) | auth-service:3300 | không | như dev |
| `/auth/*` | auth-service | có | |
| `/user/api`, `/user/swagger` | user-service:3301 | không | như dev |
| `/user/*` | user-service | có | header `x-auth-user` do gateway gắn (như dev) |
| `/notification/api`, `/notification/swagger` | notification-service:3303 | không | như dev |
| `/notification/*` | notification-service | có | |
| `/<svc>/api/health` (auth, user, notification, ai) | service tương ứng | không | [health-endpoints.md](health-endpoints.md) |
| `/ai/*` | ai-service:8000 | có | gateway **ghi đè** `X-Internal-Token`; timeout read 120 s |
| `/ai/metrics`, `/ai/dev/*`, `/ai/docs`, `/ai/openapi.json` | — | — | 404 (chặn) |

## Giới hạn tốc độ (`limit-count`, khóa `remote_addr` thật sau Caddy)

| Route | Hạn mức | Vượt |
|---|---|---|
| `/ai/api/start`, `/ai/api/cv/parse`, `/ai/api/jd/parse` | 10 / phút / IP | 429 `{statusCode: 429, message, errorCode: "RATE_LIMITED", details: null}` |
| `/ai/api/next-turn`, `/ai/api/finalize`, `/ai/api/stt/phrases` | 60 / phút / IP | 429 như trên |

## CORS

`allow_origins_by_regex`: `^https://app\.<domain>$`, `^https://<vercel-project>-[a-z0-9-]+\.vercel\.app$`;
`allow_methods: GET,POST,PUT,PATCH,DELETE,OPTIONS`; `allow_headers: Authorization,Content-Type`; không cho
`X-Internal-Token`. Chưa có frontend → chỉ regex Vercel bật khi US5.

## Không công khai

Admin API 9180 (chỉ mạng docker), Prometheus export 9091 (bind `127.0.0.1` cho Ops Agent), Postgres / Redis / MinIO
/ etcd: không publish cổng ra host.

## Khi `interview-service` có

Bỏ `/ai/*` khỏi bề mặt công khai (chỉ giữ `/ai/api/health`); interview-service gọi ai-service trong mạng nội bộ với
token nội bộ của chính nó.
