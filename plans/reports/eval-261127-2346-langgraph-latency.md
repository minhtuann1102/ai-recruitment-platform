# Đo độ trễ LangGraph + checkpoint phiên (plan 261127-1517, phase 06)

Ngày 2026-11-27 · nhánh `thang/langgraph-latency-docs` · **không gọi LLM** (agent ép mock, simulator quy tắc).
Lệnh: `cd apps/ai-service && python -m evals.session_store_latency --sessions 20 --db-url postgresql://...@localhost:5545/postgres --out <json>`.
Báo cáo không chứa câu trả lời ứng viên (chỉ số).

## Thiết lập
- Máy dev macOS 16 GB, Python 3.11, Postgres 16-alpine **local** (docker `-p 5545:5432`), pool tối đa 10.
- Mỗi tổ hợp `SESSION_STORE` × `SESSION_GRAPH`: 1 phiên warm-up (bỏ) + 20 phiên mock persona `junior-java-average`,
  chạy nối tiếp, service thật qua socket (TTFT thật phía client, có chạy lifespan nên store đã mở).
- Mỗi request `/api/next-turn`: TTFT, tổng thời gian, tổng thời gian đọc / ghi checkpoint (metric
  `ai_session_checkpoint_seconds`, gồm cả lần ghi trong graph). Percentile nearest-rank. Mẫu: ~130-140 request / tổ hợp.
  Phiên mock ~7 lượt nên P95 dựa trên ít mẫu: đọc là mức xấp xỉ.

## Kết quả (ms)

| Store / graph | TTFT P50 | TTFT P95 | Tổng P50 | Tổng P95 | Đọc P50 / P95 | Ghi P50 / P95 | Đọc+ghi P95 | Checkpoint / phiên | Byte DB / phiên |
|---|---|---|---|---|---|---|---|---|---|
| memory / per_turn | 3 | 3 | 4 | 5 | 0,10 / 0,18 | 0,03 / 0,04 | 0,22 | 15 | – |
| memory / session | 3 | 4 | 5 | 6 | 0,11 / 0,20 | 0,04 / 0,06 | 0,25 | 16 | – |
| postgres / per_turn | 6 | 8 | 11 | 14 | 2,9 / 4,5 | 2,9 / 3,5 | 7,8 | 15 | 106 059 (~104 KB) |
| postgres / session | 7 | 8 | 13 | 15 | 2,9 / 3,7 | 6,9 / 8,6 | 12,1 | 16 | 117 211 (~114 KB) |

(Giá trị TTFT / tổng làm tròn tới ms do `call_sse` làm tròn 3 chữ số giây. Phiên 1 dùng bảng checkpoint đã có, 3 lần
chạy lại cho số cùng cỡ: Postgres đọc+ghi P95 7,7-12,1 ms.)

Tham chiếu phase 02 (graph mỗi lượt, mock, memory): P50 3,0-3,5 ms, P95 4,5-6,9 ms: khớp với dòng memory.

## So với tiêu chí (phase 06)
| Tiêu chí | Kết quả | |
|---|---|---|
| Overhead graph < 50 ms P50 | tổng lượt mock P50 4-5 ms (memory), 11-13 ms (Postgres), gồm cả logic Evaluator / Interviewer mock | Đạt |
| Đọc + ghi checkpoint < 100 ms P95 trên DB | 7,8 ms (per_turn), 12,1 ms (session) trên Postgres local | Đạt **trên local** |

Caveat: Postgres local trên cùng máy, RTT ~0. Supabase / staging có RTT mạng (thường 10-60 ms mỗi lệnh) và mỗi lượt có
khoảng 8-9 lệnh đọc / ghi, nên **phải đo lại khi DE dựng DB đích**; con số này không đủ kết luận cho prod.
`session` ghi chậm hơn `per_turn` (P50 6,9 vs 2,9 ms) vì `interrupt` ghi thêm checkpoint + `pending_writes` mỗi lượt.
Mức 12 ms vẫn rất nhỏ so với ngân sách ~10 s của Evaluator.

## Phình do lần chạy lỗi (review phase 05, M3)
Một phiên mới, gửi 10 lần `/api/next-turn` `answer_source=voice`, `answer="ừm"` (422 `voice_no_speech`):

| Store / graph | Checkpoint thêm | Byte thêm (Postgres) |
|---|---|---|
| memory / per_turn | +10 | – |
| memory / session | +10 | – |
| postgres / per_turn | +10 | +16 822 (~1,7 KB / lần) |
| postgres / session | +10 | +13 878 (~1,4 KB / lần) |

- **Phình không riêng `session`**: `per_turn` cũng +1 checkpoint mỗi lần lỗi (graph chạy tới `perceive` rồi ném lỗi,
  `durability="exit"` ghi lại). Mỗi lượt 409 / 422 / bị ngắt / Reporter lỗi đều thêm một checkpoint không bao giờ bị xoá.
- Quy mô: ~1,5 KB / lần lỗi; 10 lần lỗi ≈ 15 KB, so với ~105-115 KB cả phiên bình thường (20 lượt mock tốn nhiều hơn).
  Chưa nguy hiểm nếu client không retry vô hạn; phiên của ứng viên cố ý spam vẫn tăng tuyến tính, không giới hạn.
- Khuyến nghị (owner: DE): (1) TTL theo `created_at`/job dọn phiên cũ (đã có trong doc 12 mục 9); (2) xoá checkpoint cũ của
  thread khi `/finalize` xong (giữ lại checkpoint cuối, hoặc xoá thread sau khi FSD lưu report); (3) tuỳ chọn:
  giới hạn số lần lỗi liên tiếp mỗi `turn_number` ở lớp guard (429), nếu thấy bị spam. AIE chưa tự làm gì ở code.

## Chưa làm
- `cost_latency` với LLM thật: **cần user đồng ý** (tốn token), ngoài phạm vi lần này, để mở.
- Đo trên Supabase / staging; đo đồng thời nhiều phiên (chỉ đo concurrency 1).

## Câu hỏi mở
1. DB đích là Supabase `ai_db` hay Postgres trên VM (doc 12 G9)? Khi chốt cần chạy lại bench với `--db-url` đó.
2. TTL phiên và dọn checkpoint lỗi: DE nhận việc, chính sách giữ bao lâu (consent)?
3. Có cần giới hạn số lần retry lỗi mỗi lượt không, hay đủ TTL?
4. Có cho chạy `cost_latency` thật một lần (ước tính chi phí nhỏ) để có TTFT thật + overhead đã chứng minh ngoài mock không?
