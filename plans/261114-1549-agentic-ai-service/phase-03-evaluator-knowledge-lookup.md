# Phase 03: Evaluator tự tra cứu (hạng mục 1)

## Context Links
- Đề xuất mục 5; reply mục 1, 4, 5, 8; code map mục "1. Evaluator tự tra cứu", "Đo"; audit H1, H3, H4, M4, M8, L4, L5
- `app/turn_evaluation.py:50-71`, `app/agents/evaluator.py:46-120,139-234`, `app/evaluator_source_checks.py:24-70`,
  `app/turn_reference_snippets.py:27-123`, `app/prompts/evaluator.v8.md:29,41`, `app/prompts/store.py:28-52`,
  `evals/turn_source_recorder.py:31-37`, `evals/run_evaluator.py:31-45`, `evals/run_evaluator_sourced.py:62-66`,
  `evals/ttft_breakdown.py:25,39-40`, `docs/ai-service/06-api-contract.md:302`

## Overview
- Priority: P2. Status: code + test xong (cờ tắt); đo thật [BLOCKED-KEY]. Nhánh: `thang/evaluator-lookup`. Effort 2d. Cờ `EVALUATOR_TOOLS=false`,
  `EVALUATOR_MAX_TOOL_CALLS=1` (trần cứng 2), `EVALUATOR_TOOL_DEADLINE_S=2.0`.
- Lượt không có `R` (không intro): Evaluator được gọi `search_knowledge(query)`; code cố định phạm vi tìm.

## Key Insights
- Gate là `not inp.reference_answer` (có qa_id mà lấy đáp án lỗi thì R rỗng, `turn_engine.py:162`).
- `_search` < 20 ms chỉ khi `memory_only=True`; độ khó áp trong `_search:85-86`; `_known` chỉ lọc chuỗi truyền vào. Lookup
  tôn trọng cờ RAG theo lượt hiện có (`turn_reference_snippets.py:104`: hybrid + `turn_retrieval`).
- Id theo vị trí: `source_blocks` (`evaluator_source_checks.py:24-27`) = `S1..Sn` từ `all_snippets(inp)` (`evaluator.py:109-111`)
  rồi `R`. Nối chunk công cụ vào **cuối** `turn_snippets`/`turn_sources` → `S{n+1}..`; `postcheck`, `check_sources`,
  `cited_sources`, `source_refs` chạy nguyên; Reporter lấy `Evaluation.sources`. Lookup chỉ khi không R → không lệch R.
- **"Chỉ R bác" chưa được ép cho misconception LLM tự viết** (H4): code chỉ bác bằng R (`:57-61`), nhưng v8 bảo LLM ghi
  `misconceptions` cho mọi `contradicted` (`evaluator.v8.md:41`) và mọi misconception chặn `technical_accuracy`
  (`evaluator.py:172-173`, luật 4 `evaluator.v8.md:29`). Chunk công cụ do truy vấn bị câu trả lời lái → tăng rủi ro phạt oan.
- Ngân sách (H1): lần đầu của mỗi `complete` mới được đủ 8 s; vòng lặp + fallback cũ ≈ 18–20 s > first event 15 s
  (`06-api-contract.md:302`). Hiện tại worst ≈ 10–11 s.
- `CallRecord` chỉ ghi khi thành công (`gateway.py:124-125`) → vòng lặp lỗi mất latency (M4).
- `_RecordingEvaluator` (`turn_source_recorder.py:31-37`) chụp `inp` trước vòng lặp. `run_evaluator`/`_sourced` dựng
  `EvaluationInput` không có lookup (`run_evaluator.py:31-36,45`) → gate golden vô nghĩa nếu không thêm `--lookup` (H3).
  Golden 51 + holdout 24 mẫu đều không có R, không `catalog_ref` → category None (rộng hơn prod; ghi rõ là xấp xỉ).
- `evaluator.py` 234 dòng → tách trước.

## Requirements
- F: gate = cờ ∧ agent LLM ∧ `not key` ∧ `phase != "intro"` ∧ `filters_for_turn(...)` không None ∧ BM25 nạp ∧ `turn_retrieval`
  ∧ latch `tools_supported` ∧ `precheck_answer` không chặn.
- F: tool `search_knowledge(query)` strict; category/source_types/độ khó/topic do code; `memory_only=True`; ≤ 3 chunk/≤ 600 token
  mỗi lần; bỏ trùng; bọc `wrap_untrusted`; query cắt 200 (02) và `has_injection(query)` → `"error: invalid_query"` (M8).
- F: luật tra cứu ở fragment `evaluator_tools.v1.md`, nối vào system prompt chỉ khi lượt có tools. Version fragment ghi vào
  trace Langfuse + log, **không** nhét vào `prompt_version` (`uses_sources` parse số, `evaluator.py:67`) (L4).
- F: **1 ngân sách đồng hồ** `B = retry_budget_s` (10 s) từ `t0` đầu `evaluate_with_raw` cho vòng lặp + fallback:
  `asyncio.wait_for(complete_with_tools(..., budget_started=t0, budget_s=B, failure_fallback="evaluator_lookup_fallback"), B − elapsed)`; lỗi → nếu còn ≥ `MIN_FALLBACK_S`
  (2,5 s) thì 1 lần gọi không tools với `budget_started=t0` (cắt cả lần đầu), không thì thẳng `mock_evaluator` + `degraded`.
  Worst case trước sự kiện `meta`: RAG theo lượt ≤ 1,0 s (`TURN_DEADLINE_S`) + Evaluator ≤ 10 s + mock ≈ **≤ 11,5 s** < 15 s.
- F: ép "chỉ R bác" ở lượt có chunk công cụ (H4): trong `postcheck`, khi `inp.tool_base_ids is not None`:
  (a) bỏ misconception LLM khớp (`SequenceMatcher ≥ 0,8` hoặc chứa, như `merge_misconceptions`) `point`/`quote` của điểm
  `contradicted` mà mọi id hợp lệ là id công cụ (> `tool_base_ids`) — chỉ những misconception này không chặn
  `technical_accuracy` (vẫn trả về cho báo cáo); (b) misconception khác (không gắn nguồn, hoặc dựa snippet có sẵn)
  chặn như khi tắt cờ. Mục tiêu: bật cờ không làm điểm cao hơn so với tắt cờ ở cùng câu trả lời, ngoài phần do chunk công cụ.
- F: vòng lặp lỗi → truyền `failure_fallback="evaluator_lookup_fallback"` cho `complete_with_tools`, gateway đã tự thêm `CallRecord` kèm latency (M4); caller KHÔNG thêm record thứ hai; thêm vào
  `FALLBACK_KINDS`; báo FSD mã fallback mới.
- NF: cờ tắt → request Evaluator byte-identical; postcheck không đổi khi `tool_base_ids is None`.

## Architecture
```
evaluate_turn → lookup = TurnLookup.build(...) if gate else None → evaluator.evaluate(EvaluationInput(..., lookup=lookup))
LlmEvaluator.evaluate_with_raw (t0)
  if inp.lookup: result, inp = await call_with_lookup(gw, prompt, inp, t0)   # agents/evaluator_lookup_call.py
  else:          result = await gateway.complete(...)                           # như cũ
  ev = postcheck(result.data, inp)        # inp đã nối chunk + tool_base_ids khi lookup thành công
```
```python
@dataclass
class TurnLookup:                                   # app/evaluator_lookup.py
    search: Callable[[str, Sequence[str]], Awaitable[List[Chunk]]]   # closure search_turn(..., memory_only=True)
    known_base: List[str]; base_ids: int            # len(all_snippets(inp))
    texts: List[str] = ...; sources: List[SourceRef] = ...; queries: List[str] = ...; committed: bool = False

    async def run_tool(self, name, args) -> str:
        if name != "search_knowledge": return "error: unknown_tool"
        q = args["query"]
        if has_injection(q): return "error: invalid_query"
        if q.casefold() in map(str.casefold, self.queries): return "error: duplicate_query"
        self.queries.append(q)
        chunks = await self.search(q, [*self.known_base, *self.texts])
        if not chunks: return "Không tìm thấy tài liệu phù hợp."
        start = self.base_ids + len(self.texts) + 1
        self.texts += [c.content for c in chunks]; self.sources += [source_ref(c) for c in chunks]
        return format_blocks(start, chunks)          # cùng định dạng label()/wrap_untrusted như build_messages

    def extend(self, inp): return replace(inp, turn_snippets=[*inp.turn_snippets, *self.texts],
                                          turn_sources=[*inp.turn_sources, *self.sources], tool_base_ids=self.base_ids)

async def call_with_lookup(gw, prompt, inp, t0):
    B = cfg.retry_budget_s
    try:
        r = await asyncio.wait_for(complete_with_tools(..., budget_started=t0, budget_s=B), B - (now() - t0))
        inp.lookup.committed = True
        return r, inp.lookup.extend(inp)
    except (LlmError, asyncio.TimeoutError) as err:
        # gateway đã thêm CallRecord(fallback="evaluator_lookup_fallback") qua failure_fallback; không thêm record thứ hai
        if B - (now() - t0) < MIN_FALLBACK_S: raise LlmTimeoutError("no_budget_for_fallback") from err  # → mock+degraded
        return await gw.complete(..., budget_started=t0, budget_s=B), inp
```

## Related Code Files
- Create: `app/evaluator_lookup.py`, `app/agents/evaluator_lookup_call.py`, `app/agents/evaluator_output_models.py` (dời
  `evaluator.py:46-67`, re-export), `app/prompts/evaluator_tools.v1.md`, `tests/test_evaluator_lookup.py`,
  `tests/test_evaluator_lookup_call.py`, `tests/test_evaluator_lookup_only_reference_refutes.py`.
- Modify: `app/agents/evaluator.py` (`EvaluationInput` `:70-85` + `lookup`, `tool_base_ids`; nhánh `:216-220`; postcheck
  `:146-173` luật H4), `app/evaluator_source_checks.py` (helper `tool_only_contradicted(contradicted, base_ids)`),
  `app/turn_evaluation.py:50-71`, `app/turn_reference_snippets.py` (public `filters_for_turn`, `search_turn`, alias tên cũ),
  `app/metrics.py` (`ai_evaluator_lookup_total{result=hit|empty|error|fallback|unsupported}`),
  `evals/turn_source_recorder.py:31-37` (đọc `inp.lookup` chỉ khi `committed`, L5), `evals/run_evaluator.py` +
  `run_evaluator_sourced.py` (`--lookup`: `TurnLookup` trên BM25 bộ nhớ qua `memory_retriever()` sau khi nạp corpus),
  `evals/sim_metrics.py` (`lookup_rate`, `empty_rate`, `misconception_rate`, `ta_le1_rate`), `evals/ttft_breakdown.py:25,39-40`
  (`FALLBACK_KINDS` + tách lượt tra cứu), `.env.example`.
- Delete: không.

## Implementation Steps
1. Refactor thuần: `evaluator_output_models.py`; pytest xanh; commit riêng.
2. `evaluator_lookup.py` + `evaluator_tools.v1.md` (luật: chỉ tra khi có khẳng định kỹ thuật cụ thể chưa có trong S; không
   tra cho "không biết", lạc đề, đã đủ; query ngắn, thuật ngữ, không chép câu ứng viên; ý dựa tài liệu tra cứu chỉ được
   `supported`/`no_source`, **không ghi misconception chỉ dựa tài liệu tra cứu**).
3. `call_with_lookup` (ngân sách chung, wait_for, fallback có điều kiện, CallRecord fallback).
4. Postcheck H4 + helper.
5. Gate trong `turn_evaluation.py`.
6. Test fake: cờ tắt → params y hệt; có R/intro/`turn_retrieval` tắt → không tools; tool 1 lần → id `S{n+1}` khớp postcheck,
   `Evaluation.sources` có chunk; trùng chunk/query; query injection; **fake LLM ghi misconception cho điểm contradicted chỉ
   dựa S công cụ → bị bỏ, `technical_accuracy` không bị chặn**; misconception không gắn nguồn ở lượt tra cứu → giữ trong
   danh sách, không chặn; loop chậm 9 s → không fallback, mock+degraded, tổng ≤ 10,5 s; loop lỗi sớm → fallback 1 call;
   `tools_unsupported` → đường cũ; recorder thấy chunk chỉ khi committed.
7. Eval tooling: `--lookup`, recorder, metric mới, TTFT tách.
8. **[BLOCKED-KEY]** Đo (cờ tắt vs bật, cùng commit/corpus): `judge_support` 3 lần tách AI/kho; `run_evaluator --set main` và
   `holdout --runs 3 --lookup`; `run_evaluator_sourced --lookup`; sim full `--serve --runs 2` + `ttft_breakdown`, `cost_latency`.
   Báo cáo `plans/reports/eval-<date>-evaluator-lookup.md`.
9. **[BLOCKED-KEY] + DE docs** lặp bước 8 cho scenario (`RAG_TEXTBOOK_ENABLED=true`).
10. Docs: `02` (Evaluator tra cứu, fragment, luật chỉ R bác ở lượt tra cứu), `05` (cap misconception), `06` (fallback
    `evaluator_lookup_fallback`, báo FSD), `08` (ngân sách, worst case 11,5 s), `09`; context. PR
    `[ai-service] feat: Evaluator tự tra cứu kho sau cờ EVALUATOR_TOOLS`.

## Todo List
- [x] Tách `evaluator_output_models.py` (+ `evaluator_input.py`: `evaluator.py` 234 -> 147 dòng; commit riêng)
- [x] TurnLookup + SEARCH_TOOL + fragment prompt (`app/evaluator_lookup.py`, `evaluator_tools.v1.md`)
- [x] call_with_lookup: 1 ngân sách, wait_for, fallback có điều kiện, CallRecord fallback (`agents/evaluator_lookup_call.py`)
- [x] Postcheck "chỉ R bác" ở lượt tra cứu (`split_tool_misconceptions`)
- [x] Gate turn_evaluation (`lookup_for_turn`); prompt Evaluator ghim `v8` (C1)
- [x] Test bước 6 (`test_evaluator_lookup*.py`: 937 passed, 8 skipped; ngân sách thu nhỏ 10 s -> 1,2 s cho test thời gian)
- [x] `--lookup`, recorder, metric, TTFT tách (`evals/lookup_support.py`, `sim_lookup_metrics.py`)
- [ ] [BLOCKED-KEY] đo (bước 8): judge_support 3 lần, `run_evaluator --set main` / `holdout --runs 3 --lookup`, `run_evaluator_sourced --lookup`, sim `--serve --runs 2`, `ttft_breakdown`, `cost_latency`; báo cáo `eval-<date>-evaluator-lookup.md`
- [ ] [BLOCKED-KEY] [DE] đo scenario (`RAG_TEXTBOOK_ENABLED=true`, chờ DE nạp textbook)
- [x] Docs 02/05/06/08/09 + context
- [ ] Báo FSD mã `evaluator_lookup_fallback`; PR `[ai-service] feat: Evaluator tự tra cứu kho sau cờ EVALUATOR_TOOLS` (chưa push)

## Success Criteria (reply mục 8)
- Độ đúng `supported` câu AI ≥ **0,65** (mốc 0,53), câu kho không giảm (0,71); TB 3 lần judge.
- `run_evaluator --lookup` golden + holdout: band agreement không giảm; `run_evaluator_sourced --lookup`: id sai không tăng.
- Tỷ lệ misconception và tỷ lệ `technical_accuracy ≤ 1` (lượt không R) báo cáo tắt/bật; không tăng.
- TTFT P95 lượt tra cứu ≤ **7,5 s**; toàn phiên P95 +≤ **0,3 s**; tool-call ≤ **30%** lượt không R.
- Test: mọi kịch bản fake ≤ 10,5 s; cờ tắt request y hệt.

## Risk Assessment
- Gắn nguồn sai tăng → judge_support gate; giữ 1 call, siết prompt.
- Chỉ misconception dựa hoàn toàn vào chunk công cụ mới không chặn điểm; phần còn lại giữ hành vi cờ tắt. Vẫn đo `ta_le1_rate` tắt/bật.
- Combo không hỗ trợ → latch, không có lookup; báo trong báo cáo.

## Security Considerations
- Query: phạm vi cố định, cắt 200, lọc injection; chunk bọc `wrap_untrusted`; chunk công cụ không có quyền phạt.

## Next Steps
- 04 dùng `EvaluationInput`/`evaluator_output_models.py`; 06 quyết `EVALUATOR_TOOLS`.
