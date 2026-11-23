# Kết quả đánh giá gợi ý việc làm CV–JD (spec 017, US3)

Sinh bởi `python -m pipeline match-eval --rounds 4` lúc 2026-11-23T04:43:43+00:00. Số liệu thô: `data/processed/match_eval/run-20261123T044343309633Z.json` (không commit).

## 1. Bộ dữ liệu

- 24 CV tổng hợp (viết tiếng Việt), 36 JD của 009 (0 tổng hợp; ngôn ngữ JD: en 17, mixed 1, vi 18), 264 cặp có nhãn (mọi cặp qua lọc cứng), as-of 2026-11-01.
- Tập cặp qua lọc cứng của endpoint trùng đúng tập đã gán nhãn (lệnh dừng với mã 1 nếu lệch, nên bảng này chỉ có khi hai tập bằng nhau): bằng chứng cho vế bộ lọc cứng của SC-004.
- Model embedding `text-embedding-3-small`, chỉ mục 356 JD, trọng số cosine 0.6 / skill_match 0.3 / level_fit 0.1, lệch bậc tối đa 1.
- Phân bố nhãn: 0 = 162, 1 = 62, 2 = 40.
- Cách gán nhãn: `llm:claude-sonnet (all 264 pairs); de blind 48 pairs for agreement only` (2026-11-22), phương pháp `llm+de-blind-20 (final = llm)`; rubric: specs/017-cv-jd-matching/label-rubric.md; backend language rule added 2026-11-22 (88 backend pairs relabeled), row definitions unchanged; tập cặp: hard-filter replica (research R9); recheck against match-eval-sheet after PR-2; pool checked: all 36 JD indexed under PR-1 dedup rule (feb4db1).
- Đồng thuận: kappa có trọng số (quadratic) giữa DE gán mù và LLM = 0.718 trên 48 cặp gán mù (trước khi sửa rubric: 0.659; khớp tuyệt đối 0.688, lệch tối đa một mức 0.958).
- Nguồn nhãn cuối: llm 264.
- Giới hạn của nhãn: nhãn cuối là nhãn LLM, không phải nhãn của người; DE chỉ gán mù một phần nhỏ để đo đồng thuận, nên số liệu bên dưới đo độ khớp với cách LLM chấm theo rubric.

## 2. Chất lượng gợi ý

Trung bình trên các CV. Cả ba cách xếp lại kết quả của cùng một lần gọi endpoint (cùng bộ lọc cứng); hòa điểm thì `job_id` tăng dần.

| Cách tính | P@5 | nDCG@5 | Số CV |
|---|---|---|---|
| Đầy đủ (`score`) | 0.642 | 0.883 | 24 |
| Chỉ `skill_match` | 0.625 | 0.847 | 24 |
| Chỉ `cosine` | 0.617 | 0.842 | 24 |

P@5: liên quan = nhãn ≥ 1. nDCG@5: gain = nhãn 0/1/2 (tuyến tính), ideal tính từ mọi nhãn của CV. CV không có JD liên quan trong tập đang xét bị bỏ khỏi cả hai trung bình (cột số CV).

**SC-001** (nDCG@5 đầy đủ > chỉ `skill_match`): đạt (0.883 so với 0.847, chênh 0.036).

## 3. Theo ngôn ngữ

Cách tính: CV đều viết tiếng Việt; ngôn ngữ JD lấy từ trường `language` của `jd_normalized.jsonl` (vi / en / mixed). Với mỗi CV, giữ các JD qua lọc cứng thuộc nhóm ngôn ngữ, xếp theo từng cách tính, tính P@5 và nDCG@5 trên tập con đó, rồi lấy trung bình theo từng CV. Tập con dưới 5 JD thì P@5 chia cho số JD của tập; CV không có JD liên quan trong tập con bị bỏ (cột số CV).

| Cách tính | Nhóm JD | P@5 | nDCG@5 | Số CV | Số cặp |
|---|---|---|---|---|---|
| Đầy đủ (`score`) | cùng ngôn ngữ (JD vi) | 0.455 | 0.857 | 22 | 123 |
| Chỉ `skill_match` | cùng ngôn ngữ (JD vi) | 0.482 | 0.795 | 22 | 123 |
| Chỉ `cosine` | cùng ngôn ngữ (JD vi) | 0.473 | 0.875 | 22 | 123 |
| Đầy đủ (`score`) | khác ngôn ngữ (JD en/mixed) | 0.396 | 0.962 | 24 | 132 |
| Chỉ `skill_match` | khác ngôn ngữ (JD en/mixed) | 0.396 | 0.971 | 24 | 132 |
| Chỉ `cosine` | khác ngôn ngữ (JD en/mixed) | 0.396 | 0.903 | 24 | 132 |

## 4. Độ trễ

4 vòng × 24 CV; mỗi vòng gọi cả hai kiểu (page_size 50 khi có `job_ids`, 10 khi không có). Lần gọi chất lượng ở mục 2 không tính (khởi động chỉ mục). Percentile theo nearest-rank.

| Phép đo | Số mẫu | p50 | p95 |
|---|---|---|---|
| Tính điểm, server (`timing_ms.score`), có `job_ids` (pool) | 96 | 0.0 ms | 0.0 ms |
| Tính điểm, server (`timing_ms.score`), không `job_ids` (toàn chỉ mục) | 96 | 1.0 ms | 2.0 ms |
| Toàn bộ yêu cầu, client (gồm embed CV), có `job_ids` (pool) | 96 | 211.5 ms | 270.9 ms |
| Toàn bộ yêu cầu, client (gồm embed CV), không `job_ids` (toàn chỉ mục) | 96 | 209.4 ms | 241.1 ms |

**SC-002** (p95 phần tính điểm ≤ 500 ms trên toàn chỉ mục): đạt (p95 = 2.0 ms).

## 5. Chi phí embedding

Đơn giá `EMBEDDING_PRICE_PER_1M` = $0.02 / 1 triệu token.

- Index toàn bộ JD: 113600 token ≈ $0.002272, từ `run-report-index-jd-match-20261123T042821Z.json` (embed 356 / 356 bản ghi).
- Mỗi yêu cầu: trung bình 251.6 token ≈ $0.000005 (từ `metadata.usage` của 216 yêu cầu).

## 6. Hạn chế

- Bộ dữ liệu nhỏ (24 CV, 36 JD, 264 cặp): chênh lệch nhỏ giữa các cách tính có thể là nhiễu; không có khoảng tin cậy.
- CV tổng hợp viết thẳng dưới dạng `CvProfile`, bỏ qua sai số của CV Parser: chưa đo cả chuỗi từ file CV.
- Độ trễ đo trên một máy, từng yêu cầu một, chưa đo tải đồng thời; phụ thuộc đường truyền tới provider embedding.
- Lệnh này không kiểm phần `matched_skills` / `missing_skills` khớp `skill_match` của SC-004.
- Mỗi cách tính hòa điểm thì xếp theo `job_id`; `skill_match` là tỉ lệ nên dễ hòa, khi đó thứ hạng baseline phụ thuộc thứ tự `job_id`.
- Kết quả chỉ đúng với bộ lọc cứng, trọng số và chỉ mục ghi ở mục 1 tại thời điểm chạy.

## 7. Phân tích (viết tay, 2026-11-23)

Mục 1–6 do lệnh sinh; chạy lại lệnh sẽ ghi đè, cần chép lại mục này.

- **Kết luận chính**: kết hợp ba thành phần tốt hơn từng tín hiệu riêng (nDCG@5 0,883 so với 0,847 và 0,842; P@5
  0,642 so với 0,625 và 0,617). Mức chênh nhỏ trên 24 CV nên chỉ coi là xu hướng, không phải khác biệt có ý nghĩa thống kê.
- **Theo ngôn ngữ**: trong cặp cùng ngôn ngữ (JD vi), chỉ-cosine (0,875) vượt chỉ-skill (0,795); trong cặp khác ngôn
  ngữ (JD en), chỉ-cosine (0,903) thua chỉ-skill (0,971). Nhất quán với giả thuyết cosine bị phạt khi CV tiếng Việt gặp
  JD tiếng Anh, còn `skill_match` không phụ thuộc ngôn ngữ vì so theo slug. Cách đầy đủ giữ được mức gần tốt nhất ở cả
  hai nhóm. Lưu ý: mỗi tập con chỉ còn vài JD mỗi CV nên nDCG@5 cao hơn mặt bằng chung (dễ xếp đúng khi ít ứng viên) và
  P@5 thấp (mẫu số nhỏ); chỉ so được giữa các cách tính trong cùng một nhóm, không so giữa hai nhóm.
- **SC-002 / SC-003**: tính điểm trên toàn chỉ mục 356 JD p95 = 2 ms; toàn bộ yêu cầu p95 ≈ 0,27 s, gần như hết là
  thời gian embed CV. Index toàn bộ JD ≈ 0,002 USD, mỗi yêu cầu ≈ 0,000005 USD.
- **Hạn chế thêm** (chi tiết: `plans/reports/labeling-261122-1926-017-eval-labels-and-data-issues.md`):
  - LLM soạn CV và LLM gán nhãn cuối; DE gán mù 48 cặp, chấm rộng tay hơn LLM (15/19 cặp lệch DE cao hơn).
  - Chỉ so trong cùng nhóm (lọc cứng theo nhóm) nên không có cặp âm khác nhóm; backend Python / Node có ít JD phù hợp.
  - Dữ liệu 009 có level lưu lệch nội dung (khoảng 9 JD), thẻ kỹ năng nhiễu và 2 JD xếp nhầm nhóm; các lỗi này ảnh
    hưởng trực tiếp `level_fit`, `skill_match` và lọc cứng nhưng được giữ nguyên để đo hệ thống trên dữ liệu thật.
