# Interviewer v3: câu hỏi ngắn, tự nhiên hơn (2026-10-28)

Harness full (29 persona, simulator LLM, mọi agent LLM, RAG + kho câu hỏi bật), gpt-4o-mini qua OpenRouter.
Trước: `eval-sim-bank-after2` (Interviewer v2, 2026-10-24). Sau: 4 vòng prompt v3 (a → d), bản chốt là **v3d**.
File phiên: `plans/reports/eval-sim-interviewer-v3{,b,c,d}.json` (không commit).

## Thay đổi
- `app/prompts/interviewer.v3.md`:
  - Câu hỏi ≤ 25 từ, tổng ≤ 35 từ (v2: ≤ 80 từ).
  - Tránh khuôn "Bạn có thể ... không?" và không mở đầu bằng "Bạn có thể".
  - Không nhắc lại lời ứng viên, không khen chê.
  - Ví dụ minh họa dùng chủ đề ngoài bài (git, DNS) để model không chép.
  - `hint` giữ nguyên câu đang hỏi và lồng gợi ý vào câu hỏi.
- `app/agents/interviewer.py`:
  - `recent_openers`: 3 chữ đầu của 4 câu gần nhất, để model tránh mở đầu trùng.
  - `reference_answer` chỉ gửi cho `hint`.
  - Khi có `bank_question` thì chỉ gửi tên topic, bỏ `opening_hint` (v3c cho thấy `opening_hint` kéo model sang câu tự đặt).
- `app/turn_engine.py`: lượt `hint` nhận đáp án chuẩn của câu vừa hỏi (nếu câu đó lấy từ kho).
- `app/question_stream.py`: chặn gợi ý chép ≥ 6 chữ liền từ đáp án chuẩn (`answer_leak`, thay bằng câu dự phòng).
- `app/rag/question_bank.py`: `kept_meaning` bỏ các từ khuôn câu hỏi ("bạn có thể giải thích sự khác biệt..."), để câu nói gọn vẫn được tính là giữ nghĩa câu kho.

## Kết quả

| Chỉ số | v2 | v3a | v3b | v3c | **v3d** | Ngưỡng |
|---|---|---|---|---|---|---|
| Khuôn "Bạn có thể ... không?" | 76% | 28% | 38% | 35% | **33%** | ≤ 40% |
| Độ dài TB (p90) | 31.5 (45) | 17.1 (24) | 18.6 (26) | 17.2 (24) | **16.6 (22)** | ≤ 25 |
| Mở đầu phổ biến nhất | 20% "giờ mình sang" | 16% | 22% | 13% | **15%** | ≤ 15% |
| Nhắc lại lời ứng viên | 29% | 4% | 4% | 5% | **6%** | — |
| Câu technical chính từ kho | 100% | 86% | 89% | 83% | **100%** | — |
| Thứ tự strong > average > weak | 5/8 | 8/8 | 6/8 | 8/8 | **7/8** | — |
| Recall lỗ hổng trong báo cáo | 0.75 | — | — | 0.875 | **0.955** | ≥ 0.70 |
| Lặp câu / sai ngôn ngữ | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | **0 / 0** | — |
| Fallback Interviewer | 0 | 0.3% | 0.3% | 0.9% | **0.6%** | — |
| Chi phí / phiên | $0.0080 | $0.0089 | $0.0088 | $0.0090 | **$0.0087** | ≤ $0.10 |
| TTFT P50 / P95 (s) | 3.8 / 6.0 | 4.7 / 7.4 | 4.6 / 6.7 | 4.7 / 8.2 | **4.4 / 7.0** | 3.5 / 6.0 |

Theo hành động (v2 → v3d):

| Hành động | Khuôn câu | Số từ TB |
|---|---|---|
| `ask_main` | 80% → **14%** | 28 → 16 |
| `follow_up` | 92% → **68%** | 34 → 16 |
| `hint` | 82% → **47%** | 36 → 20 |

`hint` hết dạng "hỏi câu mới". Mở đầu gợi ý đa dạng; v3a chép ví dụ "Thử nghĩ xem" 88%, v3b chép "Gợi ý nhỏ" 94%.

## Đọc kết quả
- **Cả ba ngưỡng văn phong đạt ở v3d** (v2 không đạt ngưỡng nào). Kết quả dao động giữa các lần chạy: khuôn câu 28–38%. Nên đọc là "đạt, sát ngưỡng", không phải số cố định.
- **Câu từ kho:** bỏ `opening_hint` khi có câu kho đưa tỉ lệ về 100%. Ở v3a–v3c, model bỏ câu kho kém sát topic để tự hỏi theo `opening_hint`, và lượt đó mất đáp án chuẩn.
- **TTFT tăng không do v3.** Các agent không đổi cũng chậm hơn trong cùng ngày: Planner 5.4 → 7.4 s, Evaluator 2.5 → 3.0 s, Reporter 10.7 → 13.3 s. Interviewer tăng 1.33 → 1.55 s. Cần đo lại độ trễ cùng thời điểm với v2 trước khi kết luận về mốc S4-AIE-4.
- **`follow_up` vẫn là nguồn khuôn chính (68%)**, thường ở dạng "Vậy bạn có thể ... không?". Ví dụ trong prompt chưa đủ để model bỏ.

## Việc tiếp theo
- `follow_up`: thử ví dụ âm (cấm rõ "Vậy bạn có thể"), hoặc để code viết lại phần mở đầu (rủi ro: câu kém tự nhiên). Đo lại.
- Dựng lại bộ 60 câu từ transcript v3d để người chấm so tự nhiên và hint trước/sau. Người chấm v2: tự nhiên 3.78, hint đúng 75% (`eval-261028-2255-golden-rater-a.md`).
- Đo lại TTFT v2 và v3 xen kẽ trong cùng một khung giờ.

## Câu hỏi còn mở
- Có cần đạt mốc TTFT P50 ≤ 3.5 s với gpt-4o-mini qua OpenRouter không, hay chấp nhận dao động theo nhà cung cấp?
