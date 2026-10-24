# Trạng thái dự án (cập nhật 2026-10-22)

## Kế hoạch
`plans/20261019-1100-ai-interview-brd-implementation/` (9 phase, đã có trên `main`). Phase 01 **đã merge** (PR #9–#12, 2026-10-19). Phase 02 (`thang/llm-foundation`, PR #13) CI xanh, chờ review. Phase 03 **xong code đường đọc RAG** (`thang/rag-read-path`, xếp chồng trên #13, chờ review); đo recall@5 chờ DE nạp dữ liệu và duyệt golden set. Phase 05 đang làm: Evaluator LLM xong code (`thang/evaluator-llm`), golden set + công cụ đo ở `thang/evaluator-golden-set` (chờ 2 người gán nhãn). Phase 04 xong code (#17–#19). Phase 06 xong code (4 PR xếp chồng trên #19). Phase 07: harness tầng 3 xong code (`thang/simulator-harness`), chạy thử mock; còn khóa contract (FSD), spike SSE qua APISIX (DE), client NestJS, chạy đo với LLM thật.

## Nhánh và PR
| Nhánh | PR | Trạng thái |
|---|---|---|
| `thang/brd-v04-reconcile` | #9 | **Đã merge** (2026-10-19) |
| `thang/catalog-6-tracks` | #10 | **Đã merge** |
| `thang/difficulty-bounds-align` | #11 | **Đã merge** |
| `thang/context-folder` | #12 | **Đã merge** |
| `thang/llm-foundation` | #13 | Phase 02: gateway LLM, retry, structured output, prompt store, registry; 182 test |
| `thang/rag-read-path` | #14 | Phase 03: `app/rag/` đường đọc, golden set RAG bản nháp, `evals/run_rag.py`; 207 test + 5 test tích hợp |
| `thang/evaluator-llm` | #15 | Phase 05 phần 1: Evaluator LLM, hậu kiểm bằng code, prompt v1 có mẫu neo; 248 test; xếp chồng trên #14 |
| `thang/evaluator-golden-set` | #16 | Phase 05 phần 2: golden set 48 mẫu (chưa nhãn), phiếu gán nhãn, `evals/run_evaluator.py`; 253 test; xếp chồng trên #15 |
| `thang/cv-parser-llm` | #17 | Phase 04: CV Parser LLM, 10 CV mẫu; xếp chồng trên #16 |
| `thang/jd-parser` | #18 | Phase 04: `/api/jd/parse`, `jd_profile` trong start |
| `thang/planner-llm` | #19 | Phase 04: Planner LLM, validator, khung 15–20 phút, `reference_snippets`; 321 test |
| `thang/orchestrator-limits` | #20 | Phase 06: hạn cứng, ngân sách phase/topic, turn cap theo thời lượng |
| `thang/interviewer-llm` | #21 | Phase 06: Interviewer stream, fallback, `replace`, chống lặp |
| `thang/reporter-llm` | #22 | Phase 06: Reporter, `partial`, khối `requirements` |
| `thang/internal-token-auth` | #23 | Phase 06: `X-Internal-Token`; 358 test |
| `thang/simulator-harness` | #24 | Phase 07: simulator, harness tầng 3, độ trễ và chi phí; 363 test |
| `thang/question-variety` | #25 | Chống câu hỏi lặp: focus chưa hỏi, câu dự phòng đa dạng; câu lặp mock 34.2% → 0.6%; 372 test |
| `thang/llm-baseline-measurement` | #26 | Số đo đầu với LLM thật (9 phiên): TTFT P50 6.0 s, $0.0073/phiên, fallback 2.7% |
| `thang/latency-reduction` | #27 | Evaluator v2, Planner v2: P50 6.0 → 5.0 s, Planner 13 → 8.2 s, fallback 0% |

Quy ước merge của owner: merge commit (không squash). Tiêu đề PR dạng `[scope] type: mô tả`.

## Mốc
Feature freeze 06/12/2026; Sprint 5 07–21/12. Gate voice 22/11. Mốc Evaluator ±1 band ≥ 80% ở tuần 5 (09–15/11).

## Phụ thuộc đang chờ người khác
FSD: `interview-service`, TCP `getCvFile`/`getJobDescription`, giao diện. DE: DDL `ai_db` (PR #6), bộ Q&A canonical (spec 005), `resources` cho catalog, voice (feature 015). Team: ADR, ratify constitution, người gán nhãn golden set thứ hai.

## Việc đang mở
**Cần gấp cho mốc 09–15/11:** 2 người gán nhãn golden set Evaluator (khoảng 2–3 giờ mỗi người), rồi owner chạy `python -m evals.run_evaluator --runs 3`.
Chờ owner xác nhận D7–D12 (đặc biệt D8 voice, D12 thời lượng); `gh` đã đăng nhập (tài khoản `thangp97`, quyền WRITE).

Nghiên cứu thị trường và gợi ý cải thiện (2026-10-22): `plans/20261019-1100-ai-interview-brd-implementation/reports/researcher-20261022-ai-mock-interview-market.md`.

Số đo LLM thật đầu tiên (2026-10-22): `plans/20261019-1100-ai-interview-brd-implementation/reports/eval-sim-20261022-llm-quick.md`. Khóa OpenRouter ở `apps/ai-service/.env` (owner giữ, smoke test OK).

RAG bật với ai_db dùng chung (2026-10-24): recall@5 0.875, snippet thêm ~1.5 s vào start; báo cáo `plans/20261019-1100-ai-interview-brd-implementation/reports/eval-rag-20261024-shared-ai-db.md` (nhánh `thang/rag-enable-measure`). Toàn bộ PR #13–#27 đã merge.
Cải tiến RAG (nhánh `thang/rag-improvements`): bỏ textbook khi chưa có (snippet 1.5 → 0.44 s), usage embedding vào metadata, mở rộng truy vấn tiếng Việt (golden 0.958, held-out tiếng Việt 0.625).
