---
title: Hybrid RAG + chấm/hỏi có trích nguồn (kiểu NotebookLM) trên dữ liệu DE
status: draft (chờ owner duyệt)
priority: P1
created: 2026-10-29
owner: AIE (thang)
branch: thang/hybrid-grounded-rag (Phase 01, đã merge), thang/per-turn-retrieval (Phase 02, đã merge)
---

# Hybrid RAG và trả lời có nguồn

**Mục tiêu:** mọi nhận định của AI về đúng/sai đều dựa trên chunk của kho DE và trích được nguồn. Code kiểm được câu
"AI sai hay đúng", không dựa vào kiến thức sẵn có của model. Nền tảng: RAG bật mặc định (`thang/rag-default-on`).

## Hiện trạng (2026-10-29, `app/rag/retriever.py`, `plan_snippets.py`)
- Lấy một lần lúc `/start`: tra SQL theo `topic_id` trước, vector chỉ chạy khi có dưới 2 kết quả. Câu kho xếp hạng bằng đếm từ trùng.
- Chỉ lượt có câu từ kho mới chấm theo đáp án chuẩn (`qa_id`). **Follow-up, hint, scenario và câu AI tự đặt không có
  nguồn**: Evaluator chấm bằng kiến thức của model cộng `key_points` của topic.
- Snippet chọn theo topic, không theo câu đang hỏi. Không có trích nguồn và không có cách đo grounding.
- Recall@5 0.875 (golden 24 query). `topic_id` của DE gán còn rộng. Chưa có textbook.

## Nguyên tắc (lấy từ NotebookLM)
1. **Chỉ dựa trên nguồn:** agent chấm/hỏi/nhận xét chỉ từ chunk được đưa vào, mỗi nhận định kèm `evidence_ids`.
2. **Code kiểm trích dẫn:** id phải nằm trong tập đã đưa vào, quote phải có trong chunk (giống quote check của câu trả lời).
3. **Không đủ nguồn thì nói rõ:** `grounded=false` và `confidence=low`, không trừ điểm theo suy đoán.
4. **Nguồn hiện ra cho người xem:** report có "căn cứ" theo chunk, ghi rõ license và dataset.

## Phases

| # | Phase | Nội dung chính | Phụ thuộc | Trạng thái |
|---|---|---|---|---|
| 01 | [Hybrid retrieval](phase-01-hybrid-retrieval.md) | Chạy song song 3 đường: BM25 trong bộ nhớ (thay Postgres FTS, đo kém hơn vector), vector, và khớp `topic_id`. Gộp bằng RRF (k=60, từ khóa trọng số 0.5); `topic_id` chỉ để tăng điểm, không lọc cứng. Pool kết nối ai_db. Xếp hạng câu kho bằng điểm hybrid, thay cho đếm từ | Golden RAG (DE đã duyệt) | **Xong, merge PR #52** (MRR held-out 0.823 → 0.875) |
| 02 | [Truy hồi theo lượt](phase-02-per-turn-retrieval.md) | Mỗi `next-turn`: truy vấn = câu hỏi + ý chính của câu trả lời + `missing_points` → top 3–5 chunk cho Evaluator và cho follow-up/hint. Hạn 1.5 s, có cache. Lỗi thì đi qua `metadata.rag` và bộ ngắt | 01 | Xong, merge PR #53 (BM25 theo lượt + tăng điểm `topic_id`, hạn 1 s; không embed để giữ TTFT) |
| 03 | Hợp đồng trích nguồn | Evaluator v4: mỗi ý covered có `source_ids` + `support` (`supported` / `contradicted` / `no_source`); code hậu kiểm id và quote; `no_source` thì giới hạn độ tin cậy. Interviewer: follow-up ghi `focus_source` (chunk/ý của đáp án). Reporter: điểm mạnh/lỗ hổng trích lượt + chunk; `study_plan.resources` lấy từ chunk được trích | 02 | 03a (Evaluator) xong, merge PR #55 ([phase-03a](phase-03a-evaluator-evidence-contract.md)); 03b (tham chiếu bền + `study_plan.resources`) **đang làm**: [phase-03b](phase-03b-report-sources.md), nhánh `thang/report-sources`; `focus_source` để sau |
| 04 | Dữ liệu DE | Cắt chunk > 4k ký tự; `interview_style`; gán lại topic; lọc license; câu `hard` cho senior; textbook cho scenario/system design | DE (Phase B `context/next-phase-plan.md`) | Cần DE xác nhận |
| 05 | Đo | recall@k, MRR (hybrid so với hiện tại); tỉ lệ trích dẫn hợp lệ; độ hỗ trợ (LLM-judge NLI hiệu chỉnh theo nhãn người); tỉ lệ `no_source`; Evaluator ±1 band không tụt dưới 0.93; TTFT và chi phí | 01–03 | Chưa bắt đầu |

Phase file viết just-in-time khi bắt đầu từng phase (`phase-0N-*.md`).

## Thay đổi code dự kiến
- `app/rag/bm25_index.py` (mới): BM25 trong bộ nhớ. `app/rag/hybrid_fusion.py` (mới): RRF + dedup. `repository.py`: pool kết nối, đọc corpus.
- `app/rag/retriever.py`: `retrieve_for_turn()`. `app/turn_engine.py`: gọi theo lượt, truyền chunk cho Evaluator/Interviewer.
- `app/agents/evaluator*.py`, `prompts/evaluator.v4.md`, `evaluation_checks.py`: thêm `evidence_ids`/`support` và hậu kiểm.
- `app/agents/reporter.py`: trích nguồn. Contract `docs/ai-service/06-api-contract.md`: thêm trường mới, chỉ bổ sung.
- `evals/run_rag.py` (thêm chế độ hybrid), `evals/` (chỉ số grounding mới).

## Rủi ro
- **Độ trễ:** TTFT P95 hiện 7.0 s (mốc 6 s). Truy hồi theo lượt cộng thêm ~0.5–1.5 s. Cách giảm: chạy song song với
  Evaluator ngay từ lúc nhận câu trả lời, có cache, đặt hạn chặt.
- **Tìm từ khóa tiếng Việt:** Postgres FTS (`simple`, không IDF, seq scan 1.7–4 s vì `aie_reader` không tạo được
  index) đo kém hơn vector, đã thay bằng BM25 trong bộ nhớ. Đổi lại ai-service giữ corpus trong RAM và nạp ~6 s lúc
  khởi động.
- **Model không trích dẫn đúng:** code hậu kiểm và repair một lần; vẫn sai thì gắn `no_source`.

## Câu hỏi còn mở
1. ~~ai_db có `unaccent` / `pg_trgm` không?~~ Không có (đã kiểm 29/10); dùng BM25 trong bộ nhớ. Còn mở: chấp nhận ai-service giữ corpus trong RAM, hay chờ index BM25 phía DB?
2. Chấp nhận TTFT tăng thêm tối đa bao nhiêu cho truy hồi theo lượt?
3. Có dùng rerank (LLM hoặc cross-encoder) không, hay chỉ RRF? Đề xuất: chỉ RRF trước, đo xong mới quyết.
4. Câu AI tự đặt mà không có nguồn: vẫn chấm (gắn `no_source`) hay bắt buộc chỉ hỏi những câu có nguồn?
