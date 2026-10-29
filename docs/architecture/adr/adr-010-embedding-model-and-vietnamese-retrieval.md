# ADR-010: Truy hồi tiếng Việt thuần: viết lại truy vấn bằng LLM, cân nhắc đổi sang `text-embedding-3-large`

**Ngày:** 2026-10-24  
**Trạng thái:** Phần 1 Accepted (owner, 2026-10-24, đã cài). Phần 2 **Deferred** (owner, 2026-10-24): giữ `text-embedding-3-small` cho giai đoạn 1; xem lại nếu recall tiếng Việt trên dữ liệu thật giảm hoặc muốn bỏ bước viết lại để giảm độ trễ  
**Liên quan:** [rag-design.md](../rag-design.md) §1, §7; NFR-AI-QUAL14, CMP06; số đo: `plans/20261019-1100-ai-interview-brd-implementation/reports/eval-rag-20261024-vietnamese-retrieval.md`

## Bối cảnh

Kho `knowledge_chunks` (9.006 bản ghi `interview_qa`, embed bằng `text-embedding-3-small`, 1536 chiều) trả kém với truy vấn **tiếng Việt thuần** (không thuật ngữ Anh): recall@5 0.594 trên bộ held-out 32 câu viết trước thử nghiệm, trong khi tiếng Anh và câu xen thuật ngữ Anh đạt 1.0. Ứng viên và câu hỏi trong phiên chủ yếu là tiếng Việt.

## Các phương án đã đo (cùng 2 bộ truy vấn, nhãn bản nháp)

| Model | Truy vấn gốc | + từ điển | LLM viết lại sang Anh | Gốc + viết lại |
|---|---|---|---|---|
| `3-small` (hiện tại) | 0.594 | 0.625 | 0.875 | **0.938** |
| `3-large` @1536 chiều | 0.812 | 0.875 | **1.000** | 0.969 |

Viết lại bằng `gpt-4o-mini`: P50 1.6 s, P95 2.2 s, ~250 token vào mỗi lần (không đáng kể). Embed lại cả kho bằng `3-large`: ~1,6 triệu token ≈ $0.21 (giá giả định $0.13 / 1M), 1 lần.

## Quyết định

1. **(Đã cài)** Đường tìm vector của ai-service dùng **truy vấn gốc + bản tiếng Anh do LLM viết lại** (`RAG_QUERY_REWRITE`, mặc định bật; lỗi thì dùng từ điển). Không đổi dữ liệu hay contract. Chỉ chạy khi topic có < 2 cặp Q&A theo `topic_id` (đường chính không đổi), nên không làm chậm `/api/start` khi kho đủ dữ liệu (đo: gắn snippet vẫn ~0.47 s). **Cập nhật 2026-10-29:** với hybrid search (`RAG_HYBRID`, mặc định bật; `docs/architecture/rag-design.md`) mọi topic đều viết lại + embed, dùng chung cho vector và BM25, có hạn 3.5 s (quá hạn thì topic chỉ còn `topic_id` + BM25, báo `degraded`). Gắn snippet khi chưa có cache: 3.8–4.7 s.
2. **(Đề xuất, chờ DE + team)** Chuyển kho sang `text-embedding-3-large` với `dimensions=1536`: **giữ nguyên schema** `vector(1536)` (CMP06), chỉ đổi giá trị cột `embedding_model` và DE index lại. Lợi ích chính: đạt 0.812 **không cần gọi LLM** (bỏ được 1.6 s viết lại nếu muốn), hoặc 1.000 khi kết hợp viết lại.

## Hệ quả

- Phần 1: thêm agent phụ `query_rewriter` (temperature 0, `max_tokens` 60, timeout 3 s, không retry; lỗi thì dùng từ điển); token ghi vào `metadata.usage`. Gắn snippet lúc start có hạn tổng 5 s, quá hạn thì plan không có snippet (đo lại với timeout 3 s: held-out vẫn 0.938).
- Phần 2 (nếu duyệt): DE chạy `index` với `EMBEDDING_MODEL=openai/text-embedding-3-large` (đường ghi cần truyền `dimensions=1536`); ai-service đổi `EMBEDDING_MODEL` cùng lúc (retriever luôn lọc `embedding_model` nên hai model không lẫn nhau); chạy lại `evals/run_rag.py` cả hai bộ trước khi bật cho người dùng.
- Rủi ro: bộ đo nhỏ (24 + 32 truy vấn), nhãn chưa được DE duyệt, LLM viết lại cùng họ model. Cần DE duyệt nhãn và thêm truy vấn nhắm cặp crawl.
