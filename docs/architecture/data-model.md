# Data Model

> ERD sơ bộ theo từng service. Mỗi service sở hữu DB riêng (xem [ADR-002](adr/adr-002-database-per-service.md)).
> **Lưu ý:** Đây là thiết kế dự kiến. Cần đối chiếu với ERD 14 bảng của nhóm (nếu có). Nếu mâu thuẫn, SRS/ERD của nhóm thắng.

## 1. user-service — `user_db`

```mermaid
erDiagram
    users {
        uuid id PK
        string email UK
        string first_name
        string last_name
        string full_name
        date date_of_birth
        varchar gender "Male | Female | Other"
        string phone_number
        string avatar
        boolean is_active
        string password "bcrypt hash, hidden"
        boolean email_verified
        varchar role "Admin | Candidate | Employer"
        timestamp password_changed_at
        string google_id
        string google_name
        string google_avatar
        boolean is_2fa_enabled
        timestamp created_at
        timestamp updated_at
        timestamp deleted_at "soft delete"
    }

    candidate_profiles {
        uuid id PK
        uuid user_id FK "unique, 1-1 voi users"
        string title "VD: Backend Developer"
        text summary
        int experience_years
        string education
        int desired_salary_min
        int desired_salary_max
        string desired_location
        boolean is_open_to_work
        string linkedin_url
        string portfolio_url
        jsonb skills "array skill slugs, denormalized"
        timestamp created_at
        timestamp updated_at
    }

    company_profiles {
        uuid id PK
        uuid user_id FK "unique, 1-1 voi users (role=Employer)"
        string company_name
        text description
        string logo
        string website
        string industry
        string company_size "1-10 | 11-50 | 51-200 | 201-500 | 500+"
        string address
        string city
        int founded_year
        timestamp created_at
        timestamp updated_at
    }

    users ||--o| candidate_profiles : "Candidate co 1 profile"
    users ||--o| company_profiles : "Employer co 1 profile"
```

**Ghi chú:**
- `users` đã có sẵn trong starter. Cần thêm `role` values (Candidate, Employer) và xóa các field không cần (google_id nếu không dùng Google OAuth).
- `candidate_profiles.skills` là JSONB denormalized (array slug) để hiển thị nhanh. Source of truth cho skills nằm ở `job_db.skills`.

---

## 2. job-service — `job_db`

```mermaid
erDiagram
    skills {
        uuid id PK
        string name UK "VD: React, Node.js, Python"
        string slug UK "VD: react, nodejs, python"
        string category "VD: Frontend, Backend, DevOps"
        timestamp created_at
    }

    experience_levels {
        uuid id PK
        string name UK "VD: Intern, Junior, Mid, Senior, Lead"
        int sort_order
    }

    job_postings {
        uuid id PK
        uuid employer_id "user ID cua Employer"
        string title
        text description
        text requirements
        int salary_min
        int salary_max
        string salary_currency "VND | USD"
        string location
        varchar work_type "remote | onsite | hybrid"
        uuid experience_level_id FK
        varchar status "draft | open | closed"
        date deadline
        timestamp created_at
        timestamp updated_at
        timestamp deleted_at "soft delete"
    }

    job_skills {
        uuid job_id FK
        uuid skill_id FK
    }

    applications {
        uuid id PK
        uuid job_id FK
        uuid candidate_id "user ID cua Candidate"
        varchar status "pending | reviewing | interview | accepted | rejected | withdrawn"
        text cover_letter
        string cv_url "MinIO URL"
        timestamp applied_at
        timestamp updated_at
    }

    application_events {
        uuid id PK
        uuid application_id FK
        varchar from_status
        varchar to_status
        text note
        uuid changed_by "user ID nguoi doi trang thai"
        timestamp created_at
    }

    saved_jobs {
        uuid id PK
        uuid candidate_id "user ID"
        uuid job_id FK
        timestamp created_at
    }

    job_postings ||--o{ job_skills : "co nhieu skills"
    skills ||--o{ job_skills : "duoc nhieu job dung"
    job_postings ||--|| experience_levels : "yeu cau cap bac"
    job_postings ||--o{ applications : "nhan nhieu ho so"
    applications ||--o{ application_events : "lich su trang thai"
    job_postings ||--o{ saved_jobs : "duoc nhieu nguoi luu"
```

**Ghi chú:**
- `employer_id`, `candidate_id` là user ID từ user-service. **Không có FK constraint cross-DB** — chỉ lưu UUID, validate qua TCP call.
- `cv_url` trỏ đến MinIO object. Upload qua job-service endpoint, lưu vào MinIO, trả về URL.
- `application_events` là audit trail — mỗi lần đổi status tạo 1 event.
- Index gợi ý: `job_postings(status, created_at)`, `applications(job_id, status)`, `applications(candidate_id)`, `saved_jobs(candidate_id, job_id)` UNIQUE.

---

## 3. interview-service — `interview_db`

```mermaid
erDiagram
    question_bank {
        uuid id PK
        string category "VD: Backend, Frontend, System Design"
        string subcategory "VD: Node.js, React, Database"
        varchar difficulty "easy | medium | hard"
        text question_text
        jsonb expected_topics "['REST API', 'HTTP methods', 'status codes']"
        uuid created_by "Admin user ID"
        timestamp created_at
        timestamp updated_at
    }

    interview_sessions {
        uuid id PK
        uuid candidate_id "user ID"
        uuid job_id "nullable, lien ket voi job posting"
        varchar status "in_progress | completed | abandoned"
        string category "VD: Backend, Frontend"
        varchar difficulty "easy | medium | hard"
        int total_turns
        jsonb summary_scores "tong hop diem sau khi ket thuc"
        timestamp started_at
        timestamp completed_at
        timestamp created_at
    }

    interview_turns {
        uuid id PK
        uuid session_id FK
        int turn_number
        text question_text
        varchar question_source "bank | ai"
        text candidate_answer
        jsonb scores "nullable, ghi luc finalize: {technical_accuracy, relevance, completeness, extensibility}"
        text comment "nullable, nhan xet cua Evaluator, ghi luc finalize"
        varchar answer_signal "weak | ok | strong, tin hieu so bo noi bo"
        varchar agent_decision "deepen | switch_topic | keep_difficulty"
        text agent_reasoning
        text next_question_hint "goi y cau hoi tiep (tu AI)"
        timestamp created_at
    }

    interview_results {
        uuid id PK
        uuid session_id FK "unique, 1-1"
        jsonb strengths "['Hieu biet OOP tot', 'Giai thich ro rang']"
        jsonb improvements "['Can hoc them ve testing', 'Thieu kien thuc DB']"
        float overall_score "0.0 - 10.0"
        jsonb criteria_averages "{technical: 7.5, relevance: 8.0, ...}"
        text ai_summary "Tong hop tu AI (tuong lai)"
        timestamp created_at
    }

    interview_sessions ||--o{ interview_turns : "gom nhieu luot"
    interview_sessions ||--o| interview_results : "ket qua tong hop"
```

**Ghi chú:**
- `interview_turns.scores` và `comment` **nullable**, được ghi một lần khi finalize (Evaluator chấm cuối phiên). `answer_signal` ghi mỗi lượt, chỉ dùng nội bộ. `scores` là JSONB chứa điểm theo 4 tiêu chí:
  - `technical_accuracy` (0-10): độ chính xác kỹ thuật
  - `relevance` (0-10): mức độ liên quan đến câu hỏi
  - `completeness` (0-10): độ đầy đủ câu trả lời
  - `extensibility` (0-10): khả năng mở rộng / chiều sâu
- `agent_decision` là quyết định của AI agent:
  - `deepen`: đào sâu hơn về chủ đề hiện tại
  - `switch_topic`: chuyển sang chủ đề khác
  - `keep_difficulty`: giữ nguyên độ khó
- `interview_results` chỉ tạo khi session `completed`.
- Index gợi ý: `interview_sessions(candidate_id, status)`, `interview_turns(session_id, turn_number)`.

---

## 4. notification-service — `notification_db`

```mermaid
erDiagram
    notifications {
        uuid id PK
        uuid user_id "nguoi nhan"
        varchar type "email | in_app"
        string title
        text body
        boolean is_read "default false"
        jsonb metadata "context data tuy theo loai"
        timestamp created_at
    }
```

**Ghi chú:**
- Table `notifications` thêm sau khi implement thông báo in-app (có thể Sprint 4-5).
- Hiện tại notification-service chỉ gửi email qua SMTP/SES, không lưu trữ.

---

## 5. ai-service — `ai_db` (tương lai)

```mermaid
erDiagram
    knowledge_chunks {
        uuid id PK
        text content "noi dung kien thuc"
        vector embedding "pgvector, 1536 dims"
        jsonb metadata "{source, category, subcategory}"
        timestamp created_at
    }
```

**Ghi chú:**
- DB này **tạo từ Sprint 0** (DE init script tạo database, AIE setup pgvector extension + table).
- LLM: **OpenAI GPT-4o-mini**. Embedding: **text-embedding-3-small** (1536 dims).
- Image: `pgvector/pgvector:pg16` (thay vì postgres:16 thông thường).
- `embedding` dùng cho RAG — truy vấn semantic similarity.
- 3 nguồn: Interview Q&A (`interview_qa`), Job Descriptions crawled (`job_description`), Textbook/Tutorial (`textbook`).

---

## Tổng hợp bảng

| Service | Số bảng | Bảng chính |
|---|---|---|
| user-service | 3 | users, candidate_profiles, company_profiles |
| job-service | 6 | job_postings, skills, job_skills, applications, application_events, saved_jobs |
| interview-service | 4 | question_bank, interview_sessions, interview_turns, interview_results |
| notification-service | 1 | notifications |
| ai-service | 1 | knowledge_chunks (active từ Sprint 0) |
| **Tổng** | **15** | |

> 15 bảng, gần với ERD 14 bảng của nhóm. Chênh lệch có thể do `application_events` (audit trail) hoặc `saved_jobs`. Cần đối chiếu khi nhóm cung cấp ERD gốc.
