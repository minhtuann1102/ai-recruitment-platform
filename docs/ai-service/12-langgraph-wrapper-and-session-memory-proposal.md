# Đề xuất: bọc orchestrator bằng LangGraph + memory phiên nằm trong ai-service

> **Trạng thái:** Đề xuất, chờ AIE / team duyệt · **Ngày:** 2026-11-26 · **Người đề xuất:** DE · **Người thực hiện chính:** AIE
>
> Đề xuất này **đảo ngược quyết định đã ghi** (mục 2), nên cần cả team đồng ý chứ không chỉ AIE. Trước khi được
> duyệt, không sửa README A4/A5, ADR-004 hay constitution.

## 1. Bối cảnh

- Đề cương đồ án ghi: *Orchestration: LangGraph (hoặc LangChain Agents), vòng Perceive–Evaluate–Decide–Act* và
  *Agent memory: lưu lịch sử hội thoại + điểm số từng tiêu chí qua các lượt, làm ngữ cảnh cho quyết định kế tiếp*.
- Code hiện tại đã làm đúng vòng đó nhưng tự viết bằng code (`app/turn_engine.py`, `turn_evaluation.py`,
  `turn_decision.py`, `state_update.py`). Bảo vệ dễ bị hỏi "LangGraph ở đâu".
- Memory (`CandidateState`: topics, strengths, gaps, counters, swaps, notes…) có sẵn nhưng ai-service trả về cho
  bên gọi giữ. Contract lưu trữ đã thiết kế ở [06](06-api-contract.md) / [07](07-data-storage.md) cho
  interview-service (NestJS), **nhưng FSD chưa làm**. Repo FSD (`hoangtunggg/final_recruitment_project`, kiểm
  2026-11-26) là Express + Sequelize + MySQL, chưa gọi ai-service, chưa có bảng phiên. Chốt bây giờ là rẻ nhất.

## 2. Quyết định bị đảo ngược

| Chỗ ghi | Nội dung hiện tại | Sau đề xuất |
|---|---|---|
| [README](README.md) A4 | "Không dùng LangGraph/agent framework: state machine tự viết" | LangGraph điều phối; logic trong node vẫn là code tự viết |
| README A5, [ADR-004](../architecture/adr/adr-004-interview-data-ownership.md) | interview-service sở hữu toàn bộ dữ liệu phỏng vấn; ai-service không lưu phiên | ai-service lưu memory phiên (plan, state, transcript); backend lưu session_id + report |
| Constitution IV | "ai-service là stateless processor… MUST NOT lưu phiên" | Sửa qua `/speckit-constitution` (amendment) |
| [06-api-contract](06-api-contract.md), [07-data-storage](07-data-storage.md) | Payload gửi kèm plan / state / transcript; bảng `interview_sessions` giữ state | Payload rút gọn (mục 5); bảng lưu ở ai-service (mục 4) |

Lý do cũ của ADR-004 / constitution IV là "AI có thể thay thế / mock mà không mất dữ liệu nghiệp vụ". Đề xuất
vẫn giữ được ý này một phần: **report cuối và session_id vẫn ở backend**. Chỉ dữ liệu đang chạy của phiên nằm ở
ai-service.

## 3. Graph: bọc, không viết lại

Mỗi node gọi lại đúng hàm đang có. Prompt, model, gateway, `llm/tool_loop.py` giữ nguyên. Thân hàm
`next_turn()` hiện tại tách thành 4 node:

| Node | Việc (hàm đang có) | Cạnh ra |
|---|---|---|
| `perceive` | Đọc checkpoint; `phase == done` → 409; `wrap_up` → đóng phiên; `check_alignment`; voice: `heard_answer` / `no_speech` / `low_confidence` | reask (`_reask`) · 422 voice · `evaluate` |
| `evaluate` | `evaluate_turn` (hoặc `unclear_evaluation`), `reference_missing`, `record_evaluation` | `decide` |
| `decide` | `forced_transition` ("end" → kết thúc), `choose_decision` (forced → hybrid LLM đã kiểm → luật → `low_performance_stop`), swap | end · `act` |
| `act` | `apply_action`, `pick` câu trong kho, dựng `QuestionSpec` + `TurnInfo` | END (trả `TurnResult`) |

- Interviewer stream SSE **ở ngoài graph** như hiện tại (`_stream` → `finish_turn`).
- `/start`: `start_session` giữ nguyên, thêm ghi checkpoint đầu tiên. Có thể mô hình thành node `plan` nếu muốn
  sơ đồ đủ, không bắt buộc.
- Xuất sơ đồ bằng `graph.get_graph().draw_mermaid()` cho báo cáo.

## 4. Memory trong ai-service

- Checkpointer Postgres (`langgraph-checkpoint-postgres`, `PostgresSaver`), `thread_id = session_id`.
- Lưu: input lúc start (track, level, duration, cv_profile, jd_profile), `plan` **nguyên vẹn** (kể cả
  `plan.replan`), `CandidateState` **nguyên vẹn** (kể cả `swaps`, `notes`, `schema_version`), transcript từng lượt
  (câu hỏi đã gửi, câu trả lời, nguồn, evaluation, TurnInfo).
- **Thời điểm ghi:** chỉ ghi khi stream tới `done` (sau `finish_turn`, lúc đã biết câu hỏi thật,
  `asked_questions`, `question_source`, `qa_id`). Stream đứt → không ghi → client gửi lại cùng lượt, tính lại từ
  đầu. Giống hành vi hiện tại (state chỉ trả ở event `done`).
- **Gửi trùng `turn_number`** của lượt đã ghi → trả lại kết quả đã lưu (câu hỏi + TurnInfo + evaluation), không
  chạy lại graph, không gọi LLM.
- `turn_number` nhỏ hơn lượt hiện tại mà không phải lượt vừa ghi → 409. `session_id` không có → 404.
- DB: chọn ở mục 9. Dọn phiên cũ (TTL) và xoá theo yêu cầu / consent là việc của DE.

## 5. Thay đổi API

| Endpoint | Bên gọi vẫn gửi | Bỏ khỏi request (ai-service tự lấy từ checkpoint) | Response |
|---|---|---|---|
| `POST /api/start` | `session_id`, `track`, `level`, `duration_minutes`, `cv_profile`, `jd_profile` | — | Giữ nguyên (plan / state vẫn trả để dev-play hiển thị; bỏ sau nếu không ai dùng) |
| `POST /api/next-turn` | `session_id`, `turn_number`, `answer`, `answer_source`, `stt_confidence`, `elapsed_seconds` | `track`, `level`, `plan`, `state`, `question`, `turn_kind`, `topic_turns` | Giữ nguyên |
| `POST /api/finalize` | `session_id`, `end_reason`, `duration_s` | `track`, `level`, `plan`, `state`, `turns`, `jd_profile` | Giữ nguyên |

- `elapsed_seconds` / `duration_s` **vẫn do bên gọi gửi** (bên gọi giữ đồng hồ, tính cả lúc tạm dừng).
  `forced_transition`, `time_hint`, hạn phase phụ thuộc giá trị này. Đổi sang ai-service tự tính là câu hỏi mở.
- `topic_turns` (≤ 5 cặp hỏi đáp của topic đang hỏi) dựng lại từ transcript đã lưu.
- Backend (FSD) chỉ cần lưu `session_id` + report từ `/finalize`.

## 6. Cờ đang tắt

- `REPLAN_ENABLED`: comment trong `.env.example` cần 2 điều kiện. (1) "lưu nguyên plan/state" → **B tự đáp ứng**.
  (2) "chấp nhận topic_id `alt*`" → **vẫn cần FSD**, vì topic `alt*` xuất hiện trong turn / report mà FSD hiển
  thị. Tức là mới đủ một nửa.
- `AGENT_NOTES_ENABLED`: vẫn tắt, lý do là chưa đo chất lượng (gate chấm điểm, đọc tay 20 phiên), không liên quan
  chỗ lưu. Khi bảo vệ, `state.notes` là ví dụ "agent memory" rõ nhất.

## 7. Kiểm tra (không cần chạy lại eval chất lượng)

Logic, prompt, model không đổi nên không đo lại chất lượng. Cần:

1. **Test tương đương** chế độ mock (`AGENT_*_MODE=mock`): cùng kịch bản chạy qua `next_turn()` cũ và qua graph,
   từng lượt phải giống hệt action, state, TurnInfo, QuestionSpec. Gồm cả nhánh reask voice, 422, forced end,
   wrap_up, swap.
2. **Sửa bên gọi HTTP** theo API mới: `evals/simulate_session.py`, `play.py`, `cost_latency.py`, trang dev-play
   (`app/static/dev-play*.js`), test gọi endpoint. Test gọi thẳng hàm trong `turn_engine` không đổi.
3. **Test mới**: gửi trùng `turn_number`, `turn_number` cũ, `session_id` không có, phiên đã `done`, stream đứt
   giữa chừng rồi gửi lại.
4. **Độ trễ**: chạy `cost_latency` một lần, chắc rằng đọc + ghi checkpoint không ăn vào ngân sách ~10 s của
   Evaluator.

## 8. Dependency

`pip install --dry-run` ngày 2026-11-26 (giữ `langchain-core==0.3.86`, `psycopg` 3.2.12, `psycopg-pool` 3.3.3)
giải được: `langgraph 1.0.1`, `langgraph-checkpoint 3.0.1`, `langgraph-checkpoint-postgres 3.0.5`,
`langgraph-prebuilt 1.0.1`, `langgraph-sdk 0.2.15`, `ormsgpack 1.13.1`. **Mới giải được phụ thuộc, chưa chạy
thử** → kiểm lại khi cài thật.

## 9. Chia việc

| Ai | Việc |
|---|---|
| AIE (Thắng) | Graph + node (mục 3), đổi API (mục 5), ghi checkpoint + idempotency (mục 4), test tương đương + sửa harness (mục 7) |
| DE | Chọn DB cho checkpoint (Supabase `ai_db` hay Postgres trên VM); **kiểm pooler Supabase có chạy được `PostgresSaver` không** (pooler transaction không hỗ trợ prepared statement); tạo bảng (`setup()`), job dọn phiên, xoá theo consent; viết contract mới gửi FSD; amendment constitution + ADR mới thay một phần ADR-004 |
| FSD (Tùng) | Nối backend theo contract mới: lưu `session_id`, gọi 3 endpoint, lưu report |

## 10. Khi được duyệt, cập nhật

README A4/A5 · constitution IV (`/speckit-constitution`) · ADR mới (thay một phần ADR-004) · [06](06-api-contract.md) ·
[07](07-data-storage.md) · [03](03-orchestrator-state-machine.md) (sơ đồ graph) · `.env.example` (comment
`REPLAN_ENABLED`) · `specs/README.md` (feature mới, chọn Spec Kit hay primary workflow).

## Câu hỏi mở

1. Team (AIE, FSD, DE) đồng ý đảo ADR-004 / constitution IV không? Mentor có yêu cầu gì về LangGraph / agent memory?
2. Có chỗ nào trong `next_turn()` khó tách thành node (reask voice, forced end, swap tính lại plan)?
3. Đồng hồ phiên: bên gọi giữ (`elapsed_seconds` như hiện tại) hay ai-service tự tính từ lúc start?
4. Response `/start` có còn cần trả `plan` / `state` không?
5. DB cho checkpoint: Supabase `ai_db` (nếu pooler chạy được) hay Postgres trên VM staging?
6. AIE ước lượng bao lâu cho phần của mình, so với hạn 21/12/2026?
