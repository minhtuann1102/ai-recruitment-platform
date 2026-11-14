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
| 1 | **Evaluator output gọn**: không viết đoạn lập luận; giới hạn `covered ≤ 4` (v5), `missing ≤ 3`, `misconceptions ≤ 2`, `evidence ≤ 4` (quote ≤ 100 ký tự); key JSON ngắn; `max_tokens = 300` (prompt v2: bỏ tag, quote 3–12 từ, `covered ≤ 3`, `missing ≤ 2`; tag do code sinh) | Output token quyết định latency; mục tiêu ~200 token. Đo 22/10 trước khi đổi: Evaluator P50 4.8 s |
| 2 | Evaluator chỉ nhận **lượt của topic hiện tại**, không cả transcript | Input ổn định dù phiên dài (~2.5k token thời v3; đo v6 2026-11-02: ~4.6k) |
| 3 | **RAG lấy trước 1 lần lúc plan**, lưu `reference_snippets` trong plan | Bỏ ~0.3 s embed + query mỗi lượt |
| 4 | **Prompt caching**: phần tĩnh (vai trò, rubric, few-shot) đặt đầu, ≥ 1024 token | Giảm TTFT và giá input (OpenAI cache tự động theo prefix; đã kiểm chứng qua OpenRouter 2026-11-02, xem dưới bảng) |
| 5 | **Structured outputs strict** | Gần như không phải repair retry |
| 6 | Bỏ qua Evaluator khi không cần: wrap-up, câu trả lời **chỉ gồm** cụm "không biết" (regex neo cả câu; có nội dung khác thì vẫn chấm) | ~1 s thay vì ~3.6 s |
| 7 | 1 `AsyncOpenAI` client dùng chung (HTTP keep-alive), FastAPI async | Bỏ chi phí bắt tay TLS mỗi call |
| 8 | Interviewer `max_tokens = 200`, ≤ 80 từ | Câu hỏi xong nhanh |
| 9 | Planner / Reporter ngoài đường nóng; report bất đồng bộ | Không chặn trải nghiệm |
| 10 | UI hiện "đang gõ…" ngay khi gửi câu trả lời, stream từng token | Giảm độ trễ cảm nhận |

**Đo prompt caching (2026-11-02, LLM thật, quick matrix `--serve`, 10 phiên, `openai/gpt-4o-mini` qua OpenRouter, Evaluator v6):**
provider tự cache, code không đặt `cache_control`. Số lấy từ `metadata.usage.<agent>.cached_tokens`.

| Agent | Lần gọi | Input token | Cached | Tỉ lệ cached | Lần gọi có hit |
|---|---|---|---|---|---|
| Evaluator | 69 | 314 400 | 206 592 | 65.7% | 63/69 |
| Interviewer | 94 | 149 898 | 108 544 | 72.4% | 89/94 |
| Planner | 10 | 18 130 | 8 832 | 48.7% | 5/10 |
| Reporter | 10 | 26 971 | 6 144 | 22.8% | 6/10 |
| query_rewriter | 10 | 6 357 | 0 | 0% | 0/10 |
| **Tất cả** (gồm embedding) | | 517 530 | 330 112 | **63.8%** | |

Planner và Reporter vẫn có hit dù system prompt ngắn hơn 1024 token, vì phần đầu user message giống nhau giữa các phiên.
Chưa làm: `session_cost` chưa trừ phần cached nên mức ~$0.0094 / phiên là cận trên. Nếu input cached bằng 50% giá (giả định, chưa
kiểm bảng giá OpenRouter) thì thấp hơn ~26%. Chưa đo tác động lên TTFT vì không có lần chạy tắt cache để so.

Dự phòng nếu đo thực tế vượt mục tiêu (chưa làm, theo thứ tự thử):

1. **Model nhỏ / nhanh hơn cho Evaluator** nếu đạt ngưỡng chất lượng §10 (đổi env, không đổi code).
2. **Tách Evaluator hai pha:** pha nóng chỉ trả `answer_type`, 4 band, `follow_up_focus`, `missing_points[0]`
   (~60 token) để policy chạy ngay; pha chi tiết (evidence, covered points) chạy **song song** với Interviewer
   stream, xong trước khi lưu lượt. Thêm 1 call/lượt (~+40% token input), giảm ~1.5 s.
3. Gửi trước câu dẫn trung tính cố định ("Mình hiểu rồi.") ngay khi nhận câu trả lời. Chỉ cải thiện cảm nhận.

**Tách TTFT theo chặng (2026-11-09, không gọi LLM):** `python -m evals.ttft_breakdown <file phiên --serve>` tách TTFT
từng lượt thành Evaluator, query_rewriter + embedding và `other` (TTFT Interviewer + truy vấn DB RAG + overhead). Lượt
fallback được tách riêng. Gộp 880 lượt của 4 lần chạy full ngày 03/11:
- TTFT p50 3.97 s, p95 6.73 s. Evaluator chiếm 70%: p50 2.73 s, ~1.18 s cố định + 10.6 ms/token output, ~156 token.
  `other` có p50 1.10 s.
- **2.3% lượt Evaluator hết hạn** (timeout 8 s, ngân sách retry 10 s), mỗi lượt mất ~11 s. Bỏ nhóm này thì p95 còn 6.00 s.
- Khi fallback, `latency_ms.evaluator` ghi 0, nên thời gian chờ không xuất hiện trong metadata hay `/metrics`.

Vì vậy, nên cắt đuôi hết hạn trước (hedge request sau ~4.5–5 s hoặc hạ timeout), rồi mới tách hai pha nếu vẫn cần
p50 ≤ 3.5 s. Ước tính hai pha (lạc quan): p50 2.92 s, p95 4.27 s. Báo cáo:
`plans/reports/eval-261109-1648-ttft-breakdown.md`.

**Hedge request (2026-11-09, `app/llm/retry.py`, mặc định tắt):** đã cài và đo với Evaluator sau 5 s, chưa thấy lợi
ích (số đo bên dưới), nên để tắt; bật bằng `LLM_HEDGE_EVALUATOR=5` khi cần đo lại.
- Cơ chế (ví dụ bật với 5 s): lần gọi đầu quá 5 s chưa xong thì gửi thêm một request giống hệt (cùng `seed`), lấy kết quả về trước, hủy
  request kia. Request hedge dùng phần còn lại của ngân sách 10 s, nên tối đa 5 s. Lượt bị request đầu treo ước tính
  còn ~5 + 2.7 s thay vì ~10 s chờ rồi fallback. Retry, repair và thử lại `length` không được hedge.
  Agent không có ngân sách thì request hedge phải xong trong timeout của lần gọi; hết thời gian thì không hedge.
  Một request lỗi 4xx thì báo lỗi đó, không retry tiếp.
- Chi phí: đo 09/11 thêm 5–7% request Evaluator (ước tính trước từ log 03/11 là 3.3%). Request bị hủy vẫn có thể
  bị tính tiền, nhưng `metadata.usage` không ghi token của nó; `attempts` trong log `llm_call` tính cả request hedge.
- Cấu hình: env `LLM_HEDGE_<AGENT>` (giây; để trống / `0` / `off` = tắt). Mặc định tắt cho mọi agent.
- Từ cùng ngày, Evaluator fallback ghi thời gian đã chờ vào `latency_ms.evaluator` và `ai_agent_latency_seconds`.
  Trước đó là 0, nên `/metrics` không thấy các lượt chờ ~10 s. Hệ quả: p95 latency Evaluator trên dashboard sẽ tăng,
  và không so được với số trước 09/11.
- Đo 09/11 bằng LLM thật: hai quick `--serve` chạy cùng lúc, bật và tắt hedge, mỗi bản 65 lượt.
  - Cả hai bản không có lượt Evaluator hết hạn nên **chưa đo được lợi ích**. TTFT p95 5.99 / 5.70 s, trong mức dao động.
  - Hedge chỉ bắn 1/65 lần gọi, và lần đó lãng phí vì output dài (357 token): request đầu vẫn về sau 5.07 s.
  - Không có lỗi, không có repair, chi phí như cũ.
  - Muốn đo được lợi ích cần full matrix cho mỗi bản. Báo cáo: `plans/reports/eval-261109-1648-ttft-breakdown.md`.
- Full matrix 09/11 bật / tắt hedge (dừng ở 10–11/28 phiên vì key OpenRouter chạm hạn mức $10):
  - Hedge bắn 8/111 lần (7.2%), cả 8 lần request đầu vẫn thắng.
  - Lượt treo duy nhất thì cả hai request cùng hết hạn (11.2 s).
  - Gộp cả quick: hedge bắn 9/176 lần, cứu được 0. **Chưa có bằng chứng hedge giúp được**, mà tốn thêm 5–7% lần gọi.
- Full matrix chạy lại 09/11 (đủ 28/28 phiên mỗi bản, concurrency 2):
  - TTFT p95 bật / tắt: 6.10 / 6.20 s. Lượt hết hạn: 1 / 2.
  - Hedge bắn 15/221 lần (6.8%). Có thể cứu 3 lần (xong sau 7.5–7.8 s), còn lại request đầu vẫn thắng.
  - Tác động nhỏ hơn mức dao động, nên giữ tắt mặc định.

## 9.3 Chọn model cho từng agent

> **Cài đặt (Phase 02):** bảng dưới là nguồn của `app/llm/settings.py`. Env `LLM_MODEL_<AGENT>` đổi model từng agent; thông số khác cố định theo bảng. Test `tests/test_llm_settings.py` giữ bảng và code khớp.
>
> **Reasoning theo agent (từ 2026-11-03):** `LLM_REASONING_<AGENT>` = `off` | `minimal` | `low` | `medium` | `high`, gửi tham số `reasoning` của OpenRouter (`off` → `enabled: false`, còn lại → `effort`). Không đặt thì không gửi gì, request như trước. Cần cho model có reasoning như gpt-5-nano, gpt-6-luna: mặc định chúng tự suy nghĩ, tốn token ra và bị cắt `max_tokens` (đo 03/11: Claude Haiku 5.5 dùng hết 400 token cho reasoning rồi timeout). gpt-4o-mini không có reasoning nên không cần đặt. Đo 03/11 thay Evaluator bằng gpt-6-luna (`off`): chi phí Evaluator −46%, đạt golden, nhưng mô phỏng full cho thấy chấm khoan dung (persona weak không còn `dont_know`, khoảng cách strong − weak 3.74 → 2.44), nên vẫn giữ gpt-4o-mini. Reporter thì ngược lại: chạy lại 28 phiên, gpt-6-luna viết nhận xét cụ thể hơn, `gap_recall` 0.87–0.91 → 1.0, rẻ hơn 11%, nên `.env.example` đặt `LLM_MODEL_REPORTER=openai/gpt-6-luna`, `LLM_REASONING_REPORTER=off` (giá trong `evals/pricing.json`). Interviewer với gpt-6-luna (mô phỏng chạy cùng lúc với mốc): hết khuôn "Bạn có thể", câu kho 100%, TTFT như cũ, chi phí phiên −20%; CV Parser: qua kiểm cứng, rẻ hơn 22%. Nên `.env.example` cũng đặt Interviewer và CV Parser dùng gpt-6-luna (`LLM_REASONING_<AGENT>=off`). Planner, JD Parser, query rewriter đo 03/11: Planner với luna tự viết đủ `key_points` (gpt-4o-mini để code bù 36% topic), nhưng mô phỏng full cho thấy `key_points` dài làm truy vấn RAG lúc start dài hơn 50%, quá hạn 5 s nhiều hơn, câu kho 97.2% → 93.1%, nên giữ gpt-4o-mini; JD Parser hòa; query rewriter hòa nhưng p95 chậm hơn, gần hạn 3 s. Ba agent này chưa đổi; chi tiết ở `plans/reports/eval-261103-1526-evaluator-model-comparison.md`.
>
> **Timeout là hạn tổng của mỗi lần gọi (từ 2026-11-02).** Gateway cắt bằng `asyncio.wait_for`, vì timeout của httpx chỉ tính từng lần đọc: đo 02/11 có Evaluator 8 s chạy 180 s, Reporter 60 s chạy 170 s. Quá hạn nhận `LlmTimeoutError`, đi vào retry và fallback sẵn có. "tổng ≤ N s" là ngân sách dùng chung cho retry, repair và thử lại vì `finish_reason=length`: lần gọi đầu luôn đủ timeout, các lần sau chỉ còn phần dư. Agent có timeout phía interview-service (docs 06) phải có ngân sách nhỏ hơn timeout đó, nếu không fallback về không kịp. Agent không có ngân sách (Planner có hạn tổng riêng) thì mỗi lần gọi vẫn bị cắt ở timeout. Trong log 02/11 có 0/2 443 lần gọi cần repair, nên dùng chung ngân sách không làm mất lượt đo được. `embed` không dùng hạn này. **Vòng lặp công cụ (2026-11-14):** khi gọi với `budget_started`/`budget_s` (tool loop và đường lùi của nó), lần gọi đầu cũng bị cắt theo phần dư của ngân sách chung, để vòng lặp nhiều bước cộng đường lùi không vượt 10 s; chi tiết ở docs 02 §3.3.3. Lần gọi không truyền ngân sách giữ hành vi trên.
>
> **Tác động ước tính từ log 02/11 (không đo lại):** 17/930 lần gọi Evaluator (1.8%) dài hơn 8 s. Các lần này giờ bị cắt, lần retry chỉ còn ~1.5 s trong khi P50 là 3 s, nên gần như đều thành `degraded`. Query rewriter 10/282 lần quá 3 s, giữ truy vấn gốc. Reporter 1/115 lần quá 60 s. Planner không có lần nào quá hạn.

> **Ngân sách Evaluator khi bật tra cứu (2026-11-14, `EVALUATOR_TOOLS`).** Vòng lặp tool và đường lùi dùng chung **một** ngân sách 10 s từ đầu `evaluate_with_raw` (mọi lần gọi, kể cả lần đầu, bị cắt theo phần dư; xem docs 02). Không chia như vậy thì vòng lặp (≤ 8 s) cộng gọi lại (≤ 8 s) ≈ 18-20 s, vượt hạn sự kiện đầu 15 s của interview-service (docs 06). Trường hợp xấu nhất trước sự kiện `meta`: RAG theo lượt ≤ 1,0 s (`TURN_DEADLINE_S`) + Evaluator ≤ 10 s + chấm mock ≈ **≤ 11,5 s** < 15 s. Mốc cần đo khi có khóa API (reply mục 8): TTFT P95 lượt tra cứu ≤ 7,5 s, TTFT P95 cả phiên tăng ≤ 0,3 s, ≤ 30% lượt không `R` gọi công cụ **[BLOCKED-KEY]**; chưa có số đo nào. Lệnh đo và bảng kết quả gộp: `plans/reports/eval-261114-1807-agentic-rollout.md`.

Tất cả qua cùng một endpoint OpenAI-compatible. Env riêng từng agent; không đặt thì dùng `LLM_MODEL` (mặc định
`openai/gpt-4o-mini`, như `config.py` hiện có).

| Agent | Env | Mặc định | `temperature` | `max_tokens` | Output | Timeout / lần | Ghi chú |
|---|---|---|---|---|---|---|---|
| JD Parser | `LLM_MODEL_JD_PARSER` | gpt-4o-mini | 0 | 1200 | JSON strict | 20 s, tổng ≤ 28 s | **Giả định** như CV Parser (S2-AIE-6) |
| CV Parser | `LLM_MODEL_CV_PARSER` | gpt-6-luna (`LLM_REASONING_CV_PARSER=off`, từ 03/11) | 0 | 1200 | JSON strict | 20 s, tổng ≤ 28 s | Trích xuất, model nhỏ đủ |
| Planner | `LLM_MODEL_PLANNER` | gpt-4o-mini | 0.4 | 1500 (từ 2026-10-22, prompt v2: code sinh `opening_hint`, `backup_question`, bù `key_points` thiếu; P50 13 s → 8.2 s) | JSON strict | 25 s (hạn tổng 22 s) | 1 lần/phiên: ứng viên dùng model mạnh hơn nếu eval cho thấy plan kém (chi phí tăng không đáng kể) |
| **Evaluator** | `LLM_MODEL_EVALUATOR` | gpt-4o-mini | 0 (+ `seed` cố định) | 300 (từ 2026-10-22, prompt v2; đo output P95 ~200 token, P50 3.6 s) | JSON strict | 8 s, tổng ≤ 10 s | **Nhỏ, nhanh**, nằm trên đường nóng. Độ khắt khe đến từ rubric + luật code, không từ model to |
| Interviewer | `LLM_MODEL_INTERVIEWER` | gpt-6-luna (`LLM_REASONING_INTERVIEWER=off`, từ 03/11) | 0.7 | 200 | Text stream | TTFT 5 s, cả stream 15 s | Nhiệt độ cao hơn để câu hỏi tự nhiên, không rập khuôn. Hạn 15 s chặn stream treo sau token đầu (đo 02/11: 1 095 stream, dài nhất 5.3 s), quá hạn thì gửi `replace` bằng câu dự phòng |
| Query rewriter (RAG) | `LLM_MODEL_QUERY_REWRITER` | gpt-4o-mini | 0 | 60 | Text | 3 s, không retry | Chỉ khi tìm vector (topic < 2 cặp Q&A); đo 24/10 P50 1.6 s (ADR-010) |
| Reporter | `LLM_MODEL_REPORTER` | gpt-6-luna (`LLM_REASONING_REPORTER=off`, từ 03/11) | 0.3 | 2000 | JSON strict | 60 s, tổng ≤ 80 s | 1 lần/phiên: ứng viên dùng model mạnh hơn để nhận xét sâu hơn. `/api/finalize` có timeout 90 s |

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
