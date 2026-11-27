# Phase 05: Graph cả phiên có `interrupt` (pha C, stretch)

## Context Links
- [plan.md](plan.md) · doc 12 G4 · graph phase 02, store phase 03

## Overview
- Priority: P3 · Status: pending · Effort: 3d
- Gate: phase 04 xong, còn ≥ 5 ngày trước 21/12/2026. Không đủ thời gian thì bỏ, pha A + B đã đủ để bảo vệ.
- API **không đổi** so với phase 04. Chỉ đổi cách endpoint gọi graph.

## Key Insights
- Một graph cho cả phiên: `plan → ask → wait_answer → perceive → evaluate → decide → act → ask … → report → END`.
  `wait_answer` chỉ có `answer = interrupt({...})` (node có interrupt chạy lại từ đầu khi resume, nên phải rỗng).
- `/start` = `ainvoke(start_input)` chạy tới interrupt đầu. `/next-turn` = `Command(resume=body)`.
  `/finalize` = `Command(resume={"end_reason": …})` → `perceive` rẽ thẳng sang `report`.
- Guard / lock / replay phase 03 giữ nguyên, chạy trước khi resume.
- Node `plan` bọc `start_session`; node `report` bọc Reporter (đọc request dựng từ state graph).

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
- [ ] Node plan / wait_answer / report
- [ ] Builder vòng lặp + endpoint resume
- [ ] Test interrupt / resume / finalize giữa chừng
- [ ] Chạy local + sơ đồ mới

## Success Criteria
- Như phase 04, cộng sơ đồ hiện chu trình Perceive–Evaluate–Decide–Act thật.

## Risk Assessment
- Interrupt lưu checkpoint giữa các lượt nên đổi thời điểm ghi của phase 03: kiểm lại test stream đứt.
- Thêm việc gỡ lỗi khi resume sai node: giữ graph mỗi lượt (phase 02) làm fallback sau cờ cho tới khi xong.

## Security Considerations
- Giống phase 03.

## Next Steps
- Phase 06 đo + docs.
