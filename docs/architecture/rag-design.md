# Thiết kế RAG (S0-AIE-3)

> Chốt thiết kế RAG cho `ai-service`. Liên quan: [ai-integration.md](ai-integration.md) (kiến trúc agent), [data-pipeline.md](data-pipeline.md) (DE: crawl, embed, index), [ADR-007](adr/adr-007-multi-agent-interview.md).

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
| 8 | Hybrid / rerank | **Chưa làm**. Chỉ cân nhắc ở Sprint 4 nếu recall thấp | YAGNI |
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
  category         VARCHAR(30),                -- Backend | Database | System Design | DevOps | AI (khớp catalog)
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

Mỗi vị trí phỏng vấn (`track`) có một file YAML trong `apps/ai-service/app/catalog/`: `java_backend`, `python_backend`, `nodejs_backend`, `ai_engineer`. Mỗi topic có `id`, `title`, `levels`, `category`, `key_concepts`; kèm danh sách `scenarios` theo level. Thêm vị trí mới = thêm một file YAML, loader và test tự nhận.

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

```
apps/ai-service/app/rag/
├── embedder.py       # gọi OpenAI embeddings, batch + retry
├── repository.py     # SQL: upsert theo content_hash, search cosine + filter, get theo qa_id
├── retriever.py      # retrieve(query, filters, k) -> [{id, content, score, metadata}]
└── chunking.py       # chunk_qa / chunk_textbook (dùng chung với pipeline)
```

`chunking.py` và `repository.py` là phần lõi mà pipeline index (DE) và tool của agent (AIE) cùng dùng, tránh viết hai lần.

## 7. Cách đánh giá (bắt đầu Sprint 1)

1. **Golden set 20+ query** dạng `(query, filters, qa_id/chunk_id đúng)`, gồm cả query tiếng Việt và tiếng Anh. Ghi vào `apps/ai-service/tests/rag_golden.json`.
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
