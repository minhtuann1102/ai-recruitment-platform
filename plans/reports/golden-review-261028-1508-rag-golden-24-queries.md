# Duyệt nhãn golden set RAG (005 T041) — 2026-10-28

File: `apps/ai-service/evals/rag_golden.json` (AIE soạn 2026-10-22, 24 query, nhãn trỏ `qa_id` của DE).
Bằng chứng: script tạm đọc 144 cặp curated (`data/seeds/interview_qa/*.json`) + 4.359 cặp crawl
(`data/processed/interview_qa.jsonl`) = 4.503 cặp, đúng bằng 9.006 record trên Supabase.

## Duyệt là kiểm gì (đọc trước)

- Mỗi query có "đáp án đúng" = danh sách `qa_id` (`relevant`). Eval tìm top-5; **trúng nếu có ≥ 1 `qa_id` đúng trong
  top-5**. Recall@5 = số query trúng / tổng.
- Duyệt 4 điểm: (1) `qa_id` có thật; (2) cặp đó thật sự trả lời query; (3) không bỏ sót cặp curated khác trả lời
  **đầy đủ như nhãn gốc**; (4) nhóm, `filters` đúng, query không chép nguyên văn câu hỏi (FR-020).
- Thêm `qa_id` chỉ làm recall tăng hoặc giữ nguyên → chỉ thêm khi cặp đó trả lời trọn query, không thêm cặp chỉ định
  nghĩa khái niệm ("readiness probe là gì").
- Test `test_rag_golden_and_metrics.py` bắt mọi nhãn bắt đầu `de-qa-`: cặp crawl **không gắn nhãn được**, nên ứng
  viên bổ sung chỉ xét 144 cặp curated.

## Kiểm tự động (24/24)

| Kiểm | Kết quả |
|---|---|
| `qa_id` có trong kho | 24/24 query, 26/26 nhãn |
| `category` của nhãn khớp `filters` | 8/8 query có filter |
| Nhóm | vi 6, mixed 7, en 6, no_diacritics 5; **vi_to_en 0** (chưa có textbook, 012 ở S3) |
| Trùng nguyên văn câu hỏi | 0; g22, g24 gần như chép câu hỏi rồi bỏ dấu (xem dưới) |

## Kết luận từng query

| Query | Nhóm | Nhãn | Kết luận |
|---|---|---|---|
| g01 | vi | 1100 | OK — HashMap, hashCode ít giá trị → chậm |
| **g02** | vi | 1104 | **Thiếu nhãn** — query không nói ngôn ngữ, 1016 (Node) trả lời tương đương |
| g03 | vi | 1120 | OK — idempotency key cho thanh toán khi mobile retry (1006 BullMQ là nguyên nhân khác) |
| g04 | vi | 1109 | OK — OFFSET chậm, keyset pagination |
| **g05** | vi | 1111, 1012 | OK; **tùy chọn** thêm 1057 cho nhất quán |
| g06 | vi | 1183 | OK — data leakage, CV cao production sụp |
| g07 | mixed | 1110 | OK — self-invocation qua proxy, REQUIRES_NEW |
| g08 | mixed | 1001 | OK — Promise.all 50.000 id, giới hạn concurrency |
| g09 | mixed | 1053 | OK — FastAPI `async def` gọi code blocking |
| g10 | mixed | 1204 | OK — rolling update 502, đáp án có preStop (5 lần) |
| g11 | mixed | 1252 | OK — hydration, đáp án nêu `new Date()`, múi giờ |
| g12 | mixed | 1163 | OK — HNSW vs IVFFlat, filter làm thiếu kết quả |
| g13 | mixed | 1050 | OK — Celery chạy lặp sau OOM kill, acks_late |
| g14 | en | 1102 | OK — double-checked locking, volatile |
| g15 | en | 1106 | OK — N+1, JOIN FETCH kèm phân trang |
| g16 | en | 1008 | OK — rate limiter Redis nhiều instance |
| g17 | en | 1167 | OK — LoRA / QLoRA |
| g18 | en | 1213 | OK — label cardinality cao làm Prometheus OOM |
| g19 | en | 1165 | OK — thiên lệch LLM-as-judge |
| g20 | no_diacritics | 1100 | OK — cùng đích g01, khác nhóm (so sánh được) |
| **g21** | no_diacritics | 1000 | **Lỗi: query mâu thuẫn với đáp án của nhãn** |
| g22 | no_diacritics | 1020, 1112 | OK; ghi chú gần như chép câu hỏi 1020 |
| g23 | no_diacritics | 1195 | OK — indirect prompt injection, agent đọc email |
| g24 | no_diacritics | 1256 | OK; ghi chú gần như chép câu hỏi 1256 |

### g21 — phải sửa query (đề xuất cho Thắng duyệt)

- Query: "event loop bi chan lam latency p99 tang du cpu thap". Nhãn 1000: Node CPU thấp, p99 tăng; đáp án viết rõ
  **"libuv threadpool bị bão hòa chứ không phải event loop bị block"** (nếu event loop bị block thì request đọc cache
  cũng chậm).
- Ứng viên khác cũng không khớp: 1017 là event loop bị chặn nhưng **một core CPU 100%**; 1052 là asyncio (Python).
- Không có cặp nào khớp cả hai ý → sửa nhãn không giải quyết được, phải viết lại query. Đề xuất:
  `nodejs p99 latency tang vot du cpu thap, doc file va goi crypto deu cham` → chỉ 1000 đúng.
- Đây là đổi thiết kế test của AIE → ghi trong PR, Thắng duyệt.

### g02 — thiếu nhãn

- Query "Lỗi tràn bộ nhớ heap sau vài ngày chạy, cách tìm nguyên nhân rò rỉ" không nói Java.
- 1016 (Node.js, OOMKill vài ngày một lần, phân biệt RSS với heapUsed, cách điều tra khi heapUsed tăng) trả lời đầy đủ
  như 1104 (Java).
- (A) thêm 1016 vào `relevant` (sát truy vấn thật, recall chỉ tăng hoặc giữ); (B) thêm "Java" vào query (giữ một đích,
  đo khó hơn).

### g05 — tùy chọn

- Nhãn đã có 1012 (đặt vé, bán quá số ghế) dù khác ngữ cảnh tồn kho. 1057 (Django đọc điểm, kiểm, trừ rồi `save()` →
  điểm âm; đáp án gọi đúng "race condition đọc-sửa-ghi") liên quan ngang 1012.
- Thêm 1057 cho nhất quán, hoặc giữ nguyên (không sai).

### g22, g24 — chỉ ghi chú

Query = câu hỏi gốc bỏ dấu, cắt ngắn. Không vi phạm FR-020 (không trùng nguyên văn) và hợp mục đích nhóm (đo xử lý không
dấu), nhưng recall nhóm no_diacritics sẽ hơi lạc quan.

## Quyết định DE (2026-10-28)

- g21: viết lại query thành `nodejs p99 latency tang vot du cpu thap, doc file va goi crypto deu cham`, giữ nhãn 1000
  (chờ AIE xác nhận).
- g02: thêm `de-qa-1016` vào `relevant`.
- g05: giữ nguyên.
- Held-out: duyệt luôn (dưới).
- Mọi query đã duyệt có `approved_by: "minhtuann1102"`; `status` hai file ghi ngày duyệt và thay đổi.

## Held-out `rag_golden_holdout.json` (32 query, toàn nhóm vi)

- 32/32 `qa_id` có thật, mỗi query 1 nhãn, 32 cặp khác nhau; **32/32 OK, không sửa nhãn**.
- Đã soát ứng viên curated khác cho từng query; không cặp nào trả lời trọn query bằng nhãn gốc. Gần nhất:
  - h05 (chọn ngưỡng xác suất): 1182 nói chọn điểm vận hành khi dữ liệu lệch lớp, chỉ một phần → không thêm.
  - h02 (Node OOM vài ngày): query nói rõ Node nên 1104 (Java) không thuộc.
  - h15 (test 25 phút, ngữ cảnh ứng dụng khởi tạo lại): 1067 (pytest 25 phút) khác nguyên nhân → không thêm.
  - h16 (xuất triệu dòng, mạng chậm): 1058 (Django export, N+1) khác nguyên nhân → không thêm.
- Ghi chú: h29 (77% từ trùng), h30 (70%) gần như dịch thẳng câu hỏi gốc → dễ hơn các câu còn lại.

## Recall

- Lần đo AIE 2026-10-24 (`plans/20261019-1100-ai-interview-brd-implementation/reports/eval-rag-20261024-shared-ai-db.md`),
  không mở rộng truy vấn: 0,875 = 21/24; **trượt g04, g05, g21**. Báo cáo ghi g21 "top-3 là cặp Node.js performance gần
  nghĩa nhưng không phải nhãn" → khớp lỗi query mâu thuẫn ở trên. g04, g05 là lỗi truy hồi tiếng Việt thuần: nhãn đúng,
  không cặp curated nào khác trả lời trọn query.
- Có LLM viết lại truy vấn (ADR-010): golden chính 1,000, held-out 0,938.
- Chưa đo lại sau khi sửa: `apps/ai-service/.env` chưa có `RAG_ENABLED`, `AI_DB_URL`, key embedding. g02 thêm nhãn → chỉ
  tăng hoặc giữ; g21 viết lại → có thể đổi hai chiều.

## Việc tiếp theo

1. Điền `apps/ai-service/.env` (không commit): `RAG_ENABLED=true`, `AI_DB_URL` = URI `aie_reader` (quickstart 005 §4b),
   `LLM_API_KEY` + `LLM_BASE_URL` có embedding, `EMBEDDING_MODEL` đúng model lúc index.
2. Đo: `cd apps/ai-service && .venv/Scripts/python.exe -m evals.run_rag --out <file>` và
   `--golden evals/rag_golden_holdout.json`; thêm `--no-expand` để so với số 0,875 cũ.
3. Dán bảng recall vào PR, tick T041; Thắng xác nhận query g21 mới.

## Câu hỏi còn mở

- Nhóm vi_to_en (d) trống → FR-020 "phủ đủ 5 nhóm" chưa đạt tới khi có textbook (012, S3): ghi ngoại lệ trong PR.
- Kho Supabase index bằng model embedding nào (3-small hay 3-large Thắng đề xuất ở bf7504f)? `EMBEDDING_MODEL` khi đo
  phải trùng model lúc index.
- `RAG_QUERY_REWRITE` mặc định bật → eval gọi thêm LLM chat viết lại query; key chỉ có embedding thì cần tắt, nhưng số đo
  sẽ khác cấu hình chạy thật.
- AIE đồng ý query g21 mới không, hay muốn giữ ý "event loop bị chặn" và viết thêm một query riêng cho 1017?
