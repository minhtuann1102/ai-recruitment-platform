---
title: "ai-service: từ workflow cố định sang vòng lặp agentic có rào chắn"
description: "Tool calling trong gateway, Evaluator tự tra cứu, policy lai, lập lại kế hoạch, ghi chú (tùy chọn); mỗi hạng mục 1 cờ, mặc định tắt"
status: pending
priority: P2
effort: 12d
branch: main
tags: [ai-service, agentic, tool-calling, evaluator, policy, rag]
created: 2026-11-14
---

# Plan: ai-service agentic có rào chắn (hạng mục 0–4 của đề xuất DE)

Nguồn: `plans/reports/aie-request-261114-1057-agentic-ai-service.md` (scope), `scout-261114-1549-agentic-ai-service-code-map.md`,
`researcher-261114-1549-tool-calling-strict-json-openrouter.md`, `aie-reply-261114-1448-agentic-ai-service.md`, audit `reports/audit-261114-1604-plan-review.md`.

**Mục tiêu:** LLM đề xuất (tra cứu, hành động, đổi topic, ghi chú), code quyết. Mỗi hạng mục 1 cờ env, mặc định tắt; tắt =
quyết định/giá trị y hiện tại (JSON chỉ thêm khóa mặc định, báo FSD 1 lần). Lỗi → lùi đường cũ trong ngân sách 10 s
Evaluator. `forced_transition`, `low_performance_stop`, turn cap đứng trên LLM. Không framework (A4).

## Phase

| # | Phase | Cờ | Effort | Phụ thuộc | Status |
|---|---|---|---|---|---|
| 01 | [Chuẩn bị: probe, ngưỡng, mốc, eval tooling, scenario `System Design`](phase-01-prep-calibration-probe-eval-tooling.md) | – | 2d | khóa API (bước live) | pending |
| 02 | [Vòng lặp công cụ trong gateway](phase-02-gateway-tool-loop.md) | – (thư viện) | 1,5d | không (song song 01) | pending |
| 03 | [Evaluator tự tra cứu](phase-03-evaluator-knowledge-lookup.md) | `EVALUATOR_TOOLS` | 2d | 02; DE docs (đo scenario) | code xong, đo [BLOCKED-KEY] |
| 04 | [Policy lai](phase-04-hybrid-policy.md) | `POLICY_MODE=rules\|hybrid` | 2d | 01 (ngưỡng, `--runs`); 03 (cùng file) | code xong, đo [BLOCKED-KEY] |
| 05 | [Lập lại kế hoạch giữa buổi (gated)](phase-05-mid-session-replanning.md) | `REPLAN_ENABLED` | 3d | 04; **FSD** | code xong, cờ giữ tắt chờ FSD, đo [BLOCKED-KEY] |
| 06 | [Đo tổng, quyết bật mặc định, docs](phase-06-measurement-rollout-and-docs.md) | – | 0,5d | 03–05 + khóa | pending |
| 07 | [Ghi chú agent (tùy chọn)](phase-07-optional-agent-notes.md) | `AGENT_NOTES_ENABLED` | 1d | 04 đã đo đạt mốc | optional |

```
01 code ─┐        01 live (khóa) ──► 04 (ngưỡng)
02 ──────┴──► 03 ──► 04 ──► 05 ──► 06        04 đạt mốc ──► 07 (tùy chọn)
DE textbook ──► 03 đo scenario      FSD (lưu nguyên JSON, topic_id alt*, danh sách topic) ──► 05
```
03/04 cùng sửa `agents/evaluator.py` → tuần tự. Bước gọi LLM thật: **[BLOCKED-KEY]**; code + test fake LLM làm trước.

## Quy trình mỗi phase
Nhánh `thang/<feature>`; commit conventional tiếng Anh, không ghi công AI; PR `[ai-service] type: mô tả`; cùng PR sửa
`docs/ai-service/*` + `context/*`; `python3 apps/ai-service/scripts/check_docs.py`, `python -m pytest -q`.

## Assumptions to confirm (AIE đề xuất, chưa chốt)
1. Ngân sách: lượt tra cứu TTFT P95 ≤ 7,5 s; toàn phiên P95 +≤ 0,3 s; hạn bước tool 2,0 s; cả đường tra cứu + fallback ≤ 10 s.
2. gpt-4o-mini + `tools` + JSON strict qua OpenRouter: chưa xác minh; không hỗ trợ → lượt đó chấm 1 lần không tools (như cũ).
3. Cách A (gộp vào Evaluator), `action_reason` ≤ 20 từ; TTFT P50 +> 0,5 s thì bỏ.
4. Chunk công cụ không được bác ý sai: misconception chỉ dựa chunk công cụ không chặn điểm; còn lại như cờ tắt. Mở khi `refuted` precision ≥ 0,85.
5. Docs DE: `category` khớp catalog, `topic_id` cho technical, chunk 150–300 token. 6. Docs ưu tiên: scenario java/nodejs.
7. Ngưỡng chưa hiệu chỉnh → 01, trước 04; kết quả tạm thời đến khi kiểm trên tập giữ lại.
8. Mốc bật mặc định: reply mục 8, **trừ** độ ổn định: đổi "stdev mỗi persona ≤ 1,2×" thành stdev gộp (pooled) giữa các
   persona lõi (strong/average/weak, bỏ adversarial và skewed): `s_p = sqrt(Σ_p Σ_i (x_pi − x̄_p)² / Σ_p (n_p − 1))`; hybrid `s_p` ≤ 1,2× rules và ≤ 0,5/10, kèm CI bootstrap.
9. LangGraph: chờ mentor; có yêu cầu → xem lại A4 trước khi merge 02.

## Blockers
- Khóa OpenRouter `apps/ai-service/.env` hết hạn → chặn probe, sim, eval, hiệu chỉnh ngưỡng.
- FSD (hoangtunggg) → chặn 05. DE docs `textbook` → chặn đo scenario ở 03.

## Unresolved questions
- Owner: ngưỡng mới áp ngay cho `rules` hay chờ duyệt? Hiệu chỉnh cả `STRONG_BAND/WEAK_BAND` (`state_update.py:7`)?
- Lookup có chạy khi `RAG_TURN_RETRIEVAL=false` mà BM25 đã nạp? (plan: không, theo cờ RAG theo lượt).
- FSD: chấp nhận khóa mặc định mới trong `turn`/`state`/`plan`, fallback `evaluator_lookup_fallback`, topic id `alt*`?
- Nhóm thống nhất mốc mục 8 (gồm stdev gộp) trước khi đo phase 06.

## Changelog after audit (2026-11-14)
- Ghim v8 trong `LlmEvaluator.__init__` (C1); sim đo được hybrid: recorder passthrough, field TurnInfo trước apply (C2).
- 1 ngân sách 10 s cho cả đường tra cứu + fallback (H1); ép "chỉ R bác" trong postcheck (H4); `run_evaluator --lookup` (H3).
- Ghi chú tách thành phase 07 tùy chọn; gate golden/holdout/sourced cho v9, v10 (H2). `--runs` id riêng mỗi run (H5).
- Stdev gộp (H6); JD fixture cho sim persona `skewed` (H7); bảng hành động theo phân loại (H8).
- Bỏ `shadow` (M1), bỏ split mode (M2); M3–M10, L1–L7 sửa trong phase tương ứng.
