---
title: "ai-service: LangGraph điều phối lượt phỏng vấn + memory phiên trong ai-service"
description: "Bọc vòng Perceive–Evaluate–Decide–Act bằng LangGraph (không viết lại logic), rồi lưu phiên bằng checkpointer Postgres và rút gọn API"
status: pending-team-approval
priority: P1
effort: 12.5d
branch: thang/langgraph-orchestrator
tags: [ai-service, langgraph, orchestrator, memory, api]
created: 2026-11-27
---

# Plan: LangGraph orchestrator + memory phiên

Nguồn: [docs/ai-service/12](../../docs/ai-service/12-langgraph-wrapper-and-session-memory-proposal.md) (đề xuất DE,
mục 11 là góp ý AIE G1–G11). Không chép lại nội dung doc 12, chỉ trỏ tới.

**Mục tiêu:** trả lời được câu "LangGraph ở đâu" và "agent memory ở đâu" khi bảo vệ, mà **logic, prompt, model
không đổi** (không chạy lại eval chất lượng). Không dùng LangChain Agents (doc 12 mục 11).

## Phase

| # | Phase | Pha | Effort | Gate trước khi làm | Status |
|---|---|---|---|---|---|
| 01 | [Golden trace + cài dependency](phase-01-golden-trace-and-dependency.md) | A | 0,5d | không | done 2026-11-27 |
| 02 | [Graph mỗi lượt, Interviewer trong graph](phase-02-per-turn-graph-wrapper.md) | A | 3,5d | team đồng ý đảo README A4 | code xong, chờ user test; README A4 chờ duyệt |
| 03 | [Lưu phiên: checkpointer, khoá, idempotency](phase-03-session-store-checkpointer.md) | B | 2,5d | team duyệt đảo ADR-004 / constitution IV; DE chốt DB (G9) | code xong (chạy song song, mặc định memory), chờ user test |
| 04 | [API rút gọn + sửa bên gọi](phase-04-slim-api-and-callers.md) | B | 2,5d | 03 | code xong, PR mở 2026-11-27 (voice chưa chạy) |
| 05 | [Graph cả phiên có `interrupt` (stretch)](phase-05-session-graph-with-interrupt.md) | C | 3d | 04 xong, còn ≥ 5 ngày trước 21/12 | code xong sau cờ `SESSION_GRAPH=session` (mặc định per_turn), PR mở 2026-11-27 |
| 06 | [Đo độ trễ + cập nhật docs](phase-06-latency-and-docs.md) | – | 0,5d | sau mỗi pha | pending |

```
01 ──► 02 (pha A, tự đứng được) ──► 03 ──► 04 (pha B) ──► 05 (pha C, stretch)
                 └──────────── 06 chạy sau 02, sau 04, sau 05 ────────────┘
DE: chọn DB + kiểm pooler ──► 03     FSD: nối contract mới ◄── 04
```
Dừng sau pha A vẫn có giá trị riêng: graph + sơ đồ Mermaid, API không đổi, FSD không phải làm gì.

## Quyết định đã chốt (AIE, 2026-11-27)
- Graph **bọc** hàm đang có; thân `next_turn()` chuyển thành node, không viết lại luật / prompt.
- Interviewer là node `ask` trong graph (G1). Lỗi 4xx vẫn phải là HTTP status thật (phase 02, insight 2).
- `AsyncPostgresSaver` (G2), advisory lock (G3), kiểm 404 / 409 trước graph (G7), state tách key (G6).
- Model request nội bộ (`NextTurnRequest`, `FinalizeRequest`) **giữ nguyên**. Pha B chỉ thêm lớp dựng chúng
  từ checkpoint, nên Reporter, `turn_engine` và test gọi hàm trực tiếp không đổi.

## Quy trình mỗi phase
Nhánh `thang/langgraph-orchestrator` (pha B/C có thể tách nhánh con). Sửa docs cùng nhánh. Chạy
`python -m pytest -q` và `python3 scripts/check_docs.py` trong `apps/ai-service`. Chạy thật ở local (mock, rồi một
phiên dev-play) trước khi báo xong. **Không commit / push / MR** khi user chưa test và chưa bảo.
Không gọi LLM thật, trừ bước đo độ trễ ở phase 06 (hỏi user trước).

## Câu hỏi mở
1. Team có đồng ý đảo README A4 để làm pha A trước khi chốt ADR-004 không (doc 12, câu hỏi 8)?
2. ~~`durability="exit"` có ghi checkpoint khi run bị huỷ giữa `ask` không?~~ **Có** (spike phase 01): ghi state
   sau `act`, `next=('ask',)`. Phase 03: chỉ node `record` ghi key lâu dài nên checkpoint giữ state trước lượt,
   gửi lại thì chạy lại cả lượt (không resume, xem phase 03 "Lệch 1").
3. DE: DB checkpoint là Supabase `ai_db` hay Postgres trên VM? Pooler nào?
4. `/start` có còn trả `plan` / `state` không (doc 12, câu hỏi 4)? Plan giả định là **còn**, cho dev-play.
