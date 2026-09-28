# ADR-002: Database per service

**Ngày:** 2026-09-28  
**Trạng thái:** Accepted

## Bối cảnh

Starter repo dùng chung một PostgreSQL database (`ai-agent`) cho tất cả service. Điều này vi phạm nguyên tắc service autonomy — một service có thể đọc/ghi bảng của service khác.

## Quyết định

Mỗi NestJS service sở hữu **PostgreSQL database riêng**. Không truy vấn chéo DB giữa các service.

| Service | Database | Ghi chú |
|---|---|---|
| auth-service | Không có DB riêng | Stateless JWT, gọi user-service qua TCP |
| user-service | `user_db` | users, candidate_profiles, company_profiles |
| job-service | `job_db` | job_postings, applications, skills, saved_jobs |
| interview-service | `interview_db` | sessions, turns, scores, question_bank |
| notification-service | `notification_db` | notifications |
| ai-service (tương lai) | `ai_db` | pgvector, knowledge base |

## Lý do

- **Service autonomy:** mỗi service deploy độc lập, schema riêng, migration riêng
- **Fault isolation:** DB của service A gặp vấn đề không ảnh hưởng service B
- **Scale độc lập:** có thể scale DB theo workload từng service
- **Không cross-DB join:** ép buộc giao tiếp qua API/event, architecture sạch hơn

## Hệ quả

- Docker Compose cần nhiều container PostgreSQL (hoặc init script tạo nhiều database trong cùng một PG instance cho dev local)
- Giao tiếp bằng TCP message (NestJS) hoặc REST (AI service) thay vì JOIN
- Cần correlation ID để trace request xuyên service
- Mỗi service có `mikro-orm.config.ts` riêng, trỏ đến DB riêng

## Ghi chú dev local

Để giảm tải local, có thể dùng **một PostgreSQL instance** với nhiều database (tạo bằng init script trong docker-entrypoint-initdb.d). Production mới cần tách instance.
