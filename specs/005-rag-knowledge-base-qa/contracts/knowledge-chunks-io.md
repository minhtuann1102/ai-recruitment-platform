# Contract: Ghi / đọc `knowledge_chunks` cho `interview_qa`

Hợp đồng chung DE (ghi) ↔ AIE (đọc). Schema bảng: [rag-design.md §3](../../../docs/architecture/rag-design.md)
(DDL trong `scripts/init-databases.sh`, AIE sở hữu). Hợp đồng này chỉ chốt **giá trị** ghi vào từng cột.

## Ánh xạ: 1 cặp Q&A → 2 bản ghi

| Cột | `question` | `qa_pair` |
|---|---|---|
| `content` | câu hỏi đã làm sạch | `"{question}\n\n{answer}"` (đều đã làm sạch) |
| `content_hash` | `md5(lower(strip(content)))`, `content` đã NFC (research R3) | như trái |
| `embedding` | vector 1536 chiều của `content` | như trái |
| `embedding_model` | tên chuẩn **không tiền tố provider**: `text-embedding-3-small` (research R2) | như trái |
| `source_type` | `interview_qa` | `interview_qa` |
| `category` | `category` của topic trong catalog | như trái |
| `difficulty` | `easy` \| `medium` \| `hard` | như trái |
| `topic_id` | `topic_id` của cặp | như trái |
| `language` | `vi` \| `en` | như trái |
| `metadata` | xem dưới | xem dưới |

`metadata` (JSONB), khóa cố định:

| Khóa | Giá trị |
|---|---|
| `qa_id` | `de-qa-NNNN` |
| `chunk_type` | `question` \| `qa_pair` |
| `dataset` | `de_interview_qa` |
| `tags` | mảng string (có thể rỗng) |
| `source_url` | URL nguồn hoặc `null` khi synthetic |
| `license` | giá trị `license` của cặp |
| `synthetic` | bool |

## Ngữ nghĩa ghi (chỉ pipeline DE)

- Bản ghi mới: `INSERT ... ON CONFLICT (content_hash) DO NOTHING`.
- Hash đã có cùng `dataset`: cập nhật `category`, `difficulty`, `topic_id`, `language`, `metadata`; giữ `embedding`.
- Hash đã có khác `dataset`: không đụng, đếm "skipped".
- Dọn: xóa bản ghi `source_type = 'interview_qa'` cùng `dataset` có hash không thuộc lần chạy; chỉ khi lần chạy 0 lỗi
  embedding. Không bao giờ xóa bản ghi khác `dataset`.
- Chi tiết thứ tự bước: [research.md R4](../research.md).

## Ngữ nghĩa đọc (AIE `retrieve`, và `search`/`eval` chỉ đọc của DE)

- **Tìm tương đồng**: `ORDER BY embedding <=> :query_vec LIMIT :k` (cosine), điểm trả về `1 - (embedding <=> :q)`.
  Bộ lọc tùy chọn, ghép `AND`: `source_type`, `metadata->>'chunk_type'`, `category`, `difficulty`, `topic_id`.
  Luôn lọc `embedding_model = '<tên chuẩn>'` và embed truy vấn bằng đúng model đó. `k` mặc định 5.
  **Dedup theo `qa_id`** (rag-design §4): lấy dư (vd 4k bản ghi), giữ bản ghi điểm cao nhất của mỗi `qa_id`, rồi cắt
  còn k — để `question` và `qa_pair` của cùng một cặp không chiếm hai chỗ.
- **Tra đáp án mẫu theo cặp** (FR-018): `WHERE source_type = 'interview_qa' AND metadata->>'qa_id' = :qa_id AND
  metadata->>'chunk_type' = 'qa_pair'` — không qua tìm tương đồng.
- Mỗi kết quả trả tối thiểu: `id`, `content`, `score`, `metadata.qa_id`, `metadata.chunk_type`, `topic_id`,
  `category`, `difficulty`. Log `qa_id` + điểm mỗi lần gọi (FR-017).
- Đường đọc MUST NOT ghi vào bảng (FR-010).
