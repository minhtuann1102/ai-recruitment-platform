# Vì sao hybrid (Postgres FTS) kém hơn vector, và BM25 trong bộ nhớ sửa được (2026-10-29)

Đo trên ai_db dùng chung (Supabase, 4.503 cặp `qa_pair`, `text-embedding-3-small`), golden chính 24 query +
held-out 32 query (toàn bộ tiếng Việt). LLM viết lại truy vấn bật (gpt-4o-mini, OpenRouter). Có vài lần viết lại lỗi
(`APIConnectionError` / `APITimeoutError`); khi đó truy vấn dùng từ điển thay thế, ảnh hưởng như nhau tới mọi cách đo.

File kết quả:
- `plans/reports/eval-rag-hybrid-main.json`, `eval-rag-hybrid-holdout.json` (`run_rag --mode both`)
- Script thử nghiệm nằm trong scratchpad, không commit.

## 1. Hybrid Phase 01 (Postgres FTS `simple` + vector, RRF trọng số bằng nhau)

| Bộ | Cách | recall@5 | MRR |
|---|---|---|---|
| Chính | vector | 1.000 | 0.951 |
| Chính | hybrid FTS | 0.958 | 0.873 |
| Held-out | vector | 0.938 | 0.857 |
| Held-out | hybrid FTS | 0.906 | **0.622** |

Tìm từ khóa mất **1.7–4 s mỗi truy vấn** (seq scan `to_tsvector` trên khoảng 9k dòng, không có index). Ngưỡng là 300 ms.

## 2. Nguyên nhân (đã kiểm trên dữ liệu)

1. **`ts_rank_cd` không có IDF.** Từ hiếm ("idempotent") nặng ngang từ phổ biến ("dữ", "liệu", "khi"), nên đây không
   phải BM25.
2. **Tiếng Việt bị tách theo âm tiết** (`simple`): "dữ liệu" thành "dữ" + "liệu", khớp gần như mọi chunk. ai_db không
   có `unaccent` hay `pg_trgm`. Locale `en_US.UTF-8` (chuyển chữ thường đúng với chữ có dấu).
3. **Chunk rất dài đứng đầu mọi truy vấn:**
   - `cr-doocs-advanced-java-7d93ea88` (10.237 ký tự) và `-ad68497c` (11.146 ký tự) đứng hạng 1 cho nhiều truy vấn
     không liên quan. Độ dài `qa_pair`: p50 626, p90 2.231, p99 3.971.
   - Chuẩn hóa độ dài của `ts_rank_cd` (tham số 1, 32) không sửa được.
4. **Vector gần đạt trần** nhờ viết lại truy vấn sang tiếng Anh, nên một đường nhiễu gộp ngang hàng chỉ kéo thứ hạng xuống.
5. **Golden set phạt oan một phần:**
   - Mỗi truy vấn chỉ gán 1 `de-qa`. Câu crawl cùng ý không được tính, ví dụ g03 → "thiết kế idempotent",
     h02 → "memory leak Node.js".
   - Truy vấn trong golden là câu của ứng viên, còn ứng dụng thật gửi `title | key_points` của topic.

## 3. BM25 trong bộ nhớ (Okapi, k1=1.2, b=0.75)

Cách làm:
- Nạp 4.503 `qa_pair` một lần (1.1 s, chỉ đọc).
- Token gồm âm tiết đơn + cặp âm tiết liền nhau (bắt từ ghép), bỏ từ chức năng.
- Truy vấn BM25 dùng truy vấn gốc + bản viết lại tiếng Anh (cùng văn bản với đường vector).

| Cách | Chính recall / MRR | Held-out recall / MRR |
|---|---|---|
| vector | 1.000 / 0.951 | 0.938 / 0.852 |
| chỉ BM25 (uni+bi, gốc+viết lại) | 1.000 / 0.903 | 0.906 / 0.746 |
| vector + BM25, RRF w=1.0 | 1.000 / 0.938 | 0.969 / 0.885 |
| **vector + BM25, RRF w=0.5** | **1.000 / 0.972** | **0.969 / 0.891** |
| vector + BM25, RRF w=0.3 | 1.000 / 0.972 | 0.969 / 0.891 |

- Truy vấn BM25: p50 0.8–5.9 ms, max 16 ms (so với 1.7–4 s của FTS).
- Chỉ dùng âm tiết đơn và truy vấn gốc (không viết lại) thì yếu hơn trên held-out (MRR 0.814–0.827).
- **Thận trọng:** bộ đo nhỏ. Recall khác nhau 1 truy vấn trên held-out (0.938 → 0.969), MRR +0.02 / +0.04. Có xu hướng
  nhưng chưa đủ mạnh về thống kê.

## Đề xuất

1. **Bỏ Postgres FTS, thay bằng BM25 trong bộ nhớ** (uni+bi, gốc + viết lại, trọng số 0.5) cho đường từ khóa của
   hybrid:
   - Nạp corpus lúc khởi động hoặc lần đầu dùng, làm mới theo TTL.
   - Lỗi nạp thì hybrid tự lùi về vector và báo `degraded`.
2. Tới khi BM25 xong: **đặt `RAG_HYBRID=false` mặc định** để không dùng bản FTS đang kém.
3. **Dữ liệu (DE, Phase 04):** cắt các chunk > 4k ký tự (cũng làm loãng embedding).
4. **Đo:**
   - Mở rộng golden lên ≥ 100 truy vấn, gồm truy vấn dạng `title | key_points` như ứng dụng thật gửi.
   - Cho phép nhiều câu đúng mỗi truy vấn (DE duyệt câu `cr-*` cùng ý). Thêm nDCG.

## 4. Đã làm (BM25 trong code, 2026-10-29)

Đề xuất 1 đã làm (`app/rag/bm25_index.py`); không cần đề xuất 2. Eval với code thật
(`eval-rag-hybrid-bm25-{main,holdout}.json`):

| Bộ | Vector recall / MRR | Hybrid BM25 recall / MRR |
|---|---|---|
| Chính | 1.000 / 0.951 | 1.000 / 0.972 |
| Held-out | 0.938 / 0.823 | 0.938 / 0.875 |

Held-out thấp hơn thử nghiệm (0.969) vì lần chạy này có nhiều lần viết lại qua OpenRouter bị lỗi.

Độ trễ gắn snippet lúc start, ba thay đổi để giữ dưới hạn 5 s:
- **Pool kết nối** (`psycopg_pool`, tối đa 4). Lượt có cache: 2.5–3.3 s → 1.0–1.4 s.
- **Hạn 3.5 s cho viết lại + embed:** quá hạn thì topic vẫn có snippet từ `topic_id` + BM25 (`degraded`), không mất
  hết. Lần đầu sau khởi động: quá hạn, 0 snippet → 4.6 s, đủ snippet.
- **Corpus đọc trong thread, ngoài pool; hết TTL chỉ nạp lại khi dấu vân tay đổi.** Đo: nạp + dựng (~4 s) tranh GIL
  làm event loop chậm ~1.4 s và request đang chạy quá hạn (6.0 s). Kiểm dấu vân tay mất 0.3 s.

Còn lại: request đến trong ~6 s đầu sau khởi động (corpus chưa nạp xong) vẫn quá hạn. Chưa có cache thì hybrid chậm
hơn legacy 2–3 s, vì luôn viết lại + embed mỗi topic.

## Câu hỏi còn mở
- Có chấp nhận ai-service giữ corpus trong RAM (~10 MB, 4.5k cặp; lớn lên khi thêm textbook) không, hay chờ DE thêm
  index BM25 phía DB (Supabase không có `pg_search`/ParadeDB)?
- Ai bổ sung nhãn nhiều câu đúng cho golden set: DE hay AIE?
