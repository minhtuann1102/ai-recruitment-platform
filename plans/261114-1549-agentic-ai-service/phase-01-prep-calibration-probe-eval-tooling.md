# Phase 01: Chuẩn bị (probe live, hiệu chỉnh ngưỡng, sửa mốc, eval tooling, scenario `System Design`)

## Context Links
- Reply mục 2, 5, 7, 8; code map mục "Đề xuất sai", "Đo"; research (7 câu hỏi live); audit H5, H6, H7, M7, M10, L3
- `context/workflow.md`, `context/decisions.md`

## Overview
- Priority: P1 (chặn 04). Status: code xong, bước live [BLOCKED-KEY]. Nhánh: `thang/agentic-prep`. Effort 2d.
- Việc nền không đổi hành vi (trừ ngưỡng, cần owner duyệt) để các phase sau có số và công cụ đo đúng.

## Key Insights
- `WEAK_BELOW = 1.5`, `STRONG_FROM = 3.0` (`policy.py:10-11`) "giả định mock"; `STRONG_BAND, WEAK_BAND`
  (`state_update.py:7`) cùng giá trị, dùng cho momentum. Hàm kiểm ở 04 so với `decide()` → ngưỡng sai thì đồng ý vô nghĩa.
- Docstring `plan_bank_coverage.py:3-4` còn 0,63/0,88; đúng 0,53/0,71 (judge_support v2, ±0,04 → 3 lần).
- `--runs`: metrics tra `personas[pid]` theo khóa session (`sim_metrics.py:35,40,50,66,82,96,113-114`); `run_session`
  dùng `sid = f"sim-{persona.id}"` (`simulate_session.py:51`); `attach_documents` dựng lại `sim-{pid}`
  (`turn_source_recorder.py:54`), khóa recorder `(sid, turn_number)` (`:17,36`) → chạy N lần cùng persona sẽ đè nhau.
- Stdev mỗi persona với n=3 (df=2) không đủ để so 1,2×; simulator temp 0,8 (`llm/settings.py:29`) → phần lớn nhiễu do
  simulator → dùng stdev gộp giữa persona (df ≈ 2 × số persona) + CI bootstrap.
- Sim không gửi `jd_profile`/`cv_profile` ở start (`simulate_session.py:52-53`) và finalize (`:89-92`) → `requirements_block`
  None (`requirements_coverage.py:17-18`) → gate độ phủ JD ở 05 cần fixture JD.
- Scenario: `_filters` (`turn_reference_snippets.py:50-55`) và start `plan_snippets.py:126-128` (scenario, dùng
  `main_category` `:116`) chỉ lấy 1 category (= `Backend` với java/nodejs); docs `System Design` không bao giờ được tìm.
  `category` đơn đi qua `rag/retriever.py:110,127,135,152-156` (`retrieve_for_topic`, `plan_snippets`) vào
  `SearchFilters` (`rag/models.py:27-31`) → BM25 `rag/bm25_index.py:47`, SQL `rag/repository.py:85-87`. Chỉ có tác dụng
  khi `RAG_TEXTBOOK_ENABLED=true` (mặc định tắt).
- Probe: reply nói "script sẵn sàng" nhưng `scripts/` chỉ có `check_docs.py`, `smoke_llm.py` → commit script.

## Requirements
- F: `--runs N`: mỗi run sid riêng `sim-{pid}-r{i}`; kết quả `sessions_by_run: List[Dict[pid, session]]`; hàm metric cũ
  chạy nguyên trên từng run; `sim_runs.py` gộp. `--runs 1` → định dạng output cũ.
- F: `sim_runs.pooled_stdev(sessions_by_run)` (công thức plan.md mục 8) + CI bootstrap 95% (lấy mẫu persona, 1000 lần);
  `strong_weak_gap` mean + CI.
- F: metric `end_reasons` (phân bố + tỷ lệ "đúng lý do": weak → `low_performance` hợp lệ; strong/average → hết topic/thời gian).
- F: persona `skewed` (mạnh 1 category, yếu category khác) **kèm fixture JD + CV** (yêu cầu `must` trỏ topic category yếu
  và mạnh); `run_session` gửi `jd_profile`/`cv_profile` ở start và `jd_profile` ở finalize khi persona có.
- F: scenario nhận thêm `System Design` (turn + start, BM25 + vector SQL).
- F: probe `scripts/probe_tool_strict_json.py` trả lời 7 câu hỏi research; ghi provider có/không `require_parameters` (L3).
- NF: không đổi hành vi mặc định trừ ngưỡng (PR riêng nếu owner duyệt).

## Architecture
- `SearchFilters`: giữ `category: Optional[str]`, thêm `categories: Tuple[str, ...] = ()`; helper
  `category_matches(filters, cat)` (BM25) và SQL `category = ANY(%s)` khi có `categories`. `Retriever.retrieve_for_topic`/
  `plan_snippets` thêm kwarg `categories=()` (giữ `category`). `scenario_categories(catalog)` trong `plan_snippets.py`.
- Hiệu chỉnh ngưỡng (tránh overfit, M10): sim `--runs 4` chia tập **A** (run 1–2, chỉnh) và **B** (run 3–4, kiểm). Trên A:
  histogram `turn_score` theo quality; ứng viên ngưỡng = điểm tách lân cận. Đối chiếu thêm band đã gán nhãn của golden
  (`evals/evaluator_golden*.jsonl` + `evaluator_labels/`). Trên B: gap strong−weak, end_reason, phân bố hành động không xấu
  hơn ngưỡng cũ. Số ghi "tạm thời, đo <ngày>".

## Related Code Files
- Modify: `app/rag/models.py:27-31`, `app/rag/bm25_index.py:47`, `app/rag/repository.py:85-87`,
  `app/rag/retriever.py:110,127,135,152-156`, `app/plan_snippets.py:116,126-128`, `app/turn_reference_snippets.py:50-55`,
  `app/plan_bank_coverage.py:3-4`, `evals/simulate.py:97,109-116`, `evals/simulate_session.py:51-53,89-92`,
  `evals/turn_source_recorder.py:54` (`attach_documents(sessions, seen, run)`), `evals/sim_metrics.py` (`end_reasons`),
  `evals/personas.py` (`build_skewed`, field `jd_profile`, `cv_profile` tùy chọn), `app/policy.py:10-11` +
  `app/state_update.py:7` (chỉ khi owner duyệt).
- Create: `scripts/probe_tool_strict_json.py`, `evals/sim_runs.py`, `evals/fixtures/skewed_jd_profiles.json`,
  `tests/test_scenario_categories.py`, `tests/test_sim_runs.py`.
- Delete: không.

## Implementation Steps
1. Docstring `plan_bank_coverage.py:3-4`: "0,53 / 0,71 (judge_support v2, hiệu chỉnh với LLM thứ hai, 3 lần)".
2. `categories` + `scenario_categories`; test: textbook `System Design` được tìm ở scenario java (BM25 + SQL 1 phần tử =
   SQL cũ); technical không đổi.
3. `--runs`: `run_session(..., run=i)` → sid `sim-{pid}-r{i}`; `attach_documents(..., run=i)`; `sim_runs.py`
   (`pooled_stdev`, `bootstrap_ci`, `strong_weak_gap`). Test: 2 run cùng persona không đè tài liệu; metric cũ không đổi khi `--runs 1`.
4. `end_reasons`; persona `skewed` + fixture JD/CV; `run_session` gửi JD/CV. Test: finalize của persona skewed có `requirements`.
5. Probe script (đọc `LLM_API_KEY`, `LLM_BASE_URL`; không in khóa).
6. **[BLOCKED-KEY]** Probe → `plans/reports/probe-<date>-tool-strict-json.md`. Combo lỗi 404/400 → ghi lại; 03 vẫn chạy với
   latch "không hỗ trợ" (lượt chấm như cũ) và mở lại thiết kế (không làm split mode trước).
7. **[BLOCKED-KEY]** Baseline (`rules`): `simulate.py --matrix full --simulator llm --runs 4` → stdev gộp, gap (mốc 3,74),
   end_reason; TTFT (`ttft_breakdown.py`); `judge_support` 3 lần (AI vs kho).
8. **[BLOCKED-KEY]** Hiệu chỉnh trên A, kiểm trên B; owner duyệt → sửa ngưỡng, comment "đo <ngày>, tạm thời".
9. Docs: `09` (`--runs`, stdev gộp, end_reason, persona skewed + JD), `04` (ngưỡng nếu đổi), RAG theo lượt (scenario
   category), `context/project-state.md`; check_docs, pytest. PR `[ai-service] chore: chuẩn bị đo cho agentic`.

## Todo List
- [x] Docstring mốc
- [x] `categories` (BM25, SQL, retriever) + test (`tests/test_scenario_categories.py`)
- [x] `--runs` id riêng + `sim_runs.py` + test (`tests/test_sim_runs.py`)
- [x] `end_reasons`, persona skewed + JD/CV fixture
- [x] Probe script (`scripts/probe_tool_strict_json.py`, test bằng transport giả)
- [ ] [BLOCKED-KEY] probe live -> `plans/reports/probe-<date>-tool-strict-json.md`
- [ ] [BLOCKED-KEY] baseline `rules`: `simulate.py --matrix full --simulator llm --runs 4` (stdev gộp, gap, end_reason), TTFT, `judge_support` 3 lần
- [ ] [BLOCKED-KEY] hiệu chỉnh `WEAK_BELOW`/`STRONG_FROM` trên A, kiểm trên B; owner duyệt (giữ 1.5 / 3.0 đến lúc đó)
- [x] Docs + context (09, rag-design, project-state); `04` không đổi vì ngưỡng chưa đổi
- [ ] PR `[ai-service] chore: chuẩn bị đo cho agentic` (chưa push theo yêu cầu)

## Success Criteria
- Test cũ xanh; `--runs 1` cùng định dạng cũ; 2 run cùng persona tách biệt.
- Probe trả lời đủ 7 câu hỏi (provider, combo, `tool_choice=none`+schema, `maxLength`, cached, parallel).
- Baseline có: stdev gộp + CI, gap strong−weak + CI, TTFT P50/P95, `supported` AI/kho.
- Ngưỡng mới (nếu đổi): trên tập B gap không giảm > 10% so với 3,74.

## Risk Assessment
- Khóa chưa gia hạn → 02, 03 code vẫn làm; 04 không bật được trước khi có ngưỡng.
- Đổi ngưỡng = đổi hành vi mặc định → PR riêng, sim trước/sau trên tập B.
- `ANY(%s)` đổi SQL: test 1 phần tử ra kết quả như cũ.

## Security Considerations
- Probe đọc khóa từ env, không in/commit. Fixture JD/CV giả, không dữ liệu thật.

## Next Steps
- 04 dùng ngưỡng + `sim_runs`; 05 dùng persona skewed + JD; báo DE: scenario đã nhận `System Design`.
