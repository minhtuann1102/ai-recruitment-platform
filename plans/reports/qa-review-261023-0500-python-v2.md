# Báo cáo duyệt cặp Q&A — python (2026-10-23 05:03)

> Báo cáo do Claude tạo bằng skill `interview-qa-review`: **chỉ là gợi ý kèm bằng chứng**. Các cặp này cũng do Claude viết, nên người reviewer (cùng họ model) có thể chung điểm mù. Quyết định và `reviewed_by` thuộc về người duyệt.

**22/22 cặp đã duyệt** · Đạt 20 · Cần sửa 2 · Bỏ 0 · tin cậy cao 21 / vừa 0 / thấp 1

**Phân loại cho người duyệt:** Phải đọc 4 · Chỉ hình thức 0 (câu hỏi quá rộng, quá dài: nội dung đúng) · Có thể chấp nhận 18

**Kiểm tra trích dẫn nguyên văn:** khớp 143 · không khớp 2 · không kiểm được từ máy này 0

## Cặp mồi (kiểm tra người reviewer)

| qa_id | Lỗi cài sẵn | Gợi ý nhận được | Bắt được? |
|---|---|---|---|
| de-qa-1072 | Nói gather mặc định tự hủy các awaitable còn lại khi một cái lỗi (sai: các awaitable khác không bị hủy, tiếp tục chạy; TaskGroup mới hủy) | Cần sửa: [critical] Đáp án nói gather (return_exceptions=False) tự hủy các awaitable còn lại 'nên không có tác vụ chạy ngầm'. Tài liệu asyncio nói c… | có |

## Tổng hợp

| qa_id | Topic | Gợi ý | Tin cậy | Nhóm | Vấn đề chính | Token | Golden |
|---|---|---|---|---|---|---|---|
| de-qa-1050 | Task queue với Celery | Đạt | high | Có thể chấp nhận | [minor] Rubric v2: 2 ý độc lập, ~5 phút cho các ý bắt buộc (cơ chế ack và visibility timeout là nguyên nhân chạy hai lần; thiết kế an toàn … | 688 | 1 |
| de-qa-1051 | Task queue với Celery | Đạt | high | Có thể chấp nhận | [minor] Chunk ~672 token, vượt 600. Phần bị cắt là đoạn 'Giám sát' cuối; các ý chẩn đoán và cấu hình nằm trước điểm cắt. | 672 |  |
| de-qa-1052 | GIL, threading, multiprocessing và asyn… | Đạt | high | Có thể chấp nhận | [minor] Ý 4 chỉ ghi 'từ 3.13' mà không nói 3.13 là thử nghiệm, 3.14 mới chính thức hỗ trợ (PEP 779) và vẫn là build tùy chọn, không mặc địn… | 694 |  |
| de-qa-1053 | FastAPI, async và dependency injection | Đạt | high | Có thể chấp nhận | [minor] Chunk ~643 token, vượt 600. Chỉ mất cuối đoạn 'Chẩn đoán' (py-spy, so thread bận với limiter); các ý chấm điểm còn nguyên. | 643 | 1 |
| de-qa-1054 | FastAPI, async và dependency injection | Đạt | high | Có thể chấp nhận | [minor] Chunk ~736 token, vượt 600. Điểm cắt rơi giữa khối code get_db và mất đoạn 'Thêm' (task queue, timeout httpx). Quy tắc rollback rồi… | 736 |  |
| de-qa-1055 | SQLAlchemy session và transaction | Đạt | high | Có thể chấp nhận | [minor] Chunk ~718 token, vượt 600. Phần bị cắt là 3 gạch đầu dòng cuối của 'Thiết kế lifecycle' (session theo request, transaction ngắn, t… | 718 |  |
| de-qa-1056 | SQLAlchemy session và transaction | Đạt | high | Có thể chấp nhận | [minor] Chunk ~683 token, vượt 600. Phần bị cắt là cuối ý pre_ping, pool_recycle và 'Theo dõi'; pool_recycle là một ý cho triệu chứng kết n… | 683 |  |
| de-qa-1057 | Django ORM và queryset | Đạt | high | Có thể chấp nhận | [minor] Chunk ~716 token, vượt 600. Phần bị cắt là đoạn 'Thêm' (không bắt exception trong atomic, ATOMIC_REQUESTS); hai vấn đề chính và các… | 716 |  |
| de-qa-1058 | Django ORM và queryset | Đạt | high | Có thể chấp nhận | [minor] Chunk ~640 token, vượt 600 một chút. Chỉ mất câu 'Chống tái phát' (assertNumQueries). | 640 |  |
| de-qa-1059 | Decorator và context manager | Đạt | high | Có thể chấp nhận | [minor] Chunk ~785 token, vượt 600 khá nhiều. Phần bị cắt là toàn bộ 'Lưu ý khác' (@retry vs @retry(), thứ tự xếp chồng, generator, markcor… | 785 |  |
| de-qa-1060 | Decorator và context manager | Đạt | high | Có thể chấp nhận | [minor] Chunk ~744 token, vượt 600. Phần bị cắt là cuối mục 4 (ContextDecorator, BaseException, lock) và 'Kiểm thử'; ba lỗi chính nằm trước… | 744 |  |
| de-qa-1061 | Iterator và generator | Đạt | high | Có thể chấp nhận | [minor] Chunk ~695 token, vượt 600. Phần bị cắt là ý 5 (GeneratorExit) và 'Giám sát'; vòng đời và 4 cách thiết kế chính nằm trước điểm cắt.… | 695 |  |
| de-qa-1062 | Iterator và generator | Đạt | high | Phải đọc | [minor] Rubric v2: 2 ý độc lập, ~5 phút cho các ý bắt buộc (bốn triệu chứng có hai cơ chế gốc: iterator một lượt (cạn, tee đệm) và đánh giá… | 700 |  |
| de-qa-1063 | Type hint, dataclass và Pydantic | Đạt | high | Có thể chấp nhận | [minor] Chunk ~734 token, vượt 600. Phần bị cắt là cuối đoạn model_construct (lưu ý hiệu năng) và 'Tăng tốc đúng cách' (model_validate_json… | 734 |  |
| de-qa-1064 | Type hint, dataclass và Pydantic | Đạt | high | Có thể chấp nhận | [minor] Chunk ~744 token, vượt 600. Phần bị cắt là câu issubclass và toàn bộ 'Khuyến nghị'; đánh đổi ABC/Protocol, variance và runtime_chec… | 744 |  |
| de-qa-1065 | Đóng gói và triển khai ứng dụng Python | Cần sửa | low | Phải đọc | [major] Chunk ~767 token, vượt 600. Đoạn 'Health check' (liveness không gọi DB, readiness fail khi shutdown) nằm hoàn toàn trong phần bị cắ… | 767 |  |
| de-qa-1066 | Đóng gói và triển khai ứng dụng Python | Đạt | high | Phải đọc | [minor] Chunk ~716 token, vượt 600. Phần bị cắt là non-root, 'Chuỗi cung ứng' (SBOM, quét lỗ hổng) và 'Đánh đổi'; lock, hash và multi-stage… | 716 |  |
| de-qa-1067 | Kiểm thử với pytest | Đạt | high | Có thể chấp nhận | [minor] Chunk ~715 token, vượt 600. Phần bị cắt là cuối ý 5 và 'Bẫy thường gặp'; các ý scope, rollback, teardown và xdist nằm trước điểm cắ… | 715 |  |
| de-qa-1068 | Kiểm thử với pytest | Cần sửa | high | Phải đọc | [major] Rubric v2 vẫn tính là quá rộng (3 ý độc lập, ~6 phút): ba triệu chứng có ba cơ chế khác nhau: patch nơi tra cứu tên, autospec, Asyn… | 736 |  |
| de-qa-1069 | Xác thực và phân quyền API | Đạt | high | Có thể chấp nhận | [minor] Câu hỏi gói 4 vấn đề (thuật toán băm, so sánh ==, user enumeration, nâng tham số). Mỗi ý có đáp án ngắn nên vẫn chấm được trong ~5 … | 675 |  |
| de-qa-1070 | Xác thực và phân quyền API | Đạt | high | Có thể chấp nhận | [minor] Chunk ~731 token, vượt 600. Phần bị cắt là cuối ý 4, ý 5 (test tự động A truy cập tài nguyên B) và ý 6; nguyên nhân và hàng rào chí… | 731 |  |
| de-qa-1071 | GIL, threading, multiprocessing và asyn… | Đạt | high | Có thể chấp nhận | [minor] Ý 3 ghi 'từ CPython 3.13' mà không nói 3.13 là thử nghiệm, 3.14 mới được hỗ trợ chính thức (PEP 779), vẫn là build tùy chọn. | 667 |  |

## Ảnh hưởng nếu sửa hoặc bỏ

- de-qa-1065: bỏ thì topic còn < 2 cặp hard (SC-001)
- de-qa-1068: bỏ thì topic còn < 2 cặp hard (SC-001)
- 22/22 cặp dài hơn 600 token: snippet của Planner sẽ bị cắt (de-qa-1050, de-qa-1051, de-qa-1052, de-qa-1053, de-qa-1054, de-qa-1055, de-qa-1056, de-qa-1057, de-qa-1058, de-qa-1059, de-qa-1060, de-qa-1061, de-qa-1062, de-qa-1063, de-qa-1064, de-qa-1065, de-qa-1066, de-qa-1067, de-qa-1068, de-qa-1069, de-qa-1070, de-qa-1071).

## Việc cho người duyệt

- **Phải đọc** (4): de-qa-1062, de-qa-1065, de-qa-1066, de-qa-1068. Sai kiến thức, lỗi thời, chưa kiểm chứng được, tin cậy thấp, hoặc trích dẫn không khớp nguyên văn. Đọc phần kiểm chứng; chỗ Claude bác bỏ chính nguồn mà cặp trích thì Claude cũng có thể sai.
- **Chỉ hình thức** (0): —. Nội dung đúng; vấn đề là câu hỏi quá rộng hoặc quá dài. Sửa hay giữ là lựa chọn của bạn.
- **Có thể chấp nhận** (18): de-qa-1050, de-qa-1051, de-qa-1052, de-qa-1053, de-qa-1054, de-qa-1055, de-qa-1056, de-qa-1057, de-qa-1058, de-qa-1059, de-qa-1060, de-qa-1061, de-qa-1063, de-qa-1064, de-qa-1067, de-qa-1069, de-qa-1070, de-qa-1071. Mọi ý đã có trích dẫn; chấp nhận dựa trên bằng chứng là quyết định của bạn.
- Có nhãn golden set (2): de-qa-1050, de-qa-1053. Sửa câu hỏi thì giữ các thuật ngữ chính.

## Chi tiết từng cặp

### de-qa-1050 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Task queue với Celery (`py.async.celery-queues`) · ~688 token · hard của topic: 2 · golden: g13

**Câu hỏi:** Hệ thống dùng Celery với Redis làm broker. Task `charge_order` đôi khi chạy hai lần: một lần sau khi worker bị OOM kill, và một số task đặt countdown dài thì bị chạy lặp đi lặp lại. Giải thích cơ chế acknowledgement (mặc định và acks_late), visibility timeout của Redis broker, và thiết kế để an toàn.

**Kết luận:** Đạt theo rubric v2: câu hỏi có 2 ý độc lập, trả lời các ý bắt buộc trong khoảng 5 phút; các claim chính đều có trích dẫn. (v1 gợi ý Cần sửa vì đếm 3 ý.)

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | interview_fit | Rubric v2: 2 ý độc lập, ~5 phút cho các ý bắt buộc (cơ chế ack và visibility timeout là nguyên nhân chạy hai lần; thiết kế an toàn là cách sửa); v1 đếm 3 ý. Còn lại là gợi ý: Câu hỏi có 3 yêu cầu (cơ chế ack mặc định/acks_late, visibility timeout, thiết kế an toàn) và gợi sẵn tên cơ chế, vừa rộng v… | Hỏi theo kịch bản: 'Vì sao charge_order chạy hai lần trong hai tình huống trên, và bạn thiết kế thế nào để khách không bị trừ tiền hai lần?' (2 yêu cầu). Cặp có golden label g13: đổi câu hỏi thì chạy lại eval retrieval. |
| minor | length | Chunk ~688 token, vượt 600. Phần bị cắt là cuối ý 5 (prefetch=1) và đoạn 'Chọn chế độ'; các ý chấm điểm chính nằm trước điểm cắt. | Gộp 'Chọn chế độ' thành một câu ngắn, bỏ ý 2–3 của phần thiết kế (truyền ID, tách side effect) nếu cần rút. |

**Kiểm chứng:**
- `supported` Mặc định worker ack message ngay trước khi chạy task
  > the default behavior is to acknowledge the message in advance, just before it’s executed,  
  > — https://docs.celeryq.dev/en/stable/userguide/tasks.html
- `supported` acks_late: ack sau khi chạy, worker crash giữa chừng thì task có thể chạy nhiều lần
  > This means the task may be executed multiple times should the worker crash in the middle of execution.  
  > — https://docs.celeryq.dev/en/stable/userguide/tasks.html
- `supported` Tiến trình con bị kill (OOM, signal) thì message vẫn bị ack kể cả khi bật acks_late
  > the worker will acknowledge the message if the child process executing the task is terminated  
  > — https://docs.celeryq.dev/en/stable/userguide/tasks.html
  _Câu tiếp theo trên trang: "even when `acks_late` is enabled." Trang cũng nêu lý do OOM có thể lặp lại._
- `supported` Muốn giao lại trong trường hợp này thì bật task_reject_on_worker_lost
  > consider enabling the `task_reject_on_worker_lost` setting.  
  > — https://docs.celeryq.dev/en/stable/userguide/tasks.html
- `supported` Redis: task không được ack trong visibility timeout sẽ được giao lại; mặc định 1 giờ
  > If a task isn't acknowledged within the Visibility Timeout the task will be redelivered to another worker and executed.  
  > — https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html
  _Cùng trang: "The default visibility timeout for Redis is 1 hour."_
- `supported` ETA/countdown dài hơn visibility timeout thì task bị chạy lặp
  > This causes problems with ETA/countdown/retry tasks where the time to execute exceeds the visibility timeout;  
  > — https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html
  _Câu tiếp: "in fact if that happens it will be executed again, and again in a loop." Cấu hình qua broker_transport_options._
- `supported` Task nên idempotent
  > Make sure your tasks are idempotent.  
  > — https://docs.celeryq.dev/en/stable/userguide/tasks.html
- `supported` acks_late kết hợp worker_prefetch_multiplier = 1 để mỗi process chỉ giữ một task
  > You can have a worker only reserve as many tasks as there are worker processes  
  > — https://docs.celeryq.dev/en/stable/userguide/optimizing.html
  _Đoạn tiếp: "with the condition that they are acknowledged late", ví dụ task_acks_late = True, worker_prefetch_multiplier = 1._

**Độ khó:** hard thật · hợp level middle, senior — Phải hiểu ngữ nghĩa at-most-once/at-least-once, trường hợp đặc biệt khi process bị kill và visibility timeout; middle thường chỉ biết acks_late.
**Dùng trong phỏng vấn:** ~5 phút, 2 ý hỏi, chấm được — Rubric v2: cơ chế ack và visibility timeout là nguyên nhân chạy hai lần; thiết kế an toàn là cách sửa. Có 5 ý chấm được rõ, nhưng 3 yêu cầu là nhiều so với 3–5 phút.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu khi nào Celery xác nhận (ack) message, vì sao task có thể chạy lại, và cách làm task chạy lại vẫn an toàn (idempotent).
- Ý bắt buộc: Mặc định ack ngay trước khi chạy: worker chết thì mất task, không chạy lại; acks_late ack sau khi chạy xong: at-least-once, task có thể chạy nhiều lần; Process bị OOM/kill thì vẫn bị ack kể cả acks_late, trừ khi bật task_reject_on_worker_lost; Redis visibility timeout (mặc định 1 giờ): countdown/ETA dài hơn thì task bị giao lại lặp đi lặp lại; Charge phải idempotent: khóa theo order_id, unique constraint, idempotency key ở cổng thanh toán
- Dấu hiệu trả lời sai: Nói acks_late đảm bảo exactly-once; Sửa bằng cách tắt retry hoặc tăng visibility timeout mà không làm task idempotent; Không biết task có countdown dài bị lặp do visibility timeout
- Câu hỏi nối tiếp: Nếu cổng thanh toán không hỗ trợ idempotency key thì bạn chống charge trùng thế nào?

### de-qa-1051 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Task queue với Celery (`py.async.celery-queues`) · ~672 token · hard của topic: 2

**Câu hỏi:** Một cụm Celery xử lý cả task ngắn (gửi thông báo, vài trăm ms) lẫn task dài (render báo cáo, vài phút). Người dùng phàn nàn thông báo bị trễ hàng phút dù nhiều worker process đang rảnh, và khi dịch vụ email gặp sự cố thì hàng nghìn task retry cùng lúc làm nó sập tiếp. Phân tích nguyên nhân và đề xuất cấu hình.

**Kết luận:** Đúng và bám tài liệu Celery: chẩn đoán prefetch giữ task ngắn sau task dài, tách queue/worker, retry_backoff + jitter với giá trị mặc định chính xác. Chỉ có vấn đề nhỏ về độ dài.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | Chunk ~672 token, vượt 600. Phần bị cắt là đoạn 'Giám sát' cuối; các ý chẩn đoán và cấu hình nằm trước điểm cắt. | Gộp đoạn 'Giám sát' thành một câu hoặc bỏ dòng Redis visibility timeout (đã có ở de-qa-1050). |
| minor | factual | Trang Optimizing (Celery 5.6) còn nhắc setting worker_disable_prefetch để task không phải chờ sau task dài; đáp án chưa nêu, không sai. | Có thể thêm một dòng: bản mới có worker_disable_prefetch như một lựa chọn khác. |

**Kiểm chứng:**
- `supported` Số message worker giữ trước = worker_prefetch_multiplier × số concurrency slot
  > The workers' default prefetch count is the worker_prefetch_multiplier setting multiplied by the number of concurrency slots  
  > — https://docs.celeryq.dev/en/stable/userguide/optimizing.html
  _Định nghĩa: "The prefetch limit is a limit for the number of tasks (messages) a worker can reserve for itself."_
- `supported` Hỗn hợp task dài và ngắn: tốt nhất là tách hai nhóm worker cấu hình riêng, route theo thời lượng
  > the best option is to use two worker nodes that are configured separately  
  > — https://docs.celeryq.dev/en/stable/userguide/optimizing.html
  _Câu bắt đầu bằng "If you have a combination of long- and short-running tasks,"._
- `supported` acks_late + prefetch_multiplier = 1 để mỗi process chỉ giữ một task
  > You can have a worker only reserve as many tasks as there are worker processes  
  > — https://docs.celeryq.dev/en/stable/userguide/optimizing.html
  _Kèm điều kiện "with the condition that they are acknowledged late"._
- `supported` retry_backoff=True làm delay tăng theo cấp số nhân
  > If this option is set to `True`, autoretries will be delayed following the rules of exponential backoff.  
  > — https://docs.celeryq.dev/en/stable/userguide/tasks.html
- `supported` retry_backoff_max mặc định 600 giây
  > By default, this option is set to `600`, which is 10 minutes.  
  > — https://docs.celeryq.dev/en/stable/userguide/tasks.html
- `supported` retry_jitter mặc định bật, delay là số ngẫu nhiên từ 0 tới trần, tránh các task retry cùng lúc
  > the delay value calculated by `retry_backoff` is treated as a maximum, and the actual delay value will be a random number between zero and that maximum.  
  > — https://docs.celeryq.dev/en/stable/userguide/tasks.html
  _Mặc định: "By default, this option is set to `True`."_
- `supported` max_retries mặc định 3
  > By default, this option is set to `3`.  
  > — https://docs.celeryq.dev/en/stable/userguide/tasks.html
- `supported` Với Redis, countdown vượt visibility timeout gây chạy lặp
  > This causes problems with ETA/countdown/retry tasks where the time to execute exceeds the visibility timeout;  
  > — https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html

**Độ khó:** hard thật · hợp level middle, senior — Chẩn đoán độ trễ do prefetch khi có process rảnh là kiến thức vận hành thực tế, không phải định nghĩa.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Phân tích nguyên nhân + đề xuất cấu hình cho hai triệu chứng; 5 ý chấm rõ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu prefetch của Celery làm task ngắn kẹt sau task dài, và cách chống retry storm khi dịch vụ ngoài lỗi.
- Ý bắt buộc: Worker giữ trước (prefetch) multiplier × concurrency message; task ngắn có thể kẹt sau task dài trong khi worker khác rảnh; Tách queue/worker cho task dài và task ngắn; Worker task dài: prefetch_multiplier = 1 + acks_late (task idempotent); Retry chỉ cho lỗi tạm thời, retry_backoff + retry_jitter để giãn retry, giới hạn max_retries; Rate limit/circuit breaker và giám sát độ trễ theo queue
- Dấu hiệu trả lời sai: Chỉ tăng số worker mà không hiểu prefetch; Retry mọi exception với delay cố định; Cho rằng process rảnh sẽ tự lấy message đã bị worker khác giữ
- Câu hỏi nối tiếp: Bạn đo thế nào để biết độ trễ đến từ prefetch chứ không phải do thiếu worker?

### de-qa-1052 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** GIL, threading, multiprocessing và asyncio (`py.core.gil-concurrency`) · ~694 token · hard của topic: 2

**Câu hỏi:** Một service asyncio có p99 latency tăng vọt; bật debug mode của asyncio thì log báo nhiều callback chạy quá 100ms. Code gọi một SDK đồng bộ dùng requests, parse JSON lớn, tính toán thuần Python và một số phép numpy. Phân tích từng loại tác vụ dưới góc độ GIL và event loop, và chọn cách offload phù hợp cho mỗi loại.

**Kết luận:** Phân tích đúng theo tài liệu Python: I/O đồng bộ đẩy sang thread, CPU thuần Python sang process, extension nhả GIL có thể dùng thread; debug mode log callback >100ms. Chỉ cần ghi rõ trạng thái free-threading theo phiên bản và rút gọn đuôi.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | outdated | Ý 4 chỉ ghi 'từ 3.13' mà không nói 3.13 là thử nghiệm, 3.14 mới chính thức hỗ trợ (PEP 779) và vẫn là build tùy chọn, không mặc định. | Sửa thành: 'build free-threaded (thử nghiệm ở 3.13, được hỗ trợ chính thức từ 3.14 theo PEP 779, vẫn là build tùy chọn)'. |
| minor | length | Chunk ~694 token, vượt 600. Phần bị cắt là cuối ý 4 và đoạn 'Thêm'; ba loại tác vụ chính nằm trước điểm cắt. | Bỏ đoạn 'Thêm' hoặc rút thành một mệnh đề; rút ý 4 còn một câu. |

**Kiểm chứng:**
- `supported` Debug mode log các callback chạy lâu hơn 100ms, chỉnh qua loop.slow_callback_duration
  > Callbacks taking longer than 100 milliseconds are logged. The loop.slow_callback_duration attribute can be used to set the minimum execution duration in seconds that is considered "slow".  
  > — https://docs.python.org/3/library/asyncio-dev.html
  _Bật bằng PYTHONASYNCIODEBUG=1, Python Development Mode (-X dev) hoặc asyncio.run(debug=True)._
- `supported` Code blocking/CPU-bound không được gọi trực tiếp trong event loop
  > Blocking (CPU-bound) code should not be called directly.  
  > — https://docs.python.org/3/library/asyncio-dev.html
- `supported` Do GIL, to_thread chủ yếu dùng cho hàm I/O-bound; extension nhả GIL thì dùng được cho CPU-bound
  > Due to the GIL, `asyncio.to_thread()` can typically only be used to make IO-bound functions non-blocking. However, for extension modules that release the GIL or alternative Python implementations that don’t have one, `asyncio.to_thread()` can also be used for CPU-bound functions.  
  > — https://docs.python.org/3/library/asyncio-task.html
- `supported` run_in_executor dùng được với ProcessPoolExecutor để chạy ở process khác
  > can also be used with a concurrent.futures.ProcessPoolExecutor to execute code in a different process.  
  > — https://docs.python.org/3/library/asyncio-dev.html
  _Chủ ngữ của câu là loop.run_in_executor()._
- `supported` Bản free-threaded có từ 3.13; chậm hơn ở code đơn luồng, tốn bộ nhớ hơn
  > Starting with the 3.13 release, CPython has support for a build of Python called free threading where the global interpreter lock (GIL) is disabled.  
  > — https://docs.python.org/3/howto/free-threading-python.html
  _Cùng trang: overhead "from about 1% on macOS aarch64 to 8% on x86-64 Linux"; "will typically use more memory". What's New 3.14: "PEP 779: Free-threaded Python is officially supported" (3.13 là thử nghiệm)._
- `supported` GIL có thể tự bật lại khi import extension chưa hỗ trợ free-threading
  > The GIL may also automatically be enabled when importing a C-API extension module that is not explicitly marked as supporting free threading.  
  > — https://docs.python.org/3/howto/free-threading-python.html
- `supported` Event loop chỉ giữ weak reference tới task, phải giữ reference của create_task
  > The event loop only keeps weak references to tasks. A task that isn’t referenced elsewhere may get garbage collected at any time, even before it’s done.  
  > — https://docs.python.org/3/library/asyncio-task.html

**Độ khó:** hard thật · hợp level middle, senior — Phải phân biệt I/O, CPU thuần Python và extension nhả GIL rồi chọn executor phù hợp; junior thường đáp 'dùng thread' cho mọi thứ.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Phân tích + chọn cách offload; 4–5 ý chấm rõ theo từng loại tác vụ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu event loop chạy trên một thread, GIL ảnh hưởng thế nào tới thread, và chọn thread/process cho từng loại việc.
- Ý bắt buộc: Code không await (I/O đồng bộ, tính toán dài) chặn cả event loop; debug mode log callback >100ms; I/O đồng bộ (requests): to_thread/run_in_executor với thread pool, lâu dài thay bằng client async; CPU thuần Python: thread không giúp vì GIL, dùng ProcessPoolExecutor (trả giá pickle, bộ nhớ); Extension C nhả GIL (nhiều phép numpy): thread có thể chạy song song, cần đo; Free-threaded build: chỉ là build tùy chọn, kiểm tra thư viện hỗ trợ
- Dấu hiệu trả lời sai: Nói asyncio làm code CPU chạy song song; Dùng to_thread cho vòng lặp thuần Python và nghĩ sẽ nhanh hơn; Nói 'Python không bao giờ chạy thread song song' mà không nhắc extension nhả GIL hay free-threaded
- Câu hỏi nối tiếp: Thread pool mặc định của run_in_executor bị cạn vì SDK chậm thì triệu chứng là gì và bạn xử lý ra sao?

### de-qa-1053 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** FastAPI, async và dependency injection (`py.web.fastapi-async`) · ~643 token · hard của topic: 2 · golden: g09

**Câu hỏi:** Một API FastAPI chuyển toàn bộ endpoint sang `async def` để "nhanh hơn", nhưng throughput giảm mạnh và health check timeout dưới tải, trong khi trước đó các endpoint `def` chạy ổn. Giải thích cách FastAPI thực thi `def` và `async def` (kể cả dependency), vì sao điều này xảy ra, và quy tắc chọn.

**Kết luận:** Đúng theo tài liệu FastAPI và AnyIO: def chạy trong threadpool, async def chạy trên event loop, limiter mặc định 40 thread, hàm tiện ích không tự vào threadpool. Phần bị cắt chỉ là cuối đoạn chẩn đoán.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | Chunk ~643 token, vượt 600. Chỉ mất cuối đoạn 'Chẩn đoán' (py-spy, so thread bận với limiter); các ý chấm điểm còn nguyên. | Rút đoạn 'Chẩn đoán' còn: 'bật asyncio debug mode, đo event loop lag, dùng py-spy'. |

**Kiểm chứng:**
- `supported` Path operation khai báo bằng def chạy trong threadpool bên ngoài rồi được await
  > When you declare a *path operation function* with normal `def` instead of `async def`, it is run in an external threadpool that is then awaited, instead of being called directly (as it would block the server).  
  > — https://fastapi.tiangolo.com/async/
- `supported` Dependency khai báo bằng def cũng chạy trong threadpool
  > If a dependency is a standard `def` function instead of `async def`, it is run in the external threadpool.  
  > — https://fastapi.tiangolo.com/async/
- `supported` Hàm tiện ích def gọi trực tiếp không được đưa vào threadpool
  > If your utility function is a normal function with `def`, it will be called directly (as you write it in your code), not in a threadpool,  
  > — https://fastapi.tiangolo.com/async/
- `supported` Code blocking trong async def chặn event loop
  > Blocking (CPU-bound) code should not be called directly.  
  > — https://docs.python.org/3/library/asyncio-dev.html
  _Tài liệu asyncio; FastAPI chạy async def trực tiếp ("instead of being called directly" là cách def được xử lý khác đi)._
- `supported` Limiter mặc định của AnyIO là 40 thread, chỉnh qua total_tokens
  > without an explicit `limiter` argument will cause a maximum of 40 threads to be spawned.  
  > — https://anyio.readthedocs.io/en/stable/threads.html
  _Ví dụ: to_thread.current_default_thread_limiter().total_tokens = 60_
- `supported` CPU-bound: thread không giúp vì GIL, dùng process pool
  > Due to the GIL, `asyncio.to_thread()` can typically only be used to make IO-bound functions non-blocking.  
  > — https://docs.python.org/3/library/asyncio-task.html

**Độ khó:** hard thật · hợp level middle, senior — Ngược trực giác ('async nhanh hơn'), cần hiểu threadpool, event loop và giới hạn limiter.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Giải thích cơ chế/nguyên nhân là một ý, quy tắc chọn là ý thứ hai; 4–5 ý chấm rõ. Cặp có golden label g09.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu FastAPI chạy def và async def khác nhau thế nào, và vì sao 'đổi hết sang async' có thể làm chậm hơn.
- Ý bắt buộc: def endpoint/dependency chạy trong threadpool nên code blocking không chặn loop; async def chạy thẳng trên event loop: gọi thư viện đồng bộ bên trong làm đứng mọi request kể cả health check; Threadpool có giới hạn (AnyIO mặc định 40 thread); Quy tắc: có thư viện async thì async def + await; chỉ có thư viện sync thì dùng def hoặc bọc run_in_threadpool/to_thread; CPU nặng đưa ra process pool/task queue
- Dấu hiệu trả lời sai: Cho rằng async def luôn nhanh hơn def; Nghĩ FastAPI tự đưa mọi hàm def (kể cả hàm tiện ích) vào threadpool; Gọi requests.get trong async def mà không thấy vấn đề
- Câu hỏi nối tiếp: Endpoint def gọi dịch vụ chậm làm cạn 40 thread thì triệu chứng là gì và bạn sửa thế nào ngoài việc tăng limiter?

### de-qa-1054 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** FastAPI, async và dependency injection (`py.web.fastapi-async`) · ~736 token · hard của topic: 2

**Câu hỏi:** Trong một service FastAPI, mỗi request tạo `httpx.AsyncClient()` và engine SQLAlchemy mới; dependency `get_db` dùng `yield` nhưng có khối `except Exception: pass`; BackgroundTasks dùng lại session của request để ghi log sau khi trả response. Dưới tải xuất hiện cạn kết nối, lỗi bị nuốt mất và lỗi session đã đóng. Hãy thiết kế lại vòng đời tài nguyên.

**Kết luận:** Thiết kế vòng đời đúng theo tài liệu FastAPI: tài nguyên dùng chung trong lifespan, session theo request qua yield dependency, background task tự mở session, rollback rồi raise lại. Vấn đề nhỏ: chunk dài, điểm cắt rơi giữa khối code.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | Chunk ~736 token, vượt 600. Điểm cắt rơi giữa khối code get_db và mất đoạn 'Thêm' (task queue, timeout httpx). Quy tắc rollback rồi raise lại đã nêu bằng lời trước điểm cắt nên ý chấm điểm vẫn còn, nhưng snippet có code bị cụt. | Bỏ khối code (ý đã có bằng lời) hoặc rút đoạn 'Thêm'; bỏ câu về sub-app được mount (chi tiết phụ). |

**Kiểm chứng:**
- `supported` lifespan là async context manager truyền vào FastAPI(lifespan=...); trước yield chạy lúc startup, sau yield lúc shutdown
  > The first part of the function, before the `yield`, will be executed **before** the application starts.  
  > — https://fastapi.tiangolo.com/advanced/events/
  _Cùng trang: "And the part after the `yield` will be executed **after** the application has finished."_
- `supported` Có lifespan thì handler startup/shutdown không còn được gọi; on_event là cách cũ (deprecated)
  > If you provide a `lifespan` parameter, `startup` and `shutdown` event handlers will no longer be called. It's all `lifespan` or all events, not both.  
  > — https://fastapi.tiangolo.com/advanced/events/
  _Mục on_event có tiêu đề "Alternative Events (deprecated)"._
- `supported` lifespan chỉ chạy cho app chính, không chạy cho sub-app được mount
  > Keep in mind that these lifespan events (startup and shutdown) will only be executed for the main application, not for Sub Applications - Mounts.  
  > — https://fastapi.tiangolo.com/advanced/events/
- `supported` except trong yield dependency mà không raise lại: client nhận 500, server không có log; phải raise lại
  > If you catch an exception in a dependency with `yield`, unless you are raising another `HTTPException` or similar, **you should re-raise the original exception**.  
  > — https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/
  _Cùng trang: client thấy 500 "but the server will **not have any logs**"._
- `supported` Depends(scope="function") đóng dependency trước khi gửi response; mặc định với yield là scope "request", chạy sau response
  > If not specified and the dependency has `yield`, it will have a `scope` of `"request"` by default.  
  > — https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/
  _Cùng trang: scope "function" kết thúc "**before** the response is sent back to the client"._
- `supported` Thứ tự exit code và background task từng thay đổi qua phiên bản; background task nên tự tạo session mới
  > For example, instead of using the same database session, you would create a new database session inside of the background task, and you would obtain the objects from the database using this new session.  
  > — https://fastapi.tiangolo.com/advanced/advanced-dependencies/
  _Trang nêu thay đổi ở 0.106.0 và 0.118.0._

**Độ khó:** hard thật · hợp level middle, senior — Ba lỗi thực tế về vòng đời tài nguyên, đòi hỏi hiểu lifespan, yield dependency và background task; không phải câu định nghĩa.
**Dùng trong phỏng vấn:** ~5 phút, 1 ý hỏi, chấm được — Một yêu cầu thiết kế lại cho ba triệu chứng; 4–5 ý chấm rõ. Hơi sát mức 5 phút.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Biết đặt tài nguyên ở đúng tầng vòng đời (app, request, background) trong FastAPI và không nuốt exception.
- Ý bắt buộc: Engine/pool và httpx.AsyncClient tạo một lần trong lifespan, đóng/dispose khi shutdown; Session DB theo request: dependency có yield, đóng trong finally; except trong yield dependency phải rollback rồi raise lại, nếu không lỗi bị nuốt (500 mà không có log); Background task tự mở session mới, truyền ID chứ không truyền object/session của request; Việc cần bền vững đưa vào task queue
- Dấu hiệu trả lời sai: Tạo engine hoặc AsyncClient trong mỗi request; Dùng except: pass để 'tránh lỗi'; Truyền session của request vào BackgroundTasks
- Câu hỏi nối tiếp: Vì sao tạo engine SQLAlchemy mỗi request lại dẫn tới cạn kết nối dù code có đóng session?

### de-qa-1055 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** SQLAlchemy session và transaction (`py.data.sqlalchemy-sessions`) · ~718 token · hard của topic: 2

**Câu hỏi:** Khi chuyển một service sang SQLAlchemy 2.0 `AsyncSession`, team gặp lỗi `MissingGreenlet` khi truy cập `order.items` sau khi query, lỗi tương tự khi đọc thuộc tính object ngay sau `commit()`, và dữ liệu sai lệch khi dùng chung một session trong `asyncio.gather`. Giải thích nguyên nhân từng lỗi và cách thiết kế session lifecycle cho ứng dụng async.

**Kết luận:** Đúng theo tài liệu SQLAlchemy asyncio: không có I/O ngầm khi truy cập thuộc tính, selectinload/AsyncAttrs, expire_on_commit=False, một AsyncSession không dùng chung cho nhiều task. Phần thiết kế lifecycle cuối bị cắt khỏi snippet.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | Chunk ~718 token, vượt 600. Phần bị cắt là 3 gạch đầu dòng cuối của 'Thiết kế lifecycle' (session theo request, transaction ngắn, trả DTO). Ba lỗi và nguyên nhân (ý chấm chính) nằm trước điểm cắt, nhưng câu hỏi có hỏi lifecycle nên ý 'một session mỗi request' nên được giữ. | Rút đoạn 'Gốc chung' còn 1 câu và rút ý 1 (bỏ joinedload, lazy="raise") để phần lifecycle nằm trong 600 token. |

**Kiểm chứng:**
- `supported` Với asyncio không được có I/O ngầm khi truy cập thuộc tính, lazy load sẽ lỗi
  > Using traditional asyncio, the application needs to avoid any points at which IO-on-attribute access may occur.  
  > — https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
  _Tên lỗi MissingGreenlet không xuất hiện trong phần trang đọc được; không phải ý chấm điểm._
- `supported` selectinload là cách eager load hữu ích nhất; AsyncAttrs.awaitable_attrs cho phép await thuộc tính; lazy="raise" chặn SQL ngầm
  > The most useful eager loading strategy is the selectinload() eager loader  
  > — https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
  _Cùng trang: AsyncAttrs "provides an accessor AsyncAttrs.awaitable_attrs which delivers any attribute as an awaitable"; "relationships can be declared with lazy="raise" so that by default they will not attempt to emit SQL."_
- `supported` Với asyncio nên đặt expire_on_commit=False
  > Session.expire_on_commit should normally be set to False when using asyncio.  
  > — https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- `supported` Một AsyncSession không an toàn cho nhiều task đồng thời; mỗi task dùng session riêng
  > A single instance of AsyncSession is not safe for use in multiple, concurrent tasks.  
  > — https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- `supported` Không dùng chung AsyncEngine (pool mặc định) giữa các event loop; await engine.dispose() khi tắt
  > should not share the same AsyncEngine with different event loops when using the default pool implementation  
  > — https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
  _Cùng trang: "It’s advisable to invoke the AsyncEngine.dispose() method using await"._
- `supported` selectinload phát SELECT phụ theo khóa chính của parent
  > emits a SELECT that refers to the primary key values of the parent object  
  > — https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html

**Độ khó:** hard thật · hợp level middle, senior — Ba lỗi thực tế khi chuyển sang async, cần hiểu I/O ngầm của ORM; khó với người chỉ dùng ORM đồng bộ.
**Dùng trong phỏng vấn:** ~5 phút, 2 ý hỏi, chấm được — Nguyên nhân từng lỗi + thiết kế lifecycle; mỗi lỗi một ý chấm rõ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu vì sao ORM 'tự query khi truy cập thuộc tính' không chạy được với asyncio, và cách quản lý session trong app async.
- Ý bắt buộc: asyncio cần mọi I/O là await tường minh; lazy load và refresh sau expire là I/O ngầm nên lỗi; Eager load trong query (selectinload cho collection) hoặc awaitable_attrs; lazy="raise" để bắt sớm; expire_on_commit=False với AsyncSession, refresh khi cần dữ liệu mới; Một AsyncSession không dùng cho nhiều task đồng thời; mỗi task một session; Một engine cho cả process, một session cho mỗi request/unit of work
- Dấu hiệu trả lời sai: Bọc truy cập thuộc tính trong to_thread để 'sửa' MissingGreenlet; Dùng chung session trong asyncio.gather vì 'cùng một request'; Không biết commit() làm expire object
- Câu hỏi nối tiếp: Đặt expire_on_commit=False thì rủi ro gì và khi nào bạn cần refresh?

### de-qa-1056 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** SQLAlchemy session và transaction (`py.data.sqlalchemy-sessions`) · ~683 token · hard của topic: 2

**Câu hỏi:** Một API dùng SQLAlchemy (sync) chạy gunicorn 8 worker trên 4 pod. Endpoint danh sách khách hàng kèm đơn hàng sinh hàng trăm query mỗi request; khi tải tăng thì DB báo "too many connections", và ứng dụng thỉnh thoảng gặp lỗi kết nối đã bị đóng sau thời gian idle. Phân tích và đề xuất cấu hình loading strategy và connection pool.

**Kết luận:** Đúng theo tài liệu SQLAlchemy: N+1 do lazy load, selectinload cho collection, unique() với joinedload collection, pool mặc định 5+10, pre_ping/recycle, dispose(close=False) sau fork. Tính toán 480 kết nối hợp lý.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | Chunk ~683 token, vượt 600. Phần bị cắt là cuối ý pre_ping, pool_recycle và 'Theo dõi'; pool_recycle là một ý cho triệu chứng kết nối idle bị đóng. | Rút phần N+1 (bỏ ý load_only/phân trang) để pool_pre_ping và pool_recycle nằm trong 600 token. |

**Kiểm chứng:**
- `supported` Relationship mặc định lazy load, lặp qua N object sinh N+1 SELECT
  > By default, all inter-object relationships are lazy loading.  
  > — https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html
  _Cùng trang: "accessing their lazy-loaded attributes means there will be N+1 SELECT"._
- `supported` selectinload thường là lựa chọn tốt nhất cho collection
  > The selectinload() is generally the best loading strategy to use.  
  > — https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html
- `supported` joinedload collection trong 2.0 bắt buộc gọi .unique() trên result
  > the Result.unique() method must be applied to the returned result  
  > — https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html
  _Cùng trang: "The ORM will raise an error if this is not present." joinedload được mô tả là "the most general purpose strategy", liệt kê ở mục many-to-one._
- `supported` QueuePool mặc định pool_size=5, max_overflow=10
  > The size of the pool to be maintained, defaults to 5.  
  > — https://docs.sqlalchemy.org/en/20/core/pooling.html
  _max_overflow: "Defaults to 10."_
- `supported` pool_pre_ping kiểm tra khi checkout, tốn thêm chút overhead, không cứu kết nối đứt giữa transaction
  > does not accommodate for connections dropped in the middle of transactions or other SQL operations  
  > — https://docs.sqlalchemy.org/en/20/core/pooling.html
  _Cùng trang: "emitting a test statement on the SQL connection at the start of each connection pool checkout"._
- `supported` pool_recycle thay kết nối quá tuổi ở lần checkout sau
  > Above, any DBAPI connection that has been open for more than one hour will be invalidated and replaced,  
  > — https://docs.sqlalchemy.org/en/20/core/pooling.html
  _Thay "upon next checkout"._
- `supported` Engine tạo trước khi fork: gọi engine.dispose(close=False) trong process con
  > passing the Engine.dispose.close parameter with a value of False, within the initialize phase of the child process.  
  > — https://docs.sqlalchemy.org/en/20/core/pooling.html

**Độ khó:** hard thật · hợp level middle, senior — Kết hợp N+1, tính ngân sách kết nối qua nhiều process/pod và kết nối chết; cần kinh nghiệm vận hành.
**Dùng trong phỏng vấn:** ~5 phút, 1 ý hỏi, chấm được — Một yêu cầu phân tích + cấu hình cho ba triệu chứng; ý chấm rõ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Phát hiện N+1, hiểu pool kết nối là theo process và xử lý kết nối bị cắt khi idle.
- Ý bắt buộc: N+1 do lazy load; dùng selectinload cho collection, joinedload cho many-to-one; Mỗi process một pool: 8 worker × 4 pod × (5+10) = 480 kết nối tiềm năng; Giảm pool_size/max_overflow theo ngân sách DB, cân nhắc PgBouncer; Kết nối idle bị cắt: pool_pre_ping và/hoặc pool_recycle nhỏ hơn idle timeout; Engine tạo trước fork phải dispose(close=False) ở process con
- Dấu hiệu trả lời sai: Tăng max_connections của DB là giải pháp duy nhất; joinedload mọi collection mà không biết nó nhân dòng; Nghĩ pool dùng chung giữa các worker gunicorn
- Câu hỏi nối tiếp: Dùng PgBouncer ở transaction mode thì cần lưu ý gì với SQLAlchemy?

### de-qa-1057 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Django ORM và queryset (`py.web.django-orm`) · ~716 token · hard của topic: 2

**Câu hỏi:** Trong Django, view đổi điểm thưởng làm: đọc `wallet.points`, kiểm tra đủ điểm, trừ rồi `save()`, sau đó gửi email và đẩy task Celery tạo voucher. Dưới tải xuất hiện điểm âm, đôi khi task Celery chạy mà không thấy bản ghi vừa tạo, hoặc email đã gửi dù giao dịch bị rollback. Phân tích và viết lại cho đúng.

**Kết luận:** Đúng theo tài liệu Django: update có điều kiện với F(), select_for_update trong atomic, on_commit cho email/task, không bắt exception trong atomic. Chỉ có vấn đề nhỏ về độ dài và một chữ về giá trị trả về của update().

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | Chunk ~716 token, vượt 600. Phần bị cắt là đoạn 'Thêm' (không bắt exception trong atomic, ATOMIC_REQUESTS); hai vấn đề chính và cách sửa nằm trước điểm cắt. | Bỏ đoạn 'Thêm' hoặc rút còn một câu; bỏ chi tiết nowait/skip_locked. |
| minor | factual | update() trả về số dòng khớp (matched), không hẳn là số dòng thực sự thay đổi. | Sửa 'số dòng được cập nhật' thành 'số dòng khớp điều kiện'. |

**Kiểm chứng:**
- `supported` F() để DB cập nhật dựa trên giá trị lúc UPDATE, tránh race condition
  > it will only ever update the field based on the value of the field in the database when the `save()` or `update()` is executed, rather than based on its value when the instance was retrieved.  
  > — https://docs.djangoproject.com/en/5.2/ref/models/expressions/
- `supported` Gán F() vào field rồi save() thì biểu thức còn trên instance, áp dụng lại ở lần save sau; dùng refresh_from_db()
  > `F()` objects assigned to model fields persist after saving the model instance and will be applied on each `save()`.  
  > — https://docs.djangoproject.com/en/5.2/ref/models/expressions/
  _Cùng trang: "This persistence can be avoided by reloading the model object after saving it, for example, by using `refresh_from_db()`."_
- `supported` update() trả về số dòng, 0 nghĩa là điều kiện không khớp
  > The `update()` method is applied instantly and returns the number of rows matched by the query (which may not be equal to the number of rows updated if some rows already have the new value).  
  > — https://docs.djangoproject.com/en/5.2/topics/db/queries/
  _Tài liệu nói 'matched', đáp án nói 'được cập nhật'; với điều kiện points__gte thì kết luận vẫn đúng._
- `supported` select_for_update khóa dòng tới cuối transaction; dùng ngoài transaction là TransactionManagementError; có nowait/skip_locked
  > Evaluating a queryset with `select_for_update()` in autocommit mode on backends which support `SELECT ... FOR UPDATE` is a `TransactionManagementError` error because the rows are not locked in that case.  
  > — https://docs.djangoproject.com/en/5.2/ref/models/querysets/
  _Cùng trang: "Returns a queryset that will lock rows until the end of the transaction"._
- `supported` on_commit chỉ chạy sau khi commit thành công, bị hủy khi rollback; ngoài atomic thì chạy ngay
  > If the transaction is instead rolled back (typically when an unhandled exception is raised in an `atomic()` block), the callback will be discarded, and never called.  
  > — https://docs.djangoproject.com/en/5.2/topics/db/transactions/
  _Cùng trang: "When in autocommit mode and outside of an atomic() block, the function will run immediately, not on commit."_
- `supported` Callback lỗi không rollback transaction; robust=True để callback sau vẫn chạy; việc bắt buộc thì không nên dựa vào on_commit
  > Your callbacks are executed *after* a successful commit, so a failure in a callback will not cause the transaction to roll back.  
  > — https://docs.djangoproject.com/en/5.2/topics/db/transactions/
  _robust: "Passing `robust=True` allows the next callbacks to be executed even if the current one throws an exception." Outbox là khuyến nghị kiến trúc, tài liệu Django gợi ý two-phase commit cho việc quan trọng._
- `supported` Không bắt exception bên trong atomic
  > Avoid catching exceptions inside `atomic`!  
  > — https://docs.djangoproject.com/en/5.2/topics/db/transactions/
- `supported` ATOMIC_REQUESTS có chi phí khi tải tăng
  > Opening a transaction for every view has some overhead.  
  > — https://docs.djangoproject.com/en/5.2/topics/db/transactions/

**Độ khó:** hard thật · hợp level middle, senior — Gộp race condition đọc-sửa-ghi và side effect trước commit; senior thường biết on_commit và outbox, middle thường dừng ở select_for_update.
**Dùng trong phỏng vấn:** ~5 phút, 2 ý hỏi, chấm được — Phân tích + viết lại cho ba triệu chứng, quy về hai vấn đề; ý chấm rõ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Nhận ra race condition đọc-sửa-ghi và hiểu side effect (email, task) phải chạy sau khi transaction commit.
- Ý bắt buộc: Hai request cùng đọc rồi cùng ghi: race condition gây điểm âm; Sửa bằng UPDATE có điều kiện với F() (kiểm tra số dòng trả về) hoặc select_for_update trong atomic; CheckConstraint points >= 0 làm lưới an toàn; Gửi email/task qua transaction.on_commit để không chạy khi rollback và worker thấy dữ liệu đã commit; Việc không được mất thì dùng outbox
- Dấu hiệu trả lời sai: Bọc trong atomic là đủ chống race condition; Dùng select_for_update ngoài transaction; Gọi task.delay() trong transaction và tin worker sẽ thấy dữ liệu
- Câu hỏi nối tiếp: Process chết ngay sau commit nhưng trước khi on_commit gửi task thì bạn đảm bảo voucher vẫn được tạo thế nào?

### de-qa-1058 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Django ORM và queryset (`py.web.django-orm`) · ~640 token · hard của topic: 2

**Câu hỏi:** Endpoint xuất 200.000 đơn hàng kèm khách hàng và các dòng sản phẩm trong Django chạy rất chậm, tốn vài GB RAM, và log cho thấy hàng nghìn query giống nhau. Phân tích nguyên nhân liên quan tới lazy QuerySet, N+1 và cache của QuerySet, rồi viết lại truy vấn cho hiệu quả.

**Kết luận:** Đúng theo tài liệu Django: N+1 do lazy QuerySet, cache QuerySet tốn RAM, select_related/prefetch_related với Prefetch(to_attr), iterator(chunk_size) và count()/exists(). Chỉ mất câu assertNumQueries ở cuối.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | Chunk ~640 token, vượt 600 một chút. Chỉ mất câu 'Chống tái phát' (assertNumQueries). | Bỏ dòng explain()/Debug Toolbar để giữ câu assertNumQueries. |
| minor | factual | Ý count()/exists() cần sắc thái: nếu sau đó vẫn lặp qua dữ liệu thì len()/bool trên QuerySet đã đánh giá lại không tốn thêm query. | Thêm: 'chỉ dùng count()/exists() khi không cần đến các object'. |

**Kiểm chứng:**
- `supported` QuerySet lazy, chỉ chạy query khi được đánh giá
  > `QuerySet` objects are lazy – the act of creating a `QuerySet` doesn’t involve any database activity.  
  > — https://docs.djangoproject.com/en/5.2/topics/db/queries/
- `supported` QuerySet giữ cache kết quả sau lần đánh giá đầu, tốn bộ nhớ với tập lớn; iterator() giúp
  > When you have a lot of objects, the caching behavior of the `QuerySet` can cause a large amount of memory to be used. In this case, `iterator()` may help.  
  > — https://docs.djangoproject.com/en/5.2/topics/db/optimization/
  _Cache: "Each `QuerySet` contains a cache to minimize database access." (topics/db/queries)_
- `supported` select_related cho FK/one-to-one bằng JOIN; prefetch_related query riêng và ghép trong Python
  > `prefetch_related`, on the other hand, does a separate lookup for each relationship, and does the 'joining' in Python.  
  > — https://docs.djangoproject.com/en/5.2/ref/models/querysets/
  _select_related "is limited to single-valued relationships - foreign key and one-to-one."_
- `supported` to_attr được khuyến nghị khi lọc prefetch
  > Using `to_attr` is recommended when filtering down the prefetch result as it is less ambiguous than storing a filtered result in the related manager's cache:  
  > — https://docs.djangoproject.com/en/5.2/ref/models/querysets/
- `supported` prefetch_related chỉ có hiệu lực với iterator() khi truyền chunk_size
  > If you use `iterator()` to run the query, `prefetch_related()` calls will only be observed if a value for `chunk_size` is provided.  
  > — https://docs.djangoproject.com/en/5.2/ref/models/querysets/
- `supported` Dùng count()/exists() thay cho len()/if qs
  > Use `QuerySet.exists()` … if you only want to find out if at least one result exists, rather than `if queryset`.  
  > — https://docs.djangoproject.com/en/5.2/topics/db/optimization/
  _Lưu ý của trang: nếu sau đó vẫn cần dữ liệu thì nên đánh giá ngay, vì count()/exists() thêm query._

**Độ khó:** hard thật · hợp level middle, senior — Kết hợp N+1, bộ nhớ do cache và streaming; cần hiểu cách QuerySet đánh giá, không chỉ biết tên select_related.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Phân tích nguyên nhân + viết lại truy vấn; ý chấm rõ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu QuerySet lazy và có cache, nhận ra N+1 và biết xử lý tập dữ liệu rất lớn mà không nổ RAM.
- Ý bắt buộc: Truy cập order.customer/order.items trong vòng lặp gây N+1; select_related cho FK (JOIN), prefetch_related/Prefetch cho quan hệ nhiều; QuerySet cache giữ mọi instance; dùng iterator(chunk_size) để stream (prefetch cần chunk_size); Ghi output theo từng phần, values()/values_list() khi chỉ cần dữ liệu thô; Export rất lớn chạy nền qua task queue
- Dấu hiệu trả lời sai: Dùng select_related cho quan hệ nhiều (items); Gọi list(qs) hoặc len(qs) cho 200.000 dòng; Nghĩ thêm index là đủ sửa N+1
- Câu hỏi nối tiếp: Bạn viết test thế nào để bắt N+1 khi có người thêm field quan hệ mới vào serializer?

### de-qa-1059 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Decorator và context manager (`py.core.decorators-context`) · ~785 token · hard của topic: 2

**Câu hỏi:** Bạn viết decorator `@retry(times=3)` dùng cho cả hàm đồng bộ lẫn `async def`. Phiên bản đầu dùng một wrapper thường bọc try/except quanh `func(*args, **kwargs)`: với hàm async nó không retry lần nào, còn framework (FastAPI, pytest) đọc sai chữ ký và không nhận ra hàm là coroutine function. Giải thích nguyên nhân và cách viết decorator đúng.

**Kết luận:** Đúng theo tài liệu Python: gọi async def chỉ tạo coroutine nên try/except trong wrapper sync không bắt được lỗi, wraps chép metadata và thêm __wrapped__, rẽ nhánh theo iscoroutinefunction. Chunk dài nhưng phần bị cắt chỉ là 'Lưu ý khác'.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | Chunk ~785 token, vượt 600 khá nhiều. Phần bị cắt là toàn bộ 'Lưu ý khác' (@retry vs @retry(), thứ tự xếp chồng, generator, markcoroutinefunction); hai nguyên nhân và code đúng nằm trước điểm cắt. | Rút 'Lưu ý khác' còn 2 ý (chỉ retry lỗi tạm thời/idempotent; dùng asyncio.sleep cho backoff) và bỏ các ý còn lại. |

**Kiểm chứng:**
- `supported` Gọi hàm async def chỉ tạo coroutine object, chưa chạy thân hàm
  > Note that simply calling a coroutine will not schedule it to be executed:  
  > — https://docs.python.org/3/library/asyncio-task.html
  _Cùng trang: "a *coroutine object*: an object returned by calling a *coroutine function*."_
- `supported` Thiếu wraps thì metadata là của wrapper; wraps chép __name__, __qualname__, __doc__, __annotations__ ...
  > If the wrapper function is not updated, the metadata of the returned function will reflect the wrapper definition rather than the original function definition, which is typically less than helpful.  
  > — https://docs.python.org/3/library/functools.html
  _WRAPPER_ASSIGNMENTS gồm __module__, __name__, __qualname__, __annotations__, __type_params__, __doc__._
- `supported` wraps thêm __wrapped__ trỏ về hàm gốc
  > this function automatically adds a `__wrapped__` attribute to the wrapper that refers to the function being wrapped.  
  > — https://docs.python.org/3/library/functools.html
- `supported` inspect.signature mặc định đi theo __wrapped__
  > Pass `False` to get a signature of *callable* specifically (`callable.__wrapped__` will not be used to unwrap decorated callables.)  
  > — https://docs.python.org/3/library/inspect.html
  _Câu về tham số follow_wrapped (mặc định True)._
- `supported` iscoroutinefunction trả True cho hàm async def (hoặc hàm sync được mark); wrapper def trả False
  > Return `True` if the object is a coroutine function (a function defined with an async def syntax), a functools.partial() wrapping a coroutine function, or a sync function marked with markcoroutinefunction().  
  > — https://docs.python.org/3/library/inspect.html
- `supported` inspect.markcoroutinefunction có từ Python 3.12
  > Decorator to mark a callable as a coroutine function if it would not otherwise be detected by iscoroutinefunction().  
  > — https://docs.python.org/3/library/inspect.html
  _"Added in version 3.12."_
- `supported` FastAPI chọn chạy trên event loop hay threadpool theo def/async def
  > When you declare a *path operation function* with normal `def` instead of `async def`, it is run in an external threadpool that is then awaited, instead of being called directly (as it would block the server).  
  > — https://fastapi.tiangolo.com/async/

**Độ khó:** hard thật · hợp level middle, senior — Phải hiểu coroutine chưa chạy khi gọi và vai trò __wrapped__ với introspection của framework; vượt mức định nghĩa decorator.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Nguyên nhân + cách viết; code mẫu ngắn, ứng viên có thể mô tả bằng lời.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu decorator, closure, functools.wraps và sự khác nhau khi bọc hàm async.
- Ý bắt buộc: Gọi async def chỉ tạo coroutine; lỗi xảy ra khi await, ngoài try/except của wrapper sync; Wrapper là def nên iscoroutinefunction trả False, framework xử lý sai; Thiếu functools.wraps thì mất tên/doc/annotations; wraps thêm __wrapped__ để inspect.signature thấy chữ ký gốc; Rẽ nhánh: hàm async thì wrapper async def + await; backoff dùng asyncio.sleep
- Dấu hiệu trả lời sai: Dùng time.sleep trong wrapper async; Nghĩ functools.wraps làm wrapper thành coroutine function; Gọi asyncio.run trong wrapper để 'chạy' coroutine
- Câu hỏi nối tiếp: Đặt @retry bên trong hay bên ngoài @lru_cache thì hành vi khác nhau thế nào?

### de-qa-1060 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Decorator và context manager (`py.core.decorators-context`) · ~744 token · hard của topic: 2

**Câu hỏi:** Code review phát hiện một context manager viết bằng `@contextmanager` để giữ kết nối và lock: `yield` không nằm trong try/finally, có khối `except Exception: log(...)` không raise lại, và một hàm khác mở số lượng file/kết nối thay đổi theo input bằng các `with` lồng nhau viết tay. Phân tích các lỗi về ngữ nghĩa exception và giải phóng tài nguyên, và cách sửa.

**Kết luận:** Đúng theo tài liệu contextlib: exception được ném lại tại yield nên cần try/finally, bắt mà không raise lại thì with coi như đã xử lý, ExitStack cho số tài nguyên động. Phần bị cắt chỉ là các điểm tinh tế cuối.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | Chunk ~744 token, vượt 600. Phần bị cắt là cuối mục 4 (ContextDecorator, BaseException, lock) và 'Kiểm thử'; ba lỗi chính nằm trước điểm cắt. | Rút mục 4 còn 1–2 ý (single-use, BaseException) hoặc bỏ hẳn. |

**Kiểm chứng:**
- `supported` Exception trong khối with được ném lại vào generator tại yield; cần try/finally để dọn dẹp
  > If an unhandled exception occurs in the block, it is reraised inside the generator at the point where the yield occurred.  
  > — https://docs.python.org/3/library/contextlib.html
  _Câu tiếp theo: dùng try…except…finally "to trap the error (if any), or ensure that some cleanup takes place."_
- `supported` Bắt exception để log mà không raise lại thì with coi như đã xử lý và chạy tiếp
  > If an exception is trapped merely in order to log it or to perform some action (rather than to suppress it entirely), the generator must reraise that exception.  
  > — https://docs.python.org/3/library/contextlib.html
  _Nếu không: "execution will resume with the statement immediately following the `with` statement."_
- `supported` __exit__ trả giá trị truthy là suppress exception
  > By returning true values, these callbacks can suppress exceptions the same way context manager `__exit__()` methods can.  
  > — https://docs.python.org/3/library/contextlib.html
  _Từ mục ExitStack.push(); quy tắc gốc nằm ở language reference._
- `supported` ExitStack hỗ trợ số context manager thay đổi theo input; callback chạy theo thứ tự ngược
  > Each instance maintains a stack of registered callbacks that are called in reverse order when the instance is closed (either explicitly or implicitly at the end of a `with` statement).  
  > — https://docs.python.org/3/library/contextlib.html
  _Use case chính: "supporting a variable number of context managers and other cleanup operations in a single with statement."_
- `supported` pop_all() chuyển callback sang ExitStack mới mà không gọi chúng
  > Transfers the callback stack to a fresh `ExitStack` instance and returns it. No callbacks are invoked by this operation  
  > — https://docs.python.org/3/library/contextlib.html
- `supported` Context manager từ @contextmanager là single-use; dùng làm decorator thì mỗi lần gọi tạo generator mới
  > When used as a decorator, a new generator instance is implicitly created on each function call  
  > — https://docs.python.org/3/library/contextlib.html
  _Single-use: "Context managers created using @contextmanager are also single use context managers"._

**Độ khó:** hard thật · hợp level middle, senior — Đòi hỏi hiểu ngữ nghĩa exception của generator context manager và ExitStack; không phải câu định nghĩa with.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Phân tích lỗi + cách sửa cho ba lỗi cụ thể từ code review; ý chấm rõ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Viết context manager an toàn: luôn giải phóng tài nguyên và không nuốt lỗi.
- Ý bắt buộc: Exception trong with được ném lại tại yield; không có try/finally thì code dọn dẹp không chạy; except mà không raise lại là nuốt lỗi; with chạy tiếp như không có gì; __exit__ trả True nghĩa là suppress; mặc định trả None; Số tài nguyên động: ExitStack.enter_context, dọn theo thứ tự ngược kể cả khi lỗi giữa chừng; Bản async: AsyncExitStack, @asynccontextmanager
- Dấu hiệu trả lời sai: Đặt code dọn dẹp sau yield mà không có finally; Cho rằng log rồi bỏ qua exception là an toàn; Tự viết vòng lặp with lồng nhau cho N file
- Câu hỏi nối tiếp: Bạn viết test thế nào để chứng minh lock được nhả khi khối with ném exception?

### de-qa-1061 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Iterator và generator (`py.core.generators-iterators`) · ~695 token · hard của topic: 2

**Câu hỏi:** Một hàm generator mở cursor DB (hoặc file) bên trong `with` rồi `yield` từng dòng. Consumer thường `break` sớm hoặc chỉ gọi `next()` một lần, và trên production số kết nối/cursor đang mở tăng dần, nhất là khi generator được giữ trong object sống lâu hoặc nằm trong reference cycle. Giải thích vòng đời của generator, khi nào khối finally/with bên trong thực sự chạy, và cách thiết kế an toàn.

**Kết luận:** Đúng theo language reference và contextlib: generator giữ frame tại yield, finally chỉ chạy khi chạy hết, có exception hoặc close() (gọi lúc finalize), nên phải đóng tường minh bằng closing/aclosing. Chỉ có vấn đề nhỏ về độ dài.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | Chunk ~695 token, vượt 600. Phần bị cắt là ý 5 (GeneratorExit) và 'Giám sát'; vòng đời và 4 cách thiết kế chính nằm trước điểm cắt. Ý 5 (close() ném GeneratorExit, yield thêm thì RuntimeError) chưa trích được nguồn: phần expressions.html đọc được không có mô tả generator.close(); không phải ý chấm … | Bỏ ý 5 và rút 'Giám sát' còn 'bật ResourceWarning ở dev'. |
| minor | factual | 'cleanup phải chờ GC hoặc không bao giờ xảy ra' hơi mạnh: generator trong reference cycle vẫn được GC thu gom và finalize; chỉ không xảy ra nếu object giữ nó sống mãi. | Sửa thành: 'phải chờ GC, hoặc không xảy ra chừng nào object giữ generator còn sống'. |

**Kiểm chứng:**
- `supported` Generator dừng ở yield và giữ nguyên trạng thái cục bộ, kể cả khối try/with đang mở
  > By suspended, we mean that all local state is retained, including the current bindings of local variables, the instruction pointer, the internal evaluation stack, and the state of any exception handling.  
  > — https://docs.python.org/3/reference/expressions.html
- `supported` Không được resume thì close() được gọi khi generator bị finalize (refcount về 0 hoặc GC), cho finally chạy
  > If the generator is not resumed before it is finalized (by reaching a zero reference count or by being garbage collected), the generator-iterator's `close()` method will be called, allowing any pending `finally` clauses to execute.  
  > — https://docs.python.org/3/reference/expressions.html
- `supported` contextlib.closing đảm bảo close() được gọi khi thoát with, kể cả khi lỗi
  > Return a context manager that closes *thing* upon completion of the block.  
  > — https://docs.python.org/3/library/contextlib.html
  _Cùng mục: "Even if an error occurs, `page.close()` will be called when the `with` block is exited."_
- `supported` Async generator cần aclose() được await; contextlib.aclosing dọn dẹp khi thoát sớm bằng break hay exception
  > Significantly, `aclosing()` supports deterministic cleanup of async generators when they happen to exit early by `break` or an exception.  
  > — https://docs.python.org/3/library/contextlib.html
  _Reference: "the caller must explicitly close the async generator by calling `aclose()` method"._
- `supported` itertools.batched có từ Python 3.12
  > Added in version 3.12.  
  > — https://docs.python.org/3/library/itertools.html
  _Ghi chú phiên bản ở mục batched()._

**Độ khó:** hard thật · hợp level middle, senior — Phải hiểu finalization của generator, refcount vs GC và hệ quả trên tài nguyên thật; vượt mức biết yield.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Vòng đời/khi nào finally chạy là một ý, thiết kế an toàn là ý thứ hai; ý chấm rõ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu generator 'treo' ở yield cùng tài nguyên đang mở, và vì sao không được dựa vào GC để đóng kết nối.
- Ý bắt buộc: Generator dừng ở yield, giữ nguyên frame và with/try đang mở; finally/__exit__ bên trong chỉ chạy khi chạy hết, có exception, hoặc close(); close() tự động chỉ xảy ra khi finalize (refcount 0 hoặc GC): trễ hoặc không bao giờ nếu còn bị giữ; Đóng tường minh: contextlib.closing / aclosing, hoặc để caller sở hữu cursor/connection; Đọc theo lô (fetchmany, batched) để rút ngắn thời gian giữ tài nguyên
- Dấu hiệu trả lời sai: Nghĩ break khỏi vòng for sẽ chạy ngay finally trong generator trong mọi trường hợp; Dựa vào __del__ hoặc GC để đóng kết nối; Không biết async generator cần aclose()
- Câu hỏi nối tiếp: Với async generator trong FastAPI StreamingResponse, client ngắt kết nối giữa chừng thì bạn đảm bảo cursor được đóng thế nào?

### de-qa-1062 · Đạt · tin cậy high · Phải đọc

**Topic:** Iterator và generator (`py.core.generators-iterators`) · ~700 token · hard của topic: 2

**Câu hỏi:** Một pipeline ETL viết bằng chuỗi generator và generator expression để xử lý file vài chục GB. Team gặp các lỗi khó hiểu: bước thống kê thứ hai luôn ra kết quả rỗng, `itertools.tee` làm RAM tăng vọt, lỗi dữ liệu nổ ở chỗ tiêu thụ thay vì chỗ khai báo, và một generator expression dùng biến bị gán lại sau đó cho kết quả bất ngờ. Giải thích và đưa ra nguyên tắc thiết kế.

**Kết luận:** Đạt theo rubric v2: câu hỏi có 2 ý độc lập, trả lời các ý bắt buộc trong khoảng 5 phút; các claim chính đều có trích dẫn. (v1 gợi ý Cần sửa vì đếm 5 ý.)

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | interview_fit | Rubric v2: 2 ý độc lập, ~5 phút cho các ý bắt buộc (bốn triệu chứng có hai cơ chế gốc: iterator một lượt (cạn, tee đệm) và đánh giá lười (lỗi nổ muộn, late binding)); v1 đếm 5 ý. Còn lại là gợi ý: Câu hỏi gói 4 hiện tượng độc lập (iterator cạn, tee tốn RAM, lỗi nổ muộn, late binding) cộng nguyên tắ… | Giữ 2 hiện tượng có giá trị nhất (thống kê lần hai ra rỗng + tee tốn RAM) và hỏi cách thiết kế pipeline duyệt một lượt; chuyển 'lỗi nổ muộn/late binding' thành follow-up. |
| minor | length | Chunk ~700 token, vượt 600. Phần bị cắt là phần lớn 'Nguyên tắc thiết kế pipeline' (islice, batched, checkpoint). | Khi thu hẹp câu hỏi, bỏ ý 3–4 trong đáp án sẽ đủ chỗ cho nguyên tắc thiết kế. |

**Kiểm chứng:**
- `supported` Generator là iterator, duyệt lần hai trên cùng object ra rỗng
  > All other expressions are evaluated lazily, in the same fashion as normal generators (that is, when the iterator is asked to yield a value):  
  > — https://docs.python.org/3/reference/expressions.html
  _Câu này ủng hộ tính lười; việc iterator cạn sau một lượt là hành vi chuẩn của iterator protocol, trang không có câu riêng trong phần đọc được._
- `supported` tee cần bộ nhớ phụ lớn; nếu một nhánh đọc gần hết trước nhánh kia thì dùng list() nhanh hơn **(quote không có nguyên văn trên trang nguồn)**
  > In general, if one iterator uses most or all of the data before another iterator starts, it is faster to use list instead of tee().  
  > — https://docs.python.org/3/library/itertools.html
  _Cùng mục: "This itertool may require significant auxiliary storage"._
- `supported` Iterator từ tee không thread-safe
  > `tee` iterators are not threadsafe.  
  > — https://docs.python.org/3/library/itertools.html
- `supported` Generator expression: iterable của for ngoài cùng đánh giá ngay, phần còn lại đánh giá lười
  > The iterable expression in the leftmost `for` clause is evaluated immediately, so that an error raised by this expression will be emitted at the point where the generator expression is defined, rather than at the point where the first value is retrieved:  
  > — https://docs.python.org/3/reference/expressions.html
  _Từ đó suy ra late binding của biến tự do (ý 4)._
- `supported` islice tiêu thụ luôn phần bị bỏ qua của iterator gốc
  > If the input is an iterator, then fully consuming the *islice* advances the input iterator by `max(start, stop)` steps regardless of the *step* value.  
  > — https://docs.python.org/3/library/itertools.html
- `supported` itertools.batched có từ 3.12
  > Added in version 3.12.  
  > — https://docs.python.org/3/library/itertools.html

**Độ khó:** hard thật · hợp level middle, senior — Các lỗi thực tế của pipeline lười, cần hiểu iterator protocol và tee; không phải định nghĩa generator.
**Dùng trong phỏng vấn:** ~5 phút, 2 ý hỏi, chấm được — Rubric v2: bốn triệu chứng có hai cơ chế gốc: iterator một lượt (cạn, tee đệm) và đánh giá lười (lỗi nổ muộn, late binding). Mỗi hiện tượng chấm được, nhưng tổng cộng quá nhiều cho một câu.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu iterator chỉ duyệt được một lần, chi phí bộ nhớ của tee và tính lười của generator.
- Ý bắt buộc: Generator duyệt hết là cạn; lần hai ra rỗng không báo lỗi; gọi lại hàm generator hoặc gom thống kê vào một lượt; tee đệm phần nhánh chậm chưa đọc; nhánh này đọc hết trước thì gần như toàn bộ dữ liệu nằm trong RAM; Generator expression chỉ đánh giá ngay iterable ngoài cùng; phần còn lại lười nên lỗi nổ ở chỗ tiêu thụ và biến bị đọc lúc tiêu thụ; Pipeline: mỗi bước nhận iterable trả iterator, không bước nào gom toàn bộ (sorted, list)
- Dấu hiệu trả lời sai: Dùng list() cho file vài chục GB để 'duyệt nhiều lần'; Nghĩ tee sao chép nguồn mà không tốn bộ nhớ; Không biết vì sao lần duyệt thứ hai ra rỗng
- Câu hỏi nối tiếp: Generator expression dùng biến bị gán lại trước khi tiêu thụ cho kết quả gì, và bạn cố định giá trị thế nào?

### de-qa-1063 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Type hint, dataclass và Pydantic (`py.core.typing-pydantic`) · ~734 token · hard của topic: 2

**Câu hỏi:** Một service dùng Pydantic v2 nhận dữ liệu từ đối tác. Sau một sự cố, team phát hiện chuỗi số tiền "100" được ép thành int mà không ai biết đối tác đã đổi định dạng, một validator kiểm tra định dạng chạy trước khi giá trị được chuẩn hóa nên đánh giá sai, và một developer dùng `model_construct()` cho dữ liệu từ API để tăng tốc. Phân tích và đề xuất cấu hình validation phù hợp.

**Kết luận:** Đúng theo tài liệu Pydantic v2: lax mode ép kiểu, strict mode và các mức bật, before/after/plain/wrap validator, model_construct chỉ cho dữ liệu đã validate. Phần bị cắt là mẹo tăng tốc cuối.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | Chunk ~734 token, vượt 600. Phần bị cắt là cuối đoạn model_construct (lưu ý hiệu năng) và 'Tăng tốc đúng cách' (model_validate_json, extra="forbid"); lax/strict, validator modes và cảnh báo model_construct nằm trước điểm cắt. | Bỏ các dòng wrap/model_validator và câu về JSON strict để giữ 'Tăng tốc đúng cách' trong snippet. |

**Kiểm chứng:**
- `supported` Mặc định (lax) Pydantic cố ép giá trị về kiểu khai báo
  > By default, Pydantic will attempt to coerce values to the desired type when possible.  
  > — https://pydantic.dev/docs/validation/latest/concepts/strict_mode/
- `supported` Strict mode báo lỗi thay vì ép; bật ở mức config, field, kiểu Strict hoặc từng lần gọi validate
  > Strict mode can be enabled on specific fields, by setting the strict parameter of the Field() function to True.  
  > — https://pydantic.dev/docs/validation/latest/concepts/strict_mode/
  _Trang cũng nêu mức config và "Strict mode can be enabled on a per-validation-call basis"._
- `supported` Với JSON, strict mode vẫn cho ngày giờ đi từ chuỗi
  > the date and time types allow strings even in strict mode  
  > — https://pydantic.dev/docs/validation/latest/concepts/strict_mode/
  _"strict mode is looser when validating from JSON."_
- `supported` after validator chạy sau validation nội bộ, an toàn kiểu hơn; before validator nhận dữ liệu thô
  > run after Pydantic’s internal validation. They are generally more type safe and thus easier to implement.  
  > — https://pydantic.dev/docs/validation/latest/concepts/validators/
  _Before: "they also have to deal with the raw input, which in theory could be any arbitrary object."_
- `supported` plain validator thay hẳn validation, Pydantic không kiểm tra kiểu nữa
  > so no further validators are called and Pydantic does not do any of its internal validation against the field type.  
  > — https://pydantic.dev/docs/validation/latest/concepts/validators/
- `supported` Không dùng assert trong validator vì bị bỏ qua khi chạy -O
  > be aware that these statements are skipped when Python is run with the -O optimization flag.  
  > — https://pydantic.dev/docs/validation/latest/concepts/validators/
- `supported` model_construct không validate, chỉ dùng cho dữ liệu đã validate; với model đơn giản validate có thể còn nhanh hơn
  > For simple models, going with validation may even be faster.  
  > — https://pydantic.dev/docs/validation/latest/concepts/models/
  _Caution: "You should only ever use the model_construct() method with data which has already been validated"; không chuyển dict lồng thành model con._
- `supported` model_validate_json thường nhanh hơn json.loads rồi model_validate
  > this is generally considered faster (instead of manually parsing the data as a dictionary).  
  > — https://pydantic.dev/docs/validation/latest/concepts/models/

**Độ khó:** hard thật · hợp level middle, senior — Ba lỗi thật về validation contract; cần hiểu coercion, thứ tự validator và đánh đổi hiệu năng.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Phân tích + đề xuất cấu hình cho ba lỗi; ý chấm rõ. Hơi thiên về API của Pydantic nhưng topic chính là Pydantic.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu Pydantic ép kiểu thế nào, khi nào nên strict, và chạy validator đúng thời điểm.
- Ý bắt buộc: Lax mode (mặc định) ép '100' thành 100, che lỗi đối tác; dùng strict cho contract giữa hệ thống; Bật strict ở model, field hoặc lúc gọi model_validate; số tiền dùng Decimal; Kiểm tra định dạng/nghiệp vụ trong after validator; before chỉ để chuẩn hóa dữ liệu thô; model_construct bỏ qua validation: chỉ cho dữ liệu đã validate/tin cậy; Tăng tốc đúng: model_validate_json, validate một lần ở biên; extra="forbid" để lộ field lạ
- Dấu hiệu trả lời sai: Dùng model_construct cho dữ liệu từ API để 'nhanh hơn'; Dùng float cho số tiền; Dùng assert trong validator
- Câu hỏi nối tiếp: Bật strict cho cả model thì những field nào từ JSON vẫn nhận chuỗi, và bạn xử lý Decimal thế nào?

### de-qa-1064 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Type hint, dataclass và Pydantic (`py.core.typing-pydantic`) · ~744 token · hard của topic: 2

**Câu hỏi:** Bạn thiết kế lớp abstraction cho storage (S3, local, GCS) trong codebase Python chạy mypy strict. Team tranh luận nên dùng ABC hay `typing.Protocol`; sau đó gặp lỗi mypy khi truyền `list[LocalStorage]` vào hàm nhận `list[Storage]`, và một kiểm tra `isinstance(obj, Storage)` với `@runtime_checkable` vẫn cho qua object có method sai chữ ký. Phân tích các đánh đổi và cách sửa.

**Kết luận:** Đúng theo typing spec và tài liệu mypy: Protocol là structural subtyping, list invariant nên dùng Sequence, variance tự suy với cú pháp 3.12, runtime_checkable chỉ kiểm tra sự tồn tại của member. Phần 'Khuyến nghị' bị cắt khỏi snippet.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | Chunk ~744 token, vượt 600. Phần bị cắt là câu issubclass và toàn bộ 'Khuyến nghị'; đánh đổi ABC/Protocol, variance và runtime_checkable nằm trước điểm cắt. | Bỏ câu về cú pháp 3.12/TypeVar cũ và câu issubclass để giữ 1–2 dòng khuyến nghị. |

**Kiểm chứng:**
- `supported` Protocol là structural: class có member tương thích là thỏa, không cần kế thừa
  > So while it's possible to subclass a protocol explicitly, it's *not necessary* to do so for the sake of type-checking.  
  > — https://typing.python.org/en/latest/spec/protocol.html
- `supported` Kế thừa Protocol tường minh để dùng default implementation và để type checker kiểm tra tại định nghĩa
  > In addition, type checkers can statically verify that the class actually implements the protocol correctly  
  > — https://typing.python.org/en/latest/spec/protocol.html
  _Cùng đoạn: "In this case a class could use default implementations of protocol members."_
- `supported` list là invariant (hàm có thể append phần tử kiểu khác vào list)
  > `list` is an invariant generic type.  
  > — https://mypy.readthedocs.io/en/stable/generics.html
  _Ví dụ trên trang: hàm nhận list[Shape] append Shape vào list[Circle]._
- `supported` Sequence covariant; Callable contravariant theo kiểu tham số
  > Most immutable container types, such as Sequence and frozenset are covariant.  
  > — https://mypy.readthedocs.io/en/stable/generics.html
  _"Callable is an example of type that behaves contravariant in types of arguments."_
- `supported` Cú pháp generic Python 3.12: variance được tự suy; attribute mutable public làm class invariant
  > When using the new syntax, the variance of class type variables is always inferred.  
  > — https://mypy.readthedocs.io/en/stable/generics.html
  _Cùng mục: "Without an underscore prefix, the class would be invariant" (attribute public, mutable)._
- `supported` isinstance với runtime_checkable protocol chỉ kiểm tra sự tồn tại member, không kiểm tra chữ ký
  > a simpler way to write `hasattr(x, '__iter__') and hasattr(x, '__next__')`.  
  > — https://typing.python.org/en/latest/spec/protocol.html
  _Spec mô tả check như hasattr, tức không xét chữ ký/kiểu. Trang docs.python.org/typing bị cắt trước mục runtime_checkable nên không lấy được câu nói thẳng._
- `supported` issubclass chỉ dùng được với protocol không có data member
  > `issubclass()` can be used only with non-data protocols.  
  > — https://typing.python.org/en/latest/spec/protocol.html

**Độ khó:** hard thật · hợp level middle, senior — Variance và giới hạn runtime_checkable là kiến thức type system sâu; middle thường chỉ biết Protocol là duck typing.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Đánh đổi + cách sửa cho hai lỗi cụ thể; ý chấm rõ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu nominal (ABC) vs structural (Protocol) typing, variance của generic và giới hạn của kiểm tra runtime.
- Ý bắt buộc: ABC: phải kế thừa, chặn khởi tạo khi thiếu method lúc runtime, chia sẻ code; Protocol: chỉ cần đúng hình dạng, giảm coupling, kiểm tra lúc type check; list invariant vì hàm có thể append kiểu khác; tham số chỉ đọc dùng Sequence/Iterable (covariant); runtime_checkable isinstance chỉ kiểm tra tên member tồn tại, không kiểm tra chữ ký
- Dấu hiệu trả lời sai: Nghĩ list[LocalStorage] đương nhiên là list[Storage]; Dùng runtime_checkable isinstance để validate plugin; Cho rằng Protocol được kiểm tra đầy đủ lúc runtime
- Câu hỏi nối tiếp: Vì sao Callable lại contravariant theo kiểu tham số? Cho một ví dụ.

### de-qa-1065 · Cần sửa · tin cậy low · Phải đọc

**Topic:** Đóng gói và triển khai ứng dụng Python (`py.ops.packaging-deployment`) · ~767 token · hard của topic: 2

**Câu hỏi:** Bạn triển khai API FastAPI lên Kubernetes với Dockerfile chạy gunicorn và Uvicorn worker, số worker tính bằng `2 * $(nproc) + 1`. Trên node 32 core, mỗi pod (CPU limit 2, memory limit 1Gi) sinh ra 65 worker và liên tục bị OOMKill; khi deploy thì một số request bị cắt ngang. Phân tích cách chọn số worker, cấu hình gunicorn/uvicorn và health check cho môi trường container.

**Kết luận:** Phần gunicorn/uvicorn đúng theo tài liệu chính thức. Cần sửa vì phần health check (được hỏi trực tiếp) nằm hoàn toàn trong đoạn bị cắt ở 600 token, và claim 'nproc trả số CPU của node' chưa kiểm chứng được, có thể phụ thuộc phiên bản.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| major | length | Chunk ~767 token, vượt 600. Đoạn 'Health check' (liveness không gọi DB, readiness fail khi shutdown) nằm hoàn toàn trong phần bị cắt, trong khi câu hỏi hỏi trực tiếp về health check. | Bỏ các ý max_requests, preload_app, proxy headers (không liên quan triệu chứng) và chuyển 'Health check' lên ngay sau ý graceful_timeout. |
| major | factual | Claim 'nproc trả số CPU của node chứ không phải CPU limit' là nguyên nhân chính của 65 worker nhưng chưa tìm được nguồn; hành vi của nproc với cgroup CPU quota có thể khác theo phiên bản coreutils. | Viết lại: 'nproc đếm CPU process được phép chạy (affinity/cpuset), thường không phản ánh CPU limit kiểu quota của Kubernetes, nên trên node 32 core dễ ra 65 worker; đặt số worker tường minh thay vì suy từ nproc.' |
| minor | factual | 'uvicorn dùng spawn, không pre-fork' chưa trích được nguyên văn (câu trên trang dài hơn giới hạn trích của công cụ). | Giữ nếu người duyệt xác nhận trên trang uvicorn deployment. |

**Kiểm chứng:**
- `unverified` nproc trong container thường trả số CPU của node, không theo CPU limit
  _Manual coreutils chỉ nói nproc in "the number of processing units available to the current process", không nhắc cgroup/CPU quota. Hành vi với cgroup quota có thể khác giữa các phiên bản coreutils; cần người duyệt xác nhận._
- `supported` (2 × core) + 1 chỉ là điểm xuất phát, chỉnh theo tải; worker ≠ client; 4–12 worker là đủ cho tải lớn; quá nhiều worker giảm throughput
  > Gunicorn typically needs only **4–12 workers** to handle heavy traffic.  
  > — https://gunicorn.org/design/
  _Cùng trang: "Workers ≠ clients.", "Too many workers waste resources and can reduce throughput.", "Start with this formula and adjust under load:"._
- `supported` uvicorn.workers đã deprecated, chuyển sang package uvicorn-worker
  > The `uvicorn.workers` module is deprecated and will be removed in a future release.  
  > — https://uvicorn.dev/deployment/
  _"You should use the uvicorn-worker package instead."_
- `supported` timeout mặc định 30 giây: worker im lặng quá ngưỡng bị kill và restart
  > Workers silent for more than this many seconds are killed and restarted.  
  > — https://gunicorn.org/reference/settings/
  _Default 30._
- `supported` graceful_timeout (mặc định 30 giây): thời gian worker được phép xử lý xong request sau khi nhận tín hiệu restart
  > After receiving a restart signal, workers have this much time to finish serving requests.  
  > — https://gunicorn.org/reference/settings/
  _Quan hệ với terminationGracePeriodSeconds là suy luận hợp lý, không nằm trên trang gunicorn._
- `supported` max_requests hạn chế hậu quả memory leak; jitter tránh mọi worker restart cùng lúc
  > This is intended to stagger worker restarts to avoid all workers restarting at the same time.  
  > — https://gunicorn.org/reference/settings/
  _max_requests: "This is a simple method to help limit the damage of memory leaks."_
- `supported` Số worker đặt qua WEB_CONCURRENCY hoặc -w
  > By default, the value of the `WEB_CONCURRENCY` environment variable,  
  > — https://gunicorn.org/reference/settings/
  _Nếu không đặt thì mặc định 1._
- `supported` Proxy headers: chỉ tin IP của proxy (forwarded-allow-ips)
  > However as anyone can set these headers you must configure which "clients" you will trust to have set them correctly.  
  > — https://uvicorn.dev/deployment/

**Độ khó:** hard thật · hợp level middle, senior — Kết hợp worker model, giới hạn container và graceful shutdown; cần kinh nghiệm vận hành.
**Dùng trong phỏng vấn:** ~5 phút, 2 ý hỏi, chấm được — Hai triệu chứng (OOMKill, request bị cắt khi deploy) và ba chủ đề cần nêu, vẫn trong 5 phút nếu tập trung.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu cách tính số worker trong container và graceful shutdown khi deploy trên Kubernetes.
- Ý bắt buộc: Mỗi worker là một process có bộ nhớ riêng; 65 worker vượt 1Gi; Số worker tính theo CPU limit, đặt tường minh (WEB_CONCURRENCY/-w); worker async chỉ cần 1–2 mỗi core, hoặc 1 process/pod + scale ngang; Request bị cắt: graceful_timeout < terminationGracePeriodSeconds, readiness fail sớm/preStop để ngừng nhận traffic trước; Liveness chỉ kiểm tra process, readiness kiểm tra phụ thuộc thiết yếu
- Dấu hiệu trả lời sai: Tăng memory limit để chứa 65 worker; Liveness probe gọi DB; Nghĩ công thức (2 × core) + 1 là bắt buộc
- Câu hỏi nối tiếp: Khi pod nhận SIGTERM, thứ tự sự kiện giữa endpoint bị gỡ khỏi Service và worker dừng là gì?

**Đề xuất sửa:**
- Đáp án: (1) Sửa câu về nproc như trong issue. (2) Bỏ max_requests, preload_app, proxy headers; đưa đoạn Health check lên trước để không bị cắt ở 600 token.

### de-qa-1066 · Đạt · tin cậy high · Phải đọc

**Topic:** Đóng gói và triển khai ứng dụng Python (`py.ops.packaging-deployment`) · ~716 token · hard của topic: 2

**Câu hỏi:** Image Docker của một service Python build hôm nay khác hôm qua dù code không đổi: một dependency bắc cầu lên phiên bản mới gây lỗi production, image nặng gần 1GB vì chứa cả compiler, và đội security yêu cầu chứng minh các package được cài đúng là bản đã duyệt. Thiết kế quy trình quản lý dependency và Dockerfile để build tái lập, gọn và an toàn.

**Kết luận:** Đúng theo tài liệu pip và Docker: lock ghim cả dependency bắc cầu bằng ==, hash-checking mode tự bật khi có một hash, --require-hashes, --no-deps, multi-stage build. Chỉ có vấn đề nhỏ về độ dài.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | Chunk ~716 token, vượt 600. Phần bị cắt là non-root, 'Chuỗi cung ứng' (SBOM, quét lỗ hổng) và 'Đánh đổi'; lock, hash và multi-stage nằm trước điểm cắt. | Rút đoạn 'Nguyên nhân' và gộp 'Chuỗi cung ứng' + 'Đánh đổi' thành một câu. |

**Kiểm chứng:**
- `supported` Ghim mọi dependency kể cả bắc cầu bằng == để build tái lập
  > This would pin not only the top-level packages, but also all of their transitive dependencies.  
  > — https://pip.pypa.io/en/stable/topics/repeatable-installs/
- `supported` Chỉ cần một requirement có hash là pip bắt buộc hash cho mọi requirement
  > By default, when at least one requirement has hashes, hashes become required for all requirements.  
  > — https://pip.pypa.io/en/stable/topics/secure-installs/
  _Cùng trang: "Hashes are required for all dependencies." và requirement phải được ghim (==, URL hoặc path)._
- `supported` Hash chống package bị thay nội dung
  > This mode uses local hashes, embedded in a requirements.txt file, to protect against remote tampering and network issues.  
  > — https://pip.pypa.io/en/stable/topics/secure-installs/
- `supported` --require-hashes ép bật hash-checking mode
  > It is possible to force the hash checking mode to be enabled, by passing `--require-hashes` command-line option.  
  > — https://pip.pypa.io/en/stable/topics/secure-installs/
- `supported` --only-binary :all: để không dùng sdist **(quote không có nguyên văn trên trang nguồn)**
  > Disallow source distributions, by passing `--only-binary :all:`.  
  > — https://pip.pypa.io/en/stable/topics/secure-installs/
  _Lý do 'không chạy code build của sdist' là suy luận, trang không nói thẳng._
- `supported` pip install --no-deps để không cài thứ ngoài lock
  > Performing the installation using --no-deps would provide an extra dose of insurance  
  > — https://pip.pypa.io/en/stable/topics/repeatable-installs/
  _Câu tiếp: "against installing anything not explicitly listed."_
- `supported` Multi-stage: chỉ copy artifact cần thiết sang stage cuối, image nhỏ hơn
  > You can selectively copy artifacts from one stage to another, leaving behind everything you don't want in the final image.  
  > — https://docs.docker.com/build/building/multi-stage/

**Độ khó:** hard thật · hợp level middle, senior — Gộp build tái lập, supply chain và tối ưu image; cần hiểu dependency bắc cầu và cơ chế hash của pip.
**Dùng trong phỏng vấn:** ~5 phút, 1 ý hỏi, chấm được — Một yêu cầu thiết kế cho ba vấn đề; ý chấm rõ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Biết vì sao build Python không tái lập và cách khóa dependency, kiểm tra hash, làm image gọn.
- Ý bắt buộc: requirements chỉ ghi dependency trực tiếp hoặc >= nên mỗi build resolve lại bản bắc cầu mới; File lock (pip-tools, uv, Poetry) ghim mọi package kể cả bắc cầu bằng ==, commit vào repo; Hash cho từng package (--require-hashes) để chứng minh đúng bản đã duyệt; Multi-stage: compiler chỉ ở stage build, stage runtime slim chỉ copy venv/wheel; Ghim base image theo digest, chạy non-root
- Dấu hiệu trả lời sai: Chỉ ghim dependency trực tiếp; Dùng tag base image trôi như python:3.12 và nghĩ build tái lập; Xóa compiler bằng apt remove trong cùng image thay vì multi-stage
- Câu hỏi nối tiếp: Lock chặt thì bạn cập nhật bản vá bảo mật thế nào mà không làm vỡ production?

### de-qa-1067 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Kiểm thử với pytest (`py.test.pytest-fixtures`) · ~715 token · hard của topic: 2

**Câu hỏi:** Bộ test pytest cho một service dùng PostgreSQL mất 25 phút vì mỗi test tạo lại schema. Khi chuyển engine sang fixture scope session và chạy song song bằng pytest-xdist, test bắt đầu fail ngẫu nhiên do dữ liệu của test này lọt sang test khác. Thiết kế lại hệ thống fixture: scope, teardown và cô lập dữ liệu khi chạy song song.

**Kết luận:** Đúng theo tài liệu pytest, pytest-xdist và SQLAlchemy: scope rộng cho thứ đắt, transaction rollback theo test với savepoint, teardown bằng yield theo thứ tự ngược, mỗi worker xdist chạy fixture session riêng nên cần cô lập theo worker. Chỉ có vấn đề nhỏ.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | Chunk ~715 token, vượt 600. Phần bị cắt là cuối ý 5 và 'Bẫy thường gặp'; các ý scope, rollback, teardown và xdist nằm trước điểm cắt. | Bỏ đoạn 'Bẫy thường gặp' hoặc rút còn câu --durations. |

**Kiểm chứng:**
- `supported` Fixture được dùng fixture scope rộng hơn hoặc bằng, không làm ngược lại
  > it is fine for fixtures to use “broader” scoped fixtures but not the other way round:  
  > — https://docs.pytest.org/en/stable/how-to/fixtures.html
- `supported` Teardown đặt sau yield, chạy theo thứ tự ngược với setup
  > Once the test is finished, pytest will go back down the list of fixtures, but in the reverse order  
  > — https://docs.pytest.org/en/stable/how-to/fixtures.html
  _"Any teardown code for that fixture is placed after the yield."_
- `supported` Mỗi fixture chỉ làm một thay đổi trạng thái kèm teardown riêng
  > The safest and simplest fixture structure requires limiting fixtures to only making one state-changing action each  
  > — https://docs.pytest.org/en/stable/how-to/fixtures.html
- `supported` Transaction bao ngoài + savepoint, rollback ở teardown để xóa sạch dữ liệu test
  > When the test tears down, the external transaction is rolled back so that any data changes throughout the test are reverted  
  > — https://docs.sqlalchemy.org/en/20/orm/session_transaction.html
  _Mục 'Joining a Session into an External Transaction (such as for test suites)', join_transaction_mode="create_savepoint"._
- `supported` Mỗi worker xdist là process riêng, fixture session chạy nhiều lần; dùng lock file để chỉ làm một lần
  > `pytest-xdist` is designed so that each worker process will perform its own collection and execute a subset of all tests.  
  > — https://pytest-xdist.readthedocs.io/en/stable/how-to.html
  _Cùng trang: "this can be achieved by using a lock file for inter-process communication."_
- `supported` worker_id cho biết tên worker (gw0, gw1...) để tách tài nguyên theo worker
  > The name of the worker, e.g., `"gw2"`.  
  > — https://pytest-xdist.readthedocs.io/en/stable/how-to.html
  _Trang có ví dụ "use a different account in each xdist worker"; DB riêng mỗi worker là áp dụng cùng ý, trang không nêu thẳng._

**Độ khó:** hard thật · hợp level middle, senior — Phải kết hợp scope, cô lập transaction và mô hình process của xdist; vượt mức biết viết fixture.
**Dùng trong phỏng vấn:** ~5 phút, 1 ý hỏi, chấm được — Một yêu cầu thiết kế lại với ba khía cạnh nêu rõ; ý chấm rõ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Thiết kế fixture pytest nhanh mà vẫn cô lập dữ liệu, kể cả khi chạy song song.
- Ý bắt buộc: Scope session cho DB/engine/migration (đắt, không đổi trạng thái); scope function cho transaction/dữ liệu; Mỗi test bọc trong transaction và rollback ở teardown; code có commit thì dùng savepoint; Teardown sau yield, chạy ngược thứ tự setup; mỗi fixture một thay đổi trạng thái; xdist: mỗi worker là process riêng chạy fixture session riêng; tách DB/schema theo worker_id, việc chỉ làm một lần dùng FileLock
- Dấu hiệu trả lời sai: Fixture session tạo dữ liệu dùng chung mà test sửa được; Nghĩ fixture session chạy đúng một lần khi dùng xdist; Dọn dữ liệu bằng DELETE thủ công cuối test
- Câu hỏi nối tiếp: Test cần nhiều connection thấy dữ liệu đã commit (vd test worker Celery) thì bạn cô lập thế nào?

### de-qa-1068 · Cần sửa · tin cậy high · Phải đọc

**Topic:** Kiểm thử với pytest (`py.test.pytest-fixtures`) · ~736 token · hard của topic: 2

**Câu hỏi:** Một test dùng `@patch('app.payments.stripe_client.charge')` nhưng vẫn gọi API thật; test khác mock `send_email` và pass, trong khi production lỗi vì hàm thật đã đổi chữ ký; còn mock cho hàm async thì `await` báo lỗi. Giải thích nguyên tắc patch đúng chỗ, autospec, mock hàm async, và khi nào nên tránh mock.

**Kết luận:** Nội dung đúng theo tài liệu unittest.mock (patch nơi tra cứu tên, autospec, patch tự dùng AsyncMock). Cần sửa vì câu hỏi yêu cầu 4 chủ đề riêng (patch đúng chỗ, autospec, mock async, khi nào tránh mock), quá rộng cho 3–5 phút.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| major | interview_fit | Rubric v2 vẫn tính là quá rộng (3 ý độc lập, ~6 phút): ba triệu chứng có ba cơ chế khác nhau: patch nơi tra cứu tên, autospec, AsyncMock. Câu hỏi nêu 3 triệu chứng và yêu cầu giải thích 4 chủ đề riêng: 4 yêu cầu, quá rộng cho 3–5 phút. | Thu hẹp còn hai triệu chứng đầu (patch không ăn, test pass dù chữ ký đổi) và hỏi 'vì sao và sửa thế nào'; chuyển mock async và 'khi nào tránh mock' thành follow-up. |
| minor | length | Chunk ~736 token, vượt 600. Phần bị cắt là cuối ý 4 và ý 5 (fixture monkeypatch/mocker, contract test). | Khi thu hẹp câu hỏi, bỏ ý 3–5 khỏi đáp án hoặc rút mỗi ý còn một câu. |

**Kiểm chứng:**
- `supported` Patch nơi tên được tra cứu, không phải nơi định nghĩa
  > The basic principle is that you patch where an object is *looked up*, which is not necessarily the same place as where it is defined.  
  > — https://docs.python.org/3/library/unittest.mock.html
- `supported` Mock tạo attribute khi được truy cập và chấp nhận đối số tùy ý
  > Mock objects create attributes on demand. This allows them to pretend to be objects of any type.  
  > — https://docs.python.org/3/library/unittest.mock.html
- `supported` autospec: mock có đúng chữ ký, gọi sai đối số ném TypeError
  > Methods and functions being mocked will have their arguments checked and will raise a TypeError if they are called with the wrong signature.  
  > — https://docs.python.org/3/library/unittest.mock.html
- `supported` Không truyền new thì patch tự dùng AsyncMock cho async function
  > If *new* is omitted, then the target is replaced with an AsyncMock if the patched object is an async function or a MagicMock otherwise.  
  > — https://docs.python.org/3/library/unittest.mock.html
  _Từ Python 3.8._
- `unverified` Mock ở ranh giới hệ thống, tránh mock thứ mình sở hữu và rẻ để chạy thật
  _Là khuyến nghị thực hành, không có trong tài liệu chính thức; không dùng làm điểm chấm cứng._

**Độ khó:** hard thật · hợp level middle, senior — Patch sai chỗ và mock không spec là lỗi thật, cần hiểu cách import gắn tên; không phải định nghĩa mock.
**Dùng trong phỏng vấn:** ~6 phút, 3 ý hỏi, chấm được — Rubric v2: ba triệu chứng có ba cơ chế khác nhau: patch nơi tra cứu tên, autospec, AsyncMock. Mỗi chủ đề chấm được nhưng tổng cộng quá nhiều.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu patch thay tên ở đâu, vì sao mock thường che lỗi chữ ký, và mock hàm async.
- Ý bắt buộc: from X import f tạo tên riêng trong module dùng; phải patch nơi tên được tra cứu (app.service.charge); Mock nhận mọi đối số/attribute nên test pass dù chữ ký thật đổi; autospec=True / create_autospec làm mock có đúng chữ ký, gọi sai ném TypeError; patch hàm async tự dùng AsyncMock; tự gán MagicMock thì không await được; Mock ở ranh giới hệ thống, patch qua fixture để tự hoàn tác
- Dấu hiệu trả lời sai: Patch nơi hàm được định nghĩa và không hiểu vì sao không ăn; Mock mọi thứ kể cả hàm thuần trong codebase; assert_called_with từng tham số thay vì kiểm tra kết quả
- Câu hỏi nối tiếp: Mock hàm async thì bạn kiểm tra nó đã được await bằng cách nào?

**Đề xuất sửa:**
- Câu hỏi mới: Một test dùng `@patch('app.payments.stripe_client.charge')` nhưng vẫn gọi API thật; test khác mock `send_email` và pass, trong khi production lỗi vì hàm thật đã đổi chữ ký. Giải thích nguyên nhân của từng lỗi và cách sửa.
- Đáp án: Giữ ý 1 và 2; rút ý 3 (AsyncMock) và ý 4–5 thành một câu hoặc chuyển sang follow-up.

### de-qa-1069 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Xác thực và phân quyền API (`py.web.api-auth`) · ~675 token · hard của topic: 2

**Câu hỏi:** Review module đăng nhập của một API Python: mật khẩu băm bằng SHA-256 có salt, token reset mật khẩu được so sánh bằng `==`, endpoint login trả về nhanh hơn rõ rệt khi email không tồn tại, và team muốn nâng tham số băm mà không bắt mọi người đặt lại mật khẩu. Phân tích rủi ro và đề xuất thiết kế.

**Kết luận:** Đúng theo OWASP Password Storage/Authentication Cheat Sheet và tài liệu hmac: Argon2id với tham số tối thiểu, rehash khi đăng nhập, compare_digest, chống user enumeration bằng thời gian phản hồi đồng đều. Câu hỏi gồm 4 vấn đề nên hơi dày.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | interview_fit | Câu hỏi gói 4 vấn đề (thuật toán băm, so sánh ==, user enumeration, nâng tham số). Mỗi ý có đáp án ngắn nên vẫn chấm được trong ~5 phút, nhưng sát giới hạn. | Có thể bỏ ý 'so sánh ==' khỏi câu hỏi và dùng làm follow-up nếu muốn gọn hơn. |
| minor | length | Chunk ~675 token, vượt 600. Phần bị cắt là cuối ý 5 (pepper, MFA, chạy hàm băm trên threadpool); 4 vấn đề chính nằm trước điểm cắt. | Rút danh sách tham số OWASP còn Argon2id + một dòng 'bcrypt cho hệ thống cũ'. |

**Kiểm chứng:**
- `supported` Salt chống rainbow table nhưng không làm hàm băm nhanh thành an toàn
  > Salting also protects against an attacker's pre-computing hashes using rainbow tables or database-based lookups.  
  > — https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
- `supported` Argon2id tối thiểu 19 MiB, 2 vòng, parallelism 1; scrypt khi không có Argon2id
  > Use Argon2id with a minimum configuration of 19 MiB of memory, an iteration count of 2, and 1 degree of parallelism.  
  > — https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
  _"scrypt should be used when the former is not available."_
- `supported` bcrypt chỉ cho hệ thống cũ, work factor tối thiểu 10, giới hạn 72 byte; pre-hash nguy hiểm
  > This can be dangerous because of null bytes in the hash output value and because of password shucking.  
  > — https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
  _Work factor: "with a minimum of 10."; "enforce a maximum password length of 72 bytes"._
- `supported` PBKDF2-HMAC-SHA256 600.000 vòng khi cần FIPS
  > PBKDF2-HMAC-SHA256: 600,000 iterations (recommended)  
  > — https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
- `supported` Nâng tham số bằng cách băm lại ở lần đăng nhập sau; user lâu không đăng nhập thì cho hash hết hạn
  > These hashes should be replaced with direct hashes of the users' passwords next time the user logs in.  
  > — https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
  _"Expire and delete the password hashes of users who have been inactive for an extended period"._
- `supported` hmac.compare_digest chống timing attack; có thể lộ độ dài nhưng không lộ nội dung
  > This function uses an approach designed to prevent timing analysis by avoiding content-based short circuiting behaviour, making it appropriate for cryptography.  
  > — https://docs.python.org/3/library/hmac.html
  _Note: khác độ dài có thể lộ "types and lengths of a and b—but not their values."_
- `supported` Chống user enumeration: thông báo lỗi chung và thời gian xử lý như nhau dù user không tồn tại
  > This code will go through the same process no matter what the user or the password is,  
  > — https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
  _Thông báo đúng: "Login failed; Invalid user ID or password."_

**Độ khó:** hard thật · hợp level middle, senior — Review bảo mật thực tế, cần biết vì sao hàm băm nhanh không đủ, timing attack và chiến lược rehash.
**Dùng trong phỏng vấn:** ~5 phút, 2 ý hỏi, chấm được — Phân tích + đề xuất cho 4 vấn đề trong kịch bản code review; ý chấm rõ, sát 5 phút.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu lưu mật khẩu an toàn và các lỗ rò thông tin nhỏ trong luồng đăng nhập.
- Ý bắt buộc: SHA-256 + salt quá nhanh, chỉ chống rainbow table; dùng Argon2id (hoặc scrypt/bcrypt/PBKDF2 theo ràng buộc); Hash lưu kèm thuật toán và tham số; băm lại khi user đăng nhập thành công; So sánh token bằng hmac.compare_digest; DB chỉ lưu hash của token reset, dùng một lần, hết hạn nhanh; Email không tồn tại vẫn chạy verify trên hash giả, thông báo lỗi chung; Rate limit theo IP và tài khoản
- Dấu hiệu trả lời sai: Nói thêm salt là đủ an toàn; Tự pre-hash rồi đưa vào bcrypt; Trả 'email không tồn tại' ở login hoặc quên mật khẩu
- Câu hỏi nối tiếp: Trong FastAPI async, hàm băm Argon2 tốn CPU ảnh hưởng event loop thế nào và bạn xử lý ra sao?

### de-qa-1070 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Xác thực và phân quyền API (`py.web.api-auth`) · ~731 token · hard của topic: 2

**Câu hỏi:** Pentest báo một API Django REST Framework cho phép người dùng đọc và sửa hóa đơn của người khác chỉ bằng cách đổi `id` trên URL, dù mọi view đều có `IsAuthenticated` và một permission class tự viết có `has_object_permission`. Giải thích vì sao lỗi BOLA vẫn xảy ra và thiết kế phân quyền mức object một cách có hệ thống.

**Kết luận:** Đúng theo tài liệu DRF và OWASP API Security 2023: has_object_permission chỉ chạy qua get_object(), list không kiểm tra từng object, create cần kiểm tra riêng; scoping queryset là hàng rào chính. Phần bị cắt là các lớp phòng thủ phụ.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | Chunk ~731 token, vượt 600. Phần bị cắt là cuối ý 4, ý 5 (test tự động A truy cập tài nguyên B) và ý 6; nguyên nhân và hàng rào chính (scoping queryset, object permission, owner từ request.user) nằm trước điểm cắt. | Rút phần 'Vì sao DRF vẫn lọt' (gộp ý list và action tùy chỉnh) để ý test tự động nằm trong 600 token. |

**Kiểm chứng:**
- `supported` BOLA là API1 của OWASP API Security Top 10 2023: server không kiểm tra quyền trên đúng object theo ID từ client
  > The checks should validate that the logged-in user has permissions to perform the requested action on the requested object.  
  > — https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization
  _Trang có tiêu đề "API1:2023 Broken Object Level Authorization"._
- `supported` has_object_permission chỉ chạy khi generic view gọi get_object()
  > Object level permissions are run by REST framework's generic views when `.get_object()` is called.  
  > — https://www.django-rest-framework.org/api-guide/permissions/
- `supported` Override get_object/view tự viết phải gọi check_object_permissions
  > then you'll need to explicitly call the `.check_object_permissions(request, obj)` method on the view  
  > — https://www.django-rest-framework.org/api-guide/permissions/
  _Đoạn trích là phần giữa câu._
- `supported` List không tự kiểm tra object permission cho từng phần tử, phải lọc queryset
  > For performance reasons the generic views will not automatically apply object level permissions to each instance  
  > — https://www.django-rest-framework.org/api-guide/permissions/
- `supported` has_object_permission chỉ chạy sau khi has_permission pass
  > The instance-level `has_object_permission` method will only be called if the view-level `has_permission` checks  
  > — https://www.django-rest-framework.org/api-guide/permissions/
  _Câu tiếp tục: "have already passed"._
- `supported` Create cần kiểm tra quyền trong serializer hoặc perform_create
  > In order to restrict object creation you need to implement the permission check either in your Serializer class  
  > — https://www.django-rest-framework.org/api-guide/permissions/
- `supported` UUID khó đoán giảm dò nhưng không thay kiểm tra quyền; so user id trong JWT chỉ bao một phần nhỏ
  > This approach could address only a small subset of cases.  
  > — https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization
  _"Prefer the use of random and unpredictable values as GUIDs for records' IDs."_

**Độ khó:** hard thật · hợp level middle, senior — Phải biết chi tiết luồng permission của DRF và thiết kế phòng thủ nhiều lớp; middle thường nghĩ IsAuthenticated là đủ.
**Dùng trong phỏng vấn:** ~5 phút, 2 ý hỏi, chấm được — Giải thích nguyên nhân + thiết kế; ý chấm rõ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu lỗi BOLA (đổi ID xem dữ liệu người khác) và cách DRF kiểm tra quyền mức object.
- Ý bắt buộc: IsAuthenticated chỉ kiểm tra đã đăng nhập, không kiểm tra quyền trên object; has_object_permission chỉ chạy qua get_object(); view tự viết, list, create, query trực tiếp đều bỏ qua; Hàng rào chính: get_queryset luôn lọc theo owner/tenant, ngoài phạm vi trả 404; Owner/org gán từ request.user, field read_only trong serializer; Test tự động: user A truy cập tài nguyên user B phải bị từ chối
- Dấu hiệu trả lời sai: Đổi ID sang UUID là đủ; Tin owner_id gửi trong payload; Nghĩ has_object_permission tự áp dụng cho list
- Câu hỏi nối tiếp: Với hệ thống multi-tenant, bạn đặt logic lọc tenant ở đâu để không view nào quên?

### de-qa-1071 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** GIL, threading, multiprocessing và asyncio (`py.core.gil-concurrency`) · ~667 token · hard của topic: 2

**Câu hỏi:** Một service Python xử lý tác vụ tính toán viết bằng Python thuần (CPU-bound) dùng ThreadPoolExecutor 8 thread trên máy 8 core, nhưng throughput gần như không tăng so với 1 thread. Giải thích nguyên nhân và so sánh các hướng khắc phục: multiprocessing, đẩy phần nặng xuống code native, và bản build free-threaded của CPython.

**Kết luận:** Đúng theo tài liệu Python: GIL chỉ cho một thread chạy bytecode, ProcessPoolExecutor né GIL nhưng phải pickle, extension nhả GIL khi tính toán nặng, free-threaded build có overhead và có thể bật lại GIL. Chỉ cần ghi rõ trạng thái free-threading theo phiên bản.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | outdated | Ý 3 ghi 'từ CPython 3.13' mà không nói 3.13 là thử nghiệm, 3.14 mới được hỗ trợ chính thức (PEP 779), vẫn là build tùy chọn. | Sửa thành: 'bản build free-threaded (thử nghiệm ở 3.13, hỗ trợ chính thức từ 3.14, vẫn là build tùy chọn, không mặc định)'. |
| minor | length | Chunk ~667 token, vượt 600. Chỉ mất cuối đoạn 'Cách chọn'; nguyên nhân và ba hướng khắc phục còn nguyên. | Bỏ câu về shared_memory để giữ trọn đoạn 'Cách chọn'. |
| minor | topic | Trùng một phần với de-qa-1052 (cùng topic, cùng ý thread vs process vs extension nhả GIL vs free-threaded). | Chấp nhận được vì 1052 nghiêng về asyncio; người duyệt cân nhắc giữ cả hai. |

**Kiểm chứng:**
- `supported` GIL chỉ cho một thread thực thi bytecode Python tại một thời điểm
  > The mechanism used by the CPython interpreter to assure that only one thread executes Python bytecode at a time.  
  > — https://docs.python.org/3/glossary.html
- `supported` Extension nhả GIL khi tính toán nặng (nén, hash); GIL luôn được nhả khi I/O
  > However, some extension modules, either standard or third-party, are designed so as to release the GIL when doing computationally intensive tasks such as compression or hashing. Also, the GIL is always released when doing I/O.  
  > — https://docs.python.org/3/glossary.html
- `supported` ProcessPoolExecutor né GIL nhưng chỉ chạy/trả object pickle được
  > `ProcessPoolExecutor` uses the multiprocessing module, which allows it to side-step the Global Interpreter Lock but also means that only picklable objects can be executed and returned.  
  > — https://docs.python.org/3/library/concurrent.futures.html
- `supported` Bản free-threaded từ 3.13; đơn luồng chậm hơn, tốn bộ nhớ hơn
  > The free-threaded build has additional overhead when executing Python code compared to the default GIL-enabled build.  
  > — https://docs.python.org/3/howto/free-threading-python.html
  _Cùng trang: "Starting with the 3.13 release, CPython has support for a build of Python called free threading"; "will typically use more memory". What's New 3.14: "PEP 779: Free-threaded Python is officially supported"._
- `supported` Extension chưa khai báo hỗ trợ free threading làm interpreter bật lại GIL
  > The GIL may also automatically be enabled when importing a C-API extension module that is not explicitly marked as supporting free threading.  
  > — https://docs.python.org/3/howto/free-threading-python.html
- `supported` Kiểm tra trạng thái bằng sys._is_gil_enabled()
  > The new sys._is_gil_enabled() function can be used to check whether the GIL is actually disabled in the running process.  
  > — https://docs.python.org/3/howto/free-threading-python.html

**Độ khó:** hard thật · hợp level middle, senior — Câu hỏi khá kinh điển, phần khó là so sánh trade-off và free-threaded build; middle trả lời được phần GIL.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Nguyên nhân + so sánh ba hướng; ý chấm rõ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu GIL ảnh hưởng thế nào tới thread với code CPU-bound và các cách tận dụng nhiều core.
- Ý bắt buộc: GIL: một thread chạy bytecode tại một thời điểm, nên thread không tăng tốc code CPU thuần Python; ProcessPoolExecutor: song song thật, đổi lại chi phí process, pickle và bộ nhớ; Code native nhả GIL (NumPy, hashlib): thread chạy song song được, cần kiểm chứng; Free-threaded build: build tùy chọn, đơn luồng chậm hơn, extension chưa hỗ trợ bật lại GIL, phải tự lo thread-safety; Profile trước khi chọn
- Dấu hiệu trả lời sai: Nói 'Python không chạy song song được' mà không có ngữ cảnh; Tăng số thread để tăng tốc CPU-bound; Nghĩ free-threaded là mặc định từ 3.13
- Câu hỏi nối tiếp: Nếu dữ liệu đầu vào là mảng NumPy vài GB thì bạn tránh chi phí pickle khi dùng process pool thế nào?

