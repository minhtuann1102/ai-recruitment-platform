# Contract: manifest nguồn textbook

Thư mục: `apps/data-pipeline/data/seeds/textbook_sources/`. Mọi file ở đây được commit và được `validate-textbook`
kiểm. Lý do thiết kế: [research.md](../research.md) R1–R3, R11.

## 1. `<source_id>.yaml` — một file mỗi nguồn

```yaml
source_id: postgresql            # [a-z0-9-]+, trùng tên file; dataset = de_textbook_postgresql
name: PostgreSQL Documentation
kind: official                   # official | supplementary
homepage: https://www.postgresql.org/docs/current/
format: html                     # html | markdown (markdown: trang nằm trên GitHub, tải bản raw)
content_selector: "#docContent"  # CSS vùng nội dung; bỏ trống = article, rồi main (chỉ cho html)
language: en
license: PostgreSQL              # mã SPDX; điều khoản riêng: LicenseRef-<tên>; không tìm thấy: NOASSERTION
license_class: open              # open | restricted (R11); restricted vẫn dùng được cho đồ án
license_url: https://www.postgresql.org/about/licence/
license_quote: "<câu nguyên văn nêu giấy phép của nội dung tài liệu>"
license_checked: 2026-11-15      # ngày worker mở license_url
robots_checked: 2026-11-15       # ngày đọc robots.txt của host
robots_note: "User-agent: * không cấm /docs/"
attribution: "PostgreSQL Documentation, © The PostgreSQL Global Development Group"
status: use                      # use | excluded
excluded_reason: ""              # bắt buộc khi status = excluded
pages:
  - url: https://www.postgresql.org/docs/current/explicit-locking.html
    category: System Design      # category chính của track, hoặc System Design (R2)
    tracks: [java_backend]
    scenarios: [scn.java.flash-sale-inventory]
    topics: []                   # chỉ dùng cho US4
    sections: []                 # tùy chọn: chỉ lấy các section có tiêu đề cấp cao nhất nằm trong danh sách này
                                 # (trang dài nhiều chủ đề, vd README của System Design Primer); rỗng = cả trang
    kind: guide                  # guide | concept | tutorial; KHÔNG nhận trang tham chiếu API
    why: "Khóa mức hàng FOR UPDATE, SKIP LOCKED: căn cứ cho cách chống bán vượt tồn kho"
    status: use                  # use | excluded
    excluded_reason: ""
```

## 2. Luật kiểm của `validate-textbook`

Lỗi (thoát 1):

- `source_id` không khớp tên file hoặc sai mẫu; thiếu trường bắt buộc.
- `license_class` không phải `open` / `restricted`; `license_class: open` mà `license` ngoài danh sách mở (R11);
  `license_class: restricted` mà `license` thuộc danh sách mở.
- `status: use` mà thiếu `license`, `license_class`, `license_url`, `license_quote`, `license_checked`,
  `robots_checked`, `attribution`.
- `status: excluded` mà thiếu `excluded_reason`. Lý do loại hợp lệ là lý do truy cập (robots cấm, site chặn, sau đăng
  nhập / trả phí, điều khoản cấm thu thập tự động), không phải loại giấy phép.
- Trang `status: use` thuộc nguồn `status: excluded`.
- Cặp (URL, `sections`) trùng trong cùng nguồn hoặc giữa hai nguồn (cùng URL với `sections` khác nhau là hợp lệ); URL không cùng host với `homepage` (trừ `format: markdown`).
- `tracks`, `scenarios`, `topics` có mã không tồn tại trong catalog ai-service; `scenarios` có mã không thuộc track
  nào trong `tracks`.
- `category` khác category chính của mọi track trong `tracks` và khác `System Design`; `tracks` gồm các track khác
  category chính mà `category` không phải `System Design`. Trang có `topics` thì `category` phải bằng category của
  topic đầu tiên.
- Trang không có cả `scenarios` lẫn `topics`.

Cảnh báo (vẫn thoát 0; thành lỗi khi có `--strict`):

- Track có mặt trong manifest mà không có nguồn `kind: official` nào (FR-002).
- Tình huống của một track đã có mặt mà dưới 3 hoặc trên 5 trang `status: use` (FR-003).
- Tình huống không có dòng trong `scenario-queries.yaml`.

Lệnh in bảng: track × số nguồn chính thức × số trang; tình huống × số trang; nguồn × `license` × `license_class`.

Nguồn có giấy phép yêu cầu kèm nguyên văn thông báo: lưu thông báo ở `notices/<source_id>.txt` cùng thư mục và nhắc
tên file trong `attribution`.

## 3. `scenario-queries.yaml`

```yaml
scn.java.flash-sale-inventory:
  query_en: "prevent overselling inventory under concurrent requests row locking optimistic locking"
  terms: [row-level lock, SELECT FOR UPDATE, optimistic locking, isolation level, idempotency]
```

- `query_en`: một dòng tiếng Anh, 6–20 từ, mô tả kỹ thuật cốt lõi của tình huống; dùng cho kiểm tra truy hồi (R10).
- `terms`: 3–6 thuật ngữ mà câu trả lời tốt thường nhắc; giúp worker chọn trang, không dùng khi tìm.
- Khóa phải là mã `scn.*` có trong catalog.

## 4. `review-canaries.json`

Mảng ít nhất 12 đối tượng `{ "content": "...", "kind": "nav | code_only | off_topic | reference_table" }`. Mỗi `content`
có dạng giống đoạn thật (dòng đầu là đường dẫn tiêu đề). `review-textbook-prepare` chọn 3 đoạn mỗi lô theo seed; đoạn
mồi không bao giờ được ghi vào kho.
