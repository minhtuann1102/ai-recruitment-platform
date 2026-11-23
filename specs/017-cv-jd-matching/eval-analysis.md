# Phân tích kết quả đánh giá (017, US3)

Viết tay ngày 2026-11-23, đọc kèm [eval-results.md](eval-results.md) (bản do `match-eval` sinh, lần chạy
`run-20261123T044343309633Z`). Các con số kiểm chứng độc lập trong review PR-3
(`plans/reports/code-reviewer-261123-1129-017-jd-match-eval.md`).

## 1. Chất lượng: kết hợp ba thành phần có xu hướng tốt hơn

| So sánh (nDCG@5 theo từng CV) | Thắng / thua / hòa | Chênh trung bình | Khoảng tin cậy 95% (bootstrap) |
|---|---|---|---|
| Đầy đủ so với chỉ `skill_match` | 12 / 6 / 6 | +0,036 | −0,010 đến +0,084 |
| Đầy đủ so với chỉ `cosine` | 12 / 10 / 2 | +0,041 | chứa 0 |

- SC-001 đạt theo đúng định nghĩa (trung bình cao hơn), nhưng khoảng tin cậy chứa 0: với 24 CV chỉ nói được **xu
  hướng**, chưa phải khác biệt có ý nghĩa thống kê.
- Baseline chỉ-skill hay hòa điểm (32 điểm hòa); hòa thì xếp theo `job_id`, có lợi cho baseline (nếu xếp ngẫu nhiên kỳ
  vọng nDCG@5 ≈ 0,836). Chênh thật vì vậy khoảng 0,046, tức kết luận không phải do cách phá hòa.
- Không có baseline chỉ `level_fit`, nên chỉ so được với hai trong ba tín hiệu.

## 2. Ngôn ngữ: cosine thiên vị JD cùng ngôn ngữ với CV

CV đều tiếng Việt; JD 18 vi / 17 en / 1 trộn.

- Cùng một nhãn, JD tiếng Anh có cosine thấp hơn JD tiếng Việt: nhãn 0 là 0,530 so với 0,594; nhãn 2 là 0,637 so với
  0,682.
- Tỉ lệ JD tiếng Việt trong top 5: chỉ cosine 69%, cách đầy đủ 56%, chỉ skill 50%, trong khi JD tiếng Việt chiếm
  khoảng 55% số cặp liên quan. Tức cosine đẩy JD tiếng Việt lên quá mức, `skill_match` (so theo slug, không phụ thuộc
  ngôn ngữ) kéo lại; cách đầy đủ gần đúng tỉ lệ.
- Bảng tách theo ngôn ngữ ở eval-results §3 **không** dùng được để kết luận điều này: trong mỗi nhóm mọi JD cùng ngôn
  ngữ nên một mức phạt đồng đều không đổi thứ tự trong nhóm. Mỗi nhóm chỉ còn 4–7 JD mỗi CV nên P@5 gần như không phụ
  thuộc thứ tự (cả ba cách đều 0,396 ở nhóm JD en / mixed) và thấp vì ít JD liên quan; nDCG@5 trong nhóm cao vì ít ứng
  viên. Chỉ nên đọc bảng đó để so các cách tính trong cùng một nhóm, và bỏ qua cột P@5.
- Hướng cải thiện (ngoài GĐ1): embed bản dịch cùng ngôn ngữ, hoặc giảm trọng số cosine khi CV và JD khác ngôn ngữ.

## 3. Tốc độ và chi phí

- Tính điểm trên toàn chỉ mục 356 JD: p95 khoảng 2 ms (server làm tròn xuống mili giây nên 0 / 1 / 2 ms chỉ là cỡ
  độ lớn). SC-002 (≤ 500 ms) đạt dư.
- Toàn bộ yêu cầu (gồm embed CV) đo phía client: p95 241 ms trên toàn chỉ mục, 271 ms khi giới hạn theo pool. Phần lớn
  là thời gian embed, suy ra từ việc tính điểm chỉ vài mili giây (lệnh chưa ghi `timing_ms.embed`).
- Index toàn bộ JD ≈ 0,0023 USD (113.600 token); mỗi yêu cầu ≈ 0,000005 USD (≈ 252 token). SC-003 đạt.

## 4. Nhãn và độ tin cậy

- Nhãn cuối là nhãn LLM (owner chọn chuẩn chặt cho cả 264 cặp). DE gán mù 48 cặp (2 cặp mỗi CV), trang gán không
  hiện ghi chú CV và không hiện nhãn LLM.
- Kappa trọng số giữa DE gán mù và LLM: 0,659 với rubric gốc; 0,718 sau khi thêm luật ngôn ngữ backend. Con số 0,718 đo
  trên chính 48 cặp đã làm lộ ra luật đó, nên có phần lạc quan.
- Trước khi sửa rubric, 15/19 cặp lệch là DE cao hơn LLM; sau khi sửa, cả 15 cặp còn lệch đều là DE cao hơn. Vì vậy số
  liệu đo độ khớp với chuẩn chấm của LLM, chặt hơn chuẩn của người chấm; P@5 tuyệt đối có thể thấp hơn nếu người chấm.
- SC-004: tập cặp qua lọc cứng của endpoint trùng đúng tập đã gán (264 = 264), tức endpoint khớp với bản sao luật lọc
  dùng khi gán nhãn; phần `matched_skills` / `missing_skills` do test của ai-service kiểm, lệnh đánh giá không kiểm.

## 5. Hạn chế khác

- LLM soạn CV và LLM gán nhãn (khác phiên, khác worker).
- Chỉ so trong cùng nhóm nên không có cặp âm khác nhóm; backend Python / Node có ít JD phù hợp.
- Dữ liệu 009 có level lưu lệch nội dung (khoảng 9 JD), thẻ kỹ năng nhiễu, 2 JD xếp nhầm nhóm
  (`plans/reports/labeling-261122-1926-017-eval-labels-and-data-issues.md`); giữ nguyên để đo hệ thống trên dữ liệu thật.

## Câu hỏi chưa giải quyết

- Có commit nhãn DE gán mù (48 cặp) và script tính kappa để tái lập 0,718 từ repo không? Hiện chỉ ở
  `data/processed/match_eval/` (không vào git).
