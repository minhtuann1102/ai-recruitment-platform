# 017 T036: gán nhãn bộ đánh giá + vấn đề dữ liệu (2026-11-22)

Đọc trước khi viết mục "Hạn chế" của `specs/017-cv-jd-matching/eval-results.md` (T037) và khi sửa 009.

## Bộ đánh giá

- Pool 36 JD thật (as-of 2026-11-01; mỗi nhóm backend / devops / ai_data: 4 Junior, 4 Mid, 2 không level, 2 Senior),
  18 vi / 17 en / 1 trộn. Đã kiểm: cả 36 JD được index theo luật trùng hash của PR-1 (feb4db1).
- 24 CV tổng hợp tiếng Việt (LLM soạn, dịch từ bản tiếng Anh; trường không phải văn bản giữ nguyên từng ký tự),
  junior + middle. 264 cặp qua lọc cứng (bản sao luật; kiểm lại với `match-eval-sheet` khi PR-2 xong).
- Nhãn cuối `apps/data-pipeline/data/seeds/match_eval/labels.json`: toàn bộ 264 nhãn của LLM (owner chọn chuẩn chặt). Phân bố 0/1/2 =
  162 / 62 / 40.

## Đồng thuận (48 cặp DE gán mù)

| Đo | Giá trị |
|---|---|
| Kappa trọng số bậc hai, rubric gốc | 0,659 |
| Sau khi thêm luật ngôn ngữ backend (88 cặp backend LLM gán lại) | 0,718; trùng 68,8%; lệch ≤ 1 bậc 95,8% |
| LLM lượt 1 (JD cắt 2.500 ký tự) × lượt 2 (toàn văn) | 0,916, không phải test-retest thuần |

## Hạn chế phải ghi trong báo cáo

1. **DE rộng tay hơn LLM**: 15/19 cặp lệch là DE cao hơn. Owner chọn toàn bộ nhãn LLM (chuẩn chặt) làm nhãn cuối, không
   chốt từng cặp → P@5 tuyệt đối có thể thấp hơn nếu người chấm; so sánh giữa các cách tính vẫn công bằng (cùng bộ nhãn).
2. **LLM soạn CV và LLM gán nhãn** (khác worker, khác phiên), một người gán mù 20%.
3. **Backend Python / Node mỏng**: mỗi CV chỉ 1–2 JD phù hợp rõ, thị trường ít JD backend thuần Python / Node.
4. **Chỉ so trong cùng nhóm**: lọc cứng theo nhóm nên không có cặp âm khác nhóm; mọi cặp là "gần trúng".
5. **CV tiếng Việt, JD giữ gốc**: 17/36 JD tiếng Anh → tách nDCG@5 theo cặp cùng / khác ngôn ngữ.
6. **Rubric sửa một lần** sau lần đo đầu (luật ngôn ngữ backend); 6 cặp chéo ngôn ngữ được 1 vì JD
   `careerviet:35C8B905` ghi "ít nhất 1 trong các ngôn ngữ BackEnd" (có thể tranh luận).

## Vấn đề dữ liệu 009 (ảnh hưởng `level_fit`, `skill_match`, lọc cứng)

- **Level lưu lệch nội dung**: `itviec:4938` Junior nhưng "SRE II, 2+ năm"; `itviec:1950` Junior / 2–4 năm;
  `careerviet:35C89037` Junior / 2–3+ năm; `careerviet:35C8AD4A` Junior / 2 năm; `itviec:0423` Mid / 4+ năm;
  `itviec:4904` Mid / 3–5 năm; `careerviet:35C8BE15` Senior / 3 năm; `careerviet:35C8B905` "[All level]" lưu Junior;
  `itviec:4155` Junior nhưng nêu nhiều bậc.
- **Thẻ kỹ năng nhiễu**: `itviec:0931` (helpdesk) có `unit-testing`; `itviec:4158` (Node / TS) có csharp, java,
  golang, selenium, react; `itviec:0557` có airflow, spark, data-engineering; `careerviet:35C89470` có
  `software-testing`.
- **Nhóm lệch vai trò**: `itviec:5127` (AI agent) nằm ở backend; `itviec:1530` (Dynamics AX / Power BI) ở backend.
- **Section**: 13 JD topdev chỉ có tiêu đề (không tách được mô tả / yêu cầu); vài JD careerviet gộp yêu cầu vào mô tả;
  `careerviet:35C8B905`, `careerviet:35C89470` có "Kinh nghiệm: null Năm".

## Câu hỏi chưa giải quyết

- Có sửa level / thẻ kỹ năng trong 009 trước khi chạy eval (T037) không? Nếu sửa thì phải index lại và kiểm lại tập cặp.
