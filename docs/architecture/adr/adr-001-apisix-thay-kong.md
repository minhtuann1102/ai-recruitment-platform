# ADR-001: API Gateway — APISIX thay vì Kong

**Ngày:** 2026-09-28  
**Trạng thái:** Accepted

## Bối cảnh

Starter repo (`nest-turbo-starter`) tích hợp sẵn cả Apache APISIX và Kong Gateway. Việc duy trì hai gateway tăng độ phức tạp cấu hình, docker-compose, và CI.

## Quyết định

Chỉ giữ **Apache APISIX** làm API Gateway duy nhất. Xóa toàn bộ cấu hình Kong (`docker-compose-kong.yml`, `config/kong/`).

## Lý do

| Tiêu chí | APISIX | Kong (OSS) |
|---|---|---|
| License | Apache 2.0, hoàn toàn miễn phí | OSS miễn phí, nhưng nhiều feature cần Enterprise |
| Performance | Dựa trên OpenResty/Lua, low latency | Tương đương, nhưng plugin ecosystem khác |
| Config store | etcd — declarative, sync bằng ADC CLI | PostgreSQL — nặng hơn cho config store |
| JWT auth | Built-in plugin, free | Cần Enterprise cho JWT key rotation |
| Rate limiting | Built-in plugin, free | Cần Enterprise |
| Community | Active, phát triển nhanh | Lớn hơn, nhưng chia Community/Enterprise |

## Hệ quả

- Xóa `docker-compose-kong.yml`, thư mục `config/kong/`
- Container name prefix đổi từ `nest_turbo_` sang `ai_recruit_`
- APISIX route cho mỗi service mới (job-service, interview-service, ai-service)
- Team chỉ cần học một gateway
