# Báo cáo chạy thử harness tầng 3 (mock), 2026-10-22

**Đây KHÔNG phải số đo chất lượng.** Lần chạy dùng agent mock (heuristic, không LLM) và simulator quy tắc (trả lời bằng chính `key_points` của topic), nên các chỉ số phân biệt hay recall lỗ hổng là **vòng tròn** (simulator "biết" đáp án mà Evaluator mock dùng để chấm). Mục đích: chứng minh harness chạy hết ma trận và đo đúng; tìm lỗi hành vi của orchestrator.

Lệnh: `cd apps/ai-service && python -m evals.simulate --matrix full` (in-process, `duration=20`, 28 persona: 3 chất lượng × 4 level × 2 track + 4 adversarial).

## Kết quả

| Nhóm | Chỉ số | Kết quả (mock) | Ngưỡng design 09 |
|---|---|---|---|
| Chạy | Phiên hoàn tất | 28/28 | — |
| Phân biệt | Giỏi > TB > yếu trong cùng (level, track) | 8/8 | ≥ 7/8 |
| | Khoảng cách giỏi − yếu | 5.46 | ≥ 3.0 |
| | Verdict đúng (giỏi meets/exceeds, yếu below) | 81% | ≥ 80% |
| Thích ứng | Độ dốc độ khó đúng chiều | 81% | ≥ 80% |
| | Tỉ lệ lượt `hint`: giỏi / yếu | 1.6% / 32.4% | yếu cao hơn rõ |
| Ràng buộc | Phiên vượt turn cap | 0 | 0 |
| | Đủ 4 phase gồm wrap-up (trừ phiên kết thúc sớm) | 100% | 100% |
| | Topic vượt giới hạn follow-up | 0 | 0 |
| | **Câu hỏi lặp (Jaccard ≥ 0.8)** | **34.2%** | < 5% |
| Báo cáo | Recall lỗ hổng (23 topic `does_not_know` đã hỏi) | 100% | ≥ 70% |
| | Điểm mạnh sai | 0 | 0 |
| | Topic `does_not_know` đóng trong ≤ 2 lượt | 100% | ≥ 90% |
| Độ bền | Persona injection không tăng điểm | 1/1 (0.0 so với 3.5) | 100% |
| Vận hành | TTFT, chi phí | Không có ý nghĩa (không gọi LLM, ASGI in-process) | P50 ≤ 3.5 s |

## Phát hiện

1. **Câu hỏi lặp 34% (128/374 lượt), phần lớn do mock, một phần là vấn đề thật.** Khoảng 65 lượt lặp do policy trả `focus` cố định "trade-off, internals hoặc edge case" cho mọi câu trả lời tốt (luật 10); khoảng 63 lượt do simulator quy tắc trả lời giống hệt nhau bất kể câu hỏi nên Evaluator mock trả cùng `missing_points[0]` (luật 8). Câu mẫu của mock trùng chính nó nên không bị thay. Vấn đề thật cần xử lý ở Phase 09: (a) policy nên chọn `focus` cụ thể theo topic hoặc ý chưa hỏi; (b) ở chế độ LLM, câu lặp được thay bằng câu dự phòng là mẫu cố định và **không kiểm lặp lại**, nên vẫn có thể lặp. Cần số đo với Interviewer LLM để biết mức thật.
2. Persona giỏi level senior bị verdict `near` (Java 6.3, Node 6.7) vì heuristic mock cho `extensibility` thấp; cần kiểm lại với Evaluator LLM trước khi chỉnh ngưỡng verdict (BRU-07).
3. Phiên `end_early` (3 lượt) có `end_reason = candidate_ended`, báo cáo vẫn tạo được.

## Cách chạy đo thật (owner, cần khóa API)

```bash
cd apps/ai-service
AGENT_EVALUATOR_MODE=llm AGENT_INTERVIEWER_MODE=llm AGENT_PLANNER_MODE=llm AGENT_REPORTER_MODE=llm \
LLM_MODEL_SIMULATOR=<model khác Evaluator> python -m evals.simulate --matrix full --simulator llm
```

TTFT phía client chỉ đúng khi gọi service thật (`--base-url http://localhost:8000` hoặc qua gateway `http://localhost:9080/ai`); khi chạy in-process, dùng `server_latency_ms` theo agent. Chi phí tính theo `evals/pricing.json` (**giá giả định** gpt-4o-mini $0.15 / $0.60 mỗi 1M token).

## Chỉ số của design 09 chưa cài
- LLM-as-judge chấm câu hỏi của Interviewer (Q5) và người đọc 5 transcript.
- Người kiểm `evidence_turns` đúng nội dung (5 report mỗi lần).
- Tỉ lệ lỗi format sau repair (gateway chưa đưa số lần repair ra `metadata`).
- Vượt giới hạn thời gian: bảo đảm bằng code và test biên ở tầng 1 (`tests/test_time_budget.py`), harness không đo lại.

## Câu hỏi chưa giải quyết
- Model nào cho Simulator để tránh "hiểu ý nhau" với Evaluator?
- Ngân sách cho một lần chạy full với LLM (ước 28 phiên × ~14 lượt)?
