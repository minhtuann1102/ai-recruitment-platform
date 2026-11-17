# Handoff 012 textbook — lô thử java_backend (2026-11-16 → 17)

Branch: `feat/data-pipeline/textbook-pipeline` (xếp trên `docs/textbook-ingestion-spec`). Chưa push, chưa PR.

## Đã xong
- PR-A code T002–T034 commit (591 test xanh, `.venv/Scripts/python.exe -m pytest -q` trong `apps/data-pipeline`). 33 task tick trong tasks.md.
- T035 review opus: HOÃN (quota tuần 91%+). Làm khi quota reset.
- Lô thử (T041–T043): crawl 5 nguồn (13 URL, 0 bỏ) → process → prepare 14 lô → 4 worker soát → score cả 5 nguồn thoát 0 (mọi mồi bị drop).

| Nguồn | keep | trim | drop | bản ghi sau soát |
|---|---|---|---|---|
| postgresql | 98 | 12 | 12 | 110 |
| spring-framework | 31 | 21 | 11 | 50 |
| hibernate-orm | 47 | 2 | 10 | 49 |
| spring-boot | 20 | 12 | 0 | 31 |
| system-design-primer | 10 | 12 | 2 | 22 |
| **Tổng** | | | | **262** |

Coverage offline (BM25): 4/4 `scn.java.*` có 61–105 đoạn, keyword hit hạng #1 cả 4. SC-001/SC-004 toàn cục "không đạt" vì mới 1/6 track (đúng kỳ vọng).

## Việc DE (T044) — trước khi index
- Duyệt `apps/data-pipeline/data/reviews/textbook/<S>-decisions.json` (drop + trim). In lại danh sách: `python -m pipeline review-textbook-score --source <S>`.
- Đọc mẫu 50 đoạn keep (SC-006), điền `approved_by`.
- Id worker không chắc (nên xem):
  - spring-framework: drop `98093b7f`, `4116f86c` (bảng nhưng có câu riêng), `9ce466ab` (other); trim `aaecc0a1` cắt câu thật về reactive return types; keep `8bfd29d2`.
  - postgresql: drop `710abf66`, `a939f220`, `cff79304`, `96d48ab3`, `98b9f06a`, `70678359`; trim `a0c13995`, `9ecbb7d6` (cắt câu tràn từ đoạn trước); keep `beb6c5e2`, `375927bf`, `bcce77fc`, `d87e1da6`, `2748d49d`.
  - hibernate-orm: drop `92df7140`, `03dbe2c4`, `6f66b43f`, `f73b60e4`; keep `80d5be27`, `399208b7`, `22ec380d`, `23ae6c70`, `79dbef75`, `67b7800e`.
  - spring-boot / system-design-primer: `e17c26e2` (mỏng sau trim), `b2ca6534` (chủ yếu POM), `61a19fcf`, `3deece6f`.
- spring-framework trim 21/63, sdp trim 12/24: tỉ lệ cao, soát kỹ.

## Lệch so với spec / contract (ghi vào PR)
- Lọc `sections` khớp ở BẤT KỲ cấp `heading_path` (Hibernate html_single bọc mọi chương dưới "Preface").
- Crawler nhận cả URL `raw.githubusercontent.com` lẫn `github.com/.../blob/...`; bỏ ref (GithubRawClient không có tham số ref).
- Soát gộp 3–4 lô / worker (spec: 1 lô / worker) để tiết kiệm quota; mồi lặp lại giữa các lô của cùng worker.
- Worker dùng chung scratchpad nên script ghi judgments bị đè lẫn nhau; score kiểm đủ item_id + mồi nên file cuối hợp lệ, nhưng nội dung judgments pg-05 / hibernate do script worker R2 sinh, chạy lại bởi R4.
- CLI nạp handler lười (`textbook_cli._lazy`).
- DRY: `textbook_processed_jsonl_reader.py` là wrapper mỏng của `textbook_processed_io.py`, gộp khi review.
- `docs/architecture/data-pipeline.md` §1, §9 còn "6000+" (ngoài phạm vi T034).

## Tiếp theo
1. T044 (DE) → T045 process lại + coverage → T046 PR-B (branch mới từ main sau khi PR-A merge; seed YAML + decisions + review-canaries đang untracked/ở PR-A).
2. T035 review opus khi quota reset → T036 PR-A.
3. T047 index cần `.env` DB + key embedding.

## Câu hỏi còn mở
- AIE chưa trả lời 5 câu ở spec (đã có mặc định).
- spring-data-jpa vẫn `pages: []` — có bổ sung trang không?
- hibernate-orm, spring-boot chưa có file `notices/`.
