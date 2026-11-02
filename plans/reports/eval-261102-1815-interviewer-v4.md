# Interviewer v4: bám câu trả lời, hint đúng nghĩa (2026-11-02)

Harness full (29 persona, simulator LLM, mọi agent LLM, RAG + kho câu hỏi bật), gpt-4o-mini qua OpenRouter.
File phiên và bộ câu hỏi: `plans/reports/eval-sim-interviewer-ab-{v3,v4,v4b,v4c}.json`, `question-set-{v3,v4}.json` (không commit vì có câu từ kho DE). Bản chốt là `v4c`.

**Người chấm là Claude Fable, không phải người.** Mọi điểm `natural` dưới đây là nhãn LLM, không so trực tiếp với 3.78 của người chấm.

## Kết luận
- **v4 nên dùng:** hint đúng hành động tăng rõ, khuôn câu giảm mạnh, không mất câu kho, không hồi quy ở các chỉ số phiên.
- **Điểm tự nhiên tăng chưa chứng minh được:** +0.12, khoảng tin cậy 95% −0.20 đến +0.45.
- **Chưa biết đạt 4.0 theo người chưa.** Fable chấm v4 3.37, thấp hơn 4.0, nhưng Fable không dự đoán được nhãn người (bên dưới). Câu hỏi này vẫn cần người chấm.

## Thay đổi
- `app/prompts/interviewer.v4.md`:
  - Coi `focus` là ghi chú nội bộ, không chép lại.
  - Không nhắc lại tên chủ đề ở `follow_up`, `hint`, `clarify` nếu không cần.
  - Cấm cả "Vậy bạn có thể", "Thế bạn có thể", tránh từ văn viết ("chia sẻ", "trình bày"...).
  - `scenario` nói bối cảnh ngắn rồi hỏi cách làm.
  - `hint` phải có chỗ bám, được nói lại câu hỏi ngắn hơn.
  - Câu kho có danh sách thì giữ đủ mục.
  - Thêm phần tự kiểm cuối prompt.
- `app/mock_interviewer.py`: câu dự phòng đặt `focus` sau dấu hai chấm và bỏ dấu câu cuối `focus`. Trước đây ra câu vỡ như "hãy nghĩ tới Mô tả các pha của event loop..".
- `evals/question_set.py`: `--tag`, `--golden`, `--labels-dir`, phiếu trộn nhiều phiên bản. Nhãn LLM ở `evals/question_labels_llm/`, tách khỏi nhãn người.

## Ba vòng prompt
| Bản | Khuôn "Bạn có thể" | Câu từ kho giữ được | Ghi chú |
|---|---:|---:|---|
| v3 | 25.2% | 97.2% | Mốc so sánh |
| v4 đầu | **43.1%** | 89.0% | Bỏ luật "không mở đầu bằng Bạn có thể" của v3, thêm ví dụ xấu chứa đúng khuôn đó |
| v4b | 16.0% | **89.0%** | Khôi phục luật; câu kho dài bị rút gọn nên `kept_meaning` loại, mất đáp án chuẩn |
| v4c (chốt) | **8.6%** | **97.1%** | Giữ đủ danh sách câu kho, sửa 4 lỗi prompt từ review |

Bài học: gpt-4o-mini làm theo luật "mở đầu bằng gì" và ví dụ tốt, không làm theo luật chung chung. Ví dụ xấu chứa đúng cụm cần tránh làm tăng cụm đó.

## Chỉ số bằng code (v3 so với v4c)
| Chỉ số | v3 | v4c | Ngưỡng |
|---|---:|---:|---:|
| Khuôn "Bạn có thể ... không?" | 25.2% | **8.6%** | ≤ 40% |
| Nhắc lại lời ứng viên | 3.9% | 1.1% | |
| Mở đầu "Vậy" | 13.1% | 0.8% | |
| Từ văn viết | 13.8% | 1.5% | |
| Trung bình từ | 15.9 | 17.6 | ≤ 25 |
| Câu > 25 từ | 4.6% | **10.2%** | |
| Mở đầu phổ biến nhất | 10.6% | 10.2% | ≤ 15% |
| Câu kho giữ được | 97.2% | 97.1% | |
| `follow_up` chứa cụm cuối `key_point` (dò thô) | 33% | **43%** | |
| Câu dự phòng | 4/282 | 6/266 | |

Lặp câu 0, vượt trần lượt 0, đủ phase ở cả hai. Thứ tự strong > average > weak 7/8 ở v3, 7/7 ở v4c (một phiên hỏng, xem Vấn đề khác). Trong 8 lần dự phòng của v4c, 6 lần do timeout trước token đầu và 2 lần do `answer_leak` (v3 cũng 2 lần), nên không do prompt.

**Xấu đi:** câu dài hơn, và `follow_up` vẫn chép `key_point`, luật "focus là ghi chú nội bộ" chưa có tác dụng đo được. **Khuôn mới:** ở `follow_up` và `hint`, "Khi" tăng từ 3% lên 28%, "Kể" lên 16%, trong khi "Vậy" trước đây là 30%. Prompt liệt kê từ mở đầu nào thì model dùng từ đó.

## Fable chấm mù
Phiếu trộn ngẫu nhiên, ẩn phiên bản và nguồn. Điểm giữa hai phiếu lệch thang (`wrap_up` v3: 5.0 ở phiếu 1, 4.0 ở phiếu 2), nên **chỉ so trong cùng phiếu**.

### Phiếu 2: v3 và v4 chốt (60 + 60)
| | v3 | v4 |
|---|---:|---:|
| `natural` TB | 3.25 | 3.37 |
| Câu ≥ 4 | 40% | 50% |
| Câu ≤ 2 | 11 | 11 |
| Hint đúng hành động | **62%** | **88%** |
| Hint `natural` | 2.69 | 3.19 |
| Câu AI tự đặt | 3.24 | 3.56 |
| Câu từ kho | 3.29 | 3.28 |
| `level_fit` vừa | 87% | 88% |

- v4 − v3: **+0.12, 95% CI −0.20 đến +0.45**. Bootstrap, hai mẫu độc lập.
- Ba câu dự phòng trong bộ v4 được 1.33; đã sửa khuôn `follow_up` sau khi chấm, chưa chấm lại. Bỏ 3 câu này thì v4 là 3.47.
- Câu kho hỏi danh sách 10 package được 2 điểm: nằm ở nội dung kho, prompt không sửa được mà không mất đáp án chuẩn.
- Phiếu 1 (bản v4b, 180 câu): v3 3.33, v4b 3.63, +0.30, CI −0.08 đến +0.68. Khác prompt nên chỉ để tham khảo.

### Fable có chấm ổn định không
Chấm lại đúng 60 câu v3 ở phiếu khác: trùng điểm 68%, lệch ≤ 1 100%, `action_ok` 92%, `level_fit` 83%. Trung bình 3.33 và 3.25. Ổn định ở mức này đủ để so hai bản, không đủ để bắt khác biệt nhỏ hơn ~0.3.

### Fable có thay được người không: chưa
So trên 60 câu v2 đã có nhãn người:
- Người 3.78, Fable 3.33. Trùng điểm 35%, lệch ≤ 1: 85%.
- 8 câu người chấm dưới 4 được Fable cho 3.38; 52 câu người chấm 4 được 3.33. **Fable không chọn cùng câu yếu với người.** Người gần như chỉ dùng điểm 4 nên dữ liệu này cũng ít thông tin.
- `action_ok` đồng ý 75%, `level_fit` 73%. Hint v2 đúng hành động: người 75%, Fable 31%.

Vì vậy không cộng độ lệch 0.45 để suy ra điểm người.

## Vấn đề khác phát hiện trong lúc đo
`timeout_s` của gateway là timeout từng lần đọc của httpx, không phải tổng thời gian: Evaluator 8 s từng chạy 180 s, Reporter 60 s chạy 170 s. Hai phiên bị hủy (`english_answers` ở v4 đầu, `junior-java-strong` ở v4c). Có từ trước, không do v4.

## Câu hỏi còn mở
1. Có cần người chấm 60 câu v4 không? Đây là cách duy nhất biết đạt 4.0 theo người.
2. Có đổi ngưỡng tự nhiên sang "≥ 90% câu từ 4 điểm, không câu nào ≤ 2" không?
3. Câu kho danh sách dài: DE chia nhỏ hay loại?
