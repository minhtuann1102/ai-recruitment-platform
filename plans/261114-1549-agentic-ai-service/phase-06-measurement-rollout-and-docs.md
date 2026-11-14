# Phase 06: Đo tổng, quyết bật mặc định, đồng bộ docs

## Context Links
- Reply mục 8 (bảng mốc); báo cáo eval của 01, 03, 04, 05 trong `plans/reports/`
- `docs/ai-service/08-latency-and-cost.md`, `09-agent-quality-evaluation.md`, `README.md` (A4), `context/decisions.md`,
  `context/project-state.md`, `context/quality-criteria.md`

## Overview
- Priority: P3. Status: pending. Nhánh: `thang/agentic-rollout`. Effort 0,5d (+ thời gian chạy eval).
- Docs từng hạng mục đã cập nhật trong PR của phase đó; phase này chỉ: chạy đo kết hợp (các cờ cùng bật), đề xuất cờ
  nào bật mặc định, ghi số trước/sau vào 08/09, quyết định vào `decisions.md`.

## Key Insights
- Mỗi cờ đã đo riêng; tương tác (lookup + hybrid cùng gọi Evaluator) cộng độ trễ → phải đo cấu hình kết hợp.
- Judge không tất định (±0,04) → mọi so sánh 3 lần lấy trung bình; sim `--runs 3`, độ ổn định = stdev gộp giữa persona (plan.md mục 8).
- Mốc là đề xuất AIE, cần nhóm thống nhất trước khi đo (plan.md, unresolved).

## Requirements
- F: ma trận cấu hình: baseline (tất cả tắt) · `EVALUATOR_TOOLS` · `POLICY_MODE=hybrid` · cả hai · cả hai + REPLAN
  (+ notes nếu phase 07 đã làm).
- F: bảng quyết định mỗi cờ: đạt/không đạt từng mốc, khuyến nghị (bật / giữ tắt), lý do.
- NF: không đổi mặc định khi chưa có owner duyệt.

## Architecture
- Không code mới. Dùng `simulate.py --matrix full --simulator llm --serve --runs 3`, `sim_runs.py`, `ttft_breakdown.py`,
  `cost_latency.py`, `judge_support.py` (3 lần), `run_evaluator.py --runs 3`, `run_evaluator_sourced.py`.

## Related Code Files
- Modify: `.env.example` (mặc định chỉ khi owner duyệt), `docs/ai-service/08`, `09`, `README.md` A4 (xác nhận),
  `context/decisions.md`, `context/project-state.md`, `context/next-phase-plan.md` (nếu ảnh hưởng mốc).
- Create: `plans/reports/eval-<date>-agentic-rollout.md`.
- Delete: không.

## Implementation Steps
1. **[BLOCKED-KEY]** Chạy ma trận 5 cấu hình (3 runs), cùng commit, cùng corpus (ghi số bản ghi `knowledge_chunks`).
2. Lập bảng mốc (dưới) cho từng cờ; tính tương tác TTFT.
3. Viết báo cáo; gửi owner (+ DE cho phần lookup scenario) duyệt.
4. Owner duyệt → đổi mặc định trong code/`.env.example` (PR riêng, có sim trước/sau); không duyệt → ghi lý do vào `decisions.md`.
5. Docs 08/09 (số đo ghi rõ "đã đo <ngày>, cấu hình"), README A4, context; check_docs, pytest. PR
   `[ai-service] docs: số đo và quyết định bật cờ agentic`.

## Todo List
- [ ] [BLOCKED-KEY] ma trận 5 cấu hình × 3 runs
- [ ] Bảng mốc + báo cáo
- [ ] Owner duyệt
- [ ] Đổi mặc định (nếu duyệt) / ghi lý do
- [ ] Docs 08/09, README A4, context, PR

## Success Criteria (bảng mốc tổng)
| Cờ | Mốc bật mặc định |
|---|---|
| `EVALUATOR_TOOLS` | độ đúng `supported` AI ≥ 0,65 (mốc 0,53), kho ≥ 0,71; band golden+holdout (`--lookup`) không giảm; misconception/`ta≤1` không tăng; id sai không tăng; TTFT P95 lượt tra cứu ≤ 7,5 s; toàn phiên P95 +≤ 0,3 s; tool-call ≤ 30% lượt không R |
| `POLICY_MODE=hybrid` | ngưỡng đã hiệu chỉnh; v9 vs v8 golden/holdout/sourced không giảm; overrule ≤ 15%; stdev gộp ≤ 1,2× rules và ≤ 0,5/10 (CI bootstrap); gap strong−weak giảm ≤ 10% (mốc 3,74); injection không đổi hành động; TTFT P50 +≤ 0,5 s |
| `AGENT_NOTES_ENABLED` (phase 07, tùy chọn) | ≥ 85% đúng trên 20 phiên đọc tay; 0 PII; gap/stdev không xấu hơn hybrid không notes |
| `REPLAN_ENABLED` | v10 vs v8 không giảm; độ phủ JD không giảm (sim persona skewed + JD); `/api/start` P95 +≤ 0,5 s; state/plan cũ chạy; FSD xác nhận |
- Cấu hình kết hợp vẫn đạt mốc TTFT toàn phiên.

## Risk Assessment
- Khóa API / chi phí chạy ma trận: ước tính bằng `cost_latency.py` trước khi chạy full.
- Corpus đổi giữa các lần đo (DE ingest) → ghi số bản ghi, chạy cùng ngày.

## Security Considerations
- Báo cáo không chứa khóa, không dữ liệu cá nhân thật (persona giả lập).

## Next Steps
- Nếu mentor yêu cầu LangGraph: đánh giá lại A4 (ghi `decisions.md`). Mở quyền bác ý cho docs khi `refuted` precision ≥ 0,85.
