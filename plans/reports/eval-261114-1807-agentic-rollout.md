# Agentic ai-service: runbook đo, bảng rollout, kết quả (phase 06)

- Ngày soạn: 2026-11-14. Kế hoạch: `plans/261114-1549-agentic-ai-service/`. Mốc: `plans/reports/aie-reply-261114-1448-agentic-ai-service.md` mục 8 (đề xuất AIE, **nhóm chưa thống nhất**).
- **Trạng thái: chưa có số đo nào.** Khóa OpenRouter hết hạn (401 "API key expired"), nên mọi bước [BLOCKED-KEY] dưới đây chưa chạy. Không số nào trong file này là số đo; bảng kết quả (mục 4) để trống.
- Không đổi mặc định nào. Cờ nào cũng giữ tắt cho đến khi bảng mục 4 được điền và owner duyệt.

## 1. Quy ước chạy

- Thư mục: `cd apps/ai-service`. Python: venv của dự án. Cần `LLM_API_KEY` (khóa mới, owner giữ; không in, không commit), RAG bật, `AI_DB_URL` trỏ ai_db.
- LLM thật: `AGENT_PLANNER_MODE=llm AGENT_EVALUATOR_MODE=llm AGENT_INTERVIEWER_MODE=llm AGENT_REPORTER_MODE=llm` (gọi tắt `$LLM`).
- Mọi so sánh: **cùng commit, cùng corpus (ghi `SELECT count(*) FROM knowledge_chunks`), cùng ngày**. Judge lệch ±0,04, nên so sánh nào cũng chạy 3 lần lấy trung bình.
- `simulate --out` ghi JSON phiên; summary có `pooled` (stdev gộp + CI bootstrap + gap strong-weak, từ `evals/sim_runs.py`), `hybrid_policy`, `evaluator_lookup`, `replan`, `notes`, `ops` (độ trễ, chi phí). `--serve` chạy service thật trong tiến trình (TTFT thật; cần để đo TTFT).
- Ngân sách chi phí: ước tính bằng `cost_latency` (đã nằm trong `summary.ops` của lần chạy nhỏ `--matrix quick --runs 1`) trước khi chạy `--matrix full --runs 3`.

Biến cấu hình cho 6 cấu hình ma trận (C0 là baseline; các biến khác để mặc định):

| Cấu hình | Biến env thêm vào `$LLM` |
|---|---|
| C0 baseline | (không) |
| C1 tools | `EVALUATOR_TOOLS=true` |
| C2 hybrid | `POLICY_MODE=hybrid` |
| C3 tools + hybrid | `EVALUATOR_TOOLS=true POLICY_MODE=hybrid` |
| C4 + replan | C3 + `REPLAN_ENABLED=true` |
| C5 + notes (tùy chọn) | C4 + `AGENT_NOTES_ENABLED=true` |

## 2. Lệnh đo theo phase (tất cả [BLOCKED-KEY])

Đặt `D=$(date +%y%m%d)`; file ra ở `plans/reports/`.

### Phase 01: probe, baseline, hiệu chỉnh ngưỡng
1. [BLOCKED-KEY] Probe tool calling + JSON strict: `python -m scripts.probe_tool_strict_json --out ../../plans/reports/probe-$D-tool-strict-json.md`. Ghi provider, `require_parameters`, lỗi 404/400 (nếu có). Không hỗ trợ: latch `tools_unsupported`, lượt chấm như cũ.
2. [BLOCKED-KEY] Baseline C0, 4 run: `$LLM python -m evals.simulate --matrix full --simulator llm --serve --runs 4 --out ../../plans/reports/eval-sim-$D-c0.json`. Lấy stdev gộp, gap strong-weak (mốc 3,74), `end_reasons`.
3. [BLOCKED-KEY] TTFT baseline: `python -m evals.ttft_breakdown ../../plans/reports/eval-sim-$D-c0.json`.
4. [BLOCKED-KEY] `judge_support` 3 lần, tách câu AI và câu kho: `python -m evals.judge_support ../../plans/reports/eval-sim-$D-c0.json --control --triage --out ../../plans/reports/eval-$D-judge-c0-<k>.json` (k = 1..3; trung bình).
5. [BLOCKED-KEY] Hiệu chỉnh `WEAK_BELOW`/`STRONG_FROM` (hiện 1,5 / 3,0 là giả định) trên tập A (nửa lượt từ baseline), kiểm trên tập B; owner duyệt rồi mới sửa `app/policy.py`, ghi "đo <ngày>, tạm thời". Hỏi owner có hiệu chỉnh cả `STRONG_BAND/WEAK_BAND` (`state_update.py`) không.

### Phase 03: `EVALUATOR_TOOLS`
6. [BLOCKED-KEY] Độ đúng `supported`: chạy sim C0 và C1 như bước 2 (`--runs 2` đủ), rồi `judge_support` 3 lần cho mỗi file như bước 4. So độ đúng câu AI (mốc 0,53) và câu kho (0,71).
7. [BLOCKED-KEY] Band golden và holdout: `EVALUATOR_TOOLS=true $LLM python -m evals.run_evaluator --set main --lookup --runs 3`; cùng lệnh với `--set holdout`; so với chạy không `--lookup`.
8. [BLOCKED-KEY] Trích nguồn sai id: `python -m evals.run_evaluator_sourced --runs 3` rồi `--lookup --runs 3`.
9. [BLOCKED-KEY] TTFT và tool-call: sim C1 `--serve --runs 2`, rồi `ttft_breakdown` (cột `lookup`, `evaluator_lookup_fallback`) và `summary.evaluator_lookup` (`lookup_rate`, `misconception_rate`, `ta_le1_rate`, `lookup_fallback`).
10. [BLOCKED-KEY] [DE] Scenario: lặp 6-9 với `RAG_TEXTBOOK_ENABLED=true` sau khi DE nạp textbook (scenario java/nodejs).

### Phase 04: `POLICY_MODE=hybrid`
11. [BLOCKED-KEY] Gate chấm v9 vs v8: `python -m evals.run_evaluator --set main --prompt v8 --policy-context default --runs 3` và `--prompt v9`; cùng với `--set holdout`; `run_evaluator_sourced --prompt v8|v9 --policy-context default --runs 3`.
12. [BLOCKED-KEY] Sim C0 vs C2, 3 run mỗi bên (`--matrix full --simulator llm --serve --runs 3`). Lấy `pooled` (stdev gộp persona lõi, CI), `hybrid_policy.overrule_rate_llm`, gap, TTFT P50.
13. Injection: unit test `tests/test_policy_hybrid*.py` đã có và chạy không cần khóa. Phần [BLOCKED-KEY]: đọc lượt của persona adversarial trong file sim C2 (`turns[].decided_by`, `overrule_reason`): lượt injection phải `forced` hoặc bị bác `sensitive_kind`, không có `decided_by = llm` đổi hành động.

### Phase 05: `REPLAN_ENABLED` (và FSD)
14. [BLOCKED-KEY] Gate v10 vs v8: `run_evaluator --set main|holdout --prompt v10 --policy-context default --runs 3` so v8; `run_evaluator_sourced --prompt v10 --policy-context default`.
15. [BLOCKED-KEY] Sim `skewed` (JD + CV giả) và full, C3 vs C4: `$LLM <env> python -m evals.simulate --matrix skewed --simulator llm --serve --runs 3` và `--matrix full`. `summary.replan`: `swap_rate`, `jd_assessed_rate`, `scored_topics`, `jd_priority_violations` (sim thoát mã 1 nếu > 0).
16. [BLOCKED-KEY] `/api/start` P95: không có script riêng; mỗi phiên trong file sim có `calls[]` với phần tử `path == "start"` (`total_s`). Lấy P95 gộp mọi run: `python -c "import json,sys; from evals.cost_latency import percentile as p; d=json.load(open(sys.argv[1])); s=d.get('sessions') or d; print(p([c['total_s'] for x in (s.values() if isinstance(s,dict) else s) for c in x.get('calls',[]) if c.get('path')=='start'],95))" <file.json>"` cho C3 và C4 (lệnh đã chạy thử trên file sim cũ, không cần khóa).

### Phase 07: `AGENT_NOTES_ENABLED` (tùy chọn)
17. [BLOCKED-KEY] Gate chấm v11 vs v8: `run_evaluator --set main|holdout --prompt v11 --policy-context default --runs 3`, và `run_evaluator_sourced --prompt v11 --policy-context default`.
18. [BLOCKED-KEY] Sim C4 vs C5, `--runs 3`: gap và stdev gộp không xấu hơn; `summary.notes.unsafe_notes` = 0 (sim thoát mã 1 nếu khác 0).
19. [BLOCKED-KEY] Đọc tay 20 phiên có ghi chú từ file sim C5 (phiên + `state.notes`): đếm ghi chú đúng với hội thoại và ghi chú có thông tin cá nhân (kể cả tên người, nơi làm việc; `redact_pii` không bắt tên).

### Phase 06: ma trận kết hợp
20. [BLOCKED-KEY] C0..C5 mỗi cấu hình `--matrix full --simulator llm --serve --runs 3`, cùng ngày; `ttft_breakdown` trên từng file. Kiểm cấu hình kết hợp vẫn đạt TTFT toàn phiên P95 +≤ 0,3 s so C0.

## 3. Mốc và cổng (từ reply mục 8; chưa chốt giữa nhóm)

| Cờ | Cổng bật mặc định (tất cả phải đạt) |
|---|---|
| `EVALUATOR_TOOLS` | độ đúng `supported` câu AI ≥ 0,65 (baseline 0,53), câu kho không giảm (0,71); band golden + holdout (`--lookup`) không giảm; id sai không tăng; `misconception_rate` và `ta_le1_rate` không tăng; TTFT P95 lượt tra cứu ≤ 7,5 s; TTFT P95 toàn phiên tăng ≤ 0,3 s; tool-call ≤ 30% lượt không có `R` |
| `POLICY_MODE=hybrid` | ngưỡng đã hiệu chỉnh; v9 vs v8 golden/holdout/sourced không giảm; `overrule_rate_llm` ≤ 15%; stdev gộp hybrid ≤ 1,2× rules **và** ≤ 0,5/10 (kèm CI); gap strong-weak giảm ≤ 10% (baseline 3,74); injection không đổi hành động; TTFT P50 tăng ≤ 0,5 s |
| `REPLAN_ENABLED` | v10 vs v8 không giảm; độ phủ JD không giảm; `jd_priority_violations` = 0; `/api/start` P95 tăng ≤ 0,5 s; state/plan cũ chạy; **FSD xác nhận bằng văn bản** |
| `AGENT_NOTES_ENABLED` | v11 vs v8 không giảm; `unsafe_notes` = 0; đọc tay 20 phiên: ≥ 85% đúng và 0 PII; gap/stdev không xấu hơn hybrid không notes |

Ghi chú: "overrule" dùng `overrule_rate_llm` (bỏ lượt `sensitive_kind`); chờ owner xác nhận dùng số này hay tỷ lệ đầy đủ.

## 4. Bảng kết quả (điền sau khi có khóa; đang trống)

Điền: ngày đo, commit, số bản ghi `knowledge_chunks`, cấu hình.

| Chỉ số | Mốc | C0 | C1 | C2 | C3 | C4 | C5 | Đạt? |
|---|---|---|---|---|---|---|---|---|
| Ngày / commit / số chunk | – | | | | | | | |
| TTFT P95 lượt tra cứu (s) | ≤ 7,5 | n/a | | n/a | | | | |
| TTFT P95 toàn phiên, tăng so C0 (s) | ≤ 0,3 | – | | | | | | |
| TTFT P50 tăng so C0 (s, hybrid) | ≤ 0,5 | – | n/a | | | | | |
| Tỷ lệ gọi công cụ (lượt không `R`) | ≤ 30% | n/a | | n/a | | | | |
| Độ đúng `supported`, câu AI | ≥ 0,65 (0,53) | | | | | | | |
| Độ đúng `supported`, câu kho | ≥ 0,71 | | | | | | | |
| Band agreement golden / holdout | không giảm | | | | | | | |
| Trích nguồn sai id | không tăng | | | | | | | |
| `misconception_rate`, `ta_le1_rate` | không tăng | | | | | | | |
| `overrule_rate_llm` | ≤ 15% | n/a | n/a | | | | | |
| Stdev gộp (/10), tỷ số so C0 | ≤ 1,2× và ≤ 0,5 | | | | | | | |
| Gap strong − weak | giảm ≤ 10% (3,74) | | | | | | | |
| `jd_priority_violations` | = 0 | n/a | n/a | n/a | n/a | | | |
| Độ phủ JD (`skewed`) | không giảm | | | | | | | |
| `/api/start` P95 tăng (s) | ≤ 0,5 | – | | | | | | |
| `unsafe_notes` | = 0 | n/a | n/a | n/a | n/a | n/a | | |
| Ghi chú đọc tay đúng / có PII | ≥ 85% / 0 | n/a | n/a | n/a | n/a | n/a | | |

## 5. Bảng rollout

Mọi cờ **mặc định tắt**. Tắt = quyết định, request LLM và giá trị y như trước (test ghim: prompt v8 không đổi byte; JSON chỉ thêm khóa mặc định `plan.replan: null`, `state.swaps: []`, `state.notes: []`, các khóa `turn` bằng `null`). Rollback = đặt cờ về tắt (hoặc bỏ biến) và khởi động lại ai-service; state/plan đã lưu có khóa mới vẫn nạp được.

| Cờ | Mặc định | Điều kiện cần | Cổng bật | Giới hạn liên quan |
|---|---|---|---|---|
| `EVALUATOR_TOOLS` | `false` | Evaluator LLM; `RAG_HYBRID` và `RAG_TURN_RETRIEVAL` bật; chỉ lượt không có đáp án chuẩn, không phải intro | mục 3 hàng 1; probe tool + JSON strict đạt (hoặc latch giữ đường cũ) | `EVALUATOR_MAX_TOOL_CALLS=1` (trần 2), `EVALUATOR_TOOL_DEADLINE_S=2.0`; chung ngân sách 10 s Evaluator; lỗi hoặc quá hạn thì `evaluator_lookup_fallback` |
| `POLICY_MODE` | `rules` | Evaluator LLM; hiệu chỉnh ngưỡng (phase 01) xong và owner duyệt | mục 3 hàng 2 | `forced_transition`, `low_performance_stop`, turn cap luôn đứng trên LLM; `EVALUATOR_PROMPT_VERSION` ghi đè lệch thì log `policy_prompt_mismatch` |
| `REPLAN_ENABLED` | `false` | `POLICY_MODE=hybrid`; Evaluator v10; **FSD xác nhận**; không bật ở môi trường thật trước đó | mục 3 hàng 3 | `REPLAN_MAX_SWAPS=1` (trần 2); reserve tối đa 2 topic `alt1/alt2`; pool mỏng thì không có reserve |
| `AGENT_NOTES_ENABLED` | `false` | `POLICY_MODE=hybrid`; Evaluator v11 (chọn cố định cả phiên); FSD lưu nguyên `state` | mục 3 hàng 4 | ≤ 8 ghi chú, ≤ 150 ký tự, 1 ghi chú/lượt; client gửi quá giới hạn thì 422 bất kể cờ |

Thứ tự bật đề xuất khi đạt cổng: `EVALUATOR_TOOLS`, rồi `POLICY_MODE=hybrid`, rồi `REPLAN_ENABLED`, rồi `AGENT_NOTES_ENABLED`. Mỗi bước là một PR đổi mặc định riêng, có sim trước/sau.

## 6. Việc mở

- [BLOCKED-KEY]: bước 1-20 mục 2.
- [DE]: textbook scenario java/nodejs (bước 10).
- Owner: duyệt hiệu chỉnh ngưỡng; chốt mốc mục 3 (gồm stdev gộp); `overrule_rate_llm` hay tỷ lệ đầy đủ; bật cờ nào mặc định.
- FSD: xem `docs/ai-service/06-api-contract.md` mục "Thông báo gộp cho FSD".
