# judge_support: LLM-judge cho độ bám nguồn, chưa hiệu chỉnh (2026-10-31)

**Số dưới là tạm.** Judge chưa so với nhãn người nên chưa đạt điều kiện Phase 05. Chỉ dùng để biết hướng sửa, chưa ghi làm chỉ số.

Dữ liệu: 3 vòng mô phỏng Evaluator v5 (`eval-sim-v5-ab{,-r2,-r3}-v5`, chạy trước bản sửa a04, không ảnh hưởng phần trích nguồn), gpt-4o-mini qua OpenRouter, judge prompt v1. Đầu ra `plans/reports/judge-support-261031.json`, phiếu `support-sheet-261031.csv` (không commit vì chứa văn bản tài liệu của DE).

Lệnh (`apps/ai-service`):
```
python -m evals.judge_support <3 file eval-sim> --control --triage --out ../../plans/reports/judge-support-261031.json
python -m evals.support_set export ../../plans/reports/judge-support-261031.json --out ../../plans/reports/support-sheet-261031.csv
```

## Kết quả

| Nhóm | n | `entailed` | `contradicted` | `unrelated` | `entailed` trước khi kiểm căn cứ |
|---|---|---|---|---|---|
| `supported`, mọi ý | 168 | 0.589 | 0.006 | 0.405 | 0.762 |
| `supported`, ý khác nhau | 126 | **0.603** | 0.008 | 0.389 | 0.786 |
| câu từ kho, ý khác nhau | 69 | 0.580 | 0.014 | 0.406 | 0.870 |
| câu AI tự đặt, ý khác nhau | 53 | 0.604 | 0 | 0.396 | 0.660 |
| `no_source` có tài liệu, ý khác nhau | 34 | 0.294 | 0 | 0.706 | 0.618 |
| Đối chứng: ý ghép tài liệu topic khác | 126 | **0.008** | 0 | 0.992 | 0.167 |

Phân loại 66 ý `no_source` khác nhau ngoài `intro`:

| Nguyên nhân | Tổng | `technical` | `scenario` |
|---|---|---|---|
| `not_cited`: tài liệu của lượt có nói tới ý đó, Evaluator không trích | 10 | 10 | 0 |
| `retrieval_miss`: chỉ tìm toàn kho mới thấy | 16 | 9 | 7 |
| `corpus_gap`: tìm toàn kho vẫn không thấy (cận trên) | 40 | 15 | 25 |

## Đọc kết quả
- **Độ chính xác của `supported` nằm khoảng 0.60–0.79, dưới ngưỡng 0.80 ở cả hai cách tính, nhưng cận trên rất sát ngưỡng.** Cận trên là khi tin mọi `entailed` của judge. Judge không tất định: giữa hai lần chạy cùng code, `entailed` của ý khác nhau lệch khoảng 0.04 và đối chứng 0–0.008. Kết luận "có trích sai" khá chắc; "dưới ngưỡng" phải chờ nhãn người.
- **Trích sai có thật khi đọc tay.** Ví dụ ý về resize và load factor trích tài liệu `equals`/`hashCode`, ý về `synchronized` và `Lock` trích tài liệu vòng đời thread.
- **`no_source` chủ yếu do kho:** 40/66 là `corpus_gap`, trong đó 25 ở `scenario`. Câu hỏi tình huống cần kiến thức thiết kế mà kho Q&A chưa phủ, đúng phần Phase 04 (giáo trình) nhắm tới. `corpus_gap` là cận trên vì tìm toàn kho cũng có thể trượt.
- **`contradicted` chưa dùng được.** Ca duy nhất lần này (và ca thứ hai ở lần chạy trước) đọc tay đều sai: tài liệu nói cùng chiều với ý ứng viên. Bảng trên không nên đọc là "Evaluator ghi nhầm ý sai".
- **Đối chứng chỉ chứng minh judge không dễ dãi khi tài liệu lệch hẳn.** Nó không nói gì về tài liệu cùng topic, là ca khó thật.

## Sửa trong lúc làm
- Judge phải chép đoạn tài liệu làm căn cứ, code kiểm từ của đoạn đó có trong tài liệu. Không kiểm thì 17–25% ý ghép tài liệu sai vẫn được `entailed`.
- Bản đầu đòi khớp liên tục (`quote_in_answer`) nên loại nhầm ý đúng, vì model bỏ markdown và đánh số (`equals()` / `hashCode()` trong "**1. equals()** và **2. hashCode()**"). Đổi sang tỉ lệ từ ≥ 0.8. Tính lại trên kết quả của lần chạy trước: ngưỡng 0.8–1.0 cho `supported` 0.577–0.583 và đối chứng 0, còn 0.6 làm đối chứng lên 0.024. Ngưỡng này chọn trên chính dữ liệu này.
- Phân loại ban đầu so ý với chính truy vấn nên `retrieval_miss` và `corpus_gap` vô nghĩa; bản này lấy chunk thật toàn kho. Lần chạy đầu 66/75 `unknown` do corpus BM25 chưa nạp; nay nạp trước, và lỗi một phần tính `unknown` thay vì `corpus_gap`.
- Phiếu mỗi dòng đúng một tài liệu, id mờ, để số tài liệu và tên persona không lộ nhãn.
- Review độc lập phát hiện phiếu `supported` có thể hiện tài liệu khác tài liệu judge xét, `triage` đếm trùng ý (75 → 66) và lỗi `triage` làm mất kết quả đã trả phí; đã sửa và chạy lại, số trên là của bản sửa.

## Điều kiện dùng số
`evals.support_set agree` cần đủ cả ba: ≥ 30 nhãn, đồng ý ≥ 0.8, kappa ≥ 0.6. Thêm kappa vì judge luôn trả một nhãn vẫn có thể đạt 0.8 trên mẫu lệch. Mẫu 45 `supported` và 15 `no_source` lấy trên ý khác nhau.

Giới hạn: phiếu cho người xem một tài liệu (tài liệu judge đã dùng làm căn cứ, nếu có), judge xét cả lượt. Khi judge trả `unrelated` với ý có nhiều tài liệu, người không thấy các tài liệu còn lại, nên độ đồng ý có thể cao hơn thực tế ở nhóm này.

## Việc tiếp theo
1. Người chấm 60 cặp (`support-sheet-261031.csv`), rồi `evals.support_set import --rater <tên>` và `agree`.
2. Đạt thì ghi số `supported`. Không đạt thì sửa prompt judge (v2), trước hết phần `contradicted`.
3. Sau khi có số: sửa cách Evaluator gán `support`, ưu tiên ý trích tài liệu không nói tới.

## Câu hỏi còn mở
- Ai chấm 60 cặp: DE (đã chấm golden trước) hay AIE?
