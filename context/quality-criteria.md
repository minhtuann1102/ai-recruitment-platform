# Tiêu chí chất lượng và golden set (cập nhật 2026-10-31)

## Golden set hiện có

| Bộ | Đo gì | Kích thước | Trạng thái |
|---|---|---|---|
| `evals/evaluator_golden.jsonl` | Evaluator chấm đúng band (mốc ±1 band ≥ 80%, tuần 09–15/11) | 48 mẫu (12 câu × 3 mức + 12 adversarial) | **Nhãn 1 người chấm** (`rater_a` = `final.json`, 43 mẫu, PR #46; nhãn người thứ hai bị loại vì không qua kiểm tra nội dung). Đã đo 2026-10-28, xem dưới |
| `evals/rag_golden.json` + `rag_golden_holdout.json` | Truy hồi đúng tài liệu (recall@5) | 24 + 32 truy vấn | AIE gán nhãn; **chưa có query nào được duyệt trên `main`** (PR #49 chưa merge). Số đo gần nhất đo trên nhánh PR #49 (2026-10-28): 1.000 / 0.906, xem báo cáo Phase 05 cho số held-out trên `main` |
| `evals/question_golden.jsonl` | Câu hỏi của AI: đúng level, tự nhiên, đúng hành động (Q5) | 60 câu (mỗi level 6 ask_main, 4 follow_up, 4 hint, 1 wrap_up; 45 AI tự đặt, 15 từ kho) | Dựng 2026-10-24 từ `eval-sim-bank-after2` (Interviewer v2); **nhãn 1 người chấm** (`question_labels/rater_a.json`). Đã đo 2026-10-28 |

## Số đo với nhãn người (2026-10-28, 1 người chấm)

Báo cáo: `plans/reports/eval-261028-2255-golden-rater-a.md`. Không có kappa (một người chấm).

- **Evaluator v3:** ±1 band **0.932** (đạt mốc 80%), MAE 0.69, lệch khoan dung **−0.34** (khắt khe; ngưỡng ±0.3), `answer_type` 0.98, ổn định giữa 3 lần (std 0.05), bắt injection **2/5** (3 mẫu "ghi chú hệ thống / người phỏng vấn đã đồng ý" lọt; 28/10 điểm thấp, nhưng đo lại 31/10 a02 được tới 8.8 ở v3, 5.0–5.6 ở v4). Lệch chính: `extensibility` của câu trả lời strong (2 so với 4), trả lời toàn tiếng Anh hoặc không dấu bị trừ điểm.
- **Câu hỏi (người chấm, Interviewer v2):** hợp level **87%** (câu từ kho cũng 87%), tự nhiên **3.78/5**, đúng hành động 90% (hint **75%**).
- **Judge v1 so với người:** level_fit đồng ý **0.70** (vừa ngưỡng; judge gán "quá dễ" cho 13 câu người thấy vừa), tự nhiên lệch ≤ 1: 0.93, action_ok 0.88. Con số "60% câu kho quá dễ" ngày 24/10 là do judge khắt khe, không phải do kho.

## Evaluator v4 và độ bám nguồn (2026-10-29 đến 30)

- **v4 so với v3 cùng lúc** (`plans/reports/eval-261029-1757-evaluator-v4-evidence-ab.md`, golden không có tài liệu): ±1 band 0.919–0.922 so với 0.919–0.930 (trong mức nhiễu); lệch khoan dung **−0.47** so với −0.34 đến −0.38 (khắt hơn có hệ thống); Evaluator chậm hơn 0.3–0.4 s, cộng thẳng vào TTFT.
- **Ba lỗi cũ đo lại 31/10** (`plans/reports/eval-261031-1422-evaluator-v3-v4-known-issues.md`): v4 chưa sửa lỗi nào. ±1 band 0.921, lệch −0.45, injection 2/5, `extensibility` câu strong trong ±1 chỉ 0.33 (v3 0.58).
- **Evaluator v5 (31/10, `plans/reports/eval-261031-1456-evaluator-v5.md`):** ±1 band 0.963, lệch −0.27 (đạt ngưỡng), thứ tự 1.0, injection 6/8 (LLM tự bắt 0/2), `extensibility` câu strong trong ±1: 0.83. Nhồi thuật ngữ a04 3.1–3.8 nhờ `is_term_list`. Đổi lại TTFT p50 +0.15 s, chi phí +7%. Chỉnh trên chính golden nên số có thể lạc quan; cần held-out có nhãn.
- **Độ bám nguồn** (`plans/reports/eval-261030-1640-phase-05-baseline.md`): gộp 5 lần RAG sạch (345 ý ở `technical`) `no_source` **0.24**, dao động 0.10–0.35; câu kho supported 0.88, câu AI tự đặt 0.63. `intro` và `scenario` không có tài liệu nên không tính.
- **Cách đọc số:** chỉ dùng số gộp nhiều vòng; lần chạy có `rag_health.error > 0` không dùng làm mốc; `supported` là LLM tự khai, chưa phải độ chính xác (cần `judge_support`). Mốc 53% `no_source` trong báo cáo 29/10 là sai (35/98 lượt RAG lỗi).
- **`contradicted`:** `evidence` không chứa ý bị bác, nên đếm qua log `evaluator_sources` hoặc `evaluate_with_raw`. Có 1 ca chặn điểm oan do tài liệu cũ (trạng thái thread trong Java), cần đưa vào golden có tài liệu.
- **TTFT:** số trước 30/10 là tổng thời gian lượt (ASGI in-process đệm body). Đo đúng phải dùng `--serve` hoặc `--base-url`. Hiện p50 3.57–4.06 s / p95 6.94–7.51 s, chưa đạt mốc 3.5 / 6 s; Evaluator chiếm phần lớn.

## Câu hỏi khớp trình độ ứng viên: hiện dựa vào gì

Toàn bộ là **luật bằng code**, chưa có đo chất lượng:

1. **Chọn topic theo level:** catalog gắn `levels` cho từng topic; Planner chỉ chọn topic hợp level (`topics_for(level)`).
2. **Biên độ độ khó theo level** (`docs/ai-service/01` §2.1): Fresher 1–3, Junior 1–4, Middle 2–4, Senior 2–5; bắt đầu theo `start_difficulty` của plan.
3. **Thích nghi theo câu trả lời:** policy (11 luật, `app/policy.py`) tăng độ khó +1 khi trả lời tốt, giảm −1 khi yếu hoặc "không biết"; có hint, clarify, follow-up có giới hạn theo level.
4. **Câu từ kho DE** (`RAG_QUESTION_BANK`): chọn câu có nhãn độ khó gần độ khó hiện tại (1–2 easy, 3 medium, 4–5 hard), bỏ câu lệch 2 bậc.
5. **Interviewer** nhận `difficulty` (1–5) và diễn đạt; không có kiểm tra sau để biết câu ra có thật sự ở mức đó không.

Điểm yếu đã đo:
- Nhãn độ khó trong kho lệch: LLM chấm lại 150 câu, đồng ý với nhãn DE **69%**, nhãn DE thiên về dễ (46/75 câu "easy" được chấm lại là "medium").
- Kho chỉ 4% câu `hard`: senior thường bị hỏi câu `medium` (xem `context/de-data-assessment.md`).
- Câu trong kho cơ bản hơn câu AI tự đặt: phân biệt ứng viên cấp phiên giảm (thứ tự đúng 8/8 → 5/8), xem `plans/reports/eval-261024-1614-rag-question-bank.md`.

## Interviewer chưa tự nhiên: số đo (286 câu, lần chạy `eval-sim-bank-after2`)

| Dấu hiệu | Tỉ lệ |
|---|---|
| Khuôn "Bạn có thể ... không?" | 78% |
| Mở đầu "Giờ mình sang phần ..." | 21% |
| Mở đầu "Mình muốn hỏi ..." | 16% |
| Nhắc lại câu ứng viên vừa nói ("Bạn đã/vừa nêu ...") | 23% |
| Độ dài trung bình | 31.5 từ (văn nói nên ≤ 25) |

Thêm: lượt `hint` thường là **câu hỏi mới** chứ không phải gợi ý cho câu cũ.

## Công cụ (Phase A, 2026-10-24)

- **Văn phong bằng code:** `evals/sim_style.py`, chạy trong mọi lần harness (`summary.style`) hoặc trên file đã lưu: `python -m evals.sim_style <file>`.
- **Bộ câu hỏi + phiếu người chấm:** `python -m evals.question_set build|export|import` (phiếu ẩn persona và nguồn câu hỏi).
- **LLM-judge Interviewer:** `python -m evals.judge_interviewer` (bộ 60 câu, kèm độ đồng ý với nhãn người khi có), hoặc `--run <file phiên>` cho mọi câu của một lần chạy. Prompt `evals/prompts/judge_interviewer.v1.md`, agent `judge` (temperature 0).

### Hướng dẫn người chấm (phiếu CSV)
Mỗi dòng là một câu AI đã hỏi, kèm level, phase, hành động, độ khó, topic, câu hỏi và câu trả lời ngay trước đó. Điền 3 cột:
- `level_fit`: `de` (thấp rõ so với level) / `vua` / `kho` (cao rõ so với level). Fresher: định nghĩa, dùng cơ bản; Junior: cách hoạt động, dùng đúng trong dự án, lỗi thường gặp; Middle: cơ chế, so sánh, debug tình huống thật; Senior: internals, hiệu năng, phân tán, trade-off quy mô lớn.
- `natural`: 1–5 (5 = như người phỏng vấn thật nói; 3 = đúng nhưng cứng, khuôn mẫu, dài).
- `action_ok`: `y`/`n` (ask_main mở đúng topic; follow_up hỏi sâu từ câu trả lời trước; hint là **gợi ý cho câu trước**, hỏi câu khác là `n`; wrap_up không hỏi kiến thức).
Hai người chấm độc lập, không trao đổi; nhập bằng `python -m evals.question_set import --rater <tên> <file.csv>`.

## Số đo đầu tiên (2026-10-24, chưa hiệu chỉnh với người; đã được thay bằng số đo có nhãn người ở trên)

Judge v1 trên 60 câu (`plans/reports/judge-interviewer-261024-1658.json`, không commit):

| Nhóm | n | level_fit "vừa" | "quá dễ" | natural TB | action_ok |
|---|---|---|---|---|---|
| Tất cả | 60 | 70% | 27% | 4.05 | 93% |
| ask_main | 24 | 54% | 46% | 3.92 | 100% |
| hint | 16 | 56% | 31% | 3.75 | 75% |
| Câu từ kho | 15 | 40% | **60%** | 3.80 | 100% |
| Câu AI tự đặt | 45 | 80% | 16% | 4.13 | 91% |
| Junior | 15 | 40% | **60%** | 3.93 | 87% |

Đọc với dè dặt: judge cho `natural` 4.05 trong khi đo bằng code 76% câu theo khuôn (judge có vẻ dễ tính ở mục này) và chấp nhận một số lượt hint thực chất là câu hỏi mới. Chỉ dùng số của judge sau khi đồng ý với người: `level_fit` ≥ 0.7, `natural` lệch ≤ 1 ở ≥ 80% câu. Tín hiệu đáng kiểm bằng nhãn người: câu kho cho junior (nhãn `easy`) bị đánh giá quá dễ.

Văn phong bằng code (harness full, 286 câu): khuôn "Bạn có thể ... không?" 76% (ngưỡng ≤ 40%), 31.5 từ (≤ 25), mở đầu "Giờ mình sang" 20% (≤ 15%): **cả ba chưa đạt**.

**Interviewer v3 (2026-10-28, `plans/reports/eval-261028-2306-interviewer-v3.md`):** khuôn 33%, 16.6 từ, mở đầu phổ biến nhất 15%: **cả ba đạt** (dao động giữa các lần chạy: khuôn 28–38%). Câu kho 100%, thứ tự strong > average > weak 7/8. Còn lại: `follow_up` vẫn 68% theo khuôn; chưa có nhãn người cho câu v3.

## Tiêu chí đề xuất (giai đoạn tiếp theo, xem `context/next-phase-plan.md`)

| Tiêu chí | Cách đo | Ngưỡng |
|---|---|---|
| Evaluator đúng band | Golden set 48 (+12 câu từ kho có đáp án chuẩn), 2 người chấm | ±1 band ≥ 80%, Cohen κ giữa 2 người ≥ 0.6 |
| Câu hỏi đúng level | Bộ 60 câu từ transcript, người chấm "dễ quá / vừa / khó quá" theo level; LLM-judge hiệu chỉnh theo người | "vừa" ≥ 75%; judge đồng ý người ≥ 0.7 |
| Câu hỏi tự nhiên (Q5) | LLM-judge 1–5 + người xem mẫu | TB ≥ 4.0 |
| Văn phong (code, chạy mỗi lần harness) | Tỉ lệ khuôn "Bạn có thể ... không?", độ dài, độ đa dạng câu mở đầu | ≤ 40%; ≤ 25 từ; không câu mở đầu nào > 15% |
| Hint đúng nghĩa | Judge: lượt hint có gợi ý cho câu trước, không đổi câu | ≥ 90% |
