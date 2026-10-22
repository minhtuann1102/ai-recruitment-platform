---
title: Triển khai phần AIE theo BRD v0.3
status: pending
priority: P1
created: 2026-10-19
owner: AIE
branch: tách từ main theo phase, dạng feat/ai-service/<mô-tả> (nhánh feat/aie hiện tại chỉ còn 4 commit tài liệu chưa vào main)
---

# Kế hoạch triển khai phần AIE theo BRD v0.3

**Mục tiêu:** đưa phỏng vấn kỹ thuật AI từ mock sang agent thật, đo được chất lượng, kịp feature freeze **06/12/2026**.
**Nguồn:** [BRD v0.3](../../docs/ai-service/requirements/01-brd.md) · [FR](../../docs/ai-service/requirements/02-functional-requirements.md) · [NFR](../../docs/ai-service/requirements/03-non-functional-requirements.md) · [L2](../../docs/ai-service/11-architecture-l2-containers.md) · [sprint plan](../../docs/sprint-plan.md) · [feature map](../../specs/README.md) (đây là plan của feature 006 và 011, workflow `plans/`).

## Hiện trạng (19/10)

- **Đã có trên `main`:** mock ai-service đủ contract (cv/parse, start, next-turn SSE, finalize), trích CV + redact, catalog 6 track (nhánh `thang/catalog-6-tracks`), 132 test, CI Python 3.11, đổi tên `ai_recruit_*`. DE đã viết DDL `knowledge_chunks` (nhánh `chore/docker-multi-db-minio`).
- **Chưa có:** mọi agent LLM, RAG đường đọc, golden set, simulator, `interview-service`, `job-service`, `apps/web`.
- **Lệch BRD, đã nằm trên `main` từ 15/10 (xem Quyết định cần chốt):** voice, JD, 6 track, DE sở hữu đường ghi RAG.

## Quyết định cần chốt (chặn Phase 01)

| # | Vấn đề | BRD v0.3 | `main` (team, 15/10) | Mặc định của kế hoạch |
|---|---|---|---|---|
| Q1 | Voice | Hội thoại realtime qua voice-gateway | Stretch S4, DE sở hữu: TTS đọc `done.question`, STT bấm-để-nói gửi qua `/answer`; realtime ngoài phạm vi | **Theo `main`** (tùy chọn A); realtime (B) chỉ khi bạn xác nhận, cần ADR-009 |
| Q2 | JD | Ngoài phạm vi AI | JD là input của Planner (S2-AIE-6, S3-AIE-6), AIE đã đồng ý | **Theo `main`**, cập nhật BRD v0.4 |
| Q3 | Thời lượng | 15–20 phút | Docs vẫn 30 phút | **15–20**, mặc định 20, turn cap 16 (đề xuất, cần team duyệt) |
| Q4 | Track | 4 | DE đề xuất 6 track, 90 topic, thêm category `Frontend` | **Nhận đề xuất DE** |
| Q5 | Framework, fine-tune | Cho phép | Docs ghi không dùng | Không dùng framework cho chat; học từ dữ liệu hoãn |
| Q6 | A-6 video tự xem, không gửi đi | Cần xác nhận | Chưa nói | **Đã xác nhận (owner, 19/10)** |

## Phases

| # | Phase | Tuần | Trạng thái | Task | FR / NFR chính |
|---|---|---|---|---|---|
| 01 | [Đồng bộ main, chốt quyết định](phase-01-sync-and-decisions.md) | W2 | **Gần xong**: 2 nhánh tài liệu + catalog xong, còn nhánh sửa biên độ khó; chờ owner xác nhận Q1–Q6 và quyền push | — | — |
| 02 | [Nền tảng LLM](phase-02-llm-foundation.md) | W2–W3 | **Xong code, chờ review PR** (nhánh `thang/llm-foundation`); smoke test thật do owner chạy | S1-AIE-4 | FR-063, 070, 080, 081 |
| 03 | [RAG đường đọc](phase-03-rag-read-path.md) | W2–W4 | **Xong code đường đọc, chờ review PR** (nhánh `thang/rag-read-path`, xếp chồng trên Phase 02); recall@5 chưa đo (chờ dữ liệu DE + duyệt nhãn) | S1-AIE-2 | FR-022, 060, 061 · QUAL14 |
| 04 | [CV, JD, Planner](phase-04-cv-jd-planner.md) | W3–W4 | **Xong code, chờ review** (3 PR: CV Parser, JD Parser, Planner LLM + RAG snippet); chưa chạy LLM thật | S1-AIE-3, S2-AIE-1, 3, 6 | FR-003, 013, 016, 017, 020–023 |
| 05 | [Evaluator và golden set](phase-05-evaluator-golden-set.md) | W3–W5 | **Đang làm**: Evaluator LLM + hậu kiểm xong code (`thang/evaluator-llm`); golden set + công cụ đo (`thang/evaluator-golden-set`); chưa đo | S1-AIE-3, S3-AIE-4 | FR-030–032 · QUAL01–08 |
| 06 | [Interviewer, Reporter, orchestrator](phase-06-interviewer-reporter-orchestrator.md) | W4–W6 | **Xong code, chờ review** (4 PR: giới hạn thời gian, Interviewer stream, Reporter + `requirements`, token nội bộ); chưa chạy LLM thật | S2-AIE-2, 4, S3-AIE-1, 2, 3, 6 | FR-035–039, 052–056, 070–072, 091 |
| 07 | [Tích hợp và đo](phase-07-integration-and-measurement.md) | W4–W7 | Chưa bắt đầu | S2-AIE-5, S3-AIE-5, S4-AIE-4, 5 | FR-082, 083, 090 · PERF, COST |
| 08 | [Voice và học từ dữ liệu (có điều kiện)](phase-08-voice-and-learning.md) | W7+ | Chưa bắt đầu | S4-DE-5 (DE) | FR-120–133 · gate 22/11 |
| 09 | [Hoàn thiện và báo cáo](phase-09-polish-and-report.md) | W8–S5 | Chưa bắt đầu | S4-AIE-1–3, S5-3, 5, 6, 8 | tất cả NFR |

## Timeline

W2 19–25/10 · W3 26/10–01/11 · W4 02–08/11 (**khóa contract**) · W5 09–15/11 (**Evaluator ±1 band ≥ 80%**) · W6 16–22/11 (**gate voice 22/11**) · W7 23–29/11 · W8 30/11–06/12 (**freeze 06/12**) · Sprint 5 07–21/12.

## Phụ thuộc bên ngoài

- **DE:** DDL `ai_db` (PR #6), đường ghi RAG và bộ Q&A canonical có `topic_id` (spec 005), `resources` cho catalog, voice (feature 015).
- **FSD:** `interview-service` (chưa có), TCP `application.getCvFile` và `application.getJobDescription` (S2-FSD-11), giao diện (S4-FSD-8). **Kế hoạch không chờ FSD:** harness và simulator gọi thẳng ai-service.
- **Team:** ADR/constitution, 1 người gán nhãn golden set, khóa OpenRouter (Thắng giữ).

## Mốc cắt giảm (sprint plan, thêm cho AIE)

Cắt từ trên xuống: voice → JD (S2-AIE-6, S3-AIE-6) → Redis cache → category-specific RAG → RAG grounding. **Không cắt:** Evaluator mỗi lượt, policy, tính điểm bằng code, quality gates.

## Quy tắc làm việc (bắt buộc, từ 19/10)

1. **Mỗi phase có Bàn giao và Cách test** (mục tương ứng trong từng file phase); PR ghi lại kết quả test.
2. **Mọi thay đổi phải đồng bộ BRD, FR, NFR, L2 và tài liệu thiết kế trong cùng PR**, rồi chạy `check_docs.py`.
3. **Mỗi tính năng một nhánh `thang/<tính-năng>`** (username/feature), tách từ `main`; nhánh phụ thuộc thì xếp chồng và ghi rõ. Một nhánh một PR.
4. **Xong một việc thì commit, push và mở PR vào `main`** (owner cho phép thường trực từ 19/10). Ngoài ra không push thẳng vào `main`. Ghi chú quy trình lưu ở thư mục `context/`.

## Definition of Done (mọi phase)

Code chạy, `pytest` xanh trên Python 3.11 (CI), file < 200 dòng, không secret, docs cập nhật cùng PR, review trước khi merge, PR nhỏ theo phase.
