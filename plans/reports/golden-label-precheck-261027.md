# Pre-check nhãn retrieval golden set RAG (spec 005 T041)

- Ngày: 2026-10-27. Chỉ báo cáo, **không sửa** `rag_golden*.json`, không điền `approved_by`, không chạy eval trên DB.
- Input (main `eed98fa`): `apps/ai-service/evals/rag_golden.json` (24 query, `k=5`, 5 group), `rag_golden_holdout.json` (32 query, `k=5`, group `vi` = "tiếng Việt thuần, không thuật ngữ Anh"); corpus 144 pair trong `apps/data-pipeline/data/seeds/interview_qa/hard-*.json`; category của pair lấy theo `topic_id` trong `apps/ai-service/app/catalog/*.yaml` (cách `qa_record_builder.py` gán).
- Cách làm: đọc cả 144 pair (question + answer), đối chiếu từng query; kiểm group rule và `filters`.
- Metric hiện tại là hit@k (`rag_metrics.hit_at_k`: trúng **bất kỳ** id nào trong `relevant` là hit). Vì vậy thêm id chỉ làm query dễ trúng hơn, nên chỉ đề xuất thêm khi pair đó thật sự trả lời được query.

## 1. Bảng tóm tắt

| Query | Group | Đề xuất | Độ tin cậy |
|---|---|---|---|
| g01 | vi | keep | cao |
| g02 | vi | **reword** (hoặc add de-qa-1016) | cao |
| g03 | vi | keep | cao |
| g04 | vi | keep | cao |
| g05 | vi | keep (xem ghi chú) | trung bình |
| g06 | vi | keep | cao |
| g07 | mixed | keep | cao |
| g08 | mixed | keep | cao |
| g09 | mixed | keep | cao |
| g10 | mixed | keep | cao |
| g11 | mixed | keep | cao |
| g12 | mixed | keep | cao |
| g13 | mixed | keep | cao |
| g14 | en | keep | cao |
| g15 | en | keep | cao |
| g16 | en | keep | cao |
| g17 | en | keep | cao |
| g18 | en | keep | cao |
| g19 | en | keep | cao |
| g20 | no_diacritics | keep | trung bình |
| g21 | no_diacritics | **reword** (hoặc add de-qa-1017) | trung bình |
| g22 | no_diacritics | **reword** | trung bình-cao |
| g23 | no_diacritics | keep | cao |
| g24 | no_diacritics | **reword** | trung bình |
| h01 | vi | keep | cao |
| h02 | vi | keep | cao |
| h03 | vi | keep | cao |
| h04 | vi | keep | cao |
| h05 | vi | **add de-qa-1182** | trung bình-thấp |
| h06 | vi | keep | cao |
| h07 | vi | keep | cao |
| h08 | vi | keep | cao |
| h09 | vi | keep | cao |
| h10 | vi | keep | cao |
| h11 | vi | keep | cao |
| h12 | vi | keep | cao |
| h13 | vi | keep | cao |
| h14 | vi | keep | cao |
| h15 | vi | keep | cao |
| h16 | vi | keep | cao |
| h17 | vi | keep | cao |
| h18 | vi | keep | cao |
| h19 | vi | keep | cao |
| h20 | vi | keep (xem ghi chú) | trung bình |
| h21 | vi | keep | cao |
| h22 | vi | keep | cao |
| h23 | vi | keep | cao |
| h24 | vi | keep | cao |
| h25 | vi | keep | cao |
| h26 | vi | keep | cao |
| h27 | vi | keep | cao |
| h28 | vi | **add de-qa-1013** | trung bình |
| h29 | vi | keep | cao |
| h30 | vi | keep | cao |
| h31 | vi | keep | cao |
| h32 | vi | keep | cao |

Tổng: 56 query, **keep 50, reword 4 (g02, g21, g22, g24), add 2 (h05, h28), remove 0**. Mọi nhãn hiện có đều đúng (không có id nào trả lời sai query). Mọi `filters.category` khớp category của pair được gán (g01/g08 Backend, g06/g12/g17 AI, g10 DevOps, g11 Frontend). Hai set không trùng target nào.

## 2. Query cần thay đổi

### g02 (vi): reword, cao
- Query: "Lỗi tràn bộ nhớ heap sau vài ngày chạy, cách tìm nguyên nhân rò rỉ" → `de-qa-1104`.
- Nhãn đúng: 1104 Q "Một service Java chạy vài ngày thì ném OutOfMemoryError: Java heap space…"; A "Phân biệt bằng xu hướng live set: theo dõi heap đã dùng sau GC… Mức đáy tăng dần theo thời gian là dấu hiệu leak".
- Vấn đề 1 (group rule): "heap" là thuật ngữ Anh, nhóm `vi` yêu cầu tiếng Việt thuần.
- Vấn đề 2 (thiếu nhãn): query không nói ngôn ngữ, nên `de-qa-1016` (Node.js, OOMKill vài ngày một lần; A "heapUsed tăng dần → rò rỉ trên heap JS: …") trả lời được tương đương.
- Đề xuất A (ưu tiên): reword cho khớp riêng 1104, ví dụ "Dịch vụ Java báo tràn bộ nhớ sau vài ngày chạy, khởi động lại thì ổn một thời gian, làm sao biết là rò rỉ hay cấp thiếu bộ nhớ". Đề xuất B: giữ query, add `de-qa-1016` (vẫn vi phạm group rule).

### g21 (no_diacritics): reword, trung bình
- Query: "event loop bi chan lam latency p99 tang du cpu thap" → `de-qa-1000`.
- Nhãn chỉ khớp một phần: 1000 Q "CPU thấp nhưng p99 latency tăng vọt… libuv threadpool"; A nói ngược tiền đề của query: "Triệu chứng gợi ý libuv threadpool bị bão hòa chứ không phải event loop bị block".
- Pair trả lời đúng ý "event loop bị chặn" là `de-qa-1017` (A "perf_hooks.monitorEventLoopDelay() tạo histogram độ trễ event loop…"), nhưng 1017 có triệu chứng "một core CPU chạm 100%", trái với "cpu thap". `de-qa-1052` (asyncio, callback chạy >100ms) cũng là "event loop bị chặn" nhưng là Python.
- Đề xuất A (ưu tiên): reword theo triệu chứng của 1000, ví dụ "node p99 tang vot du cpu thap, doc file va pbkdf2 cham cung luc, cache trong ram van nhanh". Đề xuất B: giữ query, add `de-qa-1017`.

### g22 (no_diacritics): reword, trung bình-cao
- Query: "thiet ke access token va refresh token co the thu hoi phien" → `de-qa-1020`, `de-qa-1112`.
- Cả hai nhãn đúng: 1020 A "Refresh token rotation: mỗi lần client đổi refresh token… server cấp kèm refresh token mới và vô hiệu hóa token cũ"; 1112 Q "logout hoặc khóa tài khoản phải có hiệu lực nhanh… thiết kế access/refresh token". Không thấy pair nào khác tốt hơn.
- Vấn đề: query gần như là câu hỏi của 1020 bỏ dấu ("Thiết kế cơ chế access token và refresh token… sao cho có thể thu hồi phiên"). Vi phạm rule rag-design mục 9 "không dùng nguyên văn câu hỏi trong `interview_qa`", làm recall nhóm no_diacritics bị thổi phồng.
- Đề xuất: reword, ví dụ "dang xuat xong token cu van goi duoc api, lam sao cho logout co hieu luc ngay". Giữ 2 nhãn.

### g24 (no_diacritics): reword, trung bình
- Query: "test e2e playwright fail ngau nhien tren ci" → `de-qa-1256`.
- Nhãn đúng: 1256 A "Retry không sửa được gì… `waitForTimeout` là ngủ cố định… Bật trace cho lần retry đầu trên CI".
- Vấn đề: gần nguyên văn Q của 1256 ("Bộ test E2E Playwright của team fail ngẫu nhiên trên CI") bỏ dấu.
- Đề xuất: reword, ví dụ "test giao dien tu dong lan pass lan fail tren may build, them sleep va retry cung khong het". Pair gần: `de-qa-1018` (Jest flaky trên CI) là unit test backend, không thêm.

### h05 (vi): add de-qa-1182, trung bình-thấp
- Query: "Chọn ngưỡng xác suất cho mô hình phân loại hai lớp như thế nào" → `de-qa-1181`.
- Nhãn đúng: 1181 A "Ngưỡng mặc định 0,5 không gắn với nghiệp vụ… chọn ngưỡng tối đa hóa utility trên validation".
- Thiếu nhãn: `de-qa-1182` cũng trả lời việc chọn ngưỡng ("Báo cáo precision và recall tại ngưỡng vận hành…", "Chọn điểm vận hành theo năng lực"), chỉ là trong bối cảnh lệch lớp.
- Đề xuất: add 1182 nếu DE chấp nhận nhãn "trả lời được một phần". Nếu muốn nhãn chặt (chỉ pair tốt nhất), giữ nguyên.

### h28 (vi): add de-qa-1013, trung bình
- Query: "Thử phiên bản mới cho mười phần trăm người dùng nhưng phiên bản đó đổi tên một cột trong cơ sở dữ liệu dùng chung" → `de-qa-1216`.
- Nhãn đúng: 1216 A "canary… và blue-green… đều giả định hai phiên bản chạy cùng lúc… Giải pháp: expand/contract".
- Thiếu nhãn: `de-qa-1013` A "Đổi tên cột: không rename trực tiếp khi code cũ còn chạy. Thêm cột mới → code ghi cả hai → backfill → code đọc cột mới → ngừng ghi cột cũ → xóa cột cũ" trả lời đúng phần "đổi tên cột khi bản cũ còn chạy".
- Đề xuất: add 1013 (1216 vẫn là pair tốt nhất).

## 3. Ghi chú cho các query keep

- **g05**: 1111 (trừ tồn kho, lost update) và 1012 (đặt vé, oversell) đều đúng. `de-qa-1057` (Django trừ điểm ví, đọc-sửa-ghi) và `de-qa-1101` (bộ đếm `counts.put(k, counts.get(k) + 1)` mất cập nhật) cùng dạng lỗi. Gán 1012 mà không gán 1057 hơi thiếu nhất quán, nhưng query nói "tồn kho" nên giữ nguyên là hợp lý. DE chọn: giữ, hoặc bỏ 1012 để nhãn chặt hơn.
- **g20**: "it gia tri khac nhau" chép cụm "rất ít giá trị khác nhau" trong Q của 1100; cùng target với g01. Chấp nhận được (không phải nguyên câu).
- **h20**: cụm "trả lời trôi chảy nhưng sai… không có thông tin" chép từ Q của 1176 (bản gốc có "knowledge base", query đã Việt hóa). Có thể reword nhẹ, ưu tiên thấp.
- **h15**: `de-qa-1067` (pytest "mất 25 phút vì mỗi test tạo lại schema") trùng con số "hai mươi lăm phút", là distractor; 1118 ("ApplicationContext bị khởi tạo lại hàng chục lần") vẫn đúng.
- **h09**: "trong bảng" mơ hồ (bảng băm hay bảng DB); 1101 vẫn là pair khớp nhất ("check-then-act… containsKey = false rồi cùng gọi loadExpensive"). Có thể ghi rõ "bảng băm".
- **Tên riêng trong nhóm vi**: g01 "Java", h02 "Node", h03 "Django". Đây là tên sản phẩm, không phải thuật ngữ; tôi coi là hợp lệ, DE xác nhận.
- Pair gần nhưng không đủ để thêm: g03 ↔ 1006/1050 (job chạy lại phía worker, không phải client retry); g06 ↔ 1184 (rò rỉ do chia dữ liệu theo nhóm/thời gian); g09 ↔ 1052 (asyncio chung, không phải FastAPI); g13 ↔ 1006 (BullMQ); g15 ↔ 1056/1058 (N+1 trên SQLAlchemy/Django); g19 ↔ 1180; g23 ↔ 1196/1150; h07 ↔ 1261; h18 ↔ 1162; h22 ↔ 1187.

## 4. Bằng chứng cho các nhãn keep (Q/A của pair khớp query)

| Query | qa_id | Câu khớp trong pair |
|---|---|---|
| g01 | 1100 | A "hashCode() phân bố kém nên rất nhiều key rơi vào cùng bucket, HashMap thoái hóa từ O(1)…" |
| g03 | 1120 | Q "mobile client tự retry khi timeout nên thỉnh thoảng khách bị trừ tiền hai lần" |
| g04 | 1109 | A "các dòng bị OFFSET bỏ qua vẫn phải được tính trong server; trang 5000 phải đọc rồi vứt 100000 dòng" |
| g05 | 1111, 1012 | 1111 A "Hai transaction cùng đọc stock = 5… (lost update)"; 1012 A "lỗi check-then-act (lost update)… UPDATE … WHERE … remaining > 0" |
| g06 | 1183 | Q "điểm cross-validation cao bất thường nhưng sụp khi lên production… data leakage" |
| g07 | 1110 | A "this.writeAudit() là self-invocation… nên REQUIRES_NEW bị phớt lờ hoàn toàn" |
| g08 | 1001 | A "Promise.all chỉ chờ kết quả, không giới hạn concurrency" |
| g09 | 1053 | A "async def được gọi trực tiếp trên event loop. Mọi lời gọi blocking bên trong… chặn cả event loop" |
| g10 | 1204 | A "`preStop` sleep ngắn (vài giây) để việc gỡ endpoint kịp lan truyền trước khi app nhận SIGTERM" |
| g11 | 1252 | A "Thời gian, múi giờ, locale: `new Date()`, `toLocaleString()` (server chạy UTC…)" |
| g12 | 1163 | A "Với index xấp xỉ, điều kiện lọc áp dụng sau khi quét index" |
| g13 | 1050 | A "acks_late=True… at-least-once: task có thể chạy nhiều lần" |
| g14 | 1102 | A "JMM chỉ bảo đảm thread B thấy kết quả ghi của thread A khi phép ghi happens-before phép đọc" |
| g15 | 1106 | A "join với collection nhân mỗi đơn thành nhiều dòng, nên LIMIT/OFFSET ở SQL không còn đếm theo đơn" |
| g16 | 1008 | Q "rate limiter phân tán bằng Redis cho API Node.js chạy nhiều instance" |
| g17 | 1167 | A "chỉ adapter có gradient và optimizer state… bộ nhớ GPU giảm 3 lần" |
| g18 | 1213 | A "`user_id` và URL đầy đủ… là các tập giá trị không giới hạn… Prometheus OOM" |
| g19 | 1165 | A "Position bias… Verbosity bias… Self-enhancement bias" |
| g20 | 1100 | như g01 |
| g23 | 1195 | A "một 'ứng viên' gửi email có chữ ẩn… Agent đọc email, coi đó là chỉ dẫn" |
| h01 | 1009 | A "Race 1 (lần đọc chậm ghi đè dữ liệu mới)… Cache giữ v1 tới hết TTL dù DB đã là v2" |
| h02 | 1016 | Q "Node.js chạy trong container bị OOMKill vài ngày một lần"; A "heapUsed tăng dần → rò rỉ trên heap JS" |
| h03 | 1057 | A "hai request cùng đọc 100 điểm, cùng thấy đủ, cùng save… số dư sai hoặc âm" |
| h04 | 1069 | A "OWASP khuyến nghị: Argon2id…"; "Dùng hmac.compare_digest cho token" |
| h06 | 1212 | Q "hơn trăm alert mỗi tuần… phần lớn không cần hành động gì… alerting dựa trên SLO" |
| h07 | 1260 | Q "Tab ra được nội dung phía sau, screen reader vẫn đọc trang nền" |
| h08 | 1206 | A "Plan chậm vì phải refresh toàn bộ resource"; "Tách state" |
| h09 | 1101 | A "Hai thread có thể cùng thấy containsKey = false rồi cùng gọi loadExpensive" |
| h10 | 1103 | A "các method *Async không truyền Executor chạy trên ForkJoinPool.commonPool()" |
| h11 | 1105 | Q "pause 150–300 ms ở các mixed collection… SLO p99 latency 50 ms" |
| h12 | 1107 | A "Hibernate không tự evict entity… Heap tăng tuyến tính… dẫn tới OOM" |
| h13 | 1113 | A "Tách hai chain: securityMatcher("/api/**")… bỏ CSRF chỉ trong chain này" |
| h14 | 1116 | A "Từ Spring Boot 2.6, circular reference bị cấm mặc định… BeanCurrentlyInCreationException" |
| h15 | 1118 | Q "chạy 25 phút; log cho thấy ApplicationContext bị khởi tạo lại hàng chục lần" |
| h16 | 1002 | A "write() trả về false… Code bỏ qua giá trị trả về… thiếu backpressure" |
| h17 | 1156 | Q "GPU vẫn dư compute nhưng throughput không tăng"; A về KV cache |
| h18 | 1161 | Q "input token từ system prompt dài… prompt caching" |
| h19 | 1171 | Q "So sánh RLHF (reward model kết hợp PPO) với DPO" |
| h20 | 1176 | A "Cho phép model nói 'không đủ thông tin'" |
| h21 | 1182 | A "Precision thì phụ thuộc mạnh vào π… Khoảng 96% cảnh báo là sai" |
| h22 | 1188 | A "Semantic VAD… đoán người dùng đã nói xong ý chưa"; "Barge-in" |
| h23 | 1200 | A "Port publish được DNAT trong bảng `nat`… trước khi đi qua các chain của ufw" |
| h24 | 1203 | Q "connection refused, hoặc nhận response từ phiên bản cũ… mọi Pod đều Running" |
| h25 | 1207 | A "Đổi địa chỉ resource (đổi tên block…)… thêm `moved` block" |
| h26 | 1210 | A "app chỉ thấy IP của proxy liền trước… Phần tử đầu tiên… có thể giả mạo" |
| h27 | 1214 | A "Thu hồi và rotate ngay lập tức… Điều tra phạm vi bằng audit log (CloudTrail)" |
| h29 | 1250 | A "microtask không nhường main thread" |
| h30 | 1251 | A "'last response wins'… Fetch API không có tùy chọn timeout" |
| h31 | 1255 | A "Quên `cancelQueries`, nên refetch nền… ghi đè giá trị optimistic" |
| h32 | 1261 | A "SPA thay DOM bằng JavaScript nên không có page load để AT nhận biết" |

## 5. Vấn đề chung (metadata)

- `rag_golden.json.status` còn ghi "Nhãn trỏ vào qa_id của bộ canonical DE (PR #8, chưa merge)". Bộ `hard-*.json` đã có trên main và mọi id đều tồn tại, nên dòng này đã cũ.
- rag-design mục 9 yêu cầu "Ghi `source` của từng query", nhưng không query nào có trường `source`.
- `rag_golden_holdout.json.groups` chỉ định nghĩa `vi`. Quy tắc này ("không thuật ngữ Anh") chặt hơn quy tắc `vi` của golden chính ("diễn đạt lại"), nên g02 đạt quy tắc của golden chính nhưng không đạt quy tắc của holdout.
- Group `vi_to_en` vẫn trống (chưa có textbook), đúng như status ghi.

## Câu hỏi chưa giải quyết

1. Corpus khi đo là `de_interview_qa` trên ai_db dùng chung, khoảng 9.006 bản ghi (rag-design mục 7), lớn hơn nhiều so với 144 pair đã kiểm ở đây. Có thể còn pair ngoài 144 pair này cũng trả lời được query nhưng không có nhãn, và báo cáo này không kiểm được chúng. DE có muốn kiểm thêm trên corpus đầy đủ không?
2. Chính sách nhãn: chỉ gán pair tốt nhất, hay gán mọi pair "trả lời được" (ảnh hưởng tới h05, h28, g05)? Với metric hit@k, gán rộng làm recall tăng.
3. Tên sản phẩm (Java, Node, Django) trong nhóm `vi` có được chấp nhận không?
