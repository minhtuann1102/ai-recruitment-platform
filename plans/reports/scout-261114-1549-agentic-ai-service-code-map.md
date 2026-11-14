# Scout: bản đồ code cho đề xuất agentic ai-service

Baseline `main` cbb51f7. Đường dẫn tương đối `apps/ai-service/`. Đối chiếu với `plans/reports/aie-request-261114-1057-agentic-ai-service.md`.

## Đề xuất sai / thiếu so với code
- Hạng mục 3: `NextTurnRequest` (`models_interview.py:150-165`) **không có `jd_profile`**. Ưu tiên JD phải lưu vào plan/state lúc start, hoặc next-turn thêm trường tùy chọn.
- Hạng mục 3 thiếu chỗ đọc topic: `report_resources.py:26`, `agents/reporter.py:71`, `evals/simulate_session.py:47`. Đổi 1:1 trong technical thì `topic_budget_s` không đổi. `plan_validator` không cần sửa (chỉ Planner gọi, trước khi có reserve).
- Hạng mục 3: id dự phòng "r1" trùng kiểu id yêu cầu JD (`r1..`, `models_jd.py:10`) và id resource báo cáo (`report_resources.py:39`). Dùng tiền tố khác.
- Hạng mục 3: số topic dự phòng mỏng. fresher chỉ dư 1–2 topic (python fresher 5 topic / 4 slot). "2 topic dự phòng" không luôn có.
- Hạng mục 2: `_clamp` ở `state_update.py:10`. `next_topic` dùng `min(delta, 0)` (`state_update.py:80`), nên delta dương của LLM vô tác dụng khi sang topic.
- Hạng mục 2: tập loại câu nhạy cảm còn thiếu `dont_know` (cũng không giao cho LLM).
- Hạng mục 1: `_search` không "< 20 ms": chỉ BM25 nhanh; còn SQL boost `topic_id` tới 1 s trừ khi `memory_only=True`. `_filters` không mang độ khó (áp ở `_search:85-86`). `_known` chỉ lọc `topic.reference_snippets`. `wrap_untrusted` ở `prompts/store.py:52`.
- Hạng mục 1: "`current_qa_id` rỗng" khác "không có R": có qa_id nhưng lấy đáp án lỗi/quá hạn thì R rỗng và turn chunks cũng bị bỏ (`turn_engine:162` đặt `reference_missing`). Điều kiện bật công cụ nên là `not inp.reference_answer`.
- Thêm `evaluator.v9.md` làm vỡ test: `tests/test_llm_evaluator.py:63,129` cố định "v8" là mới nhất; `tests/test_evaluator_source_checks.py:83` dùng v9 làm bản không tồn tại.
- interview-service không có trong repo: chưa xác minh được "lưu nguyên plan/state". Docs 06 `:518,523` nói lưu nguyên `evaluation` và `plan`.
- Docstring `plan_bank_coverage.py:3-4` còn mốc cũ 0,63/0,88 (đúng: 0,53/0,71 theo judge_support v2).

## 0. Gateway / tool calling
- Dòng: `llm/gateway.py` 188, `usage.py` 51, `retry.py` 116, `settings.py` 117, `structured_output.py` 52, `metrics.py` 109, `tracing.py` 171, `tests/fakes/fake_llm.py` 98.
- `complete` `:65-72` mở 1 observation generation cho cả lần gọi. `_complete` `:74-126`: params `:76-82` (response_format strict); closure `chat()` `:85-105` giữ hedge (chỉ lần đầu, `:89`), trừ ngân sách dùng chung (`:90-92`), retry, cộng usage, `finish_reason == "length"` thử lại ×1.5 max_tokens; trả `message.content or ""`. Parse + 1 lần repair `:107-118`. Ghi `rec`, `collector.add` `:119-126`.
- **Phải tách closure `chat()` ra hàm dùng chung** để vòng lặp công cụ tái dùng; gateway gần 200 dòng.
- Evaluator: temp 0, max_tokens 400, timeout 8 s, seed 7, retry budget 10 s (`settings.py:26`). `retry.py`: 2 lần retry, `_within` cắt bằng `wait_for`.
- Bẫy: có `tool_calls` thì `content` None; `finish_reason == "tool_calls"`; fake `reply()` không có thuộc tính `tool_calls` (dùng `getattr`); SimpleNamespace không có `model_dump`, phải tự dựng message assistant.
- Lỗi: `LlmError` ⊃ `LlmOutputError`, `LlmTimeoutError`; Evaluator bắt `(LlmError, ConfigError, openai.APIError)` `agents/evaluator.py:221`. Lỗi công cụ, JSON đối số sai, quá `max_steps` phải quy về các lớp này.
- Usage: `CallRecord` `usage.py:7-17`; `to_metadata` `:35-51`. Thêm số lần gọi công cụ vào `metadata.usage[agent]` là đổi contract (docs 06 §7.4). Metrics: `record_request` `metrics.py:57-73`, `record_turn` `:82`; mọi writer bọc `@_safe`.
- Tracing: `observation(name, as_type, nest=False)` `tracing.py:124`; span con dùng `nest=True` như `turn_evaluation.py:58`.

## 1. Evaluator tự tra cứu
- Gọi: `turn_engine.next_turn:160` → `evaluate_turn` (`turn_evaluation.py:50-71`): `answer_key` + `turn_snippets` song song trong `observation("rag_turn")`, rồi `evaluator.evaluate(EvaluationInput(...))` `:66-70`. Retriever **không** được truyền vào Evaluator: cần field hoặc closure.
- `Evaluator` Protocol `agents/evaluator_provider.py:17-18` trả `Evaluation`; `MockEvaluator` `:21-36`; `evals/turn_source_recorder._RecordingEvaluator` `:34-39` chụp `inp` trước vòng lặp, sẽ không thấy chunk từ công cụ nếu không sửa.
- `agents/evaluator.py` (234): `EvaluatorOutput` `:46-52`, `EvaluatorOutputV4` `:61-63`, `uses_sources` `:66`; `EvaluationInput` `:70-85` (`turn_snippets`, `turn_sources` `:82-83`); `build_messages` `:88-106`; `all_snippets` `:109-111` = topic snippets + turn snippets (S-ids cố định, R cuối); `source_refs` `:114-120`; `postcheck` `:139-185`; `evaluate_with_raw` `:202-234` (precheck `:205-207`, STT `replace(inp)` `:210-213`, gọi gateway `:216-220`, postcheck `:230` phải nhận `inp` đã mở rộng, degraded `:221-229`).
- `evaluator_source_checks.py`: `source_blocks` `:24-27`, `check_sources` `:42-54` (bỏ id lạ, tối đa 3), `refuted_by_reference` `:57-61` (chỉ R).
- `turn_reference_snippets.py` (123): hằng `:27-33` (`TURN_K, TURN_TOKENS = 3, 600`); `_known` `:45-47`; `_filters` `:50-55`; `_search(..., memory_only)` `:79-96`; `turn_snippets` `:99-123` bỏ qua khi intro, có đáp án, độ khó ngoài 1–5.
- Công cụ: `known` = `[*topic.reference_snippets, *inp.turn_snippets]`; dùng `memory_only=True` để giữ < 20 ms.
- Prompt: `PromptStore.get` lấy N lớn nhất (`prompts/store.py:28-44`), mới nhất v8 (88 dòng). Env `EVALUATOR_PROMPT_VERSION` `evaluator_provider.py:50`. `strict_schema` bắt mọi field required, nên field mới phải ở lớp mới (vd `EvaluatorOutputV9`) có cổng phiên bản.

## 2. Policy lai
- `policy.py` (60): ngưỡng `:10-11` (trùng ở `state_update.py:7`); `Decision` `:14-19`; `classify` `:22-28`; `decide` `:31-60` (11 luật; `left` `:36` đếm chung follow_up/hint/clarify `state_update.py:49`; `hinted` `:39`).
- `focus.py`: `same` `:16`, `gap_focus` `:51-56`, `hint_focus` `:59-64`, `deepen_focus` `:67-70`. `safe_focus` ở `agents/interviewer.py:43-48` (trả None khi có injection, cắt 150). Mẫu injection `cv_text.py:27-30` gồm `\binstruction`, `you are`, "```" nên có thể bỏ nhầm ghi chú kỹ thuật.
- Thứ tự `turn_engine.next_turn` (216 dòng): `:160` chấm → `:167` `forced_transition` → `:172-176` quyết định cưỡng bức, nếu không `:179-180` `decide` → `:181` `low_performance_stop` → `:185` `safe_focus` → `:186` `apply_action` → `:189-199` chọn câu kho → `:203-205` `TurnInfo`. Chỗ móc hybrid: giữa `:177` và `:180`. `time_hint` tính sau quyết định (`:197`, `:210-216`).
- Đưa `next_action` từ Evaluator sang `next_turn`: `Evaluator.evaluate` chỉ trả `Evaluation` (gửi cho interview-service). Lựa chọn: thêm field vào `Evaluation` (đổi contract) hoặc đổi Protocol / dùng `evaluate_with_raw`.
- `TurnInfo` `models_interview.py:121-131`; `reasoning` hiện "do code sinh" (docs 06 `:529`). `Counters` `:84-89`, reset khi đóng topic `state_update.py:67`.

## 3. Lập lại kế hoạch
- `flat_topics` `turn_engine.py:70-71`, dùng ở `:97`, `:138`; test `test_time_budget.py`, `test_early_stop.py`.
- Đọc `plan.phases[].topics`: `turn_engine:96,212`; `time_budget.py:19,29,38,51`; `report_scoring.py:82,100`; `requirements_coverage.py:20`; `report_resources.py:26`; `agents/reporter.py:71`; `evals/simulate_session.py:47`; `evals/sim_metrics.py`.
- Căn theo vị trí: `state.topics[i]` ↔ `flat_topics(plan)[i]` (`turn_engine:100-104`, `state_update:63-65,75`, `early_stop:28`, `next_turn:144`). **Thay tại chỗ** topic pending giữ được căn chỉnh; **chèn** thì vỡ.
- Start: `start_coverage` `:90` đã đếm mọi topic của level; `prefer_covered(plan, ..., keep=jd.priority_topic_ids())` `:92-93` đổi tại chỗ, giữ `topic.id`, dựng lại bằng `catalog_topic` (`mock_planner.py:71`); `attach_reference_snippets` `:95` (`plan_snippets.py:156-189`, hạn 5 s, thêm reserve vào danh sách `:163`).
- `TopicState.status` Literal `pending|active|done` `models_interview.py:74`; `InterviewPlan` `:65-68`; Pydantic bỏ field lạ. `/api/next-turn` không trả plan (`main.py:243-247`).
- Báo cáo: topic chưa hỏi đã bị loại vì chỉ tính topic có lượt chấm (`report_scoring:77-131`), `requirements_block` ghi `not_assessed`.
- Nếu swap chỉ nằm trong state và reserve nằm ngoài `phases`, finalize sẽ bỏ lượt chấm của topic mới và vỡ trạng thái JD. Mọi chỗ đọc topic cần danh sách thực tế.

## 4. Ghi chú
- `CandidateState` `models_interview.py:97-118`; `Tagged` `:92-94`; `strengths`/`gaps` ≤ 10 tag (`state_update.py:19`); `covered` ≤ 10 × 150 ký tự, `focus_used` 6 gần nhất, theo topic. Thêm `notes: List[Note] = []` tương thích state cũ.

## Đo
- `evals/simulate.py`: `--matrix quick|full`, `--simulator rule|llm`, `--serve`, `--duration`, `--concurrency`, `--out`. **Không có `--runs`** (phương sai cần vòng ngoài) và không có cờ chế độ policy (theo env).
- `sim_metrics.py`: discrimination, adaptation, constraints (`repeat_rate`, vi phạm follow-up), report_quality, injection, question_bank, grounding, rag_health. **Chưa có** tỷ lệ kết thúc đúng lý do và tỷ lệ đồng ý quyết định.
- `personas.py`: 3 mức × 4 level × java/nodejs + 5 persona đối kháng; persona lệch kỹ năng cần builder mới.
- `ttft_breakdown.py`, `cost_latency.py`, `judge_support.py` (+ `support_set.py`), `run_evaluator.py` (`--runs --prompt --set main|holdout --stt`), `run_evaluator_sourced.py`, `turn_source_recorder.py` (cần sửa để thấy chunk công cụ).

## Cấu hình và test
- Cờ boolean: `_flag(value, default)` `llm/settings.py:64-66`. Cờ RAG trong `RagSettings` (`rag/settings.py`), nạp một lần. Cờ khác đọc `os.getenv` lúc gọi (`EVALUATOR_PROMPT_VERSION`, `AGENT_<NAME>_MODE`, `LLM_HEDGE_<AGENT>`). Thêm cờ mới vào `.env.example`.
- Test: `tests/test_*.py` phẳng + `tests/fakes/`; `conftest.py` tắt RAG, Langfuse, agent mock; dùng `asyncio.run`. CI `python -m pytest -q`. `test_prompt_injection_guards.py` (130) chưa có ca chặn LLM đổi hành động / ghi chú.

## File đã quá 200 dòng sẽ bị chạm
`agents/evaluator.py` 234, `turn_engine.py` 216, `models_interview.py` 249, `main.py` 266 (nếu đổi `done()`), `tests/test_llm_gateway.py` 231, `tests/test_langfuse_tracing.py` 306, `tests/test_plan_bank_coverage.py` 220, `tests/test_question_bank.py` 211, `evals/judge_support.py` 244. Gần ngưỡng: `llm/gateway.py` 188, `plan_snippets.py` 189, `tracing.py` 171. Docs 02 (577), 06 (601).
