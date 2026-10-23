# Bật RAG với ai_db dùng chung (Supabase), 2026-10-24

Kho: `ai_db` trên Supabase do DE dựng (PR #32), 9.006 bản ghi `interview_qa` (≈ 4.400 cặp crawl + dịch, 144 cặp hard của DE), `text-embedding-3-small`. ai-service đọc bằng role `aie_reader` (chỉ `SELECT`, read-only ở cấp role) qua Session pooler. Cấu hình: `RAG_ENABLED=true`, `AI_DB_CONNECT_TIMEOUT_S=10`. Chưa có `textbook`.

## Recall (đã đo, NFR-AI-QUAL14)

`python -m evals.run_rag` trên golden set AIE (24 truy vấn, nhãn bản nháp trỏ vào cặp hard `de-qa-1xxx`). Khớp đúng số DE đo ở PR #32.

| Nhóm | n | recall@5 |
|---|---|---|
| Tất cả | 24 | **0.875** (mục tiêu ≥ 0.8: đạt) |
| Tiếng Anh | 6 | 1.000 |
| Việt xen thuật ngữ Anh | 7 | 1.000 |
| Không dấu | 5 | 0.800 |
| Tiếng Việt thuần | 6 | **0.667** |

Trượt: g04 (phân trang bằng OFFSET, diễn đạt thuần Việt), g05 (cập nhật tồn kho đồng thời, thuần Việt), g21 (event loop không dấu: top-3 là cặp Node.js performance gần nghĩa nhưng không phải nhãn). Golden set chỉ gắn nhãn cặp hard; cặp crawl (`cr-*`) liên quan cũng có thể đứng đầu nên recall thật có thể cao hơn một chút. Nhãn vẫn là bản nháp, chờ DE duyệt.

## Ảnh hưởng tới độ trễ

Đo trực tiếp phần truy hồi (máy dev, Việt Nam → Supabase Singapore):

| Bước | Thời gian |
|---|---|
| Tra theo `topic_id` (một kết nối mới qua pooler) | ~0.4 s |
| Tìm vector (embed truy vấn + tìm) | ~1.5 s |
| Gắn snippet cho cả plan (song song) | **~1.5 s**, cộng vào `/api/start` |

Phần 1.5 s chủ yếu do topic **scenario**: chỉ tìm `textbook` bằng vector, mà kho chưa có textbook nên luôn trả rỗng. Topic technical đều trúng theo `topic_id` (~0.4 s).

Harness tầng 3 (quick, 9 phiên, LLM thật) bật RAG so với lần không RAG (v3, cùng code): `/api/start` P50 8.8 s (trước 10.1 s), lượt P50 4.0 s (trước 5.0 s), Planner 5.8 s (trước 8.2 s). **Mọi agent đều nhanh hơn, kể cả agent không dùng RAG**, nên chênh lệch là do OpenRouter dao động giữa các lần chạy; không dùng số này để nói RAG làm nhanh hơn. Chi phí $0.0074/phiên (trước $0.0071; chưa tính embed truy vấn RAG vì chưa ghi vào usage, xem dưới). Fallback 0%.

## Snippet trong plan (FR-AI-022)

43 topic / 9 phiên: technical 25/25 có 1–3 snippet; intro 9 bỏ qua theo thiết kế; scenario 9/9 rỗng (chưa có textbook). Input Evaluator P50 2.735 → 3.080 token (+13%) do có snippet.

## Chất lượng (chưa kết luận)

Persona Java junior: giỏi 5.3 / TB 4.8 / yếu 2.0 (không RAG: 5.7 / 4.3 / 1.1), khoảng cách 3.3 (trước 4.6). Recall lỗ hổng 6/7. Cỡ mẫu 3 phiên mỗi mức và Simulator cùng model, nên chưa biết RAG làm Evaluator chấm sát hơn hay dễ hơn; cần golden set có nhãn người (chạy `run_evaluator` với và không với `reference_snippets`).

## Đề xuất
1. Tạm bỏ truy hồi textbook cho scenario khi kho chưa có textbook (tiết kiệm ~1.1 s mỗi lần start), bật lại khi DE nạp textbook.
2. Ghi usage embedding truy vấn RAG vào `metadata` để tính đủ chi phí (hiện retriever gọi embed không truyền collector).
3. Tiếng Việt thuần (0.667): thử mở rộng truy vấn bằng tên topic/thuật ngữ Anh trước khi nghĩ tới đổi model embedding (đổi model cần ADR và re-index).
4. DE duyệt nhãn golden set RAG; thêm truy vấn nhắm cặp crawl.

## Sau 3 cải tiến (nhánh `thang/rag-improvements`, 2026-10-24)

1. **Tạm bỏ textbook** (`RAG_TEXTBOOK_ENABLED`, mặc định tắt): scenario không tìm nữa. Gắn snippet cả plan **~1.5 s → ~0.44 s** (3 lần đo, máy dev → Supabase Singapore); topic technical vẫn có snippet (3, 1, 3).
2. **Ghi usage embedding** của RAG vào `metadata.usage.embedding` (start). Với plan đo được, cả 3 topic technical trúng theo `topic_id` nên không cần embed (usage rỗng); embed chỉ phát sinh khi topic có < 2 cặp Q&A.
3. **Mở rộng truy vấn tiếng Việt** (`app/rag/query_expansion.py`): nối thuật ngữ Anh cho ~60 cụm IT tiếng Việt, so khớp trên chuỗi bỏ dấu.

| Bộ truy vấn | Không mở rộng | Có mở rộng |
|---|---|---|
| Golden set chính (24) | 0.875 | **0.958** |
| · tiếng Việt thuần (6) | 0.667 | 1.000 |
| · không dấu (5) | 0.800 | 0.800 |
| · en, mixed | 1.000 | 1.000 |
| **Held-out tiếng Việt thuần (8)** | 0.500 | **0.625** |

**Đọc số cẩn thận:** từ điển được viết sau khi biết 2 câu tiếng Việt bị trượt ở golden set chính; các cụm chép gần nguyên văn từ câu đó đã bị bỏ, nhưng vài thuật ngữ chung ("phân trang", "tồn kho", "cập nhật đồng thời") vẫn được chọn khi đã biết. Vì vậy con số 1.000 của nhóm tiếng Việt ở golden set chính **bị thổi phồng**. Bộ held-out (`evals/rag_golden_holdout.json`, 8 câu viết sau khi chốt từ điển, không sửa từ điển sau đó) cho thấy mức thật: **tiếng Việt thuần ~0.6, mở rộng giúp +1/8 câu**. Truy vấn thuần Việt vẫn là điểm yếu.

Ảnh hưởng thực tế hạn chế: đường plan dùng `topic_id` trước (khớp chính xác), vector chỉ dùng khi topic có < 2 cặp. Hướng tiếp nếu cần: model embedding đa ngôn ngữ (cần ADR, DE re-index), hoặc LLM viết lại truy vấn sang tiếng Anh ở đường vector (thêm ~1 s).

## Câu hỏi chưa giải quyết
- DE có kế hoạch nạp `textbook` trước feature freeze không?
- Golden set RAG có cần gắn nhãn thêm cặp `cr-*` không?
