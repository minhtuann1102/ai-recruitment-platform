# Review phase 05: graph cả phiên có interrupt (opus, read-only, 2026-11-27)

Nhánh `thang/langgraph-session-graph` (chồng lên `thang/langgraph-slim-api`). Thiết kế gọn, file nhỏ, đường
`per_turn` không đổi. Có 1 lỗi Critical đã dựng lại được bằng probe.

## Critical
- **C1** `app/session_store/session_resume_point.py:17,20-27`: mỗi lần chạy lỗi (perceive 409/422, client ngắt giữa
  `ask` hoặc evaluate, Reporter lỗi) đều ghi thêm một checkpoint con của checkpoint `wait_answer`. Hàm tìm điểm resume
  quét lịch sử cả thread từ mới về cũ, `limit=8`. Probe: 10 lần `voice_no_speech` cho ra 422 x8, rồi 404 vĩnh viễn, log
  sai là `session_graph_mismatch`.
  Sửa: lần theo `parent_config` thay vì quét lịch sử. Thêm test 10 lần no-speech rồi trả lời đúng ra 200, và test ngắt
  stream 9 lần rồi gửi lại ra 200.

## High
- **H1** `session_graph_nodes.py:79-88`, `interview_session_routes.py:158-161`: Reporter ném lỗi trong mode session
  thì phiên không được chốt `done`, next-turn sau đó vẫn 200. Sửa: gọi `record_finalize_end` trước `finalize_run` như
  `per_turn`; node `report` chỉ viết báo cáo.

## Medium
- **M1** Lock giữ suốt lúc Reporter chạy: finalize thứ hai gửi trong lúc đó nhận 409 `turn_in_progress`. Cần ghi vào
  doc 06 và xác nhận interview-service có retry khi gặp mã này.
- **M2** Mỗi lượt / finalize đọc checkpoint 2–3 lần: truyền snapshot của `stored_values` sang `resume_config`.
- **M3** Checkpoint của các lần chạy lỗi không bao giờ được dọn: ghi là phình dữ liệu đã biết (phase 06).

## /start (lệch 1)
Chấp nhận được: trả 503 trước khi mở response. Cần ghi rõ: gửi lại `/start` mà Planner lỗi (422) thì phiên cũ đã bị xoá.

## Low
- **L1** Doc 03 và `.env.example`: đổi cờ giữa phiên chỉ gây 404 khi đổi từ `per_turn` sang `session`; lùi về
  `per_turn` thì phiên đang chạy vẫn đi tiếp.
- **L2** Sơ đồ Mermaid ở doc 03 đã bị cắt tay (thiếu cạnh `wait_answer -.-> __end__`); README chưa cập nhật.
- **L3** Assert lỏng: Postgres `rows >= n + 1` (nên là `==`), `test_session_graph_interrupt.py:148` chấp nhận cả 404 lẫn
  409 (nên chốt một mã).
- **L4** Fixture `session_graph_mode` chạy đôi cả các test không dùng tới cờ (chỉ tốn thời gian).
- **L5** Số test ghi trong file phase không khớp số chạy thật.

## Câu hỏi chưa giải quyết
- interview-service có retry `/finalize` khi nhận 409 `turn_in_progress` không?
- Thread không có checkpoint `wait_answer` (`/start` bị huỷ): nên đổi tên log thành `session_not_resumable`?
