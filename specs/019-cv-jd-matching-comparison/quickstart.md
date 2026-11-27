# Quickstart: 019 GĐ1 (bộ test khóa)

Chạy từ `apps/data-pipeline` bằng `.venv`. Không cần mạng hay DB, trừ bước dịch (worker làm một lần).

## 1. Dựng bộ cặp

```bash
.venv/Scripts/python.exe -m pipeline.jd_match_cli match-test-build --seed match-test-v1
# lần đầu: thoát 3, in 30 cv_id cần dịch → worker tạo seeds/match_test/cvs_en.json → DE kiểm 6 CV
.venv/Scripts/python.exe -m pipeline.jd_match_cli match-test-build --seed match-test-v1
```

Kỳ vọng: 210 cặp; mỗi track 35 cặp; 0 trùng 017; độ dài lớn nhất ≤ 30.000; chạy lại cùng băm.

## 2. Trang gán và lô luyện tập

- Sinh dữ liệu trang từ `inputs.jsonl` + `practice.json`, publish artifact riêng tư, gửi link cho FSD.
- Hai rater làm lô luyện tập 20 cặp → DE đọc chỗ lệch → nếu sửa rubric thì tăng phiên bản (v1 → v2) **trước** khi
  mở lô chính.
- Gán lô chính, mỗi người xuất JSON → `seeds/match_test/labels_a.json`, `labels_b.json`.

## 3. Đồng thuận, phân xử, khóa

```bash
.venv/Scripts/python.exe -m pipeline.jd_match_cli match-test-lock --labels-a ... --labels-b ...       # thoát 4, ghi adjudication nháp
# hai người bàn từng cặp lệch, DE điền final
.venv/Scripts/python.exe -m pipeline.jd_match_cli match-test-lock --labels-a ... --labels-b ... \
    --adjudication data/processed/match_test/adjudication.json --write
.venv/Scripts/python.exe -m pipeline.jd_match_cli match-test-verify                                    # thoát 0
```

Kỳ vọng: in kappa (mục tiêu ≥ 0,60, dưới sàn thì có `low_reliability: true`), phân bố nhãn tập cùng nhóm, ghi
manifest.

## 4. Kiểm

```bash
.venv/Scripts/python.exe -m pytest tests/test_match_test_*.py
```

Sửa một nhãn trong `labels.json` → `match-test-verify` thoát 1.
