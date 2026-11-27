# Implementation Plan: Bộ test khóa CV–JD do người gán (019 GĐ1)

**Branch**: spec + plan trên `docs/cv-jd-matching-comparison-spec`; code trên `feat/data-pipeline/match-test-set` |
**Date**: 2026-11-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/019-cv-jd-matching-comparison/spec.md`

## Summary

Kết quả GĐ1, toàn bộ ở `apps/data-pipeline` (DE). Không sửa ai-service, không sửa repo FSD:
- **`match-test-build`**: chọn 30 CV × 7 JD = 210 cặp bằng seed, chỉ dựa trên siêu dữ liệu. Lệnh render đầu vào cố
  định cho từng hệ (văn bản CV đầy đủ vi / en, JD dạng tin của FSD, `jd_id` cho bộ chấm 017), kiểm tra loại trùng 017
  và giới hạn 30.000 ký tự, rồi ghi `pairs.json` + `inputs.jsonl` + băm.
- **Bản dịch CV**: worker dịch 30 CV sang tiếng Anh một lần, lưu thành seed. Tên công nghệ giữ nguyên. DE kiểm ≥ 6 CV.
- **Trang gán mù 2 người**: artifact dựa trên trang 017. Mỗi rater có thứ tự ngẫu nhiên riêng và lưu nhãn riêng
  (`labels/<rater>/<pair_id>`). Trang có lô luyện tập 20 cặp lấy từ dev 017.
- **`match-test-lock`**: gộp nhãn A / B, tính weighted kappa (dùng lại `match_eval_agreement`), xuất danh sách cặp cần
  phân xử, rồi ghi `labels.json` cuối + `manifest.json` (SHA-256, seed, phiên bản rubric, ngày khóa, kappa, cờ độ tin
  cậy). Lệnh `match-test-verify` kiểm băm trước mọi lần chấm ở GĐ2.

GĐ2 (chấm 5 hệ, báo cáo) có plan riêng sau khi khóa; [research.md](research.md) R9 chỉ chốt nguyên tắc.

## Technical Context

**Language/Version**: Python 3.11 (data-pipeline), như hiện có

**Primary Dependencies**: không thêm. Dùng lại `pyyaml`, `numpy` có sẵn. Import `app.matching.levels_tracks` /
`skill_normalizer` của ai-service chỉ ở chế độ đọc (cách 017 đã làm cho `match-eval`), nếu không được thì đọc thẳng
`skill_dictionary.yaml`.

**Storage**: seed nhỏ commit được ở `apps/data-pipeline/data/seeds/match_test/`, gồm ID, bản dịch CV (tổng hợp,
không PII), nhãn, manifest. Đầu vào đã render có chứa văn bản JD crawl, nên nằm ở `data/processed/match_test/`
(gitignored); manifest giữ băm của file này.

**Testing**: pytest offline (không mạng, không DB). Fixture gồm CV / JD giả nhỏ.

**Target Platform**: máy DE (CLI); trang gán là artifact claude.ai

**Project Type**: CLI trong monorepo + một trang artifact

**Performance Goals**: không có (210 cặp, dựng < 1 phút)

**Constraints**:
- File code < 200 dòng.
- Không ghi điểm của bất kỳ hệ nào trước khi khóa.
- Mọi file test có seed cố định, chạy lại ra cùng băm.

**Scale/Scope**: 30 CV, khoảng 100–150 JD khác nhau, 210 cặp, 2 rater, lô luyện tập 20 cặp

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Kiểm tra | Kết quả |
|---|---|---|
| I. Database-per-Service | Không đọc hay ghi DB nào; chỉ đọc file 009 / 017 | Đạt |
| II. Gateway & Transport | Không thêm endpoint | Đạt |
| III. Contract-First | Định dạng file + CLI ở [contracts/](contracts/match-test-files-and-cli.md) | Đạt |
| IV. AI Stateless | Không đụng ai-service | Đạt |
| V. Pipeline tái lập được | Seed cố định, băm, in thống kê; văn bản JD crawl không vào git (chỉ ID) | Đạt |
| VI. Quality Gates | pytest cho chọn cặp, render, khóa, kappa; không secret | Đạt |
| VII. Đơn giản | 2 lệnh + 1 lệnh kiểm tra, dùng lại code 017; là task Stretch | Đạt |
| Quy trình | Spec Kit; branch theo conventions; không commit cho tới khi owner yêu cầu | Đạt |

Kiểm lại sau Phase 1: không có vi phạm.

## Project Structure

### Documentation (this feature)

```text
specs/019-cv-jd-matching-comparison/
├── spec.md, plan.md, research.md, data-model.md, quickstart.md
├── label-rubric.md          # rubric v1 (dựa trên 017 + "không đủ thông tin"), DE chốt
├── contracts/match-test-files-and-cli.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
apps/data-pipeline/
├── pipeline/
│   ├── match_test_select.py          # chọn CV, JD, cặp theo seed (thuần)
│   ├── match_test_render.py          # CV → văn bản đầy đủ; JD → tin FSD; JD → văn bản cho rater
│   ├── match_test_build_command.py   # CLI match-test-build: chọn + render + kiểm + ghi + băm
│   ├── match_test_lock_command.py    # CLI match-test-lock / match-test-verify
│   └── cli.py (hoặc jd_match_cli.py) # đăng ký 3 lệnh con
├── data/seeds/match_test/            # pairs.json, cvs_en.json, practice.json, labels_*.json, labels.json, manifest.json
├── data/processed/match_test/        # inputs.jsonl (gitignored), adjudication.json
└── tests/test_match_test_*.py
```

Trang gán: artifact mới "019 gán nhãn CV–JD". Dữ liệu trang được sinh từ `inputs.jsonl` (chỉ văn bản, không siêu dữ
liệu). Trang riêng tư, chỉ chia sẻ link cho FSD.

**Structure Decision**: mọi code ở data-pipeline cạnh `match_eval_*` của 017 để dùng lại loader, agreement, settings.

## Complexity Tracking

Không có vi phạm cần biện minh.
