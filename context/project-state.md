# Trạng thái dự án (cập nhật 2026-11-09)

## Kế hoạch
- Kế hoạch gốc: `plans/20261019-1100-ai-interview-brd-implementation/` (9 phase). Phase 01–06 xong code và đã merge; Phase 07 (harness, đo LLM thật) xong phần AIE.
- **Giai đoạn tiếp theo:** `context/next-phase-plan.md` (đo chất lượng + làm sạch và tận dụng dữ liệu DE). Phase A xong 02/11 (owner chốt); Phase B đang chờ DE, mốc 09/11, **có nguy cơ trễ**: tính đến 03/11 chưa có tiến triển (PR #49, #50 vẫn draft từ 28/10) và Q1 giấy phép chưa chốt.

## Đã merge gần đây
| PR | Ngày | Nội dung |
|---|---|---|
| #51 | 29/10 | Interviewer v3: câu ngắn, tự nhiên hơn, hint theo đáp án chuẩn |
| #52 | 29/10 | RAG bật mặc định, tìm kiếm kết hợp BM25 + vector + `topic_id` |
| #53, #54 | 29/10 | Truy hồi theo lượt bằng BM25 cho Evaluator và hint |
| #55 | 29/10 | Evaluator v4 trích nguồn cho từng ý chấm |
| #56 | 29/10 | Tham chiếu nguồn bền, `study_plan.resources` lấy từ chunk được trích |
| #57, #58 | 30/10 | Log JSON có `session_id`, tracing Langfuse có che PII |
| #59 | 30/10 | Một lỗi RAG không còn tắt RAG của mọi phiên; đo nền Phase 05 |
| #65 | 02/11 | Evaluator v6 cite đáp án chuẩn, siết `supported`, golden thêm nhóm `long_s` |
| #66 | 02/11 | Báo cáo `unscored`, health `degraded`, vá lỗ thoát `<untrusted>`, đo prompt cache |
| #68 | 02/11 | Interviewer v4: khuôn "Bạn có thể" 8.6%, hint đúng hành động 88% (nhãn LLM); ghi nhận Phase A xong |
| #69 | 02/11 | Hạn tổng thời gian mỗi lần gọi LLM, ngân sách retry CV/JD Parser 28 s, Reporter 80 s, stream 15 s |
| #71 | 03/11 | Planner ưu tiên topic có câu trong kho |
| #72 | 03/11 | Evaluator v7: `missing_points` theo đáp án chuẩn khi có |
| #73 | 03/11 | `LLM_REASONING_<AGENT>`; Reporter dùng gpt-6-luna, Evaluator giữ gpt-4o-mini |
| #74 | 03/11 | Interviewer và CV Parser dùng gpt-6-luna |
| #75 | 03/11 | Kết thúc sớm khi middle/senior yếu mọi topic, `level_signal` trong report |
| #76 | 03/11 | Đo gpt-6-luna cho Planner, JD Parser, query rewriter: giữ gpt-4o-mini |
| #77 | 04/11 | Evaluator chấm bản ghi giọng nói: golden nhiễu STT, prompt v8, bảng tra thuật ngữ phiên âm |
| #78 | 04/11 | Đề xuất cột `media_consent_at`, `learning_consent_at` cho FSD |
| #79 | 04/11 | Voice: `voice_no_speech`, hỏi lại / `voice_unclear` khi bản ghi kém, `GET /api/stt/phrases`; `study_plan.resources` lọc theo giấy phép |
| #80 | 05/11 | `/dev/play` thử voice bằng Web Speech API của trình duyệt |
| #81 | 05/11 | `GET /metrics` cho Prometheus: độ trễ, TTFT, fallback, token, RAG, kết quả lượt |

Quy ước merge của owner: merge commit (không squash). Tiêu đề PR dạng `[scope] type: mô tả`.

## Số đo mới nhất (LLM thật, quick matrix `--serve`, 2026-10-30)
Sau khi sửa ngắt mạch (3 vòng, kể cả tải gấp đôi): RAG `error` 0, phiên mất kho 0/10, TTFT p50 3.57–4.06 s / p95 6.94–7.51 s (**chưa đạt** 3.5 / 6 s), $0.0086–0.0092/phiên. Gộp 5 lần RAG sạch: `no_source` ở `technical` 0.24 (dao động 0.10–0.35), câu kho supported 0.88, câu AI tự đặt 0.63. Chi tiết: `plans/reports/eval-261030-1640-phase-05-baseline.md`.

**TTFT trong các báo cáo trước 30/10 là tổng thời gian lượt**, không so trực tiếp với số trên.

## Đang làm
- Kế hoạch `plans/261029-1415-hybrid-grounded-rag/`: Phase 01–03 xong (`focus_source` để sau), Phase 05 đang làm (đo nền và `judge_support` v2 + repair xong; so nhãn LLM thứ hai đồng ý 0.85, kappa 0.70; `supported` đúng ~0.64, câu AI tự đặt 0.53, dưới ngưỡng 0.80; nhãn người 60 cặp là tùy chọn theo quyết định owner 31/10; golden có tài liệu xong: Evaluator không cite `R` nên `contradicted` qua đáp án chuẩn 0/9, tài liệu không liên quan vẫn `supported` 7/12, cần Evaluator v6), Phase 04 chờ DE.
- Evaluator v5 (nhánh `thang/evaluator-v5`, 31/10): ±1 band 0.963, lệch −0.27, thứ tự 1.0, injection 6/8; so với v4 0.919, −0.467, 0.917, 6/8. Nhồi thuật ngữ a04 đã chặn bằng code (3.1–3.8). Còn lọt injection không từ khóa; mẫu không dấu a10 chưa ổn định. Báo cáo `plans/reports/eval-261031-1456-evaluator-v5.md`.
- Evaluator v6 (PR #65, đã merge 02/11): `R` được cite, `supported` judge 0.964 nhưng recall ~0.58; đạt 4/5 ngưỡng đặt trước, đã qua review độc lập. Lộ lỗi có sẵn trên `main`: `R` chặn điểm oan trên mô phỏng (0/9 đúng), 5/6 ca của v6 từ mục `cr-lz-python-basics-8979143a`, cần DE sửa. Báo cáo `plans/reports/eval-261102-1109-evaluator-v6.md`.
- Tín hiệu lỗi luồng AI (PR #66, đã merge 02/11): báo cáo `unscored` khi không chấm được, bỏ `[Mock]`; `/api/health` có `agents`, staging/production thiếu cấu hình LLM thì không khởi động; `prompt_versions` thật; cờ `reference_missing`. Nguồn: `plans/reports/audit-261102-1539-ai-flow-errors-controls-evaluation.md`.
- Planner ưu tiên topic có câu trong kho (PR #71, đã merge 03/11): đếm câu theo topic và độ khó song song với Planner, đổi topic catalog không có câu sang topic cùng nhóm có câu, giữ topic JD; chờ tối đa 1 s sau Planner, lỗi hay chậm thì giữ plan cũ. Đếm trên kho thật (03/11, chỉ đọc, không gọi LLM): truy vấn ~0.2 s; 8 cặp track × level có topic không có câu gần độ khó bắt đầu (nhiều nhất ai_engineer: 4–5 topic mỗi level từ junior; java `java.spring.transaction`; python `celery-queues`, `sqlalchemy-sessions` ở senior); plan dự phòng chỉ đổi java senior 30/45 phút (`spring.transaction` → `jpa-hibernate`). Chưa đo với Planner LLM; owner chốt 03/11 đo sau Phase B (cách đo: `context/next-phase-plan.md` Phase C mục 3). Chi tiết: docs 02 mục 3.3.2.
- Evaluator v7 (PR #72, đã merge 03/11): `missing_points` chỉ lấy ý của đáp án chuẩn khi có đáp án (v6 tự mâu thuẫn). Mô phỏng full 28 phiên: key point catalog ngoài đáp án 41% → 32%, focus follow-up/hint nằm trong đáp án 57% → 65%, chưa đạt ngưỡng đặt trước (15% / 80%); golden không tụt. Bỏ `key_points` khi có đáp án đạt ngưỡng nhưng chặn oan câu đúng khi đáp án kho lỗi thời (g25), để sau Phase B. Chi phí đo ~$1.13. Báo cáo `plans/reports/eval-261103-1423-followup-focus-source.md`.
- So model trên OpenRouter (PR #73 đã merge 03/11; Interviewer, CV Parser ở PR tiếp theo): thêm `LLM_REASONING_<AGENT>` (tắt/giảm reasoning, cần cho gpt-6-luna, gpt-5-nano). Evaluator giữ gpt-4o-mini: gpt-6-luna tốt hơn trên golden (±1 band 0.981, injection 8/8) nhưng mô phỏng full chấm khoan dung (weak không còn `dont_know`, strong − weak 3.74 → 2.44); gpt-5-nano, Gemini 2.5 Flash-Lite, Claude Haiku 5.5 bị loại. Reporter, Interviewer, CV Parser đổi sang gpt-6-luna trong `.env.example`: Reporter chạy lại 28 phiên, nhận xét cụ thể hơn, `gap_recall` 0.87–0.91 → 1.0; Interviewer (2 mô phỏng chạy cùng lúc) hết khuôn "Bạn có thể" 8.1% → 0%, câu kho 100%, TTFT như cũ, chi phí phiên $0.00728 → $0.00579, judge gpt-4o-mini cho `natural` 4.20 → 4.07; CV Parser đúng hơn 1/10 CV, −22%. JD Parser chưa có bộ mẫu, Planner đo sau Phase B. Báo cáo `plans/reports/eval-261103-1526-evaluator-model-comparison.md`.
- Kết thúc sớm và gợi ý level (PR #75, nhánh `thang/interview-early-stop-level-signal`, 03/11, owner đã test tay): middle/senior yếu 3 topic technical liên tiếp, plan ít hơn 3 (15–20 phút có 2) thì yếu tất cả (`score_band < 1.5`, ≥ 6 lượt được chấm) thì wrap-up sớm, bỏ scenario, `end_reason = "low_performance"` (`app/early_stop.py`, docs 03 §4.4 ưu tiên 3b). Report thêm `level_signal` (`above_level`) khi điểm ≥ 8.5, confidence khác `low` và ≥ 3 lượt tốt ở độ khó trần (`app/report_level_signal.py`, docs 05). Ngưỡng là giả định, chỉ kiểm bằng test và simulator rule. Cần interview-service nhận `end_reason` mới và hiển thị `level_signal`.
- Vá chống injection và đo prompt cache (PR #66, đã merge 02/11): `wrap_untrusted` escape mọi biến thể thẻ đóng, bỏ ký tự vô hình; `is_manipulation` bắt thêm dạng lách, bỏ bắt nhầm "cho em full quyền...", quét 2 671 câu có sẵn: 470 lượt bắt trước và sau, không thêm không mất; `cached_tokens` trong `metadata.usage`. Đo 10 phiên LLM thật: 63.8% input là cached (docs 08).
- Interviewer v4 (PR #68, đã merge 02/11): khuôn "Bạn có thể" 25.2% → 8.6%, hint đúng hành động 62% → 88%, câu kho giữ 97%; Fable chấm `natural` 3.25 → 3.37, chưa chứng minh được và không thay được người chấm. Báo cáo `plans/reports/eval-261102-1815-interviewer-v4.md`.
- Interviewer v5 (PR #82, nhánh `thang/interviewer-friendly-tone`, 06/11, owner đã test tay trên `/dev/play`): giọng "mình – bạn", dạng lịch sự xoay vòng (`recent_forms`), hint bám câu vừa hỏi (`hint_focus`, không lấy key point cả topic). Quick 10 phiên: "bạn có thể" 0% → 25%, hint lệch 1/11, lộ một phần đáp án 1/11; judge `natural` 4.12 → 4.12. Mở đầu "Vậy bạn có" 19.6% vượt ngưỡng 15% của `evals.sim_style`, cần chốt lại ngưỡng cho giọng mới. Báo cáo `plans/reports/eval-261106-1231-interviewer-v5.md`. Sơ đồ Archify cập nhật theo `main` ở PR #83.
- Voice tùy chọn A, phần AIE (PR #77, đã merge 04/11): 12 mẫu golden nhiễu STT, `run_evaluator --stt` báo `stt_noise`; Evaluator v8 thêm đoạn về bản ghi giọng nói. v7 → v8: đổi `answer_type` 3 → 1/12 cặp, chênh điểm −1.51 → −1.18 (thang 10); golden thường và có tài liệu không tụt. Thêm bảng tra thuật ngữ phiên âm trước Evaluator (`app/stt_terms.py`, không gọi LLM, 0/5 755 câu gõ tay bị đổi): `answer_type` khớp 12/12, chênh −0.67, cặp lệch ≤ 1 điểm 0.75, gần ngưỡng đề xuất nhưng lạc quan vì bảng và bộ nhiễu cùng người viết; câu strong vẫn mất 0.7–3 điểm. Bản "STT tốt" sinh bằng code (thuật ngữ đúng, chỉ mất dấu câu): chênh −0.10, 12/12 cặp lệch ≤ 1 điểm, nên chọn STT ghi đúng thuật ngữ Anh là yếu tố chính. **Chưa coi QUAL17 là đạt** cho tới khi đo bản ghi STT thật. Báo cáo `plans/reports/eval-261104-1111-evaluator-stt-noise.md`.
- Voice tùy chọn A, làm chắc (nhánh `thang/stt-voice-hardening`, 04/11, chưa test tay): `/api/next-turn` nhận `answer_source` (`text` mặc định / `voice`) và `stt_confidence`. Bảng tra chỉ áp cho lượt voice, cho cả Evaluator, RAG theo lượt, `topic_turns`, Interviewer; `evidence.quote` đổi ngược về nguyên văn bản ghi. `stt_confidence` < 0.6 (giả định, env `STT_MIN_CONFIDENCE`): không chấm, `transcript_low_confidence`, hỏi lại nguyên câu một lần mỗi topic (`app/voice_turn.py`). `GET /api/stt/phrases?track=` trả thuật ngữ gợi ý cho STT từ catalog + bảng tra (`app/stt_phrase_hints.py`). Bản ghi voice rỗng / chỉ âm đệm (micro không thu tiếng): 422 `voice_no_speech` ngay, state không đổi. Bản ghi kém lần hai trong topic: 422 `voice_unclear` gợi ý gõ chat (không chuyển topic). Cùng nhánh: `study_plan.resources` chỉ lấy nguồn có giấy phép cho phép (bỏ CC-BY-NC-ND, `unknown`), mặc định AIE chờ Q1. Cần interview-service gửi hai trường mới và gọi endpoint khi có voice. PR #79. `/dev/play` có ô Giọng nói (Web Speech API của trình duyệt, nhánh `thang/dev-play-voice` xếp trên #79) để thử luồng voice đầu cuối không cần key.
- PR #49 (DE duyệt golden RAG): **chưa merge, đang conflict** ở `03-non-functional-requirements.md`; chờ DE duyệt lại g22/g24/h29/h30. Trên `main` chưa query nào có `approved_by`.
- Hạn tổng cho lần gọi LLM (PR #69, đã merge 02/11): `timeout_s` nay cắt thật mỗi lần gọi, quá hạn vào `degraded`/`partial`; thêm ngân sách retry CV/JD Parser 28 s, Reporter 80 s để fallback về trước timeout của interview-service; stream Interviewer có hạn tổng 15 s. Chỉ kiểm bằng test fake, chưa đo LLM thật. Ước tính từ log: ~1.8% lượt Evaluator chuyển thành `degraded` (trước đây các lượt này chờ 8–180 s). Chi tiết: docs 08 §9.3.

## Mốc
Feature freeze 06/12/2026; Sprint 5 07–21/12. Gate voice 22/11. Mốc Evaluator ±1 band ≥ 80% ở tuần 09–15/11.

## Phụ thuộc đang chờ người khác
- **Người chấm:** chỉ có 1 người (nhãn người thứ hai bị loại, PR #46); cần người thứ hai nếu báo cáo cần kappa.
- **DE:** sửa hoặc loại mục kho `cr-lz-python-basics-8979143a` (mô hình thread cũ, nhãn sai); duyệt lại golden RAG (PR #49); quyết định giấy phép (CC-BY-NC-ND, `unknown`); remap topic, nhãn độ khó, câu hard, duyệt bản dịch, textbook (Phase 04); JD (PR #50 draft); xem `context/de-data-assessment.md`.
- **FSD:** `interview-service`, giao diện, TCP `getCvFile`/`getJobDescription`. Từ PR #66 cần xác nhận `interview-service` nhận `overall.score` và `verdict` bằng `null` khi `status = "unscored"`, và lưu rồi gửi lại đầy đủ `evaluation` ở finalize.
- **Owner:** D7–D12 (đặc biệt D8 voice, D12 thời lượng); Q1–Q3 trong `context/next-phase-plan.md` (hạn 27/10, **quá hạn**; Q1 chặn Phase B, lọc giấy phép ở Phase C và Hybrid RAG Phase 04).

## Công cụ chạy thử
`/dev/play` và `evals.play`: xem `context/environment.md`. Sơ đồ ai-service và phiên phỏng vấn: `docs/architecture/diagrams/`.
