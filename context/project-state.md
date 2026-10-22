# Trạng thái dự án (cập nhật 2026-10-22)

## Kế hoạch
`plans/20261019-1100-ai-interview-brd-implementation/` (9 phase, đã có trên `main`). Phase 01 **đã merge** (PR #9–#12, 2026-10-19). Phase 02 (`thang/llm-foundation`, PR #13) CI xanh, chờ review. Phase 03 **xong code đường đọc RAG** (`thang/rag-read-path`, xếp chồng trên #13, chờ review); đo recall@5 chờ DE nạp dữ liệu và duyệt golden set. Phase 05 đang làm: Evaluator LLM xong code (`thang/evaluator-llm`), golden set + công cụ đo ở `thang/evaluator-golden-set` (chờ 2 người gán nhãn). Sau đó Phase 04 Planner.

## Nhánh và PR
| Nhánh | PR | Trạng thái |
|---|---|---|
| `thang/brd-v04-reconcile` | #9 | **Đã merge** (2026-10-19) |
| `thang/catalog-6-tracks` | #10 | **Đã merge** |
| `thang/difficulty-bounds-align` | #11 | **Đã merge** |
| `thang/context-folder` | #12 | **Đã merge** |
| `thang/llm-foundation` | #13 | Phase 02: gateway LLM, retry, structured output, prompt store, registry; 182 test |
| `thang/rag-read-path` | #14 | Phase 03: `app/rag/` đường đọc, golden set RAG bản nháp, `evals/run_rag.py`; 207 test + 5 test tích hợp |
| `thang/evaluator-llm` | (mới) | Phase 05 phần 1: Evaluator LLM, hậu kiểm bằng code, prompt v1 có mẫu neo; 248 test; xếp chồng trên #14 |

Quy ước merge của owner: merge commit (không squash). Tiêu đề PR dạng `[scope] type: mô tả`.

## Mốc
Feature freeze 06/12/2026; Sprint 5 07–21/12. Gate voice 22/11. Mốc Evaluator ±1 band ≥ 80% ở tuần 5 (09–15/11).

## Phụ thuộc đang chờ người khác
FSD: `interview-service`, TCP `getCvFile`/`getJobDescription`, giao diện. DE: DDL `ai_db` (PR #6), bộ Q&A canonical (spec 005), `resources` cho catalog, voice (feature 015). Team: ADR, ratify constitution, người gán nhãn golden set thứ hai.

## Việc đang mở
Chờ owner xác nhận D7–D12 (đặc biệt D8 voice, D12 thời lượng); `gh` đã đăng nhập (tài khoản `thangp97`, quyền WRITE).

Nghiên cứu thị trường và gợi ý cải thiện (2026-10-22): `plans/20261019-1100-ai-interview-brd-implementation/reports/researcher-20261022-ai-mock-interview-market.md`.
