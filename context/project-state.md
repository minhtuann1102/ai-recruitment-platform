# Trạng thái dự án (cập nhật 2026-10-19)

## Kế hoạch
`plans/20261019-1100-ai-interview-brd-implementation/` (9 phase, nằm trong PR `thang/brd-v04-reconcile` cho tới khi merge). Phase hiện tại: **01 Đồng bộ main và chốt quyết định** (gần xong). Tiếp theo: Phase 02 `thang/llm-foundation`.

## Nhánh và PR (đã push ngày 2026-10-19)
| Nhánh | Nội dung | Phụ thuộc |
|---|---|---|
| `thang/brd-v04-reconcile` | BRD v0.5, FR/NFR/L2, kế hoạch, `check_docs.py`, bản nháp sửa constitution | — (merge trước) |
| `thang/catalog-6-tracks` | Catalog 6 track, 90 topic, category `Frontend` | xếp chồng trên nhánh trên |
| `thang/difficulty-bounds-align` | Sửa biên độ khó cho khớp design | xếp chồng trên nhánh trên |
| `thang/context-folder` | Thư mục `context/` này | độc lập |

Thứ tự merge: `brd-v04-reconcile` trước, rồi các nhánh còn lại. Số PR: ghi vào đây khi mở.

## Mốc
Feature freeze 06/12/2026; Sprint 5 07–21/12. Gate voice 22/11. Mốc Evaluator ±1 band ≥ 80% ở tuần 5 (09–15/11).

## Phụ thuộc đang chờ người khác
FSD: `interview-service`, TCP `getCvFile`/`getJobDescription`, giao diện. DE: DDL `ai_db` (PR #6), bộ Q&A canonical (spec 005), `resources` cho catalog, voice (feature 015). Team: ADR, ratify constitution, người gán nhãn golden set thứ hai.

## Việc đang mở
Chờ owner xác nhận D7–D12 (đặc biệt D8 voice, D12 thời lượng); chưa có `gh` nên PR mở bằng link.
