# Phase 02: Graph mỗi lượt, Interviewer trong graph (pha A)

## Context Links
- [plan.md](plan.md) · doc 12 mục 3, G1, G5, G6, G7 · [doc 03](../../docs/ai-service/03-orchestrator-state-machine.md)
- Code: `app/turn_engine.py` (`next_turn`, `_reask`, `finish_turn`), `app/turn_decision.py`, `app/main.py`
  (`_stream`, `next_turn_route`), `app/question_stream.py`

## Overview
- Priority: P1 · Status: **code xong + đã review 2026-11-27, chờ user test** · Effort: 3,5d
- Gate: team đồng ý đảo README A4. API, payload, event SSE **không đổi**. Không có checkpointer.

## Key Insights
1. Node gọi hàm đang có. Thân `next_turn()` (khoảng 75 dòng) tách thành 4 hàm thuần trên một `TurnContext`, để
   `next_turn()` cũ gọi tuần tự (cho test gọi hàm trực tiếp, khoảng 25 file test) và graph gọi từng node.
2. **Lỗi 4xx phải là HTTP status thật.** Hiện tại `next_turn()` chạy xong *trước* khi tạo `StreamingResponse`,
   nên 409 / 422 trả JSON đúng mã. Nếu graph chạy trong generator SSE thì header đã gửi đi rồi mới tới lỗi.
   → Endpoint mở `graph.astream(...)` rồi `await anext()` lấy event đầu (`meta`, phát ở đầu node `ask`) **trước**
   khi trả response. `ApiError` từ `perceive` nổ ở bước này, nên vẫn ra 4xx như cũ.
3. `finish_turn` chạy ở cuối node `ask`. Event `done` dựng từ state cuối của graph.
4. Cạnh có điều kiện theo `dec.action` (G5) chỉ để sơ đồ đúng. Mọi nhánh đều về `act` → `ask`, trừ `end`.

## Requirements
- Node: `perceive` → (`reask` | `evaluate`) → `decide` → (`end` | `act`) → `ask` → END; `wrap_up` / forced end đi
  thẳng END không qua `ask`.
- State graph: `TypedDict` với key riêng `request`, `plan`, `state`, `turn` (ngữ cảnh tạm của lượt), `result` (G6).
- Mỗi lượt cho ra cùng action / state / TurnInfo / QuestionSpec / chuỗi event SSE như golden ở phase 01.
- `/start` giữ `start_session` + `_stream` như cũ (node `plan` để sang pha C).
- Xuất sơ đồ: `scripts/export_turn_graph_mermaid.py` → `docs/ai-service/03` (khối mermaid).

## Architecture
```
perceive ──reask──► reask_turn ─┐
   │ (409 / 422 raise)          │
   ▼                            ▼
evaluate ─► decide ─end──► END  ask (Interviewer stream + finish_turn) ─► END
              │ follow_up | hint | clarify | next_topic | next_phase | wrap_up
              ▼
             act ─────────────────────────────────────────► ask
```
Endpoint: `graph.astream(input, stream_mode=["custom", "values"])`: `custom` → event SSE, `values` cuối → `done`.

## Related Code Files
- Tạo: `app/turn_graph/turn_graph_state.py` (TypedDict + `TurnContext`), `app/turn_graph/turn_graph_nodes.py`
  (4 node + `reask`, gọi hàm cũ), `app/turn_graph/turn_graph_builder.py` (`build_turn_graph()`, cạnh, compile),
  `app/turn_graph/turn_graph_stream.py` (node `ask`: bọc `QuestionStream`, `get_stream_writer`),
  `scripts/export_turn_graph_mermaid.py`, `tests/test_turn_graph_equivalence.py`, `tests/test_turn_graph_errors.py`
- Sửa: `app/turn_engine.py` (tách thân `next_turn` thành `perceive_step` / `evaluate_step` / `decide_step` /
  `act_step`, `next_turn()` gọi tuần tự; mỗi file vẫn < 200 dòng), `app/main.py` (`next_turn_route` dùng graph + mồi
  event đầu; `_stream` tách phần phát event dùng chung)
- Docs: README A4, `docs/ai-service/03` (sơ đồ graph), `context/*` nếu có nhắc "không framework"

## Implementation Steps
1. Tách thân `next_turn()` thành 4 hàm trên `TurnContext`. Chạy golden phase 01 qua `next_turn()` + HTTP: phải xanh.
2. Viết node bọc 4 hàm + `reask`, builder, cạnh điều kiện. Graph compile 1 lần lúc import (không checkpointer).
3. Node `ask`: phát `meta`, chạy `QuestionStream.events()` qua `get_stream_writer()`, gọi `finish_turn`.
   Giữ nguyên metric TTFT / `observe_ttft` / tracing Langfuse.
4. `next_turn_route`: mồi event đầu (insight 2), rồi `_TurnStream` phát tiếp. Ngắt client → đóng `astream` (như
   `aclosing` hiện tại).
5. Test tương đương: chạy golden qua graph, so từng lượt + chuỗi event. Test lỗi: 409 / 422 vẫn đúng mã HTTP.
6. Toàn bộ `pytest -q`, `check_docs.py`. Chạy local `docker compose up` (mock), chơi 1 phiên dev-play tới report.
7. Xuất Mermaid, sửa doc 03 + README A4.

## Todo List
- [x] Tách `next_turn()` thành 4 bước, golden xanh
- [x] Node + builder + cạnh điều kiện
- [x] Node `ask` stream qua writer, giữ metric / tracing
- [x] Endpoint mồi event đầu, giữ mã 4xx
- [x] Test tương đương + test lỗi
- [x] Chạy local dev-play 1 phiên
- [x] Sơ đồ Mermaid + docs (doc 03 §4.5, doc 11). **README A4 chưa sửa**: doc 12 cấm sửa trước khi team duyệt

## Kết quả (2026-11-27)
- Code: `app/turn_result.py` (TurnResult, finish_turn, flat_topics), `app/turn_steps.py` (TurnContext + 4 bước +
  reask), `app/turn_engine.py` (start_session, `turn_context`, next_turn tuần tự, 71 dòng),
  `app/question_stream.py` (`turn_question_events` dùng chung /start và node `ask`),
  `app/turn_graph/{turn_graph_nodes,turn_graph_builder,turn_graph_runner}.py`, `app/main.py` (`_stream` nhận
  nguồn event; `/next-turn` qua `GraphTurnRun`; `_TurnStream` có `cleanup`), `scripts/export_turn_graph_mermaid.py`.
- State graph pha A chỉ có `ctx` (TurnContext) + `route`. Tách key `plan` / `state` để lưu (G6) dời sang phase 03,
  vì chỉ có nghĩa khi có checkpointer.
- `draw_mermaid()` gộp các cạnh cùng đích `decide → act` thành một nhãn: `turn_graph_mermaid()` ghi lại đủ 6 hành động.
- Test: 8 golden (qua graph, không ghi lại fixture), `tests/test_turn_graph.py` (thứ tự node 4 nhánh, ApiError không
  bị bọc, Mermaid, client ngắt giữa câu hỏi thì Interviewer bị đóng, `status=cancelled`). Toàn bộ: 1432 passed, 8 skipped.
  Một test đổi chỗ patch (`forced_transition` giờ ở `turn_steps`), không đổi assert.
- Chạy local (uvicorn mock, cổng 8010): `evals.simulate --matrix quick` qua HTTP OK. Cùng môi trường in-process,
  code cũ (stash) và graph cho 10 phiên / 125 lượt / báo cáo giống hệt (bỏ timing). dev-play: start → clarify →
  hint → kết thúc → báo cáo, log mọi request `status=ok`, có `session_id` / `turn_number`.
- Overhead (mock, in-process, 300 lượt): tuần tự 0,6 ms P50, graph 3,0–3,5 ms P50 / 4,5–6,9 ms P95.
- Review (opus): [reviewer-261127-1600-langgraph-phase02.md](../reports/reviewer-261127-1600-langgraph-phase02.md).
  Đã sửa M1 (client ngắt thì Interviewer vẫn chạy nền: graph chạy trong pump task, `aclose` huỷ), M2 (test ngắt
  dương tính giả), m1 (route `session_end`), m2 (Evaluator / Interviewer gọi lazy), m3 (test SSE `error`), m4–m5.
  Sau sửa: 1439 passed; mô phỏng in-process vẫn giống hệt code cũ.

## Success Criteria
- Golden phase 01 giống hệt qua graph (mọi nhánh). Toàn bộ test cũ xanh, không sửa assert.
- 409 / 422 trả đúng mã. Ngắt client giữa stream không treo task, không lỗi log.
- `draw_mermaid()` ra sơ đồ có đủ nhánh của doc 03.

## Risk Assessment
- Overhead của LangGraph trên đường TTFT: đo ở phase 06; nếu > 50 ms P50 thì xem lại `stream_mode`.
- Context var (tracing, `bind_request`) không đi qua task của LangGraph: kiểm log có `session_id` / `turn_number`.
- `astream` bị huỷ khi client ngắt có thể ném `CancelledError` từ trong node: giữ `CancelScope(shield=True)` như `_TurnStream`.

## Security Considerations
- Không đổi guard: `safe_focus`, injection check, PII trong `action_reason` vẫn ở đúng hàm cũ.

## Next Steps
- Phase 03 thêm checkpointer vào chính graph này.
