# Data Model: RAG Knowledge Base — Interview Q&A

Feature không tạo bảng. Bảng duy nhất được ghi: `knowledge_chunks` trong `ai_db` — schema tại
[rag-design.md §3](../../docs/architecture/rag-design.md), giá trị từng cột tại
[contracts/knowledge-chunks-io.md](contracts/knowledge-chunks-io.md). File này mô tả thực thể và quan hệ.

```text
Topic (catalog YAML, AIE) 1 ──< N  Interview Q&A Item (seed JSON, DE) 1 ──< 2  Knowledge Chunk (ai_db)
                                              N >── 1..N  Golden Query
Crawl Source 1 ──< N Raw Record  ──(DE chuyển thể tay)──>  Interview Q&A Item
Pipeline Run Report: 1 / lần chạy process|index
```

## Interview Q&A Item (seed)

Trường và luật kiểm tra: [contracts/qa-seed-format.md](contracts/qa-seed-format.md).

- Định danh: `qa_id` bất biến; xóa cặp = bỏ khỏi seed (lần `index` sau dọn bản ghi), không tái dùng id.
- Suy ra lúc xử lý: `category` = `category` của topic; `dataset` = `de_interview_qa`.
- Vòng đời trong kho:

  | Thay đổi trong seed | Kết quả sau `index` |
  |---|---|
  | Thêm cặp | +2 bản ghi |
  | Sửa đáp án | `qa_pair` mới thay bản cũ; `question` giữ nguyên |
  | Sửa câu hỏi | cả 2 bản ghi thay mới |
  | Đổi `topic_id` / độ khó / tags, nội dung giữ nguyên | cập nhật cột, không embed lại |
  | Xóa cặp | 2 bản ghi bị dọn |
  | `topic_id` thành mồ côi (catalog đổi) | `validate` lỗi → `index` dừng ở bước seed; sửa seed rồi chạy lại |

## Topic (catalog, chỉ đọc)

`id`, `category` từ `apps/ai-service/app/catalog/*.yaml` → `topics[]`. `scenarios[]` không phải topic hợp lệ cho
`topic_id` (FR-002). Mỗi topic có ≥ 2 cặp lúc nghiệm thu (SC-001).

## Knowledge Chunk (record xử lý / bản ghi kho)

Record sau `process` (dòng JSONL) có đúng các khóa sẽ ghi: `content`, `content_hash`, `source_type`, `category`,
`difficulty`, `topic_id`, `language`, `metadata`. `index` thêm `embedding`, `embedding_model`.
Bất biến: một `qa_id` có đúng 1 `question` + 1 `qa_pair` (trừ khi bị dedup — báo trong run report).

## Pipeline Run Report

Khóa: [contracts/pipeline-cli.md](contracts/pipeline-cli.md) § Thống kê. Ghi ra `data/processed/` (gitignore).

## Golden Query

Trường: [contracts/qa-seed-format.md](contracts/qa-seed-format.md) § Golden set. Trạng thái nhãn:
`approved_by` trống = chưa duyệt → AIE điền khi duyệt (FR-020).

## Crawl Source / Raw Record (US5)

| Thực thể | Trường |
|---|---|
| Crawl Source (cấu hình trong code crawler) | `name`, `base_url`, `start_paths`, `license`, `robots_url`, `delay_seconds`, `max_pages` |
| Raw Record (`data/raw/<source>/*.jsonl`, gitignore) | `url`, `title`, `sections[]` (`heading_path`, `text`), `crawled_at` (ISO 8601 UTC), `license` |

Raw Record đã scrub email/số điện thoại trước khi ghi (FR-023).
