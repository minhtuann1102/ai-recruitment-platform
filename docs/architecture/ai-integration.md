# Tích hợp AI Service

> Tóm tắt cách `interview-service` tích hợp `ai-service`. **Thiết kế chi tiết và contract nằm ở [docs/ai-service/](../ai-service/README.md)** (nguồn duy nhất, tránh chép lại). Quyết định kiến trúc: [ADR-008](adr/adr-008-evaluator-per-turn-orchestrator.md).

## 1. Tổng quan

```
interview-service (NestJS)               ai-service (FastAPI, stateless)
┌─────────────────────────┐   REST/SSE   ┌───────────────────────────────┐
│ AiInterviewClient       │              │ POST /api/cv/parse            │ CV Parser
│   .parseCv()          ──┼────────────▶ │ POST /api/start      (SSE)    │ Planner → Interviewer
│   .start()            ──┼────────────▶ │ POST /api/next-turn  (SSE)    │ Evaluator → policy → Interviewer
│   .nextTurn()         ──┼────────────▶ │ POST /api/finalize            │ code tính điểm → Reporter
│   .finalize()         ──┼────────────▶ │ GET  /api/health              │
│ MockAiInterviewClient   │ ◀────────────┤                               │
└─────────────────────────┘              └───────────────────────────────┘
```

**Nguyên tắc:**
- `interview-service` sở hữu **toàn bộ dữ liệu** phỏng vấn, kể cả plan và candidate state ([ADR-004](adr/adr-004-interview-data-ownership.md)). `ai-service` nhận state kèm mỗi request và trả state mới.
- Giao tiếp REST/HTTP, streaming bằng SSE ([ADR-003](adr/adr-003-tcp-rest-transport.md)).
- Code điều phối luồng; LLM chỉ làm việc hẹp. Ứng viên **không thấy điểm giữa phiên**, chỉ thấy báo cáo cuối buổi.

## 2. Agent

| Agent | Chạy khi | Việc |
|---|---|---|
| CV Parser | Khi gắn CV | Trích xuất `cv_profile` (CV đã redact PII) |
| Planner | Một lần, đầu buổi | Chọn 5–6 topic từ topic catalog theo `track` + `level` |
| Evaluator | Sau mỗi câu trả lời | Chấm 4 tiêu chí (band 0–4), nêu ý có / thiếu / hiểu sai kèm trích dẫn |
| Interviewer | Mỗi lượt | Diễn đạt một câu hỏi theo action policy đã chọn, stream token |
| Reporter | Một lần, cuối buổi | Viết nhận xét; điểm do code tổng hợp, Reporter không sửa điểm |

Chi tiết: [docs/ai-service/02](../ai-service/02-multi-agent-architecture-and-prompts.md) (agent, prompt), [03](../ai-service/03-orchestrator-state-machine.md) (state machine), [04](../ai-service/04-adaptive-loop-and-candidate-state.md) (adapt), [05](../ai-service/05-rubric-and-final-report.md) (rubric, report).

## 3. Contract

Public API (interview-service) và internal API (ai-service) mô tả đầy đủ ở [docs/ai-service/06-api-contract.md](../ai-service/06-api-contract.md). Interface phía NestJS:

```typescript
export interface AiInterviewClient {
  parseCv(input: ParseCvInput): Promise<ParseCvResult>;
  start(req: AiStartRequest): AsyncIterable<AiStreamEvent>;       // meta | token | replace | done | error
  nextTurn(req: AiNextTurnRequest): AsyncIterable<AiStreamEvent>;
  finalize(req: AiFinalizeRequest): Promise<AiReport>;
}
```

## 4. Mock

`MockAiInterviewClient` (NestJS) giữ cho dev: `start` / `nextTurn` phát câu hỏi từ `question_bank` thành một event `token` rồi `done`; `finalize` trả report điểm cố định. Mock FastAPI (`apps/ai-service/app/`) dùng để thử gateway routing.

> **Trạng thái:** mock FastAPI hiện cài đặt contract cũ của ADR-007 (không SSE, không `cv/parse`, có `answer_signal`). Cần cập nhật sang contract ở docs/ai-service/06 trước khi FSD tích hợp.

## 5. Topic catalog và dữ liệu

- Chủ đề phỏng vấn theo vị trí nằm trong `apps/ai-service/app/catalog/*.yaml` (`java_backend`, `python_backend`, `nodejs_backend`, `ai_engineer`). Planner chỉ chọn topic có trong catalog.
- RAG chỉ dùng `interview_qa` và `textbook`. Thiết kế đầy đủ: [rag-design.md](rag-design.md).

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
   - Gọi REST/SSE đến ai-service (đọc stream, không chờ cả body)
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
   - Orchestrator bằng code, policy chọn action (xem docs/ai-service)

### Phase 3: Optimization (stretch)

- gRPC thay REST (nếu cần performance)
- (Streaming SSE đã chuyển vào phạm vi bắt buộc, xem ADR-008)
- Caching RAG results trong Redis
- A/B testing giữa các model

## 8. RAG Knowledge Base

**LLM đã chốt:** OpenAI GPT-4o-mini (cost-effective, 128k context)
**Embedding model:** text-embedding-3-small (1536 dims, match schema pgvector)

### Nguồn dữ liệu (3 loại)

| Loại | Nguồn | Volume mục tiêu | Tag source_type |
|---|---|---|---|
| Interview Q&A | Curated Q&A phỏng vấn CNTT (Backend, Frontend, System Design, DB, DevOps) | 200+ cặp | `interview_qa` |
| Textbook/Tutorial | Node.js docs, React docs, PostgreSQL docs, CS fundamentals, System Design | 5000+ chunks | `textbook` |

### Schema knowledge_chunks (ai_db)

Schema đầy đủ, index và lý do: xem [rag-design.md](rag-design.md#3-schema-knowledge_chunks-thay-thế-bản-trong-ai-integrationmd). Tóm tắt: cột `content`, `content_hash` (unique), `embedding vector(1536)`, `embedding_model`, `source_type`, `category`, `difficulty`, `language`, `metadata JSONB`. Chưa tạo ANN index (exact scan), thêm HNSW khi cần.

### Retrieval flow

Mỗi agent có tool retrieval riêng với bộ lọc khác nhau (Interviewer, Planner, Evaluator). Chi tiết: [rag-design.md](rag-design.md#4-retrieval-theo-từng-agent).

```
Query (category + topic + tóm tắt câu trả lời)
  → embed (text-embedding-3-small)
  → cosine similarity (pgvector, top-5) + lọc source_type/category/difficulty
  → khử trùng lặp theo qa_id → chèn vào prompt (≤ ~1500 token)
```
