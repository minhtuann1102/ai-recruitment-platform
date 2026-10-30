# Đo nền Phase 05: độ bám nguồn, TTFT thật, sức khỏe RAG

Quick matrix 10 phiên × 2 vòng, agent + simulator LLM, Evaluator v4, main 6ea55e4 + harness mới, `evals.simulate --serve`
(service qua socket trong cùng tiến trình, có lifespan). Tắt Langfuse. JSON (gitignored):
`plans/reports/eval-sim-05-baseline-r{1,2}.json`, `eval-rag-05-baseline-holdout*.json`.

> **Đính chính cùng ngày:** "10% `no_source` ở `technical`" dưới đây là một lần chạy may mắn. Gộp 5 lần chạy RAG sạch: **24%**
> (mục "Sau khi sửa ngắt mạch"). Mọi số một lần chạy trong báo cáo này dao động mạnh, chỉ dùng số gộp.

## Kết quả

| Chỉ số | Vòng 1 (RAG sập 1 phút) | Vòng 2 (RAG sạch) |
|---|---|---|
| Request RAG `error` | **42 / 102** | 0 / 104 |
| Phiên mất cả kho từ đầu (không snippet, không câu kho) | 4 / 10 | 0 / 10 |
| Ý giữ lại trong `evidence` (tối đa 3 / lượt) | 72 | 88 |
| supported / no_source | 0.653 / 0.347 | 0.693 / 0.307 |
| Ý bị tài liệu bác bỏ (log `evaluator_sources`) | 0 | **2** (1 theo `R`) |
| Id nguồn LLM ghi hợp lệ (id bịa bị code bỏ) | 0.91 (5 bịa) | 0.94 (4 bịa) |
| Riêng `technical`: supported / no_source | 0.783 / 0.217 (60 ý) | **0.897 / 0.103** (68 ý) |
| Câu từ kho: supported | 0.92 (25 ý) | 0.974 (39 ý) |
| Câu AI tự đặt ở technical: supported | 0.706 (34 ý) | 0.793 (29 ý) |
| `no_source` ở lượt không có tài liệu / có tài liệu | 16 / 9 | 20 / 7 |
| Lượt `confidence = low` | 0.148 | 0.059 |
| TTFT p50 / p95 (s), qua socket, bỏ lượt không có token | **4.03 / 6.20** | **4.01 / 6.00** |
| Tổng lượt p50 / p95 (s), cùng mẫu | 4.10 / 6.41 | 4.32 / 6.21 |
| Chi phí TB / phiên (USD) | 0.00829 | 0.00867 |
| Fallback / request | 0.393 | 0.018 |

## Nhận xét

**1. Con số 53% `no_source` là sai mốc.** Nó đến từ `eval-sim-03a-v4-r2`, lần chạy có 35/98 lượt RAG lỗi. Lần sạch: 31%.

**2. Phần lớn `no_source` còn lại là do cấu trúc, không phải lỗi.** Ở vòng 2, 20/27 ý thuộc `intro` + `scenario`, nơi không
lượt nào có tài liệu: intro không truy hồi, scenario chỉ lấy `textbook` mà kho chưa có (Phase 04). Vậy không nên đặt ngưỡng
trên `no_source` toàn phiên.

**3. Trong 7 ý `no_source` có tài liệu (vòng 2), đọc tay 110 ký tự đầu mỗi tài liệu:** 4 ý tài liệu lệch hẳn chủ đề (vd
chunk `settings.py` của Django cho câu về OOP), 2 ý là nhận định chung về trade-off, 1 ý có thể LLM bỏ sót `R`. Mẫu quá nhỏ,
chưa phải số đo, nhưng gợi ý nguyên nhân ở truy hồi theo lượt nhiều hơn ở Evaluator.

**4. Một lần timeout làm mất RAG của mọi phiên trong 60 giây.** Log vòng 1: `rag_snippets_timeout` lúc 09:30:54 ở một
`/api/start`, ngắt mạch 09:30:55–09:31:55, 42 request lỗi. `get_retriever()` trả None nên mất luôn BM25 trong bộ nhớ và đáp
án chuẩn, dù chúng không phụ thuộc đường vector đã timeout. Phiên nào `start` trong khoảng này mất snippet và câu kho **cả
phiên**, kể cả sau khi mạch đóng. Nguyên nhân gốc: `/api/start` cùng lúc đẩy viết lại truy vấn (p50 4.4–6 s) + embed (p50
2.9 s) vượt `SNIPPET_DEADLINE_S = 5`. Quét lại file JSON: **8/12 lần chạy gần nhất có RAG lỗi** (18–73 request mỗi lần), tải
chỉ 4 phiên đồng thời. Kèm theo, các so sánh mô phỏng trước không cân: vd vòng 2 của 03a, v3 sạch còn v4 có 36 request lỗi
(golden không dùng RAG nên không ảnh hưởng).

**5. Nhánh `contradicted` có chạy; các báo cáo trước nói "0 ý" là sai.** `postcheck` đưa ý bị bác bỏ ra khỏi `evidence`, mà
`sim_metrics.grounding` chỉ đọc `evidence`, nên chỉ số đó luôn bằng 0 (reviewer phát hiện). Log cho số đúng: 0 và 2. Đọc tay
2 ý: `Exception` là lớp gốc, bị S2 bác đúng (`Throwable`). Ý còn lại đáng lo: persona strong nói `sleep()` / `wait()` đưa
thread vào BLOCKED hoặc WAITING, `R` là tài liệu mô hình cũ (ready / running), Evaluator bác và thêm misconception sai sự thật
"BLOCKED không phải là trạng thái chính thức trong Java"; `technical_accuracy` bị chặn 1, lượt còn 5.0. Đây là rủi ro của
nhánh chặn điểm khi kho không đầy đủ, nên đưa vào golden có tài liệu.

**6. TTFT các báo cáo trước thực ra là tổng thời gian lượt.** Chạy in-process, ASGI đệm cả body nên `ttft_s = total_s`. Lượt
trả lời câu wrap_up không có token mà vẫn vào mẫu (~10% lượt, ~2 ms), kéo percentile xuống; harness đã bỏ. Tính lại từ JSON
đã có: p50 4.0 s **chưa đạt** ≤ 3.5 s, p95 6.0–6.2 s sát mốc 6 s. Token đầu chỉ sớm hơn kết thúc ~0.16 s. Evaluator p50 2.9 s
chiếm gần hết.

**7. MRR held-out 0.836 và 0.820 so với 0.875 của Phase 01, recall giữ 0.938: chưa phải tụt chất lượng.** Hai truy vấn đổi
hạng do đường tìm timeout: h01 (`lexical`, corpus BM25 chưa nạp ở truy vấn đầu, `run_rag` không warm) và h06 (`vector`). Bỏ hai
truy vấn đó thì ~0.86. Còn h19 tụt hạng 1 → 2 ổn định qua hai lần, chưa rõ nguyên nhân. Một lần chạy khác treo 16 phút ở bước
nối `ai_db` (`error connecting in 'ai_db_reader'`) và đã bị dừng.

**8. Chưa đo:** `supported` là LLM tự khai, 0.897 chưa phải độ chính xác. Câu hỏi 1 của Phase 05 vẫn mở, cần `judge_support`.

## Sau khi sửa ngắt mạch

Sửa: ngắt cần 3 lỗi trong 2 phút (lúc đo là 30 s; 3 vòng đều 0 lần mở mạch nên không ảnh hưởng số dưới đây), start giữ topic đã
xong khi quá hạn, đang ngắt vẫn dùng BM25 + cache đáp án, không đọc ai_db. Cùng quick matrix,
`--serve`; JSON `eval-sim-05-breaker-{r1,r2,x8}.json`. `x8` là tải gấp đôi (8 phiên đồng thời).

| Chỉ số | r1 | r2 | x8 |
|---|---|---|---|
| Request RAG `error` | **0 / 103** | **0 / 108** | **0 / 107** |
| Phiên mất cả kho | 0 / 10 | 0 / 10 | 0 / 10 |
| Fallback / request | 0.009 | 0 | 0 |
| `technical`: no_source | 0.214 | 0.284 | 0.346 |
| TTFT p50 / p95 (s) | 3.57 / 7.28 | 3.86 / 6.94 | 4.06 / 7.51 |
| Evaluator p95 (ms) | 6230 | 5117 | 7526 |
| Ý bị bác bỏ (log) | 0 | 2 | 3 |
| Chi phí TB / phiên (USD) | 0.00861 | 0.00905 | 0.00915 |

- **Lỗi đã hết trong 3 vòng này**, kể cả tải gấp đôi. Vòng `x8` có đúng tình huống gây sập trước đây (`rag_snippets_timeout
  pending=1 found=1`): giờ chỉ `degraded`, phiên đó vẫn có tài liệu và câu kho. Trước đây 8/12 lần chạy dính lỗi, nên 3 vòng
  sạch là tín hiệu tốt, chưa phải bằng chứng tuyệt đối.
- **`no_source` tăng không phải do bản sửa.** Tài liệu mỗi lượt giữ nguyên so với vòng sạch trước (topic ~2, `R` ~0.47, turn ~1),
  cùng prompt v4; chỉ Evaluator tự khai khác đi. Lần `03b-r2` trước đó cũng 0.246.
- **Số gộp 5 lần RAG sạch** (`03b-r2`, baseline r2, breaker r1, r2, x8; 345 ý ở `technical`): `no_source` **0.243**, dao động
  0.10–0.35; câu từ kho supported 0.881 (176 ý); câu AI tự đặt 0.627 (169 ý).
- **p95 TTFT 6.9–7.5 s, cao hơn lần nền 6.0–6.2 s.** Đi cùng Evaluator p95 cao hơn. Lần `03b-r2` trước sửa cũng có p95 7.84 s với
  Evaluator p95 8.5 s, nên phần đuôi này là LLM, chưa có dấu hiệu do bản sửa. Vẫn vượt mốc 6 s.
- **Còn lại:** phiên `start` trong lúc mạch mở vẫn mất snippet + câu kho cả phiên, nhưng giờ chỉ xảy ra khi có 3 lỗi thật trong
  2 phút. 3 lỗi `rag_timeout` cùng lúc vẫn mở mạch (chưa phân biệt LLM chậm với ai_db hỏng); cả 3 vòng chưa có `rag_timeout` nào.
  `ai_db` chậm chứ không sập: mỗi start vẫn đợi đủ 5 s, chỉ `degraded`, không ngắt. Mạch mở mà cache đáp án trượt thì lượt đó không
  có đáp án chuẩn lẫn BM25 (hiếm: cache 2000 mục).
  Viết lại truy vấn p50 ~4.3 s vẫn vượt ngân sách 3.5 s, nên 1–3/10 start `degraded` (mất đường vector, còn BM25 + topic_id).

## Đề xuất
- `no_source` chỉ tính ở `technical`, dùng số gộp nhiều vòng (≥ 150 ý). Chưa đặt ngưỡng: mốc hiện tại 0.24, chờ phân loại.
- Câu hỏi mở số 4 (chính sách câu không có nguồn): intro coi `no_source` là bình thường; scenario chờ textbook (Phase 04).
- Lần chạy có `rag_health.error > 0` không dùng làm mốc.

- Golden có tài liệu đo `contradicted` qua `evaluate_with_raw` (có output LLM trước hậu kiểm), không qua `evidence`.

## Câu hỏi chưa giải quyết
- Sửa ngắt mạch thế nào: cần chọn trong đề xuất ở phase-05 (giữ BM25 khi mạch mở, không ngắt vì một timeout, hay nới hạn).
- `SNIPPET_DEADLINE_S = 5` có còn hợp lý khi viết lại truy vấn p50 đã 4.4–6 s?
