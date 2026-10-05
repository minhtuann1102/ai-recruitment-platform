# AI Recruitment Platform Constitution

## Core Principles

### I. Service tự chủ & Database-per-Service

- Mỗi service sở hữu PostgreSQL database riêng: `user_db`, `job_db`, `interview_db`,
  `notification_db`, `ai_db`. `auth-service` stateless, không có DB (ADR-002).
- Service MUST NOT query, join hay ghi vào DB của service khác. Dữ liệu chéo service chỉ đi qua
  TCP message hoặc REST API của service sở hữu.
- Schema của mỗi DB chỉ được thay đổi bằng migration nằm trong chính service đó. Ngoại lệ duy
  nhất: `ai_db` (service Python, chưa có migration tool) định nghĩa DDL trong
  `scripts/init-databases.sh`; phần DDL đó do AIE sở hữu, DE sở hữu phần tạo database.
- Ứng tuyển (applications) là module của `job-service`, không tách service riêng (ADR-006).
- Script seed/ingest của data pipeline chỉ được ghi vào DB khác `ai_db` khi bám đúng schema do
  migration của service sở hữu tạo ra; MUST NOT tạo/sửa bảng ngoài migration.

**Lý do:** fault isolation, deploy và migrate độc lập, ép kiến trúc giao tiếp qua contract.

### II. Gateway duy nhất & Transport đã chốt

- Apache APISIX là entry point public duy nhất; Kong bị loại bỏ hoàn toàn (ADR-001).
- JWT được verify tại gateway; gateway inject header `x-auth-user` cho service phía sau. Service
  MUST enforce RBAC bằng `@Roles()` với role `Admin | Candidate | Employer`.
- NestJS ↔ NestJS dùng NestJS TCP transport; NestJS ↔ ai-service dùng REST/HTTP (ADR-003).
  gRPC chỉ là stretch goal, MUST NOT tồn tại song song với TCP trong code chính.
- Mỗi route public mới MUST được khai báo trong `config/apisix/conf/apisix-*.yaml`.

**Lý do:** một điểm kiểm soát auth/RBAC; transport đơn giản, dễ debug cho team 3 người.

### III. Contract-First

- `docs/architecture/api-contracts.md` (HTTP + TCP) và `docs/architecture/ai-integration.md`
  (AI REST) là nguồn sự thật cho contract. Thay đổi contract MUST cập nhật docs trong cùng PR.
- Response/error MUST theo format trong `docs/conventions.md` (`{data, meta}` /
  `{statusCode, message, errorCode, details}`).
- interview-service gọi AI qua interface `AiInterviewClient`; Mock và Real hoán đổi bằng env
  `AI_SERVICE_MOCK`, không sửa code nghiệp vụ. Mapping snake_case ↔ camelCase làm tại biên client.
- Mỗi endpoint HTTP MUST có Swagger cập nhật.

**Lý do:** 3 workstream chạy song song, contract rõ thì không chặn nhau.

### IV. AI Stateless & quyền sở hữu dữ liệu phỏng vấn

- Toàn bộ dữ liệu phỏng vấn (sessions, turns, scores, results, question bank) thuộc
  `interview-service` (ADR-004).
- ai-service là stateless processor: nhận lịch sử qua request, trả kết quả theo contract
  `start` / `next-turn` / `finalize` (ADR-007), MUST NOT lưu phiên. ai-service chỉ sở hữu
  `knowledge_chunks` trong `ai_db`.
- Lỗi/timeout từ LLM provider MUST có retry giới hạn và fallback (mock response) để luồng
  phỏng vấn không chết.
- LLM provider truy cập qua API OpenAI-compatible cấu hình bằng env (`LLM_BASE_URL`, key, model).
  Model mặc định: GPT-4o-mini (LLM), `text-embedding-3-small` 1536 dims (embedding). Đổi model
  embedding là thay đổi contract dữ liệu (dims) và cần amendment hoặc ADR.

**Lý do:** tách trách nhiệm rõ, AI có thể thay thế/mock mà không mất dữ liệu nghiệp vụ.

### V. Data Pipeline tái lập được

- Pipeline (crawl → clean → chunk → dedup → embed → index) MUST idempotent: chạy lại cùng input
  không sinh chunk trùng (content-hash dedup trước embed + upsert khi index).
- Dữ liệu thô và processed MUST NOT commit (gitignore); chỉ commit seed curated nhỏ
  (vd `data/seeds/qa_seed.json`).
- Mỗi chunk MUST có `source_type` (`interview_qa | job_description | textbook`) và metadata đủ để
  lọc (tối thiểu category; chunk_type khi có).
- Mỗi lần chạy MUST in thống kê: số record vào, số chunk, tỉ lệ dedup, số embedding lỗi.
- Quality gates (data-pipeline.md §9): embedding non-null ≥ 99%, dedup < 5%, đạt số chunk tối
  thiểu theo sprint (200 / 1500 / 6000).
- Crawler MUST tôn trọng robots.txt, có rate limit, MUST NOT lưu thông tin cá nhân (email, số điện
  thoại của người liên hệ).

**Lý do:** RAG chỉ tốt bằng dữ liệu của nó; pipeline phải chạy lại được trên máy bất kỳ thành viên.

### VI. Quality Gates (NON-NEGOTIABLE)

- CI MUST chạy `lint`, `check-types`, `test` cho mọi PR; PR đỏ MUST NOT merge.
- Coverage unit test ≥ 60% cho mỗi NestJS service; Python service MUST có test cho logic
  xử lý chính.
- MUST NOT skip/xóa test đang fail, mock giả để qua CI.
- MUST NOT commit secret (`.env`, API key, password thật). Mọi env var mới MUST có mặt trong
  `.env.example` (placeholder) và `turbo.json` > `globalEnv` nếu dùng trong NestJS.
- Migration MUST chạy thành công trên DB sạch trước khi merge.

**Lý do:** đồ án chấm điểm trên demo chạy được; một lỗi build chặn cả 3 người.

### VII. Đơn giản & kỷ luật phạm vi

- YAGNI / KISS / DRY. Không thêm service, hạ tầng hay abstraction khi chưa có task cần.
- Task gắn nhãn Stretch chỉ làm khi task Bắt buộc của sprint đã xong.
- Khi trễ, cắt phạm vi theo thứ tự trong `docs/sprint-plan.md` (Mức 1 → Mức 4), không cắt
  Quality Gates.
- Phần thừa từ starter repo (Kong, gRPC, tên `nest-turbo-*`/`@app/*`, prefix `nest_turbo_*`)
  MUST bị gỡ bỏ, không giữ song song.
- File code nên < 200 dòng; vượt thì tách module theo trách nhiệm.

**Lý do:** team 3 người, hạn cứng 21/12/2026.

## Ràng buộc kỹ thuật & hạ tầng

| Thành phần | Chuẩn |
|---|---|
| Runtime / Backend | Node.js 22, NestJS 11, TypeScript, MikroORM 7 |
| Monorepo | Turborepo + pnpm 10; packages tên `@ai-recruit/*` |
| Database | PostgreSQL 16, image `pgvector/pgvector:pg16`; dev local: 1 instance, nhiều DB qua init script |
| Cache | Redis 8 |
| Gateway | Apache APISIX 3.14 (+ etcd, ADC sync) |
| AI service | Python FastAPI, dependency pin trong `requirements.txt` |
| Data pipeline | Python, đặt tại `apps/data-pipeline/` |
| Frontend | Next.js tại `apps/web` (ADR-005) |
| Object storage | MinIO (S3-compatible) cho CV, avatar, logo |
| Container | Docker Compose; container prefix `ai_recruit_*` |
| Staging | Docker Compose trên VPS/cloud, có HTTPS |

- Primary key UUID v7; bảng/cột snake_case; quy ước đầy đủ tại `docs/conventions.md`.
- Mọi service MUST có health endpoint để Compose/gateway/monitoring kiểm tra.
- `docker compose up -d` trên máy sạch (sau khi copy `.env.example`) MUST dựng đủ hạ tầng local.

## Quy trình phát triển

- **Bản đồ feature:** `specs/README.md` theo dõi mọi feature; mỗi feature MUST có mã task sprint
  (`S#-ROLE-#`) mà nó bao phủ, một owner theo role (FSD / AIE / DE) và công cụ planning.
- **Spec Kit** (`/speckit-specify` → (`/speckit-clarify`) → `/speckit-plan` → `/speckit-tasks` →
  (`/speckit-analyze`) → `/speckit-implement`, tài liệu tại `specs/NNN-slug/`): MUST dùng cho feature
  của DE. Feature khác: owner chọn Spec Kit hoặc workflow `plans/`
  (`.claude/rules/primary-workflow.md`); MUST NOT dùng cả hai cho cùng một feature.
- Dù dùng công cụ nào, plan MUST có mục kiểm tra tuân thủ constitution (tương đương
  "Constitution Check" của Spec Kit).
- Plan MUST link tới `docs/architecture/*` (data-model, api-contracts, ai-integration,
  data-pipeline) thay vì chép lại; chỉ ghi phần mới hoặc phần thay đổi.
- Thay đổi kiến trúc (thêm/bỏ service, đổi transport, đổi DB ownership) MUST có ADR mới trong
  `docs/architecture/adr/`.
- Branch theo `docs/conventions.md`: `feat/{service}/{mo-ta}`, `fix/...`, `chore/...`, `docs/...`.
  Thư mục spec và tên branch độc lập với nhau.
- PR: ≥ 1 reviewer, squash merge, Conventional Commits tiếng Anh, không nhắc tới AI tool.
  TODO(DEVELOP_BRANCH): tạo nhánh `develop` trên origin hoặc sửa conventions cho PR vào `main`.

## Governance

- Constitution này tóm tắt các quyết định đã chốt; ADR là nguồn chi tiết. Khi spec/plan mâu
  thuẫn với constitution, constitution thắng cho tới khi được amend.
  TODO(SRS_PRECEDENCE): nếu nhóm có SRS chính thức, xác định thứ tự ưu tiên SRS ↔ constitution.
- Amendment: PR sửa file này + (nếu là kiến trúc) ADR tương ứng; cần đồng ý của ít nhất 2/3 thành
  viên, trong đó có owner của workstream bị ảnh hưởng.
- Versioning (semver): MAJOR = bỏ/định nghĩa lại principle; MINOR = thêm principle/section hoặc
  mở rộng đáng kể; PATCH = làm rõ câu chữ.
- Compliance: mục "Constitution Check" trong mỗi `plan.md` là gate trước khi viết tasks; reviewer
  kiểm tra Quality Gates (VI) trên mọi PR. Vi phạm có chủ đích MUST ghi vào "Complexity Tracking"
  của plan kèm lý do.

**Status**: Proposed — chờ team duyệt qua PR

**Version**: 1.0.0 | **Ratified**: TODO(RATIFICATION_DATE): sau khi ≥ 2/3 thành viên duyệt qua PR | **Last Amended**: 2026-10-05
