# ADR-006: Gộp application-service vào job-service

**Ngày:** 2026-09-28  
**Trạng thái:** Accepted

## Bối cảnh

Brief đề xuất tách `application-service` (ứng tuyển, CV, trạng thái hồ sơ) và `job-service` (tin tuyển dụng, kỹ năng, tìm kiếm) thành hai service riêng. Cần đánh giá có phù hợp với team 3 người không.

## Quyết định

**Gộp `application-service` vào `job-service`** như một module. Job-service quản lý cả tin tuyển dụng lẫn hồ sơ ứng tuyển.

## Lý do

### Ứng tuyển gắn chặt với tin tuyển dụng

- Mỗi application **luôn** tham chiếu một job_posting — không tồn tại độc lập
- Query "tất cả ứng viên của job X" là thao tác phổ biến nhất của employer
- Nếu tách: mỗi query cần cross-service call, tăng latency và complexity
- Nếu gộp: một SQL JOIN đơn giản

### Giảm overhead cho team 3 người

| Metric | 7 services (tách) | 6 services (gộp) |
|---|---|---|
| Database | 5 DB | 4 DB |
| Dockerfile | 5 | 4 |
| Migration sets | 5 | 4 |
| APISIX routes | 5 | 4 |
| CI jobs | 5 | 4 |

Mỗi service thêm khoảng 2-3 ngày setup (DB, config, Dockerfile, APISIX route, migration, test). Gộp tiết kiệm ~2-3 ngày.

### Có thể tách lại sau

Nếu sau này cần scale riêng, extract `application` module từ job-service ra service riêng. Hướng này dễ hơn chiều ngược (merge hai service đã tách).

## Cấu trúc module trong job-service

```
apps/job-service/src/modules/
├── job/                    # Tin tuyen dung
│   ├── job.controller.ts
│   ├── job.service.ts
│   └── dto/
├── application/            # Ung tuyen
│   ├── application.controller.ts
│   ├── application.service.ts
│   └── dto/
├── skill/                  # Danh muc ky nang
│   ├── skill.controller.ts
│   └── skill.service.ts
└── saved-job/              # Viec lam da luu
    ├── saved-job.controller.ts
    └── saved-job.service.ts
```

## Hệ quả

- Tổng cộng 5 NestJS service + 1 mock FastAPI = 6 services
- `job_db` chứa cả job_postings, applications, skills, saved_jobs
- API route: `/job/*` (bao gồm `/job/api/applications/*`)
- Cần RBAC để phân quyền: Candidate tạo application, Employer xem application
