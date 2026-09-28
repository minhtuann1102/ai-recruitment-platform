# API Contracts

> Hợp đồng API chi tiết để team làm việc song song. Mọi người code theo contract này, đảm bảo tương thích khi tích hợp.

## 1. Shared Types (libs/common)

### Enums

```typescript
// enums/app.enum.ts
export enum Role {
  Admin = 'Admin',
  Candidate = 'Candidate',
  Employer = 'Employer',
}

export enum JobStatus {
  Draft = 'draft',
  Open = 'open',
  Closed = 'closed',
}

export enum WorkType {
  Remote = 'remote',
  Onsite = 'onsite',
  Hybrid = 'hybrid',
}

export enum ApplicationStatus {
  Pending = 'pending',
  Reviewing = 'reviewing',
  Interview = 'interview',
  Accepted = 'accepted',
  Rejected = 'rejected',
  Withdrawn = 'withdrawn',
}

export enum InterviewSessionStatus {
  InProgress = 'in_progress',
  Completed = 'completed',
  Abandoned = 'abandoned',
}

export enum Difficulty {
  Easy = 'easy',
  Medium = 'medium',
  Hard = 'hard',
}

export enum AgentDecision {
  Deepen = 'deepen',
  SwitchTopic = 'switch_topic',
  KeepDifficulty = 'keep_difficulty',
}

export enum NotificationType {
  Email = 'email',
  InApp = 'in_app',
}
```

### Shared DTOs

```typescript
// dto/pagination.dto.ts
export class PaginationQuery {
  page?: number;    // default 1
  limit?: number;   // default 20, max 100
  sortBy?: string;  // field name
  sortOrder?: 'ASC' | 'DESC';
}

export class PaginationMeta {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
}

// dto/success-response.dto.ts
export class SuccessResponse<T> {
  data: T;
  meta?: PaginationMeta;
}
```

---

## 2. TCP Message Patterns (Inter-service)

> Giao tiếp nội bộ giữa NestJS services qua TCP transport.
> Mỗi pattern định nghĩa: message pattern, request DTO, response DTO.

### 2.1 user-service TCP Handlers

user-service **lắng nghe** các message này (implement trong `user.consumer.ts`):

#### `user.create`

Gọi bởi: auth-service (khi sign-up)

```typescript
// Request
interface CreateUserMessage {
  email: string;
  password: string;       // plain text, user-service hash bang bcrypt
  role: Role;             // 'Candidate' | 'Employer'
  firstName?: string;
  lastName?: string;
}

// Response
interface UserResponse {
  id: string;             // UUID v7
  email: string;
  firstName: string | null;
  lastName: string | null;
  fullName: string | null;
  role: Role;
  isActive: boolean;
  emailVerified: boolean;
  avatar: string | null;
  createdAt: string;      // ISO 8601
  updatedAt: string;
}
```

#### `user.findByEmail`

Gọi bởi: auth-service (khi login, forgot-password)

```typescript
// Request
interface FindUserByEmailMessage {
  email: string;
}

// Response — bao gom password hash de auth-service verify
interface UserWithPasswordResponse extends UserResponse {
  password: string;       // bcrypt hash
}
```

#### `user.getById`

Gọi bởi: job-service, interview-service (lấy thông tin user)

```typescript
// Request
interface GetUserByIdMessage {
  id: string;
}

// Response: UserResponse (khong co password)
```

#### `user.getByIds`

Gọi bởi: job-service (hiển thị employer info trong danh sách job)

```typescript
// Request
interface GetUsersByIdsMessage {
  ids: string[];
}

// Response
type GetUsersByIdsResponse = UserResponse[];
```

#### `user.update`

Gọi bởi: auth-service (đổi password, verify email)

```typescript
// Request
interface UpdateUserMessage {
  id: string;
  firstName?: string;
  lastName?: string;
  fullName?: string;
  phoneNumber?: string;
  dateOfBirth?: string;   // ISO 8601
  gender?: Gender;
  avatar?: string;
  password?: string;      // new plain text password
  emailVerified?: boolean;
  passwordChangedAt?: string;
}

// Response: UserResponse
```

### 2.2 notification-service TCP Handlers

notification-service **lắng nghe** các message này:

#### `notification.sendEmail`

Gọi bởi: auth-service (forgot password, verify email), job-service (tương lai)

```typescript
// Request
interface SendEmailMessage {
  to: string;             // email address
  template: EmailTemplate;
  context: Record<string, any>;  // template variables
}

export enum EmailTemplate {
  ForgotPassword = 'forgot-password',
  VerifyEmail = 'verify-email',
  ApplicationReceived = 'application-received',    // tuong lai
  ApplicationStatusChanged = 'application-status', // tuong lai
}

// Response: void (fire-and-forget, dung emit thay send)
```

---

## 3. HTTP API Contracts

> Chi tiết request/response cho mỗi endpoint. Client (frontend) và APISIX gọi qua HTTP.
> Tất cả response bọc trong `{ data: T }` hoặc `{ data: T, meta: PaginationMeta }`.

### 3.1 auth-service

Base URL: `/auth/api`

#### POST /sign-up

```typescript
// Request Body
interface SignUpRequest {
  email: string;          // required, valid email
  password: string;       // required, min 8 chars, 1 uppercase, 1 number, 1 special
  role: 'Candidate' | 'Employer';  // required
  firstName?: string;
  lastName?: string;
}

// Response 201
interface SignUpResponse {
  data: {
    id: string;
    email: string;
    role: Role;
    createdAt: string;
  };
}

// Error 409: email da ton tai
```

#### POST /login

```typescript
// Request Body
interface LoginRequest {
  email: string;
  password: string;
}

// Response 200
interface LoginResponse {
  data: {
    accessToken: string;
    refreshToken: string;
    user: {
      id: string;
      email: string;
      role: Role;
      fullName: string | null;
      avatar: string | null;
    };
  };
}

// Error 401: sai email/password
```

#### POST /refresh-token

```typescript
// Header: Authorization: Bearer <refreshToken>

// Response 200
interface RefreshTokenResponse {
  data: {
    accessToken: string;
    refreshToken: string;
  };
}
```

#### POST /forgot-password

```typescript
// Request Body
interface ForgotPasswordRequest {
  email: string;
}

// Response 200: { data: { message: "OTP sent to email" } }
```

#### POST /forgot-password/verify

```typescript
// Request Body
interface VerifyResetPasswordRequest {
  email: string;
  code: string;           // OTP code
}

// Response 200: { data: { resetToken: string } }
```

#### POST /reset-password

```typescript
// Request Body
interface ResetPasswordRequest {
  resetToken: string;
  newPassword: string;
}

// Response 200: { data: { message: "Password reset successfully" } }
```

#### POST /change-password

```typescript
// Header: Authorization: Bearer <accessToken>

// Request Body
interface ChangePasswordRequest {
  currentPassword: string;
  newPassword: string;
}

// Response 200: { data: { message: "Password changed" } }
// Error 400: sai current password
```

---

### 3.2 user-service

Base URL: `/user/api`

#### GET /users/me

```typescript
// Header: x-auth-user (injected by APISIX)

// Response 200
interface GetMeResponse {
  data: {
    id: string;
    email: string;
    firstName: string | null;
    lastName: string | null;
    fullName: string | null;
    dateOfBirth: string | null;
    gender: Gender | null;
    phoneNumber: string | null;
    avatar: string | null;
    role: Role;
    emailVerified: boolean;
    createdAt: string;
  };
}
```

#### PUT /users/me

```typescript
// Request Body
interface UpdateMeRequest {
  firstName?: string;
  lastName?: string;
  dateOfBirth?: string;   // YYYY-MM-DD
  gender?: Gender;
  phoneNumber?: string;
}

// Response 200: GetMeResponse
```

#### PUT /users/me/avatar

```typescript
// Request: multipart/form-data
// Field: avatar (file, max 5MB, image/jpeg | image/png | image/webp)

// Response 200
interface UpdateAvatarResponse {
  data: {
    avatar: string;       // MinIO URL
  };
}
```

#### GET /users (Admin)

```typescript
// Query: PaginationQuery + filters
interface GetUsersQuery extends PaginationQuery {
  role?: Role;
  isActive?: boolean;
  search?: string;        // search email, fullName
}

// Response 200
interface GetUsersResponse {
  data: UserResponse[];
  meta: PaginationMeta;
}
```

#### PATCH /users/:id/status (Admin)

```typescript
// Request Body
interface UpdateUserStatusRequest {
  isActive: boolean;
}

// Response 200: { data: UserResponse }
```

#### POST /candidate-profile

```typescript
// Request Body
interface UpsertCandidateProfileRequest {
  title?: string;                  // "Backend Developer"
  summary?: string;
  experienceYears?: number;
  education?: string;
  desiredSalaryMin?: number;
  desiredSalaryMax?: number;
  desiredLocation?: string;
  isOpenToWork?: boolean;
  linkedinUrl?: string;
  portfolioUrl?: string;
  skills?: string[];               // skill slugs: ["react", "nodejs"]
}

// Response 200/201
interface CandidateProfileResponse {
  data: {
    id: string;
    userId: string;
    title: string | null;
    summary: string | null;
    experienceYears: number | null;
    education: string | null;
    desiredSalaryMin: number | null;
    desiredSalaryMax: number | null;
    desiredLocation: string | null;
    isOpenToWork: boolean;
    linkedinUrl: string | null;
    portfolioUrl: string | null;
    skills: string[];
    createdAt: string;
    updatedAt: string;
  };
}
```

#### GET /candidate-profile

```typescript
// Header: JWT (Candidate)
// Response 200: CandidateProfileResponse
// Error 404: chua tao profile
```

#### POST /company-profile

```typescript
// Request Body
interface UpsertCompanyProfileRequest {
  companyName: string;             // required
  description?: string;
  logo?: string;                   // URL (upload rieng qua avatar endpoint)
  website?: string;
  industry?: string;
  companySize?: '1-10' | '11-50' | '51-200' | '201-500' | '500+';
  address?: string;
  city?: string;
  foundedYear?: number;
}

// Response 200/201
interface CompanyProfileResponse {
  data: {
    id: string;
    userId: string;
    companyName: string;
    description: string | null;
    logo: string | null;
    website: string | null;
    industry: string | null;
    companySize: string | null;
    address: string | null;
    city: string | null;
    foundedYear: number | null;
    createdAt: string;
    updatedAt: string;
  };
}
```

#### GET /company-profile/:id

```typescript
// Public (neu employer active) hoac JWT
// Response 200: CompanyProfileResponse
```

---

### 3.3 job-service

Base URL: `/job/api`

#### POST /jobs (Employer)

```typescript
// Request Body
interface CreateJobRequest {
  title: string;                   // required, max 200
  description: string;             // required
  requirements?: string;
  salaryMin?: number;
  salaryMax?: number;
  salaryCurrency?: 'VND' | 'USD'; // default VND
  location?: string;
  workType?: WorkType;             // default 'onsite'
  experienceLevelId?: string;      // UUID
  skillIds?: string[];             // UUID array
  deadline?: string;               // YYYY-MM-DD
  status?: JobStatus;              // default 'draft'
}

// Response 201
interface JobResponse {
  data: {
    id: string;
    employerId: string;
    title: string;
    description: string;
    requirements: string | null;
    salaryMin: number | null;
    salaryMax: number | null;
    salaryCurrency: string;
    location: string | null;
    workType: WorkType;
    experienceLevel: { id: string; name: string } | null;
    skills: { id: string; name: string; slug: string }[];
    status: JobStatus;
    deadline: string | null;
    createdAt: string;
    updatedAt: string;
    // Populated khi GET chi tiet
    employer?: {
      id: string;
      fullName: string | null;
      company?: CompanyProfileResponse['data'];
    };
  };
}
```

#### GET /jobs (Public)

```typescript
// Query
interface SearchJobsQuery extends PaginationQuery {
  keyword?: string;                // full-text search title + description
  skills?: string;                 // comma-separated slugs: "react,nodejs"
  experienceLevelId?: string;
  location?: string;
  workType?: WorkType;
  salaryMin?: number;
  salaryMax?: number;
  status?: JobStatus;              // default 'open' cho public
}

// Response 200
interface SearchJobsResponse {
  data: JobResponse['data'][];     // voi employer info populated
  meta: PaginationMeta;
}
```

#### GET /jobs/:id (Public)

```typescript
// Response 200: JobResponse (voi employer + company info populated)
```

#### PUT /jobs/:id (Employer, owner)

```typescript
// Request Body: Partial<CreateJobRequest>
// Response 200: JobResponse
// Error 403: khong phai owner
```

#### PATCH /jobs/:id/status (Employer, owner)

```typescript
// Request Body
interface UpdateJobStatusRequest {
  status: JobStatus;               // 'open' | 'closed'
}

// Response 200: JobResponse
```

#### GET /jobs/my (Employer)

```typescript
// Query: PaginationQuery + status filter
interface MyJobsQuery extends PaginationQuery {
  status?: JobStatus;
}

// Response 200: { data: JobResponse['data'][], meta: PaginationMeta }
```

#### POST /applications (Candidate)

```typescript
// Request: multipart/form-data
interface CreateApplicationRequest {
  jobId: string;                   // required
  coverLetter?: string;
  cv: File;                        // required, max 10MB, pdf/docx
}

// Response 201
interface ApplicationResponse {
  data: {
    id: string;
    jobId: string;
    candidateId: string;
    status: ApplicationStatus;
    coverLetter: string | null;
    cvUrl: string;                 // MinIO URL
    appliedAt: string;
    updatedAt: string;
    // Populated tuy context
    job?: JobResponse['data'];
    candidate?: {
      id: string;
      fullName: string | null;
      email: string;
      candidateProfile?: CandidateProfileResponse['data'];
    };
  };
}

// Error 409: da ung tuyen job nay roi
// Error 400: job khong open
```

#### GET /applications/my (Candidate)

```typescript
// Query: PaginationQuery + status filter
interface MyApplicationsQuery extends PaginationQuery {
  status?: ApplicationStatus;
}

// Response 200: { data: ApplicationResponse['data'][] (voi job populated), meta }
```

#### GET /applications/job/:jobId (Employer, owner)

```typescript
// Query: PaginationQuery + status filter
interface JobApplicationsQuery extends PaginationQuery {
  status?: ApplicationStatus;
}

// Response 200: { data: ApplicationResponse['data'][] (voi candidate populated), meta }
```

#### PATCH /applications/:id/status (Employer)

```typescript
// Request Body
interface UpdateApplicationStatusRequest {
  status: ApplicationStatus;
  note?: string;                   // ly do doi trang thai
}

// Response 200: ApplicationResponse
// Side effect: tao application_event record
// Error 403: khong phai employer cua job nay
```

#### POST /saved-jobs/:jobId (Candidate)

```typescript
// Response 201: { data: { id: string, jobId: string, createdAt: string } }
// Error 409: da luu roi
```

#### DELETE /saved-jobs/:jobId (Candidate)

```typescript
// Response 204: no content
```

#### GET /saved-jobs (Candidate)

```typescript
// Query: PaginationQuery
// Response 200: { data: { id, jobId, createdAt, job: JobResponse['data'] }[], meta }
```

#### GET /skills (Public)

```typescript
// Query
interface GetSkillsQuery {
  category?: string;
  search?: string;
}

// Response 200
interface SkillsResponse {
  data: {
    id: string;
    name: string;
    slug: string;
    category: string | null;
  }[];
}
```

#### POST /skills (Admin)

```typescript
// Request Body
interface CreateSkillRequest {
  name: string;
  category?: string;
}

// Response 201: { data: { id, name, slug, category } }
// slug tu dong generate tu name
```

#### GET /experience-levels (Public)

```typescript
// Response 200
interface ExperienceLevelsResponse {
  data: {
    id: string;
    name: string;         // "Intern" | "Junior" | "Mid" | "Senior" | "Lead" | "Manager"
    sortOrder: number;
  }[];
}
```

---

### 3.4 interview-service

Base URL: `/interview/api`

#### POST /sessions (Candidate)

```typescript
// Request Body
interface CreateSessionRequest {
  category: string;                // "Backend" | "Frontend" | "System Design"
  difficulty: Difficulty;
  jobId?: string;                  // optional, lien ket voi job posting
}

// Response 201
interface SessionResponse {
  data: {
    id: string;
    candidateId: string;
    jobId: string | null;
    category: string;
    difficulty: Difficulty;
    status: InterviewSessionStatus;
    totalTurns: number;
    startedAt: string;
    completedAt: string | null;
    createdAt: string;
    // First question included
    currentQuestion: {
      turnNumber: number;
      questionText: string;
      questionMetadata: {
        topic: string;
        difficulty: string;
        expectedTopics: string[];
      };
    };
  };
}
```

#### POST /sessions/:id/answer (Candidate)

```typescript
// Request Body
interface SubmitAnswerRequest {
  answer: string;                  // required, min 10 chars
}

// Response 200
interface SubmitAnswerResponse {
  data: {
    turn: {
      turnNumber: number;
      questionText: string;
      candidateAnswer: string;
      scores: CriteriaScores;
      agentDecision: AgentDecision;
      agentReasoning: string;
    };
    nextQuestion: {
      turnNumber: number;
      questionText: string;
    } | null;                      // null neu session ket thuc (VD: sau 10 turns)
    sessionStatus: InterviewSessionStatus;
  };
}

interface CriteriaScores {
  technicalAccuracy: number;       // 0.0 - 10.0
  relevance: number;
  completeness: number;
  extensibility: number;
}
```

#### POST /sessions/:id/end (Candidate)

```typescript
// Response 200
interface EndSessionResponse {
  data: {
    session: SessionResponse['data'];
    result: {
      id: string;
      overallScore: number;        // 0.0 - 10.0
      criteriaAverages: CriteriaScores;
      strengths: string[];
      improvements: string[];
      aiSummary: string | null;    // tu AI, null khi mock
    };
  };
}
```

#### GET /sessions (Candidate)

```typescript
// Query: PaginationQuery + filters
interface MySessionsQuery extends PaginationQuery {
  status?: InterviewSessionStatus;
  category?: string;
}

// Response 200
interface SessionListResponse {
  data: {
    id: string;
    category: string;
    difficulty: Difficulty;
    status: InterviewSessionStatus;
    totalTurns: number;
    overallScore: number | null;   // null neu chua completed
    startedAt: string;
    completedAt: string | null;
  }[];
  meta: PaginationMeta;
}
```

#### GET /sessions/:id (Candidate or Employer)

```typescript
// Response 200 — chi tiet phien + tat ca turns
interface SessionDetailResponse {
  data: {
    session: SessionResponse['data'];
    turns: {
      turnNumber: number;
      questionText: string;
      questionSource: 'bank' | 'ai';
      candidateAnswer: string;
      scores: CriteriaScores;
      agentDecision: AgentDecision;
      agentReasoning: string;
      createdAt: string;
    }[];
    result: EndSessionResponse['data']['result'] | null;
  };
}
```

#### GET /sessions/candidate/:candidateId (Employer)

```typescript
// Employer xem ket qua phong van cua ung vien (tin hieu tham khao)
// Query: PaginationQuery

// Response 200
interface CandidateSessionsResponse {
  data: SessionListResponse['data'];
  meta: PaginationMeta;
}
```

#### Question Bank — Admin CRUD

```typescript
// POST /question-bank (Admin)
interface CreateQuestionRequest {
  category: string;                // "Backend" | "Frontend" | "System Design" | "Database" | "DevOps"
  subcategory: string;             // "Node.js" | "React" | "PostgreSQL"
  difficulty: Difficulty;
  questionText: string;
  expectedTopics: string[];        // ["REST API", "HTTP methods"]
}

// Response 201
interface QuestionResponse {
  data: {
    id: string;
    category: string;
    subcategory: string;
    difficulty: Difficulty;
    questionText: string;
    expectedTopics: string[];
    createdBy: string;
    createdAt: string;
    updatedAt: string;
  };
}

// GET /question-bank (Admin)
// Query: { category?, subcategory?, difficulty?, search? } + PaginationQuery
// Response 200: { data: QuestionResponse['data'][], meta }

// PUT /question-bank/:id (Admin)
// Request: Partial<CreateQuestionRequest>
// Response 200: QuestionResponse

// DELETE /question-bank/:id (Admin)
// Response 204
```

---

## 4. Error Contract

Tất cả error response theo format chung:

```typescript
interface ErrorResponse {
  statusCode: number;
  message: string;
  errorCode: string;
  details?: ValidationError[] | Record<string, any>;
}

interface ValidationError {
  field: string;
  message: string;
  value?: any;
}
```

### Error Codes chung

| errorCode | HTTP | Mô tả |
|---|---|---|
| `VALIDATION_ERROR` | 400 | Input validation fail |
| `UNAUTHORIZED` | 401 | Không có token / token hết hạn |
| `FORBIDDEN` | 403 | Không đủ quyền (RBAC) |
| `NOT_FOUND` | 404 | Resource không tồn tại |
| `CONFLICT` | 409 | Duplicate (email, application) |
| `INTERNAL_ERROR` | 500 | Lỗi server |

### Error Codes theo domain

| errorCode | Service | Mô tả |
|---|---|---|
| `EMAIL_EXISTS` | auth | Email đã đăng ký |
| `INVALID_CREDENTIALS` | auth | Sai email/password |
| `TOKEN_EXPIRED` | auth | JWT hết hạn |
| `PROFILE_NOT_FOUND` | user | Chưa tạo profile |
| `JOB_NOT_FOUND` | job | Tin tuyển dụng không tồn tại |
| `JOB_NOT_OPEN` | job | Tin đã đóng, không thể ứng tuyển |
| `ALREADY_APPLIED` | job | Đã ứng tuyển tin này |
| `NOT_JOB_OWNER` | job | Không phải người đăng tin |
| `ALREADY_SAVED` | job | Đã lưu tin này |
| `SESSION_NOT_FOUND` | interview | Phiên không tồn tại |
| `SESSION_COMPLETED` | interview | Phiên đã kết thúc |
| `SESSION_NOT_YOURS` | interview | Không phải phiên của bạn |
| `AI_SERVICE_ERROR` | interview | AI service lỗi (timeout, 5xx) |

---

## 5. Authentication Flow

### Header x-auth-user

APISIX inject JWT payload vao header `x-auth-user` (JSON string):

```typescript
interface AuthUserPayload {
  sub: string;            // user ID (UUID)
  email: string;
  role: Role;
  iat: number;            // issued at (unix timestamp)
  exp: number;            // expiry (unix timestamp)
  iss: string;            // "ai-recruit"
}
```

Mọi service parse header này để biết user hiện tại:

```typescript
// Trong controller, dung decorator
@Get('me')
async getMe(@AuthUser() user: AuthUserPayload) {
  return this.userService.findById(user.sub);
}
```

### RBAC Check

```typescript
// Trong controller
@Roles(Role.Employer)
@Post('jobs')
async createJob(@AuthUser() user: AuthUserPayload, @Body() dto: CreateJobRequest) {
  // chi Employer moi vao duoc day
}
```

---

## 6. Dependency Map — Ai cần gì của ai

```
                         ┌─────────────────────┐
                         │     libs/common      │
                         │  enums, DTOs, types  │
                         └─────────┬───────────┘
                                   │ import
              ┌────────────────────┼───────────────────┐
              ▼                    ▼                    ▼
      ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐
      │ auth-service  │   │ user-service │   │ job-service      │
      │               │   │              │   │                  │
      │ TCP client:   │   │ TCP server:  │   │ TCP client:      │
      │  → user.*     │   │  user.*      │   │  → user.getById  │
      │  → notif.*    │   │              │   │  → user.getByIds │
      └──────┬────────┘   └──────────────┘   │                  │
             │                                │ S3 client:       │
             │                                │  → MinIO         │
             │                                └──────────────────┘
             │
             │            ┌──────────────────┐
             └──────────▶ │ notification-svc │
                          │ TCP server:      │
                          │  notif.*         │
                          └──────────────────┘

      ┌───────────────────┐          ┌──────────────────┐
      │ interview-service │  REST    │ ai-service       │
      │                   │ ───────▶ │ (FastAPI mock)   │
      │ REST client:      │          │                  │
      │  → ai-service     │          │ POST /api/start  │
      │                   │          │ POST /api/eval   │
      └───────────────────┘          └──────────────────┘
```

### Cho từng người

| Người A (auth + interview) | Cần từ người khác |
|---|---|
| auth-service | `UserResponse`, `CreateUserMessage` types từ libs/common. TCP message pattern `user.*` (B implement) |
| interview-service | `CriteriaScores`, `AgentDecision` types từ libs/common. REST contract `/api/evaluate` (C implement mock) |

| Người B (user + job) | Cần từ người khác |
|---|---|
| user-service | TCP handler patterns `user.*` — implement theo contract này |
| job-service | `UserResponse` type. TCP client gọi `user.getById`, `user.getByIds` |

| Người C (infra + AI mock + frontend) | Cần từ người khác |
|---|---|
| ai-service mock | REST contract `/api/start`, `/api/evaluate` — implement theo contract này |
| frontend | HTTP API contracts của tất cả services — call theo contract này |
