# Phase 01: Golden trace + cài dependency

## Context Links
- [plan.md](plan.md) · doc 12 mục 7.1 (test tương đương), mục 8 (dependency), G1, G10
- Code: `apps/ai-service/app/turn_engine.py`, `app/main.py` (`_stream`), `tests/test_interview_flow.py`

## Overview
- Priority: P1 · Status: **done (2026-11-27)** · Effort: 0,5d
- Chụp hành vi hiện tại **trước khi sửa code**, để phase 02 so được với bản gốc chứ không phải với chính bản đã
  refactor. Cài langgraph thật và trả lời câu hỏi mở về `durability`.

## Key Insights
- Nếu chỉ so `next_turn()` cũ với graph sau khi đã tách hàm, cả hai gọi chung hàm mới, nên lỗi do tách hàm không
  lộ ra. Golden trace ghi từ code trên `main` mới là chuẩn để so.
- Doc 12 mục 8 mới `pip install --dry-run`, chưa chạy thật.

## Requirements
- Bộ kịch bản mock (`AGENT_*_MODE=mock`, `RAG_ENABLED=false`) phủ: lượt bình thường, follow_up, hint, clarify,
  next_topic, next_phase, swap (`POLICY_MODE=hybrid`, `REPLAN_ENABLED=true` với proposal giả), reask voice,
  422 `voice_no_speech`, 422 `voice_unclear`, forced end, wrap_up → done, 409 phiên `done`, `low_performance` stop.
- Mỗi lượt ghi: action, `TurnInfo`, `CandidateState`, `QuestionSpec` (các trường dữ liệu), evaluation, các event SSE
  (tên + data), mã lỗi nếu có.

## Related Code Files
- Tạo: `tests/golden_turns/scenarios.py` (định nghĩa kịch bản), `tests/golden_turns/record_golden_turns.py`
  (script ghi), `tests/fixtures/golden_turns/*.json`
- Sửa: `requirements.txt` (thêm `langgraph`, `langgraph-checkpoint-postgres`, pin đúng bản ở doc 12 mục 8)

## Implementation Steps
1. Viết kịch bản dựa vào fake sẵn có ở `tests/fakes/` (Evaluator / Interviewer giả, xác định được).
2. Ghi golden bằng `TestClient` gọi `/api/start` + `/api/next-turn` (đúng đường HTTP + SSE), khi code còn như `main`.
3. Cài thật trong venv: `pip install langgraph==1.0.1 langgraph-checkpoint-postgres==3.0.5`. Chạy `pytest -q`
   toàn bộ để chắc không vỡ (`langchain-core` giữ `0.3.86`).
4. Spike 30 phút (script trong scratchpad, không commit): graph 2 node, node 2 dùng `get_stream_writer()` rồi
   `asyncio.sleep`. Huỷ task giữa chừng, với `InMemorySaver` + `durability="exit"`, rồi kiểm `aget_state()` có
   checkpoint mới không. Ghi kết quả vào plan.md câu hỏi mở 2.
5. Spike: `JsonPlusSerializer` round-trip `CandidateState` / `InterviewPlan` (pydantic v2). Nếu lỗi thì phase 03 lưu `model_dump()`.

## Todo List
- [x] Kịch bản + script ghi golden
- [x] Fixture golden ghi từ code `main`
- [x] Cài dependency thật, toàn bộ test xanh
- [x] Spike `durability` khi huỷ, ghi kết quả
- [x] Spike serializer pydantic

## Kết quả (2026-11-27)
- **Golden:** `tests/golden_turns/` (runner đóng vai bên gọi, 8 kịch bản), fixture `tests/fixtures/golden_turns/`
  (~880 KB, chủ yếu `state` mỗi lượt + lịch sử `/finalize`), test `tests/test_golden_turns_match_fixture.py`. Ghi lại:
  `.venv/bin/python -m tests.golden_turns.record_golden_turns [tên]`.
  Phủ: follow_up, hint, clarify, ask_main (sau next_topic / next_phase), wrap_up → done, 409 sau done, `two_dont_know`,
  `low_performance` (senior), `time_hard_limit`, voice 422 `voice_no_speech` / reask / 422 `voice_unclear`, câu trong
  kho (`question_source = bank`, qa_id, fake RAG), hybrid (`decided_by = llm`, swap `applied` / `budget` / `not_applicable`).
  Chưa phủ: forced `wrap_up` do `turn_cap`, `AGENT_NOTES_ENABLED`, `reference_missing`, Interviewer lỗi giữa stream (`replace`).
  Đã kiểm: chạy lại ra fixture y hệt; sửa 1 giá trị trong fixture thì test báo đúng lượt.
- Mỗi event `token` liên tiếp được gộp thành `["token*", {n, t}]`. Khoá `latency_ms` bị bỏ.
- Patch Evaluator ở `app.turn_engine.get_evaluator` (`EVALUATOR_SEAM` trong `golden_scenarios.py`). Phase 02 đổi chỗ
  gọi thì đổi seam, **không** ghi lại fixture.
- **Dependency:** `langgraph 1.0.1`, `langgraph-checkpoint 3.0.1`, `langgraph-checkpoint-postgres 3.0.5` (+ prebuilt
  1.0.1, sdk 0.2.15, ormsgpack 1.13.1) cài được với `langchain-core 0.3.86`, psycopg 3.2.12. Toàn bộ test: 1425 passed, 8 skipped
  (Python 3.11, `.venv` dựng bằng `uv venv --python 3.11`). Cảnh báo `LangChainPendingDeprecationWarning` (`allowed_objects`)
  lúc import serde: vô hại, xử lý ở phase 03 nếu dựng serde riêng.
- **Spike durability** (graph `prep → ask`, `ask` stream qua `get_stream_writer`, `InMemorySaver`):

  | durability | chạy hết | ngắt (aclose / huỷ task) giữa `ask` |
  |---|---|---|
  | `exit` | 1 checkpoint, state cuối | **vẫn ghi 1 checkpoint**: state sau `prep`, `next=('ask',)`; phần `ask` dở không ghi |
  | `async` / `sync` | 4 checkpoint | 3 checkpoint, cũng dừng ở `next=('ask',)` |

  → Giả định "huỷ thì không ghi" ở G1 **sai**. Hệ quả cho phase 03 ghi ở đó (resume `ask` hoặc lùi về checkpoint cha).
- **Spike serializer:** `JsonPlusSerializer` round-trip `InterviewPlan` (có `replan`) và `CandidateState` cả dạng object
  lẫn `model_dump(mode="json")`, bằng nhau. Plan 30 phút khoảng 5,1 KB, state khoảng 1 KB. Chọn lưu **dict** cho key lâu dài:
  checkpoint không bị phụ thuộc đường dẫn import của class (đổi tên module là checkpoint cũ không đọc được).

## Success Criteria
- Fixture golden có đủ các nhánh trong Requirements. Ghi lại hai lần cho ra file giống hệt (xác định được).
- `pytest -q` xanh sau khi thêm dependency.

## Risk Assessment
- Fake có ngẫu nhiên (`pick` câu trong kho): cố định seed / dùng fake retriever. Không xác định được thì không dùng làm golden.
- langgraph kéo bản `langchain-core` khác: giữ pin, đọc lại kết quả resolver.

## Security Considerations
- Không có. Không gọi LLM thật, không cần khoá.

## Next Steps
- Phase 02 dùng fixture này làm test tương đương.
