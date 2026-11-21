# Contract: lệnh pipeline của 017 (`python -m pipeline <lệnh>`, chạy trong `apps/data-pipeline/`)

Parser và handler nằm trong `pipeline/jd_match_cli.py`; `__main__.py` chỉ đăng ký (giống `textbook_cli`).

## `index-jd-match [--rebuild] [--limit N]`

- Vào: `data/processed/jd_normalized.jsonl` (đầu ra `process-jd` của 009).
- Làm:
  1. Dựng văn bản và bản ghi (data-model §1).
  2. Kiểm trùng hash.
  3. Preflight DB.
  4. Kiểm `embedding_model` của dataset `jd-match`; `--rebuild` thì xóa dataset trước.
  5. Gọi `plan_writes` + `write_records`.
- Thống kê in ra và ghi vào run report: `input`, `skipped_no_group`, `skipped_duplicate_hash`, `embedded`,
  `embed_errors`, `inserted`, `updated`, `deleted`, `embedding_tokens`.
- Mã thoát: 0 xong; 1 lỗi đầu vào hoặc lệch model (chưa có `--rebuild`); 2 preflight hoặc cấu hình; 3 còn lỗi embedding.
- Không có chế độ mock: vector giả không bao giờ ghi vào ai_db (research R8).

## `match-eval-sheet --out data/processed/match_eval/`

- Vào: `data/seeds/match_eval/{cvs.json,pool.json}`, cùng ai-service đang chạy (`AI_SERVICE_URL`,
  `AI_SERVICE_INTERNAL_TOKEN`).
- Làm: với mỗi CV, gọi endpoint với `job_ids` = pool để lấy đúng tập JD qua lọc cứng (dùng chung bộ lọc, không chép
  logic). Sau đó viết bảng soát markdown: thông tin CV, rồi các JD xếp ngẫu nhiên theo seed cố định, mỗi JD có tiêu đề,
  level, kỹ năng và trích đoạn yêu cầu đọc từ `jd_normalized.jsonl`. Bảng **không có điểm hay thứ hạng**. Kèm một file
  `labels.template.json`.
- Mã thoát: 0; 1 thiếu file hoặc CV không có JD nào qua lọc; 2 không gọi được ai-service.

## `match-eval [--rounds 4] [--out specs/017-cv-jd-matching/eval-results.md]`

- Vào: `cvs.json`, `pool.json`, `labels.json`, cùng ai-service đang chạy ở chế độ thật.
- Làm:
  1. Mỗi CV gọi endpoint với `job_ids` = pool, `page_size` = 50.
  2. Xếp lại kết quả theo `score`, `components.skill_match`, `components.cosine`.
  3. Tính P@5 (nhãn ≥ 1) và nDCG@5 (gain = nhãn).
  4. Chạy thêm `--rounds` vòng có và không có `job_ids` để đo độ trễ: p50 / p95 của `timing_ms.score` và của thời gian
     phía client.
  5. Tính chi phí: token từ `metadata.usage` và run report `index-jd-match` mới nhất, nhân với `EMBEDDING_PRICE_PER_1M`.
- Ra: bảng markdown (bộ dữ liệu, chất lượng theo từng cách, độ trễ, chi phí, hạn chế), kèm JSON thô trong
  `data/processed/match_eval/`.
- Mã thoát: 0; 1 thiếu nhãn cho một cặp qua lọc, hoặc nhãn thừa không qua lọc; 2 không gọi được ai-service; 4 có
  phản hồi `degraded` hoặc `mock` (dừng, không ghi bảng).

## Env mới (thêm vào `apps/data-pipeline/.env.example`)

`AI_SERVICE_URL` (mặc định `http://localhost:8000`), `AI_SERVICE_INTERNAL_TOKEN`, `EMBEDDING_PRICE_PER_1M` (mặc định
`0.02` USD).
