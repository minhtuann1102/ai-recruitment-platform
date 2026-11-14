# Trả lời đề xuất agentic ai-service (mục 13)

- Người trả lời: Thắng (AIE). Gửi: Tuấn (DE).
- Trả lời cho: `plans/reports/aie-request-261114-1057-agentic-ai-service.md`.
- Ngày: 2026-11-14. Căn cứ: code `main` tại `83725ad`, báo cáo đo 31/10 và 09/11.

## Tóm tắt

| # | Câu hỏi | Trả lời ngắn |
|---|---|---|
| 1 | Ngân sách độ trễ lượt có tra cứu | Lượt có tra cứu: TTFT P95 ≤ 7,5 s. Toàn phiên: P95 không tăng quá 0,3 s. |
| 2 | gpt-4o-mini có nhận `tools` cùng JSON schema strict qua OpenRouter không | **Chưa xác minh**: khóa API hết hạn. Đã có script thử, chạy lại khi có khóa mới. |
| 3 | Cách A hay B | **A** (gộp vào Evaluator), kèm điều kiện về số token ra. |
| 4 | Chunk docs có được bác ý sai không | **Không**, chỉ `R` như hiện tại. |
| 5 | `topic_id`, `category`, cỡ chunk | `category` bắt buộc và phải khớp đúng giá trị catalog. `topic_id` nên có cho topic technical. Chunk 150–300 token. |
| 6 | Track / topic cần docs trước | Phần scenario của `java_backend` và `nodejs_backend`. |
| 7 | Ngưỡng `WEAK_BELOW` / `STRONG_FROM` | Chưa hiệu chỉnh. Phải làm trước hạng mục 2. |
| 8 | Mốc để bật mặc định | Xem mục 8 bên dưới. |

## 1. Ngân sách độ trễ

Số đo 09/11 (`eval-261109-1648-ttft-breakdown.md`):

| Chỉ số | Giá trị |
|---|---|
| TTFT p50 / p95 toàn phiên | 3,97 s / 6,73 s |
| Evaluator | ~1,18 s cố định + 10,6 ms mỗi token ra |
| Mục tiêu đang ghi ở docs 08 | P50 ≤ 3,5 s, P95 ≤ 6 s |

Một bước gọi công cụ là thêm một lần gọi LLM nối tiếp: khoảng 1,2 s cố định, cộng ~20 token cho tool call và ~20 ms cho BM25. Lần gọi cuối cũng dài hơn vì input có thêm tối đa 600 token tài liệu. Ước tính mỗi lượt có tra cứu chậm thêm **~1,4–1,6 s**.

Đề xuất chốt:

- Lượt có tra cứu: TTFT P95 ≤ **7,5 s**.
- Toàn phiên: TTFT P95 không tăng quá **0,3 s** so với khi tắt cờ, đo trên full matrix.
- Vòng lặp công cụ có hạn riêng **2,0 s**. Quá hạn thì chấm bằng tài liệu đang có, như đề xuất mục 5.
- Tỷ lệ lượt gọi công cụ ≤ **30%** số lượt không có `R`. Cao hơn thì prompt đang tra quá tay, phải sửa trước khi đo tiếp.
- Vẫn tôn trọng timeout Evaluator 8 s và ngân sách tổng 10 s. Vòng lặp không được nới hai số này.

## 2. Tool calling cùng JSON schema strict

Chưa xác minh được. Ngày 14/11 đã chạy thử 5 lần với `openai/gpt-4o-mini`, cả 5 lần OpenRouter trả 401 "API key expired". Lỗi nằm ở khóa API, chưa nói gì về khả năng của model.

Theo tài liệu OpenAI, structured outputs dùng được cùng function calling. Nhưng OpenRouter có thể chuyển request sang provider khác, nên phải đo qua đúng đường đang chạy.

Script thử đã sẵn sàng, sẽ chạy lại khi có khóa mới. Script gọi bước 1 với `tools` + `response_format` strict, trả kết quả công cụ, rồi gọi bước 2 với `tool_choice="none"`. Script ghi lại provider, độ trễ từng bước và JSON cuối có đúng schema không.

Nếu không dùng chung được, thiết kế mục 4 vẫn ổn: bước cuối tách thành một lần gọi riêng không có `tools`. Cách này không tốn thêm lần gọi so với vòng lặp hiện đề xuất.

## 3. Cách A hay B

Chọn **A**, đồng ý với lý do TTFT.

Cách A vẫn có chi phí. Bốn trường mới (`next_action`, `next_focus`, `difficulty_delta`, `action_reason`) tốn khoảng 40 token ra, tức **+0,4 s** mỗi lượt theo mức 10,6 ms/token. Điều kiện kèm theo:

- `action_reason` tối đa 20 từ.
- Đo TTFT trước/sau. Nếu tăng quá 0,5 s ở P50 thì cân nhắc bỏ `action_reason`, chỉ giữ ở chế độ debug.
- Để đo được riêng chất lượng quyết định, ghi `decided_by` và tỷ lệ đồng ý với `decide()` như đề xuất. Không cần tách agent riêng chỉ để đo.

## 4. Chunk docs có được bác ý sai không

**Giữ chỉ `R`.** Lý do từ số đo 31/10 (`eval-261031-1700-judge-support.md`, `eval-261031-1800-evaluator-v6.md`):

- Độ chính xác của nhãn `supported` mới khoảng 0,64. Câu từ kho đạt 0,71, câu AI tự đặt 0,53.
- Lỗi chính là gpt-4o-mini gắn `supported` cho tài liệu không nói đúng ý đó (8/12 ca sai). Prompt v6 không sửa được lỗi này.

Nếu đã gắn nguồn sai cho ý đúng, thì cho chunk bác ý sai sẽ gây phạt oan. Mở quyền này chỉ khi độ chính xác của `refuted` trên chunk docs đạt ≥ 0,85, đo bằng `judge_support`.

Lưu ý thêm cho hạng mục 1: thêm chunk có thể làm **tăng** lỗi gắn nguồn sai. Tiêu chí xong phải đo **độ đúng** của `supported` bằng `judge_support`, không chỉ tỷ lệ `supported`.

## 5. Metadata và cỡ chunk

**`category` là bắt buộc, phải khớp chính xác giá trị trong catalog.** BM25 lọc theo `chunk.category == filters.category`.

- Lượt technical lấy `category` của topic trong catalog.
- Lượt scenario lấy **category phổ biến nhất của track** (`main_category`). Với `java_backend` và `nodejs_backend`, giá trị đó là `Backend`, không phải `System Design`. Chunk thiết kế hệ thống gắn `System Design` sẽ **không bao giờ** được tìm ở phần scenario của hai track này.
- Giá trị hiện có trong catalog: `Backend`, `Database`, `System Design`, `DevOps`, `Frontend`, `AI`.
- Hai cách xử lý. Một là DE gắn `Backend` cho docs thiết kế dùng cho scenario backend. Hai là AIE sửa `_filters` để scenario nhận thêm `System Design`. Mình nghiêng về cách hai vì nó đúng nghĩa hơn. Mình sẽ làm việc này trước khi DE nạp.

**`topic_id`: nên có cho chunk technical, để trống cho scenario.** Lý do:

- Truy hồi theo lượt chỉ cộng điểm (`TOPIC_BOOST`) cho chunk có `topic_id` trùng topic đang hỏi.
- Gợi ý (`hint`) ở lượt không có `R` chỉ lấy chunk cùng `topic_id`.
- Không có `topic_id` thì docs vẫn tìm được qua BM25, nhưng không bao giờ thành gợi ý và không được ưu tiên.
- Scenario không có `topic_id` cố định trong catalog nên để trống.

**Cỡ chunk: 150–300 token, mỗi chunk một ý, tối đa ~350.**

- Mỗi lượt lấy tối đa 3 chunk trong 600 token (`TURN_K`, `TURN_TOKENS`), tức ~200 token mỗi chunk. Chunk dài hơn sẽ bị cắt.
- Ghi chú của BM25 nói chunk rất dài đứng đầu mọi truy vấn.
- Nên đặt tiêu đề mục ở đầu chunk để BM25 bắt được thuật ngữ.

## 6. Track / topic cần docs trước

Từ 42 ý `corpus_gap` ngày 31/10:

| Track | Phần | Topic | Số ý không tìm thấy trong kho |
|---|---|---|---|
| java_backend | scenario | Thiết kế API quản lý đơn hàng với Spring Boot | 20 |
| nodejs_backend | scenario | Thiết kế dịch vụ upload file lớn | 8 |
| java_backend | technical | OOP và SOLID | 4 |
| java_backend | technical | Đa luồng và concurrency | 3 |
| java_backend | technical | Collections và HashMap | 3 |
| nodejs_backend | technical | Promise, async/await, event loop, Express | 4 |

Thứ tự đề xuất:

1. Thiết kế API backend: REST, transaction, idempotency, phân trang, xử lý đồng thời đơn hàng.
2. Upload file lớn: multipart/chunked upload, presigned URL, stream, giới hạn và kiểm tra file.
3. Java concurrency và OOP/SOLID.

Giới hạn của số liệu: mô phỏng 31/10 chỉ chạy level junior với hai track java và nodejs. Các track khác chưa có số. Khi DE nạp xong đợt đầu, mình sẽ chạy lại phân loại `no_source` cho cả 6 track để chọn đợt tiếp.

## 7. Ngưỡng `WEAK_BELOW` / `STRONG_FROM`

Chưa hiệu chỉnh. `policy.py` vẫn ghi hai ngưỡng 1,5 và 3,0 là "giả định mock". Chưa có báo cáo nào đo chúng.

**Phải làm trước hạng mục 2.** Hàm kiểm của hạng mục 2 so đề xuất của LLM với `decide()`. Nếu ngưỡng của `decide()` sai thì tỷ lệ đồng ý không còn ý nghĩa. Cách làm: chạy `simulate.py` full matrix với persona weak / average / strong, xem phân bố điểm lượt theo persona, rồi đặt ngưỡng ở chỗ tách các nhóm. Việc này của AIE.

## 8. Mốc để bật mặc định từng cờ

| Cờ | Điều kiện bật mặc định |
|---|---|
| `EVALUATOR_TOOLS` | Độ đúng của `supported` ở câu AI tự đặt ≥ **0,65** (mốc 0,53), câu từ kho không giảm (mốc 0,71). Độ khớp band trên golden + holdout không giảm. Không tăng trích nguồn sai id. Đạt ngân sách mục 1. |
| `POLICY_MODE=hybrid` | Ngưỡng ở mục 7 đã hiệu chỉnh. Tỷ lệ bị bác ≤ 15%. Cùng persona chạy 3 lần, độ lệch chuẩn điểm tổng (/10) không quá **1,2 lần** chế độ `rules` và không quá **0,5 điểm**. Khoảng cách điểm persona strong − weak không giảm quá 10% (mốc 3,74). Mọi ca chèn lệnh trong test injection không đổi được hành động. |
| `REPLAN_ENABLED` | Độ phủ yêu cầu JD không giảm. `/api/start` P95 tăng ≤ 0,5 s. State/plan cũ chạy được. FSD xác nhận interview-service lưu nguyên JSON. |
| Ghi chú (hạng mục 4) | Đọc tay 20 phiên, ≥ 85% ghi chú đúng với hội thoại. Không ghi chú nào chứa thông tin cá nhân. |

Lưu ý về mốc: đề xuất dùng mốc 0,63 / 0,88 của ngày 30/10. Số đó đo bằng judge cũ chưa hiệu chỉnh. Mốc đúng là **0,53 / 0,71**, đo bằng `judge_support` v2 đã hiệu chỉnh với bộ nhãn tham chiếu (agreement 0,85, kappa 0,70). Judge không tất định, các lần chạy lệch ±0,04, nên mỗi lần so cần chạy 3 lần lấy trung bình.

## Việc AIE nhận làm

1. Thay khóa API rồi chạy lại phép thử tool calling cùng JSON strict (câu 2).
2. Sửa `_filters` để scenario nhận `System Design`, trước khi DE nạp docs (câu 5).
3. Hiệu chỉnh `WEAK_BELOW` / `STRONG_FROM` bằng mô phỏng (câu 7).
4. Sửa mốc trong `plan_bank_coverage.py` và đề xuất theo số `judge_support` v2.
5. Việc ở mục 12 của đề xuất: khởi động lại ai-service, lọc `interview_style`, đổi 54 id golden, gỡ `langchain-core`.

## Câu hỏi chưa có lời đáp

- Tiêu chí chấm môn có yêu cầu agentic hay LangGraph không: chờ Tuấn hỏi mentor. Nếu có yêu cầu LangGraph thì phải xem lại quyết định A4 trước khi làm hạng mục 0.
- Mốc ở mục 8 là đề xuất của AIE. Cần nhóm thống nhất trước khi đo.
