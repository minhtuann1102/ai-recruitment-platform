# Phase 04: API rút gọn + sửa bên gọi (pha B)

## Context Links
- [plan.md](plan.md) · doc 12 mục 5, mục 7.2–7.3 · [06-api-contract](../../docs/ai-service/06-api-contract.md) ·
  [07-data-storage](../../docs/ai-service/07-data-storage.md)
- Code: `app/models_interview.py` (`NextTurnRequest`, `FinalizeRequest`, `FinalizeTurn`, `TopicTurn`),
  `app/report_scoring.py` (đọc `req.turns`), `app/static/dev-play*.js`, `evals/{simulate_session,play,cost_latency,
  sim_lookup_metrics,ttft_breakdown}.py`

## Overview
- Priority: P1 · Status: pending · Effort: 2,5d
- Breaking change với bên gọi HTTP. FSD chưa nối nên chỉ phải sửa harness trong repo này.

## Key Insights
- Thêm model body mới cho HTTP (`NextTurnBody`, `FinalizeBody`), giữ model nội bộ. Hàm
  `build_next_turn_request(body, checkpoint)` / `build_finalize_request(body, checkpoint)` dựng lại model cũ, nên
  `turn_engine`, Reporter và `report_scoring` không đổi.
- `question` = câu đã gửi ở lượt cuối của transcript; `turn_kind` = `TurnInfo.turn_kind` lượt cuối; `topic_turns`
  = ≤ 5 cặp hỏi đáp cuối của topic đang hỏi, trong transcript; `track` / `level` / `jd_profile` lấy từ `start_input`.
- Khoảng 10 file test post `/api/next-turn` kèm `state` tự dựng (ví dụ `test_time_budget`). Cần helper
  `seed_session(app, session_id, plan, state, transcript)` ghi thẳng vào store `memory`, không cần chạy `/start`.

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
- [ ] Body HTTP mới + builder + test
- [ ] Endpoint dùng body mới
- [ ] Helper seed_session, sửa test HTTP (giữ assert)
- [ ] Sửa evals + dev-play JS
- [ ] Chạy local dev-play text + voice
- [ ] Docs 06 / 07 + payload mẫu cho FSD

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
