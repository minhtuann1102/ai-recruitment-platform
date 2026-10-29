# Phase 01: Hybrid retrieval

## Context Links
- [plan.md](plan.md), `docs/architecture/rag-design.md` (mục 8 và đoạn Hybrid search)
- Contract kho: `specs/005-rag-knowledge-base-qa/contracts/knowledge-chunks-io.md`
- Vì sao bỏ Postgres FTS, chuyển BM25: `plans/reports/research-261029-1500-hybrid-vs-vector-rag.md`

## Overview
- Priority P1. Trạng thái: **xong code (BM25 + pool), đã đo trên ai_db; chờ owner test** (chưa commit).
- Thay "tra `topic_id` trước, vector chỉ khi có dưới 2 kết quả" bằng ba danh sách chạy song song, gộp bằng RRF.

## Key Insights
- `topic_id` của DE gán còn rộng, nên lọc cứng theo nó làm mất câu đúng. Chuyển nó thành một danh sách trong RRF.
- Bản đầu dùng Postgres FTS (`ts_rank_cd`) kém hơn vector (MRR held-out 0.857 → 0.622) và chậm 1.7–4 s: không có
  IDF, chunk 10k ký tự đứng đầu mọi truy vấn. BM25 trong bộ nhớ sửa được cả hai.
- Mở kết nối Supabase mất 1.5–1.8 s, nên cần pool kết nối.
- Nạp + dựng corpus (~4 s) tranh GIL với event loop, nên không được làm trong lúc phục vụ nếu dữ liệu không đổi.

## Architecture
`Retriever.retrieve_for_topic` (hybrid) chạy song song, gộp `rrf` (từ khóa 0.5, còn lại 1.0) → `trim_to_budget`:
- `list_by_topic_id` (SQL, pool)
- BM25 (`Bm25Store`, trong bộ nhớ) trên truy vấn gốc + bản viết lại
- `search(vector)` (SQL, pool)

Viết lại + embed dùng chung qua cache, có hạn `RESOLVE_BUDGET_S` = 3.5 s. Quá hạn: BM25 dùng truy vấn gốc, đường vector
tính là lỗi nhẹ (`rag_hybrid_partial`). Corpus nạp lúc khởi động; hết TTL thì so dấu vân tay, chỉ nạp lại khi đổi.

`bank_for_topic` dùng `HybridSearcher.query_vector` (cùng cache, cùng hạn). `BANK_SQL` trả thêm `similarity`, rồi
`question_bank.rank` xếp hạng bằng RRF của số từ trùng và `similarity`.

## Related Code Files
- **Tạo:** `app/rag/bm25_index.py`, `hybrid_fusion.py`, `hybrid_search.py`, `tests/test_rag_hybrid_search.py`
- **Sửa:**
  - `app/rag/repository.py` (pool, `load_corpus`, `corpus_version`), `retriever.py`, `question_bank.py`, `settings.py`,
    `factory.py`, `circuit_breaker.py`
  - `app/plan_snippets.py` (`warm_rag`), `app/main.py` (lifespan)
  - `requirements.txt` (`psycopg-pool`)
  - `evals/run_rag.py`, `evals/rag_metrics.py` (MRR)
  - các fake trong test, `tests/integration/test_rag_pgvector.py`

## Todo List
- [x] RRF có trọng số; retriever hybrid; `rag_hybrid_partial` → `degraded`, không ngắt RAG
- [x] Cache viết lại + vector theo truy vấn (`asyncio.shield`; viết lại lỗi thì không cache)
- [x] Sửa theo review: task dùng chung không bị hủy, không cache bản lỗi, đường không chạy không đếm, khử trùng `qa_id`
- [x] Câu kho xếp theo RRF (từ trùng có cùng điểm thì cùng hạng)
- [x] `RAG_HYBRID` (mặc định bật), `run_rag --mode vector|hybrid|both`, MRR
- [x] Đo FTS trên ai_db → kém hơn vector; nghiên cứu nguyên nhân
- [x] Thay FTS bằng BM25 trong bộ nhớ (uni + bi âm tiết, truy vấn gốc + viết lại, trọng số 0.5)
- [x] Pool kết nối; `PoolTimeout` không thử lại
- [x] Hạn viết lại + embed 3.5 s; corpus đọc trong thread ngoài pool; làm mới chỉ khi dấu vân tay đổi
- [x] Đo lại eval và độ trễ gắn snippet (bảng dưới)
- [x] Sửa theo review lần 2:
  - Nạp corpus có hạn 30 s; `statement_timeout` 15 s + keepalive cho mọi phiên.
  - Pool mở sẵn 4, tối đa 8; `max_lifetime` 10 phút (không dùng `check`: chậm gấp đôi); đóng pool khi tắt service.
  - Không thử lại `QueryCanceled`; kiểm dấu vân tay lỗi thì vẫn nạp lần đầu.
- [ ] Owner test thủ công (`/api/start`, `/api/health`) trước khi commit
- [ ] Chạy test tích hợp (`AI_DB_TEST_URL`, pgvector local) cho `load_corpus`, `corpus_version`, `similarity`

## Kết quả đo (2026-10-29, ai_db Supabase, code thật)

| Bộ | Vector recall@5 / MRR | Hybrid BM25 recall@5 / MRR |
|---|---|---|
| Chính (24) | 1.000 / 0.951 | 1.000 / 0.972 |
| Held-out (32) | 0.938 / 0.823 | 0.938 / 0.875 |

Gắn snippet lúc start (plan junior 20 phút; trước khi có pool: legacy 2.5–3.3 s, hybrid lần đầu quá hạn 5 s):

| Tình huống | Legacy | Hybrid |
|---|---|---|
| Lần đầu sau khởi động (corpus đã nạp) | 3.0–3.9 s | 4.6 s, đủ snippet, có lúc `degraded` |
| Track khác, chưa có cache | 1.2–1.6 s | 3.8–4.6 s, có lúc `degraded` |
| Cùng track lần 2 (cache) | 1.1–1.4 s | 1.0–1.4 s |
| Đang làm mới TTL, kho không đổi | — | 4.3–4.7 s, đủ snippet |
| Request đến trước khi nạp corpus xong (~6 s đầu) | — | quá hạn 5 s, 0 snippet |

## Success Criteria
- Recall@5 của hybrid ≥ vector trên cả hai bộ; MRR tăng: **đạt** (MRR +0.02 / +0.05; bộ nhỏ, chưa đủ mạnh thống kê).
- Gắn snippet lúc start dưới hạn 5 s: **đạt khi corpus đã nạp**; chậm hơn legacy 2–3 s khi chưa có cache.

## Risk Assessment
- **Độ trễ cao hơn legacy** vì luôn viết lại + embed mỗi topic (legacy chỉ khi thiếu hit). OpenRouter chậm thì vector
  quá hạn 3.5 s và topic chỉ còn `topic_id` + BM25 (`degraded`). Giảm được nếu bỏ viết lại cho hybrid (MRR held-out
  giảm, xem report) hoặc chuyển bước gắn snippet ra khỏi đường găng của `/start`.
- **Ngay sau khởi động** (~6 s nạp corpus) request start mất snippet. Có thể chặn readiness tới khi `warm_rag` xong.
- **RAM:** corpus + index ~vài chục MB, tăng theo textbook.
- **Dữ liệu đổi thì vẫn nạp lại trong lúc phục vụ** (~4 s tranh GIL). Kho DE đổi ít nên chấp nhận.

## Còn mở
- Usage của viết lại + embed dùng chung được tính cho request khởi tạo task; request khác dùng cache không thấy usage,
  và usage sau khi quá hạn ghi vào collector đã trả response. Chấp nhận (chi phí nhỏ), ghi lại ở đây.
- Supabase session pooler giới hạn bao nhiêu client và cắt kết nối rảnh sau bao lâu? Quyết `POOL_MAX_SIZE` và
  `POOL_MAX_LIFETIME_S`.
- `rag_timeout` vẫn kích hoạt bộ ngắt (60 s không RAG). Với hạn 3.5 s cho viết lại + embed, quá hạn 5 s chỉ còn ở
  tình huống mới khởi động. Có nên coi là lỗi nhẹ không?
- Có cần readiness probe chờ `warm_rag` không (phụ thuộc cách deploy)?

## Security Considerations
- Mọi truy vấn vẫn qua phiên read-only (pool và kết nối riêng đều đặt `default_transaction_read_only=on`); tham số được
  bind, không ghép chuỗi SQL. BM25 chạy trong bộ nhớ, không có SQL động.

## Next Steps
- Owner test xong → commit, push, MR → Phase 02 (truy hồi theo lượt).
