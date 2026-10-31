# judge_support: LLM-judge cho độ bám nguồn, chưa hiệu chỉnh với người (2026-10-31)

**Số dưới là tạm.** Judge chỉ mới so với nhãn LLM thứ hai, chưa so với nhãn người, nên chưa đạt điều kiện Phase 05. Bản chốt: prompt **v2** + hỏi lại một lần khi judge chép lời ứng viên làm căn cứ (mục "Hiệu chỉnh").

Dữ liệu: 3 vòng mô phỏng Evaluator v5 (`eval-sim-v5-ab{,-r2,-r3}-v5`, chạy trước bản sửa a04, không ảnh hưởng phần trích nguồn), gpt-4o-mini qua OpenRouter, judge prompt v2 + repair. Đầu ra `plans/reports/judge-support-261031.json`, phiếu `support-sheet-261031.csv` (không commit vì chứa văn bản tài liệu của DE).

Lệnh (`apps/ai-service`):
```
python -m evals.judge_support <3 file eval-sim> --control --triage --out ../../plans/reports/judge-support-261031.json
python -m evals.support_set export ../../plans/reports/judge-support-261031.json --out ../../plans/reports/support-sheet-261031.csv
```

## Kết quả (v2 + repair)

| Nhóm | n | `entailed` | `contradicted` | `unrelated` | hỏi lại |
|---|---|---|---|---|---|
| `supported`, mọi ý | 168 | 0.625 | 0.012 | 0.363 | 24 |
| `supported`, ý khác nhau | 126 | **0.635** | 0.016 | 0.349 | 19 |
| câu từ kho, ý khác nhau | 69 | 0.710 | 0.014 | 0.275 | 14 |
| câu AI tự đặt, ý khác nhau | 53 | 0.528 | 0.019 | 0.453 | 4 |
| `no_source` có tài liệu, ý khác nhau | 34 | 0.265 | 0 | 0.735 | 9 |
| Đối chứng: ý ghép tài liệu topic khác | 126 | **0.008** | 0 | 0.992 | 14 |

Phân loại 66 ý `no_source` khác nhau ngoài `intro`:

| Nguyên nhân | Tổng | `technical` | `scenario` |
|---|---|---|---|
| `not_cited`: tài liệu của lượt có nói tới ý đó, Evaluator không trích | 9 | 9 | 0 |
| `retrieval_miss`: chỉ tìm toàn kho mới thấy | 14 | 10 | 4 |
| `corpus_gap`: tìm toàn kho vẫn không thấy (cận trên) | 42 | 14 | 28 |
| `unknown`: tìm kiếm lỗi | 1 | 1 | 0 |

## Đọc kết quả
- **Độ chính xác của `supported` khoảng 0.64 (câu kho 0.71, câu AI tự đặt 0.53), dưới ngưỡng 0.80.** Sau repair không còn khoảng "trước/sau kiểm căn cứ". Judge không tất định: cùng prompt, các lần chạy lệch ±0.04. Kết luận "có trích sai, nhất là ở câu AI tự đặt" khá chắc; con số chính thức phải chờ nhãn người.
- **Trích sai có thật khi đọc tay.** Ví dụ ý về resize và load factor trích tài liệu `equals`/`hashCode`, ý về `synchronized` và `Lock` trích tài liệu vòng đời thread.
- **`no_source` chủ yếu do kho:** 42/66 là `corpus_gap`, trong đó 28 ở `scenario`. Câu hỏi tình huống cần kiến thức thiết kế mà kho Q&A chưa phủ, đúng phần Phase 04 (giáo trình) nhắm tới. `corpus_gap` là cận trên vì tìm toàn kho cũng có thể trượt.
- **`contradicted` chưa dùng được.** Cả 2 ca đọc tay đều sai; một ca `doc_quote` trùng nguyên văn ý ứng viên mà judge vẫn trả "ngược". Bảng trên không nên đọc là "Evaluator ghi nhầm ý sai".
- **Đối chứng chỉ chứng minh judge không dễ dãi khi tài liệu lệch hẳn.** Nó không nói gì về tài liệu cùng topic, là ca khó thật.

## Sửa trong lúc làm
- Judge phải chép đoạn tài liệu làm căn cứ, code kiểm từ của đoạn đó có trong tài liệu. Không kiểm thì 17–25% ý ghép tài liệu sai vẫn được `entailed`.
- Bản đầu đòi khớp liên tục (`quote_in_answer`) nên loại nhầm ý đúng, vì model bỏ markdown và đánh số (`equals()` / `hashCode()` trong "**1. equals()** và **2. hashCode()**"). Đổi sang tỉ lệ từ ≥ 0.8. Tính lại trên kết quả của lần chạy trước: ngưỡng 0.8–1.0 cho `supported` 0.577–0.583 và đối chứng 0, còn 0.6 làm đối chứng lên 0.024. Ngưỡng này chọn trên chính dữ liệu này.
- Phân loại ban đầu so ý với chính truy vấn nên `retrieval_miss` và `corpus_gap` vô nghĩa; bản này lấy chunk thật toàn kho. Lần chạy đầu 66/75 `unknown` do corpus BM25 chưa nạp; nay nạp trước, và lỗi một phần tính `unknown` thay vì `corpus_gap`.
- Phiếu mỗi dòng đúng một tài liệu, id mờ, để số tài liệu và tên persona không lộ nhãn.
- Review độc lập phát hiện phiếu `supported` có thể hiện tài liệu khác tài liệu judge xét, `triage` đếm trùng ý (75 → 66) và lỗi `triage` làm mất kết quả đã trả phí; đã sửa và chạy lại, số trên là của bản sửa.

## Hiệu chỉnh với nhãn LLM thứ hai (chưa phải nhãn người)
AIE nhờ Claude (Fable 5.1, không xem kết quả judge) chấm 60 cặp của phiếu: `evals/support_labels/claude.json`. Đây là LLM so LLM, **không thay nhãn người**, dùng để chọn prompt và sửa code trước khi nhờ người.

| Bản judge | Đồng ý | Kappa | Lệch chính |
|---|---|---|---|
| v1 (3 lần chạy) | 0.68–0.73 | 0.37–0.47 | 8–10 ca judge dễ; 8–9 ca bị loại nhầm vì `doc_quote` chép lời ứng viên |
| v2 (siết "nhắc tên chưa đủ", ví dụ chép sai/đúng) | 0.80 | 0.61 | dễ còn 4; loại nhầm còn 6 |
| v1 / v2 + đảo thứ tự trường (bằng chứng trước) | 0.68 / 0.75 | 0.37 / 0.50 | dễ hơn, bỏ |
| **v1 / v2 + repair** (phát hiện chép lời ứng viên, hỏi lại một lần) | 0.85 / **0.85–0.87** | 0.70 / **0.70–0.74** | loại nhầm 0; còn 5–9 ca judge dễ |

Ma trận bản chốt (`claude` → judge): ủng hộ→ủng hộ 27, không liên quan→không liên quan 24, không liên quan→ủng hộ 5, ủng hộ→không liên quan 3, ủng hộ→ngược 1.
- **Chép lời ứng viên làm căn cứ** là lỗi của gpt-4o-mini mà prompt không sửa được (100% đoạn bị loại thuộc dạng này ở mọi bản). Repair hỏi lại một lần kèm câu trả lời cũ; 24/168 ý `supported` phải hỏi lại, lần hai chép đúng hoặc trả `unrelated`. Chi phí thêm ~15% lời gọi.
- **Judge dễ** còn ở ý mơ hồ ("thứ tự thực thi cần hiểu rõ") và ý chỉ nêu tên khái niệm. 14 cặp `claude` phân vân cũng xoay quanh quy tắc này; hướng dẫn chấm cho người phải chốt.
- Lệch giữa các lần chạy cùng bản ±0.05, nên khác biệt v1/v2 sau repair không chắc; chọn v2 vì dễ ít hơn (5 vs 9 ca) và đối chứng thô 0.008 vs 0.032.

## Điều kiện dùng số
`evals.support_set agree` cần đủ cả ba: ≥ 30 nhãn, đồng ý ≥ 0.8, kappa ≥ 0.6. Thêm kappa vì judge luôn trả một nhãn vẫn có thể đạt 0.8 trên mẫu lệch. Mẫu 45 `supported` và 15 `no_source` lấy trên ý khác nhau.

Giới hạn: phiếu cho người xem một tài liệu (tài liệu judge đã dùng làm căn cứ, nếu có), judge xét cả lượt. Khi judge trả `unrelated` với ý có nhiều tài liệu, người không thấy các tài liệu còn lại, nên độ đồng ý có thể cao hơn thực tế ở nhóm này.

## Việc tiếp theo
Owner chốt 31/10: hiệu chỉnh với LLM thứ hai là đủ cho đồ án, nhãn người là tùy chọn.
1. *(Tùy chọn)* Người chấm 60 cặp (trang chấm riêng của AIE, hoặc `support-sheet-261031.csv`), rồi `evals.support_set import --rater <tên>` và `agree`. Hướng dẫn chấm cần chốt quy tắc ý chỉ nêu tên khái niệm.
2. Đạt thì ghi số `supported`. Không đạt thì judge v3, trước hết phần ý mơ hồ và `contradicted`.
3. Sau khi có số: sửa cách Evaluator gán `support`, ưu tiên ý trích tài liệu không nói tới, nhất là ở câu AI tự đặt.

## Câu hỏi còn mở
- Ai chấm 60 cặp cho nhãn người: DE (đã chấm golden trước) hay AIE? AIE đã xem kết quả judge nên nhãn có thể lệch.
- Ý chỉ nêu tên khái niệm ("Giải thích polymorphism"): tài liệu nhắc tên là `entailed` hay phải giải thích?
