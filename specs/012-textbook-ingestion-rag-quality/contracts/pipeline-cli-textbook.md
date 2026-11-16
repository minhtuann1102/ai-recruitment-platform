# Contract: lệnh CLI textbook

Chạy trong `apps/data-pipeline/`: `python -m pipeline <lệnh>`. Mã thoát dùng chung với
[005 pipeline-cli](../../005-rag-knowledge-base-qa/contracts/pipeline-cli.md): 0 xong; 1 lỗi đầu vào; 2 lỗi preflight
(thiếu key, DB chưa sẵn sàng); 3 ghi xong nhưng còn embedding lỗi; 4 nguồn bị chặn. Mọi lệnh in thống kê cuối lần chạy
(FR-020). `--source` nhận `source_id`; lặp lại được; bỏ trống = mọi nguồn `status: use`.

| Lệnh | Mạng | DB / key | Đọc | Ghi |
|---|---|---|---|---|
| `validate-textbook [--strict]` | Không | Không | manifest, catalog | — |
| `crawl-textbook --source S [--delay 1.0] [--render]` | Có | Không | manifest | `data/raw/textbook/<S>/<UTC>.jsonl` |
| `process-textbook [--source S]` | Không | Không | trang thô mới nhất, manifest, decisions | `data/processed/textbook/<S>.jsonl` |
| `review-textbook-prepare --source S [--batch-size 25] [--seed N]` | Không | Không | đoạn đã xử lý, decisions, đoạn mồi | `data/raw/textbook/review/<S>/batch-NN.json`, `canary-key.json` |
| `review-textbook-score --source S` | Không | Không | lô soát, `judgments-NN.jsonl` | `data/reviews/textbook/<S>-decisions.json` |
| `coverage-textbook [--db]` | Không | Chỉ khi `--db` | đoạn đã xử lý, manifest, truy vấn tình huống | `data/processed/textbook/coverage-report.json` |
| `index-textbook --source S` | Không | Có | đoạn đã xử lý, decisions | `knowledge_chunks` |

## Hành vi từng lệnh

**`validate-textbook`**: luật ở [textbook-source-manifest.md](textbook-source-manifest.md) §2. Mọi lệnh khác gọi kiểm
manifest trước và dừng với mã 1 nếu có lỗi.

**`crawl-textbook`**: chỉ tải trang `status: use` của nguồn `status: use`. Bắt buộc `--source` (không crawl mọi nguồn
một lúc). Trang bị robots cấm, 404, hoặc rỗng sau khi tách section: bỏ qua, in lý do, đếm. Thoát 1 nếu 0 trang ghi
được; thoát 4 nếu host chặn (3 lần 403 / 429 liên tiếp). In: số trang trong manifest, tải được, bỏ theo lý do, thời
gian.

**`process-textbook`**: lấy file thô mới nhất của mỗi nguồn; cắt đoạn (R6), lọc nhiễu (R7), xóa PII, dedup, áp
decisions nếu có. In: trang vào, đoạn tạo, bỏ theo lý do (`too_short`, `code_only`, `link_list`, `blocked_heading`,
`review_drop`, `too_short_after_trim`), trùng, đoạn chưa có quyết định soát. Thoát 1 nếu nguồn chưa có file thô.

**`review-textbook-prepare`**: chỉ đưa vào lô những đoạn chưa có trong decisions; mỗi lô thêm 3 đoạn mồi, xáo vị trí
theo seed. Lô chỉ có `item_id` và `content`: không lộ đoạn nào là mồi. `canary-key.json` nằm cùng thư mục, worker
không được đọc. Thoát 0 và in "không có đoạn cần soát" khi mọi đoạn đã có quyết định.

**`review-textbook-score`**: thoát 1 và không ghi gì nếu: thiếu kết luận cho đoạn nào; lô nào có đoạn mồi không bị
`drop` (in tên lô phải soát lại); chuỗi `trim` không có trong đoạn hoặc có nhiều hơn một lần. Đạt thì gộp vào file
decisions (giữ quyết định cũ, `approved_by` đặt lại rỗng) và in: số `keep` / `trim` / `drop` theo lý do.

**`coverage-textbook`**: định dạng báo cáo ở [data-model.md](../data-model.md) §5. Luôn thoát 0 khi chạy được; chỗ
thiếu nằm trong `gaps`. `--strict` thoát 1 khi không đạt SC-001 hoặc SC-004.

**`index-textbook`**: bắt buộc `--source`. Từ chối (thoát 1) nếu: decisions của nguồn có `approved_by` rỗng; còn đoạn
chưa có quyết định. In số bản ghi từng `source_type` trong kho trước và sau; dừng với mã 1 trước khi ghi nếu kho đã có
bản ghi `textbook` không thuộc dataset `de_textbook_*` nào trong manifest (edge case bản ghi sót). Chạy lại: 0 bản ghi
mới, không gọi API embedding.

## Thứ tự cho một nguồn

```bash
python -m pipeline validate-textbook
python -m pipeline crawl-textbook --source postgresql
python -m pipeline process-textbook --source postgresql
python -m pipeline review-textbook-prepare --source postgresql
#   worker soát -> judgments-NN.jsonl
python -m pipeline review-textbook-score --source postgresql
#   DE duyệt, điền approved_by, commit decisions
python -m pipeline process-textbook --source postgresql
python -m pipeline coverage-textbook
python -m pipeline index-textbook --source postgresql
python -m pipeline coverage-textbook --db
```
