# Data Model: Textbook Ingestion & RAG Quality

Không có bảng mới. Bảng `knowledge_chunks` (`ai_db`, DDL do AIE sở hữu) giữ nguyên; xem
[`docs/architecture/rag-design.md`](../../docs/architecture/rag-design.md) §3 và
[005 knowledge-chunks-io](../005-rag-knowledge-base-qa/contracts/knowledge-chunks-io.md). File này chỉ ghi phần mới.

## 1. File và vị trí

| Thực thể | Vị trí | Commit | Định dạng |
|---|---|---|---|
| Manifest nguồn | `apps/data-pipeline/data/seeds/textbook_sources/<source_id>.yaml` | Có | [contract](contracts/textbook-source-manifest.md) |
| Truy vấn tình huống | `apps/data-pipeline/data/seeds/textbook_sources/scenario-queries.yaml` | Có | cùng contract §3 |
| Đoạn mồi | `apps/data-pipeline/data/seeds/textbook_sources/review-canaries.json` | Có | mảng `{content, kind}` |
| Trang thô | `apps/data-pipeline/data/raw/textbook/<source_id>/<UTC>.jsonl` | Không | §2 |
| Đoạn đã xử lý | `apps/data-pipeline/data/processed/textbook/<source_id>.jsonl` | Không | §3 |
| Lô soát + kết luận worker | `apps/data-pipeline/data/raw/textbook/review/<source_id>/` | Không | [hướng dẫn soát](contracts/textbook-review-instructions.md) |
| Quyết định soát | `apps/data-pipeline/data/reviews/textbook/<source_id>-decisions.json` | Có (sau khi DE duyệt) | §4 |
| Báo cáo độ phủ | `apps/data-pipeline/data/processed/textbook/coverage-report.json` + bản in | Không (dán bảng vào PR) | §5 |

## 2. Trang thô (một dòng JSONL)

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `source_id` | string | khớp tên file manifest |
| `url` | string | đúng URL trong manifest |
| `title` | string | h1 của trang |
| `sections` | `[{heading_path: [string], text: string}]` | `heading_path` không gồm tên trang; code giữ dạng khối ``` |
| `crawled_at` | string ISO 8601 UTC | |

Trang lỗi (404, robots cấm, rỗng sau khi tách) không ghi dòng; lý do nằm trong log và thống kê của lệnh.

## 3. Đoạn đã xử lý = bản ghi sẵn sàng ghi vào `knowledge_chunks`

| Cột / khóa | Giá trị |
|---|---|
| `content` | `"<Tên trang> > <H2> > <H3>\n\n<thân đoạn>"`, đã `clean_text` + `scrub_pii`, đã áp `trim` nếu có |
| `content_hash` | `content_hash(content)` của 005 (md5 trên nội dung đã chuẩn hóa) |
| `source_type` | `"textbook"` |
| `category` | từ manifest (R2): category chính của track hoặc `System Design`; US4: category của topic |
| `difficulty` | `null` |
| `topic_id` | `null`; US4: mã topic đầu tiên trong `topic_ids` của trang |
| `language` | `language` của nguồn (mặc định `"en"`) |
| `metadata.dataset` | `"de_textbook_<source_id>"` |
| `metadata.chunk_type` | `"doc_section"` |
| `metadata.source_id` | mã nguồn |
| `metadata.source_url` | URL trang |
| `metadata.license` | `license` từ manifest (SPDX, `LicenseRef-…` hoặc `NOASSERTION`) |
| `metadata.license_class` | `open` hoặc `restricted`, từ manifest |
| `metadata.attribution` | dòng ghi nguồn từ manifest |
| `metadata.title` | tên trang |
| `metadata.heading_path` | mảng tiêu đề cha |
| `metadata.tracks` | mảng mã track, sắp theo bảng chữ cái |
| `metadata.scenario_ids` | mảng `scn.*`, sắp theo bảng chữ cái; có thể rỗng với trang US4 |
| `metadata.topic_ids` | mảng mã topic (US4); mặc định rỗng |
| `metadata.review` | `"keep"` hoặc `"trimmed"`; đoạn chưa soát không có khóa này |
| `metadata.original_hash` | hash trước khi `trim`; chỉ có khi `review = "trimmed"` |

**Luật kiểm**:

- Cỡ thân đoạn ≤ 1.600 ký tự; đoạn dưới 30 từ không được tạo (R6).
- Trùng `content_hash` trong cùng nguồn: giữ đoạn đầu theo thứ tự (URL trong manifest, vị trí trong trang), đếm vào
  `dedup`.
- `tracks`, `scenario_ids`, `topic_ids` lấy từ dòng trang trong manifest; mọi mã phải tồn tại trong catalog.
- Đoạn có quyết định `drop` không xuất hiện trong file đã xử lý.

## 4. Quyết định soát

```json
{
  "source_id": "postgresql",
  "reviewed_at": "2026-11-16",
  "approved_by": "",
  "decisions": {
    "<content_hash trước khi áp>": {"verdict": "keep"},
    "<content_hash>": {"verdict": "drop", "reason": "nav"},
    "<content_hash>": {"verdict": "trim", "remove": ["Edit this page on GitHub"]}
  }
}
```

- `reason` của `drop`: `nav` (điều hướng / mục lục), `code_only`, `off_topic`, `not_self_contained`, `reference_table`,
  `other`.
- `approved_by` để trống tới khi qua cổng mồi (`review-textbook-score` thoát 0) rồi điền `auto:canary-gate` (DE bỏ duyệt tay 2026-11-17); `index-textbook` từ chối file có `approved_by` rỗng.
- Áp `trim`: xóa từng chuỗi trong `remove` (khớp nguyên văn, mỗi chuỗi đúng một lần); thân đoạn sau khi cắt dưới 30 từ
  thì coi như `drop` với lý do `too_short_after_trim`.

## 5. Báo cáo độ phủ

| Phần | Nội dung |
|---|---|
| `sources` | mỗi nguồn: giấy phép, số trang dùng / loại, số đoạn, số `drop` theo lý do |
| `tracks` | mỗi track: số nguồn chính thức, số đoạn |
| `scenarios` | mỗi `scn.*`: số đoạn gắn, `keyword_hit` (bool), `vector_hit` (bool, chỉ khi `--db`), thứ hạng đoạn trúng đầu tiên |
| `gaps` | tình huống 0 đoạn; tình huống dưới 3 đoạn; tình huống trượt kiểm tra truy hồi |
| `totals` | tổng đoạn; tỉ lệ tình huống ≥ 1, ≥ 3 đoạn; tỉ lệ trúng từ khóa / vector |

## 6. Vòng đời một nguồn

```
ứng viên → [worker kiểm giấy phép + robots] → manifest (status use / excluded)
        → [DE duyệt manifest] → crawl → process (lọc nhiễu, dedup)
        → review-prepare → [worker soát] → review-score → [DE duyệt decisions]
        → process (áp quyết định) → coverage → index → [báo AIE]
```

Thêm trang cho track sau: sửa manifest của nguồn → crawl → process → chỉ đoạn chưa có quyết định mới phải soát →
`index-textbook` lại nguồn (đoạn cũ đi nhánh `UPDATE`, không embed lại).
