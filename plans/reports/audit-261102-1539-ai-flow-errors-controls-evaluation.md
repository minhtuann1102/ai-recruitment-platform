# Rà soát luồng AI: lỗi, kiểm soát, đánh giá (2026-11-02)

Phạm vi: `apps/ai-service`, nhánh `thang/evaluator-v6`. interview-service, APISIX, FE, data-pipeline không có trong phạm vi nên mọi kết luận về chúng là chưa kiểm. Không đổi code sản phẩm.

Mức bằng chứng: **[TH]** tái hiện hoặc đo thật. **[Code]** tự đọc lại code. **[Rà]** subagent đọc code, chưa kiểm lại.

## Kết luận
- **Xử lý lỗi tốt ở chỗ không làm sập phiên, yếu ở chỗ không nói cho ai biết.** Phiên hầu như luôn chạy tiếp, nhưng 2 ca hỏng nặng vẫn trả báo cáo `complete`.
- **Kiểm soát mạnh ở phần code, nhiều phần còn lại chỉ dựa vào prompt.** Schema, clamp, trần điểm, kiểm quote là code. Không thiên vị, chống bơm lệnh vào điểm, kết luận của Reporter chủ yếu là prompt hoặc chưa có gì.
- **Đánh giá nhiều nhưng không cưỡng chế.** CI không chạy eval nào, ruleset của repo đang `disabled`, production không có cảnh báo.
- **Việc đáng lo nhất về chất lượng:** phân hạng chưa đúng trên mô phỏng. Ứng viên strong 0/16 lần đạt `meets`, average 16/16 lần `below`, `verdict_ok` trượt ngưỡng 19/19 lần chạy, chưa ghi ở tài liệu nào.

## 1. Check lỗi ở đâu

| Chặng | Lỗi | Phát hiện | Hệ thống làm gì | Ai biết |
|---|---|---|---|---|
| CV, JD parse | File sai, quá lớn | `cv_text.py:68-76` | 413/415/422 | Caller |
| CV, JD parse | LLM lỗi | `cv_parser.py:104`, `jd_parser.py:53` | Về parser luật, vẫn 200 | `metadata.model`, log; không vào `fallbacks` |
| Plan | LLM lỗi, plan sai 2 lần | `planner.py:107-136`, `plan_validator.py` | Plan luật | `fallbacks`, log |
| RAG lúc start | DB lỗi, quá 5 s, breaker mở | `plan_snippets.py`, `circuit_breaker.py` | Plan thiếu snippet | `metadata.rag`, `fallbacks` |
| Lấy đáp án chuẩn | Quá 2 s, DB lỗi | `turn_engine.py:103-117` | Chấm không có `R` | `metadata.rag`; `degraded` vẫn false |
| Chấm | LLM lỗi, JSON sai, 402 | `gateway.py:65-110`, `evaluator.py:211` | Heuristic, `degraded`, không tính điểm | `evaluation.degraded`, `fallbacks`, log |
| Hậu kiểm | Quote giả, id giả, hiểu sai | `evaluation_checks.py`, `evaluator_source_checks.py` | Bỏ ý, hạ trần | Log `evaluator_sources` |
| Quyết định | State, plan lệch | `turn_engine.py:139-146` | 409/422; có ca thành 500 | Caller |
| Stream câu hỏi | LLM lỗi trước token | `question_stream.py:86-90` | Câu dự phòng | `fallbacks`, log |
| Stream câu hỏi | Đứt giữa chừng, vi phạm nội dung | `question_stream.py:91-105` | Event `replace` | `fallbacks`; người dùng đã thấy token cũ |
| Báo cáo | Reporter lỗi | `reporter.py:132-136` | `status: partial`, nhận xét mẫu | Caller |

Quan sát: log JSON có `session_id`, `turn_number`; `request_done` có token, fallback, trace; Langfuse theo phiên. Lấy một phiên xấu ra xem được, nhưng CV/JD parse chưa nối vào phiên [Rà]. Không có metrics, dashboard, cảnh báo nào [Code: grep].

## 2. Kiểm soát như nào

| Kiểm soát | Cơ chế | Còn hở |
|---|---|---|
| Xác thực service | Code, token `X-Internal-Token` | Mở nếu không đặt token và `APP_ENV` khác staging/prod [Code] |
| Cô lập phiên | Không có; tin caller | `plan`, `state`, điểm do caller gửi, không ký [Code] |
| Schema đầu ra LLM | Schema strict, repair 1 lần, clamp 0–4 | Ổn |
| Quote có thật | Code | Ổn; nhưng `supports_point` chỉ cần 1 từ chung [TH] |
| Trần điểm | Code | Chỉ `completeness` theo bằng chứng; 3 band còn lại do LLM trừ khi có misconception [Code] |
| Nguồn trích dẫn | Code kiểm id, LLM tự khai nhãn | Xem báo cáo recall |
| Bơm lệnh vào câu trả lời | Regex + prompt | 3/3 câu thử lọt regex [TH] |
| Bơm lệnh vào CV, JD | Regex + bọc `<untrusted>` | 3/3 câu thử lọt regex [TH]; đầu độc `key_points` qua Planner chưa thử với LLM |
| Tài liệu RAG | Bọc `<untrusted>` | Không quét nội dung chunk [Rà] |
| Câu hỏi | Code: độ dài, lộ điểm, lặp, ngôn ngữ | Kiểm sau khi đã stream; hợp level chỉ dựa vào prompt [Code] |
| Che PII | Regex 4 mẫu | Không che tên, địa chỉ, SĐT bàn, SĐT quốc tế, ngày sinh không có từ khóa [TH] |
| Không thiên vị | Evaluator không nhận CV | Câu hỏi, độ khó bắt đầu vẫn theo CV; không có test đối chứng [Rà] |
| Người sửa điểm | Không có | Không API khiếu nại; báo cáo có disclaimer [Rà] |
| Chi phí | `max_tokens`, retry, timeout | Không rate limit, budget phiên; chỉ cảnh báo ở eval [Rà] |
| Version | `metadata.prompt_versions` theo request | Báo cáo cuối luôn ghi `mock` [Code] |

## 3. Đánh giá như nào

| Thành phần | Chỉ số, dữ liệu | Số gần nhất | Nhãn | CI |
|---|---|---|---|---|
| CV parser | 10 CV tổng hợp, lộ PII, injection | Không có số [Rà] | Tác giả | Không |
| JD parser | Không có | Không có | | Không |
| Planner | Gián tiếp qua mô phỏng | Không đo plan khớp CV/JD | | Không |
| RAG | recall@5, 24 + 32 truy vấn | Held-out 0.91–0.94 | Tác giả, nháp | Không |
| Evaluator điểm | 51 mẫu | ±1 band 0.965, lệch −0.31 (ngưỡng ±0.3 trượt sát) | 1 người, 43 mẫu | Không |
| Evaluator nguồn | 47 mẫu | `long_s` recall 0.50–0.63 | Tác giả | Không |
| Interviewer | 60 câu của v2 | Hợp level 87%; v3 chưa có nhãn người | 1 người | Không |
| Policy | Test đơn vị | Không có `test_policy.py`, phủ từng luật chưa rõ [Rà] | | Có |
| Reporter | Mô phỏng | `gap_recall` 0.86–1.0 | Persona | Không |
| Cả phiên | 10 phiên × 8 vòng | Xem mục 4, lỗi 3 | Persona | Không |

- CI chỉ chạy `pytest` với mock, không cần khóa; test LLM dùng model giả [Rà]. 8 test pgvector bị bỏ qua [Rà].
- Ruleset duy nhất `Rule1` đang `disabled` [TH: `gh api`], nên CI xanh cũng không bắt buộc. Branch protection cổ điển không đọc được do thiếu quyền.
- Quy tắc "không merge nếu ±1 band giảm > 5 điểm" (docs 09) là quy ước tay, phải khai `unenforced`.
- Prompt v3–v6 chỉnh trên chính golden, chưa có held-out cho Evaluator, không có kappa.

## 4. Lỗi xếp hạng

### Cao: sai kết quả mà không ai biết
1. **Phiên hỏng toàn bộ vẫn `complete`, điểm 0.0, `below`** [TH]. Mọi lượt degraded thì `scored` rỗng, `overall = 0.0` (`report_scoring.py:73-76`). Credit hết (402) là đủ gây ra, như lúc đo hôm nay. Dấu vết duy nhất: `confidence: low`, `meta.degraded_turns`. Hiện báo cáo còn hiện `[Mock] Kết quả tổng thể: below`.
2. **Thiếu key thì chạy mock im lặng** [TH]. `/api/health` vẫn `healthy`, `fallbacks: []`. `AGENT_*_MODE` thiếu cũng về mock (`registry.py:18`).
3. **Phân hạng chưa đúng** [TH]. 8 vòng v6, persona không có hành vi đặc biệt: strong `near` 16/16, average `below` 16/16. Tính cả các biến thể, strong `meets` 2/32. `verdict_ok` < 0.8 ở 19/19 lần chạy, `slope_direction_ok` trượt 17/19. Chưa phân biệt được lỗi chấm với persona chưa đủ giỏi; `verdict_ok` chỉ có n = 3 mỗi lần.
4. **Trần `completeness` phạt lượt follow_up** [TH]. Trần tính trên `key_points` cả topic, trong khi follow_up chỉ hỏi một khía cạnh; câu kho có `R` thì được miễn (`evaluator.py:163-168`). Replay 71 lượt: 53 lượt bị ép, band trung bình 2.21 → 0.82, điểm lượt 5.44 → 4.73. Điểm phiên strong thấp đi 0.1–0.5. **Bỏ trần cũng không đổi verdict ở cả 20 phiên**, nên đây là lỗi thật nhưng chưa phải toàn bộ lý do ở mục 3. Nếu lệch −0.31 band cũng là thật thì tương đương ~0.8 điểm thang 10; cộng hai phần đủ vượt 7.0, nhưng chưa kiểm chứng.
5. **Lấy đáp án chuẩn lỗi làm tụt điểm im lặng** [Code]. `has_answer_key` vẫn true nên không truy hồi chunk, `reference_answer` rỗng nên quay về trần theo cả topic. Lượt vẫn tính điểm, `degraded` false, báo cáo cuối không biết.
6. **Không cổng chất lượng** [TH]. Đổi prompt làm ±1 band tụt 10 điểm vẫn merge được. v4 từng lệch −0.47, chỉ lộ nhờ người chạy tay.
7. **Không cảnh báo production** [Code]. Fallback tăng, RAG tắt, Evaluator hỏng không ai biết trừ khi tự đọc log.
8. **PII lên bên thứ ba** [TH phần regex]. Prompt và câu trả lời đi nguyên văn lên Langfuse, mặc định cloud. Chưa biết cấu hình thật. Cần xử lý trước khi có ứng viên thật.

### Trung bình
9. **Báo cáo ghi sai version** [Code]: `prompt_versions` luôn `mock` (`report_scoring.py:107`). Sửa rất rẻ, ảnh hưởng truy vết.
10. **Reporter không bị kiểm nội dung** [Rà]: có thể ghi "nên tuyển" hoặc "9/10" khi verdict `below`; `_text` chỉ lọc injection, URL, tiếng Anh.
11. **Reporter bị loại summary thì lọt chuỗi `[Mock]`** với `status: complete` [Rà; chuỗi đã thấy ở lỗi 1].
12. **Không chống lượt trùng** [Rà]: retry làm chấm 2 lần, có thể ra 2 câu hỏi khác nhau.
13. **`elapsed_seconds` mặc định 0** [Rà]: caller bỏ field thì tắt mọi giới hạn thời gian.
14. **`/api/finalize` tin điểm caller gửi** [Code]: không ràng buộc phạm vi `turn_score_10`. Mức độ tùy interview-service.
15. **Không deadline tổng cho lượt chấm** [Rà]: `retry_budget` chỉ giới hạn thời gian ngủ; LLM sập thì mỗi lượt chờ ~17–25 s.
16. **Token của lần gọi lỗi không được tính** [Rà]: chi phí báo thiếu đúng lúc có sự cố.
17. **State hỏng ra 500 sai contract** [Rà]; event `error` trong stream luôn `retryable: true`.
18. **Câu hỏi vi phạm đã hiện trước khi bị thay** [Code]; TTS sẽ đọc phần lộ.
19. **`supports_point` quá yếu** [TH]: 1 từ chung là đủ để tính key point.
20. **CV, JD, Planner không có eval LLM thật** [Rà]: parse sai làm lệch cả phiên.
21. **Bơm lệnh:** regex lọt 3/3, nhưng Evaluator giữ được: 2.5 điểm so với 1.9 của câu đối chứng, 1 câu ra `dont_know` (3 mẫu × 3). Mẫu nhỏ, chưa thể coi là an toàn; golden bắt 6/8.

### Thấp
`gateway.stream` không đóng `resp` khi ngắt, đọc cả upload trước khi kiểm 10 MB, `</UNTRUSTED>` qua được `wrap_untrusted`, breaker theo từng worker [đều là Rà].

## 5. Thứ tự sửa đề xuất
**Làm ngay, rẻ, không đổi thiết kế (đã sửa trên nhánh `thang/report-failure-signals`):**
1. Thêm trạng thái báo cáo khi không chấm được (không ra 0.0 `complete`), bỏ chuỗi `[Mock]` khỏi kết quả (lỗi 1, 11).
2. Chế độ `llm` thiếu key thì fail lúc khởi động; `/api/health` báo mode thật (lỗi 2).
3. Sửa `prompt_versions` (lỗi 9); lượt thiếu đáp án chuẩn gắn cờ (lỗi 5).

**Quyết định về chấm điểm, cần owner:**
4. Đổi trần `completeness` cho follow_up. Gợi ý: dùng cùng quy tắc câu kho; đo lại ±1 band trước khi nhận.
5. Hiệu chỉnh verdict: cần vài phiên có người chấm để biết persona hay cách chấm sai. Thêm `verdict_ok`, `slope` vào báo cáo eval.

**Hạ tầng đo:**
6. Bật required check; thêm eval tối thiểu trước merge khi đổi prompt, có thể chạy tay theo nhãn PR để giữ chi phí.
7. Cảnh báo tối thiểu trên log: tỉ lệ fallback, degraded, RAG error, chi phí phiên.
8. Tách held-out cho Evaluator, thêm người chấm thứ hai.

**Trước khi có dữ liệu thật:**
9. PII: che thêm tên, hoặc tắt nội dung gửi Langfuse, hoặc tự host.
10. Test đối chứng không thiên vị; luồng khiếu nại điểm.

## Giới hạn
- Replay trần `completeness` dùng 4 vòng, 71 lượt, 1 lần mỗi lượt; đã kiểm công thức tính lại lệch tối đa 0.1 so với báo cáo gốc.
- Mục [Rà] chưa kiểm lại. Không chạy thử tải, không kiểm CVE.
- Số liệu thô: `plans/reports/eval-followup-cap-261102.json`. Script ở scratchpad, không đưa vào repo.

## Câu hỏi còn mở
1. Hệ thống dùng cho luyện tập hay sàng lọc? Disclaimer ghi "luyện tập"; nếu là sàng lọc thì lỗi 3, 4, không có người sửa điểm và thiên vị trở thành chặn.
2. interview-service có lưu `metadata`, có gửi `elapsed_seconds`, có xử lý `degraded` không?
3. Langfuse production là cloud hay tự host? Retention ra sao?
4. Vì sao `Rule1` bị tắt?
5. Persona strong có thật sự ở mức `meets` không?
