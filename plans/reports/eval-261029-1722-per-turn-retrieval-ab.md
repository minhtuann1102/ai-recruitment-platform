# Eval A/B: truy hồi theo lượt (Phase 02)

Quick matrix, 10 phiên, agent + simulator LLM, RAG bật. Hai bản chạy **song song cùng lúc** (cùng tải DB/LLM).
JSON: `plans/reports/eval-sim-turn-rag-ab-{0,1}.json` (gitignored).

| Chỉ số | Cờ tắt | Cờ bật |
|---|---|---|
| TTFT p50 / p95 (s) | 4.095 / 6.094 | 4.102 / 6.408 |
| Evaluator p50 / p95 (ms) | 3071 / 4920 | 3002 / 5070 |
| Câu kho (technical main) | 0.769 | 0.815 |
| gap strong-weak / gap_recall | 5.0 / 0.80 | 3.5 / 0.778 |
| hint_rate weak | 0.417 | 0.455 |
| Chi phí TB / phiên (USD) | 0.00830 | 0.00846 |
| Lượt chạy truy hồi theo lượt / có chunk | 0 | 24 / 24 |
| `rag_turn_failed` | 0 | 0 |

Nhận xét:
- p50 không đổi. p95 +0.31 s, vượt tiêu chí 0.2 s, nhưng n ≈ 100 nên p95 nhiễu: fallback_call_rate hai bản cũng khác nhau
  (0.29 / 0.15). Phần thêm thật trên lượt có truy hồi là SQL `topic_id` (~0.25 s qua pool), BM25 < 20 ms.
- 24/24 lượt chạy truy hồi có ít nhất 1 chunk. Thứ tự strong > average > weak giữ; gap 5.0 → 3.5 chỉ 1 nhóm, chưa kết luận.
- Lần đo mốc đầu (`eval-sim-turn-rag-baseline.json`) RAG đang lỗi (fallback 0.60, câu kho 0.15): không dùng làm mốc.

## Câu hỏi chưa giải quyết
- Bỏ tăng điểm `topic_id` (chỉ BM25, không chạm DB mỗi lượt) để gỡ ~0.25 s, đổi lại hint không còn nguồn "cùng topic"?
- Cần chạy matrix lớn hơn để p95 / gap đáng tin trước khi chốt?
