# Contract: CLI `python -m pipeline` (chạy trong `apps/data-pipeline/`)

| Lệnh | Story | Cần DB | Cần key | Việc | Mã thoát |
|---|---|---|---|---|---|
| `validate [--strict] [--extra-catalog DIR]` | US1 | không | không | kiểm seed ([qa-seed-format.md](qa-seed-format.md)), in báo cáo phân bố | 0 sạch · 1 có lỗi |
| `process [--extra-catalog DIR]` | US2 | không | không | `validate` → làm sạch → 2 bản ghi/cặp → dedup → ghi `data/processed/interview_qa.jsonl` (sắp theo `qa_id`, `chunk_type`) | 0 · 1 seed lỗi |
| `index` | US3 | có | có | `process` → preflight → embed bản ghi mới → ghi / cập nhật / dọn ([knowledge-chunks-io.md](knowledge-chunks-io.md)) | 0 · 1 seed lỗi · 2 preflight lỗi · 3 có embedding lỗi |
| `search "<query>" [--k 5] [--category C] [--difficulty D] [--topic-id T] [--chunk-type question\|qa_pair]` | US3 | có | có | truy hồi chỉ đọc, in top-k: điểm, `qa_id`, `chunk_type`, `topic_id`, 120 ký tự đầu | 0 · 2 preflight lỗi |
| `eval [--k 5]` | US4 | có | có | kiểm golden set → recall@k tổng + theo nhóm + truy vấn trượt + top-3 mỗi truy vấn; ghi báo cáo `data/processed/eval-<timestamp>.json` | 0 khi chạy xong (kể cả < 0.8) · 1 golden set lỗi · 2 preflight lỗi |
| `crawl react-docs [--max-pages N] [--delay S] [--render]` | US5 | không | không | crawl nguồn mẫu → `data/raw/react_docs/<timestamp>.jsonl` | 0 · 1 thu 0 record |

`--extra-catalog` chỉ dùng khi soạn trước với YAML đề xuất; nghiệm thu không dùng (research R5).

## Thống kê mỗi lần chạy (FR-016, constitution V)

`process` và `index` in một khối và ghi `data/processed/run-report-<timestamp>.json`:

```text
records_in        cặp Q&A đọc được
records_rejected  cặp bị loại (kèm danh sách qa_id + lý do)
chunks_out        bản ghi sau dedup
dedup_ratio       bản ghi trùng / bản ghi trước dedup
# chỉ index:
embedded          số bản ghi đã gọi embed
embed_errors      số bản ghi embed lỗi sau retry
inserted | updated | skipped_same | skipped_other_dataset | deleted
cleanup           done | skipped (embed_errors > 0)
```

## Env (`apps/data-pipeline/.env.example`)

| Biến | Mẫu | Dùng bởi |
|---|---|---|
| `LLM_API_KEY` | trống (placeholder) | `index`, `search`, `eval` |
| `LLM_BASE_URL` | `https://openrouter.ai/api/v1` | như trên |
| `EMBEDDING_MODEL` | `openai/text-embedding-3-small` | như trên; tên lưu DB = phần sau `/` cuối |
| `EMBEDDING_DIMENSIONS` | `1536` | preflight kiểm số chiều |
| `AI_DB_URL` | `postgresql://postgres:secret@localhost:5534/ai_db` | `index`, `search`, `eval` |
| `CATALOG_DIR` | `../ai-service/app/catalog` | `validate`, `process`, `index` |
