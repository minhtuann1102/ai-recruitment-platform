# Sprint 0 — Kickoff Guide

> 28/09 → 12/10/2026. Mục tiêu: stack chạy local, architecture chốt, mock AI có trong Docker, ai_db sẵn sàng.
> File này breakdown công việc **theo role**, có thứ tự và phụ thuộc.
> Roles: **FSD** (Fullstack Developer) | **AIE** (AI Engineer) | **DE** (Data Engineer + DevOps)

## Dependency Graph

```
DE: Rename project + Docker multi-DB + ai_db + MinIO ──┐
                                                        ├──▶ Tất cả service boot
FSD: TCP migration + Role enum ────────────────────────┘        │
                                                                ▼
FSD: Skeleton interview-service ◀── cần TCP transport đã chạy
FSD: Skeleton job-service ◀──────── cần Docker multi-DB đã chạy
AIE: Mock ai-service + ai_db setup ◀── cần Docker đã chạy
DE: APISIX routes + CI pipeline ◀── cần build thành công
```

**Tuần 1 (28/09 → 05/10):** Infra + migration song song
**Tuần 2 (05/10 → 12/10):** Scaffold services + CI + verify 

---

## DE — Data Engineer + DevOps (___________) 

### Tuần 1 — Nền tảng

#### DE-1. Đổi tên project (ngày 1-2)

**Files thay đổi:**
- `package.json` — `name: "@ai-recruit/root"`
- `apps/*/package.json` — scope `@ai-recruit/auth-service`, `@ai-recruit/user-service`...
- `libs/*/package.json` — scope `@ai-recruit/common`, `@ai-recruit/core`...
- `pnpm-workspace.yaml` — verify
- `docker-compose.yml` — container names `nest_turbo_*` → `ai_recruit_*`, network `ai-recruit-network`
- Xóa `docker-compose-kong.yml`
- Xóa `config/kong/`

**Verify:**
```bash
pnpm install    # khong loi
pnpm build      # build thanh cong
docker compose up -d   # containers boot voi ten moi
```

#### DE-2. Docker multi-DB + MinIO (ngày 2-4)

**Thay đổi `docker-compose.yml`:**

Thay 1 PG container bằng init script tạo nhiều DB:

```yaml
db:
  container_name: ai_recruit_db
  image: postgres:16
  environment:
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: secret
    POSTGRES_DB: user_db
  volumes:
    - ./scripts/init-databases.sh:/docker-entrypoint-initdb.d/init-databases.sh
  ports:
    - '5534:5432'
```

Tạo `scripts/init-databases.sh`:
```bash
#!/bin/bash
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE job_db;
    CREATE DATABASE interview_db;
    CREATE DATABASE notification_db;
    CREATE DATABASE ai_db;
EOSQL
```

Thêm MinIO:
```yaml
minio:
  image: minio/minio:latest
  container_name: ai_recruit_minio
  command: server /data --console-address ":9001"
  environment:
    MINIO_ROOT_USER: minioadmin
    MINIO_ROOT_PASSWORD: minioadmin
  ports:
    - '9000:9000'    # S3 API
    - '9001:9001'    # Console
  volumes:
    - ./.docker/volumes/minio_data:/data
```

**Cập nhật `.env.example`:**
```bash
# MinIO
MINIO_ENDPOINT=localhost
MINIO_PORT=9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=ai-recruit-files
MINIO_USE_SSL=false

# DB per service
USER_DB_HOST=localhost
USER_DB_PORT=5534
USER_DB_NAME=user_db
JOB_DB_HOST=localhost
JOB_DB_PORT=5534
JOB_DB_NAME=job_db
INTERVIEW_DB_HOST=localhost
INTERVIEW_DB_PORT=5534
INTERVIEW_DB_NAME=interview_db
NOTIFICATION_DB_HOST=localhost
NOTIFICATION_DB_PORT=5534
NOTIFICATION_DB_NAME=notification_db
```

**Verify:**
```bash
docker compose up -d
docker exec ai_recruit_db psql -U postgres -c "\l"
# Phai thay: user_db, job_db, interview_db, notification_db
# MinIO console: http://localhost:9001
```

### Tuần 2

> Mock ai-service được **AIE** own — xem section AIE bên dưới.
> ai_db đã được tạo trong DE-2 init script.

#### DE-3. APISIX routes cho service mới (ngày 7-8)

Cập nhật `config/apisix/conf/apisix-dev.yaml` — thêm route cho:
- `/job/*` → job-service:3302
- `/interview/*` → interview-service:3304
- `/ai/*` → ai-service:8000

Copy pattern từ auth-service route (JWT plugin, proxy-rewrite, serverless-post-function).

#### DE-4. CI pipeline (ngày 8-10)

Tạo `.github/workflows/ci.yml`:
```yaml
on: [push, pull_request]
jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22 }
      - run: pnpm install --frozen-lockfile
      - run: pnpm lint
      - run: pnpm check-types
      - run: pnpm test
```

#### DE-5. Cập nhật .env.example + turbo.json (ngày 10)

Thêm tất cả env vars mới vào `turbo.json` > `globalEnv`.

**File ownership DE:**
```
docker-compose.yml
docker-compose-kong.yml (xoa)
config/kong/ (xoa)
config/apisix/conf/apisix-dev.yaml
scripts/init-databases.sh (tao moi)
.env.example
.github/workflows/ci.yml (tao moi)
turbo.json (globalEnv)
package.json (root)
```

---

## AIE — AI Engineer (___________) 

### Tuần 1

#### AIE-1. Research RAG architecture (ngày 1-3)

Chốt thiết kế RAG pipeline trước khi code:
- Embedding model: `text-embedding-3-small` (1536 dims, match pgvector schema)
- Chunking: chunk_size=512 tokens, overlap=50
- Retrieval: cosine similarity top-5, filter theo source_type nếu cần
- LLM: `gpt-4o-mini` (128k context, cost ~$0.15/1M input tokens)

Document kết quả vào `docs/architecture/ai-integration.md`.

#### AIE-2. Setup ai_db + pgvector (ngày 2-4)

Sau khi DE hoàn thành DE-2 (multi-DB, đã tạo `ai_db`), thêm vào cuối `scripts/init-databases.sh`:

```bash
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    \c ai_db
    CREATE EXTENSION IF NOT EXISTS vector;
    CREATE TABLE IF NOT EXISTS knowledge_chunks (
        id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        content     TEXT NOT NULL,
        embedding   vector(1536),
        source_type VARCHAR(50),
        metadata    JSONB,
        created_at  TIMESTAMPTZ DEFAULT now()
    );
    CREATE INDEX IF NOT EXISTS knowledge_chunks_embedding_idx
        ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops);
EOSQL
```

**Verify:**
```bash
docker exec ai_recruit_db psql -U postgres -d ai_db -c "\dx"
# Phai thay: vector extension installed
```

### Tuần 2

#### AIE-3. Mock ai-service (ngày 5-7)

**Tạo files:**
```
apps/ai-service/
├── main.py
├── Dockerfile
├── requirements.txt    # fastapi, uvicorn, openai, pgvector, sqlalchemy, python-dotenv
└── .env.example        # OPENAI_API_KEY, AI_DB_URL
```

Nội dung `main.py`: xem [ai-integration.md](architecture/ai-integration.md#5-mock-fastapi-service)

`Dockerfile`:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Thêm vào `docker-compose.yml`:
```yaml
  ai-service:
    build: ./apps/ai-service
    container_name: ai_recruit_ai_service
    ports: ["8000:8000"]
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - AI_SERVICE_MOCK=true
    networks: [ai-recruit-network]
```

**Verify:**
```bash
docker compose up -d ai-service
curl http://localhost:8000/api/health
curl http://localhost:9080/ai/api/health  # qua APISIX
```

#### AIE-4. Setup OpenAI SDK + test connection (ngày 7-8)

```python
# test_openai_connection.py (chạy local, không commit key)
from openai import OpenAI
client = OpenAI()  # reads OPENAI_API_KEY from env

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Say hello"}]
)
print(response.choices[0].message.content)

embedding = client.embeddings.create(
    model="text-embedding-3-small",
    input="Test embedding"
)
print(f"Embedding dims: {len(embedding.data[0].embedding)}")  # should be 1536
```

**File ownership AIE:**
```
apps/ai-service/ (tao moi)
scripts/init-databases.sh (them ai_db + vector extension, phoi hop voi DE)
docs/architecture/ai-integration.md (cap nhat RAG design)
```

---

## FSD — Fullstack Developer (___________) 

### Tuần 1

#### FSD-1. Mở rộng Role enum (ngày 1-2)

**Files thay đổi:**
- `libs/common/src/enums/app.enum.ts` — thêm `Candidate`, `Employer` vào `Role`
- `libs/common/src/decorators/rbac.decorator.ts` — verify hoạt động với role mới

```typescript
export enum Role {
  Admin = 'Admin',
  Candidate = 'Candidate',
  Employer = 'Employer',
}
```

**Verify:**
```bash
pnpm check-types  # khong loi
```

#### FSD-2. Chuyển gRPC sang TCP (ngày 2-5)

> Đây là task phức tạp nhất Sprint 0. Làm trên branch riêng `chore/grpc-to-tcp`.

**Files thay đổi:**

1. **Xóa gRPC:**
   - Xóa `libs/common/src/grpc/proto/*.proto`
   - Xóa `libs/common/src/grpc/*-grpc.interface.ts`
   - Xóa `libs/common/src/grpc/grpc.constant.ts`
   - Xóa `libs/common/src/config/grpc.config.ts`
   - Giữ `libs/common/src/config/tcp.config.ts`

2. **User-service — đổi sang TCP server:**
   - `apps/user-service/src/main.ts` — thay gRPC listener bằng TCP listener (port 3411)
   - `apps/user-service/src/modules/user/user.consumer.ts` — đổi `@GrpcMethod()` sang `@MessagePattern()`
   - `apps/user-service/src/modules/app.module.ts` — xóa gRPC imports

3. **Auth-service — đổi sang TCP client:**
   - `apps/auth-service/src/modules/app.module.ts` — đổi `MicroserviceModule` từ gRPC sang TCP
   - `apps/auth-service/src/modules/auth/auth.service.ts` — đổi gRPC stub sang `ClientProxy.send()`

4. **Notification-service — đổi sang TCP server:**
   - `apps/notification-service/src/main.ts` — TCP listener port 3413
   - `apps/notification-service/src/modules/send-mail/send-mail.consumer.ts` — đổi `@GrpcMethod()` sang `@MessagePattern()`

5. **libs/core/src/microservice/** — cập nhật factory cho TCP default

**Test:**
```bash
pnpm build    # build thanh cong
pnpm dev      # tat ca services boot
# Test sign-up → login → get profile (auth goi user qua TCP)
curl -X POST http://localhost:9080/auth/api/sign-up \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"12345678Aa@"}'
```

### Tuần 2

#### FSD-3. Scaffold interview-service (ngày 6-8)

**Tạo `apps/interview-service/`** — copy pattern từ user-service:

```
apps/interview-service/
├── package.json            # @ai-recruit/interview-service
├── tsconfig.json
├── tsconfig.build.json
├── nest-cli.json
├── mikro-orm.config.ts     # tro den interview_db
├── .env.example
├── src/
│   ├── main.ts             # HTTP only, khong TCP
│   ├── config/
│   │   ├── app.config.ts
│   │   ├── database.config.ts   # interview_db
│   │   └── index.ts
│   ├── data-access/
│   │   └── all.entity.ts
│   ├── database/
│   │   └── migrations/
│   └── modules/
│       ├── app.module.ts
│       ├── app.controller.ts   # health check
│       └── app.service.ts
```

**Verify:**
```bash
pnpm dev --filter=interview-service
curl http://localhost:3304/api   # health check
curl http://localhost:9080/interview/api  # qua APISIX
```

#### FSD-4. Cập nhật auth-service sign-up (ngày 8-10)

Thêm `role` field vào `SignUpRequest`:
- `apps/auth-service/src/modules/auth/dto/request/sign-up.dto.ts` — thêm `role: Role`
- `apps/auth-service/src/modules/auth/auth.service.ts` — truyền role vào `user.create` message

**File ownership FSD (Auth+Interview tasks):**
```
libs/common/src/enums/app.enum.ts
libs/common/src/grpc/ (xoa noi dung)
libs/common/src/config/grpc.config.ts (xoa)
libs/core/src/microservice/ (cap nhat)
apps/auth-service/ (toan bo)
apps/interview-service/ (tao moi)
apps/user-service/src/main.ts (doi transport)
apps/user-service/src/modules/user/user.consumer.ts (doi decorator)
apps/notification-service/src/main.ts (doi transport)
apps/notification-service/src/modules/send-mail/send-mail.consumer.ts (doi decorator)
```

> **Lưu ý:** FSD chỉnh sửa file của user-service và notification-service CHỈ cho TCP migration. Sau Sprint 0, own toàn bộ recruitment services.

---

## FSD — Fullstack Developer: User + Job Track

> Cùng FSD ở trên. Section này gom các task liên quan user-service và job-service.

### Tuần 1

#### FSD-5. Review architecture docs (ngày 1-2)

Đọc kỹ các file trong `docs/architecture/`:
- [api-contracts.md](architecture/api-contracts.md) — focus section 2 (TCP handlers user-service) và section 3.2-3.3 (user + job HTTP API)
- [data-model.md](architecture/data-model.md) — section 1 (user_db) và section 2 (job_db)
- [service-communication.md](service-communication.md) — hiểu TCP transport

#### FSD-6. Cập nhật user-service cho DB riêng (ngày 3-5)

Sau khi DE hoàn thành DE-2 (multi-DB):
- `apps/user-service/src/config/database.config.ts` — đổi connection sang `user_db`
- `apps/user-service/mikro-orm.config.ts` — đổi DB name
- `apps/user-service/.env.example` — thêm DB env vars

**Verify:**
```bash
pnpm --filter=user-service migration:up  # chay tren user_db
pnpm dev --filter=user-service
```

#### FSD-7. Chuẩn bị entity cho candidate/company profile (ngày 5-7)

Tạo entity files (chưa cần controller/service, chỉ entity + migration):
- `apps/user-service/src/data-access/candidate-profile/candidate-profile.entity.ts`
- `apps/user-service/src/data-access/company-profile/company-profile.entity.ts`

Chạy `pnpm --filter=user-service migration:create` để tạo migration.

### Tuần 2

#### FSD-8. Scaffold job-service (ngày 6-9)

**Tạo `apps/job-service/`** — tương tự interview-service nhưng với TCP client:

```
apps/job-service/
├── package.json            # @ai-recruit/job-service
├── mikro-orm.config.ts     # tro den job_db
├── src/
│   ├── main.ts             # HTTP only (TCP client, khong server)
│   ├── config/
│   │   ├── database.config.ts   # job_db
│   │   └── ...
│   ├── data-access/
│   │   ├── job-posting/
│   │   ├── skill/
│   │   ├── application/
│   │   └── all.entity.ts
│   ├── modules/
│   │   ├── app.module.ts   # import ClientsModule cho user-service TCP
│   │   ├── job/
│   │   ├── application/
│   │   ├── skill/
│   │   └── saved-job/
```

**Verify:**
```bash
pnpm dev --filter=job-service
curl http://localhost:3302/api
curl http://localhost:9080/job/api  # qua APISIX
```

#### FSD-9. Tạo entities + migration cho job_db (ngày 9-10)

Tạo tất cả entities theo [data-model.md](architecture/data-model.md#2-job-service--job_db):
- `job-posting.entity.ts`
- `skill.entity.ts`
- `job-skill.entity.ts`
- `experience-level.entity.ts`
- `application.entity.ts`
- `application-event.entity.ts`
- `saved-job.entity.ts`

Chạy migration.

**File ownership FSD (User+Job tasks):**
```
apps/user-service/ (toan bo, sau khi FSD merge TCP migration)
apps/job-service/ (tao moi)
```

---

## Checklist Sprint 0 Done

- [ ] **DE:** Project renamed (`@ai-recruit/*`), containers `ai_recruit_*`
- [ ] **DE:** Kong removed (compose + config)
- [ ] **DE:** Docker multi-DB: user_db, job_db, interview_db, notification_db, ai_db
- [ ] **DE:** MinIO in Docker, console accessible
- [ ] **DE:** APISIX routes cho job, interview, ai
- [ ] **DE:** CI pipeline (lint + check-types + test)
- [ ] **DE:** `.env.example` và `turbo.json` cập nhật
- [ ] **AIE:** Mock ai-service boots, health check pass
- [ ] **AIE:** ai_db có pgvector extension, knowledge_chunks table created
- [ ] **AIE:** RAG architecture documented (embedding model, chunking strategy)
- [ ] **AIE:** OpenAI SDK configured, test connection GPT-4o-mini thành công
- [ ] **FSD:** Role enum: Admin, Candidate, Employer
- [ ] **FSD:** gRPC → TCP migration, auth↔user flow works
- [ ] **FSD:** Skeleton interview-service boots
- [ ] **FSD:** Sign-up accepts role parameter
- [ ] **FSD:** user-service trỏ đến user_db
- [ ] **FSD:** candidate_profiles + company_profiles entities + migration
- [ ] **FSD:** Skeleton job-service boots
- [ ] **FSD:** job_db entities + migration
- [ ] **Team:** `docker compose up -d && pnpm dev` → tất cả services boot
- [ ] **Team:** APISIX route tới mỗi service
- [ ] **Team:** Review docs, merge vào main

## Demo Sprint 0

```bash
# 1. Boot infrastructure
docker compose up -d

# 2. Verify databases
docker exec ai_recruit_db psql -U postgres -c "\l"

# 3. Boot services
pnpm dev

# 4. Verify routes
curl http://localhost:9080/auth/api          # auth health
curl http://localhost:9080/user/api          # user health
curl http://localhost:9080/job/api           # job health
curl http://localhost:9080/interview/api     # interview health
curl http://localhost:9080/ai/api/health     # ai mock health

# 5. Test auth flow (TCP)
curl -X POST http://localhost:9080/auth/api/sign-up \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"12345678Aa@","role":"Candidate"}'

# 6. Test AI mock
curl -X POST http://localhost:9080/ai/api/start \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test","category":"Backend","difficulty":"medium"}'

# 7. Verify ai_db pgvector (AIE)
docker exec ai_recruit_db psql -U postgres -d ai_db -c "\dx"
docker exec ai_recruit_db psql -U postgres -d ai_db -c "\d knowledge_chunks"
```
