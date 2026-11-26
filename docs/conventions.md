# Quy ước dự án

## 1. Đặt tên

### Files & Directories

| Loại | Convention | Ví dụ |
|---|---|---|
| Python module | snake_case | `query_expansion.py` |
| Test | `test_*.py` (pytest) | `test_voice_turn.py` |

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
| Feature | `feat/{service}/{mo-ta-ngan}` | `feat/ai-service/rag-retrieval` |
| Fix | `fix/{service}/{mo-ta-ngan}` | `fix/voice-service/vad-threshold` |
| Chore | `chore/{mo-ta}` | `chore/rename-project-scope` |
| Docs | `docs/{mo-ta}` | `docs/architecture-overview` |

## 2. Format lỗi và response API

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

## 3. Commit Message

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

## 4. Pull Request

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
- Không push thẳng vào `main` — mọi thay đổi đi qua PR, CI phải xanh
- Squash merge khi merge vào main
- Delete branch sau khi merge

## 5. Branching Strategy (GitHub Flow)

```
main ← nhánh duy nhất lâu dài, luôn build được, được bảo vệ bằng CI
  ├── feat/ai-service/rag-retrieval
  ├── feat/data-pipeline/jd-crawl
  └── fix/voice-service/vad-threshold
```

- `main`: nhánh tích hợp duy nhất; branch protection yêu cầu CI xanh + ≥ 1 approve
- Feature/fix branches: tách từ `main`, PR lại vào `main`, sống ngắn (≤ vài ngày), rebase thường xuyên
- Bản ổn định để demo: gắn tag cuối mỗi sprint, vd `v0.1-sprint0`, `v0.2-sprint1`; cần quay lại bản demo thì
  checkout tag
- Hotfix: như feature branch (`fix/...`), PR vào `main`

## 6. Definition of Done

Một feature/story được coi là **done** khi:

- [ ] Code implement đúng spec
- [ ] `pytest` pass (CI xanh)
- [ ] Swagger doc / contract trong `specs/` cập nhật
- [ ] PR được review và approve
- [ ] Manual test trên local environment
- [ ] Không có secret nào bị commit
