# Interviewer v5: giọng thân thiện, hint bám câu vừa hỏi (2026-11-06)

Harness quick (10 persona, simulator LLM, mọi agent LLM, RAG + kho câu hỏi bật). Interviewer gpt-6-luna, Evaluator gpt-4o-mini.
Mốc v4: cùng 10 persona lấy từ `eval-sim-planner-luna-261103.json` (Evaluator v7, cùng model Interviewer).
File phiên: `plans/reports/eval-sim-interviewer-{v4-quick-baseline-261103,v5a,v5b,v5}-quick-261106.json` (không commit, có câu từ kho DE).

## Yêu cầu
- Giọng thân thiện, lịch sự: "Vậy bạn có thể ... cho mình không?", "rồi giờ mình bắt đầu buổi phỏng vấn nhé".
- Không bắt buộc chủ ngữ "bạn"; dạng lịch sự xoay vòng với câu cùng nghĩa để không lặp.
- Hint dạng "Thế bạn kể thử cho mình nghe về ... xem?".
- Lỗi gốc từ /dev/play: hint đổi sang khái niệm khác (encapsulation → polymorphism) vì `focus` lấy key point của cả topic.

## Thay đổi
- `app/prompts/interviewer.v5.md`: bỏ luật cấm "Bạn có thể"; danh sách dạng lịch sự xoay vòng; câu chuyển phần nói đúng `phase`,
  không có `phase_changed` thì không nói; `ask_main` đúng `topic.title`; "mình" chỉ người phỏng vấn; hint giữ ý `last_question`,
  một câu hỏi, chỗ bám không được là chính đáp án.
- `app/agents/interviewer.py`: thêm `recent_forms` (dạng lịch sự ở 2 câu gần nhất) vào đầu vào; prompt cấm dùng lại.
- `app/focus.py` `hint_focus`, `app/policy.py` luật 4/6: focus của hint = `follow_up_focus` của Evaluator rồi ý còn thiếu;
  không còn lấy key point của cả topic. Không có thì `focus` rỗng, Interviewer gợi ý từ câu vừa hỏi và đáp án chuẩn.

## Ba vòng
| Chỉ số (code) | v4 | v5a | v5b | v5 (chốt) |
|---|---:|---:|---:|---:|
| "bạn có thể" | 0% | 42% | 25% | 25% |
| Hai câu liền đều "bạn có thể" | 0 | 15 | 4 | 5 |
| Hint lệch sang khái niệm khác | – | 2/10 | 0/11 | 1/11 |
| Hint lộ đáp án (đọc tay) | 0/15 | ≥2 | 2/11 | 1/11 |
| Trung bình từ (≤ 25) | 18.6 | 23.3 | 20.9 | 21.0 |
| Mở đầu phổ biến nhất (≤ 15%) | 10% | 17.2% | 18.6% | **19.6%** ("vay ban co") |
| Câu dự phòng | – | 1 | 1 | 1 |

v5a: luật xoay vòng chỉ nằm trong prompt, model bỏ qua. v5b: thêm `recent_forms` và `hint_focus`. v5: thêm luật hint không nêu đáp án.

## Judge v1 (v4 so với v5b, câu AI tự đặt)
| | v4 (43) | v5b (42) |
|---|---:|---:|
| natural | 4.12 | 4.12 |
| action_ok | 90.7% | 92.9% |
| single_question | 79.1% | 83.3% |
| level_fit ok | 53.5% | 61.9% |
| hint action_ok | 6/9 | 4/7 |

Mẫu nhỏ, chưa chứng minh v5 tốt hơn; chỉ cho thấy không kém đi. Judge không bắt được hint lộ đáp án
("kể thử về hai phương thức equals và hashCode" chấm `leaks = false`), và judge v1 vẫn chấm khuôn "Bạn có thể ... không?" là 3 điểm
nên không đo được mục tiêu giọng mới.

## Còn lại
- Mở đầu "Vậy bạn có" 19.6%, vượt ngưỡng 15% của `evals.sim_style`. Ngưỡng đặt khi mục tiêu là bỏ khuôn này; cần chốt lại ngưỡng
  theo giọng mới hoặc giảm "Vậy" trong prompt.
- Hint còn lộ một phần đáp án ("nếu java.lang.Throwable là lớp gốc thì hai lớp con là gì"); `answer_leak` chỉ bắt chép ≥ 6 chữ.
- Hint phần giới thiệu đôi khi lan man; một hint gần như nhắc lại nguyên câu hỏi.
- Chưa có nhãn người cho câu v5.
