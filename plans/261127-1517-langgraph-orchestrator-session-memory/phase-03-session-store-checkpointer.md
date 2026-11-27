# Phase 03: Lưu phiên: checkpointer, khoá, idempotency (pha B)

## Context Links
- [plan.md](plan.md) · doc 12 mục 4, G1, G2, G3, G6, G7, G9
- Code: graph phase 02, `app/rag/settings.py` (mẫu đọc env DB), `app/main.py` (`lifespan`)

## Overview
- Priority: P1 · Status: code xong 2026-11-27 (nhánh `thang/langgraph-session-store`), chờ user test · Effort: 2,5d
- Gate: team duyệt đảo ADR-004 / constitution IV; DE chốt DB + pooler. API **chưa** đổi ở phase này: request cũ
  vẫn gửi đủ, ai-service bắt đầu ghi và dùng checkpoint song song, để kiểm trước khi bỏ trường ở phase 04.

## Key Insights
- `thread_id = session_id`. State lưu: `start_input`, `plan`, `state`, `transcript` (append, `Annotated[list, add]`).
  Key tạm của lượt (`turn`, `result`) **không** lưu: xoá trước khi kết thúc run, hoặc dùng `output_schema`.
- Thời điểm ghi (spike phase 01): với `durability="exit"`, run bị huỷ giữa `ask` **vẫn ghi** state sau `act`, kèm
  `next=('ask',)`. Dùng `exit` và xử lý checkpoint dở dang ở guard. Gặp checkpoint có `next == ('ask',)`:
  request gửi lại cùng `turn_number` + cùng `answer` thì **resume** (`astream(None, cfg)`), chỉ chạy lại Interviewer,
  không chấm lại (rẻ hơn hành vi cũ). Khác `answer` thì **lùi** về checkpoint cha (`aget_state_history`, `checkpoint_id`
  của run trước) rồi chạy lại cả lượt. Phương án dự phòng nếu resume rối: graph không checkpointer, endpoint gọi
  `aupdate_state()` sau `done`.
- Key lâu dài lưu dạng dict (`model_dump(mode="json")`), không lưu object pydantic (spike serializer phase 01).
- Kiểm trước graph (G7), so với `turn_count` trong checkpoint:
  `turn_number == turn_count` → chạy · `== turn_count - 1` và transcript có lượt đó → replay · khác → 409 ·
  thread không có → 404 · `phase == done` → 409 · `/start` trên thread đã có → 409.
- Khoá: `pg_try_advisory_lock(hashtext(session_id))` trên một connection giữ suốt stream, không lấy được → 409
  `turn_in_progress`. Bản `memory` dùng `asyncio.Lock` theo session.

## Đã làm (2026-11-27) và chỗ lệch so với thiết kế trên
- Code: `app/session_store/` (settings, checkpointer, record, guard, lock), node `record` trong graph, `TurnContext`
  qua runtime context (`context_schema`), `/start` ghi checkpoint đầu (`adelete_thread` + `aupdate_state`).
- **Lệch 1, stream đứt:** không resume ở `ask`. `ctx` (spec câu hỏi) không lưu được nên resume không có gì để hỏi.
  Chỉ node `record` ghi key lâu dài, lượt bị ngắt không tới `record` nên checkpoint giữ state trước lượt; gửi lại cùng
  answer thì chạy lại cả lượt (chấm lại, như hành vi cũ). Không cần lùi checkpoint cha. Run mới (`input={}`) luôn bắt
  đầu từ START dù checkpoint trước có `next=('ask',)` (spike phase 01, test `test_session_store_concurrency`).
- **Lệch 2, khoá:** khoá trong tiến trình (`session_lock.py`), không advisory lock. Đủ cho một instance (hiện tại).
  Chạy nhiều instance phải thêm advisory lock trên một kết nối giữ suốt stream trước khi bật.
- **Lệch 3, `/start` gửi lại:** xoá thread và ghi lại (không 409), vì interview-service có thể retry `/start`.
- **Lệch 4, thread không có:** chạy từ request rồi ghi, log `session_thread_missing` (404 để phase 04).
- Guard: replay → phiên `done` (409 `session_invalid_state`) → cùng lượt answer khác (409 `turn_already_answered`) →
  sai thứ tự (409 `turn_out_of_order`). Replay chạy trước kiểm `done` nên lượt kết thúc phiên cũng replay được.
- Review opus ([report](../reports/reviewer-261127-phase03-session-store.md)): đã sửa H1 (pool timeout 3 s +
  `wait_for` khi đọc / ghi `/start`: DB treo trả 503 nhanh, không giữ khoá), H2 (memory chỉ giữ 500 phiên mới nhất,
  cảnh báo khi `APP_ENV` staging/production dùng memory), M2 (ghi checkpoint `/start` lỗi chỉ log, vẫn `done`), M3
  (`/start` giữ khoá phiên), L3 (script không in thông báo lỗi). M1 ghi vào contract (retry phải gửi lại nguyên answer).
- **Còn mở:** M4 / L4 xoá dữ liệu phiên (transcript, checkpoint của lượt bị từ chối, text lỗi trong
  `checkpoint_writes`) theo TTL / consent là việc DE (doc 12 mục 9), hoặc ai-service xoá thread ở finalize (chưa
  chốt). L1 (huỷ đúng lúc ghi checkpoint cuối, retry có thể chấm lại), L5 (đổi qua lại memory / postgres để lại
  thread cũ) chấp nhận. Staging/prod chạy `SESSION_STORE` nào ở phase 03: chưa chốt.
- Đo trên Postgres local: phiên 17 lượt ≈ 245 KB (transcript ghi lại cả danh sách mỗi lượt, max 11 KB/blob).
- Kiểm: 1457 test xanh, golden 8/8 không đổi, test tích hợp Postgres qua, dev-play trên Postgres (start + 3 lượt =
  4 checkpoint, không có `session_state_mismatch`).

## Requirements
- `SESSION_STORE=memory|postgres` (mặc định `memory`: compose mock, test, dev-play). `postgres` cần `SESSION_DB_URL`.
- `AsyncPostgresSaver` + `AsyncConnectionPool` (`autocommit=True`; `prepare_threshold` theo pooler DE chốt, G9).
  Tạo bảng bằng `setup()`, chỉ chạy qua script / lệnh của DE, không tự chạy lúc app khởi động.
- Replay trả event SSE `meta` → `token` (cả câu, một lần) → `done` từ transcript, không gọi LLM (G11).
- Lỗi DB khi đọc → 503 `session_store_unavailable`, retryable. Không lùi về state client gửi (tránh hai nguồn sự thật).

## Related Code Files
- Tạo: `app/session_store/session_store_settings.py`, `app/session_store/session_checkpointer.py` (dựng saver
  theo cờ, mở / đóng pool trong `lifespan`), `app/session_store/session_turn_guard.py` (kiểm 404 / 409, replay),
  `app/session_store/session_lock.py`, `scripts/setup_session_checkpoint_tables.py`,
  `tests/test_session_store_guard.py`, `tests/test_session_store_replay.py`,
  `tests/integration/test_session_checkpoint_postgres.py`
- Sửa: `app/turn_graph/turn_graph_builder.py` (compile kèm checkpointer), `app/main.py` (`/start` ghi checkpoint
  đầu, `/next-turn` qua guard + lock), `.env.example` (`SESSION_STORE`, `SESSION_DB_URL`, comment `REPLAN_ENABLED`)

## Implementation Steps
1. Settings + dựng saver theo cờ; `lifespan` mở / đóng pool.
2. `/start`: sau `done` ghi checkpoint đầu (start_input, plan, state, transcript lượt 1).
3. `/next-turn`: lock → guard → chạy graph với `config={"configurable": {"thread_id": session_id}}` → ghi theo insight 2.
   Giai đoạn này vẫn đọc `plan` / `state` từ request, rồi **so** với checkpoint (log `session_state_mismatch`) để bắt lệch.
4. Test: trùng `turn_number` (không gọi Evaluator, đếm bằng fake), lượt cũ, thread không có, phiên `done`, hai
   request đồng thời, stream đứt rồi gửi lại cùng answer (resume, Evaluator không gọi lại), stream đứt rồi gửi lại
   answer khác (lùi checkpoint, chấm lại).
5. Test tích hợp Postgres: chạy trên Postgres local của compose, đánh dấu như `test_rag_pgvector.py`.
6. Chạy local: compose + `SESSION_STORE=postgres` trỏ DB local, chơi 1 phiên dev-play, kiểm bảng checkpoint.

## Todo List
- [x] Settings + saver + pool trong lifespan
- [x] Ghi checkpoint `/start` và `/next-turn`
- [x] Guard 409 + replay SSE (404 để phase 04)
- [x] Khoá trong tiến trình (advisory lock khi chạy nhiều instance)
- [x] Test guard, replay, đồng thời, stream đứt
- [x] Test tích hợp Postgres local
- [x] Chạy local dev-play với Postgres

## Success Criteria
- Một phiên mock đầy đủ không có log `session_state_mismatch`.
- Replay không gọi Evaluator / Interviewer. Hai request đồng thời: đúng một lần chạy, lần kia 409.
- Stream đứt rồi gửi lại cho ra cùng kết quả như chưa đứt.

## Risk Assessment
- Pooler Supabase không chạy được prepared statement → DE chọn session pooler / VM (G9).
- Advisory lock trên transaction pooler không giữ qua các câu lệnh: lock phải dùng session pooler hoặc kết nối trực tiếp.
- Checkpoint phình theo số lượt: mỗi lượt chỉ ghi `state` + một phần tử transcript (G6). Kiểm kích thước sau 1 phiên 30 phút.

## Security Considerations
- Transcript có câu trả lời của ứng viên (dữ liệu cá nhân): chỉ ai-service đọc. TTL + xoá theo consent là việc của DE (doc 12 mục 9).
- `SESSION_DB_URL` chỉ ở `.env`, không commit.

## Next Steps
- Phase 04 bỏ các trường khỏi request, dựng request nội bộ từ checkpoint.
