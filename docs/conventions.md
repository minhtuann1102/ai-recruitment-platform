# Quy ước dự án

## 1. Đặt tên

### Files & Directories

| Loại | Convention | Ví dụ |
|---|---|---|
| NestJS module/service/controller | kebab-case | `job-posting.service.ts`, `saved-job.controller.ts` |
| Entity | kebab-case file, PascalCase class | `job-posting.entity.ts` → `class JobPosting` |
| DTO | kebab-case | `create-job-posting.dto.ts` |
| Migration | timestamp prefix | `Migration20261001120000.ts` |
| Test | `.spec.ts` (unit), `.e2e-spec.ts` (e2e) | `job.service.spec.ts` |
| React component | kebab-case file, PascalCase export | `job-card.tsx` → `export function JobCard` |
| Constant/enum | kebab-case file | `app.enum.ts`, `app.constant.ts` |

### Database

| Loại | Convention | Ví dụ |
|---|---|---|
| Table | snake_case, số nhiều | `job_postings`, `application_events` |
| Column | snake_case | `created_at`, `employer_id`, `is_active` |
| PK | `id` (UUID v7) | Tất cả entity kế thừa `BaseEntity` |
| FK | `{entity}_id` | `job_id`, `candidate_id` |
| Index | `idx_{table}_{columns}` | `idx_job_postings_status_created` |
| Enum values | PascalCase (TS) | `Role.Candidate`, `Gender.Male` |

### API Endpoints

| Rule | Ví dụ |
|---|---|
| RESTful, số nhiều | `/api/jobs`, `/api/applications` |
| Nested resource khi cần | `/api/jobs/:id/skills` |
| Action verb khi không REST | `/api/sessions/:id/answer`, `/api/sessions/:id/end` |
| Query params cho filter | `/api/jobs?status=open&skill=react&page=1` |

### Git Branch

| Loại | Pattern | Ví dụ |
|---|---|---|
| Feature | `feat/{service}/{mo-ta-ngan}` | `feat/job-service/crud-job-postings` |
| Fix | `fix/{service}/{mo-ta-ngan}` | `fix/auth-service/refresh-token-expiry` |
| Chore | `chore/{mo-ta}` | `chore/rename-project-scope` |
| Docs | `docs/{mo-ta}` | `docs/architecture-overview` |

## 2. Cấu trúc module NestJS

Mỗi module trong service theo pattern:

```
apps/{service}/src/
├── config/
│   ├── app.config.ts          # service-specific config
│   ├── database.config.ts     # MikroORM config
│   └── index.ts
├── data-access/
│   ├── {entity}/
│   │   ├── {entity}.entity.ts
│   │   ├── {entity}.repository.ts
│   │   └── index.ts
│   └── all.entity.ts          # export tat ca entities
├── database/
│   └── migrations/            # MikroORM migrations
├── modules/
│   ├── app.module.ts          # root module
│   ├── app.controller.ts      # health check
│   ├── app.service.ts
│   ├── auth/                  # JWT/RBAC guard
│   └── {feature}/
│       ├── {feature}.module.ts
│       ├── {feature}.controller.ts
│       ├── {feature}.service.ts
│       ├── {feature}.consumer.ts  # TCP handler (neu co)
│       ├── {feature}.mapper.ts    # entity ↔ DTO mapping
│       └── dto/
│           ├── create-{feature}.dto.ts
│           ├── update-{feature}.dto.ts
│           ├── get-{features}.dto.ts  # query/filter
│           └── index.ts
├── main.ts
└── mikro-orm.config.ts
```

## 3. Format lỗi và response API

### Success Response

```json
{
  "data": { ... },
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "totalPages": 8
  }
}
```

Single item không có `meta`:

```json
{
  "data": {
    "id": "019abc...",
    "title": "Backend Developer",
    "status": "open"
  }
}
```

### Error Response

```json
{
  "statusCode": 400,
  "message": "Validation failed",
  "errorCode": "VALIDATION_ERROR",
  "details": [
    { "field": "email", "message": "email must be a valid email" }
  ]
}
```

| HTTP Status | Khi nào |
|---|---|
| 200 | GET thành công, PUT/PATCH thành công |
| 201 | POST tạo mới thành công |
| 204 | DELETE thành công |
| 400 | Validation failed |
| 401 | Chưa đăng nhập / token hết hạn |
| 403 | Không có quyền (RBAC) |
| 404 | Không tìm thấy resource |
| 409 | Conflict (VD: email đã tồn tại) |
| 500 | Server error |

## 4. Commit Message

Dùng **Conventional Commits**:

```
<type>(<scope>): <mo ta ngan>

[body — neu can]
```

| Type | Khi nào |
|---|---|
| `feat` | Feature mới |
| `fix` | Sửa lỗi |
| `docs` | Thay đổi tài liệu |
| `refactor` | Refactor code không đổi behavior |
| `test` | Thêm/sửa test |
| `chore` | Config, build, dependency |
| `style` | Format, whitespace |

**Scope** là tên service hoặc module:

```
feat(job-service): add job posting CRUD endpoints
fix(auth): handle expired refresh token correctly
docs(architecture): update service communication diagram
chore(docker): add MinIO to docker-compose
```

**Quy tắc:**
- Không có reference AI/Claude/ChatGPT trong commit message
- Viết bằng tiếng Anh
- Dòng đầu <= 72 ký tự
- Imperative mood: "add" không phải "added" hay "adds"

## 5. Pull Request

### Naming

```
[{service}] {type}: {mo ta ngan}
```

Ví dụ: `[job-service] feat: add job posting CRUD with search and filter`

### PR Template

```markdown
## Summary
- Mo ta ngan nhung gi thay doi va tai sao

## Changes
- Liet ke cac thay doi chinh (bullet points)

## Testing
- [ ] Unit tests pass
- [ ] E2E tests pass (neu co)
- [ ] Manual test ket qua

## Screenshots (neu co UI)

## Checklist
- [ ] Code follow conventions
- [ ] No secrets committed
- [ ] Migration tested
- [ ] Swagger updated
```

### Review Rules

- Mỗi PR cần **ít nhất 1 reviewer**
- Không merge vào `main` trực tiếp — dùng `develop` branch
- Squash merge khi merge vào main
- Delete branch sau khi merge

## 6. Branching Strategy

```
main ← production-ready code
  └── develop ← integration branch
        ├── feat/job-service/crud
        ├── feat/user-service/profiles
        └── fix/auth-service/token-bug
```

- `main`: chỉ chứa code đã test, sẵn sàng deploy
- `develop`: nhánh tích hợp, merge feature vào đây trước
- Feature branches: tách từ `develop`, merge lại `develop`
- Hotfix: tách từ `main`, merge vào cả `main` và `develop`

## 7. Definition of Done

Một feature/story được coi là **done** khi:

- [ ] Code implement đúng spec
- [ ] Unit tests pass (coverage >= 60%)
- [ ] Swagger doc cập nhật
- [ ] No lint errors (`pnpm lint`)
- [ ] Type check pass (`pnpm check-types`)
- [ ] PR được review và approve
- [ ] Migration chạy thành công
- [ ] Manual test trên local environment
- [ ] Không có secret nào bị commit
