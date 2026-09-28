# Tích hợp AI Service

> Tài liệu thiết kế interface, hợp đồng OpenAPI, và chiến lược chuyển từ mock sang FastAPI thật.

## 1. Tổng quan

```
interview-service (NestJS)          ai-service (FastAPI)
┌────────────────────────┐          ┌──────────────────────┐
│ AiInterviewClient      │  REST    │ POST /api/evaluate   │
│   .evaluateAnswer()  ──┼────────▶ │                      │
│   .startSession()    ──┼────────▶ │ POST /api/start      │
│   .getNextQuestion() ──┼────────▶ │ POST /api/next       │
│                        │ ◀────────┤                      │
│ MockAiInterviewClient  │          │ GET  /api/health     │
│ (giai doan hien tai)   │          └──────────────────────┘
└────────────────────────┘
```

**Nguyên tắc:**
- `interview-service` sở hữu **toàn bộ dữ liệu** phỏng vấn (xem [ADR-004](adr/adr-004-interview-data-ownership.md))
- `ai-service` là **stateless processor** — nhận context, trả về kết quả
- Giao tiếp qua **REST/HTTP** (xem [ADR-003](adr/adr-003-tcp-rest-transport.md))
- Giai đoạn hiện tại dùng **mock** — thay thế bằng FastAPI thật mà không đổi interview-service

## 2. Interface AiInterviewClient

Định nghĩa trong `apps/interview-service/src/modules/ai-client/`:

```typescript
// ai-interview-client.interface.ts

export interface StartSessionRequest {
  sessionId: string;
  category: string;        // "Backend" | "Frontend" | "System Design"
  difficulty: string;      // "easy" | "medium" | "hard"
  candidateContext?: {
    skills: string[];
    experienceYears: number;
  };
}

export interface StartSessionResponse {
  firstQuestion: string;
  questionMetadata: {
    topic: string;
    difficulty: string;
    expectedTopics: string[];
  };
}

export interface EvaluateAnswerRequest {
  sessionId: string;
  turnNumber: number;
  question: string;
  answer: string;
  history: TurnHistory[];  // cac luot truoc
}

export interface TurnHistory {
  turnNumber: number;
  question: string;
  answer: string;
  scores?: CriteriaScores;
}

export interface EvaluateAnswerResponse {
  scores: CriteriaScores;
  agentDecision: AgentDecision;
  nextQuestion: string;
  reasoning: string;       // ly do ngan gon cho quyet dinh
}

export interface CriteriaScores {
  technicalAccuracy: number;  // 0.0 - 10.0
  relevance: number;          // 0.0 - 10.0
  completeness: number;       // 0.0 - 10.0
  extensibility: number;      // 0.0 - 10.0
}

export type AgentDecision = 'deepen' | 'switch_topic' | 'keep_difficulty';

// Interface chinh
export interface AiInterviewClient {
  startSession(req: StartSessionRequest): Promise<StartSessionResponse>;
  evaluateAnswer(req: EvaluateAnswerRequest): Promise<EvaluateAnswerResponse>;
}
```

## 3. Mock Implementation

Giai đoạn hiện tại, `MockAiInterviewClient` implements interface trên:

```typescript
// mock-ai-interview-client.ts

@Injectable()
export class MockAiInterviewClient implements AiInterviewClient {
  constructor(
    // Inject question bank repository
    private readonly questionBankRepo: QuestionBankRepository,
  ) {}

  async startSession(req: StartSessionRequest): Promise<StartSessionResponse> {
    const question = await this.questionBankRepo.findRandom({
      category: req.category,
      difficulty: req.difficulty,
    });

    return {
      firstQuestion: question.questionText,
      questionMetadata: {
        topic: question.subcategory,
        difficulty: question.difficulty,
        expectedTopics: question.expectedTopics,
      },
    };
  }

  async evaluateAnswer(req: EvaluateAnswerRequest): Promise<EvaluateAnswerResponse> {
    // Mock: tra ve scores co dinh + random cau hoi tiep
    const nextQuestion = await this.questionBankRepo.findRandom({
      category: req.history[0]?.question ? 'Backend' : 'General',
    });

    return {
      scores: {
        technicalAccuracy: 7.0,
        relevance: 7.5,
        completeness: 6.5,
        extensibility: 6.0,
      },
      agentDecision: 'keep_difficulty',
      nextQuestion: nextQuestion.questionText,
      reasoning: 'Mock evaluation — scores co dinh.',
    };
  }
}
```

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

## 4. Hợp đồng OpenAPI — AI Service

> Dùng làm contract trước khi code. Mock ai-service (FastAPI) implement contract này.

### POST /api/evaluate

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
      "scores": {
        "technical_accuracy": 8.0,
        "relevance": 9.0,
        "completeness": 7.0,
        "extensibility": 6.0
      }
    }
  ],
  "context": {
    "category": "Backend",
    "difficulty": "medium",
    "candidate_skills": ["nodejs", "typescript", "postgresql"]
  }
}
```

**Response (200 OK):**

```json
{
  "scores": {
    "technical_accuracy": 7.5,
    "relevance": 8.0,
    "completeness": 6.5,
    "extensibility": 7.0
  },
  "agent_decision": "deepen",
  "next_question": "Ban da noi ve REST endpoints. Vay lam sao de thiet ke API co versioning tot?",
  "reasoning": "Ung vien hieu co ban ve REST nhung chua de cap versioning va HATEOAS. Dao sau de danh gia chieu sau.",
  "metadata": {
    "model_version": "mock-v1",
    "processing_time_ms": 150
  }
}
```

### POST /api/start

**Request:**

```json
{
  "session_id": "019234ab-...",
  "category": "Backend",
  "difficulty": "medium",
  "candidate_context": {
    "skills": ["nodejs", "typescript"],
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

### GET /api/health

**Response (200 OK):**

```json
{
  "status": "healthy",
  "version": "mock-v1",
  "model_loaded": false
}
```

### Error Response (4xx/5xx):

```json
{
  "error": "invalid_request",
  "message": "session_id is required",
  "details": {}
}
```

## 5. Mock FastAPI Service

File `apps/ai-service/main.py` (chạy trong Docker):

```python
from fastapi import FastAPI
import random

app = FastAPI(title="AI Interview Service (Mock)", version="0.1.0")

MOCK_QUESTIONS = [
    "Giai thich su khac biet giua process va thread?",
    "Design pattern nao ban thuong dung nhat? Tai sao?",
    "Lam sao de toi uu hoa query SQL chay cham?",
    "Giai thich CAP theorem va ap dung vao thiet ke he thong?",
    "Event-driven architecture la gi? Khi nao nen dung?",
]

@app.get("/api/health")
def health():
    return {"status": "healthy", "version": "mock-v1", "model_loaded": False}

@app.post("/api/start")
def start_session(body: dict):
    return {
        "first_question": random.choice(MOCK_QUESTIONS),
        "question_metadata": {
            "topic": body.get("category", "General"),
            "difficulty": body.get("difficulty", "medium"),
            "expected_topics": ["concept", "example", "trade-off"],
        },
    }

@app.post("/api/evaluate")
def evaluate_answer(body: dict):
    return {
        "scores": {
            "technical_accuracy": round(random.uniform(5.0, 9.0), 1),
            "relevance": round(random.uniform(5.0, 9.0), 1),
            "completeness": round(random.uniform(4.0, 8.0), 1),
            "extensibility": round(random.uniform(4.0, 8.0), 1),
        },
        "agent_decision": random.choice(["deepen", "switch_topic", "keep_difficulty"]),
        "next_question": random.choice(MOCK_QUESTIONS),
        "reasoning": "Mock: random evaluation for testing.",
        "metadata": {"model_version": "mock-v1", "processing_time_ms": 50},
    }
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

### Phase 1: Mock (Sprint 0-3)

- `MockAiInterviewClient` trong interview-service
- Mock FastAPI trong Docker để test gateway routing
- Không gọi FastAPI từ interview-service (dùng mock trực tiếp)

### Phase 2: Integration (Sprint 4-5)

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
   - FastAPI + LangChain/LlamaIndex
   - RAG từ knowledge base (pgvector)
   - Claude/GPT API cho evaluation
   - Agent logic phức tạp hơn

### Phase 3: Optimization (stretch)

- gRPC thay REST (nếu cần performance)
- Streaming response (cho real-time typing effect)
- Caching RAG results trong Redis
- A/B testing giữa các model

## Câu hỏi mở

- [ ] Nhóm dùng LLM nào cho AI service? (Claude API, OpenAI GPT, self-hosted?)
- [ ] Budget cho LLM API calls?
- [ ] Knowledge base lấy từ nguồn nào? (textbook, documentation, curated Q&A?)
