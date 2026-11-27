# Contract: lệnh CLI và trang gán (019 GĐ1)

Định dạng file: [data-model.md](../data-model.md). Chạy từ `apps/data-pipeline` (`python -m pipeline.<cli> ...`, cùng
cách gọi các lệnh 017).

## `match-test-build`

```
match-test-build [--seed match-test-v1] [--cvs-per-track 5] [--jds-per-cv 7] [--extend-seed <s>] [--dry-run]
```

- Đọc: `seeds/candidates/candidate_cvs.json`, `seeds/match_eval/{cvs,pool}.json`, `processed/jd_normalized.jsonl`,
  run-report `index-jd-match` mới nhất, `seeds/match_test/cvs_en.json` (nếu thiếu: chỉ ghi `pairs.json` và in danh
  sách CV cần dịch, mã thoát 3).
- Ghi: `seeds/match_test/pairs.json`, `processed/match_test/inputs.jsonl`; in thống kê (số cặp theo loại, ngôn ngữ JD,
  track, cờ, số JD khác nhau, số lần dùng lại JD lớn nhất, độ dài văn bản lớn nhất) và băm.
- `--extend-seed`: thêm cặp mới, giữ nguyên các cặp cũ; chỉ được dùng khi chưa có `manifest.json`.
- Mã thoát: 0 xong; 1 thiếu file / vi phạm ràng buộc (trùng 017, > 30k ký tự, JD không có trong index); 2 đã khóa
  (có manifest), từ chối ghi đè; 3 thiếu bản dịch.
- Chạy lại cùng seed và đầu vào ra cùng băm.

## `match-test-lock`

```
match-test-lock --labels-a seeds/match_test/labels_a.json --labels-b seeds/match_test/labels_b.json \
                [--adjudication processed/match_test/adjudication.json] [--write]
```

- Không có `--adjudication`: tính đồng thuận, in kappa / khớp / lệch ≤ 1 / số "u", ghi `adjudication.json` nháp
  (`final` rỗng cho cặp lệch), rồi thoát 4 (chưa phân xử).
- Có `--adjudication` đủ `final`: kiểm phân bố tập cùng nhóm (cảnh báo nếu một mức < 15%). Với `--write`, ghi
  `labels.json` + `manifest.json`. Không có `--write` thì chỉ in.
- Mã thoát: 0 khóa xong; 1 file sai; 2 đã khóa; 4 còn cặp chưa phân xử.

## `match-test-verify`

```
match-test-verify
```

So băm hiện tại với `manifest.json`. Thoát 0 nếu khớp, 1 nếu lệch (in file lệch). Mã chấm GĐ2 MUST gọi lệnh này
trước.

## Trang gán (artifact)

- Dữ liệu nhúng: lô luyện tập (`practice_id`, văn bản CV vi, văn bản JD cho rater, nhãn dev ẩn) + 210 cặp (`pair_id`,
  văn bản CV vi, văn bản JD cho rater). Không có track / level / nhóm / ngôn ngữ / điểm.
- Lưu: `labels/<A|B>/<pair_id>` = `0|1|2|"u"`; `practice/<A|B>/<practice_id>`.
- Mỗi rater thấy thứ tự hoán vị theo seed của mình; có thanh tiến độ và nút "Xuất JSON" (định dạng `labels_*.json`).
- Rubric v1 hiện cố định ở đầu trang.
