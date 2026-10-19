# Phase 03. RAG đường đọc

## Context Links
- [plan.md](plan.md) · [rag-design.md](../../docs/architecture/rag-design.md) · [spec 005](../../specs/005-rag-knowledge-base-qa/spec.md) (phân chia ghi/đọc) · FR-AI-022, 060, 061

## Overview
- **Priority:** P1 · **Status:** chưa bắt đầu · **Tuần:** W2–W4
- Theo spec 005: **DE sở hữu đường ghi** (load, chunk, embed, upsert), **AIE sở hữu đường đọc** (embed truy vấn, tìm tương đồng, tra theo `qa_id`). Phase này làm đường đọc và nối vào Planner/Evaluator.

## Key Insights
- DDL `knowledge_chunks` đã nằm trong `scripts/init-databases.sh` của DE (nhánh `chore/docker-multi-db-minio`), sao từ rag-design §3 (có `content_hash`, `topic_id`).
- AIE ngừng index seed mock khi bộ Q&A canonical của DE vào kho; seed mock chỉ còn cho test/local.
- Bảng nhỏ: quét chính xác, chưa cần index vector.

## Requirements
- FR-AI-022 (≤ 3 chunk mỗi topic lúc plan, `reference_snippets` ≤ 600 token), FR-AI-060 (không dữ liệu phiên trong kho), FR-AI-061 (theo `topic_id` trước, dưới 2 kết quả thì vector fallback; top-5; khử trùng; ≤ ~1.500 token; log score+id).
- NFR: QUAL14 (recall@5 ≥ 0.8), OBS04, SEC (tài khoản đọc), CMP06 (1536 chiều).

## Architecture
`Planner → retriever.retrieve_for_topic(topic) → repository` (SQLAlchemy + pgvector, tài khoản **chỉ đọc**). RAG tắt được (`RAG_ENABLED=false`) và ai-service vẫn chạy khi `ai_db` lỗi.

## Related Code Files
- **Tạo:** `app/rag/{embedder,repository,retriever,difficulty}.py`, `evals/run_rag.py`, `evals/rag_golden.json`, `tests/test_retriever.py` (fake repo), `tests/integration/test_rag_pgvector.py` (marker `integration`, bỏ qua trong CI).
- **Sửa:** `.env.example` (`AI_DB_URL`, `RAG_ENABLED`), `docker-compose.yml` (biến cho ai-service), `requirements.txt` (driver Postgres đã chọn).

## Implementation Steps
1. Đối chiếu DDL của DE với rag-design §3; ghi chênh lệch (nếu có) vào PR.
2. `embedder.embed_query` qua gateway (Phase 02). `repository.search` (cosine, lọc `category`, `difficulty`, `source_type`), `get_pair_by_qa_id`, `list_by_topic_id`.
3. `retriever`: topic_id trước, vector bổ sung khi < 2; khử trùng theo `qa_id`; cắt theo ngân sách token; map độ khó 1–5 sang easy/medium/hard.
4. Test đơn vị bằng repo giả; test tích hợp với pgvector chạy trong Docker Compose.
5. Golden set RAG: DE soạn truy vấn + nhãn, AIE duyệt nhãn; có nhóm Việt thuần, code-mixed, Anh, không dấu, Việt tới tài liệu Anh. Chạy `evals/run_rag.py` ra recall@5 theo nhóm.

## Todo List
- [ ] Đối chiếu DDL với DE
- [ ] embedder, repository, retriever, difficulty map
- [ ] Test đơn vị + test tích hợp pgvector
- [ ] Golden set RAG được duyệt; số recall@5 theo nhóm
- [ ] Nối `reference_snippets` vào plan (cùng Phase 04)

## Success Criteria
- Truy vấn mẫu trả đúng topic; lookup `qa_id` trả đúng `qa_pair`; ai_db tắt thì ai-service vẫn chạy không RAG; recall@5 được đo (mục tiêu ≥ 0.8, không đạt thì báo cáo hướng cải thiện, không chặn merge).

## Risk Assessment
- Bộ Q&A canonical chưa có khi cần → dùng seed mock gắn `topic_id` cục bộ để phát triển.
- Embedding tiếng Việt chưa đo → thử model khác nếu recall thấp (đổi model là thay đổi contract dữ liệu, cần ADR).

## Security Considerations
- Chunk RAG là dữ liệu không tin cậy: đưa vào prompt trong khối phân cách; tài khoản DB chỉ đọc; không ghi dữ liệu phiên vào `knowledge_chunks`.

## Next Steps
Phase 04 (Planner dùng retriever), Phase 05 (Evaluator dùng đáp án mẫu).
