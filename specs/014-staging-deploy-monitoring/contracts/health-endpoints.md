# Contract: health endpoints

## NestJS (`auth-service`, `user-service`, `notification-service`) — mới

`GET /api/health` (qua gateway: `/<svc>/api/health`), không cần JWT, không ghi log mỗi lần gọi.

```json
{ "status": "ok", "version": "<APP_VERSION | dev>", "checks": { "db": "ok", "redis": "ok" } }
```

- `checks` chỉ có phụ thuộc bắt buộc của service đó: auth → `redis`; user → `db`, `redis`; notification → `redis`.
- Một check lỗi → HTTP 503, `status: "error"`, check đó mang `"error"`; timeout mỗi check 2 giây.
- `HealthModule` dùng chung trong `libs/core` (research R8); service khai báo check của mình khi import.

## ai-service `GET /api/health` — thêm một trường

Giữ nguyên các trường hiện có (`status`, `version` = model, `model_loaded`, `rag`, `agents`); thêm `build` =
`APP_VERSION` (mặc định `"dev"`). Không đổi ý nghĩa `version` để không vỡ client hiện có.

## ai-service `GET /metrics`

Thêm vào `OPEN_PATHS` của middleware token nội bộ (chỉ mạng nội bộ thấy; gateway chặn `/ai/metrics`).
