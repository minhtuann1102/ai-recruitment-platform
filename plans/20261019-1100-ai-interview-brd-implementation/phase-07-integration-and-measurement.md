# Phase 07. Tích hợp và đo

## Context Links
- [plan.md](plan.md) · [design 06](../../docs/ai-service/06-api-contract.md) (contract, §7.5 SSE) · [design 08](../../docs/ai-service/08-latency-and-cost.md) · [design 09 §10.2 tầng 3](../../docs/ai-service/09-agent-quality-evaluation.md) · FR-AI-080, 082, 083, 090

## Overview
- **Priority:** P1 · **Status:** đang làm (2026-10-22): harness tầng 3 xong code (`thang/simulator-harness`); khóa contract, spike SSE qua APISIX, `RealAiInterviewClient` chưa làm (cần FSD, DE) · **Tuần:** W4–W7
- Khóa contract với FSD, cập nhật mock theo contract chốt, spike SSE qua APISIX, harness ứng viên giả lập (tầng 3) và **số đo thật đầu tiên** về độ trễ và chi phí.

## Key Insights
- `interview-service` chưa tồn tại và giao diện của FSD ở Sprint 4 (23/11–07/12): **không chờ**. Simulator và harness gọi thẳng ai-service, truyền state bằng script như interview-service sẽ làm.
- Mọi NFR hiện là ước tính. Phase này biến chúng thành số đo thật, thay các dòng "giả định".
- SSE qua hai hop proxy là rủi ro chưa kiểm chứng; mock đã có `MOCK_STREAM_DELAY_MS` để thử.

## Requirements
- FR-AI-080 (usage/latency/cost), 082 (3 tầng test), 083 (mock theo contract), 090 (endpoint). NFR: PERF01–02, COST01–03, OBS01–03, CMP04–05, QUAL09–13.

## Architecture
`evals/simulate.py` ─▶ ai-service (cv/parse → start → next-turn… → finalize) với persona YAML; log `metadata` → bảng chỉ số; không cần interview-service.

## Related Code Files
- **Tạo:** `evals/simulate.py`, `evals/personas/*.yaml` (3 chất lượng × 4 level × track), `evals/simulator_llm.py`, `evals/report_eval.py`; `libs/` hoặc `apps/interview-service/src/modules/ai-client/real-ai-interview-client.ts` (S2-AIE-5, khi interview-service có mặt).
- **Sửa:** mock (`app/main.py`, `app/models_*.py`) theo contract chốt; `docs/architecture/{api-contracts,ai-integration}.md`; `config/apisix/conf/apisix-dev.yaml` (timeout `read` ≥ 60 s cho SSE).

## Implementation Steps
1. W4: PR contract (JD, `requirements`, 15–20 phút, `replace`, lỗi) vào docs + mock; FSD duyệt; coi là **khóa contract**.
2. W4–W5: spike `curl -N` qua cổng 9080: token hiện dần, không dồn cuối; sửa buffer/nén/timeout; ghi kết quả.
3. W5–W6: `RealAiInterviewClient` (S2-AIE-5) khi `interview-service` sẵn; nếu chưa, cung cấp client + test hợp đồng để FSD nhúng.
4. W6: Candidate Simulator: persona có `knows_well`, `knows_partially`, `does_not_know`; 24 phiên (3 chất lượng × 4 level × 2 track) + 4 phiên adversarial. Cộng `30 + 0.4 × số từ` giây vào `elapsed_seconds` mỗi lượt.
5. W6–W7: đo TTFT P50/P95, chi phí mỗi phiên, tỉ lệ fallback; so sánh với NFR; cập nhật cột căn cứ từ "Giả định" sang "Đã đo".
6. Tinh chỉnh (policy, ngưỡng verdict/trọng số, prompt) dựa trên số đo.

## Todo List
- [ ] Contract khóa, FSD duyệt
- [ ] Spike SSE qua APISIX có kết quả
- [ ] RealAiInterviewClient (hoặc client + test hợp đồng)
- [x] Simulator + 28 phiên + báo cáo baseline **bằng mock** ([eval-sim-20261022-mock-baseline.md](reports/eval-sim-20261022-mock-baseline.md)); bản LLM chờ khóa API
- [ ] Số đo thật TTFT, chi phí; NFR cập nhật

## Success Criteria
- Phiên giỏi > trung bình > yếu ở ≥ 7/8 tổ hợp, khoảng cách ≥ 3.0 điểm; recall lỗ hổng ≥ 70%; điểm mạnh sai = 0; injection không làm tăng điểm; TTFT và chi phí có số đo (mục tiêu P50 ≤ 3.5 s, P95 ≤ 6 s theo dõi, cải thiện dần).

## Delivery (bàn giao)
- PR contract được FSD duyệt + mock theo contract chốt
- Kết quả spike SSE qua APISIX (có số liệu)
- Simulator + 28 phiên + báo cáo baseline
- `RealAiInterviewClient` (hoặc client + test hợp đồng)

## Cách test và nghiệm thu
1. `curl -N` qua cổng 9080: token đến dần (ghi mốc thời gian từng event), không dồn cuối
2. `python -m evals.simulate --matrix full` ra bảng: phân biệt (≥ 7/8 tổ hợp, khoảng cách ≥ 3.0), thích ứng, recall lỗ hổng ≥ 70%, điểm mạnh sai = 0, injection không tăng điểm
3. Số đo TTFT P50/P95 và chi phí mỗi phiên từ log
4. Test hợp đồng client với mock

## Đồng bộ tài liệu (bắt buộc, cùng PR với thay đổi)
`api-contracts.md`, `ai-integration.md`, `06-api-contract.md` (bản khóa), NFR PERF01–02/COST01–03 sang "Đã đo", BRD §8 và R-3 (độ trễ thật), L2 §5 và G7.
Sau khi sửa: chạy `python apps/ai-service/scripts/check_docs.py` (link, ID, truy vết BR→FR→NFR, số lượng trong mục lục).

## Nhánh
4 nhánh: `thang/contract-freeze`, `thang/sse-gateway-spike`, `thang/simulator-harness`, `thang/real-ai-client`. Mỗi nhánh một PR; mô tả PR ghi lại kết quả các bước test ở trên.

## Risk Assessment
- TTFT vượt mục tiêu → áp dụng tuần tự: Evaluator gọn, model nhanh hơn, Evaluator chạy song song với Interviewer cho các lượt `ok`.
- Simulator cùng họ model Evaluator → dùng model khác cho Simulator nếu được.

## Security Considerations
- Persona CV tổng hợp, không PII thật; báo cáo eval không chứa khóa; dữ liệu mô phỏng tách khỏi `knowledge_chunks`.

## Next Steps
Số liệu vào Phase 09 (báo cáo) và vào quyết định gate voice ở Phase 08.
