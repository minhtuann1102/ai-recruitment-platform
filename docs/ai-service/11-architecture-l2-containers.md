# 13. Kiến trúc L2 — Container (C4 Level 2)

> Thuộc bộ [AI Service design doc](README.md). Mô tả các **container** (đơn vị chạy và triển khai được) liên quan tới phần AIE, cách chúng giao tiếp, nơi lưu dữ liệu và ranh giới tin cậy. Yêu cầu nguồn: [BRD](requirements/01-brd.md) · [FR](requirements/02-functional-requirements.md) · [NFR](requirements/03-non-functional-requirements.md).

| Mục | Giá trị |
|---|---|
| Phiên bản | 0.3 (Draft, chờ team review) |
| Ngày | 2026-10-12 |
| Owner | AIE |
| Mức C4 | **Level 2 (Container)**. Level 1 (Context) tóm tắt ở §2; Level 3 (Component) của ai-service xem sơ lược ở §9 và chi tiết ở [02](02-multi-agent-architecture-and-prompts.md), [03](03-orchestrator-state-machine.md) |

> **Giả định về thuật ngữ:** "L2" được hiểu là C4 Level 2. Nếu nhóm dùng "L2" theo nghĩa khác (ví dụ tầng thứ hai của bộ tài liệu riêng), cần điều chỉnh.

> **Cập nhật theo [BRD v0.5](requirements/01-brd.md) (2026-10-19).** Giai đoạn 1: chat văn bản trong phòng họp, 15 đến 20 phút, **luyện theo CV và JD** (JD vào Planner, không vào RAG). Giai đoạn 2 là voice Stretch: **mặc định tùy chọn A theo `main`** (lớp voice nằm trong Web App, DE sở hữu: TTS và STT bấm-để-nói, ai-service không đổi). **voice-gateway trong sơ đồ là tùy chọn B**, ngoài kế hoạch mặc định, chỉ làm nếu owner xác nhận và có ADR-009. Giai đoạn 3 (học từ dữ liệu) hoãn.

## 1. Cách đọc

- **Container** ở đây là thứ chạy độc lập: ứng dụng web, service, cơ sở dữ liệu, hàng đợi, hệ thống ngoài. Module hay class trong một service không xuất hiện ở mức này.
- **Hiện trạng trong repo** (nhánh `feat/aie`, `f1e61b2`, 2026-10-08) có ba trạng thái: **Có** (đã có code), **Mock** (đã có nhưng dùng quy tắc thay phần thật), **Kế hoạch** (chưa có trong repo).
- Mọi quyết định đã được ghi ở các ADR; tài liệu này chỉ liên kết, không lặp lại.
- **Giai đoạn:** nét liền là giai đoạn 1 (chat); nét đứt và nhãn "GĐ2" là giai đoạn 2 (voice). Ý tưởng chính: **ai-service giữ nguyên, stateless, chỉ REST và SSE**; phần giọng nói nằm trong một container riêng gọi đúng contract của chat (xem BRD §0.3).

## 2. Ngữ cảnh hệ thống (C4 Level 1)

| Tác nhân hoặc hệ thống | Quan hệ với phần AI |
|---|---|
| **Candidate** | Chọn vị trí và level, trả lời câu hỏi, xem báo cáo |
| **Employer, Admin** | Không dùng trực tiếp tính năng này trong MVP |
| **LLM provider** (OpenRouter chuyển tiếp tới OpenAI) | Hệ thống ngoài. Nhận prompt và trả text, JSON, embedding |
| **Đội phát triển** (FSD, DE, AIE) | Soạn catalog, dữ liệu RAG, prompt; chạy bộ đánh giá |

## 3. Sơ đồ container

```mermaid
flowchart TB
    CAND(["Candidate<br/>trình duyệt"])
    LLM[["LLM provider<br/>OpenRouter → OpenAI<br/>chat + embeddings"]]
    STT[["STT / TTS provider<br/>(GĐ2)"]]

    subgraph EDGE["Biên công khai"]
        WEB["Web App · Next.js<br/>phòng họp: ảnh AI, video tự xem,<br/>khung chat, đồng hồ"]
        GW["API Gateway<br/>Apache APISIX 3.14 :9080<br/>JWT, RBAC, định tuyến"]
        VG["voice-gateway (GĐ2)<br/>hạ tầng voice-agent có sẵn<br/>VAD, STT, TTS, âm thanh"]
    end

    subgraph BE["Backend NestJS (mạng nội bộ)"]
        AUTH["auth-service<br/>:3300"]
        USER["user-service<br/>:3301"]
        JOB["job-service<br/>:3302"]
        INT["interview-service<br/>:3304<br/>sở hữu dữ liệu phỏng vấn"]
    end

    subgraph AI["Dịch vụ AI (mạng nội bộ)"]
        AIS["ai-service<br/>Python FastAPI :8000<br/>stateless · 5 agent + orchestrator"]
        CAT[("Topic catalog<br/>YAML trong image")]
    end

    subgraph DATA["Lưu trữ"]
        INTDB[("interview_db<br/>PostgreSQL")]
        AIDB[("ai_db<br/>PostgreSQL + pgvector<br/>knowledge_chunks")]
        REDIS[("Redis<br/>khóa phiên, quota")]
        S3[("MinIO / S3<br/>file CV của job-service")]
    end

    PIPE["data-pipeline<br/>Python · DE<br/>crawl, chunk, embed, index"]

    CAND -->|HTTPS| WEB
    WEB -->|"HTTPS + JWT<br/>chat: fetch stream SSE"| GW
    WEB -.->|"âm thanh (GĐ2)<br/>đã được đồng ý"| VG
    GW -->|"HTTP + x-auth-user"| INT
    GW -->|HTTP| AUTH
    GW -->|HTTP| USER
    GW -->|HTTP| JOB
    GW -.->|"chỉ /ai/api/health"| AIS
    VG -.->|"cùng contract chat<br/>HTTP + SSE (GĐ2)"| INT
    VG -.->|"HTTPS (GĐ2)"| STT
    INT -->|"REST + SSE<br/>X-Internal-Token"| AIS
    INT -->|"TCP<br/>application.getCvFile"| JOB
    INT -->|"HTTPS<br/>presigned URL"| S3
    JOB --> S3
    INT --> INTDB
    INT --> REDIS
    AIS -->|"SQL (đọc)"| AIDB
    AIS -->|"HTTPS API"| LLM
    AIS --- CAT
    PIPE -->|"SQL (ghi)"| AIDB
    PIPE -->|"embeddings"| LLM

    classDef have fill:#e6f4ea,stroke:#2e7d32,color:#000
    classDef mock fill:#fff8e1,stroke:#f9a825,color:#000
    classDef plan fill:#f5f5f5,stroke:#9e9e9e,stroke-dasharray:4 3,color:#000
    classDef ext fill:#e3f2fd,stroke:#1565c0,color:#000
    class AUTH,USER,GW,REDIS have
    class AIS,CAT mock
    class WEB,JOB,INT,PIPE,INTDB,AIDB,S3,VG plan
    class LLM,CAND,STT ext
```

Chú giải màu: xanh lá = đã có trong repo; vàng = mock; xám nét đứt = kế hoạch, chưa có code; xanh dương = bên ngoài.

## 4. Danh mục container

| Container | Công nghệ | Trách nhiệm trong phạm vi phần AI | Chủ sở hữu | Hiện trạng |
|---|---|---|---|---|
| **Web App** | Next.js (`apps/web`, ADR-005) | **Phòng họp** kiểu cuộc họp trực tuyến: khung AI là ảnh tĩnh, khung video ứng viên (tự xem cục bộ, không gửi đi), khung chat, đồng hồ, trạng thái AI; xin đồng ý trước khi bật camera (và micro ở GĐ2); đọc stream SSE bằng `fetch`; trang báo cáo | FSD (đề xuất) | Kế hoạch |
| **Lớp voice trong Web App** *(GĐ2, tùy chọn A, mặc định)* | Trình duyệt (TTS, STT bấm-để-nói) | TTS đọc `done.question`; STT bấm-để-nói, cho sửa transcript, gửi qua `/answer` kèm bản STT gốc; **không ghi âm** | DE (feature 015, S4-DE-5) | Kế hoạch (Stretch) |
| **voice-gateway** *(GĐ2, tùy chọn B)* | Hạ tầng voice-agent có sẵn (chưa chọn), kèm STT và TTS | Nhận âm thanh ứng viên đã đồng ý, phát hiện hết lượt nói, chuyển thành văn bản, **gọi đúng contract chat** qua interview-service, đọc câu hỏi trả về bằng TTS; khi lỗi thì chuyển sang chat. **Không giữ dữ liệu phiên, không ghi âm** | AIE + DE (đề xuất) | Kế hoạch (chờ ADR-009) |
| **STT / TTS provider** *(GĐ2)* | Dịch vụ ngoài (chưa chọn) | Nhận dạng và tổng hợp giọng nói tiếng Việt xen thuật ngữ Anh | Bên ngoài | Chưa khảo sát |
| **API Gateway** | Apache APISIX 3.14 + etcd, ADC sync | Điểm vào công khai duy nhất; xác thực JWT; inject `x-auth-user`; định tuyến; chỉ cho `/ai/api/health` ra ngoài; không buffer SSE | DE | Có (route `/ai/*` thêm trong nhánh `feat/aie`, chưa kiểm chứng) |
| **auth-service** | NestJS | Đăng ký, đăng nhập, JWT | FSD | Có |
| **user-service** | NestJS | Hồ sơ người dùng | FSD | Có |
| **job-service** | NestJS | Tin tuyển dụng và **ứng tuyển, giữ file CV**; cung cấp TCP `application.getCvFile` kèm presigned URL và `application.getJobDescription` (JD của job gắn application, S2-FSD-11) | FSD | Kế hoạch |
| **interview-service** | NestJS | **Chủ sở hữu mọi dữ liệu phỏng vấn** (session, plan, candidate state, transcript, evaluation, report, `cv_profile`); điều phối gọi ai-service qua `AiInterviewClient`; relay SSE; khóa phiên và quota qua Redis; chống gửi trùng | FSD | Kế hoạch |
| **ai-service** | Python 3.11 hoặc 3.12, FastAPI, Pydantic v2, SDK `openai` | Thực hiện **toàn bộ logic AI không trạng thái**: CV Parser, **JD Parser**, Planner, Evaluator, Interviewer, Reporter; orchestrator, policy, tổng hợp điểm; truy xuất RAG; SSE | AIE | Mock |
| **Topic catalog** | YAML (`app/catalog/*.yaml`) | Danh sách chủ đề và tình huống theo vị trí (6 track, 90 topic); đóng gói cùng image ai-service | AIE + DE | Có (nội dung chưa review) |
| **interview_db** | PostgreSQL 16 | Dữ liệu phỏng vấn của interview-service | FSD | Kế hoạch |
| **ai_db** | PostgreSQL 16 + pgvector (`pgvector/pgvector:pg16`) | Bảng `knowledge_chunks` (`interview_qa`, `textbook`) | AIE (DDL) + DE (tạo DB, nạp dữ liệu) | Kế hoạch (DDL đã thiết kế, chưa chạy) |
| **Redis 8** | Redis | Khóa phiên `interview:lock:{sessionId}`, quota ngày; cache RAG (Sprint 4) | FSD (+ AIE cho cache) | Có trong compose |
| **MinIO / S3** | S3 API | Lưu file CV (một bản duy nhất, thuộc job-service) | DE / FSD | Kế hoạch |
| **data-pipeline** | Python | Crawl, chunk, dedup, embed, index vào `ai_db`; dùng chung module chunking và repository với ai-service | DE | Kế hoạch |
| **LLM provider** | OpenRouter → OpenAI (API OpenAI-compatible) | Sinh text và JSON; tạo embedding | Bên ngoài | Có (thử bằng smoke test) |

## 5. Giao tiếp giữa các container

| # | Từ | Tới | Giao thức | Mục đích | Xác thực | Timeout / ghi chú |
|---|---|---|---|---|---|---|
| I1 | Web App | API Gateway | HTTPS, JSON và SSE qua `fetch` | Mọi lời gọi của ứng viên | JWT | `EventSource` không dùng được vì cần header `Authorization` và POST (D06 §7.5) |
| I2 | API Gateway | interview-service | HTTP | Định tuyến `/interview/*` | Gateway verify JWT, inject `x-auth-user` | `timeout.read` upstream ≥ 60 s cho SSE |
| I3 | API Gateway | ai-service | HTTP | **Chỉ** `GET /ai/api/health` | Công khai | Route còn lại yêu cầu JWT trong cấu hình hiện tại; mục tiêu là chặn hẳn (SEC01) |
| I4 | interview-service | ai-service | REST/HTTP, SSE | `cv/parse`, `jd/parse`, `start`, `next-turn`, `finalize`, `health` | Header `X-Internal-Token` (chưa làm) | 30 s, 40 s, 45 s, 90 s, 5 s (D06 §7.4); snake_case ở biên, ánh xạ camelCase làm ở client |
| I5 | interview-service | job-service | NestJS TCP | `application.getCvFile`: kiểm tra application thuộc ứng viên, trả presigned URL | Nội bộ | Kiểm quyền sở hữu là bắt buộc (D10 P9) |
| I16 | interview-service | job-service | NestJS TCP | `application.getJobDescription`: JD của job gắn application, kiểm application thuộc ứng viên | Nội bộ | S2-FSD-11 (đề xuất, chờ FSD xác nhận); JD thô được gửi tới ai-service qua I4, không lưu |
| I6 | interview-service | MinIO / S3 | HTTPS, presigned URL | Tải file CV, stream, tối đa 10 MB, không ghi đĩa | URL có hạn 5 phút | |
| I7 | interview-service | interview_db | SQL (MikroORM) | Lưu và đọc dữ liệu phiên | | State có `state_version` để khóa lạc quan |
| I8 | interview-service | Redis | Redis protocol | Khóa phiên TTL 60 s, quota ngày | | |
| I9 | ai-service | ai_db | SQL (psycopg 3 async, pgvector; `app/rag/repository.py`) | **Đọc** `knowledge_chunks` | Phiên `default_transaction_read_only=on` (đã cài, có test tích hợp); tài khoản chỉ đọc (đề xuất, DE tạo) | Chỉ ai-service và pipeline đụng `ai_db` |
| I10 | ai-service | LLM provider | HTTPS | Chat completions, embeddings | API key trong biến môi trường | Retry tối đa 2 lần; ngân sách thời gian theo agent (D08 §9.3) |
| I11 | data-pipeline | ai_db | SQL | **Ghi** chunk, upsert theo `content_hash` | Tài khoản ghi | Idempotent (CON V) |
| I12 | data-pipeline | LLM provider | HTTPS | Embedding khi index | API key | |
| I13 | Web App | voice-gateway *(GĐ2)* | Kênh âm thanh thời gian thực của hạ tầng voice-agent | Truyền âm thanh ứng viên và phát giọng AI | Token của phiên | Chỉ mở sau khi ứng viên đồng ý micro; kênh cụ thể do ADR-009 chọn |
| I14 | voice-gateway | interview-service *(GĐ2)* | HTTP + SSE, **cùng contract như chat** | Gửi văn bản đã nhận dạng, nhận câu hỏi | Thông tin nội bộ | interview-service và ai-service **không đổi** |
| I15 | voice-gateway | STT / TTS provider *(GĐ2)* | HTTPS hoặc luồng của nhà cung cấp | Nhận dạng và tổng hợp giọng nói | API key | Âm thanh không lưu; nhà cung cấp được nêu trong thông báo đồng ý |

Quy tắc ràng buộc (constitution): service **không** truy vấn hay ghi DB của service khác (I); NestJS ↔ NestJS dùng TCP, NestJS ↔ ai-service dùng REST (II); contract đổi thì cập nhật tài liệu cùng PR (III); ai-service stateless và chỉ sở hữu `knowledge_chunks` (IV).

## 6. Dữ liệu và quyền sở hữu

| Dữ liệu | Nơi lưu | Chủ sở hữu | ai-service đọc/ghi |
|---|---|---|---|
| Session, transcript, evaluation từng lượt, report | `interview_db` | interview-service | Nhận qua request, trả qua response; **không lưu** |
| `cv_profile` (đã bỏ liên hệ), `cv_file_ref` | `interview_db` | interview-service | Tạo ra (CV Parser) rồi trả về |
| Plan và candidate state | `interview_db` (JSONB) | interview-service | Nhận trong request, trả bản mới trong `done` |
| **File CV gốc** | MinIO / S3 | job-service | Chỉ thấy bytes trong một request `cv/parse`, không lưu |
| Knowledge base (`interview_qa`, `textbook`) | `ai_db.knowledge_chunks` | ai-service (schema), pipeline (nội dung) | Đọc |
| Topic catalog | File YAML trong repo, đóng gói trong image | AIE + DE | Đọc lúc chạy |
| Prompt | File trong repo (`app/prompts/*.md`) | AIE | Đọc lúc chạy |
| Khóa phiên, quota | Redis | interview-service | Không |
| Token, độ trễ, phiên bản prompt, fallback | `ai_meta` JSONB trong `interview_db` | interview-service | Tạo `metadata` trong response |
| Dữ liệu phiên trong ai-service | **Không có** | | Log chỉ chứa id và số đo |
| **Video ứng viên** | **Không lưu ở đâu cả**: chỉ hiển thị trong trình duyệt của chính ứng viên | Trình duyệt | Không nhận (diễn giải A-6) |
| `jd_profile` (yêu cầu đã trích từ JD) | `interview_db` (đề xuất) | interview-service | Tạo ra (JD Parser) rồi trả về |
| **JD gốc** | `job_db` (job-service) | job-service | Chỉ thấy văn bản trong một request `jd/parse`, không lưu |
| Transcript STT gốc và bản đã sửa (tùy chọn A) | `interview_db` (đề xuất) | interview-service | Chỉ nhận văn bản, không có audio |
| **Âm thanh ứng viên** *(GĐ2)* | Không lưu; chỉ đi tới nhà cung cấp STT đã khai báo | voice-gateway | Không nhận âm thanh, chỉ nhận văn bản |
| Cờ đồng ý (`media_consent_at`, `learning_consent_at`) | `interview_db` (đề xuất; FSD xác nhận) | interview-service | Không |

Ranh giới quan trọng: transcript, câu trả lời, `cv_profile` và file CV **không bao giờ** đi vào `knowledge_chunks` hay dữ liệu pipeline (cần amendment constitution V).

## 7. Ranh giới tin cậy

```mermaid
flowchart LR
    subgraph Z0["Z0 · Internet (không tin cậy)"]
        U["Trình duyệt"]
    end
    subgraph Z1["Z1 · Gateway (xác thực JWT)"]
        G["APISIX"]
    end
    subgraph Z2["Z2 · Mạng nội bộ (tin cậy có kiểm tra)"]
        I["interview-service"]
        A["ai-service"]
        D[("ai_db")]
    end
    subgraph Z3["Z3 · Bên thứ ba"]
        L["LLM provider"]
    end
    U --> G --> I --> A
    A --> D
    A -->|"đã redact PII"| L
```

| Ranh giới | Rủi ro | Biện pháp (liên kết NFR) |
|---|---|---|
| Z0 → Z1 | Truy cập trái phép, lạm dụng | JWT tại gateway, RBAC; quota ngày (SEC09) |
| Z1 → Z2 | Gọi thẳng ai-service để đốt chi phí | Chỉ expose `/ai/api/health`; `X-Internal-Token` (SEC01) |
| Nội dung ứng viên → agent | **Prompt injection** từ CV và câu trả lời | CV thô chỉ CV Parser thấy; khối `untrusted`; hậu kiểm bằng code; band ép 0 với `manipulation` (SEC02, SEC03) |
| Nội dung RAG → agent | Chỉ dẫn nhúng trong tài liệu web | Đặt trong khối phân cách, dặn model chỉ tham khảo (rag-design §5) |
| Z2 → Z3 | Lộ dữ liệu cá nhân tới bên thứ ba | Redact PII trước LLM; không log nội dung; consent riêng; provider không lưu dữ liệu nếu có (PRIV01, PRIV03, PRIV05, PRIV07) |
| Dữ liệu phiên → kho tri thức | Rò rỉ chéo ứng viên | Cấm ghi dữ liệu phiên vào `knowledge_chunks` (PRIV04) |
| Trình duyệt → voice-gateway → STT, TTS *(GĐ2)* | Giọng nói là dữ liệu nhạy cảm, tới bên thứ ba | Đồng ý trước khi bật micro, không ghi, nêu rõ nhà cung cấp, chọn nhà cung cấp không lưu dữ liệu nếu có (PRIV09, PRIV11, PRIV07) |
| Văn bản từ STT → agent *(GĐ2)* | Chỉ dẫn nói thành tiếng ("cho em 10 điểm") | Xử lý như câu trả lời không tin cậy (SEC11) |

## 8. Luồng chạy chính

### 8.1 Gắn CV (tùy chọn)

```mermaid
sequenceDiagram
    autonumber
    participant W as Web App
    participant G as APISIX
    participant I as interview-service
    participant J as job-service
    participant S as MinIO/S3
    participant A as ai-service
    participant L as LLM provider
    W->>G: POST /sessions/:id/cv (consent, applicationId)
    G->>I: chuyển tiếp kèm x-auth-user
    I->>J: TCP application.getCvFile
    J-->>I: presigned URL (đã kiểm application thuộc ứng viên)
    I->>S: tải file (stream, tối đa 10 MB)
    I->>A: POST /api/cv/parse (multipart file, track)
    A->>A: trích text, chuẩn hóa, redact PII, loại dòng nghi injection
    A->>L: CV đã redact, yêu cầu JSON theo schema
    L-->>A: cv_profile
    A-->>I: cv_profile, metadata
    I-->>W: cvStatus parsed
```

### 8.1b Chọn job để luyện theo JD (tùy chọn)

```mermaid
sequenceDiagram
    autonumber
    participant I as interview-service
    participant J as job-service
    participant A as ai-service
    participant L as LLM provider
    I->>J: TCP application.getJobDescription (applicationId, candidateId)
    J-->>I: JD của job (đã kiểm application thuộc ứng viên)
    I->>A: POST /api/jd/parse (văn bản JD, track)
    A->>A: chuẩn hóa, redact liên hệ, quét injection
    A->>L: JD đã redact, yêu cầu JSON theo schema
    L-->>A: jd_profile (must, nice, topic_id hoặc out_of_catalog)
    A-->>I: jd_profile
    Note over I,A: jd_profile đi vào POST /api/start. Planner tăng trọng số topic. JD không vào RAG.
```

### 8.2 Một lượt phỏng vấn (đường nóng)

```mermaid
sequenceDiagram
    autonumber
    participant W as Web App
    participant I as interview-service
    participant A as ai-service
    participant L as LLM provider
    W->>I: POST /sessions/:id/answer (SSE)
    I->>I: khóa phiên, kiểm turnNumber, lưu câu trả lời
    I->>A: POST /api/next-turn (plan, state, topic_turns, answer)
    A->>L: Evaluator (JSON, không stream)
    L-->>A: Evaluation
    A->>A: hậu kiểm, cập nhật state, policy chọn action
    A->>L: Interviewer (stream)
    L-->>A: token
    A-->>I: SSE meta, token, done (evaluation, state, turn)
    I-->>W: relay meta, token, done (không có điểm)
    I->>I: lưu evaluation, state mới, câu hỏi
```

Độ trễ đường nóng gồm hai lời gọi LLM nối tiếp (Evaluator rồi Interviewer); chỉ tiêu và rủi ro ở NFR-AI-PERF01. Trường hợp `dont_know` bỏ qua Evaluator.

### 8.3 Kết thúc và báo cáo

```mermaid
sequenceDiagram
    autonumber
    participant W as Web App
    participant I as interview-service
    participant A as ai-service
    participant L as LLM provider
    W->>I: POST /sessions/:id/end (hoặc hết giờ)
    I->>A: POST /api/finalize (plan, state, toàn bộ lượt kèm evaluation)
    A->>A: code tính điểm, verdict, confidence
    A->>L: Reporter (JSON)
    L-->>A: nhận xét, điểm mạnh, cần cải thiện
    A->>A: kiểm evidence_turns, tra link từ catalog
    A-->>I: report (hoặc status partial nếu Reporter lỗi)
    I->>I: lưu report
    W->>I: GET /sessions/:id/report (polling)
```

### 8.4 Một lượt bằng giọng nói (tùy chọn B, ngoài kế hoạch mặc định, bản nháp)

Voice-gateway là bộ chuyển đổi: toàn bộ logic phỏng vấn vẫn đi qua đường chat ở §8.2.

```mermaid
sequenceDiagram
    autonumber
    participant W as Web App
    participant V as voice-gateway
    participant T as STT/TTS provider
    participant I as interview-service
    participant A as ai-service
    W->>V: âm thanh ứng viên (đã đồng ý micro)
    V->>V: phát hiện ứng viên dứt lời
    V->>T: âm thanh, yêu cầu văn bản
    T-->>V: văn bản (kèm độ tin cậy nếu có)
    V->>I: POST /sessions/:id/answer (cùng contract chat)
    I->>A: POST /api/next-turn
    A-->>I: SSE meta, token, done
    I-->>V: SSE token (câu hỏi)
    V->>T: câu hỏi, yêu cầu giọng nói
    T-->>V: âm thanh
    V-->>W: phát giọng AI
    Note over V,W: lỗi ở bất kỳ bước nào của voice thì chuyển sang chat, giữ nguyên state
```

## 9. Bên trong ai-service (xem trước Level 3)

| Thành phần mục tiêu | Trách nhiệm | File hiện có trong mock (`apps/ai-service/app/`) |
|---|---|---|
| API layer | Route, validate Pydantic, SSE, format lỗi | `main.py`, `sse.py`, `api_error.py`, `models_*.py` |
| Orchestrator (state machine) | Điều phối một lượt: chấm, cập nhật state, policy, hỏi | `turn_engine.py` |
| Policy | Chọn action theo bảng luật | `policy.py` |
| Agent: CV Parser | Trích `cv_profile` | `mock_cv_parser.py` + `cv_text.py` (phần trích text, redact, injection là code thật) |
| Agent: Planner | Sinh plan từ catalog | `mock_planner.py` |
| Agent: Evaluator | Chấm band, bằng chứng | `mock_evaluator.py` |
| Agent: Interviewer | Diễn đạt câu hỏi, stream | `mock_interviewer.py` |
| Agent: Reporter + scoring | Tổng hợp điểm (code) + nhận xét | `report_scoring.py` |
| Topic catalog loader | Đọc YAML, kiểm schema | `catalog/` |
| LLM client | Client OpenAI-compatible, retry, repair, đo usage | `llm/gateway.py`, `llm/retry.py`, `llm/structured_output.py`, `llm/usage.py`, `llm/settings.py` (đã cài đặt, test bằng LLM giả; chưa nối vào agent) |
| RAG module | Embedding, truy xuất, repository, chunking | **Chưa có** (`app/rag/` theo rag-design §6) |
| Prompt store | Prompt có phiên bản | `prompts/store.py` (chưa có prompt agent thật, chỉ `smoke.v1.md`) |
| Agent registry | Chọn `mock` hoặc `llm` theo từng agent | `agents/registry.py` (mặc định `mock`) |

Hiện các file `mock_*` dùng quy tắc thay LLM; khi có LLM thật chỉ thay phần thân agent, giữ nguyên interface và orchestrator.

## 10. Triển khai

```mermaid
flowchart LR
    subgraph HOST["Máy dev hoặc VPS staging · Docker Compose"]
        GWC["apisix :9080<br/>etcd, adc"]
        AISC["ai-service :8000"]
        PG["PostgreSQL (nhiều DB) :5534<br/>pgvector/pgvector:pg16"]
        RD["Redis :6374"]
        MN["MinIO :9000/:9001"]
        subgraph APPS["Chạy bằng pnpm dev trên host (dev)"]
            NE["auth, user, job, interview, notification"]
        end
    end
    GWC --> NE
    GWC -.-> AISC
    NE --> AISC
    AISC --> PG
    NE --> PG
    NE --> RD
    NE --> MN
```

| Hạng mục | Giá trị hiện tại | Ghi chú |
|---|---|---|
| Đóng gói ai-service | `apps/ai-service/Dockerfile`, `python:3.12-slim`, `uvicorn app.main:app` cổng 8000, healthcheck `curl /api/health` | Catalog YAML nằm trong image; chưa build lại với thư viện CV mới |
| Tên container, network | `nest_turbo_*`, `nest-turbo-network` trong nhánh này | Nhánh `chore/rename-project-scope` (DE) đổi sang `ai_recruit_*` và `ai-recruit-network`; khối `ai-service` phải đổi theo sau khi nhánh đó merge |
| Biến môi trường ai-service | `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`, `LLM_STRUCTURED_OUTPUTS`, `LOG_LLM_IO`, `LLM_MODEL_<AGENT>`, `AGENT_<AGENT>_MODE`, `MOCK_STREAM_DELAY_MS` | Cần thêm: `X-Internal-Token`, kết nối `ai_db` |
| Gateway | Route `/ai/*` trong `config/apisix/conf/apisix-dev.yaml`; chỉ `/ai/api/health` công khai | Chưa kiểm chứng SSE qua gateway |
| Scale | Thêm instance ai-service sau gateway hoặc load balancer; không cần sticky session vì stateless | Quy mô demo khoảng 20 phiên đồng thời |
| Staging | Docker Compose trên VPS hoặc cloud có HTTPS | Thuộc DE (feature 014) |
| voice-gateway *(GĐ2)* | Container riêng chạy hạ tầng voice-agent đã chọn; cổng và tên chờ ADR-009 | Không đụng tới ai-service; có thể tắt hẳn mà chat vẫn chạy |

## 11. Chiến thuật kiến trúc cho thuộc tính chất lượng

| Thuộc tính | Chiến thuật | NFR |
|---|---|---|
| Hiệu năng | Evaluator output gọn (`max_tokens` 350), RAG lấy trước một lần lúc plan, bỏ qua Evaluator khi `dont_know`, client HTTP dùng chung, stream câu hỏi, bất đồng bộ I/O | PERF01..09 |
| Khả năng mở rộng | Stateless, thêm process ngang, catalog dạng dữ liệu | SCAL01..04 |
| Độ tin cậy | Retry giới hạn, repair, fallback theo agent, bảng xử lý lỗi, giới hạn cứng bằng code, interview-service đọc hết stream | REL01..09 |
| Độ chính xác chấm | Rubric theo level, luật khắt khe áp bằng prompt **và** code, hậu kiểm quote, điểm do code tổng hợp, tách Evaluator khỏi Interviewer | QUAL01..15 |
| Bảo mật | Gateway duy nhất, `X-Internal-Token`, cô lập CV thô, khối untrusted, validate input | SEC01..09 |
| Quyền riêng tư | Redact trước LLM, không log nội dung, consent riêng, cấm dữ liệu phiên vào kho tri thức | PRIV01..08 |
| Chi phí | Model nhỏ cho đường nóng, ghi usage mọi lời gọi, cảnh báo ngưỡng, quota ngày | COST01..05 |
| Bảo trì | Policy và scoring là code thuần nên unit test được; prompt có phiên bản; catalog tách khỏi code; file nhỏ | MNT01..08 |
| Hội thoại giọng nói | Tách voice-gateway thành adapter gọi contract chat; chat giữ làm dự phòng; độ trễ đo tách theo thành phần và cải thiện dần | PERF10, PERF11, REL11, CMP08 |
| Đồng ý và quyền riêng tư của media | Xin đồng ý trước khi bật thiết bị; video không rời trình duyệt; âm thanh không lưu; không phân tích cảm xúc | PRIV09..PRIV12 |

## 12. Quyết định kiến trúc liên quan

| ADR / nguồn | Nội dung | Ảnh hưởng tới L2 |
|---|---|---|
| ADR-001 | APISIX thay Kong | Gateway duy nhất |
| ADR-002 | Database-per-service | `interview_db` và `ai_db` tách |
| ADR-003 | TCP giữa NestJS, REST với ai-service | I4, I5 |
| ADR-004 | interview-service sở hữu dữ liệu phỏng vấn, ai-service stateless | §6 |
| ADR-005 | Frontend trong monorepo | Web App |
| ADR-006 | Gộp application vào job-service | I5 (CV lấy từ job-service) |
| **ADR-008** | Evaluator mỗi lượt, Planner một lần, orchestrator bằng code | §9 |
| Constitution IV, V | AI stateless; pipeline tái lập, không dữ liệu cá nhân vào kho | §6, §7; cần amendment vì ADR-008 đổi nội dung contract |
| **ADR-009** *(đề xuất, chưa viết; chỉ khi chọn tùy chọn B)* | voice-gateway, hạ tầng voice-agent, phân kỳ chat trước voice | §3, §8.4; xem BRD §0.3 |

## 13. Khoảng cách giữa mục tiêu và hiện trạng

| # | Hạng mục | Mục tiêu | Hiện trạng | Việc cần làm |
|---|---|---|---|---|
| G1 | Agent LLM | 5 agent gọi LLM thật | Mock bằng quy tắc | FR-AI-013, 020, 030, 037, 052 |
| G2 | Truy xuất RAG | `ai_db` + `app/rag/` | Chưa có DDL chạy, chưa có module | FR-AI-060..062, cần DE (T016) |
| G3 | Độ bền | Retry, repair, fallback đầy đủ | Chưa | FR-AI-070..072 |
| G4 | Bảo vệ route | `X-Internal-Token`, chặn `/ai/*` | Route có, token chưa | FR-AI-091 |
| G5 | `interview-service` | Có, quản lý phiên và relay SSE | Chưa tồn tại | FSD, cần duyệt contract |
| G6 | `job-service` | `application.getCvFile` | Chưa tồn tại | FSD; thiếu thì phỏng vấn không CV |
| G7 | Streaming qua gateway | Không buffer | Chưa kiểm chứng | Spike tuần 4 (CMP04) |
| G8 | Tên container | `ai_recruit_*` | `nest_turbo_*` | Chờ nhánh rename merge rồi sửa khối ai-service |
| G9 | Python | Một phiên bản (CI 3.11 dự kiến) | 3.12 ở Docker, 3.9 máy dev | Chốt một phiên bản (CMP03) |
| G10 | Constitution | Amendment IV, V | Constitution đang Proposed | Cả team duyệt |
| G11 | Image Docker | Build với thư viện CV mới | Chưa build lại | Build khi Docker chạy |
| G12 | Phòng họp (Web App) | Có, theo FR-AI-100..105 | Chưa tồn tại | FSD, chưa xác nhận người thực hiện |
| G13 | Lưu cờ đồng ý | `media_consent_at`, `learning_consent_at` trong `interview_db` | Chưa có | FSD xác nhận migration |
| G14 | Thời lượng 15 đến 20 phút | Planner và policy theo công thức mới | Mock vẫn nhận 15 đến 45 phút | FR-AI-001, 003, 035 |
| G15 | voice-gateway | Có (GĐ2) | Chưa chọn hạ tầng voice-agent, chưa có ADR | Khảo sát, ADR-009 (chỉ khi giai đoạn 1 ổn) |
| G16 | JD Parser và TCP lấy JD | Có (S2-AIE-6, S2-FSD-11) | Chưa | Phase 04; FSD xác nhận S2-FSD-11 |
| G17 | Đường ghi RAG | DE sở hữu (spec 005) | Chưa chạy | DE; AIE chỉ làm đường đọc (Phase 03) |

## 14. Câu hỏi mở

1. `ai-service` đọc `ai_db` qua tài khoản chỉ đọc riêng, hay dùng chung tài khoản với pipeline? (Đề xuất: tách.)
2. DDL `knowledge_chunks` đặt trong `scripts/init-databases.sh` (constitution I) hay có migration riêng cho `ai_db`?
3. `X-Internal-Token` cấp phát và xoay vòng thế nào giữa interview-service và ai-service?
4. Cache RAG (Redis, TTL 1 giờ, Sprint 4) đặt ở ai-service hay ở interview-service? Hiện thiết kế ghi ai-service nhưng ai-service chưa kết nối Redis.
5. Relay SSE trong interview-service có chịu được nén (compression middleware) và timeout của APISIX không? (D06 §7.5)
6. voice-gateway đặt ở biên công khai (cùng lớp với gateway) hay trong mạng nội bộ? Kênh âm thanh thời gian thực có đi qua APISIX không, hay mở cổng riêng? (phụ thuộc hạ tầng voice-agent chọn)
7. Cờ đồng ý và thời điểm đồng ý lưu ở interview-service (đề xuất). Có cần lưu bản chữ của thông báo đồng ý theo phiên bản không?
8. Khung chat có nên hiển thị lại câu hệ thống nghe được khi dùng voice (FR-AI-123)?
9. Với tùy chọn A (voice trong Web App), có cần container hay route nào mới ở phía gateway không? (Mặc định: không, vì dùng lại `/answer`.)
