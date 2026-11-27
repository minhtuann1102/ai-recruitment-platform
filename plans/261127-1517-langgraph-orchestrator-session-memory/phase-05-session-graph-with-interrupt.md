# Phase 05: Graph cả phiên có `interrupt` (pha C, stretch)

## Context Links
- [plan.md](plan.md) · doc 12 G4 · graph phase 02, store phase 03

## Overview
- Priority: P3 · Status: code xong, chờ user test (2026-11-27) · Effort: 3d
- Gate: phase 04 xong, còn ≥ 5 ngày trước 21/12/2026. Không đủ thời gian thì bỏ, pha A + B đã đủ để bảo vệ.
- API **không đổi** so với phase 04. Chỉ đổi cách endpoint gọi graph.

## Key Insights
- Một graph cho cả phiên: `plan → ask → wait_answer → perceive → evaluate → decide → act → ask … → report → END`.
  `wait_answer` chỉ có `answer = interrupt({...})` (node có interrupt chạy lại từ đầu khi resume, nên phải rỗng).
- `/start` = `ainvoke(start_input)` chạy tới interrupt đầu. `/next-turn` = `Command(resume=body)`.
  `/finalize` = `Command(resume={"end_reason": …})` → `perceive` rẽ thẳng sang `report`.
- Guard / lock / replay phase 03 giữ nguyên, chạy trước khi resume.
- Node `plan` bọc `start_session`; node `report` bọc Reporter (đọc request dựng từ state graph).

## Quyết định khi bắt đầu code (2026-11-27, nhánh `thang/langgraph-session-graph` chồng lên `thang/langgraph-slim-api`)
- **Cờ `SESSION_GRAPH=per_turn|session`**, mặc định `per_turn`. Graph mỗi lượt của phase 02 vẫn là đường mặc định và
  là fallback (Risk). Một hàm `session_graph()` trả graph theo cờ; guard, record, seed test và `/start` đều dùng hàm
  này, vì `aget_state` phải chạy trên đúng graph đã ghi thread.
- **Sơ đồ:** `START → plan → ask → record → wait_answer`. `wait_answer` rẽ `answer → perceive`, `finalize → report`.
  `perceive` / `decide` / `act` / `reask` giữ nguyên như phase 02, nhưng `record` quay về `wait_answer`, không về END.
  `report → wait_answer`: phiên luôn chờ, nên gọi finalize lần nữa vẫn chạy lại `report` (finalize gọi lại được như
  phase 04). Lệch so với "report → END" ở trên.
- **Context mỗi request:** dataclass `SessionRunContext` gồm `turn: Optional[TurnContext]`, `start_req`,
  `finalize_req`, `collector`, `interviewer`, cộng kết quả (`start_result`, `report`). Node mới gọi thẳng
  `turn_steps`. Node `record` ghi `start_values` khi run là `/start`, còn lại ghi `turn_values`.
- **`/start`:** `adelete_thread`, rồi `astream({}, ...)` chạy tới interrupt đầu. Ghi checkpoint lỗi thì stream báo
  `error` (giữ hành vi phase 04).
- **`/next-turn`:** lock, guard, build request (phase 04), rồi `astream(Command(resume={"kind": "answer"}), cfg)`.
  Giá trị resume chỉ để rẽ nhánh; dữ liệu lượt nằm trong context. Vẫn `prime()` như phase 02.
- **Stream đứt giữa `ask`:** checkpoint mới nhất có `next=('ask',)`, không còn chờ ở `wait_answer`. Trước khi resume
  thì tìm trong `aget_state_history` checkpoint gần nhất có `next == ('wait_answer',)` rồi resume từ `checkpoint_id`
  đó: chạy lại cả lượt, giống phase 03 Lệch 1. Không tìm được thì 404 với log `session_graph_mismatch` (thread ghi bằng
  graph mỗi lượt, do đổi cờ giữa phiên).
- **`/finalize`:** kiểm như phase 04 (404 / 409 / 503, `finalize_end_reason`), rồi resume `{"kind": "finalize"}`.
  Node `report` gọi Reporter với `FinalizeRequest` trong context, và trả `{"state": state done}` nếu phiên chưa done
  (thay `record_finalize_end`).
- Trước khi code: spike xem `Command(resume=...)` có dùng được trên thread có `next=('wait_answer',)` mà chưa có
  interrupt không (thread do `aupdate_state(as_node="record")` ghi, như seed test).

## Requirements
- Golden phase 01 vẫn xanh (đã chuyển sang API phase 04).
- `draw_mermaid()` hiện vòng lặp `ask → … → ask` và nhánh `report`.

## Related Code Files
- Tạo: `app/turn_graph/session_graph_builder.py`, `tests/test_session_graph_interrupt.py`
- Sửa: `app/main.py` (3 endpoint gọi session graph), `app/turn_graph/turn_graph_nodes.py` (thêm `plan`,
  `wait_answer`, `report`), docs 03 (sơ đồ mới)

## Implementation Steps
1. Node `plan`, `wait_answer`, `report`; builder có vòng lặp.
2. Endpoint chuyển sang `Command(resume=...)`; giữ cách mồi event đầu (phase 02, insight 2).
3. Test interrupt / resume, finalize giữa chừng, resume trên phiên đã xong.
4. `pytest -q`, chạy local dev-play 1 phiên.
5. Thay sơ đồ ở doc 03 + README.

## Todo List
- [x] Spike: `Command(resume=...)` trên thread seed `as_node="record"`, lùi checkpoint sau stream đứt
- [x] Cờ `SESSION_GRAPH` (`session_graph_settings.py`, kiểm lúc khởi động) + `session_graph()` (`session_graph_selector.py`)
- [x] Node plan / wait_answer / report / ask / record + 5 node bước (`session_graph_nodes.py`), `SessionRunContext`
- [x] Builder vòng lặp (`session_graph_builder.py`) + endpoint rẽ theo cờ (`session_graph_runs.py`, `session_resume_point.py`)
- [x] Test interrupt / resume / finalize giữa chừng / finalize hai lần / luồng đứt / mismatch (`tests/test_session_graph_interrupt.py`)
- [x] Golden + test lưu phiên chạy cả hai giá trị cờ (fixture `session_graph_mode`); Postgres tích hợp cả hai chế độ
- [x] Sơ đồ mới ở doc 03 (giữ sơ đồ mỗi lượt, có nhãn), `.env.example`
- [x] `evals.simulate --matrix quick` mode `session` (memory và Postgres): 10/10 phiên có report
- [ ] User chạy dev-play / thử tay 1 phiên với `SESSION_GRAPH=session`

## Kết quả (2026-11-27)
- Spike (langgraph 1.0.1): (1) thread seed `aupdate_state(as_node="record")` có `next=('wait_answer',)`, chưa có
  interrupt, `Command(resume=...)` vẫn chạy được, từ lượt sau interrupt thật nằm trong checkpoint. (2) Huỷ run giữa
  `ask` với `durability="exit"` vẫn ghi checkpoint (`next=('ask',)`, state y như trước lượt), checkpoint cha của nó có
  `next=('wait_answer',)`; resume với `checkpoint_id` đó chạy lại cả lượt và nhánh mới thành checkpoint mới nhất.
- Review (opus, `plans/reports/reviewer-261127-2330-phase05-session-graph.md`) đã sửa: C1 (điểm resume lần theo
  `parent_config` thay vì quét 8 checkpoint lịch sử, mất phiên sau ~8 lượt lỗi; thêm test 10x `voice_no_speech` và 9 lần
  ngắt stream), H1 (`record_finalize_end` trước `finalize_run`, node `report` chỉ báo cáo), M2 (snapshot từ
  `stored_snapshot` truyền sang `resume_config`), L3 (pin `rows == n + 1` và mã lỗi), L2 (bỏ cạnh `__end__` trong
  `session_graph_mermaid`). Log không-resume được đổi thành `session_not_resumable` (vẫn 404 `session_not_found`).
- Test: mặc định (có `SESSION_DB_TEST_URL`) 1552 passed, 8 skipped; cả bộ với `SESSION_GRAPH=session` 1552 passed,
  8 skipped (không có `SESSION_DB_TEST_URL` thì 1550 passed, 10 skipped). Postgres tích hợp xanh ở cả hai chế độ (`rows == n + 1` cả hai).
- `evals.simulate --matrix quick --simulator rule` (mock, `SESSION_GRAPH=session`): 10/10 phiên có report, 125 lượt
  (y hệt per_turn); lại với Postgres (`SESSION_STORE=postgres`): 10/10, 10 thread / 145 checkpoint, 145 interrupt (chạy lại
  sau khi sửa review: vẫn 10/10).
- Dung lượng Postgres, phiên 17 lượt: per_turn 562 KB (35,7 KB `checkpoints` + 526 KB blob), session 593 KB
  (+3,3 KB `checkpoint_writes` cho interrupt, `checkpoints` 63 KB): +5,5%. Số checkpoint bằng nhau (18).

## Lệch so với kế hoạch
1. `/start` trên `session`: lỗi xoá thread cũ (DB treo) trả 503 `session_store_unavailable` retryable trước khi mở
   response, không còn stream `error` sau câu hỏi đầu như phase 04 (thread phải xoá trước khi chạy vì channel
   `transcript` cộng dồn). Lỗi ghi checkpoint ở cuối run vẫn thành event `error`. Hệ quả cần biết: `/start` gửi lại mà
   Planner lỗi (422...) hoặc bị ngắt thì phiên cũ đã bị xoá (per_turn giữ thread cũ tới khi ghi xong).
2. `/finalize` trên `session` chạy Reporter bên trong graph và giữ khoá phiên suốt lúc báo cáo (per_turn nhả khoá
   trước Reporter): `/finalize` hoặc next-turn gửi lúc đó nhận 409 `turn_in_progress` (ghi ở doc 06; cần xác nhận
   interview-service retry mã này). Phiên chưa done được chốt `done` trước graph bằng `record_finalize_end` như per_turn.
3. `GraphTurnRun` nhận thêm `graph_input` / `config`; `turn_graph_builder.py` tách `route_of` /
   `mermaid_with_decide_labels`; `session_turn_guard.stored_snapshot` trả cả snapshot.
4. `scripts/export_turn_graph_mermaid.py` chưa đổi (chỉ xuất sơ đồ mỗi lượt); sơ đồ cả phiên lấy từ `session_graph_mermaid()`.
5. Checkpoint của lần chạy lỗi chưa được dọn: xem phase 06.

## Success Criteria
- Như phase 04, cộng sơ đồ hiện chu trình Perceive–Evaluate–Decide–Act thật.

## Risk Assessment
- Interrupt lưu checkpoint giữa các lượt nên đổi thời điểm ghi của phase 03: kiểm lại test stream đứt.
- Thêm việc gỡ lỗi khi resume sai node: giữ graph mỗi lượt (phase 02) làm fallback sau cờ cho tới khi xong.

## Security Considerations
- Giống phase 03.

## Next Steps
- Phase 06 đo + docs.
