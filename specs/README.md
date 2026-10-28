# Feature Map

Bản đồ theo dõi **mọi** feature của dự án. Luật chung: [`.specify/memory/constitution.md`](../.specify/memory/constitution.md)
(trạng thái Proposed, chờ team duyệt). Nguồn task: [`docs/sprint-plan.md`](../docs/sprint-plan.md).

**Mô hình Hybrid:** Spec Kit MUST dùng cho feature của DE. Feature khác, owner chọn Spec Kit (`specs/NNN-slug/`)
hoặc workflow `plans/` (`.claude/rules/primary-workflow.md`), không dùng cả hai cho cùng một feature. Dù dùng công
cụ nào, plan phải kiểm tra tuân thủ constitution.

Mọi task `Bắt buộc`/`Stretch` S0–S4 đều nằm trong đúng một feature. Sprint 5 (S5-*: integration test, bug fix,
báo cáo, slides) là việc chung của team, không cần spec.

| # | Feature | Sprint | Owner | Công cụ | Task sprint | Phụ thuộc | Trạng thái |
|---|---|---|---|---|---|---|---|
| 001 | [platform-foundation](001-platform-foundation/spec.md) | S0 | DE | Spec Kit | S0-DE-1..6 | — | Đang làm — PR-1 #2 merged; PR-2 #6 (T016–T026); CI #5 (T031–T032); route job/interview hoãn chờ FSD scaffold |
| 002 | backend-foundation | S0 | FSD (đề xuất) | Owner chọn | S0-FSD-1..6 | 001 (multi-DB) | Chưa viết |
| 003 | ai-service-foundation | S0 | AIE (đề xuất) | Owner chọn | S0-AIE-1..4 | 001 (ai_db) | Đang làm tại `origin/feat/aie` |
| 004 | auth-and-user-profiles | S1 | FSD (đề xuất) | Owner chọn | S1-FSD-1..7 | 002 | Chưa viết |
| 005 | [rag-knowledge-base-qa](005-rag-knowledge-base-qa/spec.md) | S1 | AIE + DE | Spec Kit | S1-AIE-1..2, S1-DE-1..4 | 001, 003 | Merged (2026-10-23) — PR #31, #28, #29; ai_db dùng chung Supabase (#32); golden set + eval chuyển AIE; còn T041, T047, T049, T053 |
| 006 | ai-interview-agents | S1–S2 | AIE (đề xuất) | Owner chọn | S1-AIE-3..4, S2-AIE-1..6 | 003, 005 | Kế hoạch: [plan](../plans/20261019-1100-ai-interview-brd-implementation/plan.md) (workflow `plans/`) |
| 007 | job-posting-search | S2 | FSD (đề xuất) | Owner chọn | S2-FSD-1..4, S2-FSD-9..10 | 004 | Chưa viết |
| 008 | job-applications | S2 | FSD (đề xuất) | Owner chọn | S2-FSD-5..8, S2-FSD-11 | 007, 001 (MinIO) | Chưa viết |
| 009 | [jd-crawling-seeding](009-jd-crawling-seeding/spec.md) | S2 | DE | Spec Kit | S2-DE-1..4 | 005 (pipeline), 004 + 007 (migration) | US1 crawl merged (#45), US2 process merged (#47, 341 JD); US5 synthetic: code xong, chờ chạy thật (key LLM hết số dư); seed (US4) chờ migration `company_profiles` (004) + job-service (007) |
| 010 | interview-sessions | S3 | FSD (đề xuất) | Owner chọn | S3-FSD-1..8 | 006, 002 | Chưa viết |
| 011 | agentic-interview-hardening | S3–S4 | AIE (đề xuất) | Owner chọn | S3-AIE-1..6, S4-AIE-1..5 | 006, 010 | Kế hoạch: [plan](../plans/20261019-1100-ai-interview-brd-implementation/plan.md) (workflow `plans/`) |
| 012 | textbook-ingestion-rag-quality | S3–S4 | DE | Spec Kit | S3-DE-1..5, S4-DE-1 | 009 (pipeline ổn định), 011 (S3-AIE-1 cho eval) | Chưa viết |
| 013 | web-frontend | S4 | FSD (đề xuất) | Owner chọn | S4-FSD-1..9 | 004, 007, 008, 010 | Chưa viết |
| 014 | staging-deploy-monitoring | S4 | DE | Spec Kit | S4-DE-2..4 | 001, mọi service chạy được | Chưa viết |
| 015 | voice-mode | S4 | DE | Spec Kit | S4-DE-5 | 006, 010, 013 | Chưa viết (Stretch; cần tài khoản STT/TTS) |
| 016 | [interview-learning-roadmap](016-interview-learning-roadmap/spec.md) | S3 | DE (AIE review) | Spec Kit | S3-DE-6, phần `study_plan` của S3-AIE-1 | 005, 011 (Reporter, finalize), 012 (tùy chọn) | Draft spec (2026-10-21) — ranh giới AIE + FSD chốt 2026-10-24 (chỉ `study_plan`); còn FR-020, FR-024 |

Owner "(đề xuất)" được bỏ chữ đề xuất khi người đó xác nhận trong PR review. Feature 005 dùng Spec Kit vì DE đồng
sở hữu; AIE review spec.

## Quy trình

1. Viết tài liệu **just-in-time**: đầu mỗi sprint, owner viết spec/plan cho feature của sprint đó.
2. Feature dùng Spec Kit: giữ đúng số trong bảng bằng cách chỉ định thư mục khi gọi `/speckit-specify`, ví dụ
   `SPECIFY_FEATURE_DIRECTORY=specs/005-rag-knowledge-base-qa` (nếu không, script tự đánh số tiếp theo).
   Thứ tự: `/speckit-clarify` (tùy chọn) → `/speckit-plan` → `/speckit-tasks` → `/speckit-analyze` (tùy chọn) →
   `/speckit-implement`.
3. Feature dùng workflow `plans/`: cột Trạng thái link tới thư mục plan trong `plans/`.
4. Plan link tới `docs/architecture/*`, không chép lại data model / API contract.
5. Cập nhật cột Trạng thái khi tài liệu xong hoặc feature merged.
