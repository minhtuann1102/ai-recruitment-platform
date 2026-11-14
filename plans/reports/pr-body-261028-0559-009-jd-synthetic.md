## Summary
Sprint 2 · `009-jd-crawling-seeding` · **US5 `synth-jd` (T030–T037, phần bù của S2-DE-1)**: sinh JD synthetic cho các ô (nhóm, cấp bậc, thành phố) còn thiếu. DE chốt (spec Clarifications 2026-10-28): **chỉ bù sàn đa dạng FR-022**, không bù đủ 500 JD.

## Thay đổi
- `pipeline/jd_gap_planner.py`: lưới 5 nhóm × 6 cấp × 3 thành phố; bù số lượng tới `--target` rồi bù sàn 20 cho mỗi nhóm / Junior–Mid–Senior / thành phố; deterministic.
- `pipeline/jd_synthetic_prompt.py` + `jd_synthetic_generator.py`: code chọn công ty hư cấu (không trùng công ty crawl), kỹ năng của nhóm, kinh nghiệm, lương; LLM chỉ viết tiêu đề + mô tả. Hậu kiểm: JSON, 0 PII / URL, cụm cấm, kỹ năng cụ thể ngoài nhóm, round trip qua `build_record` của `process-jd` (không bị loại, nhóm / cấp / thành phố suy lại đúng ô, đủ section). Lỗi → thử lại tối đa 2 lần rồi bỏ.
- `pipeline/jd_synth_command.py` + lệnh `python -m pipeline synth-jd [--target 500] [--limit N] [--dry-run]`: ghi `data/raw/jd/synthetic/<UTC>.jsonl` (gitignore), mã thoát 0 / 1 / 2 / 3 theo contract.
- Sửa sau review: kỹ năng chung chung (kiểm thử, bảo mật, cloud, cơ sở dữ liệu) của nhóm khác không còn làm JD bị loại; nhóm vẫn kiểm qua round trip.
- Test: client LLM giả (`tests/jd_fake_llm.py`), toàn bộ suite data-pipeline **368 passed**.
- Spec: Clarification "chỉ bù sàn", SC-001 ghi chú hạ mục tiêu; tasks.md tick T029, T037; `specs/README.md` dòng 009.

## T037 trên dữ liệu thật (2026-10-28, máy DE)
- Key LLM trong `.env` (DeepSeek) trả 402 hết số dư → 24 JD do Claude viết trong phiên của DE theo đúng tham số `build_params`, chạy qua cùng `generate_one` / `check_candidate`, ghi bằng `write_synthetic`. **24/24 đạt hậu kiểm lần đầu**. Chi phí LLM: 0.
- `synth-jd --target 0` (bù sàn): frontend +12, mobile_fullstack +9, backend +3; Đà Nẵng lên 20.

| Chỉ số | Trước | Sau |
|---|---|---|
| JD hợp lệ | 341 | **365** (341 crawl + 24 synthetic, 6.6%) |
| frontend / mobile_fullstack | 8 / 11 | **20 / 20** |
| Đà Nẵng | 8 | **20** |
| `pii_remaining` | 0 | 0 |
| Kế hoạch bù sàn còn lại | 24 JD | **0** |
| JD đủ điều kiện seed T041 | 186 | **210** (191 nếu `experience_levels` không có Manager) |

## Còn mở
- US4 seed chờ migration `company_profiles` (004) + job-service (007) của FSD; cần biết `experience_levels` có `Manager` không (nếu không: map Manager → Lead hoặc bù thêm ~10 JD).
- Chạy `synth-jd` với LLM thật sau này (khi nạp key) để bù tới 500 nếu nhóm cần lại.
