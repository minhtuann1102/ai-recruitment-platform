# AI Recruitment Platform

Hệ thống tuyển dụng trực tuyến ngành CNTT tích hợp AI Agentic phỏng vấn luyện tập.

**Đồ án tốt nghiệp** — Nhóm 3 người, 09/2026 → 12/2026.

## Giới thiệu

Platform giúp:
- **Candidate:** tìm việc IT, ứng tuyển, luyện phỏng vấn với AI
- **Employer:** đăng tin tuyển dụng, quản lý ứng viên, xem kết quả phỏng vấn ứng viên
- **Admin:** quản trị hệ thống, duyệt tin, quản lý danh mục và bộ câu hỏi

**Điểm nổi bật:** AI Agentic interview — phỏng vấn luyện tập thông minh với scoring theo tiêu chí, agent quyết định đào sâu / chuyển hướng / giữ độ khó.

## Kiến trúc

```
Client (Browser)
     │
     ▼
Apache APISIX (API Gateway, JWT auth, RBAC)
     │
     ├── auth-service      (NestJS, TCP client)
     ├── user-service       (NestJS, TCP server)
     ├── job-service        (NestJS, TCP server)
     ├── interview-service  (NestJS, REST client → AI)
     ├── notification-svc   (NestJS, TCP server)
     └── ai-service         (FastAPI, mock/real)
```

- **Backend:** NestJS 11 microservices, monorepo (Turborepo + pnpm)
- **Database:** PostgreSQL 16 (DB per service), Redis 8.0
- **Gateway:** Apache APISIX 3.14
- **AI Service:** Python FastAPI (mock hiện tại, tích hợp LLM + RAG sau)
- **Frontend:** Next.js (apps/web)
- **Storage:** MinIO (S3-compatible, lưu CV)
- **ORM:** MikroORM 7.x

Chi tiết: [docs/architecture/overview.md](docs/architecture/overview.md)

## Cấu trúc monorepo

```
ai-recruitment-platform/
├── apps/
│   ├── auth-service/          # Dang ky, dang nhap, JWT, RBAC
│   ├── user-service/          # Ho so nguoi dung, ung vien, cong ty
│   ├── job-service/           # Tin tuyen dung, ung tuyen, ky nang
│   ├── interview-service/     # Phong van AI, Q&A, scoring
│   ├── notification-service/  # Email, thong bao
│   ├── ai-service/            # FastAPI (mock)
│   └── web/                   # Next.js frontend
├── libs/
│   ├── common/                # Shared: config, enums, decorators, DTOs
│   ├── core/                  # Base entity, microservice factory, guards
│   └── email-template/        # Email templates
├── config/
│   └── apisix/                # APISIX gateway config
├── docs/                      # Tai lieu kien truc, conventions
│   ├── architecture/
│   │   ├── overview.md
│   │   ├── services.md
│   │   ├── data-model.md
│   │   ├── ai-integration.md
│   │   └── adr/               # Architecture Decision Records
│   ├── conventions.md
│   └── sprint-plan.md
├── docker-compose.yml
├── turbo.json
└── package.json
```

## Chạy nhanh (Local Development)

### Yêu cầu

- Node.js >= 20
- pnpm >= 10
- Docker & Docker Compose

### Bước 1: Clone & cài dependencies

```bash
git clone <repo-url>
cd ai-recruitment-platform
pnpm install
```

### Bước 2: Cấu hình environment

```bash
cp .env.example .env
# Chinh sua .env theo moi truong local

# Moi service cung can .env rieng
cd apps/auth-service && cp .env.example .env
cd apps/user-service && cp .env.example .env
# ... tuong tu cho cac service khac
```

### Bước 3: Khởi động infrastructure

```bash
docker compose up -d
```

Container khởi động: PostgreSQL (nhiều DB), Redis, APISIX, etcd, MinIO, mock ai-service.

### Bước 4: Chạy migration

```bash
pnpm migration:up
```

### Bước 5: Chạy development

```bash
# Tat ca services
pnpm dev

# Hoac chi 1 service
pnpm dev --filter=auth-service
```

### Bước 6: Sync APISIX config

```bash
docker compose run --rm adc adc sync -f conf/apisix-dev.yaml
```

## Truy cập

| Service | URL |
|---|---|
| APISIX Gateway | http://localhost:9080 |
| Auth API | http://localhost:9080/auth/api |
| Auth Swagger | http://localhost:9080/auth/swagger |
| User API | http://localhost:9080/user/api |
| Job API | http://localhost:9080/job/api |
| Interview API | http://localhost:9080/interview/api |
| AI Health | http://localhost:9080/ai/api/health |
| Redis Insight | http://localhost:5544 |
| MinIO Console | http://localhost:9001 |

## Thêm service mới

1. Copy scaffold từ service có sẵn:
   ```bash
   cp -r apps/user-service apps/new-service
   ```

2. Sửa `package.json` — đổi name sang `@ai-recruit/new-service`

3. Tạo database trong Docker init script

4. Cập nhật `mikro-orm.config.ts` — trỏ đến DB mới

5. Thêm APISIX route trong `config/apisix/conf/apisix-dev.yaml`

6. Thêm env vars vào `.env.example` và `turbo.json` > `globalEnv`

7. Chạy:
   ```bash
   pnpm install
   docker compose run --rm adc adc sync -f conf/apisix-dev.yaml
   pnpm dev --filter=new-service
   ```

## Scripts

| Command | Mô tả |
|---|---|
| `pnpm dev` | Chạy tất cả services (development) |
| `pnpm build` | Build tất cả |
| `pnpm check-types` | Kiểm tra TypeScript types |
| `pnpm lint` | Lint code |
| `pnpm test` | Chạy tests |
| `pnpm migration:up` | Chạy DB migrations |
| `pnpm format` | Format code với Prettier |

## Tech Stack

| Component | Version | Mô tả |
|---|---|---|
| Node.js | 22.15 | Runtime |
| NestJS | 11 | Backend framework |
| TypeScript | 6.x | Language |
| PostgreSQL | 16 | Database (per service) |
| MikroORM | 7.x | ORM |
| Redis | 8.0 | Cache |
| Apache APISIX | 3.14 | API Gateway |
| Python FastAPI | — | AI Service |
| Next.js | — | Frontend |
| MinIO | — | Object storage (CV) |
| Turborepo | latest | Monorepo build |
| pnpm | 10.x | Package manager |
| Docker Compose | latest | Containerization |

## Tài liệu

- [Tổng quan kiến trúc](docs/architecture/overview.md)
- [Danh mục service](docs/architecture/services.md)
- [Data model](docs/architecture/data-model.md)
- [Tích hợp AI](docs/architecture/ai-integration.md)
- [Architecture Decision Records](docs/architecture/adr/)
- [Quy ước dự án](docs/conventions.md)
- [Sprint plan](docs/sprint-plan.md)
- [Giao tiếp giữa services](docs/service-communication.md)

## License

MIT
