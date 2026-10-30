# Thiết kế RAG (S0-AIE-3)

> Chốt thiết kế RAG cho `ai-service`. Liên quan: [ai-integration.md](ai-integration.md) (kiến trúc agent), [data-pipeline.md](data-pipeline.md) (DE: crawl, embed, index), [ADR-008](adr/adr-008-evaluator-per-turn-orchestrator.md).

## 1. Quyết định

| # | Hạng mục | Quyết định | Ghi chú |
|---|---|---|---|
| 1 | Embedding | `text-embedding-3-small`, 1536 chiều | Giữ nguyên. Chất lượng tiếng Việt **chưa đo**, xem mục 8 |
| 2 | LLM | `gpt-4o-mini` | Giữ nguyên |
| 3 | Vector store | PostgreSQL 16 + pgvector (`ai_db`) | Giữ nguyên |
| 4 | Khoảng cách | Cosine (`<=>`) | |
| 5 | Index vector | **Chưa tạo ANN index** (exact scan). Thêm **HNSW** khi >~10k chunks hoặc retrieval chậm | **Đổi** so với `ivfflat` trong docs cũ, xem mục 3 |
| 6 | Chunking | Theo loại nguồn (mục 2); textbook 512 token, overlap 50, thêm heading path | Overlap sẽ được đo (mục 7) |
| 7 | Retrieval | Top-5, lọc bằng cột `source_type`, `category`, `difficulty`; mỗi agent có tool riêng | Mục 4 |
| 8 | Hybrid / rerank | **Hybrid đã làm (2026-10-29, `RAG_HYBRID` mặc định bật)**: từ khóa (BM25 trong bộ nhớ) + vector + `topic_id` gộp RRF có trọng số. Rerank chưa làm, chờ số đo | [plan](../../plans/261029-1415-hybrid-grounded-rag/plan.md) |
| 9 | Đánh giá | Golden set 20+ query, đo recall@5, bắt đầu Sprint 1 | Mục 7 |

## 2. Chunking theo nguồn

| Nguồn | Đơn vị chunk | Chi tiết |
|---|---|---|
| `interview_qa` | Không cắt. 1 cặp Q&A → **2 bản ghi** | `question` (chỉ câu hỏi, để khớp câu tương tự) và `qa_pair` (câu hỏi + đáp án mẫu). Cả hai có chung `metadata.qa_id` và cùng `topic_id` (id trong topic catalog) |
| `textbook` | Theo heading (h2/h3); không có heading thì cửa sổ trượt 512 token, overlap 50 | Cắt ở ranh giới câu. **Thêm heading path vào đầu `content`**, ví dụ `Node.js > Streams > Backpressure` |

Lý do chính:
- Cặp Q&A là một đơn vị ý nghĩa, cắt ra sẽ mất đáp án.
- Embedding hai bản ghi `question` và `qa_pair` cho phép Interviewer tìm câu hỏi tương tự, còn Evaluator lấy đáp án mẫu. `qa_id` nối hai bản ghi, không cần tìm tương đồng lần hai.
- Một số tài liệu về RAG cho rằng overlap không cho lợi ích đo được và còn tăng chi phí index. Vì dữ liệu textbook nhỏ (vài nghìn chunk, chi phí embed vài cent), ta giữ overlap 50 làm mặc định rồi đo lại với overlap 0 (mục 7).

## 3. Schema `knowledge_chunks` (thay thế bản trong ai-integration.md)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE knowledge_chunks (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content          TEXT NOT NULL,
  content_hash     CHAR(32) NOT NULL UNIQUE,   -- md5(lower(trim(content))), upsert idempotent
  embedding        vector(1536) NOT NULL,
  embedding_model  VARCHAR(50) NOT NULL DEFAULT 'text-embedding-3-small',
  source_type      VARCHAR(30) NOT NULL,       -- interview_qa | textbook (job_description: Stretch, AI không dùng)
  category         VARCHAR(30),                -- Backend | Frontend | Database | System Design | DevOps | AI (khớp catalog)
  difficulty       VARCHAR(10),                -- easy | medium | hard (null với textbook)
  topic_id         VARCHAR(80),                -- id trong topic catalog; Q&A luôn có, textbook để NULL
  language         VARCHAR(5),                 -- vi | en
  metadata         JSONB NOT NULL DEFAULT '{}', -- qa_id, chunk_type, tags, source_url, section, heading_path...
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX knowledge_chunks_filter_idx ON knowledge_chunks (source_type, category);
CREATE INDEX knowledge_chunks_topic_idx ON knowledge_chunks (source_type, topic_id);
-- Chưa tạo index vector. Khi cần:
-- CREATE INDEX ON knowledge_chunks USING hnsw (embedding vector_cosine_ops);
```

Khác với thiết kế cũ:
- **Bỏ `ivfflat`.** IVFFlat phải "huấn luyện" trên dữ liệu có sẵn và kém đi khi insert dần, nên tạo trên bảng rỗng là sai. HNSW không cần huấn luyện. Với vài nghìn bản ghi, quét chính xác (exact) vẫn nhanh, chính xác 100%, và lọc bằng `WHERE` không làm thiếu kết quả. Đây là hướng các tài liệu pgvector hay khuyên cho bảng nhỏ. Đo lại trước khi thêm index.
- **`content_hash UNIQUE`.** `ON CONFLICT DO NOTHING` trong `data-pipeline.md` mục 7 hiện **không có tác dụng** vì bảng không có ràng buộc unique, nên chạy lại pipeline sẽ nhân đôi dữ liệu. DE nên dùng `ON CONFLICT (content_hash) DO NOTHING`.
- **`category`, `difficulty`, `source_type`, `language` là cột thật** thay vì chỉ nằm trong JSONB, vì đó là các điều kiện lọc thường xuyên.
- **`embedding_model`:** để biết chunk nào cần embed lại nếu đổi model.

## 4. Retrieval theo từng agent

Mỗi agent có tool riêng (xem ai-integration.md mục 2). Tất cả dùng chung hàm `retrieve(query, filters, k)` trong `app/rag/`.

| Agent | Tool | Lọc | Mục đích |
|---|---|---|---|
| Interviewer | `retrieve_knowledge` | `source_type IN (interview_qa[question], textbook)`, `category`, `difficulty` | Câu hỏi mẫu gần chủ đề + kiến thức nền để sinh câu hỏi tiếp |
| Planner | không dùng RAG | Chọn topic từ **topic catalog** theo `track` + `level` (mục 4.1) | Chủ đề phỏng vấn theo vị trí; không còn dùng JD |
| Evaluator | `retrieve_reference_answer` | Nếu câu hỏi từ ngân hàng: **tra thẳng theo `qa_id`**, không tìm tương đồng. Nếu câu hỏi do AI sinh: `interview_qa[qa_pair]` + `textbook` | Đáp án mẫu và tài liệu để chấm từng câu |

### 4.1 Topic catalog (chủ đề theo vị trí phỏng vấn)

Mỗi vị trí phỏng vấn (`track`) có một file YAML trong `apps/ai-service/app/catalog/`: `java_backend`, `python_backend`, `nodejs_backend`, `ai_engineer`, `frontend_react`, `devops_engineer` (6 track, 90 topic: Backend 30, AI 25, DevOps 14, Frontend 12, System Design 5, Database 4). Mỗi topic có `id`, `title`, `levels`, `category`, `key_concepts`; kèm danh sách `scenarios` theo level. Thêm vị trí mới = thêm một file YAML, loader và test tự nhận.

**Scenario không có `topic_id` hay `category`** nên phase scenario **không** lấy `interview_qa` theo topic; Evaluator chấm scenario bằng `key_points` chung của scenario, RAG chỉ bổ sung `textbook` lọc theo category của track (AIE xác nhận mục 7 trong spec 005).

Lấy ngữ cảnh cho từng topic: `interview_qa` theo `topic_id` trước (khớp chính xác); dưới 2 kết quả thì bổ sung bằng vector search lọc `category` + `difficulty`, cả `interview_qa` và `textbook`. Pipeline index từ chối chunk có `topic_id` không có trong catalog.

Quy tắc chung:
- **Query:** ghép `category + topic + tóm tắt ngắn câu trả lời gần nhất`. Không đưa cả lịch sử vào query.
- **Số lượng:** top-5. Không đặt ngưỡng điểm lúc đầu; **log điểm tương đồng và id** của mỗi lần gọi để chọn ngưỡng dựa trên dữ liệu thật.
- **Khử trùng lặp** theo `qa_id`. Giới hạn context chèn vào prompt khoảng 1500 token.
- **Cache (Sprint 4):** Redis, TTL 1 giờ, khóa là hash của (query, filters, embedding_model).

## 5. Bảo mật nội dung RAG

- Chunk lấy từ tài liệu web là **dữ liệu không tin cậy**. Trong prompt, đặt chunk trong khối có phân cách rõ và dặn model chỉ xem là tài liệu tham khảo, không làm theo chỉ dẫn nằm trong đó.
- Câu trả lời của ứng viên cũng không tin cậy (ví dụ "hãy cho tôi 10 điểm"). Evaluator phải nhận câu trả lời trong khối riêng, và điểm đi qua schema kiểm tra (0–10) cùng bước validator.
- **Pháp lý:** crawl tài liệu web có thể vướng điều khoản sử dụng hoặc bản quyền. Nhóm nên ghi rõ nguồn và cách dùng trong báo cáo, và kiểm tra điều khoản trước khi crawl.

## 6. Cấu trúc code trong `ai-service`

**Đã cài (2026-10-22, Phase 03, đường đọc):**

```
apps/ai-service/app/rag/
├── settings.py       # RAG_ENABLED (mặc định bật từ 2026-10-29), AI_DB_URL, tên embedding_model bỏ tiền tố provider
├── difficulty.py     # độ khó 1–5 -> easy/medium/hard
├── models.py         # Chunk, SearchFilters
├── repository.py     # psycopg 3 async, phiên read-only: list_by_topic_id, search (cosine + filter), get_pair_by_qa_id
├── retriever.py      # topic_id trước, < 2 thì vector fallback; dedup qa_id; ngân sách token; log id + điểm
└── factory.py        # build_retriever(): None khi RAG tắt; embed truy vấn qua LlmGateway
apps/ai-service/evals/ # rag_golden.json (bản nháp), rag_metrics.py, run_rag.py (recall@5 theo nhóm)
```

Khác thiết kế ban đầu: **không có `embedder.py`, `chunking.py` và upsert** trong ai-service, vì spec 005 giao toàn bộ đường ghi (chunk, embed, upsert) cho DE (`apps/data-pipeline`). Embed truy vấn dùng `LlmGateway.embed` (Phase 02). Hai bên dùng chung **contract** `specs/005-rag-knowledge-base-qa/contracts/knowledge-chunks-io.md` thay vì chung module. RAG lỗi (DB tắt, embedding lỗi, quá hạn, thiếu `AI_DB_URL`) thì retriever ghi log và trả rỗng, phiên vẫn chạy chỉ với `key_points`, và response start / next-turn báo lỗi trong `metadata.rag` (`status = error`, mã lỗi, thông báo; xem `docs/ai-service/06-api-contract.md` mục start). Từ 2026-10-29 RAG **bật mặc định**; chỉ tắt hẳn khi đặt `RAG_ENABLED=false`. **Hybrid search (Phase 01, `app/rag/hybrid_search.py`, `bm25_index.py`, `hybrid_fusion.py`):** mỗi truy vấn chạy song song ba danh sách: từ khóa (BM25 Okapi k1 = 1.2, b = 0.75, trong bộ nhớ), vector (như cũ) và tra theo `topic_id`. Ba danh sách gộp bằng RRF (k = 60), từ khóa trọng số 0.5, hai danh sách còn lại 1.0. Bản Postgres full-text (`ts_rank_cd`) trước đó đã bỏ: không có IDF, chunk rất dài đứng đầu mọi truy vấn, seq scan 1.7–4 s; kết quả kém hơn vector (`plans/reports/research-261029-1500-hybrid-vs-vector-rag.md`). BM25 tách token theo âm tiết (giữ dấu tiếng Việt, bỏ từ chức năng) cộng cặp âm tiết liền nhau (bắt từ ghép như "dữ_liệu"), và tìm trên cùng văn bản với vector (truy vấn gốc + bản tiếng Anh LLM viết lại). Corpus (mọi `qa_pair` của interview_qa + textbook, ~4.5k dòng, ~4.5 MB, đọc ~3 s) nạp lúc khởi động (`warm_rag` trong lifespan), đọc trong thread bằng kết nối riêng ngoài pool, dựng index trong thread (~1.1 s). Hết TTL (1 giờ) chỉ so dấu vân tay corpus (`CORPUS_VERSION_SQL`, md5 các dòng, ~0.3 s); chỉ đọc lại cả kho khi dữ liệu đổi, vì nạp + dựng tranh GIL với event loop làm request đang chạy quá hạn (đo 29/10). `topic_id` giờ chỉ tăng điểm chứ không lọc cứng, nên câu bị DE gán nhầm topic vẫn lên được nếu khớp cả từ khóa lẫn vector. Bản viết lại và vector được cache theo truy vấn, nên snippet và ngân hàng câu hỏi của cùng topic chỉ viết lại và embed một lần. Task dùng chung được bọc `asyncio.shield`, nên một request hết hạn không hủy vector mà request khác đang chờ. Viết lại lỗi thì không cache, lần sau thử lại. Viết lại + embed có hạn `RESOLVE_BUDGET_S` = 3.5 s (đo: viết lại 1.2–2.5 s, embed 1.0–1.3 s, SQL sau đó 0.5–1.1 s); quá hạn thì BM25 dùng truy vấn gốc, đường vector tính là lỗi nhẹ, topic vẫn có snippet từ `topic_id` + BM25 thay vì mất hết khi chạm hạn 5 s. Câu kho được xếp theo RRF của số từ trùng và độ giống vector (cột `similarity` của `BANK_SQL`); bộ lọc "phải có ít nhất một từ chung với topic" vẫn giữ. Một đường lỗi hay quá hạn thì vẫn dùng các đường còn lại và báo `degraded`. `RAG_HYBRID=false` quay về đường cũ. Truy vấn ai_db đi qua pool kết nối (`psycopg_pool`, mở sẵn 4, tối đa 8; kết nối rảnh trên mức tối thiểu đóng sau 60 s, mọi kết nối thay ở nền sau 10 phút; đóng pool khi tắt service): mở kết nối Supabase mất 1.5–1.8 s, còn truy vấn chỉ 0.2–0.3 s. Không dùng `check` của pool vì mỗi lần mượn kết nối thêm một vòng gọi (truy vấn 0.24 → 0.53 s). Kết nối bị pooler cắt thì thử lại một lần; `PoolTimeout` và `QueryCanceled` thì không thử lại. Mọi phiên đặt `statement_timeout` 15 s và TCP keepalive, nên truy vấn treo do mạng không giữ kết nối hay thread mãi. Nạp corpus có hạn 30 s; kiểm dấu vân tay lỗi thì vẫn nạp. **Truy hồi theo lượt (Phase 02, `app/turn_reference_snippets.py`, cờ `RAG_TURN_RETRIEVAL`):** mỗi next-turn không phải câu kho và không phải intro chạy BM25 (đã nạp sẵn, không chờ nạp) trên câu hỏi + 800 ký tự đầu câu trả lời, cùng bộ lọc category / độ khó như snippet; tra `topic_id` (hạn 1 s) chỉ để tăng điểm (RRF, trọng số 0.5) chunk BM25 đã tìm thấy. Truy vấn quá hạn được tách ra chạy tiếp ở nền (`asyncio.shield`): hủy truy vấn psycopg phải chờ server xác nhận, có thể giữ lượt nhiều giây khi mạng treo. Lỗi hay quá hạn thì 30 s sau đó các lượt chỉ dùng BM25, không chờ SQL. Tối đa 3 chunk, 600 token, bỏ chunk trùng snippet của topic (kể cả snippet bị cắt đuôi " ..."). Hint không có đáp án chuẩn chỉ lấy chunk cùng `topic_id` với topic đang hỏi. Không viết lại, không embed vì TTFT P95 đã sát 6 s. Lỗi `topic_id` là lỗi nhẹ `rag_turn_failed` (degraded, không ngắt RAG). Đo: `python -m evals.run_rag --mode both` (recall@5 và MRR, vector so với hybrid). 3 request lỗi RAG trong 2 phút thì không gọi ai_db trong `RAG_COOLDOWN_S` giây (`app/rag/circuit_breaker.py`, mặc định 60) rồi thử lại; trong lúc đó start không có RAG, next-turn vẫn dùng BM25 và cache đáp án (`rag_memory_only`). Start quá hạn thì giữ topic đã xong (`rag_start_partial`). Trạng thái xem ở `GET /api/health` (`rag`).

## 7. Cách đánh giá (bắt đầu Sprint 1)

1. **Golden set 20+ query** dạng `(query, filters, qa_id/chunk_id đúng)`, gồm cả query tiếng Việt và tiếng Anh. Ghi vào `apps/ai-service/evals/rag_golden.json` (bản nháp 24 query, 2026-10-22, nhãn trỏ vào `qa_id` của bộ canonical DE, chờ DE duyệt; nhóm Việt → tài liệu Anh để trống tới khi có textbook). Chạy `python -m evals.run_rag`. **Số đo 2026-10-24** (ai_db dùng chung trên Supabase, 9.006 bản ghi `interview_qa`, chưa có textbook): recall@5 0.875; en 1.0, mixed 1.0, không dấu 0.8, vi 0.667. Truy hồi theo `topic_id` ~0.4 s, vector ~1.5 s (gồm embed), gắn snippet cả plan ~1.5 s. Chi tiết: `plans/20261019-1100-ai-interview-brd-implementation/reports/eval-rag-20261024-shared-ai-db.md`.

**Truy hồi tiếng Việt (2026-10-24, [ADR-010](adr/adr-010-embedding-model-and-vietnamese-retrieval.md)):** đường vector dùng truy vấn gốc + bản tiếng Anh do LLM viết lại (`RAG_QUERY_REWRITE`, mặc định bật): held-out 32 câu tiếng Việt thuần 0.594 → 0.938, golden chính 1.000; đổi sang `text-embedding-3-large` @1536 chiều **hoãn** (owner 24/10: 3-small + viết lại đủ cho giai đoạn 1). Báo cáo: `plans/20261019-1100-ai-interview-brd-implementation/reports/eval-rag-20261024-vietnamese-retrieval.md`.

**Cải tiến 2026-10-24 (trước đó):** (a) mở rộng truy vấn tiếng Việt bằng thuật ngữ Anh trước khi embed (`app/rag/query_expansion.py`, áp cho đường vector của retriever và `run_rag`, tắt bằng `--no-expand`): golden chính 0.875 → 0.958, held-out tiếng Việt thuần 0.5 → 0.625; (b) `RAG_TEXTBOOK_ENABLED` (mặc định tắt khi kho chưa có textbook): scenario không truy hồi, gắn snippet ~1.5 s → ~0.44 s; (c) token embed truy vấn ghi vào `metadata.usage.embedding`.
2. Đo **recall@5** và xem tay top-3 (khớp quality gate "top-3 liên quan" trong data-pipeline.md). Mục tiêu đề xuất: recall@5 ≥ 0.8, cần nhóm xác nhận.
3. So sánh trên cùng golden set: overlap 0 và 50; có và không có heading path.
4. Nếu recall thấp ở truy vấn tiếng Việt: thử embedding model khác (ví dụ bge-m3) trước khi thêm hybrid hay rerank. Re-embed ~6000 chunk chỉ tốn vài cent và `embedding_model` đã có sẵn trong schema.
5. Chỉ thêm hybrid (BM25 + vector) hoặc rerank khi số đo cho thấy cần.

## 8. Rủi ro và điều chưa biết

- **Tiếng Việt:** các nguồn tôi tìm được không có số liệu riêng cho tiếng Việt của `text-embedding-3-small`, nên chưa thể khẳng định model này đủ tốt. Quyết định giữ model dựa trên chi phí thấp và đã chốt từ đầu, cần kiểm chứng bằng golden set.
- **Truy vấn khác ngôn ngữ:** câu hỏi tiếng Việt tìm tài liệu tiếng Anh (textbook) cần model hoạt động tốt chéo ngôn ngữ. Kết quả chưa biết.
- **Phối hợp AIE/DE:** S1-AIE-1 (ingestion, AIE) và S1-DE-1 (index Q&A, DE) trùng nhau một phần. Đề xuất: AIE giao `chunking.py` + `repository.py`, DE dùng lại và lo crawl, quy mô, vận hành.

## 9. Quyết định của nhóm

- **Ngôn ngữ:** phỏng vấn bằng **tiếng Việt, xen thuật ngữ tiếng Anh** (code-mixed). Q&A mẫu viết tiếng Việt, giữ nguyên thuật ngữ Anh (idempotent, CAP theorem...). Textbook chủ yếu tiếng Anh. Hệ quả: query tiếng Việt phải tìm được chunk tiếng Anh; cần test cả query có dấu và không dấu.
- **Golden set:** tổng hợp từ nhiều dataset. Yêu cầu bắt buộc:
  - Mỗi query phải gắn nhãn tới `qa_id`/`chunk_id` **trong corpus của ta** (nhãn của dataset ngoài trỏ vào corpus của họ, không dùng trực tiếp được).
  - Query **tách khỏi dữ liệu đã index**: không dùng nguyên văn câu hỏi trong `interview_qa`, nếu không recall bị thổi phồng.
  - Chia nhóm để báo cáo riêng: (a) tiếng Việt thuần, (b) code-mixed, (c) tiếng Anh, (d) Việt → tài liệu Anh, (e) không dấu.
  - Ghi `source` của từng query và kiểm tra giấy phép dataset.
- **Còn mở:** OpenAI API key và hạn mức để chạy S0-AIE-4; phân công AIE/DE cho ingestion (mục 8).
