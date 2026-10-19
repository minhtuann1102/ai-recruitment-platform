# Trạng thái dự án (cập nhật 2026-10-19)

## Kế hoạch
`plans/20261019-1100-ai-interview-brd-implementation/` (9 phase, đã có trên `main`). Phase 01 **đã merge** (PR #9–#12, 2026-10-19). Phase hiện tại: **02 Nền tảng LLM** (nhánh `thang/llm-foundation`, PR #13 đang chờ review và CI). Tiếp theo: Phase 03 `thang/rag-read-path`.

## Nhánh và PR
| Nhánh | PR | Trạng thái |
|---|---|---|
| `thang/brd-v04-reconcile` | #9 | **Đã merge** (2026-10-19) |
| `thang/catalog-6-tracks` | #10 | **Đã merge** |
| `thang/difficulty-bounds-align` | #11 | **Đã merge** |
| `thang/context-folder` | #12 | **Đã merge** |
| `thang/llm-foundation` | #13 | Phase 02: gateway LLM, retry, structured output, prompt store, registry; 182 test |

Quy ước merge của owner: merge commit (không squash). Tiêu đề PR dạng `[scope] type: mô tả`.

## Mốc
Feature freeze 06/12/2026; Sprint 5 07–21/12. Gate voice 22/11. Mốc Evaluator ±1 band ≥ 80% ở tuần 5 (09–15/11).

## Phụ thuộc đang chờ người khác
FSD: `interview-service`, TCP `getCvFile`/`getJobDescription`, giao diện. DE: DDL `ai_db` (PR #6), bộ Q&A canonical (spec 005), `resources` cho catalog, voice (feature 015). Team: ADR, ratify constitution, người gán nhãn golden set thứ hai.

## Việc đang mở
Chờ owner xác nhận D7–D12 (đặc biệt D8 voice, D12 thời lượng); `gh` đã đăng nhập (tài khoản `thangp97`, quyền WRITE).
