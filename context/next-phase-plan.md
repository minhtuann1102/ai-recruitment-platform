# Kế hoạch giai đoạn tiếp theo: đo được chất lượng và tận dụng dữ liệu DE (lập 2026-10-24)

Mục tiêu: (1) đo được Evaluator chấm đúng không và câu hỏi có đúng level, tự nhiên không; (2) làm sạch và mở rộng dữ liệu DE để câu hỏi, chấm điểm, báo cáo dựa trên kho đã duyệt; (3) đạt mốc Evaluator 09–15/11, gate voice 22/11, feature freeze 06/12.

Cơ sở: `context/quality-criteria.md`, `context/de-data-assessment.md`, `plans/reports/eval-261024-1614-rag-question-bank.md`.

## Quyết định cần owner và DE chốt trước (tuần 27/10)
- **Q1 giấy phép:** bỏ 1.145 cặp CC-BY-NC-ND (bản dịch vi phạm ND) và xử lý 2.147 cặp `unknown` (tra lại nguồn hoặc bỏ)? Nếu bỏ hết còn ~1.200 cặp → phải bù bằng nguồn permissive hoặc tự viết.
- **Q2 người chấm:** ai là 2 người chấm golden set Evaluator và bộ câu hỏi (owner + FSD/DE?).
- **Q3 phân vai:** DE sở hữu đường ghi (remap topic, nhãn độ khó, câu mới); AIE cung cấp công cụ LLM-judge và tiêu chí, đọc kết quả.

## Phase A: đo được chất lượng (27/10 – 07/11, AIE + người chấm)
1. Golden set Evaluator: 2 người chấm 48 mẫu; thêm 12 mẫu là câu từ kho kèm đáp án chuẩn để đo lợi ích của `reference_answer`. Chạy `run_evaluator --runs 3`. Đích: ±1 band ≥ 80%, κ ≥ 0.6.
2. Bộ câu hỏi (mới): 60 câu lấy từ transcript harness, đủ 4 level × action; người chấm "dễ quá / vừa / khó quá" và tự nhiên 1–5.
3. LLM-judge cho Interviewer (Q5): hiệu chỉnh theo nhãn người ở bước 2 (đồng ý ≥ 0.7) rồi đưa vào harness.
4. Chỉ số văn phong bằng code trong harness: tỉ lệ khuôn "Bạn có thể ... không?", độ dài, độ đa dạng mở đầu.
Xong khi: có số đo thật cho Evaluator, level-fit và tự nhiên.
**Tiến độ 2026-10-28:** đã đo với nhãn **1 người chấm** (người thứ hai bị loại): Evaluator ±1 band 0.932, câu hỏi hợp level 87%, judge level_fit 0.70; xem `context/quality-criteria.md`. Không có kappa. Q2 còn mở nếu báo cáo cần kappa.
**Xong 2026-11-02 (owner chốt):** tiêu chí "có số đo thật" đã đạt, gồm Evaluator ±1 band 0.961 (v6), hợp level 87%, tự nhiên 3.78/5 (nhãn người, Interviewer v2). Phase A chỉ yêu cầu có số đo, không yêu cầu đạt ngưỡng: tự nhiên vẫn dưới đích 4.0 và chưa đo lại bằng nhãn người trên v3, đích κ ≥ 0.6 chưa đo được vì chỉ có 1 người chấm.

## Phase B: làm sạch dữ liệu DE (27/10 – 09/11, DE chính, AIE hỗ trợ công cụ)
1. Giấy phép theo Q1 (DE lọc trong pipeline, ghi rõ trong NOTICE).
2. Remap topic: chạy LLM-judge (`python -m evals.judge_bank`, ~$0.3 cho cả kho) → cặp "off" gán lại topic đúng hoặc `none`; DE duyệt mẫu 10%. Đích: đúng trọng tâm ≥ 85%.
3. Nhãn độ khó: chấm lại bằng rubric neo theo level (easy = nhớ định nghĩa, medium = cơ chế/so sánh/áp dụng, hard = internals/hiệu năng/trade-off); DE duyệt chỗ lệch. Thêm cờ `interview_style` (bỏ câu đố, trắc nghiệm, viết code dài khỏi ngân hàng câu hỏi; vẫn dùng làm snippet).
4. Duyệt bản dịch: điền verdict cho 440 dòng `translation-review.csv` (DE + AIE chia đôi). Đích: lỗi dịch nghiêm trọng < 5%.
5. Câu `hard` cho senior: DE viết hoặc chọn nguồn permissive, ≥ 3 câu hard cho mỗi topic senior (~120 câu), theo format seed có `reviewed_by`.
6. Bù track AI: 12 topic < 3 câu.
Xong khi: ai_db được index lại; harness + golden set chạy lại cho số đo trước/sau.

## Phase C: AIE tận dụng kho đã làm sạch (03/11 – 22/11)
1. Interviewer v3 (tự nhiên hơn): bỏ khuôn "Bạn có thể ... không?", ≤ 25 từ, mở đầu đa dạng; hint lấy từ đáp án chuẩn (gợi ý đúng câu đang hỏi, không đổi câu). **Xong 2026-10-28** (ba ngưỡng văn phong đạt; còn `follow_up` theo khuôn 68%). v4 ngày 02/11: khuôn 8.6%, hint đúng hành động 88% theo Fable, chưa có nhãn người.
2. Follow-up theo đáp án chuẩn: focus lấy từ ý chính của đáp án mà ứng viên chưa nêu (Evaluator v3 đã trả `missing_points` theo đáp án). **Đo 2026-11-03:** 41% `missing_points` trên câu kho có đáp án vẫn là key point catalog đáp án không nói (prompt v6 mâu thuẫn); Evaluator v7 giảm còn 32%, focus nằm trong đáp án 57% → 65%. Bỏ `key_points` khi có đáp án đạt 9% / 80% nhưng chặn oan câu đúng khi đáp án lỗi thời, nên để sau Phase B (`plans/reports/eval-261103-1423-followup-focus-source.md`).
3. Planner chọn topic theo độ phủ kho ở level (tránh topic không có câu phù hợp level). **Code xong 2026-11-03** (`app/plan_bank_coverage.py`, docs 02 mục 3.3.2): topic catalog không có câu gần độ khó bắt đầu thì đổi sang topic cùng nhóm có câu, giữ topic JD; chỉ kiểm bằng test fake, chưa đo LLM thật. **Owner chốt 03/11: đo với Planner LLM thật sau Phase B** (remap topic và nhãn độ khó sẽ đổi số đếm). Cách đo khi ai_db đã index lại: đếm lại độ phủ (`count_bank`, chỉ đọc); gọi `LlmPlanner` không CV/JD cho các cặp track × level còn topic rỗng, mỗi thời lượng 15/30/45 phút; ghi số topic kỹ thuật không có câu trong plan trước và sau `prefer_covered`, số lần đổi, số lần không có ứng viên. Chạy thử 1 lượt trước để ước chi phí rồi mới chạy đủ.
4. Reporter: `study_plan.resources` = câu hỏi liên quan trong kho + nguồn (chỉ nguồn có giấy phép cho phép). **Xong phần lấy từ chunk được trích (PR #56);** lọc giấy phép ở đường đọc làm theo mặc định an toàn 04/11 (chỉ nguồn giấy phép cho phép, bỏ NC-ND và `unknown`; nhánh `thang/stt-voice-hardening`), bỏ khỏi kho vẫn chờ Q1.
5. Scenario: DE thu thập tình huống / system design (vd system-design-primer, CC-BY) làm `textbook` → bật `RAG_TEXTBOOK_ENABLED`.
6. Thử câu kho cao hơn một bậc (junior hỏi medium) **chỉ khi** golden set cho thấy chấm ổn (quyết định 2026-10-24).
Xong khi: harness full + golden set + judge đều đạt ngưỡng trong `context/quality-criteria.md`.

## Hybrid RAG và trích nguồn (bổ sung 2026-10-29, AIE)
Kế hoạch riêng: `plans/261029-1415-hybrid-grounded-rag/plan.md`. Phase 01–03 đã merge (PR #52–#56), Phase 05 đang đo (`plans/reports/eval-261030-1640-phase-05-baseline.md`, `eval-261031-1700-judge-support.md`, `eval-261102-1109-evaluator-v6.md`), nhãn người 60 cặp là tùy chọn, Evaluator v6 chờ owner chốt, Phase 04 phụ thuộc Phase B của DE.

## Phase D: dữ liệu ngoài kho Q&A (song song, DE)
- JD thật (spec 009, đang Draft): cần cho JD Parser và khối `requirements` của báo cáo; tạo golden set JD → topic.
- CV mẫu ẩn danh (hiện 10 CV tự tạo): thêm 20–30 CV đa dạng level để đo CV Parser.

## Mốc
| Ngày | Mốc |
|---|---|
| 27/10 | Chốt Q1–Q3 |
| 07/11 | Phase A xong: có số đo Evaluator, level-fit, tự nhiên. **Đạt 02/11** |
| 09/11 | Phase B xong, ai_db index lại |
| 09–15/11 | Mốc Evaluator ±1 band ≥ 80% |
| 22/11 | Phase C xong; gate voice |
| 06/12 | Feature freeze |

## Rủi ro
- Bỏ dữ liệu vì giấy phép làm kho mỏng → ưu tiên nguồn MIT/CC-BY, tự viết cho topic thiếu.
- Không đủ người chấm → golden set nhỏ hơn (tối thiểu 30 mẫu, 2 người) và báo rõ khoảng tin cậy.
- LLM-judge cùng họ model với agent → thiên vị; luôn hiệu chỉnh với nhãn người trước khi dùng.
