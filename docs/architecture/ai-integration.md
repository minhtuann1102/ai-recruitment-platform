# Tích hợp AI Service

> Tài liệu thiết kế interface, hợp đồng REST, kiến trúc multi-agent và chiến lược chuyển từ mock sang FastAPI thật.
> Quyết định kiến trúc: xem [ADR-007](adr/adr-007-multi-agent-interview.md).

## 1. Tổng quan

```
interview-service (NestJS)          ai-service (FastAPI)
┌────────────────────────┐          ┌──────────────────────────┐
│ AiInterviewClient      │  REST    │ POST /api/start          │
│   .startSession()    ──┼────────▶ │ POST /api/next-turn      │  Planner + Interviewer
│   .nextTurn()        ──┼────────▶ │                          │  (moi luot)
│   .finalize()        ──┼────────▶ │ POST /api/finalize       │  Evaluator (1 lan, cuoi phien)
│                        │ ◀────────┤ GET  /api/health         │
│ MockAiInterviewClient  │          └──────────────────────────┘
└────────────────────────┘
```

**Nguyên tắc:**
- `interview-service` sở hữu **toàn bộ dữ liệu** phỏng vấn (xem [ADR-004](adr/adr-004-interview-data-ownership.md))
- `ai-service` là **stateless processor** — nhận context, trả về kết quả
- Giao tiếp qua **REST/HTTP** (xem [ADR-003](adr/adr-003-tcp-rest-transport.md))
- **Trong phiên:** ứng viên chỉ thấy câu hỏi tiếp theo, không thấy điểm
- **Sau phiên:** ứng viên thấy điểm **từng câu hỏi** + nhận xét từng câu trả lời + tổng kết

## 2. Kiến trúc multi-agent (trong ai-service)

Workflow có kiểm soát (graph, thứ tự cố định), không để agent tự gọi nhau tự do.

| Agent | Chạy khi | Nhiệm vụ | Tool riêng |
|---|---|---|---|
| **Planner** | Mỗi lượt | Chọn chiến lược `deepen` / `switch_topic` / `keep_difficulty` | `get_session_state`, `retrieve_topics` |
| **Interviewer** | Mỗi lượt | Sinh câu hỏi tiếp theo theo chiến lược + ghi `answer_signal` | `retrieve_knowledge`, `check_duplicate_question` |
| **Evaluator** | 1 lần, sau khi kết thúc phiên | Chấm điểm **từng câu trả lời**, viết nhận xét từng câu, tổng kết | `retrieve_reference_answer`, `score_rubric` |

```
Moi luot:   request ─▶ Planner ─▶ Interviewer ─▶ { next_question, agent_decision, answer_signal }
Cuoi phien: transcript ─▶ Evaluator ─▶ { turns[{scores, comment}], overall, strengths, improvements }
```

**`answer_signal`** (`weak | ok | strong`): tín hiệu sơ bộ nội bộ để Planner quyết định giữa phiên. Không phải điểm, không hiển thị cho ứng viên. Được gửi lại trong `history` ở lượt sau.

## 3. Interface AiInterviewClient

Định nghĩa trong `apps/interview-service/src/modules/ai-client/`:

```typescript
// ai-interview-client.interface.ts

export interface InterviewContext {
  category: string;        // "Backend" | "Frontend" | "System Design"
  difficulty: string;      // "easy" | "medium" | "hard"
  candidateSkills?: string[];
  experienceYears?: number;
}

export interface StartSessionRequest {
  sessionId: string;
  context: InterviewContext;
}

export interface StartSessionResponse {
  firstQuestion: string;
  questionMetadata: {
    topic: string;
    difficulty: string;
    expectedTopics: string[];
  };
}

export type AnswerSignal = 'weak' | 'ok' | 'strong';
export type AgentDecision = 'deepen' | 'switch_topic' | 'keep_difficulty';

export interface TurnHistory {
  turnNumber: number;
  question: string;
  answer: string;
  answerSignal?: AnswerSignal;     // tu next-turn truoc do
  agentDecision?: AgentDecision;
}

export interface NextTurnRequest {
  sessionId: string;
  turnNumber: number;
  question: string;
  answer: string;
  history: TurnHistory[];          // cac luot truoc
  context: InterviewContext;
}

export interface NextTurnResponse {
  nextQuestion: string;
  agentDecision: AgentDecision;
  answerSignal: AnswerSignal;
  reasoning: string;               // ly do ngan gon cho quyet dinh
}

export interface CriteriaScores {
  technicalAccuracy: number;  // 0.0 - 10.0
  relevance: number;          // 0.0 - 10.0
  completeness: number;       // 0.0 - 10.0
  extensibility: number;      // 0.0 - 10.0
}

export interface FinalizeRequest {
  sessionId: string;
  context: InterviewContext;
  turns: { turnNumber: number; question: string; answer: string }[];
}

export interface TurnEvaluation {
  turnNumber: number;
  scores: CriteriaScores;
  comment: string;                 // nhan xet cho cau tra loi nay
}

export interface FinalizeResponse {
  turns: TurnEvaluation[];
  overallScore: number;            // 0.0 - 10.0
  criteriaAverages: CriteriaScores;
  strengths: string[];
  improvements: string[];
  summary: string;
}

export interface AiInterviewClient {
  startSession(req: StartSessionRequest): Promise<StartSessionResponse>;
  nextTurn(req: NextTurnRequest): Promise<NextTurnResponse>;
  finalize(req: FinalizeRequest): Promise<FinalizeResponse>;
}
```

## 4. Mock Implementation

`MockAiInterviewClient` implements interface trên, lấy câu hỏi từ `question_bank`:

- `startSession`: random câu hỏi theo `category`, `difficulty`.
- `nextTurn`: random câu hỏi tiếp, `agentDecision: 'keep_difficulty'`, `answerSignal: 'ok'`.
- `finalize`: mỗi lượt trả scores cố định (7.0 / 7.5 / 6.5 / 6.0), `comment: 'Mock comment'`, tổng hợp trung bình.

**Đăng ký qua DI:**

```typescript
// ai-client.module.ts
const AI_CLIENT_TOKEN = 'AI_INTERVIEW_CLIENT';

@Module({
  providers: [
    {
      provide: AI_CLIENT_TOKEN,
      useClass: MockAiInterviewClient, // doi thanh RealAiInterviewClient sau
    },
  ],
  exports: [AI_CLIENT_TOKEN],
})
export class AiClientModule {}
```

## 5. Hợp đồng REST — AI Service

> Contract trước khi code. Mock ai-service (FastAPI) implement contract này. Python dùng snake_case.

### POST /api/start

**Request:**

```json
{
  "session_id": "019234ab-...",
  "context": {
    "category": "Backend",
    "difficulty": "medium",
    "candidate_skills": ["nodejs", "typescript"],
    "experience_years": 2
  }
}
```

**Response (200 OK):**

```json
{
  "first_question": "Hay giai thich cach ban thiet ke mot REST API cho he thong quan ly nguoi dung.",
  "question_metadata": {
    "topic": "API Design",
    "difficulty": "medium",
    "expected_topics": ["REST principles", "HTTP methods", "resource naming", "status codes"]
  }
}
```

### POST /api/next-turn

**Request:**

```json
{
  "session_id": "019234ab-...",
  "turn_number": 3,
  "question": "Giai thich su khac biet giua REST va GraphQL?",
  "answer": "REST su dung HTTP methods, moi endpoint...",
  "history": [
    {
      "turn_number": 1,
      "question": "HTTP methods nao ban biet?",
      "answer": "GET, POST, PUT, DELETE, PATCH...",
      "answer_signal": "strong",
      "agent_decision": "deepen"
    }
  ],
  "context": { "category": "Backend", "difficulty": "medium", "candidate_skills": ["nodejs"] }
}
```

**Response (200 OK):**

```json
{
  "next_question": "Ban da noi ve REST endpoints. Vay lam sao de thiet ke API co versioning tot?",
  "agent_decision": "deepen",
  "answer_signal": "ok",
  "reasoning": "Ung vien hieu co ban ve REST nhung chua de cap versioning. Dao sau.",
  "metadata": { "model_version": "mock-v1", "processing_time_ms": 150 }
}
```

### POST /api/finalize

Gọi **một lần** khi phiên kết thúc (ứng viên bấm kết thúc hoặc đủ số lượt). Chấm điểm từng câu + nhận xét.

**Request:**

```json
{
  "session_id": "019234ab-...",
  "context": { "category": "Backend", "difficulty": "medium", "candidate_skills": ["nodejs"] },
  "turns": [
    { "turn_number": 1, "question": "HTTP methods nao ban biet?", "answer": "GET, POST, PUT..." },
    { "turn_number": 2, "question": "REST va GraphQL khac nhau the nao?", "answer": "REST su dung..." }
  ]
}
```

**Response (200 OK):**

```json
{
  "turns": [
    {
      "turn_number": 1,
      "scores": { "technical_accuracy": 8.0, "relevance": 9.0, "completeness": 7.0, "extensibility": 6.0 },
      "comment": "Liet ke dung cac method chinh, nhung chua noi ve tinh idempotent cua PUT/DELETE."
    },
    {
      "turn_number": 2,
      "scores": { "technical_accuracy": 7.5, "relevance": 8.0, "completeness": 6.5, "extensibility": 7.0 },
      "comment": "Hieu co ban ve REST, chua de cap versioning va HATEOAS."
    }
  ],
  "overall_score": 7.5,
  "criteria_averages": { "technical_accuracy": 7.8, "relevance": 8.5, "completeness": 6.8, "extensibility": 6.5 },
  "strengths": ["Nam vung HTTP co ban", "Tra loi dung trong tam"],
  "improvements": ["Can hoc them ve idempotency", "Thieu kien thuc API versioning"],
  "summary": "Nen tang vung, can cai thien chieu sau.",
  "metadata": { "model_version": "mock-v1", "processing_time_ms": 4200 }
}
```

> `/finalize` chậm hơn `/next-turn` (chấm cả transcript). Timeout phía client cần đặt dài hơn.

### GET /api/health

```json
{ "status": "healthy", "version": "mock-v1", "model_loaded": false }
```

### Error Response (4xx/5xx):

```json
{ "error": "invalid_request", "message": "session_id is required", "details": {} }
```

## 6. Docker Compose — Mock AI Service

Thêm vào `docker-compose.yml`:

```yaml
  ai-service:
    build:
      context: ./apps/ai-service
      dockerfile: Dockerfile
    container_name: ai_recruit_ai_service
    ports:
      - "8000:8000"
    networks:
      - ai-recruit-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 10s
      timeout: 5s
      retries: 3
```

APISIX route thêm:

```yaml
  - name: ai-service
    plugins:
      jwt-auth:
        _meta:
          disable: true  # Internal only, khong can JWT
    routes:
      - methods: [POST, GET]
        name: ai-route
        plugins:
          proxy-rewrite:
            regex_uri:
              - ^/ai/(.*)
              - /$1
        uris:
          - /ai/*
    upstream:
      name: ai-upstream
      nodes:
        - host: ai-service
          port: 8000
          weight: 1
      scheme: http
      type: roundrobin
```

## 7. Chiến lược chuyển từ Mock sang FastAPI thật

### Phase 1: Mock (Sprint 0-1)

- `MockAiInterviewClient` trong interview-service
- Mock FastAPI trong Docker để test gateway routing
- AIE setup ai_db + pgvector, RAG pipeline prototype
- Không gọi FastAPI từ interview-service (dùng mock trực tiếp)

### Phase 2: Integration (Sprint 2-3)

1. **Tạo `RealAiInterviewClient`** implements `AiInterviewClient`:
   - Dùng `HttpModule` (NestJS) gọi REST đến ai-service
   - Map response từ snake_case (Python) sang camelCase (TS)
   - Retry logic, timeout, circuit breaker

2. **Đổi DI provider:**
   ```typescript
   {
     provide: AI_CLIENT_TOKEN,
     useClass: process.env.AI_SERVICE_MOCK === 'true'
       ? MockAiInterviewClient
       : RealAiInterviewClient,
   }
   ```

3. **AI service thật:**
   - FastAPI + OpenAI SDK (openai, langchain-core)
   - RAG từ knowledge base (pgvector — xem [Section 8](#8-rag-knowledge-base))
   - **LLM: OpenAI GPT-4o-mini** cho evaluation + question generation
   - **Embedding: text-embedding-3-small** (1536 dims)
   - Agent logic: deepen / switch_topic / keep_difficulty

### Phase 3: Optimization (stretch)

- gRPC thay REST (nếu cần performance)
- Streaming response (cho real-time typing effect)
- Caching RAG results trong Redis
- A/B testing giữa các model

## 8. RAG Knowledge Base

**LLM đã chốt:** OpenAI GPT-4o-mini (cost-effective, 128k context)
**Embedding model:** text-embedding-3-small (1536 dims, match schema pgvector)

### Nguồn dữ liệu (3 loại)

| Loại | Nguồn | Volume mục tiêu | Tag source_type |
|---|---|---|---|
| Interview Q&A | Curated Q&A phỏng vấn CNTT (Backend, Frontend, System Design, DB, DevOps) | 200+ cặp | `interview_qa` |
| Job Descriptions | Crawl từ topcv.vn, itviec.com, linkedin — extract skills/requirements | 500+ JD | `job_description` |
| Textbook/Tutorial | Node.js docs, React docs, PostgreSQL docs, CS fundamentals, System Design | 5000+ chunks | `textbook` |

### Schema knowledge_chunks (ai_db)

```sql
CREATE TABLE knowledge_chunks (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content     TEXT NOT NULL,
  embedding   vector(1536),
  source_type VARCHAR(50),   -- 'interview_qa' | 'job_description' | 'textbook'
  metadata    JSONB,         -- { topic, difficulty, source_url, category }
  created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops);
```

### Retrieval flow

```
Query (question + candidate context)
  → embed (text-embedding-3-small)
  → cosine similarity search (pgvector, top-5)
  → filter by source_type nếu cần
  → top-k chunks → inject vào prompt GPT-4o-mini
```
