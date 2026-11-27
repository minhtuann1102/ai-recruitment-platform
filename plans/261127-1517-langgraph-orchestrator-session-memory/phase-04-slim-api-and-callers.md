# Phase 04: API rút gọn + sửa bên gọi (pha B)

## Context Links
- [plan.md](plan.md) · doc 12 mục 5, mục 7.2–7.3 · [06-api-contract](../../docs/ai-service/06-api-contract.md) ·
  [07-data-storage](../../docs/ai-service/07-data-storage.md)
- Code: `app/models_interview.py` (`NextTurnRequest`, `FinalizeRequest`, `FinalizeTurn`, `TopicTurn`),
  `app/report_scoring.py` (đọc `req.turns`), `app/static/dev-play*.js`, `evals/{simulate_session,play,cost_latency,
  sim_lookup_metrics,ttft_breakdown}.py`

## Overview
- Priority: P1 · Status: code xong, PR mở 2026-11-27 (nhánh `thang/langgraph-slim-api`); dev-play text mock đã chạy, voice chưa · Effort: 2,5d
- Breaking change với bên gọi HTTP. FSD chưa nối nên chỉ phải sửa harness trong repo này.

## Key Insights
- Thêm model body mới cho HTTP (`NextTurnBody`, `FinalizeBody`), giữ model nội bộ. Hàm
  `build_next_turn_request(body, checkpoint)` / `build_finalize_request(body, checkpoint)` dựng lại model cũ, nên
  `turn_engine`, Reporter và `report_scoring` không đổi.
- `question` = câu đã gửi ở lượt cuối của transcript; `turn_kind` = `TurnInfo.turn_kind` lượt cuối; `topic_turns`
  = ≤ 5 cặp hỏi đáp cuối của topic đang hỏi, trong transcript; `track` / `level` / `jd_profile` lấy từ `start_input`.
- Khoảng 10 file test post `/api/next-turn` kèm `state` tự dựng (ví dụ `test_time_budget`). Cần helper
  `seed_session(app, session_id, plan, state, transcript)` ghi thẳng vào store `memory`, không cần chạy `/start`.

## Quyết định khi bắt đầu code (2026-11-27)
Checkpoint phase 03 chưa đủ để dựng request, nên lưu thêm:
- `turn`: `TurnInfo` (JSON) của câu đang chờ trả lời. Ghi ở `/start` và ở mọi lượt có câu hỏi mới. Dùng để lấy
  `turn_kind` và `topic_id` của câu đó.
- Mỗi phần tử `transcript` thêm `topic_id`, `phase`, `turn_kind`, `difficulty` (lấy từ `turn` đã lưu của câu được
  trả lời) và `evaluation` (null nếu lượt không chấm).
- `session.jd_profile` (lưu ở `/start`; null nếu không có), dùng cho finalize.
- `topic_turns` = các phần tử transcript có `topic_id` trùng với câu đang hỏi, lấy 5 phần tử cuối,
  dạng `{q, a, source}`. Giống bên gọi hiện tại: lượt hỏi lại vì STT cũng được tính.
- `FinalizeRequest.turns` = toàn bộ transcript. `state.end_reason` lấy theo body nếu state lưu chưa có.
- Thread không có: next-turn và finalize trả 404 `session_not_found` (bỏ Lệch 4). Transcript rỗng khi finalize:
  409 `session_no_turns`. Finalize giữ khoá phiên (409 `turn_in_progress` khi đang có lượt chạy).
- Bỏ `mismatched_fields` / `session_state_mismatch`, và bỏ fallback ghi `session` / `plan` ở `turn_values`.

## Đã làm (2026-11-27)
- Code: `app/models_interview_http.py`, `app/session_store/session_request_builder.py`; `main.py` (`/next-turn`, `/finalize` dùng
  body slim, finalize giữ khoá khi đọc checkpoint); guard bỏ `mismatched_fields`, thread không có → 404; `session_record`
  lưu thêm `turn`, `session.jd_profile`, 4 trường + `evaluation` mỗi phần tử transcript, bỏ fallback ghi `session` / `plan`.
- Test: 1473 passed, 9 skipped (baseline phase 03: 1457). Golden 8/8 xanh, fixture không đổi (runner gửi body slim nhưng
  vẫn ghi request dựng tay vào trace). `test_session_request_builder` so request dựng lại với request dựng tay trên từng
  lượt của 8 kịch bản golden: bằng nhau, không có chỗ `topic_turns` lệch.
- Test sửa cách gửi (assert giữ nguyên) trừ chỗ hành vi bị bỏ theo spec: `test_finalize_requires_turns` (422 → 409
  `session_no_turns`), `test_missing_thread_runs_from_request...` (200 → 404), `test_checkpoint_keeps_small_per_turn_values_and_logs_state_drift`
  (bỏ log drift, thêm kiểm `turn` / transcript), `test_full_session_has_no_state_drift` (bỏ vế log đã không còn).
- `evals/simulate_session.py` gửi body slim (`evals/play`, `cost_latency`, `sim_lookup_metrics`, `ttft_breakdown` không gọi
  HTTP trực tiếp nên không đổi); `dev-play.js` gửi body slim. `evals.simulate --matrix quick` mock chạy đủ 10 phiên tới báo cáo.
- Review opus ([report](../reports/reviewer-261127-2243-phase04-slim-api.md)) đã sửa: H1 (`/start` ghi checkpoint lỗi
  → event `error` retryable, không `done`), M1 (`end_reason` một nguồn: state đã lưu hoặc body), M2 (thread thiếu `session` /
  `turn` → 404, log `session_schema_outdated`), M3 (test notes ở mức model), M4 (test e2e jd_profile → finalize
  `requirements`), M6 (tách `main.py` → `request_lifecycle_telemetry.py` + `interview_session_routes.py`), L1, L2, L4.
- **Deploy gate (H2):** `SESSION_STORE=memory` giờ là bản duy nhất của phiên: restart / dọn >500 phiên → 404 giữa phiên.
  Staging / production phải dùng `postgres`; không chặn khởi động (chỉ cảnh báo), ghi ở doc 06 / 07.
- **M5 đã sửa (user chốt 2026-11-27):** phiên phải hết giờ. `/start` ghi `session.started_at` (giờ server); mỗi lượt
  elapsed = max(body, elapsed lượt trước, giờ thực từ /start) (`session_clock.py`). Finalize phiên chưa `done` → 409
  `session_not_done`, trừ `candidate_ended` (ứng viên bấm kết thúc) và quá hạn cứng theo giờ server (`time_hard_limit`);
  hai trường hợp này ghi state `done` vào checkpoint (next-turn sau đó 409 `session_invalid_state`); bấm kết thúc khi
  chưa trả lời câu nào cũng chốt `done` rồi 409 `session_no_turns`. Review opus không có High. Còn để ngỏ: `duration_s`
  của báo cáo vẫn lấy từ body; `elapsed_seconds` body không có trần (chủ ý cho đồng hồ giả lập).
- **Kiểm Postgres (2026-11-27):** test tích hợp checkpoint qua trên Postgres 16 local. `evals.simulate --matrix quick`
  với `SESSION_STORE=postgres`: 10/10 phiên ra báo cáo; phiên 13–17 lượt tốn 140–310 KB blob (max 23 KB/blob), cả 10
  phiên 1,4 MB. Phase 03 đo 245 KB / 17 lượt trước khi lưu `evaluation`: tăng khoảng 25%. Voice chưa chạy (cần key
  Blaze cho voice-service + micro thật).
- Chưa làm: chạy local dev-play (text + voice) trên trình duyệt; đo kích thước checkpoint trên Postgres.

## Requirements
- `/api/next-turn` nhận `session_id`, `turn_number`, `answer`, `answer_source`, `stt_confidence`, `elapsed_seconds`.
- `/api/finalize` nhận `session_id`, `end_reason`, `duration_s`. Response hai endpoint giữ nguyên.
- Gửi trường cũ (`plan`, `state`…) → 422 (`extra="forbid"`), để bên gọi sửa sớm, không âm thầm bỏ qua.
- `/start` vẫn trả `plan` / `state` (plan.md câu hỏi mở 4).

## Related Code Files
- Tạo: `app/models_interview_http.py` (body mới), `app/session_store/session_request_builder.py`,
  `tests/helpers/seed_session.py`, `tests/test_session_request_builder.py`
- Sửa: `app/main.py` (endpoint nhận body mới), `app/static/dev-play-api.js` (+ `dev-play.js`, `dev-play-voice.js`,
  `dev-play-report.js`, `dev-play-trace.js` chỗ gửi payload), `evals/simulate_session.py`, `evals/play.py`,
  `evals/cost_latency.py`, `evals/sim_lookup_metrics.py`, `evals/ttft_breakdown.py`, các test HTTP liên quan
- Docs: `docs/ai-service/06`, `07`, contract gửi FSD (DE viết, AIE cung cấp payload mẫu)

## Implementation Steps
1. Body mới + builder + test builder (so với request cũ dựng tay từ golden phase 01: phải bằng nhau).
2. Endpoint đổi sang body mới; bỏ bước so `session_state_mismatch` của phase 03.
3. Helper `seed_session`; sửa các test HTTP: test chỉ đổi cách gửi, **không sửa assert**.
4. Sửa harness `evals/*` + dev-play JS. Chạy `simulate_session` mock 1 phiên đủ.
5. `pytest -q`, `check_docs.py`. Chạy local: compose + dev-play 1 phiên text, 1 phiên voice (nếu voice-service chạy được) tới report.

## Todo List
- [x] Body HTTP mới + builder + test
- [x] Endpoint dùng body mới
- [x] Helper seed_session, sửa test HTTP (giữ assert)
- [x] Sửa evals + dev-play JS
- [x] Chạy local dev-play text (mock, 2 phiên tới report); voice chưa (cần key Blaze + micro)
- [x] Docs 06 / 07 + payload mẫu cho FSD

## Success Criteria
- Golden phase 01 vẫn xanh qua API mới (đổi cách gửi, kết quả giống).
- Toàn bộ test xanh; `simulate_session` mock chạy hết phiên; dev-play chơi tới report.

## Risk Assessment
- `topic_turns` dựng lại khác cái bên gọi đang gửi (ví dụ bên gọi đang gộp cả lượt reask): so bằng golden trước khi bỏ trường.
- Trường `source` trong `TopicTurn` (text / voice từng lượt) phải được lưu trong transcript ở phase 03.

## Security Considerations
- Payload nhỏ hơn: bên gọi không còn gửi được state giả để lách luật (trước đây state do client giữ, sửa được).

## Next Steps
- Báo FSD contract mới (DE). Phase 05 nếu còn thời gian.
