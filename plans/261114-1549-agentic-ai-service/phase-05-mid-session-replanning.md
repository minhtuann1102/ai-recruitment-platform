# Phase 05: Lập lại kế hoạch giữa buổi (hạng mục 3, gated)

## Context Links
- Đề xuất mục 7; reply mục 8; code map mục "3. Lập lại kế hoạch" + "Đề xuất sai" (jd_profile, id `r`, pool mỏng)
- `app/turn_engine.py:70-104,138,144,212`, `app/state_update.py:40-80`, `app/early_stop.py:18-28`, `app/time_budget.py:19-51`,
  `app/plan_bank_coverage.py`, `app/mock_planner.py:71,133-135`, `app/plan_snippets.py:156-189`, `app/models_interview.py:60-118`,
  `app/models_jd.py:10,32`, `app/report_scoring.py:77-131`, `app/requirements_coverage.py:20`, `app/report_resources.py:26,39`,
  `app/agents/reporter.py:71`, `app/main.py:223-266`, `evals/simulate_session.py:47`, `evals/sim_metrics.py`
- Phase 04 (V9, `choose_decision`, TurnInfo trace); phase 01 (persona `skewed` + fixture JD/CV); audit H7, M5, M6, M9, L1

## Overview
- Priority: P3. Status: code + test LLM giả xong (1108 passed), **cờ giữ tắt, blocked bởi FSD**; đo [BLOCKED-KEY]. Nhánh: `thang/mid-session-replan`. Effort 3d.
- Cờ `REPLAN_ENABLED=false`, `REPLAN_MAX_SWAPS=1`; chỉ có tác dụng khi `POLICY_MODE=hybrid`.
- Ở ranh giới topic technical, LLM đề xuất đổi 1 topic technical `pending` lấy 1 topic dự phòng chuẩn bị sẵn lúc start;
  code kiểm và đổi **tại chỗ** (cùng vị trí).

## Key Insights
- Căn theo vị trí: `state.topics[i]` ↔ `flat_topics(plan)[i]` (`turn_engine:100-104`, `state_update:63-65,75`,
  `early_stop:28`). Thay tại chỗ giữ căn chỉnh; chèn thì vỡ. Đổi 1:1 → `topic_budget_s` không đổi.
- `/api/next-turn` không trả plan (`main.py:243-247`); `NextTurnRequest` không có `jd_profile` (`models_interview.py:150-165`)
  → reserve và id topic JD ưu tiên phải lưu trong plan lúc start. `FinalizeRequest` có cả `plan` và `state` (`:240-249`).
- Id dự phòng không dùng tiền tố `r` (trùng id yêu cầu JD `models_jd.py:10` và resource `report_resources.py:39`); topic
  plan là `t{n}` (`mock_planner.py:133-135`) → dùng `alt{n}`.
- Pool mỏng: fresher dư 0–1 topic (python fresher 5 topic / 4 slot) → reserve = tối đa 2, có thể 0 → tắt replan cho phiên.
- Topic chưa hỏi đã không tính điểm (`report_scoring:77-131` chỉ tính topic có lượt chấm) → **không cần** status `skipped`:
  topic bị bỏ biến mất khỏi danh sách thực tế.
- `plan_validator` không cần sửa (chỉ Planner gọi, trước khi có reserve).

## Requirements
- F: start chọn reserve bằng code: `catalog.topics_for(level)` chưa có trong plan, có câu kho (`bank_count`), xếp theo
  `_rank` CV/JD (`mock_planner.py`); dựng bằng `catalog_topic(f"alt{i}", ...)`; gắn snippet + bank question trong cùng
  `attach_reference_snippets` (hạn 5 s chung).
- F: `InterviewPlan.replan: Optional[ReplanPool] = None` với `reserve: List[PlanTopic]`, `keep_ids: List[str]` (id topic plan
  ứng với `jd.priority_topic_ids()`, tính lúc start). `CandidateState.swaps: List[Swap] = []` (`drop, add, turn, reason`).
- F: `effective_plan(plan, state)` thay topic theo `swaps` tại đúng vị trí; gọi **một lần ở mỗi entry point** (next-turn,
  finalize, sim) → mọi reader phía sau thấy plan thực tế, không phải sửa từng reader.
- F: V10 output = V9 + `swap: {drop, add, reason}|null`; prompt `evaluator.v10.md`. Chọn v10 **cố định cả phiên** khi
  `POLICY_MODE=hybrid` ∧ `REPLAN_ENABLED` (env, không đổi giữa lượt → không đổi prompt chấm giữa phiên, giữ prompt cache;
  `get_evaluator()` không thấy plan/state, M5). `swap=null` khi không áp dụng. Khối context (topic technical pending (id,
  title), reserve chưa dùng, band topic xong) chỉ render khi ở ranh giới có reserve, đặt cuối user message.
- F: `swap.reason` qua `safe_focus` + PII; `drop/add` chỉ nhận id trong whitelist.
- F: `validate_swap` (dưới). Không hợp lệ → bỏ qua, ghi lý do. Plan/state cũ (không `replan`/`swaps`) chạy như cũ.
- NF: `/api/start` P95 tăng ≤ 0,5 s.

## Architecture
```python
# app/replan.py
def effective_plan(plan, state) -> InterviewPlan:
    if not state.swaps or plan.replan is None: return plan
    reserve = {t.id: t for t in plan.replan.reserve}
    phases = []
    for ph in plan.phases:
        topics = list(ph.topics)
        if ph.phase == "technical":
            for s in state.swaps:
                i = next((k for k, t in enumerate(topics) if t.id == s.drop), None)
                if i is not None and s.add in reserve: topics[i] = reserve[s.add]
        phases.append(ph.model_copy(update={"topics": topics}))
    return plan.model_copy(update={"phases": phases})

def validate_swap(p, state, plan, pos, topics, phase, action, time_hint, max_swaps) -> Optional[str]:  # None = ok
    if p is None or action != "next_topic" or phase != "technical": return "not_applicable"
    if plan.replan is None or len(state.swaps) >= max_swaps or time_hint == "hurry": return "budget"
    i = index_of(topics, p.drop)
    if i is None or i <= pos or topics[i][0] != "technical" or state.topics[i].status != "pending": return "bad_drop"
    if p.drop in plan.replan.keep_ids: return "jd_priority"
    if p.add not in {t.id for t in plan.replan.reserve} or p.add in {s.add for s in state.swaps}: return "bad_add"
    return None

def apply_swap(state, p, i, turn):   # gọi TRƯỚC apply_action; sau đó topics = flat_topics(effective_plan(plan, state))
    state.swaps.append(Swap(drop=p.drop, add=p.add, turn=turn, reason=safe_focus(p.reason) or ""))
    state.topics[i] = TopicState(id=p.add)       # pending, cùng vị trí
```
Entry points: `turn_engine.next_turn` đầu hàm `plan = effective_plan(req.plan, req.state)` (bao `:138` `flat_topics`,
`:212` `_time_hint`; `:96` thuộc `start_session`, không cần),
`time_budget`, `early_stop`, `apply_action`); `main.finalize` `req = req.model_copy(update={"plan": effective_plan(req.plan, req.state)})`
(bao `report_scoring:82,100`, `requirements_coverage:20`, `report_resources:26`, `reporter.py:71`);
`evals/simulate_session.py:47` (`_topic`) dùng `effective_plan(plan, state)` với state mới nhất; `sim_metrics` kiểm lại.
Plan trả về client từ next-turn vẫn là plan gốc (không đổi contract), swap đi trong state.

## Related Code Files
- Create: `app/replan.py` (effective_plan, validate_swap, apply_swap, `replan_enabled()`), `app/replan_reserve.py`
  (chọn reserve lúc start), `app/models_replan.py` (`ReplanPool`, `Swap`), `app/prompts/evaluator.v10.md`,
  `tests/test_replan.py`, `tests/test_replan_reserve.py`, `tests/test_replan_entry_points.py`.
- Modify: `app/models_interview.py:65-68` (`InterviewPlan.replan`), `:97-118` (`CandidateState.swaps`),
  `app/turn_engine.py` (start `:90-95` gọi reserve trước `attach_reference_snippets`; next_turn đầu hàm), `app/turn_decision.py`
  (validate/apply swap khi `next_topic`), `app/plan_snippets.py:156-189` (gồm `plan.replan.reserve` trong danh sách `:163`),
  `app/main.py:252-266` (finalize effective_plan), `app/agents/evaluator_output_models.py` (V10, `uses_replan`),
  `app/agents/evaluator.py` (context reserve), `app/agents/evaluator_provider.py` (chọn v10), `evals/simulate_session.py:47`,
  `evals/sim_metrics.py` (`swap_rate`, độ phủ JD), `evals/simulate.py` (`--personas skewed`), `.env.example`.
- Delete: không.

## Implementation Steps
0. **Gate FSD** (M9), hỏi 3 câu: (a) interview-service lưu nguyên JSON `plan`/`state` (không lọc schema)? (b) có tra
   `turn.topic_id` (giờ có thể là `alt1`) theo plan đã lưu không — `alt*` không có trong `plan.phases`, chỉ trong
   `plan.replan.reserve`? (c) UI có hiển thị danh sách topic từ plan (topic bị bỏ hiện ra mà không hỏi)? Chưa có → dừng ở bước 3.
1. Models (`ReplanPool`, `Swap`, field mặc định rỗng) + test nạp plan/state cũ.
2. `effective_plan` + test entry points: swap → next_turn, time_budget, early_stop, report_scoring, requirements_coverage,
   report_resources, reporter, simulate_session đều thấy `alt1` ở vị trí topic bị bỏ; plan/state cũ y nguyên.
3. `replan_reserve.select_reserve(plan, catalog, level, coverage, cv, jd)` (0–2 topic, id `alt{n}`), `keep_ids`; start gắn snippet;
   chỉ khi `replan_enabled()` (tắt → plan không có `replan`, output start y cũ).
4. V10 + prompt + context; `validate_swap`/`apply_swap` trong `choose_decision` khi `next_topic` (sau `low_performance_stop`:
   nếu dừng sớm thì không đổi).
5. Test: pool 0 (fresher) → không đề xuất; drop là JD priority/intro/scenario/đã done/topic hiện tại → bác; vượt max; hurry;
   add đã dùng; id `alt` không trùng `r*`/`t*`; reason injection bị lọc.
6. Eval (H7, chọn **fixture JD trong sim** thay vì test kịch bản: gate là chất lượng quyết định của LLM nên phải đo đầu-cuối;
   bất biến "không bỏ topic JD ưu tiên" đã có unit test ở bước 5): persona `skewed` gửi JD/CV ở start + JD ở finalize (01);
   `swap_rate`, độ phủ JD (`requirements_block`), số topic có điểm; assert sim: không swap nào có `drop ∈ keep_ids`.
7. **[BLOCKED-KEY]** gate v10 vs v8 (golden/holdout/sourced); sim `skewed` + full matrix, hybrid ± REPLAN, `--runs 3`; đo `/api/start` P95. Báo cáo
   `plans/reports/eval-<date>-replan.md`.
8. Docs: `03` (swap ở ranh giới topic), `04` (`swaps`, reserve), `06` (`plan.replan`, `state.swaps`, báo FSD), `02` (v10);
   context. PR `[ai-service] feat: lập lại kế hoạch giữa buổi sau cờ REPLAN_ENABLED`.

## Todo List
- [ ] [FSD] xác nhận lưu nguyên plan/state (3 câu hỏi + khóa mặc định ghi ở 06 §7.4; **chưa có trả lời, cờ giữ tắt**)
- [x] Models + tương thích ngược
- [x] effective_plan + test mọi entry point/reader (next_turn, finalize/report, sim; time_budget/early_stop/scoring đọc plan thực tế qua căn chỉnh vị trí)
- [x] Reserve lúc start + keep_ids
- [x] V10 + validate/apply swap
- [x] Test ràng buộc
- [x] Eval skewed (sim `replan`, bất biến `jd_priority_violations = 0`); [ ] **[BLOCKED-KEY]** sim + gate v10 vs v8 + start P95
- [x] Docs 02/03/04/06/09 + context + `.env.example`; [ ] PR (chưa tạo: không push theo yêu cầu)

## Deviations (ghi khi triển khai, 2026-11-14)
- `ReplanPool` và `Swap` nằm trong `models_interview.py`, không có `models_replan.py`: `ReplanPool` chứa `PlanTopic` nên tách file gây import vòng; file đạt 200 dòng.
- Thêm `TurnInfo.swap_result` (nhãn bounded) để sim/debug thấy đề xuất bị bác; không có trong spec gốc, cùng nhóm khóa mặc định báo FSD.
- Chỉ số sim ở `evals/sim_replan_metrics.py` (không thêm vào `sim_metrics.py` 189 dòng); `simulate.py` thoát mã 1 nếu `jd_priority_violations > 0`. `--personas skewed` thực tế là `--matrix skewed` (phase 01 đã có), không thêm cờ.
- `effective_plan` trong `next_turn` là plan nội bộ; `TurnResult.plan` cũng là plan thực tế nhưng route next-turn không trả plan nên client không thấy khác.
- Reserve: khi chưa biết số câu kho (số đếm rỗng: RAG tắt, quá hạn 1 s) thì không lọc theo kho (spec yêu cầu có câu kho khi biết). `replan_context.current_topic_band` là band topic hiện tại **trước** câu trả lời này (không phải topic vừa xong).
- `time_hint` cho `validate_swap` tính theo phase `technical`; `apply_swap` chạy trong `choose_decision` (sau `low_performance_stop`), `turn_engine` tính lại `topics` khi `swap_result == applied`. Lượt có `swap` null hay cờ tắt không đụng state.
- Chuyển `hint_source` từ `turn_engine.py` sang `turn_evaluation.py` để `turn_engine.py` < 200 dòng.
- Ghi đè `EVALUATOR_PROMPT_VERSION` kèm `REPLAN_ENABLED` (v < 10) chỉ log cảnh báo `policy_prompt_mismatch`, không chặn.

## Success Criteria (reply mục 8)
- v10 vs v8 (H2): band agreement golden + holdout (`run_evaluator --prompt v10 --policy-context default --runs 3`) không
  giảm; `run_evaluator_sourced` id sai không tăng.
- Độ phủ yêu cầu JD không giảm so với tắt cờ; persona `skewed`: số topic có điểm không giảm; 0 swap bỏ topic JD ưu tiên.
- `/api/start` P95 tăng ≤ **0,5 s**.
- Plan/state cũ chạy được (test); FSD xác nhận bằng văn bản (link trong PR).
- Cờ tắt: quyết định và giá trị y cũ; JSON chỉ thêm khóa mặc định (`plan.replan: null`, `state.swaps: []`), báo FSD cùng 04 (M6).

## Risk Assessment
- interview-service lọc field lạ → swap mất giữa lượt → gate FSD; thêm test round-trip JSON.
- Reserve thêm truy hồi lúc start → cùng hạn 5 s, chạy song song; đo P95.
- LLM đổi topic làm lệch công bằng giữa ứng viên → max 1 swap, không đụng JD priority, chỉ technical.

## Security Considerations
- `reason` từ LLM qua `safe_focus`; `drop/add` chỉ nhận id trong whitelist (plan + reserve).
- Không mở rộng phạm vi: reserve chỉ từ catalog track/level.

## Next Steps
- 06 quyết `REPLAN_ENABLED`; nếu không đạt mốc, giữ tắt và ghi lý do trong `context/decisions.md`.
