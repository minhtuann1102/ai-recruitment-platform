# Phase 02: Truy hồi theo lượt

## Context Links
- [plan.md](plan.md), [phase-01](phase-01-hybrid-retrieval.md) (BM25, RRF, `metadata.rag`)
- Mục tiêu độ trễ: `docs/ai-service/08-latency-and-cost.md` (TTFT P50 ≤ 3.5 s, P95 ≤ 6 s)
- Code: `app/turn_engine.py` (`next_turn`), `app/agents/evaluator.py` (`build_messages`), `app/rag/bm25_index.py`

## Overview
- Priority P1. Trạng thái: **xong**, merge PR #53.
- Hiện nay RAG chỉ chạy một lần lúc `/start`: Evaluator mỗi lượt nhận `reference_snippets` cố định của topic, cộng
  `reference_answer` khi câu vừa hỏi lấy từ kho. Follow-up, hint và câu AI tự đặt chấm theo snippet của cả topic, có
  thể không khớp câu đang hỏi.
- Phase này: mỗi `next-turn` tìm thêm chunk theo **chính câu vừa hỏi + câu trả lời**, đưa cho Evaluator, và cho hint
  khi không có đáp án chuẩn.

## Key Insights
- Đo Phase 01: viết lại + embed mất 2.2–3.8 s. TTFT P95 đã sát mốc 6 s (eval 24/10: 5.49–6.13 s). Nếu thêm embed
  trước Evaluator thì cộng ~1–1.3 s vào mỗi lượt, vượt mục tiêu.
- BM25 trong bộ nhớ đã có sẵn từ Phase 01, truy vấn < 20 ms, không gọi mạng. Câu hỏi + câu trả lời là văn bản dài,
  nhiều thuật ngữ, hợp với tìm theo từ khóa.
- Câu hỏi lấy từ kho đã có `reference_answer` đúng câu đó (tốt nhất có thể), nên không cần truy hồi thêm.

## Quyết định
- **Đường theo lượt = BM25(câu hỏi + câu trả lời) + tăng điểm theo `topic_id`**, gộp RRF (từ khóa 1.0, topic 0.5,
  chỉ giữ chunk có trong kết quả BM25). Không viết lại, không embed: không thêm lời gọi LLM nào.
- Chạy song song với việc lấy đáp án chuẩn, hạn `TURN_DEADLINE_S` = 1.0 s. Quá hạn hay lỗi thì lượt đó dùng snippet
  của topic như trước, báo `degraded` (lỗi nhẹ, không ngắt RAG).
- Bỏ qua khi: RAG tắt, `RAG_HYBRID=false` (không có BM25), phase `intro`, câu có `qa_id` (đã có đáp án chuẩn), corpus
  BM25 chưa nạp xong (không chờ).
- Tối đa 3 chunk, ≤ 600 token; bỏ chunk trùng snippet của topic và trùng đáp án chuẩn.
- Evaluator: ghép vào khối `reference_snippets` (snippet topic trước, chunk theo lượt sau). Prompt v3 không đổi.
- Hint: không có đáp án chuẩn thì dùng chunk đầu **cùng `topic_id`** với topic làm `reference_answer` cho Interviewer
  (đã có kiểm chép quá 5 chữ). Chunk BM25 thuần không dùng: câu trả lời sai kéo truy vấn lệch khái niệm (review).
- SQL `topic_id` quá hạn: tách ra chạy nền (`asyncio.shield`), không giữ lượt; lỗi thì 30 s chỉ dùng BM25.
- Cờ `RAG_TURN_RETRIEVAL` (mặc định bật).
- Vector theo lượt **để sau**: chỉ làm nếu đo thấy BM25 bỏ sót nhiều và còn ngân sách độ trễ.

## Architecture
`next_turn`: `gather(_answer_key, turn_snippets)` → `EvaluationInput(turn_snippets=…)` → `build_messages` ghép snippet.
`app/turn_reference_snippets.py` (mới): `turn_snippets(retriever, …)` dùng `Bm25Store.ready()` (index đã nạp hoặc None, không
chờ) + `repo.list_by_topic_id`.

## Related Code Files
- **Tạo:** `app/turn_reference_snippets.py`, `tests/test_rag_turn_retrieval.py`
- **Sửa:** `app/rag/bm25_index.py` (`ready()`), `app/rag/settings.py`, `app/rag/factory.py`, `app/rag/retriever.py`
  (cờ), `app/rag/circuit_breaker.py` (lỗi nhẹ), `app/turn_engine.py`, `app/agents/evaluator.py`
- **Docs:** `docs/architecture/rag-design.md`, `docs/ai-service/06-api-contract.md` (mã lỗi), `.env.example`

## Todo List
- [x] Đo TTFT mốc (lần đầu RAG đang lỗi, mốc không dùng được; đo lại A/B cờ tắt/bật cùng lúc) (quick matrix, agent + simulator LLM, RAG bật)
- [x] `turn_snippets` + `Bm25Store.ready()` + cờ `RAG_TURN_RETRIEVAL`
- [x] Nối vào `next_turn` (song song với đáp án chuẩn, hạn 1 s), Evaluator, hint
- [x] Test: bỏ qua đúng trường hợp, khử trùng, quá hạn → degraded, không ngắt RAG
- [x] Đo lại A/B ([báo cáo](../reports/eval-261029-1722-per-turn-retrieval-ab.md)): p50 không đổi, p95 +0.31 s (nhiễu,
  vượt tiêu chí 0.2 s), 24/24 lượt có chunk
- [x] Docs, review độc lập (sửa: shield SQL quá hạn, cooldown 30 s, hint cùng topic, khử trùng snippet cắt đuôi)
- [x] Owner test

## Success Criteria
- TTFT P95 không tăng quá 0.2 s so với mốc.
- Phần lớn lượt không phải câu kho (follow-up, hint, câu AI tự đặt) có ít nhất 1 chunk theo lượt.
- Thứ tự strong > average > weak và gap_recall không tụt so với mốc.

## Risk Assessment
- **BM25 bắt nhầm theo từ chung** trong câu trả lời lan man → chunk lạc đề. Giảm bằng lọc category/độ khó, tăng điểm
  `topic_id`, cắt câu trả lời 800 ký tự.
- **Token Evaluator tăng** (~≤ 600 token mỗi lượt có chunk). Chi phí nhỏ (gpt-4o-mini).
- **Ứng viên nhồi từ khóa** để kéo chunk có đáp án vào Evaluator: chunk chỉ là tài liệu đối chiếu, prompt cấm trích
  quote từ đó (luật 8); không làm lộ đáp án cho ứng viên.

## Security Considerations
- Câu trả lời của ứng viên chỉ dùng làm truy vấn BM25 trong bộ nhớ, không vào SQL. Chunk vẫn bọc `<untrusted>`.

## Next Steps
- Phase 03: thêm id cho từng chunk (topic + theo lượt) để Evaluator trích `evidence_ids`.
