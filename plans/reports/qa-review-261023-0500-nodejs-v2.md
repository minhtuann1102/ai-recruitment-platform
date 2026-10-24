# Báo cáo duyệt cặp Q&A — nodejs (2026-10-23 05:03)

> Báo cáo do Claude tạo bằng skill `interview-qa-review`: **chỉ là gợi ý kèm bằng chứng**. Các cặp này cũng do Claude viết, nên người reviewer (cùng họ model) có thể chung điểm mù. Quyết định và `reviewed_by` thuộc về người duyệt.

**22/22 cặp đã duyệt** · Đạt 16 · Cần sửa 6 · Bỏ 0 · tin cậy cao 21 / vừa 1 / thấp 0

**Phân loại cho người duyệt:** Phải đọc 6 · Chỉ hình thức 1 (câu hỏi quá rộng, quá dài: nội dung đúng) · Có thể chấp nhận 15

**Kiểm tra trích dẫn nguyên văn:** khớp 115 · không khớp 5 · không kiểm được từ máy này 15

## Cặp mồi (kiểm tra người reviewer)

| qa_id | Lỗi cài sẵn | Gợi ý nhận được | Bắt được? |
|---|---|---|---|
| de-qa-1022 | Nói worker dùng chung V8 isolate/heap và postMessage truyền tham chiếu không copy (sai: mỗi worker có isolate riêng, postMessage dùng struc… | Cần sửa: [critical] Đáp án khẳng định worker dùng chung isolate/heap và postMessage chỉ truyền tham chiếu. Thực tế mỗi Worker là một JS engine insta… | có |

## Tổng hợp

| qa_id | Topic | Gợi ý | Tin cậy | Nhóm | Vấn đề chính | Token | Golden |
|---|---|---|---|---|---|---|---|
| de-qa-1000 | Event loop của Node.js | Đạt | high | Có thể chấp nhận | [minor] 639 token; phần bị cắt ở 600 token chỉ là ý chia nhỏ tác vụ và rate limit endpoint login, các ý bắt buộc (cơ chế, chẩn đoán, UV_THR… | 639 | 1 |
| de-qa-1001 | Bất đồng bộ, Promise và async/await | Đạt | high | Có thể chấp nhận | [minor] 655 token; bị cắt mất ý checkpoint và đoạn đánh đổi chọn N. Các ý bắt buộc (không giới hạn concurrency, không hủy, giới hạn N, Abor… | 655 | 1 |
| de-qa-1002 | Stream và Buffer | Đạt | high | Có thể chấp nhận | [minor] 639 token; phần bị cắt chỉ là ý timeout query và giới hạn số export đồng thời, các ý bắt buộc vẫn còn. | 639 |  |
| de-qa-1003 | Stream và Buffer | Cần sửa | high | Phải đọc | [minor] Rubric v2: 1 ý độc lập, ~5 phút cho các ý bắt buộc (các bẫy liệt kê là các mặt của một câu: dùng Buffer an toàn); v1 đếm 4 ý. Còn l… | 608 |  |
| de-qa-1004 | Worker threads và cluster | Đạt | high | Có thể chấp nhận | [minor] Rubric v2: 1 ý độc lập, ~5 phút cho các ý bắt buộc (pool, cách truyền dữ liệu, lỗi và giới hạn tài nguyên là các mặt của một thiết … | 656 |  |
| de-qa-1005 | Worker threads và cluster | Cần sửa | high | Phải đọc | [minor] Rubric v2: 1 ý độc lập, ~5 phút cho các ý bắt buộc (một quyết định (cluster hay 1 process mỗi pod) với các mặt phân phối kết nối, s… | 667 |  |
| de-qa-1006 | Hàng đợi tác vụ (BullMQ, RabbitMQ) | Đạt | high | Phải đọc | [minor] 667 token; bị cắt ý noeviction/AOF và đoạn đánh đổi exactly-once, các ý bắt buộc (cơ chế stalled, idempotency, jobId) vẫn còn. | 667 |  |
| de-qa-1007 | Hàng đợi tác vụ (BullMQ, RabbitMQ) | Đạt | high | Có thể chấp nhận | [minor] Rubric v2: 1 ý độc lập, ~5 phút cho các ý bắt buộc (retry, rate limit, dead letter và giám sát là các mặt của một thiết kế xử lý lỗ… | 666 |  |
| de-qa-1008 | Cache với Redis | Cần sửa | high | Phải đọc | [minor] Rubric v2: 2 ý độc lập, ~5 phút cho các ý bắt buộc (so sánh thuật toán và tính nguyên tử là một thiết kế; hành vi khi Redis lỗi là … | 624 | 1 |
| de-qa-1009 | Cache với Redis | Đạt | medium | Có thể chấp nhận | [minor] 681 token; bị cắt ý LRU xấp xỉ và đoạn theo dõi metrics, các ý bắt buộc (2 race, giảm thiểu, 3 nhóm policy) vẫn còn. | 681 |  |
| de-qa-1010 | NestJS module và Dependency Injection | Đạt | high | Có thể chấp nhận | [minor] 679 token; bị cắt nửa cuối ý durable provider và đoạn kết luận, các ý bắt buộc vẫn còn. | 679 |  |
| de-qa-1011 | NestJS module và Dependency Injection | Đạt | high | Có thể chấp nhận | [minor] Rubric v2: 1 ý độc lập, ~4 phút cho các ý bắt buộc (đặt việc vào đúng lớp và thứ tự lifecycle là cùng một mạch); v1 đếm 3 ý. Còn lạ… | 696 |  |
| de-qa-1012 | ORM, transaction và migration | Cần sửa | high | Phải đọc | [major] 711 token; bị cắt câu 'Sửa: transaction ngắn, side effect sau commit, statement/lock timeout, tính pool theo max_connections' — đây… | 711 | 1 |
| de-qa-1013 | ORM, transaction và migration | Đạt | high | Có thể chấp nhận | [minor] 684 token; bị cắt nửa cuối bước đổi tên cột và đoạn nguyên tắc; các bước 1-4 còn đủ. | 684 |  |
| de-qa-1014 | TypeScript cho backend | Đạt | high | Có thể chấp nhận | [minor] 664 token; bị cắt nửa cuối đoạn đánh đổi (contract nội bộ), các ý bắt buộc còn đủ. | 664 |  |
| de-qa-1015 | TypeScript cho backend | Đạt | high | Có thể chấp nhận | [minor] Rubric v2: 1 ý độc lập, ~5 phút cho các ý bắt buộc (một thiết kế type kèm khi nào type quá phức tạp (trade-off của chính thiết kế đ… | 650 |  |
| de-qa-1016 | Profiling và rò rỉ bộ nhớ | Đạt | high | Có thể chấp nhận | [minor] 671 token; bị cắt nửa cuối lưu ý production (--max-old-space-size thấp hơn limit, cảnh báo theo xu hướng); các ý bắt buộc còn đủ. | 671 |  |
| de-qa-1017 | Profiling và rò rỉ bộ nhớ | Đạt | high | Có thể chấp nhận | [minor] Rubric v2: 1 ý độc lập, ~4 phút cho các ý bắt buộc (đo event loop lag, profile CPU và nguyên nhân hay gặp là một bài chẩn đoán); v1… | 640 |  |
| de-qa-1018 | Kiểm thử với Jest | Đạt | high | Có thể chấp nhận | [minor] 673 token; bị cắt 2 gạch cuối (randomize/seed, fake timers), các nguyên nhân và cách sửa chính còn đủ. | 673 |  |
| de-qa-1019 | Kiểm thử với Jest | Đạt | high | Có thể chấp nhận | [minor] 688 token; bị cắt đoạn 'Thiết kế cho testability' (inject sleep/clock) và một phần ý 5; các ý bắt buộc (nguyên nhân, API async, khô… | 688 |  |
| de-qa-1020 | Xác thực JWT và phân quyền | Cần sửa | high | Chỉ hình thức | [major] Phần cắt ở 600 token rơi vào mục 'Lưu ở client': mất ý chống CSRF cho endpoint refresh và ý giữ access token trong bộ nhớ thay vì l… | 687 | 1 |
| de-qa-1021 | Xác thực JWT và phân quyền | Cần sửa | high | Phải đọc | [minor] Rubric v2: 1 ý độc lập, ~5 phút cho các ý bắt buộc (các lỗ hổng liệt kê là checklist của một bài review jwt.verify); v1 đếm 5 ý. Cò… | 658 |  |

## Ảnh hưởng nếu sửa hoặc bỏ

- de-qa-1003: bỏ thì topic còn < 2 cặp hard (SC-001)
- de-qa-1005: bỏ thì topic còn < 2 cặp hard (SC-001)
- de-qa-1008: là nhãn golden set g16 (báo Thắng nếu đổi nội dung)
- de-qa-1012: bỏ thì topic còn < 2 cặp hard (SC-001), là nhãn golden set g05 (báo Thắng nếu đổi nội dung)
- de-qa-1020: bỏ thì topic còn < 2 cặp hard (SC-001), là nhãn golden set g22 (báo Thắng nếu đổi nội dung)
- de-qa-1021: bỏ thì topic còn < 2 cặp hard (SC-001)
- 22/22 cặp dài hơn 600 token: snippet của Planner sẽ bị cắt (de-qa-1000, de-qa-1001, de-qa-1002, de-qa-1003, de-qa-1004, de-qa-1005, de-qa-1006, de-qa-1007, de-qa-1008, de-qa-1009, de-qa-1010, de-qa-1011, de-qa-1012, de-qa-1013, de-qa-1014, de-qa-1015, de-qa-1016, de-qa-1017, de-qa-1018, de-qa-1019, de-qa-1020, de-qa-1021).

## Việc cho người duyệt

- **Phải đọc** (6): de-qa-1003, de-qa-1005, de-qa-1006, de-qa-1008, de-qa-1012, de-qa-1021. Sai kiến thức, lỗi thời, chưa kiểm chứng được, tin cậy thấp, hoặc trích dẫn không khớp nguyên văn. Đọc phần kiểm chứng; chỗ Claude bác bỏ chính nguồn mà cặp trích thì Claude cũng có thể sai.
- **Chỉ hình thức** (1): de-qa-1020. Nội dung đúng; vấn đề là câu hỏi quá rộng hoặc quá dài. Sửa hay giữ là lựa chọn của bạn.
- **Có thể chấp nhận** (15): de-qa-1000, de-qa-1001, de-qa-1002, de-qa-1004, de-qa-1007, de-qa-1009, de-qa-1010, de-qa-1011, de-qa-1013, de-qa-1014, de-qa-1015, de-qa-1016, de-qa-1017, de-qa-1018, de-qa-1019. Mọi ý đã có trích dẫn; chấp nhận dựa trên bằng chứng là quyết định của bạn.
- Có nhãn golden set (5): de-qa-1000, de-qa-1001, de-qa-1008, de-qa-1012, de-qa-1020. Sửa câu hỏi thì giữ các thuật ngữ chính.

## Chi tiết từng cặp

### de-qa-1000 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Event loop của Node.js (`node.core.event-loop`) · ~639 token · hard của topic: 2 · golden: g21

**Câu hỏi:** Một service Node.js có CPU thấp nhưng p99 latency tăng vọt khi tải cao: các request đọc file, gọi crypto.pbkdf2 và kết nối tới host theo tên miền đều chậm cùng lúc, trong khi request chỉ đọc cache trong bộ nhớ vẫn nhanh. Bạn chẩn đoán nguyên nhân liên quan tới libuv threadpool thế nào và khắc phục ra sao?

**Kết luận:** Đúng và bám tài liệu Node/libuv: phân biệt threadpool bão hòa với event loop bị block, liệt kê đúng API dùng threadpool và cách khắc phục. Chỉ thiếu sót nhỏ: phần cuối (rate limit) bị cắt ở 600 token; pair có golden label g21 nên giữ nguyên wording.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | 639 token; phần bị cắt ở 600 token chỉ là ý chia nhỏ tác vụ và rate limit endpoint login, các ý bắt buộc (cơ chế, chẩn đoán, UV_THREADPOOL_SIZE, DNS) vẫn còn. | Rút gọn câu về dns.resolve và bỏ ý rate limit để dưới 600 token. |
| minor | factual | Câu 'gán process.env trong code không đảm bảo có hiệu lực' đúng hướng nhưng libuv nói pool được cấp phát khi lần đầu cần dùng, nên gán sớm ở dòng đầu entrypoint thường vẫn có tác dụng. | Giữ khuyến nghị đặt qua biến môi trường, nói rõ 'gán trong code chỉ có tác dụng nếu chạy trước mọi thao tác dùng threadpool'. |

**Kiểm chứng:**
- `supported` fs (trừ bản sync và FSWatcher) chạy trên libuv threadpool
  > All file system APIs except `fs.FSWatcher()` and those that are explicitly synchronous use libuv's threadpool.  
  > — https://nodejs.org/en/learn/asynchronous-work/dont-block-the-event-loop
- `supported` crypto.pbkdf2/scrypt/randomBytes/generateKeyPair và zlib async dùng threadpool
  > `crypto.pbkdf2()`, `crypto.scrypt()`, `crypto.randomBytes()`, `crypto.randomFill()`, `crypto.generateKeyPair()`.  
  > — https://nodejs.org/en/learn/asynchronous-work/dont-block-the-event-loop
  _Cùng trang: "All zlib APIs except those that are explicitly synchronous use libuv's threadpool."_
- `supported` dns.lookup() gọi getaddrinfo đồng bộ trên threadpool
  > it is implemented as a synchronous call to getaddrinfo(3) that runs on libuv's threadpool.  
  > — https://raw.githubusercontent.com/nodejs/node/main/doc/api/dns.md
  _Mục Implementation considerations của dns.md_
- `supported` dns.resolve*() luôn query qua mạng, không dùng threadpool, không dùng /etc/hosts
  > This network communication is always done asynchronously and does not use libuv's threadpool.  
  > — https://raw.githubusercontent.com/nodejs/node/main/doc/api/dns.md
  _nodejs.org/api/dns.html: "These functions do not use the same set of configuration files used by dns.lookup() (e.g. /etc/hosts)."_
- `supported` Threadpool mặc định 4 thread, đổi bằng UV_THREADPOOL_SIZE lúc khởi động
  > it can be changed at startup time by setting the UV_THREADPOOL_SIZE environment variable to any value  
  > — https://docs.libuv.org/en/v1.x/threadpool.html
  _Cùng câu bắt đầu bằng "Its default size is 4". Mục UV_THREADPOOL_SIZE trong cli.md không đọc được do trang bị cắt khi fetch._
- `supported` Tác vụ dài chiếm trọn một thread, làm pool nhỏ lại
  > each relatively long Task effectively decreases the size of the Worker Pool by one until it is completed  
  > — https://nodejs.org/en/learn/asynchronous-work/dont-block-the-event-loop
- `supported` monitorEventLoopDelay đo độ trễ event loop
  > Creates a histogram object that samples and reports the event loop delay over time. The delays will be reported in nanoseconds.  
  > — https://raw.githubusercontent.com/nodejs/node/main/doc/api/perf_hooks.md

**Độ khó:** hard thật · hợp level middle, senior — Phải suy luận từ triệu chứng (cache nhanh, fs/crypto/dns chậm) ra threadpool bão hòa, không phải câu hỏi định nghĩa.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Hai yêu cầu: chẩn đoán và khắc phục; có 4-5 ý chấm được.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu sự khác nhau giữa event loop và libuv threadpool, biết API 'async' nào thực ra chạy trên threadpool.
- Ý bắt buộc: Request đọc cache vẫn nhanh nên event loop không bị block; nghi threadpool bão hòa; fs, crypto.pbkdf2/scrypt, zlib async và dns.lookup chạy trên threadpool; socket mạng thì không; Threadpool mặc định 4 thread, đổi bằng UV_THREADPOOL_SIZE trước khi process khởi động; Đo event loop delay (monitorEventLoopDelay) để phân biệt hai trường hợp; Giảm tải: keep-alive/cache DNS hoặc dns.resolve, đưa việc CPU nặng sang worker_threads
- Dấu hiệu trả lời sai: Nói event loop bị block mà không giải thích vì sao request cache vẫn nhanh; Cho rằng mọi I/O mạng đều đi qua threadpool; Tăng UV_THREADPOOL_SIZE thật lớn như cách chữa duy nhất, bỏ qua chi phí
- Câu hỏi nối tiếp: Vì sao dns.resolve4() không dùng threadpool nhưng lại có thể trả kết quả khác dns.lookup() cho cùng hostname?

### de-qa-1001 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Bất đồng bộ, Promise và async/await (`node.core.async-promises`) · ~655 token · hard của topic: 2 · golden: g08

**Câu hỏi:** Một job đồng bộ dữ liệu viết `await Promise.all(ids.map((id) => callApi(id)))` với 50.000 id. Khi chạy thật thì cạn socket và bộ nhớ, API đối tác trả 429, và khi một lời gọi lỗi thì job báo lỗi nhưng các request khác vẫn tiếp tục chạy ngầm. Phân tích vấn đề và thiết kế lại phần điều phối bất đồng bộ.

**Kết luận:** Phân tích đúng: Promise.all không giới hạn concurrency, không hủy promise còn lại; unhandled rejection mặc định throw từ Node 15. Thiết kế lại hợp lý. Chỉ phần đánh đổi cuối bị cắt ở 600 token.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | 655 token; bị cắt mất ý checkpoint và đoạn đánh đổi chọn N. Các ý bắt buộc (không giới hạn concurrency, không hủy, giới hạn N, AbortController, allSettled) vẫn còn. | Gộp bước 4 và 5, rút gọn đoạn đánh đổi để dưới 600 token. |

**Kiểm chứng:**
- `supported` Promise.all reject ngay ở lỗi đầu tiên
  > It rejects when any of the input's promises rejects, with this first rejection reason.  
  > — https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise/all
- `supported` Promise.all reject không hủy các thao tác còn lại
  > Rejecting the returned promise does not cancel the remaining operations or unsubscribe the handlers attached to their promises.  
  > — https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise/all
- `supported` Mặc định --unhandled-rejections=throw; không có hook unhandledRejection thì ném như uncaught exception
  > In `throw` mode, if an `unhandledRejection` hook is not set, the `unhandledRejection` is raised as an uncaught exception.  
  > — https://nodejs.org/en/blog/release/v15.0.0
  _Mặc định đổi từ warn sang throw kể từ Node 15. Mục --unhandled-rejections trong cli.md không đọc được do trang bị cắt khi fetch._
- `supported` AbortSignal.timeout(ms) tạo signal tự abort sau ms
  > Returns a new `AbortSignal` which will be aborted in `delay` milliseconds.  
  > — https://nodejs.org/api/globals.html
- `supported` AbortSignal.any gộp nhiều signal
  > Returns a new `AbortSignal` which will be aborted if any of the provided signals are aborted.  
  > — https://nodejs.org/api/globals.html
- `supported` Promise reject mà không có handler sẽ phát sự kiện unhandledRejection
  > The `'unhandledRejection'` event is emitted whenever a `Promise` is rejected and no error handler is attached to the promise within a turn of the event loop.  
  > — https://nodejs.org/api/process.html

**Độ khó:** hard thật · hợp level middle, senior — Cần hiểu ngữ nghĩa Promise (eager, không hủy) và thiết kế điều phối có giới hạn; junior thường chỉ biết Promise.all.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Phân tích + thiết kế lại; 5 ý chấm được.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu Promise chạy ngay khi tạo, Promise.all không giới hạn và không hủy, và cách điều phối concurrency có hủy.
- Ý bắt buộc: map tạo 50.000 promise cùng lúc; Promise.all chỉ chờ, không giới hạn concurrency; Promise.all fail-fast nhưng không hủy các request còn lại; Giới hạn N worker/p-limit theo quota đối tác, xử lý 429 bằng backoff và Retry-After; Hủy bằng AbortController chung, timeout từng request bằng AbortSignal.timeout + AbortSignal.any; Dùng allSettled theo batch nếu muốn giữ phần thành công
- Dấu hiệu trả lời sai: Nghĩ Promise.all chạy tuần tự hoặc tự giới hạn số request; Nghĩ khi Promise.all reject thì các request khác tự dừng; Dùng listener unhandledRejection để nuốt lỗi thay cho xử lý đúng chỗ
- Câu hỏi nối tiếp: Nếu đối tác giới hạn 100 request mỗi giây chứ không theo số request đồng thời, bạn đổi bộ điều phối thế nào?

### de-qa-1002 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Stream và Buffer (`node.core.streams-buffers`) · ~639 token · hard của topic: 2

**Câu hỏi:** Endpoint export CSV đọc hàng triệu dòng từ database rồi gọi `res.write()` cho từng dòng. Với client mạng chậm, RSS của process tăng lên hàng GB, và khi client hủy tải giữa chừng thì query vẫn chạy đến hết. Giải thích nguyên nhân và cách viết lại cho đúng.

**Kết luận:** Đúng và bám tài liệu stream của Node: thiếu backpressure khi bỏ qua giá trị trả về của write(), pipeline() tự destroy stream và nhận AbortSignal. Chỉ có vấn đề nhỏ về độ dài.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | 639 token; phần bị cắt chỉ là ý timeout query và giới hạn số export đồng thời, các ý bắt buộc vẫn còn. | Rút gọn đoạn highWaterMark để dưới 600 token. |

**Kiểm chứng:**
- `supported` write() trả false thì phải dừng tới khi có 'drain'
  > If `false` is returned, further attempts to write data to the stream should stop until the [`'drain'`][] event is emitted.  
  > — https://raw.githubusercontent.com/nodejs/node/main/doc/api/stream.md
- `supported` Thiếu backpressure làm bộ nhớ phình và GC quá tải
  > If a backpressure system was not present, the process would use up your system's memory, effectively slowing down other processes, and monopolizing a large part of your system until completion.  
  > — https://nodejs.org/en/learn/modules/backpressuring-in-streams
  _Cùng trang liệt kê "A very overworked garbage collector"._
- `supported` pipeline() chuyển tiếp lỗi và gọi destroy() trên các stream
  > `stream.pipeline()` will call `stream.destroy(err)` on all streams except:  
  > — https://raw.githubusercontent.com/nodejs/node/main/doc/api/stream.md
  _Cùng trang: "`stream.pipeline()` closes all the streams when an error is raised."_
- `supported` Truyền AbortSignal vào pipeline; async generator phải xử lý signal nếu không pipeline không kết thúc
  > Remember to handle the `signal` argument passed into the async generator.  
  > — https://raw.githubusercontent.com/nodejs/node/main/doc/api/stream.md
  _Câu tiếp theo kết thúc bằng "or the pipeline will never complete." Trang cũng ghi: "To use an `AbortSignal`, pass it inside an options object, as the last argument."_
- `supported` .pipe() không tự đóng đích khi nguồn lỗi
  > One important caveat is that if the `Readable` stream emits an error during processing, the `Writable` destination _is not closed_ automatically.  
  > — https://raw.githubusercontent.com/nodejs/node/main/doc/api/stream.md

**Độ khó:** hard thật · hợp level middle, senior — Cần hiểu backpressure và vòng đời stream khi client hủy; không phải câu định nghĩa.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Giải thích nguyên nhân + viết lại; 4-5 ý chấm được.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu backpressure của Writable stream và cách dọn tài nguyên khi đích đóng sớm.
- Ý bắt buộc: Bỏ qua write() trả false nên dữ liệu dồn vào buffer của res, RSS tăng; Client ngắt nhưng nguồn DB không bị destroy nên query chạy tiếp; Dùng stream nguồn + pipeline() (Transform/async generator) để có backpressure và tự destroy; Truyền AbortSignal, hủy khi request đóng sớm; Nếu tự ghi: write() false thì chờ 'drain'
- Dấu hiệu trả lời sai: Tăng highWaterMark hoặc RAM để 'chữa' việc RSS tăng; Dùng .pipe() trần mà không xử lý lỗi; Nghĩ client đóng kết nối thì query tự dừng
- Câu hỏi nối tiếp: Nếu driver DB không có stream mà chỉ có phân trang theo cursor, bạn tự tạo nguồn có backpressure thế nào?

### de-qa-1003 · Cần sửa · tin cậy high · Phải đọc

**Topic:** Stream và Buffer (`node.core.streams-buffers`) · ~608 token · hard của topic: 2

**Câu hỏi:** Khi xử lý dữ liệu nhị phân và văn bản UTF-8 dung lượng lớn bằng Buffer trong Node.js, có những cái bẫy nào về tính đúng đắn, bảo mật và bộ nhớ (ký tự bị cắt giữa hai chunk, subarray, allocUnsafe, Buffer pool)? Bạn tránh chúng thế nào?

**Kết luận:** Nội dung đúng và bám tài liệu Buffer/StringDecoder, nhưng câu hỏi liệt kê 4 bẫy riêng (chunk UTF-8, subarray, allocUnsafe, pool) nên quá rộng cho 3-5 phút và dễ thành câu hỏi kể tên. Nên thu hẹp câu hỏi. (Rubric v2: không còn tính là quá rộng; vẫn cần sửa vì claim chưa có nguồn.)

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | interview_fit | Rubric v2: 1 ý độc lập, ~5 phút cho các ý bắt buộc (các bẫy liệt kê là các mặt của một câu: dùng Buffer an toàn); v1 đếm 4 ý. Còn lại là gợi ý: Câu hỏi liệt kê 4 bẫy trong ngoặc cộng 'tránh thế nào', thực tế là 4-5 yêu cầu; ứng viên dễ trả lời kiểu kể tên và không đủ thời gian đi sâu. | Thu hẹp còn 2 bẫy có tình huống, ví dụ chỉ chunk UTF-8 bị cắt và rò bộ nhớ do giữ subarray/pool. |
| minor | length | 608 token; chỉ câu cuối của ý 5 bị cắt. | Bỏ đoạn 'Nguyên tắc' vì lặp lại các ý trên. |
| minor | factual | 'Buffer.from có thể cắt từ pool' đúng với Buffer.from(array/string) nhưng không với Buffer.from(arrayBuffer); ý --max-old-space-size chưa kiểm chứng được. | Ghi 'Buffer.from(string\|array)' thay cho 'Buffer.from'. |

**Kiểm chứng:**
- `supported` StringDecoder giữ byte dở dang của ký tự nhiều byte tới lần write()/end() tiếp
  > These are held in the buffer until the next call to `stringDecoder.write()` or until `stringDecoder.end()` is called.  
  > — https://raw.githubusercontent.com/nodejs/node/main/doc/api/string_decoder.md
- `supported` subarray tạo view trên cùng vùng nhớ, sửa view là sửa bản gốc
  > Also note that this is creating a new view on the existing buffer; changes to the new object's contents will impact the original object and vice versa.  
  > — https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/TypedArray/subarray
  _Buffer là Uint8Array; mục buf.subarray trong buffer.md không đọc được do trang bị cắt khi fetch._
- `supported` allocUnsafe không khởi tạo bộ nhớ, có thể chứa dữ liệu nhạy cảm
  > The contents of the newly created `Buffer` are unknown and _may contain sensitive data_.  
  > — https://raw.githubusercontent.com/nodejs/node/main/doc/api/buffer.md
- `supported` Buffer nhỏ có thể cắt từ pool chung; giữ lâu thì dùng allocUnsafeSlow rồi copy
  > it may be appropriate to create an un-pooled `Buffer` instance using `Buffer.allocUnsafeSlow()` and  
  > — https://raw.githubusercontent.com/nodejs/node/main/doc/api/buffer.md
  _Ngữ cảnh: "retain a small chunk of memory from a pool for an indeterminate amount of time"; pool dùng cho allocUnsafe, Buffer.from(array|string), concat._
- `supported` Buffer.alloc zero-fill, chậm hơn nhưng không lộ dữ liệu cũ
  > Calling [`Buffer.alloc()`][] can be measurably slower than the alternative  
  > — https://raw.githubusercontent.com/nodejs/node/main/doc/api/buffer.md
- `supported` Buffer tính vào external và arrayBuffers của process.memoryUsage()
  > This is also included in the `external` value.  
  > — https://raw.githubusercontent.com/nodejs/node/main/doc/api/process.md
  _Câu trước: arrayBuffers "including all Node.js Buffers"._
- `unverified` --max-old-space-size không giới hạn bộ nhớ Buffer
  _Không đọc được mục --max-old-space-size trong cli.md (trang bị cắt). Suy luận từ việc Buffer nằm ngoài V8 heap là hợp lý nhưng chưa có câu trích._

**Độ khó:** hard thật · hợp level middle, senior — Có chiều sâu (pool, view giữ sống vùng nhớ lớn), nhưng dạng liệt kê kéo nó về phía nhớ kiến thức.
**Dùng trong phỏng vấn:** ~5 phút, 1 ý hỏi, chấm được — Rubric v2: các bẫy liệt kê là các mặt của một câu: dùng Buffer an toàn. 4 bẫy được nêu sẵn trong câu hỏi, đáp án có 5 ý; quá rộng cho một câu.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu Buffer là vùng nhớ nhị phân ngoài V8 heap, các API chia sẻ vùng nhớ và giải mã UTF-8 qua nhiều chunk.
- Ý bắt buộc: toString() từng chunk làm vỡ ký tự nhiều byte; dùng setEncoding hoặc StringDecoder; subarray/slice không copy; giữ view nhỏ giữ sống vùng nhớ lớn; allocUnsafe không zero-fill, có thể lộ dữ liệu cũ; dùng alloc khi dữ liệu có thể ra ngoài; Buffer nhỏ có thể lấy từ pool chung; cần giữ lâu thì copy ra (allocUnsafeSlow); Rò Buffer thể hiện ở external/arrayBuffers và RSS, không ở heapUsed
- Dấu hiệu trả lời sai: Nghĩ slice() của Buffer tạo bản sao như Array.prototype.slice; Dùng allocUnsafe cho buffer gửi ra ngoài mà không ghi đè hết; Tìm rò Buffer bằng heapUsed
- Câu hỏi nối tiếp: Một service giữ hàng nghìn ID 16 byte cắt bằng subarray từ payload 1 MB; vì sao RSS cao và sửa thế nào?

**Đề xuất sửa:**
- Câu hỏi mới: Service đọc file văn bản UTF-8 lớn theo stream và giữ lại một số đoạn nhỏ trong cache. Bạn thấy chữ tiếng Việt thỉnh thoảng thành ký tự '�' và RSS tăng dần dù heapUsed ổn định. Giải thích hai hiện tượng và cách sửa.
- Đáp án: Giữ ý 1 (chunk UTF-8, StringDecoder/setEncoding) và ý 2 (subarray/pool giữ sống vùng nhớ, copy khi giữ lâu) cùng ý 5 (đo external/arrayBuffers); chuyển allocUnsafe thành ghi chú ngắn hoặc follow-up; bỏ đoạn 'Nguyên tắc'; ghi rõ Buffer.from(string|array) mới dùng pool.

### de-qa-1004 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Worker threads và cluster (`node.core.worker-cluster`) · ~656 token · hard của topic: 2

**Câu hỏi:** API Node.js phải tạo thumbnail hoặc parse file lớn (CPU-bound) cho mỗi upload. Bạn thiết kế việc offload sang worker_threads thế nào: tạo worker mỗi request hay dùng pool, truyền dữ liệu bằng structured clone, transferList hay SharedArrayBuffer, và xử lý lỗi, giới hạn tài nguyên ra sao?

**Kết luận:** Đạt theo rubric v2: câu hỏi có 1 ý độc lập, trả lời các ý bắt buộc trong khoảng 5 phút; các claim chính đều có trích dẫn. (v1 gợi ý Cần sửa vì đếm 4 ý.)

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | interview_fit | Rubric v2: 1 ý độc lập, ~5 phút cho các ý bắt buộc (pool, cách truyền dữ liệu, lỗi và giới hạn tài nguyên là các mặt của một thiết kế offload); v1 đếm 4 ý. Còn lại là gợi ý: Câu hỏi có 4 yêu cầu (pool/tạo mới, structured clone vs transferList vs SharedArrayBuffer, xử lý lỗi, giới hạn tài nguyên); k… | Giữ trọng tâm pool + cách truyền dữ liệu; chuyển xử lý lỗi/resourceLimits thành follow-up. |
| minor | length | 656 token; bị cắt đoạn đánh đổi cuối (lỗi native, tách service), các ý chính còn. | Rút gọn đoạn Lỗi và tài nguyên. |
| minor | topic | Trùng nhiều ý (pool, transferList, structured clone) với de-qa-1022 cùng topic. | Khi sửa de-qa-1022, để cặp đó tập trung vào việc parse vẫn chạy trên main thread và chi phí clone, tránh lặp. |

**Kiểm chứng:**
- `supported` Worker hữu ích cho việc CPU-bound, ít giúp cho I/O
  > They do not help much with I/O-intensive work.  
  > — https://raw.githubusercontent.com/nodejs/node/main/doc/api/worker_threads.md
  _Câu trước: "Workers (threads) are useful for performing CPU-intensive JavaScript operations."_
- `supported` Nên dùng pool; tự viết pool thì dùng AsyncResource
  > In practice, use a pool of Workers for these kinds of tasks.  
  > — https://raw.githubusercontent.com/nodejs/node/main/doc/api/worker_threads.md
  _Cùng trang: "When implementing a worker pool, use the AsyncResource API to inform" (diagnostic tools)._
- `supported` postMessage dùng structured clone; instance class mất prototype
  > instances of JavaScript classes will be cloned as plain JavaScript objects.  
  > — https://raw.githubusercontent.com/nodejs/node/main/doc/api/worker_threads.md
- `supported` transferList chuyển quyền sở hữu, bên gửi không dùng được nữa
  > After transferring, they are not usable on the sending side of the channel  
  > — https://raw.githubusercontent.com/nodejs/node/main/doc/api/worker_threads.md
- `supported` Buffer cắt từ pool nội bộ không transfer được, luôn bị clone
  > transferring them is not possible and they are always cloned,  
  > — https://raw.githubusercontent.com/nodejs/node/main/doc/api/worker_threads.md
- `supported` Uncaught exception trong worker phát 'error' và worker bị terminate
  > exception. In that case, the worker is terminated.  
  > — https://raw.githubusercontent.com/nodejs/node/main/doc/api/worker_threads.md
  _Câu đầy đủ bắt đầu: "The 'error' event is emitted if the worker thread throws an uncaught"._
- `supported` resourceLimits không tính ArrayBuffer
  > These limits only affect the JS engine, and no external data, including no `ArrayBuffer`s.  
  > — https://raw.githubusercontent.com/nodejs/node/main/doc/api/worker_threads.md

**Độ khó:** hard thật · hợp level middle, senior — Thiết kế offload có đánh đổi rõ (chi phí clone, pool, cô lập lỗi).
**Dùng trong phỏng vấn:** ~5 phút, 1 ý hỏi, chấm được — Rubric v2: pool, cách truyền dữ liệu, lỗi và giới hạn tài nguyên là các mặt của một thiết kế offload. Đáp án chấm được nhưng câu hỏi quá rộng.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Biết khi nào worker_threads giúp được và cách truyền dữ liệu giữa các thread với chi phí thấp.
- Ý bắt buộc: Worker chỉ giúp việc CPU-bound, không giúp I/O; Dùng pool cố định + hàng đợi có giới hạn thay vì tạo worker mỗi request; postMessage clone dữ liệu; transferList chuyển ArrayBuffer không copy; SharedArrayBuffer cần tự đồng bộ; Worker lỗi phát 'error' và bị terminate: pool phải thay worker và reject task; resourceLimits giới hạn heap nhưng không tính ArrayBuffer
- Dấu hiệu trả lời sai: Tạo Worker mới cho mỗi request; Cho rằng postMessage chỉ truyền tham chiếu; Đưa I/O (query DB) vào worker để 'chạy nhanh hơn'
- Câu hỏi nối tiếp: Worker trong pool bị treo vì input độc hại; bạn phát hiện và phục hồi thế nào mà không làm mất các task khác?

### de-qa-1005 · Cần sửa · tin cậy high · Phải đọc

**Topic:** Worker threads và cluster (`node.core.worker-cluster`) · ~667 token · hard của topic: 2

**Câu hỏi:** Service Node.js đang chạy bằng cluster module (hoặc PM2 cluster mode) trên VM, nay chuyển lên Kubernetes. Nên giữ nhiều worker process trong một container hay chạy một process mỗi pod? Phân tích cách cluster phân phối kết nối, vấn đề state trong bộ nhớ, WebSocket và graceful shutdown.

**Kết luận:** Các ý về cluster và graceful shutdown khớp tài liệu, nhưng câu hỏi gộp 5 yêu cầu (lựa chọn kiến trúc, phân phối kết nối, state, WebSocket, graceful shutdown) nên quá rộng. Ý 'process thấy số core của host' chưa kiểm chứng và phụ thuộc phiên bản. (Rubric v2: không còn tính là quá rộng; vẫn cần sửa vì claim chưa có nguồn.)

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | interview_fit | Rubric v2: 1 ý độc lập, ~5 phút cho các ý bắt buộc (một quyết định (cluster hay 1 process mỗi pod) với các mặt phân phối kết nối, state, WebSocket, shutdown); v1 đếm 5 ý. Còn lại là gợi ý: Câu hỏi có 5 yêu cầu: chọn cluster hay 1 process/pod, cách cluster phân phối kết nối, state, WebSocket, gracef… | Giữ câu hỏi chính (cluster trong pod hay 1 process/pod) kèm state; đưa WebSocket và graceful shutdown thành follow-up. |
| minor | factual | Ý 'số core process nhìn thấy là của host' chưa kiểm chứng và có thể sai với os.availableParallelism() trên bản Node mới. | Viết lại: 'os.cpus() trả về CPU của node chứ không phản ánh CPU limit của container, nên đừng dùng nó để chọn số worker'. |
| minor | length | 667 token; bị cắt nửa sau của graceful shutdown (chờ request, đóng pool, đóng WebSocket); bước đầu (SIGTERM, readiness, server.close) vẫn còn. | Rút gọn phần lý do chọn 1 process/pod. |

**Kiểm chứng:**
- `supported` Round-robin là mặc định trên mọi nền tảng trừ Windows **(quote không có nguyên văn trên trang nguồn)**
  > the default one on all platforms except Windows.  
  > — https://raw.githubusercontent.com/nodejs/node/main/doc/api/cluster.md
  _Ngữ cảnh: mô tả cách 1 (round-robin)._
- `supported` Cách worker tự accept về lý thuyết nhanh hơn nhưng phân phối rất lệch
  > The second approach should, in theory, give the best performance. In practice however, distribution tends to be very unbalanced due to operating system scheduler vagaries.  
  > — https://raw.githubusercontent.com/nodejs/node/main/doc/api/cluster.md
- `supported` Node không có routing theo session; không dựa vào object trong bộ nhớ cho session
  > Node.js does not provide routing logic.  
  > — https://raw.githubusercontent.com/nodejs/node/main/doc/api/cluster.md
  _Tài liệu khuyên không "rely too heavily on in-memory data objects for things like sessions and login."_
- `supported` K8s gửi SIGTERM rồi chờ grace period (mặc định 30s) trước khi KILL
  > The default `terminationGracePeriodSeconds` setting is 30 seconds.  
  > — https://raw.githubusercontent.com/kubernetes/website/main/content/en/docs/concepts/workloads/pods/pod-lifecycle.md
  _Cùng trang: "by first sending a TERM (aka. SIGTERM) signal, with a grace period timeout, to the main process in each container."_
- `supported` server.close() ngừng nhận kết nối mới, giữ kết nối đang có
  > Stops the server from accepting new connections and keeps existing connections.  
  > — https://raw.githubusercontent.com/nodejs/node/main/doc/api/net.md
- `unverified` Trong container, số core process nhìn thấy thường là của host chứ không phải CPU limit
  _Phụ thuộc API (os.cpus() vs os.availableParallelism()) và phiên bản libuv; không tìm được câu trích chính thức trong số lần fetch cho phép._

**Độ khó:** hard thật · hợp level middle, senior — Câu hỏi kiến trúc có đánh đổi giữa process model của Node và Kubernetes.
**Dùng trong phỏng vấn:** ~5 phút, 1 ý hỏi, chấm được — Rubric v2: một quyết định (cluster hay 1 process mỗi pod) với các mặt phân phối kết nối, state, WebSocket, shutdown. Nhiều ý chấm được nhưng quá rộng cho một câu.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu cluster module chia kết nối thế nào và vì sao trên Kubernetes thường chạy 1 process mỗi container.
- Ý bắt buộc: Primary chia kết nối round-robin (trừ Windows); worker là process riêng, không chia sẻ bộ nhớ; Trên k8s thường 1 process/container, scale bằng replica vì probe, restart, limit tính theo container; App phải stateless: session, rate limit, cache ở Redis/DB; WebSocket cần sticky session nếu có long-polling và adapter pub/sub để broadcast; Graceful shutdown: bắt SIGTERM, readiness fail, server.close(), chờ request xong trong grace period
- Dấu hiệu trả lời sai: Lưu session trong bộ nhớ process khi chạy nhiều worker/replica; Chọn số worker theo os.cpus() trong container có CPU limit nhỏ; Thoát ngay khi nhận SIGTERM
- Câu hỏi nối tiếp: Pod nhận SIGTERM nhưng load balancer vẫn gửi request thêm vài giây; bạn xử lý khoảng trễ này thế nào?

**Đề xuất sửa:**
- Câu hỏi mới: Service Node.js đang chạy bằng cluster module (hoặc PM2 cluster mode) trên VM, nay chuyển lên Kubernetes. Nên giữ nhiều worker process trong một container hay chạy một process mỗi pod, và việc chuyển đổi ảnh hưởng gì tới state trong bộ nhớ?
- Đáp án: Giữ phần cách cluster hoạt động, lý do chọn 1 process/pod và ý stateless; rút WebSocket và graceful shutdown còn 1 câu mỗi ý hoặc chuyển sang follow-up; sửa câu về số core theo issue factual.

### de-qa-1006 · Đạt · tin cậy high · Phải đọc

**Topic:** Hàng đợi tác vụ (BullMQ, RabbitMQ) (`node.arch.queues-bullmq`) · ~667 token · hard của topic: 2

**Câu hỏi:** Worker BullMQ xử lý job "trừ tiền rồi gửi email xác nhận". Sau một đợt CPU cao và một lần deploy, một số khách bị trừ tiền hai lần. Giải thích cơ chế lock và stalled job của BullMQ, vì sao job có thể chạy lại, và bạn thiết kế job, worker thế nào cho an toàn.

**Kết luận:** Đúng và bám tài liệu BullMQ: lock/stalled đưa job về waiting, jobId trùng bị bỏ qua nhưng dùng lại được khi job đã xóa, cần idempotency và noeviction. Chỉ có vấn đề nhỏ về độ dài.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | 667 token; bị cắt ý noeviction/AOF và đoạn đánh đổi exactly-once, các ý bắt buộc (cơ chế stalled, idempotency, jobId) vẫn còn. | Rút gọn ý 2 và 3 để dưới 600 token. |
| minor | factual | Đề xuất 'sandboxed processor' để tránh stalled không có trong trang stalled-jobs (trang chỉ khuyên trả quyền cho event loop thường xuyên). | Có thể giữ, nhưng ưu tiên câu 'chia nhỏ việc CPU để worker kịp gia hạn lock'. |

**Kiểm chứng:**
- `supported` Worker đặt lock lên job và phải gia hạn; CPU bận làm không kịp gia hạn và job bị stalled
  > if the CPU is very busy (due to the process being very CPU intensive), the worker may not have time to renew the lock  
  > — https://docs.bullmq.io/guide/workers/stalled-jobs
  _Cùng trang: lock "to protect the job from being modified by any other client or worker"._
- `supported` Job stalled về waiting để worker khác chạy lại; vượt số lần stall tối đa thì vào failed **(quote không có nguyên văn trên trang nguồn)**
  > A stalled job is moved back to the waiting status and will be processed again by another worker.  
  > — https://docs.bullmq.io/guide/workers/stalled-jobs
  _Tiếp theo: "or if it has reached its maximum number of stalls, it will be moved to the failed set."_
- `supported` Worker bị kill khi deploy (không close được) thì job thành stalled và chạy lại **(quote không có nguyên văn trên trang nguồn)**
  > the pending jobs will be marked as stalled and processed by other workers.  
  > — https://docs.bullmq.io/guide/workers/graceful-shutdown
- `supported` Job phải idempotent, atomic; tách job phức tạp bằng flow
  > To achieve this behaviour, your jobs should be as atomic and simple as possible.  
  > — https://docs.bullmq.io/patterns/idempotent-jobs
  _Cùng trang: "If necessary, split complex jobs as described in the flow pattern."_
- `supported` Thêm job với jobId đã tồn tại sẽ bị bỏ qua; id dùng lại được khi job cũ đã bị xóa
  > if you add a job with an existing id then that job will just be ignored and not added to the queue at all.  
  > — https://docs.bullmq.io/guide/jobs/job-ids
  _Cùng trang: "you can add the same job id many times over as long as the previous job has already been removed from the queue."_
- `supported` Redis cho BullMQ phải dùng maxmemory-policy noeviction, nên bật AOF
  > Therefore is very important to configure the `maxmemory-policy` setting to `noeviction`.  
  > — https://docs.bullmq.io/guide/going-to-production
  _Cùng trang: "We recommend enabling AOF (Append Only File), which provides a robust and fast solution."_
- `supported` Graceful shutdown: nghe SIGINT/SIGTERM rồi await worker.close()
  > it is considered good practice to listen for both `SIGINT` and `SIGTERM` signals to close gracefully.  
  > — https://docs.bullmq.io/guide/going-to-production

**Độ khó:** hard thật · hợp level middle, senior — Phải suy luận từ sự cố trừ tiền hai lần ra ngữ nghĩa at-least-once và thiết kế idempotency.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Giải thích cơ chế + thiết kế an toàn; 5 ý chấm được.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu hàng đợi chỉ đảm bảo at-least-once và cách làm job idempotent.
- Ý bắt buộc: Worker giữ lock và phải gia hạn; worker chết hoặc event loop bị chặn thì job bị stalled và chạy lại; attempts > 1 cũng chạy lại job từ đầu: thực tế là at-least-once; Idempotency theo khóa nghiệp vụ (unique constraint, idempotency key của cổng thanh toán); Tách job thành bước nhỏ atomic, kiểm tra trạng thái trước mỗi bước; Graceful shutdown bằng worker.close(); Redis noeviction
- Dấu hiệu trả lời sai: Tin rằng BullMQ đảm bảo exactly-once; Chỉ dùng jobId để chống trừ tiền hai lần; Tăng lockDuration là cách sửa duy nhất
- Câu hỏi nối tiếp: Nếu cổng thanh toán không hỗ trợ idempotency key, bạn làm sao biết lần charge trước đã thành công hay chưa?

### de-qa-1007 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Hàng đợi tác vụ (BullMQ, RabbitMQ) (`node.arch.queues-bullmq`) · ~666 token · hard của topic: 2

**Câu hỏi:** Hàng đợi BullMQ của bạn gọi API bên thứ ba thường xuyên trả 429 hoặc 5xx, đôi khi trả 400 do dữ liệu sai. Thiết kế chiến lược retry và backoff, rate limit, xử lý job thất bại cuối cùng (dead letter) và giám sát hàng đợi.

**Kết luận:** Đạt theo rubric v2: câu hỏi có 1 ý độc lập, trả lời các ý bắt buộc trong khoảng 5 phút; các claim chính đều có trích dẫn. (v1 gợi ý Cần sửa vì đếm 4 ý.)

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | interview_fit | Rubric v2: 1 ý độc lập, ~5 phút cho các ý bắt buộc (retry, rate limit, dead letter và giám sát là các mặt của một thiết kế xử lý lỗi hàng đợi); v1 đếm 4 ý. Còn lại là gợi ý: Câu hỏi có 4 yêu cầu (retry/backoff, rate limit, dead letter, giám sát), mỗi mảng đủ cho một câu riêng. | Tập trung vào phân loại lỗi để retry/backoff/rate limit; dead letter và giám sát thành follow-up. |
| minor | length | 666 token; bị cắt ý noeviction và đoạn đánh đổi, phần retry/rate limit/dead letter vẫn còn. | Rút gọn phần giám sát còn 2 gạch. |

**Kiểm chứng:**
- `supported` Backoff exponential: trễ 2^(attempts-1) × delay; jitter trong khoảng 0..1
  > With exponential backoff, it will retry after `2 ^ (attempts - 1) * delay` milliseconds.  
  > — https://docs.bullmq.io/guide/retrying-failing-jobs
  _Cùng trang: "Jitter percentage option value must be between 0 and 1."_
- `supported` UnrecoverableError đưa job vào failed ngay, không retry
  > BullMQ will just move the job to the failed set without performing any retries  
  > — https://docs.bullmq.io/patterns/stop-retrying-jobs
- `supported` Rate limit thủ công: worker.rateLimit(duration) rồi ném Worker.RateLimitError; worker phải có limiter
  > Don't forget to pass limiter options into your worker's options  
  > — https://docs.bullmq.io/guide/rate-limiting
  _Ví dụ trên trang: "await worker.rateLimit(duration);" và "throw Worker.RateLimitError();". Job bị rate limit "will actually stay in the waiting state."_
- `supported` Job bị rate limit không tiêu attempts; dùng attemptsStarted để tự giới hạn
  > the `attempts` check is ignored, as rate limiting is not considered a real error  
  > — https://docs.bullmq.io/patterns/stop-retrying-jobs
  _Cùng trang: "`job.attemptsStarted` is increased every time that a job is moved to active". Trang này gọi queue.rateLimit, trang rate-limiting gọi worker.rateLimit._
- `supported` limiter global cho mọi worker; concurrency chỉ là số job song song trong một worker
  > The rate limiter is global  
  > — https://docs.bullmq.io/guide/rate-limiting
  _docs.bullmq.io/guide/workers/concurrency: "The local concurrency factor is a worker option that determines how many jobs are allowed to be processed concurrently"._
- `supported` Không có DLQ riêng; job hết retry nằm trong failed, có thể giữ để retry thủ công
  > you can keep either all of the failed jobs or a very large number in case you want to manually retry them  
  > — https://docs.bullmq.io/guide/going-to-production
  _Trang retrying: "When a processor throws an exception, the worker will catch it and move the job to the failed set."_

**Độ khó:** hard thật · hợp level middle, senior — Phải phân loại lỗi và chọn cơ chế BullMQ phù hợp cho từng loại.
**Dùng trong phỏng vấn:** ~5 phút, 1 ý hỏi, chấm được — Rubric v2: retry, rate limit, dead letter và giám sát là các mặt của một thiết kế xử lý lỗi hàng đợi. Đáp án nhiều ý chấm được nhưng câu hỏi quá rộng.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Biết phân loại lỗi (tạm thời, vĩnh viễn, rate limit) và dùng đúng cơ chế retry của BullMQ.
- Ý bắt buộc: Lỗi tạm thời: attempts + backoff exponential có jitter; Lỗi vĩnh viễn (400): ném UnrecoverableError, không retry; 429: worker.rateLimit theo Retry-After + RateLimitError; không tiêu attempts nên cần trần bằng attemptsStarted; limiter là global cho queue, concurrency là theo worker; Job hết retry nằm ở failed; giữ đủ lâu hoặc chuyển sang bảng dead letter để replay
- Dấu hiệu trả lời sai: Retry mọi lỗi kể cả 400; Coi 429 là lỗi thường, tiêu hết attempts; Nghĩ concurrency giới hạn tổng request lên đối tác
- Câu hỏi nối tiếp: Đối tác sập 2 giờ; làm sao để job không hết attempts và không dồn tải khi đối tác vừa hồi phục?

### de-qa-1008 · Cần sửa · tin cậy high · Phải đọc

**Topic:** Cache với Redis (`node.data.redis-caching`) · ~624 token · hard của topic: 7 · golden: g16

**Câu hỏi:** Thiết kế rate limiter phân tán bằng Redis cho API Node.js chạy nhiều instance (ví dụ 100 request mỗi phút cho mỗi API key). So sánh fixed window, sliding window và token bucket, cách đảm bảo tính nguyên tử, và hệ thống nên hành xử thế nào khi Redis gặp sự cố.

**Kết luận:** Các ý kỹ thuật về INCR/EXPIRE, Lua nguyên tử và KEYS khớp tài liệu Redis, nhưng câu hỏi có 3 yêu cầu lớn (so sánh 3 thuật toán, tính nguyên tử, hành vi khi Redis lỗi) nên quá rộng. Pair có golden label g16: chỉ sửa câu hỏi khi đã cập nhật golden set. (Rubric v2: không còn tính là quá rộng; vẫn cần sửa vì claim chưa có nguồn.)

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | interview_fit | Rubric v2: 2 ý độc lập, ~5 phút cho các ý bắt buộc (so sánh thuật toán và tính nguyên tử là một thiết kế; hành vi khi Redis lỗi là ý thứ hai); v1 đếm 3 ý. Còn lại là gợi ý: 3 yêu cầu lớn: so sánh fixed/sliding/token bucket, tính nguyên tử trên nhiều instance, hành vi khi Redis lỗi. | Giữ so sánh thuật toán + tính nguyên tử; chuyển 'khi Redis lỗi' thành follow-up. |
| minor | length | 624 token; chỉ câu về 429 + Retry-After bị cắt. | Không cần cắt thêm nếu bỏ phần Redis lỗi. |
| minor | factual | Nhận định về burst ở biên fixed window và chi phí sliding log là kiến thức thuật toán, chưa có nguồn chính thức trích được. | Không cần sửa nội dung; người duyệt xác nhận bằng kinh nghiệm. |

**Kiểm chứng:**
- `supported` INCR rồi EXPIRE có race: client chết giữa hai lệnh thì key không có TTL
  > If for some reason the client performs the `INCR` command but does not perform the EXPIRE the key will be leaked until we'll see the same IP address again.  
  > — https://redis.io/docs/latest/commands/incr/
  _Tài liệu sửa bằng Lua: incr, nếu current == 1 thì expire; pattern 1 dùng MULTI/EXEC._
- `supported` Lua script chạy nguyên tử và chặn mọi hoạt động khác khi chạy
  > Redis guarantees the script's atomic execution. While executing the script, all server activities are blocked during its entire runtime.  
  > — https://redis.io/docs/latest/develop/programmability/eval-intro/
- `supported` Mọi tên key phải truyền qua KEYS để chạy đúng trên Cluster
  > all names of keys that a script accesses must be explicitly provided as input key arguments.  
  > — https://redis.io/docs/latest/develop/programmability/eval-intro/
  _Câu bắt đầu: "Important: to ensure the correct execution of scripts, both in standalone and clustered deployments,"._
- `supported` Các key của một thao tác nhiều key phải cùng hash slot; dùng hash tag
  > Redis Cluster implements a concept called **hash tags** that can be used to force certain keys to be stored in the same hash slot.  
  > — https://redis.io/docs/latest/operate/oss_and_stack/reference/cluster-spec/
- `unverified` Fixed window cho phép burst gần gấp đôi limit quanh biên cửa sổ; sliding log tốn bộ nhớ theo số request
  _Suy luận thuật toán phổ biến, không có trong tài liệu Redis đã fetch. Hợp lý nhưng chưa có trích dẫn._

**Độ khó:** hard thật · hợp level middle, senior — Thiết kế phân tán có đánh đổi độ chính xác, bộ nhớ, nguyên tử.
**Dùng trong phỏng vấn:** ~5 phút, 2 ý hỏi, chấm được — Rubric v2: so sánh thuật toán và tính nguyên tử là một thiết kế; hành vi khi Redis lỗi là ý thứ hai. Đáp án có 5 ý chấm được, câu hỏi hơi rộng.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Thiết kế rate limiter dùng chung nhiều instance và giữ tính nguyên tử trên Redis.
- Ý bắt buộc: Fixed window: INCR + EXPIRE, rẻ nhưng burst ở biên; INCR/EXPIRE phải nguyên tử; Sliding log chính xác nhưng tốn bộ nhớ; sliding counter là xấp xỉ rẻ; Token bucket cho burst có kiểm soát; đọc-tính-ghi trong một Lua script; Lua chạy nguyên tử nhưng chặn server nên phải ngắn; key qua KEYS, cùng hash slot; Chọn fail-open hay fail-closed khi Redis lỗi tùy endpoint
- Dấu hiệu trả lời sai: GET rồi SET từ Node (không nguyên tử); INCR rồi EXPIRE ở hai lệnh rời mà không bàn race; Mỗi instance giữ bộ đếm riêng trong bộ nhớ
- Câu hỏi nối tiếp: Redis timeout 2 giây trong lúc sự cố; endpoint login và endpoint đọc sản phẩm nên hành xử khác nhau thế nào?

**Đề xuất sửa:**
- Câu hỏi mới: Thiết kế rate limiter phân tán bằng Redis cho API Node.js chạy nhiều instance (100 request mỗi phút cho mỗi API key). So sánh fixed window, sliding window và token bucket, và cách đảm bảo tính nguyên tử.
- Đáp án: Chuyển đoạn 'Khi Redis lỗi' thành follow-up hoặc một câu ngắn. Vì có golden label g16, cập nhật rag_golden.json cùng lúc nếu đổi wording.

### de-qa-1009 · Đạt · tin cậy medium · Có thể chấp nhận

**Topic:** Cache với Redis (`node.data.redis-caching`) · ~681 token · hard của topic: 7

**Câu hỏi:** Hệ thống dùng cache-aside với Redis: đọc cache, miss thì đọc DB rồi SET kèm TTL; khi cập nhật thì ghi DB rồi DEL key. Thỉnh thoảng người dùng thấy dữ liệu cũ kéo dài tới hết TTL, và khi Redis đầy bộ nhớ thì lệnh ghi cache báo lỗi. Giải thích các race condition và cách chọn maxmemory-policy.

**Kết luận:** Đúng: race 'stale set' của cache-aside và các maxmemory-policy đều khớp nguồn. Race condition dựa trên paper Memcache của Facebook (nguồn thứ cấp) nên confidence medium.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | 681 token; bị cắt ý LRU xấp xỉ và đoạn theo dõi metrics, các ý bắt buộc (2 race, giảm thiểu, 3 nhóm policy) vẫn còn. | Bỏ ý 'CDC/outbox' và rút gọn phần volatile-* để dưới 600 token. |
| minor | factual | Các biện pháp double delete, versioning là thực hành phổ biến, không có nguồn chính thức; paper Facebook dùng lease thay vì double delete. | Có thể thêm 'lease' như một lựa chọn bên cạnh versioning. |

**Kiểm chứng:**
- `supported` Cache-aside có race: lần đọc chậm SET giá trị cũ sau khi đã DEL
  > A stale set occurs when a web server sets a value in memcache that does not reflect the latest value that should be cached. This can occur when concurrent updates to memcache get reordered.  
  > — https://www.usenix.org/system/files/conference/nsdi13/nsdi13-final170_update.pdf
  _Paper NSDI 2013 'Scaling Memcache at Facebook', nguồn thứ cấp so với tài liệu Redis._
- `supported` noeviction: không xóa key, lệnh ghi dữ liệu mới bị lỗi
  > `noeviction`: Keys are not evicted but the server will return an error when you try to execute commands that cache new data.  
  > — https://redis.io/docs/latest/develop/reference/eviction/
- `supported` allkeys-lru là mặc định hợp lý khi một phần nhỏ key được truy cập nhiều
  > Use `allkeys-lru` when you expect that a subset of elements will be accessed far more often than the rest.  
  > — https://redis.io/docs/latest/develop/reference/eviction/
- `supported` volatile-* hành xử như noeviction nếu không key nào có TTL
  > The `volatile-xxx` policies behave like `noeviction` if no keys have an associated expiration.  
  > — https://redis.io/docs/latest/develop/reference/eviction/
- `supported` LRU/LFU là xấp xỉ bằng lấy mẫu (maxmemory-samples)
  > The Redis LRU algorithm uses an approximation of the least recently used keys rather than calculating them exactly.  
  > — https://redis.io/docs/latest/develop/reference/eviction/
- `supported` Buffer replication/persistence không tính vào maxmemory
  > The memory used by this buffer is not included in the total that is compared to `maxmemory` to see if eviction is required.  
  > — https://redis.io/docs/latest/develop/reference/eviction/
- `supported` BullMQ yêu cầu noeviction
  > Therefore is very important to configure the `maxmemory-policy` setting to `noeviction`.  
  > — https://docs.bullmq.io/guide/going-to-production

**Độ khó:** hard thật · hợp level middle, senior — Phải dựng được kịch bản race theo thời gian và chọn policy theo vai trò của Redis.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Race condition + chọn maxmemory-policy; 4-5 ý chấm được.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu vì sao cache-aside vẫn có dữ liệu cũ và chọn eviction policy theo mục đích dùng Redis.
- Ý bắt buộc: Race: request đọc DB cũ, request khác cập nhật + DEL, rồi request đầu SET giá trị cũ; DEL sau commit, luôn có TTL làm lưới an toàn; versioning/lease để chặn ghi đè cũ; noeviction làm lệnh ghi lỗi khi đầy: đúng cho queue (BullMQ), sai cho cache thuần; allkeys-lru/lfu cho cache; volatile-* như noeviction nếu không key nào có TTL
- Dấu hiệu trả lời sai: Nghĩ DEL sau khi cập nhật DB là đủ để luôn nhất quán; Dùng chung một Redis noeviction cho cả cache và queue rồi đổi sang allkeys-lru; Không đặt TTL cho key cache
- Câu hỏi nối tiếp: Bạn kiểm chứng race 1 đang xảy ra trên production bằng metric hay log nào?

### de-qa-1010 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** NestJS module và Dependency Injection (`node.web.nestjs-di`) · ~679 token · hard của topic: 2

**Câu hỏi:** Trong một ứng dụng NestJS, developer đánh dấu TenantContextService là `Scope.REQUEST` để lưu tenant hiện tại. Sau đó latency tăng, còn Passport strategy và cron job thì không dùng được service này. Giải thích các injection scope, cơ chế scope lan ngược (bubble up) và các phương án thay thế.

**Kết luận:** Đúng và bám tài liệu NestJS: 3 scope, REQUEST scope lan ngược, Passport/cron phải là singleton, durable provider và AsyncLocalStorage. Chỉ có vấn đề nhỏ về độ dài; lưu ý topic không có level senior.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | 679 token; bị cắt nửa cuối ý durable provider và đoạn kết luận, các ý bắt buộc vẫn còn. | Rút gọn mô tả 3 scope (junior đã biết) để dưới 600 token. |
| minor | topic | Topic node.web.nestjs-di có levels fresher/junior/middle, không có senior; câu này hợp middle-senior. | Giữ ở middle; không cần sửa pair. |

**Kiểm chứng:**
- `supported` DEFAULT là một instance dùng chung cả ứng dụng
  > A single instance of the provider is shared across the entire application.  
  > — https://docs.nestjs.com/fundamentals/injection-scopes
- `supported` REQUEST scope lan ngược lên chuỗi injection
  > The `REQUEST` scope bubbles up the injection chain.  
  > — https://docs.nestjs.com/fundamentals/injection-scopes
  _Cùng trang: "A controller that depends on a request-scoped provider is itself request-scoped."_
- `supported` TRANSIENT không lan như vậy
  > Transient-scoped dependencies don't follow that pattern.  
  > — https://docs.nestjs.com/fundamentals/injection-scopes
- `supported` Request-scoped ảnh hưởng hiệu năng
  > Request-scoped providers affect application performance.  
  > — https://docs.nestjs.com/fundamentals/injection-scopes
- `supported` Passport strategy và cron phải là singleton, không dùng provider request-scoped
  > Some providers must act as singletons and should not use request-scoped providers, like *Passport strategies* or *Cron controllers*.  
  > — https://docs.nestjs.com/fundamentals/injection-scopes
- `supported` Durable provider + ContextIdStrategy cho multi-tenant, không hợp khi rất nhiều tenant
  > This strategy is not ideal for applications with a large number of tenants.  
  > — https://docs.nestjs.com/fundamentals/injection-scopes
- `supported` AsyncLocalStorage giữ mọi provider là singleton cho dữ liệu theo request
  > For that, a per-request store based on AsyncLocalStorage keeps every provider a singleton  
  > — https://docs.nestjs.com/fundamentals/injection-scopes

**Độ khó:** hard thật · hợp level middle, senior — Cần hiểu cơ chế DI bên trong và chi phí, không chỉ định nghĩa scope.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Giải thích scope/bubble up + phương án thay thế; 5 ý chấm được.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu injection scope của NestJS và cái giá của REQUEST scope.
- Ý bắt buộc: DEFAULT singleton, REQUEST mỗi request một instance, TRANSIENT mỗi consumer một instance; REQUEST scope lan ngược: ai phụ thuộc cũng thành request-scoped, tốn CPU/GC mỗi request; Passport strategy và cron phải là singleton nên không dùng được provider request-scoped; Thay thế: AsyncLocalStorage (nestjs-cls) giữ tenant theo ngữ cảnh async; Durable provider khi thật sự cần cây DI riêng theo tenant
- Dấu hiệu trả lời sai: Nghĩ chỉ service đánh dấu REQUEST mới bị ảnh hưởng; Lưu tenant vào biến của singleton; Dùng TRANSIENT để giữ state theo request
- Câu hỏi nối tiếp: Với AsyncLocalStorage, tenant có còn đúng khi bạn đẩy job vào queue và xử lý ở worker không? Vì sao?

### de-qa-1011 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** NestJS module và Dependency Injection (`node.web.nestjs-di`) · ~696 token · hard của topic: 2

**Câu hỏi:** Trong NestJS bạn cần thêm xác thực JWT, kiểm tra quyền theo role, validate DTO, đo thời gian xử lý và chuẩn hóa định dạng lỗi. Mỗi việc nên đặt ở middleware, guard, interceptor, pipe hay exception filter? Giải thích thứ tự trong request lifecycle và các bẫy thường gặp.

**Kết luận:** Đạt theo rubric v2: câu hỏi có 1 ý độc lập, trả lời các ý bắt buộc trong khoảng 4 phút; các claim chính đều có trích dẫn. (v1 gợi ý Cần sửa vì đếm 3 ý.)

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | interview_fit | Rubric v2: 1 ý độc lập, ~4 phút cho các ý bắt buộc (đặt việc vào đúng lớp và thứ tự lifecycle là cùng một mạch); v1 đếm 3 ý. Còn lại là gợi ý: Câu hỏi có 3 yêu cầu (đặt 5 việc vào 5 lớp, giải thích thứ tự lifecycle, bẫy thường gặp); đáp án 7 ý, khó nói hết trong 3-5 phút. | Hỏi đặt 5 việc vào đâu và vì sao; thứ tự lifecycle là must-have, bẫy là follow-up. |
| minor | length | 696 token; bị cắt 2 trong 3 bẫy (guard từ chối không tới interceptor, nhồi logic nghiệp vụ). Bẫy APP_GUARD vẫn còn. | Rút phần thứ tự lifecycle thành một dòng ngắn. |
| minor | topic | Topic có levels fresher/junior/middle, không có senior. | Giữ ở middle. |

**Kiểm chứng:**
- `supported` Guard chạy sau mọi middleware, trước interceptor và pipe
  > Guards are executed after all middleware, but before any interceptor or pipe.  
  > — https://docs.nestjs.com/guards
- `supported` Middleware không biết handler nào chạy sau next(); guard có ExecutionContext
  > Middleware, however, is context-blind by nature: it doesn't know which handler will be executed after it calls next().  
  > — https://docs.nestjs.com/guards
- `supported` Guard trả false thì Nest ném ForbiddenException
  > Behind the scenes, when a guard returns false, the framework throws a ForbiddenException.  
  > — https://docs.nestjs.com/guards
- `supported` Guard global đăng ký ngoài module không inject được dependency; dùng APP_GUARD
  > a global guard registered outside of any module cannot inject dependencies, because the registration happens outside the context of any module.  
  > — https://docs.nestjs.com/guards
- `supported` Guard: global → controller → route
  > Guard execution starts with global guards, proceeds to controller guards, and ends with route guards.  
  > — https://docs.nestjs.com/faq/request-lifecycle
- `supported` Interceptor phần sau chạy ngược route → controller → global
  > the response side (i.e., after the route handler returns) is resolved from route to controller to global.  
  > — https://docs.nestjs.com/faq/request-lifecycle
- `supported` Filter: route → controller → global; mỗi exception chỉ một filter xử lý
  > Nest checks route-bound filters first, then controller-level filters, and finally global filters.  
  > — https://docs.nestjs.com/faq/request-lifecycle
  _Cùng trang: "Exceptions can't be passed from filter to filter"._

**Độ khó:** hard thật · hợp level middle — Phần lớn là hiểu đúng vai trò từng lớp; độ khó middle hơn là senior.
**Dùng trong phỏng vấn:** ~4 phút, 1 ý hỏi, chấm được — Rubric v2: đặt việc vào đúng lớp và thứ tự lifecycle là cùng một mạch. Chấm được theo từng việc, nhưng câu quá rộng.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu vai trò và thứ tự chạy của middleware, guard, interceptor, pipe, exception filter trong NestJS.
- Ý bắt buộc: Thứ tự: middleware → guard → interceptor (trước) → pipe → handler → interceptor (sau) → filter; JWT và role ở guard (có ExecutionContext, đọc metadata bằng Reflector); Validate DTO bằng ValidationPipe; đo thời gian bằng interceptor; format lỗi bằng exception filter global; Đăng ký global qua APP_GUARD/APP_PIPE... để có DI
- Dấu hiệu trả lời sai: Validate DTO trong guard hoặc controller; Nghĩ interceptor thấy được mọi request, kể cả request bị guard chặn; Dùng useGlobalGuards(new X()) rồi thắc mắc vì sao X không inject được service
- Câu hỏi nối tiếp: Bạn muốn log mọi request kể cả bị guard từ chối, kèm thời gian xử lý; đặt logic đó ở đâu?

### de-qa-1012 · Cần sửa · tin cậy high · Phải đọc

**Topic:** ORM, transaction và migration (`node.data.orm-transactions`) · ~711 token · hard của topic: 2 · golden: g05

**Câu hỏi:** Endpoint đặt vé dùng ORM: đọc số ghế còn lại, nếu lớn hơn 0 thì tạo booking và giảm số ghế, tất cả bọc trong một transaction. Dưới tải cao vẫn bán quá số ghế, và có lúc connection pool cạn khiến mọi request treo. Phân tích nguyên nhân với isolation level mặc định của PostgreSQL và nêu cách sửa.

**Kết luận:** Phân tích đúng theo tài liệu PostgreSQL (Read Committed, UPDATE đánh giá lại WHERE, serialization failure 40001), nhưng phần sửa lỗi pool cạn bị cắt ở 600 token và câu hỏi có 2 vấn đề lớn với nhiều cách sửa. Pair có golden label g05. (Rubric v2: không còn tính là quá rộng; vẫn cần sửa vì length.)

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| major | length | 711 token; bị cắt câu 'Sửa: transaction ngắn, side effect sau commit, statement/lock timeout, tính pool theo max_connections' — đây là phần trả lời vế 'pool cạn' của câu hỏi. | Rút gọn 4 cách sửa oversell còn 1 dòng mỗi cách để câu 'Sửa' nằm trong 600 token. |
| minor | interview_fit | Rubric v2: 2 ý độc lập, ~5 phút cho các ý bắt buộc (hai sự cố độc lập (oversell, cạn pool), mỗi cái nguyên nhân và cách sửa); v1 đếm 2 ý. Còn lại là gợi ý: Câu hỏi hỏi 2 sự cố (oversell và pool cạn), đáp án có 4 cách sửa oversell + 2 nguyên nhân + nhiều cách sửa pool; dày cho 3-5 phút. | Giữ cả hai sự cố nhưng chỉ yêu cầu 1-2 cách sửa mỗi sự cố. |

**Kiểm chứng:**
- `supported` PostgreSQL mặc định Read Committed; SELECT chỉ thấy dữ liệu commit trước khi câu bắt đầu
  > *Read Committed* is the default isolation level in PostgreSQL. When a transaction uses this isolation level, a `SELECT` query (without a `FOR UPDATE/SHARE` clause) sees only data committed before the query began  
  > — https://www.postgresql.org/docs/current/transaction-iso.html
- `supported` UPDATE ở Read Committed chờ transaction kia rồi đánh giá lại WHERE trên phiên bản mới
  > The search condition of the command (the `WHERE` clause) is re-evaluated to see if the updated version of the row still matches the search condition.  
  > — https://www.postgresql.org/docs/current/transaction-iso.html
- `supported` Repeatable Read/Serializable có thể lỗi serialization (40001), ứng dụng phải retry cả transaction
  > When an application receives this error message, it should abort the current transaction and retry the whole transaction from the beginning.  
  > — https://www.postgresql.org/docs/current/transaction-iso.html
  _SQLSTATE '40001' được nêu ở mục Serializable._
- `supported` ORM không tự retry lỗi serialization **(quote không có nguyên văn trên trang nguồn)**
  > Prisma ORM does not retry write conflicts for you, so write the retry yourself around the `db.transaction(...)` call.  
  > — https://www.prisma.io/docs/orm/fundamentals/transactions
  _Đúng với Prisma; 'ORM thường không tự retry' là khái quát._
- `supported` Trong callback transaction dùng client gốc thì query chạy trên connection khác, ngoài transaction **(quote không có nguyên văn trên trang nguồn)**
  > Use `tx` for every query inside the callback.  
  > — https://www.prisma.io/docs/orm/fundamentals/transactions
  _Trang giải thích query trên `db` chạy trên connection riêng, ngoài transaction đang mở._
- `supported` Transaction giữ connection suốt thời gian callback chạy
  > There is no transaction timeout either, so a transaction stays open for as long as your callback runs.  
  > — https://www.prisma.io/docs/orm/fundamentals/transactions

**Độ khó:** hard thật · hợp level middle, senior — Cần hiểu isolation level và hành vi UPDATE đồng thời của PostgreSQL.
**Dùng trong phỏng vấn:** ~5 phút, 2 ý hỏi, chấm được — Rubric v2: hai sự cố độc lập (oversell, cạn pool), mỗi cái nguyên nhân và cách sửa. Hai sự cố, nhiều điểm chấm được nhưng đáp án quá dày.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu vì sao bọc transaction không đủ chống oversell ở Read Committed và vì sao transaction dài làm cạn pool.
- Ý bắt buộc: Read Committed: hai transaction cùng đọc 'còn 1 ghế' rồi cùng ghi (check-then-act); UPDATE ... WHERE remaining > 0 rồi kiểm tra số dòng: UPDATE chờ và đánh giá lại WHERE; Hoặc SELECT ... FOR UPDATE; hoặc Serializable + retry khi lỗi 40001; Transaction giữ connection: không gọi HTTP/email trong transaction; Dùng client của transaction (tx), không dùng client gốc trong callback
- Dấu hiệu trả lời sai: Nghĩ có transaction là đủ chống oversell; Tăng pool size là cách chữa duy nhất; Gọi cổng thanh toán bên trong transaction DB
- Câu hỏi nối tiếp: Nếu dùng Serializable thay cho UPDATE có điều kiện, bạn viết retry thế nào để không gửi email hai lần?

**Đề xuất sửa:**
- Đáp án: Rút phần 'Cách sửa' oversell: giữ cách 1 (UPDATE có điều kiện) và cách 2 (FOR UPDATE) chi tiết, gộp cách 3-4 và CHECK constraint vào một dòng. Đưa câu 'Sửa: transaction ngắn, side effect sau commit, timeout, tính pool theo max_connections' lên trước để nằm trong 600 token. Golden label g05: kiểm tra lại recall sau khi sửa.

### de-qa-1013 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** ORM, transaction và migration (`node.data.orm-transactions`) · ~684 token · hard của topic: 2

**Câu hỏi:** Bạn cần đổi schema bảng orders hàng chục triệu dòng trên PostgreSQL production đang nhận ghi liên tục: thêm cột status NOT NULL, tạo index cho cột đó, và sau này đổi tên một cột cũ. Migration do ORM sinh ra, chạy trong transaction, từng làm hệ thống đứng nhiều phút. Hãy thiết kế quy trình migration không downtime.

**Kết luận:** Đúng và bám tài liệu PostgreSQL: ACCESS EXCLUSIVE lock, ADD COLUMN default không volatile không rewrite, NOT VALID + VALIDATE, SET NOT NULL bỏ scan khi có CHECK hợp lệ, CREATE INDEX CONCURRENTLY. Chỉ đoạn nguyên tắc cuối bị cắt.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | 684 token; bị cắt nửa cuối bước đổi tên cột và đoạn nguyên tắc; các bước 1-4 còn đủ. | Rút gọn đoạn 'Vì sao từng bị đứng' để bước 5 nằm trong 600 token. |
| minor | factual | Ý 'ALTER chờ lock xếp hàng và chặn query đến sau' là hành vi lock queue của PostgreSQL, đúng nhưng không có câu trích trong 2 trang đã fetch. | Không cần sửa. |

**Kiểm chứng:**
- `supported` Phần lớn ALTER TABLE lấy ACCESS EXCLUSIVE lock
  > An `ACCESS EXCLUSIVE` lock is acquired unless explicitly noted.  
  > — https://www.postgresql.org/docs/current/sql-altertable.html
- `supported` ADD COLUMN với DEFAULT không volatile lưu vào metadata, không rewrite bảng
  > The value will be only applied when the table is rewritten, making the `ALTER TABLE` very fast even on large tables.  
  > — https://www.postgresql.org/docs/current/sql-altertable.html
  _Câu trước: default "stored in the table's metadata"._
- `supported` DEFAULT volatile (clock_timestamp()) rewrite cả bảng và index
  > Adding a column with a volatile `DEFAULT` (e.g., `clock_timestamp()`), a stored generated column, an identity column, or a column with a domain data type that has constraints will cause the entire table and its indexes to be rewritten.  
  > — https://www.postgresql.org/docs/current/sql-altertable.html
- `supported` NOT VALID bỏ qua scan; VALIDATE CONSTRAINT chỉ lấy SHARE UPDATE EXCLUSIVE
  > Hence, validation acquires only a `SHARE UPDATE EXCLUSIVE` lock on the table being altered.  
  > — https://www.postgresql.org/docs/current/sql-altertable.html
  _Cùng trang: "But if the `NOT VALID` option is used, this potentially-lengthy scan is skipped."_
- `supported` SET NOT NULL bỏ scan khi có CHECK hợp lệ chứng minh không có NULL
  > if a valid `CHECK` constraint exists (and is not dropped in the same command) which proves no `NULL` can exist, then the table scan is skipped.  
  > — https://www.postgresql.org/docs/current/sql-altertable.html
- `supported` CREATE INDEX thường chặn ghi; CONCURRENTLY không chặn ghi nhưng hai lần scan, lâu hơn
  > When this option is used, PostgreSQL must perform two scans of the table, and in addition it must wait for all existing transactions that could potentially modify or use the index to terminate.  
  > — https://www.postgresql.org/docs/current/sql-createindex.html
  _Cùng trang: index thường "will block until the index build is finished" với insert/update/delete._
- `supported` CONCURRENTLY không chạy trong transaction block; thất bại để lại index INVALID vẫn tốn chi phí cập nhật
  > Another difference is that a regular `CREATE INDEX` command can be performed within a transaction block, but `CREATE INDEX CONCURRENTLY` cannot.  
  > — https://www.postgresql.org/docs/current/sql-createindex.html
  _Cùng trang: index invalid "will still consume update overhead"; khuyến nghị drop rồi tạo lại._

**Độ khó:** hard thật · hợp level middle, senior — Cần hiểu lock level của DDL và quy trình expand/contract.
**Dùng trong phỏng vấn:** ~5 phút, 1 ý hỏi, chấm được — Một yêu cầu thiết kế, nhưng bao 3 thay đổi schema; 5 bước chấm được.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Biết DDL nào khóa bảng lâu trên PostgreSQL và cách migration không downtime.
- Ý bắt buộc: Phần lớn ALTER TABLE lấy ACCESS EXCLUSIVE; chờ lock là chặn cả query đến sau; ADD COLUMN default hằng số không rewrite; đặt lock_timeout ngắn + retry; NOT NULL: CHECK ... NOT VALID rồi VALIDATE, sau đó SET NOT NULL bỏ scan; CREATE INDEX CONCURRENTLY, ngoài transaction; thất bại thì drop index INVALID; Đổi tên cột bằng expand/contract qua nhiều release
- Dấu hiệu trả lời sai: Chạy RENAME COLUMN trực tiếp khi code cũ còn chạy; Tạo index thường trên bảng lớn giờ cao điểm; Backfill cả bảng trong một transaction
- Câu hỏi nối tiếp: Migration đang chờ ACCESS EXCLUSIVE lock 30 giây thì traffic đứng; bạn tìm transaction nào đang giữ lock bằng cách nào?

### de-qa-1014 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** TypeScript cho backend (`node.lang.typescript-types`) · ~664 token · hard của topic: 2

**Câu hỏi:** Một service Node.js viết TypeScript ở chế độ strict nhưng vẫn crash với lỗi `Cannot read properties of undefined` khi xử lý payload webhook, dù handler khai báo `const body = req.body as OrderEvent`. Giải thích vì sao type system không bảo vệ được ở đây và thiết kế cách kiểm tra dữ liệu lúc chạy mà vẫn giữ type safety đầu-cuối.

**Kết luận:** Đúng và bám tài liệu TypeScript/Zod: type assertion bị xóa khi biên dịch, không kiểm tra runtime; validate ở biên bằng schema, z.infer, safeParse, discriminated union + never. Chỉ có vấn đề nhỏ về độ dài.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | 664 token; bị cắt nửa cuối đoạn đánh đổi (contract nội bộ), các ý bắt buộc còn đủ. | Bỏ ý 6 (z.input/z.output) nếu cần dưới 600 token. |
| minor | factual | Ý 'type predicate tự viết không được compiler kiểm chứng' đúng theo hành vi TypeScript nhưng handbook không nói thẳng. | Không cần sửa. |

**Kiểm chứng:**
- `supported` Type annotation không thay đổi hành vi lúc chạy
  > Type annotations never change the runtime behavior of your program.  
  > — https://www.typescriptlang.org/docs/handbook/2/basic-types.html
- `supported` Type assertion không sinh kiểm tra runtime
  > Reminder: Because type assertions are removed at compile-time, there is no runtime checking associated with a type assertion. There won’t be an exception or `null` generated if the type assertion is wrong.  
  > — https://www.typescriptlang.org/docs/handbook/2/everyday-types.html
- `supported` Suy ra type từ schema bằng z.infer
  > You can extract this type with the `z.infer<>` utility  
  > — https://zod.dev/basics
- `supported` parse() ném ZodError; safeParse trả discriminated union
  > The result type is a discriminated union  
  > — https://zod.dev/basics
  _Cùng trang: "the `.parse()` method will throw a `ZodError` instance"._
- `supported` Discriminated union theo trường literal
  > When every type in a union contains a common property with literal types, TypeScript considers that to be a *discriminated union*, and can narrow out the members of the union.  
  > — https://www.typescriptlang.org/docs/handbook/2/narrowing.html
- `supported` Kiểm tra exhaustive bằng never ở nhánh default
  > This means you can use narrowing and rely on `never` turning up to do exhaustive checking in a `switch` statement.  
  > — https://www.typescriptlang.org/docs/handbook/2/narrowing.html
- `supported` z.input/z.output khác nhau khi có transform; z.infer tương đương z.output
  > equivalent to z.infer<typeof mySchema>  
  > — https://zod.dev/basics
  _Code comment trên dòng z.output trong trang._

**Độ khó:** hard thật · hợp level middle, senior — Phải phân biệt compile-time và runtime và thiết kế validate ở biên; vượt mức định nghĩa.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Giải thích + thiết kế; 4-5 ý chấm được.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu type của TypeScript bị xóa lúc chạy và cách validate dữ liệu ngoài mà vẫn giữ type safety.
- Ý bắt buộc: `as OrderEvent` là type assertion, không có kiểm tra runtime; type bị xóa khi biên dịch; req.body thực chất là any: dữ liệu qua ranh giới chưa được xác minh; Validate ở biên bằng schema runtime (Zod...) và suy ra type từ schema (z.infer); safeParse trả 400/dead letter thay vì để undefined nổ sâu; nhận dữ liệu ngoài là unknown; Discriminated union + never để bắt thiếu case lúc compile
- Dấu hiệu trả lời sai: Nghĩ strict mode sẽ kiểm tra req.body lúc chạy; Viết interface và schema riêng rẽ, để chúng lệch nhau; Dùng type predicate viết tay thay cho validate thật
- Câu hỏi nối tiếp: Payload webhook có thêm trường lạ không có trong schema; Zod mặc định xử lý thế nào và bạn muốn chặn hay cho qua?

### de-qa-1015 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** TypeScript cho backend (`node.lang.typescript-types`) · ~650 token · hard của topic: 2

**Câu hỏi:** Thiết kế một EventBus type-safe cho backend TypeScript sao cho `emit('order.created', payload)` báo lỗi compile nếu payload sai kiểu theo tên event. Trình bày cách dùng generics với keyof, mapped type và conditional type (kể cả `infer` và tính distributive), và khi nào type quá phức tạp trở thành gánh nặng.

**Kết luận:** Đạt theo rubric v2: câu hỏi có 1 ý độc lập, trả lời các ý bắt buộc trong khoảng 5 phút; các claim chính đều có trích dẫn. (v1 gợi ý Cần sửa vì đếm 3 ý.)

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | interview_fit | Rubric v2: 1 ý độc lập, ~5 phút cho các ý bắt buộc (một thiết kế type kèm khi nào type quá phức tạp (trade-off của chính thiết kế đó)); v1 đếm 3 ý. Còn lại là gợi ý: Câu hỏi có 3 yêu cầu và liệt kê 4 tính năng phải trình bày (generics/keyof, mapped, conditional/infer, distributive); dễ thành bài kể… | Giữ thiết kế EventBus + một bẫy (distributive); đưa 'khi nào thành gánh nặng' sang follow-up. |
| minor | length | 650 token; chỉ câu cuối về nguyên tắc dùng type phức tạp bị cắt. | Bỏ ví dụ Array<infer U> trùng với PayloadOf. |

**Kiểm chứng:**
- `supported` Mapped type duyệt qua keyof để tạo type mới
  > A mapped type is a generic type which uses a union of `PropertyKey`s (frequently created via a `keyof`) to iterate through keys to create a type:  
  > — https://www.typescriptlang.org/docs/handbook/2/mapped-types.html
  _Đã bỏ link markdown trong câu._
- `supported` infer khai báo biến type trong nhánh true của conditional type
  > Conditional types provide us with a way to infer from types we compare against in the true branch using the `infer` keyword.  
  > — https://www.typescriptlang.org/docs/handbook/2/conditional-types.html
- `supported` Conditional type trên generic trần phân phối qua union: ToArray<string | number> thành string[] | number[]
  > When conditional types act on a generic type, they become *distributive* when given a union type.  
  > — https://www.typescriptlang.org/docs/handbook/2/conditional-types.html
  _Ví dụ trên trang: ToArray<string | number> // string[] | number[]._
- `supported` Bọc hai vế extends trong ngoặc vuông để tránh phân phối
  > To avoid that behavior, you can surround each side of the `extends` keyword with square brackets.  
  > — https://www.typescriptlang.org/docs/handbook/2/conditional-types.html
- `supported` Type bị xóa lúc chạy nên vẫn cần validate runtime
  > Type annotations never change the runtime behavior of your program.  
  > — https://www.typescriptlang.org/docs/handbook/2/basic-types.html

**Độ khó:** hard thật · hợp level middle, senior — Generics nâng cao và distributive conditional type là phần khó; phần còn lại là áp dụng.
**Dùng trong phỏng vấn:** ~5 phút, 1 ý hỏi, chấm được — Rubric v2: một thiết kế type kèm khi nào type quá phức tạp (trade-off của chính thiết kế đó). Chấm được nhưng quá rộng; có code nên phù hợp vòng có màn hình hơn vòng nói.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Dùng generics của TypeScript để ràng buộc payload theo tên event và hiểu bẫy distributive conditional type.
- Ý bắt buộc: Interface ánh xạ tên event sang payload; emit<K extends keyof E>(name: K, payload: E[K]); K suy ra từ literal, E[K] cho đúng kiểu payload nên sai là lỗi compile; Mapped type { [K in keyof E]: handler } buộc đăng ký đủ handler; Conditional type trên generic trần phân phối qua union; bọc [T] extends [any] để tránh; Type phức tạp làm chậm tsc và khó đọc; vẫn cần validate runtime
- Dấu hiệu trả lời sai: Dùng string và any cho tên event/payload; Không hiểu vì sao ToArray<string | number> ra string[] | number[]; Nghĩ type an toàn thì dữ liệu từ queue cũng an toàn
- Câu hỏi nối tiếp: Làm sao viết test khẳng định emit('order.created', { userId }) phải lỗi compile?

### de-qa-1016 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Profiling và rò rỉ bộ nhớ (`node.perf.profiling-memory`) · ~671 token · hard của topic: 2

**Câu hỏi:** Một service Node.js chạy trong container bị OOMKill vài ngày một lần. Dashboard cho thấy RSS tăng đều nhưng heapUsed dao động ổn định. Bạn điều tra thế nào, và quy trình sẽ khác gì nếu chính heapUsed mới là chỉ số tăng dần sau mỗi lần GC?

**Kết luận:** Đúng và bám tài liệu Node: đọc đúng các trường process.memoryUsage(), phân biệt rò ngoài heap với rò heap JS, quy trình so sánh heap snapshot và rủi ro khi chụp trên production. Chỉ đoạn cuối bị cắt.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | 671 token; bị cắt nửa cuối lưu ý production (--max-old-space-size thấp hơn limit, cảnh báo theo xu hướng); các ý bắt buộc còn đủ. | Rút gọn đoạn đọc process.memoryUsage(). |

**Kiểm chứng:**
- `supported` external là bộ nhớ của object C++ gắn với object JS
  > `external` refers to the memory usage of C++ objects bound to JavaScript objects managed by V8.  
  > — https://raw.githubusercontent.com/nodejs/node/main/doc/api/process.md
- `supported` arrayBuffers gồm mọi Buffer và cũng được tính trong external
  > This is also included in the `external` value.  
  > — https://raw.githubusercontent.com/nodejs/node/main/doc/api/process.md
  _Câu trước: arrayBuffers "including all Node.js Buffers"._
- `supported` memoryUsage() duyệt từng page nên tốn; process.memoryUsage.rss() nhanh hơn
  > The `process.memoryUsage()` method iterates over each page to gather information about memory usage  
  > — https://raw.githubusercontent.com/nodejs/node/main/doc/api/process.md
  _Cùng trang: "but `process.memoryUsage.rss()` is faster."_
- `supported` So sánh hai snapshot ở chế độ Comparison, tìm delta dương lớn rồi xem retainer
  > Look for large positive deltas and explore the references that caused them in the bottom panel.  
  > — https://nodejs.org/en/learn/diagnostics/memory/using-heap-snapshot
- `supported` Chụp snapshot dừng main thread, có thể hơn một phút
  > Depending on the heap contents it could even take more than a minute.  
  > — https://nodejs.org/en/learn/diagnostics/memory/using-heap-snapshot
  _Câu trước: "When creating a snapshot, all other work in your main thread is stopped."_
- `supported` Snapshot có thể làm heap gấp đôi và làm process chết
  > The snapshot is built in memory, so it can double the heap size, resulting in filling up entire memory and then crashing the app.  
  > — https://nodejs.org/en/learn/diagnostics/memory/using-heap-snapshot
- `supported` --heapsnapshot-signal chụp snapshot khi nhận signal
  > Enables a signal handler that causes the Node.js process to write a heap dump when the specified signal is received.  
  > — https://raw.githubusercontent.com/nodejs/node/main/doc/api/cli.md

**Độ khó:** hard thật · hợp level senior — Chẩn đoán rò bộ nhớ theo chỉ số và quy trình snapshot trên production.
**Dùng trong phỏng vấn:** ~5 phút, 2 ý hỏi, chấm được — Hai nhánh điều tra (ngoài heap, trong heap); 5 ý chấm được.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Đọc đúng các chỉ số bộ nhớ của Node và biết quy trình tìm rò bộ nhớ.
- Ý bắt buộc: rss là toàn bộ process; heapUsed là heap V8; external/arrayBuffers là ngoài heap (Buffer); RSS tăng mà heapUsed ổn định: nghi Buffer, native addon, worker; heapUsed tăng sau GC: so sánh 2 heap snapshot (Comparison), xem retainers; Thủ phạm quen: cache không giới hạn, listener không gỡ, closure, setInterval; Snapshot dừng main thread và tốn thêm bộ nhớ: chụp trên instance đã rút khỏi LB
- Dấu hiệu trả lời sai: Chụp heap snapshot để tìm rò Buffer; Chụp snapshot trên instance đang nhận traffic; Tăng memory limit là cách chữa
- Câu hỏi nối tiếp: Đặt --max-old-space-size bằng đúng memory limit của container thì có vấn đề gì?

### de-qa-1017 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Profiling và rò rỉ bộ nhớ (`node.perf.profiling-memory`) · ~640 token · hard của topic: 2

**Câu hỏi:** Sau một release, API Node.js có p99 latency tăng từ khoảng 50ms lên vài giây theo từng đợt, trong lúc đó một core CPU chạm 100% và log không có lỗi. Trình bày cách đo event loop lag, profile CPU để tìm đoạn code chặn event loop, và các nguyên nhân hay gặp.

**Kết luận:** Đạt theo rubric v2: câu hỏi có 1 ý độc lập, trả lời các ý bắt buộc trong khoảng 4 phút; các claim chính đều có trích dẫn. (v1 gợi ý Cần sửa vì đếm 3 ý.)

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | interview_fit | Rubric v2: 1 ý độc lập, ~4 phút cho các ý bắt buộc (đo event loop lag, profile CPU và nguyên nhân hay gặp là một bài chẩn đoán); v1 đếm 3 ý. Còn lại là gợi ý: 3 yêu cầu: đo event loop lag, profile CPU tìm code, liệt kê nguyên nhân hay gặp; đáp án có 4 phần. | Giữ đo lag + profile; nguyên nhân hay gặp làm follow-up. |
| minor | length | 640 token; chỉ câu cuối phần khắc phục bị cắt. | Bỏ ý clinic để dưới 600 token. |
| minor | factual | Lời khuyên 'xem các khối rộng ở đỉnh stack' không có trong trang flame-graphs (trang nói xem thanh màu cam đậm nhất trước); vẫn là cách đọc flame graph phổ biến. | Không bắt buộc sửa. |

**Kiểm chứng:**
- `supported` monitorEventLoopDelay tạo histogram độ trễ event loop, đơn vị nanosecond
  > Creates a histogram object that samples and reports the event loop delay over time. The delays will be reported in nanoseconds.  
  > — https://raw.githubusercontent.com/nodejs/node/main/doc/api/perf_hooks.md
- `supported` eventLoopUtilization cho biết thời gian loop bận/rảnh
  > The `eventLoopUtilization()` function returns an object that contains the cumulative duration of time the event loop has been both idle and active  
  > — https://raw.githubusercontent.com/nodejs/node/main/doc/api/perf_hooks.md
- `supported` --cpu-prof ghi CPU profile ra file khi thoát
  > Starts the V8 CPU profiler on start up, and writes the CPU profile to disk before exit.  
  > — https://nodejs.org/api/cli.html
- `supported` Flame graph: 0x hoặc perf với --perf-basic-prof và --interpreted-frames-native-stack
  > Run `node --interpreted-frames-native-stack --perf-basic-prof-only-functions` to get function names in the flame graph regardless of which pipeline V8 used to compile your JavaScript.  
  > — https://nodejs.org/en/learn/diagnostics/flame-graphs
  _Trang cũng giới thiệu 0x._
- `supported` JSON.parse/stringify là O(n) nhưng chậm với input lớn
  > While these are `O(n)` in the length of the input, for large `n` they can take surprisingly long.  
  > — https://nodejs.org/en/learn/asynchronous-work/dont-block-the-event-loop
- `supported` Regex có nested quantifier như (a+)* có thể chặn event loop (ReDoS)
  > Avoid nested quantifiers like `(a+)*`. V8's regexp engine can handle some of these quickly, but others are vulnerable.  
  > — https://nodejs.org/en/learn/asynchronous-work/dont-block-the-event-loop

**Độ khó:** hard thật · hợp level middle, senior — Debug một sự cố cụ thể bằng công cụ đo và profile.
**Dùng trong phỏng vấn:** ~4 phút, 1 ý hỏi, chấm được — Rubric v2: đo event loop lag, profile CPU và nguyên nhân hay gặp là một bài chẩn đoán. Chấm được nhưng hơi rộng.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Biết cách xác nhận event loop bị chặn và tìm đoạn code gây chặn.
- Ý bắt buộc: Đo event loop delay (monitorEventLoopDelay) và ELU; delay tăng cùng latency = có việc đồng bộ dài; Delay thấp mà latency cao thì nhìn sang threadpool/DB/downstream; Profile CPU: --cpu-prof hoặc --inspect, flame graph (0x, perf); Nguyên nhân hay gặp: JSON lớn, ReDoS, API sync, thuật toán O(n²)
- Dấu hiệu trả lời sai: Tăng số instance mà không tìm nguyên nhân; Chỉ nhìn log vì log không có lỗi; Nhầm event loop lag với latency của DB
- Câu hỏi nối tiếp: Profile chỉ ra một regex validate email chiếm 90% CPU; bạn sửa và phòng tái diễn thế nào?

### de-qa-1018 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Kiểm thử với Jest (`node.test.jest-testing`) · ~673 token · hard của topic: 2

**Câu hỏi:** Test suite Jest của một backend Node.js chạy ổn khi chạy riêng từng file nhưng flaky trên CI: test fail ngẫu nhiên, mock của test trước "rò" sang test sau, và Jest báo không thoát được sau khi chạy xong. Phân tích nguyên nhân và cách làm cho test cô lập, ổn định.

**Kết luận:** Đúng và bám tài liệu Jest: worker song song (cores - 1), khác nhau giữa clearMocks/resetMocks/restoreMocks, isolateModules, hoist jest.mock, --detectOpenHandles, --forceExit, --randomize/--seed. Chỉ có vấn đề nhỏ về độ dài.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | 673 token; bị cắt 2 gạch cuối (randomize/seed, fake timers), các nguyên nhân và cách sửa chính còn đủ. | Rút gọn ý 3 (trạng thái module). |

**Kiểm chứng:**
- `supported` Single run mặc định số worker = số core trừ một
  > In single run mode, this defaults to the number of the cores available on your machine minus one for the main thread.  
  > — https://jestjs.io/docs/cli
- `supported` clearMocks chỉ xóa lịch sử gọi, không xóa implementation
  > This does not remove any mock implementation that may have been provided.  
  > — https://jestjs.io/docs/configuration
- `supported` resetMocks xóa implementation giả nhưng không khôi phục bản gốc
  > This will lead to any mocks having their fake implementations removed but does not restore their initial implementation.  
  > — https://jestjs.io/docs/configuration
- `supported` Khôi phục bản gốc chỉ áp dụng cho mock tạo bằng jest.spyOn; jest.fn() phải tự xử lý
  > `mockFn.mockRestore()` only works when the mock was created with `jest.spyOn()`. Thus you have to take care of restoration yourself when manually assigning `jest.fn()`.  
  > — https://jestjs.io/docs/mock-function-api
  _Với replaceProperty: "replacedProperty.restore() only works when the property value was replaced with jest.replaceProperty()"._
- `supported` jest.isolateModules tạo sandbox registry, resetModules xóa cache module
  > `jest.isolateModules(fn)` goes a step further than `jest.resetModules()` and creates a sandbox registry for the modules that are loaded inside the callback function.  
  > — https://jestjs.io/docs/jest-object
- `supported` jest.mock được hoist nên factory không được tham chiếu biến khai báo phía dưới
  > Since calls to `jest.mock()` are hoisted to the top of the file, Jest prevents access to out-of-scope variables.  
  > — https://jestjs.io/docs/es6-class-mocks
  _Ngoại lệ: biến bắt đầu bằng 'mock'._
- `supported` --detectOpenHandles ép chạy tuần tự, chậm, chỉ để debug; --forceExit là lối thoát tạm
  > This implies `--runInBand`, making tests run serially.  
  > — https://jestjs.io/docs/cli
  _Cùng trang: "This option has a significant performance penalty and should only be used for debugging." và --forceExit "This feature is an escape-hatch."_
- `supported` --randomize xáo thứ tự test trong file theo seed
  > Shuffle the order of the tests within a file. The shuffling is based on the seed.  
  > — https://jestjs.io/docs/cli

**Độ khó:** hard thật · hợp level middle — Debug test flaky đòi hiểu mô hình worker và mock của Jest; mức middle hơn senior.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Phân tích + làm cho ổn định; 5 ý chấm được.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu vì sao test Jest flaky trên CI: chạy song song, mock rò, state module, handle không đóng.
- Ý bắt buộc: Jest chạy các file song song trên nhiều worker: DB/port/thư mục dùng chung đạp lên nhau; clearMocks chỉ xóa lịch sử; resetMocks xóa implementation; restoreMocks khôi phục gốc (chỉ với spyOn); Cô lập dữ liệu theo JEST_WORKER_ID hoặc transaction rollback; Đóng server/pool/timer trong afterAll; --detectOpenHandles để tìm, --forceExit chỉ là tạm
- Dấu hiệu trả lời sai: Thêm --runInBand vĩnh viễn để 'hết flaky'; Dùng --forceExit như cách sửa; Nghĩ restoreMocks khôi phục cả jest.fn()
- Câu hỏi nối tiếp: Test chỉ fail khi chạy chung với một file khác; bạn dùng --randomize/--seed và --runInBand thế nào để khoanh vùng?

### de-qa-1019 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Kiểm thử với Jest (`node.test.jest-testing`) · ~688 token · hard của topic: 2

**Câu hỏi:** Bạn cần unit test hàm `fetchWithRetry` dùng `await sleep(backoff)` (sleep bọc setTimeout trong Promise) với exponential backoff tối đa 5 lần. Test với timer thật mất hàng chục giây, còn khi dùng `jest.useFakeTimers()` cùng `jest.advanceTimersByTime()` thì test treo hoặc assertion chạy sai thời điểm. Giải thích vì sao và cách viết test đúng.

**Kết luận:** Đúng và bám tài liệu Jest: advanceTimersByTime đồng bộ không cho microtask chạy, dùng advanceTimersByTimeAsync/runAllTimersAsync (không có ở legacy), runOnlyPendingTimers cho timer tự đặt lại. Chỉ đoạn thiết kế cho testability bị cắt.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | 688 token; bị cắt đoạn 'Thiết kế cho testability' (inject sleep/clock) và một phần ý 5; các ý bắt buộc (nguyên nhân, API async, không await trước) còn đủ. | Rút gọn ý 3-4 để đoạn inject sleep nằm trong 600 token vì đó là ý thiết kế quan trọng. |

**Kiểm chứng:**
- `supported` advanceTimersByTimeAsync cho promise callback chạy trước khi chạy timer
  > Asynchronous equivalent of `jest.advanceTimersByTime(msToRun)`. It allows any scheduled promise callbacks to execute *before* running the timers.  
  > — https://jestjs.io/docs/jest-object
- `supported` Các API async này không có ở legacy fake timers
  > This function is not available when using legacy fake timers implementation.  
  > — https://jestjs.io/docs/jest-object
- `supported` runAllTimers có giới hạn số timer đệ quy
  > The maximum number of recursive timers that will be run when calling `jest.runAllTimers()`. The default is `100_000` timers.  
  > — https://jestjs.io/docs/jest-object
- `supported` runOnlyPendingTimers chỉ chạy timer đang chờ, hợp với timer tự đặt lại
  > If any of the currently pending macro-tasks schedule new macro-tasks, those new tasks will not be executed by this call.  
  > — https://jestjs.io/docs/jest-object
- `supported` doNotFake giữ API thật
  > List of names of APIs that should not be faked. The default is `[]`, meaning all APIs are faked.  
  > — https://jestjs.io/docs/jest-object

**Độ khó:** hard thật · hợp level middle — Cần hiểu tương tác microtask với fake timers; khó với middle, quen với senior.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Giải thích + cách viết đúng; 4 ý chấm được.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu vì sao fake timers đồng bộ không tương thích với chuỗi await và cách test code có retry/backoff.
- Ý bắt buộc: Giữa các sleep có await (microtask); advanceTimersByTime chạy đồng bộ nên timer kế tiếp chưa được đăng ký; Dùng await jest.advanceTimersByTimeAsync / runAllTimersAsync; Khởi động promise, gắn expectation trước, tiến thời gian rồi mới await; Inject hàm sleep/clock để unit test không phụ thuộc timer
- Dấu hiệu trả lời sai: Tăng timeout của test để chờ timer thật; Await hàm cần test trước khi tiến đồng hồ; Dùng runAllTimers với retry vô hạn
- Câu hỏi nối tiếp: Làm sao kiểm tra hàm không gọi lại API nếu chỉ tiến thiếu 1ms so với backoff?

### de-qa-1020 · Cần sửa · tin cậy high · Chỉ hình thức

**Topic:** Xác thực JWT và phân quyền (`node.web.api-auth-jwt`) · ~687 token · hard của topic: 2 · golden: g22

**Câu hỏi:** Thiết kế cơ chế access token và refresh token cho SPA cùng API Node.js sao cho có thể thu hồi phiên và phát hiện refresh token bị đánh cắp. Trình bày refresh token rotation, reuse detection, nơi lưu token ở client và các đánh đổi.

**Kết luận:** Nội dung đúng theo RFC 9700 (rotation, reuse detection, hết hạn khi không hoạt động), nhưng câu hỏi gộp 4 yêu cầu và phần lưu access token ở client bị cắt ở 600 token. Pair có golden label g22. (Rubric v2: không còn tính là quá rộng; vẫn cần sửa vì length.)

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| major | length | Phần cắt ở 600 token rơi vào mục 'Lưu ở client': mất ý chống CSRF cho endpoint refresh và ý giữ access token trong bộ nhớ thay vì localStorage, trong khi câu hỏi hỏi trực tiếp nơi lưu token. | Nếu giữ nguyên câu hỏi, rút phần 'Chi tiết triển khai' để mục lưu token nằm trong 600 token. |
| minor | interview_fit | Rubric v2: 1 ý độc lập, ~5 phút cho các ý bắt buộc (rotation, reuse detection, nơi lưu và đánh đổi là các mặt của một thiết kế token); v1 đếm 4 ý. Còn lại là gợi ý: 4 yêu cầu: rotation, reuse detection, nơi lưu token, đánh đổi; đáp án dài 687 token. | Giữ rotation + reuse detection (cốt lõi); nơi lưu token thành follow-up. |
| minor | factual | Viết 'RFC 9700 yêu cầu refresh token của public client phải sender-constrained hoặc dùng rotation' là đúng ý, nhưng RFC nói server phải dùng một trong hai cách để phát hiện replay. | Viết: 'RFC 9700 yêu cầu authorization server dùng sender-constraint hoặc rotation để phát hiện replay refresh token của public client'. |

**Kiểm chứng:**
- `supported` Public client phải dùng sender-constrained refresh token hoặc rotation
  > Authorization servers MUST utilize one of these methods to detect refresh token replay by malicious actors for public clients  
  > — https://www.rfc-editor.org/rfc/rfc9700.txt
  _Hai phương pháp: sender-constrained refresh token và refresh token rotation (mục 4.14.2)._
- `supported` Rotation: mỗi lần refresh cấp refresh token mới
  > the authorization server issues a new refresh token with every access token refresh response.  
  > — https://www.rfc-editor.org/rfc/rfc9700.txt
- `supported` Reuse detection: server không biết bên nào hợp lệ nên thu hồi refresh token đang hoạt động
  > The authorization server cannot determine which party submitted the invalid refresh token  
  > — https://www.rfc-editor.org/rfc/rfc9700.txt
  _Câu tiếp: "but it will revoke the active refresh token."_
- `supported` Refresh token nên hết hạn khi client không hoạt động một thời gian
  > Refresh tokens SHOULD expire if the client has been inactive for some time  
  > — https://www.rfc-editor.org/rfc/rfc9700.txt
- `supported` Cookie HttpOnly không đọc được bằng JavaScript, giảm rủi ro XSS, nhưng vẫn tự gửi kèm request
  > Forbids JavaScript from accessing the cookie, for example, through the `Document.cookie` property.  
  > — https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie
  _Cùng trang: cookie HttpOnly "will still be sent with JavaScript-initiated requests" và "This mitigates attacks against cross-site scripting (XSS)."_

**Độ khó:** hard thật · hợp level middle, senior — Thiết kế bảo mật có đánh đổi (stateless vs thu hồi, XSS vs CSRF).
**Dùng trong phỏng vấn:** ~5 phút, 1 ý hỏi, chấm được — Rubric v2: rotation, reuse detection, nơi lưu và đánh đổi là các mặt của một thiết kế token. Nhiều ý chấm được, câu hỏi quá rộng.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu vai trò access/refresh token và cách rotation + reuse detection phát hiện token bị đánh cắp.
- Ý bắt buộc: Access token sống ngắn, xác minh stateless; refresh token opaque, lưu hash, thu hồi được; Rotation: mỗi lần refresh cấp token mới, vô hiệu token cũ trong cùng family; Token cũ bị dùng lại = có hai bên giữ: thu hồi cả family; Bước kiểm tra-đánh dấu-phát mới phải nguyên tử để refresh song song không tự kích hoạt reuse; Refresh token trong cookie HttpOnly/Secure/SameSite, endpoint refresh chống CSRF
- Dấu hiệu trả lời sai: Lưu refresh token trong localStorage; Access token sống nhiều ngày rồi dựa vào denylist; Nghĩ HttpOnly chống được XSS hoàn toàn
- Câu hỏi nối tiếp: Hai tab cùng gọi refresh gần như đồng thời; thiết kế của bạn có tự đăng xuất người dùng không, và bạn xử lý thế nào?

**Đề xuất sửa:**
- Câu hỏi mới: Thiết kế cơ chế access token và refresh token cho SPA cùng API Node.js sao cho có thể thu hồi phiên và phát hiện refresh token bị đánh cắp. Trình bày refresh token rotation và reuse detection.
- Đáp án: Giữ Phân vai, Rotation, Reuse detection, Chi tiết triển khai; rút 'Lưu ở client' còn 1-2 câu hoặc chuyển sang follow-up; sửa câu RFC 9700 theo issue factual. Golden label g22: kiểm tra lại recall sau khi sửa.

### de-qa-1021 · Cần sửa · tin cậy high · Phải đọc

**Topic:** Xác thực JWT và phân quyền (`node.web.api-auth-jwt`) · ~658 token · hard của topic: 2

**Câu hỏi:** Khi review đoạn code xác minh JWT trong một API Node.js chỉ gọi `jwt.verify(token, key)`, bạn kiểm tra những lỗ hổng nào? Giải thích tấn công `alg: none`, nhầm lẫn thuật toán RS256/HS256, thiếu kiểm tra iss/aud, cross-JWT confusion và cách xử lý xoay vòng khóa qua JWKS.

**Kết luận:** Các ý bảo mật đều khớp RFC 8725, nhưng câu hỏi yêu cầu giải thích 5 chủ đề (alg none, RS256/HS256, iss/aud, cross-JWT, JWKS) nên quá rộng cho 3-5 phút. (Rubric v2: không còn tính là quá rộng; vẫn cần sửa vì claim chưa có nguồn.)

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | interview_fit | Rubric v2: 1 ý độc lập, ~5 phút cho các ý bắt buộc (các lỗ hổng liệt kê là checklist của một bài review jwt.verify); v1 đếm 5 ý. Còn lại là gợi ý: Câu hỏi nêu 5 chủ đề phải giải thích (alg none, RS256/HS256, iss/aud, cross-JWT confusion, xoay khóa JWKS); thành bài kể checklist. | Hỏi 'review jwt.verify(token, key) bạn thấy lỗ hổng gì' và để ứng viên tự nêu; chỉ yêu cầu đi sâu 2 lỗ hổng (algorithm confusion, aud). |
| minor | length | 658 token; chỉ ý 6 (payload không mã hóa, secret đủ dài) bị cắt. | Bỏ ý 6 hoặc gộp vào ý 3. |
| minor | factual | Phần vận hành JWKS (cache, giới hạn refetch) chưa có nguồn chính thức trích được. | Không bắt buộc sửa. |

**Kiểm chứng:**
- `supported` Thư viện phải cho caller chỉ định tập thuật toán; không suy ra từ header
  > Libraries MUST enable the caller to specify a supported set of algorithms  
  > — https://datatracker.ietf.org/doc/html/rfc8725
- `supported` Không dùng 'none' trừ khi được yêu cầu tường minh
  > JWT libraries SHOULD NOT generate JWTs using "none" unless explicitly requested to do so by the caller.  
  > — https://datatracker.ietf.org/doc/html/rfc8725
- `supported` Tấn công đổi RS256 sang HS256, dùng public key làm secret HMAC; mỗi khóa chỉ một thuật toán
  > would try to validate the signature using HMAC-SHA256 and using the RSA public key as the HMAC shared secret  
  > — https://datatracker.ietf.org/doc/html/rfc8725
  _Cùng RFC: "Moreover, each key MUST be used with exactly one algorithm,"_
- `supported` Kiểm tra iss và khóa thuộc issuer; kiểm tra aud
  > the relying party or application MUST validate the audience value,  
  > — https://datatracker.ietf.org/doc/html/rfc8725
  _Cùng RFC: "the cryptographic keys used for the cryptographic operations in the JWT belong to the issuer."_
- `supported` Cross-JWT confusion: quy tắc xác minh các loại JWT phải loại trừ nhau; dùng typ tường minh
  > the validation rules for those JWTs MUST be written such that they are mutually exclusive,  
  > — https://datatracker.ietf.org/doc/html/rfc8725
  _Cùng RFC: "Explicit typing is RECOMMENDED for new uses of JWTs."_
- `unverified` JWKS: chỉ lấy khóa từ URL cấu hình sẵn, cache, giới hạn refetch khi gặp kid lạ
  _RFC 8725 không có phần vận hành JWKS; là thực hành phổ biến, chưa tìm được nguồn chính thức trong số lần fetch cho phép._

**Độ khó:** hard thật · hợp level middle, senior — Cần hiểu cơ chế tấn công, không chỉ thuộc khuyến nghị.
**Dùng trong phỏng vấn:** ~5 phút, 1 ý hỏi, chấm được — Rubric v2: các lỗ hổng liệt kê là checklist của một bài review jwt.verify. Chấm được theo checklist nhưng quá rộng.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Biết các lỗ hổng xác minh JWT phổ biến và cách cấu hình verify đúng.
- Ý bắt buộc: Luôn truyền danh sách algorithms tường minh; không chấp nhận 'none' hay thuật toán theo header; Algorithm confusion RS256 → HS256 dùng public key làm secret; mỗi khóa một thuật toán; Kiểm tra exp/nbf, iss, aud: thiếu aud thì token của service A dùng được ở B; Nhiều loại JWT cùng issuer: dùng typ/aud/khóa riêng để quy tắc loại trừ nhau; JWKS: chọn khóa theo kid trong JWKS tin cậy, cache và giới hạn refetch
- Dấu hiệu trả lời sai: Nghĩ chữ ký đúng là đủ; Tin URL khóa (jku) trong header token; Lưu dữ liệu nhạy cảm trong payload vì nghĩ JWT được mã hóa
- Câu hỏi nối tiếp: Issuer vừa xoay khóa và nhiều request báo kid lạ; service của bạn nên làm gì để không thành DoS lên endpoint JWKS?

**Đề xuất sửa:**
- Câu hỏi mới: Khi review đoạn code xác minh JWT trong một API Node.js chỉ gọi `jwt.verify(token, key)`, bạn kiểm tra những lỗ hổng nào? Giải thích kỹ tấn công nhầm lẫn thuật toán RS256/HS256 và hậu quả của việc thiếu kiểm tra aud.
- Đáp án: Giữ ý 1-3 chi tiết; rút ý 4 (cross-JWT) và 5 (JWKS) còn 1 câu mỗi ý hoặc chuyển sang follow-up; bỏ ý 6.

