# Phase 05. Evaluator và golden set

## Context Links
- [plan.md](plan.md) · [design 05](../../docs/ai-service/05-rubric-and-final-report.md) (rubric) · [design 09 §10.2](../../docs/ai-service/09-agent-quality-evaluation.md) (tầng 2) · FR-AI-030–032 · NFR QUAL01–08

## Overview
- **Priority:** P1 (rủi ro lớn nhất của dự án) · **Status:** Evaluator LLM + hậu kiểm + prompt v1 (có mẫu neo) xong code (2026-10-22, `thang/evaluator-llm`); golden set và công cụ đo ở nhánh `thang/evaluator-golden-set` · **Tuần:** W3–W5
- Evaluator LLM chấm mỗi câu trả lời theo rubric 4 tiêu chí, band 0–4, có trích dẫn; hậu kiểm bằng code; đo bằng golden set có nhãn người.

## Key Insights
- Độ khắt khe đến từ rubric + luật code (cap, quote kiểm chứng), không từ model to. Evaluator nằm trên đường nóng nên dùng model nhỏ, output gọn (`max_tokens` 350).
- Cùng họ model với Simulator thì dễ "hiểu ý nhau": golden set có nhãn người là thước đo chính.
- Mock hiện có sẵn các luật hậu kiểm cơ bản (cap hint, dont_know, manipulation) để tái dùng.

## Requirements
- FR-AI-030 (Evaluation đủ trường), 031 (quote fuzzy ≥ 0.9, cap completeness theo ý có bằng chứng, misconception thì `technical_accuracy ≤ 1`, hint thì ≤ 3), 032 (dont_know bỏ qua Evaluator, manipulation band 0).
- NFR: QUAL01 (±1 band ≥ 80% mốc W5, ≥ 90% cổng cuối), QUAL02 (MAE ≤ 0.6), QUAL03 (độ lệch khoan dung trong [−0.3, +0.3]), QUAL05–08, SEC03, USE02 (không dấu).

## Architecture
`Evaluator.run(level, phase, topic, difficulty, turn_kind, topic_turns, question, answer, reference_snippets) → Evaluation`; prompt có phần tĩnh dài (rubric, kỳ vọng theo level) đặt đầu để hưởng prompt caching.

## Related Code Files
- **Tạo:** `app/agents/evaluator.py`, `app/prompts/evaluator.v1.md`, `app/evaluation_checks.py` (hậu kiểm), `evals/evaluator_golden.jsonl`, `evals/run_evaluator.py`, `evals/metrics.py`, `tests/test_evaluation_checks.py`.
- **Sửa:** `app/mock_evaluator.py` (giữ làm fallback), `app/turn_engine.py` (gọi Evaluator qua registry).

## Implementation Steps
1. Viết `evaluation_checks` thuần code (quote kiểm chứng bằng `difflib`, cap, ép 0) và unit test mọi luật.
2. Prompt v1 với rubric, kỳ vọng theo level, luật "dài ≠ tốt", dữ liệu người dùng trong khối `untrusted`.
3. Golden set v1 (≥ 40 mẫu cho W5, mở rộng 70 sau): câu hỏi từ catalog (Java, Node, Python, AI) × 4 level, ba mức chất lượng, ≥ 10 adversarial (injection, nhồi keyword, lan man, sai nhưng tự tin, quá ngắn, tiếng Anh, không dấu). **2 người gán nhãn độc lập**, họp các mẫu lệch ≥ 2 band. Không lấy nguyên văn từ `interview_qa` đã index.
4. `run_evaluator.py`: ±1 band, MAE, độ lệch khoan dung, thứ tự đúng, kappa, nhất quán 3 lần, bắt manipulation, evidence hợp lệ; lưu kết quả vào `plans/reports/`.
5. Lặp prompt tới khi qua mốc W5 (≥ 80% ±1 band, độ lệch khoan dung trong ngưỡng); mỗi lần đổi prompt hoặc model chạy lại.

## Todo List
- [x] Hậu kiểm bằng code + test (`app/evaluation_checks.py`, `tests/test_evaluation_checks.py`)
- [x] Prompt evaluator.v1 (rubric, kỳ vọng level, 10 luật, 5 mẫu neo); agent `app/agents/evaluator.py` nối vào `/api/next-turn` qua `AGENT_EVALUATOR_MODE`
- [ ] Golden set v1 (≥ 40) có nhãn 2 người: **48 mẫu đã soạn** (`evals/evaluator_golden.jsonl`), phiếu gán nhãn `evals/label_sheet.py`; chờ 2 người chấm
- [ ] `run_evaluator.py` + báo cáo đầu tiên: script + chỉ số đã có (`evals/evaluator_metrics.py`, chạy thử bằng LLM giả); chờ khóa API và nhãn để có báo cáo
- [ ] Qua mốc W5; mở rộng lên 70 mẫu

## Success Criteria
- Mốc W5: ±1 band ≥ 80%, độ lệch khoan dung trong [−0.3, +0.3], bắt manipulation 100%. Cổng cuối (Phase 09): ±1 band ≥ 90%.

## Delivery (bàn giao)
- Evaluator LLM + `evaluation_checks` + prompt v1
- Golden set v1 (≥ 40 mẫu, 2 người gán nhãn) + `run_evaluator.py` + báo cáo `plans/reports/eval-evaluator-*.md`

## Cách test và nghiệm thu
1. `pytest` mọi luật hậu kiểm (quote, cap, ép 0)
2. `python -m evals.run_evaluator --prompt v1 --model <m>` in ±1 band, MAE, độ lệch khoan dung, thứ tự đúng, nhất quán 3 lần, bắt manipulation
3. Mốc W5: ±1 band ≥ 80%, độ lệch khoan dung trong [−0.3, +0.3], manipulation 100%; không đạt thì đổi prompt và chạy lại, **không** chỉnh nhãn

## Đồng bộ tài liệu (bắt buộc, cùng PR với thay đổi)
BRD §8 (bảng chỉ số ghi số đo), NFR QUAL01–08 sang "Đã đo" kèm ngày, FR-AI-030–032, design 05 (rubric nếu đổi) và 09 §10.2 (ngưỡng thực tế), L2 §9.
Sau khi sửa: chạy `python apps/ai-service/scripts/check_docs.py` (link, ID, truy vết BR→FR→NFR, số lượng trong mục lục).

## Nhánh
`thang/evaluator-llm` rồi `thang/evaluator-golden-set` (golden set và công cụ đo). Mỗi nhánh một PR; mô tả PR ghi lại kết quả các bước test ở trên.

## Risk Assessment
- Cần người gán nhãn thứ hai (2–3 giờ mỗi lần) → đặt lịch sớm; thiếu người thì golden set nhỏ hơn và ghi rõ giới hạn.
- Chấm dễ dãi → tăng luật cứng bằng code trước khi đổi sang model lớn.
- Chi phí mỗi lần chạy ≈ dưới $0.15 (giả định) → chạy theo thay đổi, không chạy trong CI.

## Security Considerations
- Câu trả lời đưa vào khối `untrusted`; band bị ép 0 với `manipulation`; CV không được đưa cho Evaluator.

## Next Steps
Phase 06 dùng Evaluation cho policy và báo cáo; Phase 07 dùng cùng golden set cho so sánh biến thể.
