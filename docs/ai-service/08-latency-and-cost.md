# 9. Latency & chi phí

> Thuộc bộ [AI Service design doc](README.md). Liên quan: §4.5 (luồng lượt), §8.6 (log usage).
>
> **Mọi con số tốc độ và giá trong file này là giả định để ước lượng**, phải đo lại bằng log thật (tuần 6, §12)
> và kiểm tra trang giá OpenRouter tại thời điểm triển khai.

## 9.1 Latency một lượt

Evaluator phải xong trước khi Interviewer biết hỏi gì, nên hai call **nối tiếp**. Thời gian tới token đầu tiên
ứng viên thấy:

```text
TTFT_user ≈ T_overhead + T_evaluator + T_interviewer_ttft

T_evaluator ≈ TTFT_model + output_tokens_evaluator / tốc_độ_sinh
```

| Thành phần | Giả định | Ước tính |
|---|---|---|
| `T_overhead`: APISIX + interview-service (lock, đọc session, lưu answer) + mạng tới ai-service | | ~0.15 s |
| RAG | Đã lấy sẵn lúc plan (§3.3.2), **không gọi mỗi lượt** | 0 s |
| `TTFT_model` (gpt-4o-mini qua OpenRouter) | 0.4–0.8 s | ~0.5 s |
| Evaluator output | ~200 token, tốc độ ~80 token/s | ~2.5 s |
| Interviewer TTFT | | ~0.5 s |
| **TTFT_user** | | **~3.6 s** |
| Interviewer stream hết câu hỏi | ~70 token / 80 token/s | +0.9 s |

**Mục tiêu:** TTFT_user **P50 ≤ 3.5 s, P95 ≤ 6 s**; câu hỏi hoàn chỉnh P95 ≤ 7 s. Lượt `dont_know` nhận diện bằng
regex (§4.5) bỏ qua Evaluator: ~1 s.

> Sprint plan đặt "P95 < 3 s cho evaluate endpoint" (S4-AIE-4) với thiết kế 1 call/lượt. Với Evaluator + Interviewer
> nối tiếp, đề xuất đổi chỉ tiêu thành TTFT như trên. Output token của Evaluator là biến số lớn nhất.

**Ngoài đường nóng** (không ảnh hưởng từng lượt):

| Bước | Ước tính | UX |
|---|---|---|
| Gắn CV: TCP job-service + tải file + parse | 5–9 s; CV đã parse ở phiên trước: < 0.5 s | Spinner "Đang đọc CV", sau đó hiện tóm tắt |
| `/start` (Planner ~1 500 token output + RAG cho 5–6 topic + Interviewer) | 15–25 s | Màn hình "Đang chuẩn bị buổi phỏng vấn"; event `: ping` giữ kết nối |
| `/finalize` (Reporter ~1 500 token output) | 15–30 s | Trang report polling mỗi 3 s |

## 9.2 Cách giảm độ trễ

Đã nằm trong thiết kế (MVP):

| # | Kỹ thuật | Hiệu quả |
|---|---|---|
| 1 | **Evaluator output gọn**: không viết đoạn lập luận; giới hạn `covered ≤ 3`, `missing ≤ 3`, `misconceptions ≤ 2`, `evidence ≤ 3` (quote ≤ 100 ký tự); key JSON ngắn; `max_tokens = 350` | Output token quyết định latency; mục tiêu ~200 token |
| 2 | Evaluator chỉ nhận **lượt của topic hiện tại**, không cả transcript | Input nhỏ, ổn định ~2.5k token dù phiên dài |
| 3 | **RAG lấy trước 1 lần lúc plan**, lưu `reference_snippets` trong plan | Bỏ ~0.3 s embed + query mỗi lượt |
| 4 | **Prompt caching**: phần tĩnh (vai trò, rubric, few-shot) đặt đầu, ≥ 1024 token | Giảm TTFT và giá input (OpenAI cache tự động theo prefix; qua OpenRouter cần kiểm chứng) |
| 5 | **Structured outputs strict** | Gần như không phải repair retry |
| 6 | Bỏ qua Evaluator khi không cần: wrap-up, câu trả lời **chỉ gồm** cụm "không biết" (regex neo cả câu; có nội dung khác thì vẫn chấm) | ~1 s thay vì ~3.6 s |
| 7 | 1 `AsyncOpenAI` client dùng chung (HTTP keep-alive), FastAPI async | Bỏ chi phí bắt tay TLS mỗi call |
| 8 | Interviewer `max_tokens = 200`, ≤ 80 từ | Câu hỏi xong nhanh |
| 9 | Planner / Reporter ngoài đường nóng; report bất đồng bộ | Không chặn trải nghiệm |
| 10 | UI hiện "đang gõ…" ngay khi gửi câu trả lời, stream từng token | Giảm độ trễ cảm nhận |

Dự phòng nếu đo thực tế vượt mục tiêu (chưa làm, theo thứ tự thử):

1. **Model nhỏ / nhanh hơn cho Evaluator** nếu đạt ngưỡng chất lượng §10 (đổi env, không đổi code).
2. **Tách Evaluator hai pha:** pha nóng chỉ trả `answer_type`, 4 band, `follow_up_focus`, `missing_points[0]`
   (~60 token) để policy chạy ngay; pha chi tiết (evidence, covered points) chạy **song song** với Interviewer
   stream, xong trước khi lưu lượt. Thêm 1 call/lượt (~+40% token input), giảm ~1.5 s.
3. Gửi trước câu dẫn trung tính cố định ("Mình hiểu rồi.") ngay khi nhận câu trả lời. Chỉ cải thiện cảm nhận.

## 9.3 Chọn model cho từng agent

Tất cả qua cùng một endpoint OpenAI-compatible. Env riêng từng agent; không đặt thì dùng `LLM_MODEL` (mặc định
`openai/gpt-4o-mini`, như `config.py` hiện có).

| Agent | Env | Mặc định | `temperature` | `max_tokens` | Output | Timeout / lần | Ghi chú |
|---|---|---|---|---|---|---|---|
| CV Parser | `LLM_MODEL_CV_PARSER` | gpt-4o-mini | 0 | 1200 | JSON strict | 20 s | Trích xuất, model nhỏ đủ |
| Planner | `LLM_MODEL_PLANNER` | gpt-4o-mini | 0.4 | 2500 | JSON strict | 25 s | 1 lần/phiên: ứng viên dùng model mạnh hơn nếu eval cho thấy plan kém (chi phí tăng không đáng kể) |
| **Evaluator** | `LLM_MODEL_EVALUATOR` | gpt-4o-mini | 0 (+ `seed` cố định) | 350 | JSON strict | 8 s, tổng ≤ 10 s | **Nhỏ, nhanh**, nằm trên đường nóng. Độ khắt khe đến từ rubric + luật code, không từ model to |
| Interviewer | `LLM_MODEL_INTERVIEWER` | gpt-4o-mini | 0.7 | 200 | Text stream | TTFT 5 s | Nhiệt độ cao hơn để câu hỏi tự nhiên, không rập khuôn |
| Reporter | `LLM_MODEL_REPORTER` | gpt-4o-mini | 0.3 | 2000 | JSON strict | 60 s | 1 lần/phiên: ứng viên dùng model mạnh hơn để nhận xét sâu hơn |

Đổi model của Evaluator **chỉ khi** chạy lại golden set (§10) và độ khớp với người chấm không giảm quá 5 điểm %.
Đổi model embedding là thay đổi contract dữ liệu (constitution IV), không thuộc phạm vi này.

## 9.4 Ước tính token & chi phí mỗi phiên

Phiên chuẩn 30 phút: 6 topic × ~2.5 lượt ≈ **15 lượt**, ~14 lượt được chấm.

| Call | Số lần | Input / lần | Output / lần | Tổng input | Tổng output |
|---|---|---|---|---|---|
| CV Parser | 1 | ~5 000 (1.5k prompt + 3.5k CV) | ~700 | 5 000 | 700 |
| Planner | 1 | ~4 500 (2k prompt + catalog + cv_profile) | ~1 500 | 4 500 | 1 500 |
| Evaluator | 14 | ~2 500 (1.6k tĩnh + 0.9k động) | ~200 | 35 000 | 2 800 |
| Interviewer | 15 | ~1 400 (0.9k tĩnh + 0.5k động) | ~70 | 21 000 | 1 050 |
| Reporter | 1 | ~6 200 | ~1 500 | 6 200 | 1 500 |
| Embedding (RAG lúc plan) | ~6 | ~60 | — | ~400 | — |
| **Tổng** | | | | **~72 000** | **~7 500** |

```text
cost_session = Σ (input_tokens × P_in + output_tokens × P_out)  − phần giảm từ cached input
```

**Giá giả định** cho gpt-4o-mini: `P_in = $0.15 / 1M token`, `P_out = $0.60 / 1M token` (giả định, kiểm tra
trang giá OpenRouter tại thời điểm triển khai):

| Kịch bản | Input | Output | Chi phí ước tính |
|---|---|---|---|
| Phiên chuẩn (15 lượt) | 72k | 7.5k | 72k × 0.15/1M + 7.5k × 0.60/1M ≈ **$0.015** |
| Phiên dài nhất (24 lượt) + 20% retry | ~125k | ~13k | ≈ **$0.027** |
| Planner + Reporter dùng model đắt gấp ~15 lần | | | ≈ $0.06–0.08 |
| 1 000 phiên / tháng (phiên chuẩn) | | | ≈ $15 |

Nằm dưới ngưỡng cảnh báo $0.10/phiên của S3-AIE-5. Rủi ro chi phí thật sự là **lạm dụng** (gọi thẳng ai-service,
tạo phiên liên tục), xử lý bằng quota ngày và chặn route `/ai/*` (§7.1).

## 9.5 Tải đồng thời

Quy mô đồ án (demo, vài chục người dùng): ~20 phiên đồng thời, mỗi lượt giữ kết nối ~5 s. FastAPI async + 2
worker uvicorn đủ dùng. Giới hạn thật là **rate limit của provider** (request/phút, token/phút theo tài khoản
OpenRouter); 429 đi vào nhánh retry ở §4.6. Không cần queue hay autoscale trong phạm vi 8 tuần.
