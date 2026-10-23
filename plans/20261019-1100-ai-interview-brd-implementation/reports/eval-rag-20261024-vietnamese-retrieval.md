# Cải thiện truy hồi tiếng Việt thuần, 2026-10-24

Mục tiêu: nhóm tiếng Việt thuần có recall@5 thấp nhất (0.667 trên golden chính, ~0.6 trên held-out). Đo trên ai_db dùng chung (9.006 bản ghi) và một bản sao cục bộ embed lại bằng `text-embedding-3-large` (đọc bằng `aie_reader`, không ghi vào kho chung; đã xóa sau khi đo).

## Bộ đo
- Golden chính: `evals/rag_golden.json`, 24 truy vấn (en, mixed, không dấu, vi).
- **Held-out tiếng Việt thuần: `evals/rag_golden_holdout.json`, 32 truy vấn** (h01–h08 viết sau khi chốt từ điển; h09–h32 viết **trước** thử nghiệm viết lại và đổi model; không sửa sau khi xem kết quả). Nhãn bản nháp, chờ DE duyệt.

## Kết quả (`python -m evals.retrieval_experiment`)

| Cấu hình | Golden chính | · vi | · không dấu | **Held-out vi (32)** |
|---|---|---|---|---|
| small / gốc | 0.875 | 0.667 | 0.800 | 0.594 |
| small / từ điển | 0.958 | 1.000 | 0.800 | 0.625 |
| small / LLM viết lại | 1.000 | 1.000 | 1.000 | 0.875 |
| **small / gốc + viết lại** (đã cài) | **1.000** | 1.000 | 1.000 | **0.938** |
| large / gốc | 0.958 | 0.833 | 1.000 | 0.812 |
| large / từ điển | 1.000 | 1.000 | 1.000 | 0.875 |
| large / viết lại | 1.000 | 1.000 | 1.000 | 1.000 |
| large / gốc + viết lại | 1.000 | 1.000 | 1.000 | 0.969 |

Chi phí và độ trễ: viết lại P50 1.6 s, P95 2.2 s, ~250 token/lần; embed lại kho bằng large ~1.6 triệu token (≈ $0.21). Đường chạy thật sau khi cài (`run_rag`, `RAG_QUERY_REWRITE` bật): golden chính **1.000**, held-out **0.938**; trượt h02 (rò rỉ bộ nhớ Node, top-3 là cặp crawl về Node gần nghĩa) và h09 (`de-qa-1100` đứng thứ 2 nhưng nhãn là `de-qa-1101`). Gắn snippet cho plan vẫn ~0.47 s vì topic trúng theo `topic_id`, không cần viết lại.

## Kết luận
- Từ điển chỉ giúp ít (+0.03 trên held-out); bỏ khỏi đường chính, giữ làm phương án khi LLM lỗi.
- **Viết lại truy vấn bằng LLM** là cải thiện lớn nhất không cần đụng dữ liệu: 0.594 → 0.938. Đã cài, mặc định bật.
- **Đổi sang `3-large`** tự nó nâng lên 0.812 không cần LLM, kết hợp viết lại đạt 1.000. Cần DE index lại và team duyệt: đề xuất ở [ADR-010](../../../docs/architecture/adr/adr-010-embedding-model-and-vietnamese-retrieval.md).

## Câu hỏi chưa giải quyết
- DE có đồng ý index lại bằng `3-large` (1536 chiều) không?
- Bộ đo nhỏ, nhãn bản nháp: cần DE duyệt và bổ sung truy vấn nhắm cặp crawl.
