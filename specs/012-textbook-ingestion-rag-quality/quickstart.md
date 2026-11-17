# Quickstart: kiểm chứng Textbook Ingestion

Chạy trong `apps/data-pipeline/` với venv của pipeline. Định dạng file: [data-model.md](data-model.md); lệnh và mã
thoát: [contracts/pipeline-cli-textbook.md](contracts/pipeline-cli-textbook.md). §0–§4 không cần mạng (trừ §2), không
cần DB. `<S>` là một `source_id` của lô thử, ví dụ `postgresql`.

## 0. Test offline

```bash
python -m pytest -q
```

Mong đợi: mọi test đạt, gồm `tests/test_textbook_*.py` và các test cũ của 005 / 009 (parser react.dev,
`knowledge_chunk_writer`).

## 1. Manifest hợp lệ (US1, FR-001–FR-005)

```bash
python -m pipeline validate-textbook --strict
```

Mong đợi: thoát 0; bảng in cho thấy track `java_backend` có ≥ 1 nguồn `official`, mỗi tình huống `scn.java.*` có 3–5
trang. Thử đổi `license` của một nguồn thành `Proprietary` → thoát 1 và nêu tên nguồn; hoàn tác.

## 2. Crawl đúng danh sách (FR-006–FR-008)

```bash
python -m pipeline crawl-textbook --source <S>
git status --short apps/data-pipeline/data/raw
```

Mong đợi: log có dòng kiểm robots; số request bằng số trang `status: use` của nguồn; file
`data/raw/textbook/<S>/<UTC>.jsonl` có đúng số dòng "tải được" trong thống kê; `git status` không liệt kê file nào
dưới `data/raw`.

## 3. Cắt đoạn, soát, áp quyết định (FR-009–FR-014, FR-021)

```bash
python -m pipeline process-textbook --source <S>
python -m pipeline review-textbook-prepare --source <S>
#   giao mỗi batch-NN.json cho một worker theo hướng dẫn C
python -m pipeline review-textbook-score --source <S>
#   DE đọc danh sách drop / trim, điền approved_by trong data/reviews/textbook/<S>-decisions.json
python -m pipeline process-textbook --source <S>
```

Mong đợi: lần `process-textbook` đầu in số đoạn chưa có quyết định bằng số đoạn tạo; `review-textbook-score` thoát 0
và báo mọi đoạn mồi bị `drop` (sửa tay một kết luận đoạn mồi thành `keep` → thoát 1, nêu tên lô; hoàn tác); lần
`process-textbook` thứ hai in 0 đoạn chưa có quyết định, và không đoạn nào dài quá 1.600 ký tự phần thân.

## 4. Độ phủ và truy hồi từ khóa (FR-022, FR-023, SC-001, SC-004)

```bash
python -m pipeline coverage-textbook
```

Mong đợi sau lô thử: 4/4 tình huống `scn.java.*` có ≥ 1 đoạn; `gaps` nêu tên tình huống dưới 3 đoạn hoặc trượt truy
hồi nếu có. Sau khi nạp đủ 6 track: 28/28 tình huống ≥ 1 đoạn, ≥ 80% tình huống ≥ 3 đoạn, ≥ 80% trúng trong 3 kết quả
đầu (`--strict` thoát 0).

## 5. Ghi vào kho (FR-015–FR-020, SC-003, SC-005) — cần `.env` có DB và key embedding

```bash
git switch main && git pull
python -m pipeline index-textbook --source <S>
python -m pipeline index-textbook --source <S>
python -m pipeline coverage-textbook --db
```

Mong đợi: lần đầu in số bản ghi từng `source_type` trước / sau, `interview_qa` và `job_description` không đổi,
`textbook` tăng đúng số đoạn; embedding lỗi = 0. Lần hai: 0 bản ghi mới, không gọi API embedding.
`coverage-textbook --db` thêm cột `vector_hit`.

Kiểm trực tiếp trên kho (chỉ đọc):

```sql
SELECT metadata->>'dataset' AS dataset, category, count(*)
FROM knowledge_chunks WHERE source_type = 'textbook' GROUP BY 1, 2 ORDER BY 1;

SELECT count(*) FROM knowledge_chunks
WHERE source_type = 'textbook'
  AND (metadata->>'source_url' IS NULL OR metadata->>'license' IS NULL);   -- mong đợi 0
```

## 6. Thêm trang cho track sau (US2, FR-017)

Thêm một trang của nguồn dùng chung vào manifest với track thứ hai, rồi chạy lại §2–§5 cho nguồn đó.

Mong đợi: chỉ đoạn mới cần soát; `index-textbook` in số bản ghi mới bằng số đoạn mới; đoạn cũ của trang dùng chung có
`metadata.tracks` gồm cả hai track; số bản ghi của nguồn khác không đổi.

## 7. Lô thử với ai-service (SC-007) — AIE làm

1. DE gửi AIE: tên dataset đã nạp, số bản ghi, category đã dùng.
2. AIE đo nền với `RAG_TEXTBOOK_ENABLED=false`: vài phiên `java_backend`, ghi tỉ lệ ý có căn cứ ở lượt scenario, độ
   trễ lúc bắt đầu buổi và theo lượt.
3. AIE bật `RAG_TEXTBOOK_ENABLED=true`, khởi động lại ai-service, kiểm log `bm25_corpus_loaded` tăng đúng số bản ghi,
   đo lại cùng các phiên.
4. DE ghi số đo và quyết định (giữ / đổi cỡ đoạn, nạp tiếp hay dừng) vào `tasks.md`.
