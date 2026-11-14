# Phase 07 (tùy chọn): Ghi chú của agent trong state (hạng mục 4)

## Context Links
- Đề xuất mục 8; reply mục 8 (dòng ghi chú); code map mục "4. Ghi chú"; audit H2
- `app/models_interview.py:97-118` (`CandidateState`), `app/state_update.py:19`, `app/agents/interviewer.py:43-48`,
  `app/cv_text.py:86,101`, phase 04 (V9, `PolicyContext`, `choose_decision`)

## Overview
- Priority: P3, **tùy chọn**. Status: optional. Nhánh: `thang/agent-notes`. Effort 1d.
- Chỉ bắt đầu khi phase 04 đã đo và `hybrid` đạt mốc (lead quyết định, audit H2). Cờ `AGENT_NOTES_ENABLED=false`,
  chỉ có tác dụng khi `POLICY_MODE=hybrid`.
- Lý do hoãn: người dùng duy nhất của ghi chú là chính lời gọi Evaluator vừa chấm điểm (Reporter/Interviewer không đọc) →
  ghi chú kiểu `risk: yếu X` có thể neo điểm; chưa có giá trị đo được cho tới khi hybrid chứng minh có ích.

## Key Insights
- `strengths`/`gaps` là tag code sinh (≤ 10, `state_update.py:19`); `covered`, `focus_used` sống trong 1 topic. Chưa có nhận
  định xuyên topic.
- Thêm `notes: List[Note] = []` vào `CandidateState` → state cũ nạp được; JSON thêm khóa `notes: []` (báo FSD).
- `has_injection` (`cv_text.py:101`) có thể bỏ nhầm ghi chú kỹ thuật (mẫu "```", `you are`) → chấp nhận, đếm metric.

## Requirements
- F: `new_note: {kind, text}|null`, `note_updates: [{id, status}]` vào **version prompt mới** (số kế tiếp, vd `v11` nếu 05
  đã dùng v10; gồm cả `swap` để 1 phiên chỉ 1 version), lớp output mới; chọn cố định cả phiên khi `AGENT_NOTES_ENABLED` ∧
  hybrid. Giữ quy tắc "field mới → lớp mới, cổng theo version"; v9/v10 không đổi.
- F: `Note(id, turn, topic_id, kind: hypothesis|to_verify|strength|risk, text ≤ 150, status: open|confirmed|rejected)`; ≤ 8;
  đầy → bỏ `confirmed/rejected` cũ nhất, không có thì bỏ note mới; 0–1 note mới mỗi lượt.
- F: **chỉ ghi chú `to_verify` đang `open`** được đưa lại vào context Evaluator (giảm neo điểm, audit H2); `strength`/`risk` chỉ lưu.
- F: `safe_note` = gộp khoảng trắng, cắt 150, `has_injection` → bỏ, PII (`redact_pii` khác bản gốc) → bỏ.
- F: không dùng ghi chú để tính điểm, không đưa vào Interviewer/Reporter.

## Architecture
```python
# app/models_agent_notes.py (re-export qua models_interview)
class Note(BaseModel): id: str; turn: int; topic_id: Optional[str]; kind: Literal[...]; text: str; status: Literal[...] = "open"
# app/agent_notes.py
def apply_notes(state, raw, turn, topic_id) -> None   # gọi trong next_turn sau record_evaluation, chỉ khi cờ bật
def notes_for_context(state) -> List[Note]            # chỉ to_verify + open
```

## Related Code Files
- Create: `app/models_agent_notes.py`, `app/agent_notes.py`, `app/prompts/evaluator.v11.md` (hoặc số kế tiếp),
  `tests/test_agent_notes.py`.
- Modify: `app/models_interview.py:97-118`, `app/agents/evaluator_output_models.py`, `app/agents/evaluator.py` (context),
  `app/agents/evaluator_provider.py` (chọn version), `app/turn_engine.py`, `evals/sim_metrics.py` (`to_verify` được xác nhận/bác),
  `tests/test_prompt_injection_agentic_guards.py`, `.env.example`.
- Delete: không.

## Implementation Steps
1. Model + `safe_note` + `apply_notes` + `notes_for_context`.
2. Version prompt mới + lớp output + chọn version.
3. Test: state cũ không `notes`; 9 note; note chứa lệnh chèn / email / sđt; update id lạ; context chỉ có `to_verify`.
4. **[BLOCKED-KEY]** gate chấm: version mới vs v8 golden/holdout/sourced; sim hybrid ± notes `--runs 3` (gap, stdev gộp);
   đọc tay 20 phiên.
5. Docs `04` (`notes`), `06` (khóa `state.notes`, báo FSD), `09`; context. PR `[ai-service] feat: ghi chú agent sau cờ AGENT_NOTES_ENABLED`.

## Todo List
- [ ] Chờ quyết định sau phase 04
- [ ] Model + apply/safe/context
- [ ] Prompt version + lớp output
- [ ] Test
- [ ] [BLOCKED-KEY] gate + đọc tay 20 phiên
- [ ] Docs + FSD, PR

## Success Criteria
- ≥ **85%** ghi chú đúng hội thoại (20 phiên đọc tay); 0 ghi chú chứa thông tin cá nhân.
- Band golden/holdout không giảm vs v8; gap strong−weak và stdev gộp không xấu hơn hybrid không notes.
- Tỷ lệ `to_verify` được xác nhận/bác ở lượt sau được báo cáo.

## Risk Assessment
- Neo điểm → chỉ `to_verify` vào context + gate chấm điểm.
- Bỏ nhầm do lọc injection → metric `notes_dropped_total{reason}`.

## Security Considerations
- Ghi chú sinh từ câu trả lời không tin cậy: injection + PII filter; chỉ nhận định năng lực kỹ thuật.

## Next Steps
- Nếu không đạt mốc: giữ tắt, ghi lý do trong `context/decisions.md`.
