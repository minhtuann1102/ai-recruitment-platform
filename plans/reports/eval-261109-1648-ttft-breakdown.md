# Tách TTFT theo chặng từ log mô phỏng (2026-11-09)

Không gọi LLM. Script mới `python -m evals.ttft_breakdown <file phiên>` đọc `ttft_s` (đo qua socket) và `metadata.latency_ms`
của từng lượt next-turn. Chỉ dùng file chạy `--serve`: chạy in-process thì `ttft_s` bằng tổng thời gian lượt (các file v5
ngày 06/11 vì vậy bị bỏ).

Dữ liệu chính: 4 lần chạy full ngày 03/11 (Evaluator v7 gpt-4o-mini, Interviewer gpt-6-luna hoặc gpt-4o-mini, RAG bật),
gộp được 880 lượt có Evaluator: `eval-sim-{evaluator-v7,interviewer-luna,planner-base-4omini,planner-luna}-261103.json`.

## Cách tách
Một lượt chạy nối tiếp (`app/turn_engine.py`): RAG theo lượt → Evaluator → Interviewer stream. `latency_ms` chỉ có thời gian
gọi LLM, nên:
- `evaluator`: thời gian gọi Evaluator, gồm cả retry và repair.
- `other` = TTFT − evaluator − query_rewriter − embedding: TTFT Interviewer + truy vấn DB RAG + overhead. Chưa tách được
  TTFT Interviewer vì metadata chỉ ghi thời gian cả stream.
- Lượt fallback được tách riêng. Khi Evaluator hết hạn, `latency_ms.evaluator` ghi 0 nên thời gian chờ không hiện ra
  ở đâu. Interviewer quá hạn TTFT 5 s thì dùng câu dự phòng.

## Kết quả (gộp 880 lượt)
| | p50 (s) | p95 (s) |
|---|---:|---:|
| TTFT mọi lượt | 3.97 | **6.73** |
| TTFT bỏ 20 lượt Evaluator hết hạn | 3.93 | **6.00** |
| Evaluator (lượt bình thường) | 2.73 | 4.53 |
| `other` (TTFT Interviewer + DB + overhead) | 1.10 | 2.12 |
| query_rewriter + embedding | 0 | 0 |
| Ước tính Evaluator hai pha | 2.92 | 4.27 |

- **Evaluator chiếm 70% TTFT** (trung vị theo lượt). Output ~156 token, input ~4.7k token. Hồi quy: ~1.18 s cố định
  + 10.6 ms/token output. Phần output (~1.65 s) là phần cắt được.
- Chỉ 29% lượt đạt p50 ≤ 3.5 s; 7.4% lượt vượt 6 s.
- **Lượt Evaluator hết hạn: 20/880 (2.3%), mỗi lượt ~11 s** (10.9–12.5 s). Con số khớp với timeout 8 s, ngân sách
  retry 10 s rồi chấm heuristic, cộng ~1 s cho Interviewer. Riêng nhóm này kéo p95 từ 6.00 lên 6.73 s.
- Lượt bình thường có Evaluator > 5 s: 3.3%, > 6 s: 1.6%, > 8 s: 0.2%. Tối đa là 9.6 s, khi đó đã có retry.
- RAG theo lượt không gọi LLM ở các lượt này (câu từ kho dùng đáp án chuẩn), nên không đáng kể.
- Interviewer quá hạn TTFT 5 s: 8/880 lượt, dùng câu dự phòng.

Theo lần chạy (lượt bình thường / mọi lượt):
| File | Lượt | TTFT p50 | p95 mọi lượt | p95 bỏ Evaluator hết hạn | Evaluator hết hạn |
|---|---:|---:|---:|---:|---:|
| evaluator-v7-261103 | 225 | 4.18 | 6.72 | 6.22 | 2 |
| interviewer-luna-261103 | 213 | 4.11 | 6.73 | 6.22 | 5 |
| planner-base-4omini-261103 | 214 | 3.74 | 7.81 | 5.70 | 7 |
| planner-luna-261103 | 228 | 3.81 | 6.71 | 5.91 | 6 |

Lần quick 02/11 (`eval-sim-06-v6-r1..r8`, Evaluator v6) không có lượt Evaluator hết hạn, p95 5.2–6.0 s.

## Ước tính hai pha (lạc quan)
Pha nóng ~60 token: 1.18 + 0.06 × 10.6 ≈ 1.81 s thay cho 2.73 s ở trung vị. Ước tính đạt cả hai đích trong mọi lần chạy
(p50 2.6–3.4 s, p95 3.1–5.0 s), nhưng bỏ qua phần input thêm và tải của call thứ hai. Lượt hết hạn vẫn giữ ~11 s.

## Đề xuất (theo thứ tự)
1. **Cắt đuôi Evaluator hết hạn trước.** Mức này đủ đưa p95 về ~6.0 s, sửa ít hơn tách hai pha.
   - Hedge: sau ~4.5–5 s chưa có kết quả thì gửi thêm một request, lấy kết quả về trước. Tốn thêm ~3–10% call
     Evaluator (3.3% lượt > 5 s, 9.9% lượt > 4 s).
   - Hoặc hạ timeout từ 8 s xuống ~5 s, giữ một lần retry trong ngân sách: phần Evaluator của lượt hết hạn còn khoảng
     5 + 2.7 ≈ 7.7 s thay vì ~10 s, nhưng 3.3% lượt chậm sẽ bị hủy rồi gọi lại.
   - Cần đo bằng LLM thật. Chưa biết vì sao các lượt này hết hạn (provider treo hay hàng đợi), vì log mô phỏng không
     lưu loại lỗi.
2. **Tách Evaluator hai pha** nếu p50 vẫn phải ≤ 3.5 s: chỉ cách này kéo được trung vị.
3. Ghi thời gian chờ vào `latency_ms.evaluator` khi fallback và ghi TTFT Interviewer vào metadata. Hiện cả hai không
   có, nên `other` gộp nhiều thứ, và `/metrics` không thấy được thời gian chờ Evaluator hết hạn.

## Đo lại sau khi cài hedge (09/11, LLM thật)
Hai quick `--serve` chạy cùng lúc trên cùng code (Evaluator v8, Interviewer v5), khác nhau chỉ ở `LLM_HEDGE_EVALUATOR`.
Mỗi bản 10 phiên, 65 lượt có Evaluator. File phiên: `eval-sim-07-hedge-{on,off}-261109.json` (không commit).

| | Hedge bật (5 s) | Hedge tắt |
|---|---:|---:|
| TTFT p50 / p95 (s) | 4.16 / 5.99 | 4.34 / 5.70 |
| Evaluator p50 / p95 (s) | 2.99 / 4.71 | 3.03 / 4.53 |
| Lượt Evaluator hết hạn | 0 | 0 |
| Lần gọi có hedge | 1/65 | – |
| Interviewer quá hạn TTFT 5 s | 1 | 1 |

- **Chưa đo được lợi ích:** cả hai bản đều không có lượt Evaluator hết hạn. Với tỉ lệ 2.3% của ngày 03/11, kỳ vọng chỉ
  ~1.5 lượt mỗi bản, nên quick không đủ mẫu. Chênh lệch p50/p95 giữa hai bản nằm trong mức dao động.
- **Không thấy hồi quy:** không có lỗi, không có repair, chi phí phiên như nhau ($0.0094).
- **Lần hedge duy nhất là lãng phí:** lần gọi đó có output dài 357 token, request đầu về sau 5.07 s, ngay sau khi gửi
  request hedge. Lượt chậm vì output dài thì hedge không giúp được; chỉ lượt bị treo mới được lợi.
- TTFT p50 4.2–4.3 s, cao hơn 03/11 (3.97 s). Input Evaluator v8 là ~5.1k token, so với ~4.7k của v7.
- Chi phí lần đo khoảng $0.2.

Muốn đo được lợi ích thì cần full matrix (~220 lượt) cho mỗi bản, hoặc chạy lại nhiều vòng quick rồi gộp bằng
`evals.ttft_breakdown`.

## Full matrix bật / tắt hedge (09/11, LLM thật, dừng giữa chừng)
Hai bản full `--serve` chạy cùng lúc. Key OpenRouter chạm hạn mức tổng $10 (403 `Key limit exceeded`), nên chỉ xong
10/28 phiên (bật hedge) và 11/28 phiên (tắt hedge); mọi phiên nodejs và adversarial đều lỗi. Log còn có cảnh báo pool DB
`limited to pool_size: 15`, nên tải nặng hơn các lần trước. File: `eval-sim-08-full-hedge-{on,off}-261109.json`.

| | Hedge bật | Hedge tắt |
|---|---:|---:|
| Lượt có Evaluator | 89 | 98 |
| TTFT p50 / p95 (s) | 4.50 / 6.70 | 4.48 / 6.70 |
| Evaluator p50 / p95 (s) | 3.34 / 5.39 | 3.37 / 5.19 |
| Lượt Evaluator hết hạn | 1 (11.2 s) | 0 |
| Lần gọi có hedge | 8/111 (7.2%) | – |

- **Cả 8 lần hedge đều lãng phí.** Các lần gọi này kết thúc sau 5.2–6.7 s, output 173–364 token. Theo hồi quy
  (~1.27 s + 13.6 ms/token), request hedge gửi lúc 5 s không thể về trước ~7 s, nên request đầu thắng cả 8 lần.
- **Lượt treo duy nhất không được cứu:** cả request đầu và request hedge đều hết hạn, lượt mất 11.2 s.
- Tỉ lệ hedge 7.2% cao hơn ước tính 3.3%, vì dưới tải này Evaluator chậm hơn (p50 3.3 s so với 2.7 s ngày 03/11).
- Gộp với quick: 176 lần gọi có hedge bật, hedge bắn 9 lần (5.1%), cứu được 0, còn 1 lượt hết hạn.

**Kết luận tạm (mẫu nhỏ, 1 lượt treo):** hedge sau 5 s chưa có bằng chứng giúp được gì, mà tốn thêm 5–7% lần gọi
Evaluator. Lần treo quan sát được làm cả hai request cùng treo, nên có vẻ là sự cố phía provider trong khoảng thời gian
đó, chứ không phải một request riêng lẻ bị kẹt. Việc ghi thời gian chờ khi fallback vẫn đúng và nên giữ.

## Full matrix chạy lại (09/11, sau khi nâng hạn mức key, concurrency 2 mỗi bản)
Hai bản chạy cùng lúc, đủ 28/28 phiên mỗi bản, không lỗi, không cảnh báo pool DB.
File: `eval-sim-09-full-hedge-{on,off}-261109.json`. Bản bật dùng `LLM_HEDGE_EVALUATOR=5`.

| | Hedge bật (5 s) | Hedge tắt |
|---|---:|---:|
| Lượt có Evaluator | 222 | 221 |
| TTFT p50 / p95 (s) | 4.07 / 6.10 | 3.97 / 6.20 |
| Evaluator p50 / p95 (s) | 3.15 / 5.17 | 3.06 / 5.03 |
| Lượt Evaluator hết hạn (~10.9 s) | 1 | 2 |
| Lần gọi có hedge | 15/221 (6.8%) | – |
| Chi phí phiên | $0.01032 | $0.01018 |

- Đa số lần hedge vẫn lãng phí: 12/15 lần xong trong 5.0–6.4 s, tức request đầu về trước.
- Có thể hedge đã cứu 3 lần, kết thúc sau 7.5–7.8 s. Lần rõ nhất có output chỉ 82 token, bình thường mất ~2.2 s;
  nếu request đầu không treo thì đã xong từ lâu. Log không ghi request nào thắng, nên chưa khẳng định được.
- Lượt hết hạn 1 so với 2, và p95 6.10 so với 6.20 s: chênh lệch quá nhỏ để kết luận.
- Đổi lại, số lần gọi Evaluator tăng 6.8%. Chi phí phiên tăng 1.4%, nằm trong mức dao động.
- Tỉ lệ hết hạn 09/11 là 0.5–0.9%, thấp hơn 2.3% ngày 03/11. Vì vậy p95 lần này gần 6 s ở cả hai bản.

**Kết luận:** hedge có thể cứu được vài lượt treo, nhưng tác động lên p95 nhỏ hơn mức dao động, mà tốn thêm ~7% lần
gọi Evaluator. Giữ quyết định tắt mặc định.

**Quyết định (09/11):** hedge để tắt mặc định, bật bằng `LLM_HEDGE_EVALUATOR=5` khi cần đo lại. Giữ phần ghi thời
gian chờ khi fallback.

## Giới hạn
- Log ngày 03/11 dùng Interviewer v4. v5 dài hơn khoảng 2 từ/câu, ảnh hưởng không đáng kể đến TTFT.
- Một số lần chạy full có 2 mô phỏng chạy cùng lúc, nên tải cao hơn một phiên thật.
- Số mẫu hết hạn nhỏ (20), tỉ lệ 2.3% có thể dao động giữa các lần chạy.

## Câu hỏi chưa giải quyết
- Owner chấp nhận chi phí Evaluator tăng 3–10% để hedge không?
- Có cần p50 ≤ 3.5 s ở MVP không, hay p95 ≤ 6 s là đủ? Câu trả lời quyết định có tách hai pha hay không.
