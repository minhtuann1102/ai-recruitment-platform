# Báo cáo duyệt cặp Q&A — de-qa-1484..1488,de-qa-1518,de-qa-1563..1565,de-qa-1422..1424,de-qa-1322..1323 (2026-11-13 09:38)

> Báo cáo do Claude tạo bằng skill `interview-qa-review`: **chỉ là gợi ý kèm bằng chứng**. Các cặp này cũng do Claude viết, nên người reviewer (cùng họ model) có thể chung điểm mù. Quyết định và `reviewed_by` thuộc về người duyệt.

**14/14 cặp đã duyệt** · Đạt 13 · Cần sửa 1 · Bỏ 0 · tin cậy cao 13 / vừa 1 / thấp 0

**Phân loại cho người duyệt:** Phải đọc 1 · Chỉ hình thức 0 (câu hỏi quá rộng, quá dài: nội dung đúng) · Có thể chấp nhận 13

**Kiểm tra trích dẫn nguyên văn:** khớp 101 · không khớp 0 · không kiểm được từ máy này 0

## Cặp mồi (kiểm tra người reviewer)

| qa_id | Lỗi cài sẵn | Gợi ý nhận được | Bắt được? |
|---|---|---|---|
| de-qa-1690 | dns.lookup noi dung c-ares, khong chiem threadpool (sai: getaddrinfo tren threadpool) | Cần sửa: [critical] Đáp án nói dns.lookup() dùng c-ares và không chiếm threadpool. Sai: tài liệu Node.js ghi dns.lookup() là lời gọi getaddrinfo(3) … | có |

## Tổng hợp

| qa_id | Topic | Gợi ý | Tin cậy | Nhóm | Vấn đề chính | Token | Golden |
|---|---|---|---|---|---|---|---|
| de-qa-1322 | Event loop của Node.js | Đạt | high | Có thể chấp nhận | [minor] Câu trả lời không nói rõ một lệnh JSON.parse hoặc regex.exec là nguyên khối, không thể chia nhỏ tại chỗ: partitioning chỉ dùng được… | 409 |  |
| de-qa-1323 | TypeScript cho backend | Cần sửa | high | Phải đọc | [major] Câu hỏi gốc kiểm tra việc nhớ một đoạn wiki (interface phẳng, cache quan hệ kiểu) và tên hai cờ tsc (extendedDiagnostics, generateT… | 363 |  |
| de-qa-1422 | Microservices và khả năng chịu lỗi | Đạt | high | Có thể chấp nhận | [minor] Câu hỏi viết 'frontend, backend và API gateway đều retry ... khi gọi database' nhưng ba tầng này gọi nhau theo chuỗi chứ không cùng… | 422 |  |
| de-qa-1423 | Microservices và khả năng chịu lỗi | Đạt | high | Có thể chấp nhận | [minor] Câu hỏi có hai ý khá độc lập (cách bù trừ khi bước thất bại; vì sao saga có dirty read/lost update). Must-have cho cả hai khoảng 5 … | 481 |  |
| de-qa-1424 | Microservices và khả năng chịu lỗi | Đạt | medium | Có thể chấp nhận | [minor] Đáp án không nhắc thứ tự: catalog nêu rõ message phải được gửi theo đúng thứ tự giao dịch (E1 trước E2), một yêu cầu quan trọng của… | 353 |  |
| de-qa-1484 | Transformer và attention | Đạt | high | Có thể chấp nhận | [minor] Đáp án nói 'phần chi phí không giảm' là thời gian bậc hai, nhưng không nhắc KV cache khi serving context 128k vẫn lớn và FlashAtten… | 354 |  |
| de-qa-1485 | Transformer và attention | Đạt | high | Có thể chấp nhận | [minor] Chưa có công thức hoặc ví dụ số cho dung lượng cache (2 x layers x kv_heads x head_dim x seq x batch x byte); ứng viên senior thườn… | 355 |  |
| de-qa-1486 | Transformer và attention | Đạt | high | Có thể chấp nhận | [minor] Đáp án dừng ở ALiBi (2021) và Position Interpolation (2023). Thực tế các model hiện nay thường mở rộng context bằng các biến thể Ro… | 384 |  |
| de-qa-1487 | Context engineering và long context | Đạt | high | Có thể chấp nhận | [minor] Đáp án chỉ nói về cấu trúc prompt; các nguyên nhân hit thấp khác mà tài liệu Anthropic nêu ngay đầu trang như TTL (5 phút hoặc 1 gi… | 357 |  |
| de-qa-1488 | Đánh giá LLM và hallucination | Đạt | high | Có thể chấp nhận | [minor] Đáp án nói 'rất có thể nằm trong nhiễu' nhưng không tính cụ thể. Với điểm nhị phân (đúng/sai), chênh 49 so với 47 nghĩa là chênh rò… | 372 |  |
| de-qa-1518 | Docker image và container | Đạt | high | Có thể chấp nhận | [minor] Đáp án không nhắc rằng cách COPY token cũng để lại secret trong build cache và hiện ra trong docker history (ARG), điều tài liệu Do… | 346 |  |
| de-qa-1563 | Bảo mật frontend | Đạt | high | Có thể chấp nhận | [minor] Ý đầu của đáp án ('vô tình cho phép domain không an toàn') chép lại nguyên văn mức MDN nhưng không nêu cơ chế XSS qua script của do… | 331 |  |
| de-qa-1564 | Bảo mật frontend | Đạt | high | Có thể chấp nhận | [minor] Đáp án không nêu rằng SameSite=Lax vẫn cho phép điều hướng cấp cao nhất cross-site bằng method an toàn, và 'same-site' khác 'same-o… | 349 |  |
| de-qa-1565 | JavaScript core: scope, closure và this | Đạt | high | Có thể chấp nhận | [minor] Đáp án dài 441 token, gần nhất ngân sách Planner trong lô (600 token cho tối đa 3 snippet) dù chưa bị cắt. Ý (b) về sửa chính một p… | 441 |  |

## Ảnh hưởng nếu sửa hoặc bỏ

- de-qa-1323: bỏ thì topic còn < 2 cặp hard (SC-001)
- 0/14 cặp dài hơn 600 token: snippet của Planner sẽ bị cắt (—).

## Việc cho người duyệt

- **Phải đọc** (1): de-qa-1323. Sai kiến thức, lỗi thời, chưa kiểm chứng được, tin cậy thấp, hoặc trích dẫn không khớp nguyên văn. Đọc phần kiểm chứng; chỗ Claude bác bỏ chính nguồn mà cặp trích thì Claude cũng có thể sai.
- **Chỉ hình thức** (0): —. Nội dung đúng; vấn đề là câu hỏi quá rộng hoặc quá dài. Sửa hay giữ là lựa chọn của bạn.
- **Có thể chấp nhận** (13): de-qa-1322, de-qa-1422, de-qa-1423, de-qa-1424, de-qa-1484, de-qa-1485, de-qa-1486, de-qa-1487, de-qa-1488, de-qa-1518, de-qa-1563, de-qa-1564, de-qa-1565. Mọi ý đã có trích dẫn; chấp nhận dựa trên bằng chứng là quyết định của bạn.
- Có nhãn golden set (0): —. Sửa câu hỏi thì giữ các thuật ngữ chính.

## Chi tiết từng cặp

### de-qa-1322 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Event loop của Node.js (`node.core.event-loop`) · ~409 token · hard của topic: 4

**Câu hỏi:** Một endpoint parse JSON rất lớn hoặc chạy regex do người dùng nhập làm event loop của Node bị chặn, mọi route khác đứng theo. Nên partition hay offload sang worker, mỗi cách đánh đổi gì?

**Kết luận:** Đạt: mọi key point (event loop bị chặn, partitioning vs offloading, chi phí serialize, không tạo child process cho mỗi request) đều khớp tài liệu Node.js; chỉ thiếu một lưu ý nhỏ là JSON.parse/regex.exec là lệnh nguyên khối nên khó partition.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | factual | Câu trả lời không nói rõ một lệnh JSON.parse hoặc regex.exec là nguyên khối, không thể chia nhỏ tại chỗ: partitioning chỉ dùng được với parser dạng stream/async (JSONStream, Big-Friendly JSON mà chính guide nhắc) hoặc vòng lặp tự chia; còn ReDoS thì gốc rễ là sửa regex/giới hạn độ dài input. Ứng vi… | Thêm một dòng vào đáp án: JSON.parse và regex.exec không partition được nếu không đổi sang parser stream; với ReDoS nên giới hạn input, dùng regex an toàn (ví dụ RE2) và/hoặc chạy trong worker có thể terminate khi quá thời gian. |

**Kiểm chứng:**
- `supported` Node dùng ít thread phục vụ nhiều client; callback/task chạy lâu làm thread chứa nó bị blocked nên request khác phải chờ
  > If any callback or task takes a long time, the thread running it becomes blocked.  
  > — https://nodejs.org/en/learn/asynchronous-work/dont-block-the-event-loop
  _Cùng trang: Node.js uses a small number of threads to handle many clients._
- `supported` JSON.parse và JSON.stringify là O(n) nhưng với input lớn có thể rất lâu (JSON DoS)
  > While these are O(n) in the length of the input, for large n they can take surprisingly long.  
  > — https://nodejs.org/en/learn/asynchronous-work/dont-block-the-event-loop
- `supported` Regex có thể chạy thời gian mũ trên input độc (ReDoS) và chặn Event Loop
  > in some cases the regexp match might require an exponential number of trips through the input string  
  > — https://nodejs.org/en/learn/asynchronous-work/dont-block-the-event-loop
- `supported` Partitioning chạy trên Event Loop và nhường lượt cho sự kiện khác giữa các bước
  > You could partition your calculations so that each runs on the Event Loop but regularly yields (gives turns to) other pending events.  
  > — https://nodejs.org/en/learn/asynchronous-work/dont-block-the-event-loop
- `supported` Nhược điểm partitioning: chỉ dùng Event Loop nên không tận dụng nhiều core, không hợp việc phức tạp
  > If you need to do something more complex, partitioning is not a good option. This is because partitioning uses only the Event Loop, and you won't benefit from multiple cores almost certainly available on your machine.  
  > — https://nodejs.org/en/learn/asynchronous-work/dont-block-the-event-loop
- `supported` Nhược điểm offloading: chi phí giao tiếp, phải serialize/deserialize dữ liệu giữa Event Loop và worker
  > The downside of the offloading approach is that it incurs overhead in the form of communication costs.  
  > — https://nodejs.org/en/learn/asynchronous-work/dont-block-the-event-loop
  _Cùng trang: Instead, you have to serialize and deserialize any objects you wish to share._
- `supported` Không tạo child process cho mỗi request vì dễ thành fork bomb, nên dùng pool cố định
  > You should not simply create a Child Process for every client.  
  > — https://nodejs.org/en/learn/asynchronous-work/dont-block-the-event-loop
  _Câu kế tiếp trên trang: your server might become a fork bomb._
- `supported` Worker thread có thể chia sẻ bộ nhớ qua ArrayBuffer hoặc SharedArrayBuffer
  > Unlike child_process or cluster, worker_threads can share memory. They do so by transferring ArrayBuffer instances or sharing SharedArrayBuffer instances.  
  > — https://nodejs.org/api/worker_threads.html
  _Docs Node.js v26.13.1._

**Độ khó:** hard thật · hợp level middle, senior — Cần suy luận đánh đổi giữa hai chiến lược cho một sự cố cụ thể (event loop bị chặn); junior thường chỉ biết dùng async/await. Hard hợp lý cho topic có đủ mức.
**Dùng trong phỏng vấn:** ~4 phút, 1 ý hỏi, chấm được — Một yêu cầu (so sánh partition và offload cùng đánh đổi). Must-have gồm 4 điểm, khoảng 4 phút; đáp án 409 token, trong ngân sách Planner.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu Node chạy JavaScript trên ít thread nên một việc CPU nặng làm đứng cả server, và biết hai hướng xử lý cùng cái giá của từng hướng.
- Ý bắt buộc: Vì sao mọi route đứng: một callback chạy lâu chiếm Event Loop, các request khác không được phục vụ; JSON.parse lớn và regex ReDoS là hai nguồn điển hình.; Partitioning: chia việc thành các bước nhỏ, nhường lượt giữa các bước (ví dụ setImmediate); đơn giản, không tốn giao tiếp, nhưng vẫn chỉ dùng một core và không hợp việc phức tạp.; Offloading: đưa việc sang Worker Pool, worker thread hoặc child process; tận dụng nhiều core nhưng tốn chi phí serialize/deserialize dữ liệu.; Không tạo child process cho mỗi request; dùng pool kích thước cố định.
- Dấu hiệu trả lời sai: Cho rằng bọc code trong async/await hoặc Promise là đủ để hết chặn event loop.; Tạo một child process mới cho mỗi request.; Nói worker thread dùng chung object JS với luồng chính mà không tốn chi phí sao chép.
- Câu hỏi nối tiếp: Nếu vấn đề là một lần regex.exec duy nhất trên chuỗi do người dùng gửi thì partitioning có áp dụng được không, và bạn xử lý gốc rễ thế nào?

### de-qa-1323 · Cần sửa · tin cậy high · Phải đọc

**Topic:** TypeScript cho backend (`node.lang.typescript-types`) · ~363 token · hard của topic: 2

**Câu hỏi:** Backend TypeScript ghép model bằng nhiều intersection type (dấu &), editor và tsc chậm hẳn. Vì sao interface extends thường nhanh hơn intersection, và bạn tìm điểm nghẽn bằng gì?

**Kết luận:** Cần sửa: nội dung đúng và khớp wiki Performance của TypeScript, nhưng câu hỏi gốc chỉ ở mức medium (chấm việc nhớ một đoạn wiki và tên cờ tsc). Dùng bản viết lại thêm suy luận về xung đột thuộc tính và đánh đổi để giữ nhãn hard, kèm lưu ý phiên bản TypeScript.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| major | difficulty | Câu hỏi gốc kiểm tra việc nhớ một đoạn wiki (interface phẳng, cache quan hệ kiểu) và tên hai cờ tsc (extendedDiagnostics, generateTrace): recall mặc áo hard, và chi tiết nội bộ compiler cùng tên cờ là thứ được chấm, trái tiêu chí interview fit (không chấm vendor trivia, tên cờ). Phần suy luận về đá… | Dùng câu hỏi viết lại: yêu cầu so sánh interface extends và intersection về xung đột thuộc tính (lỗi khi khai báo vs never im lặng), hiệu năng và declaration merging, rồi cách đo trước khi refactor. Giữ nhãn hard cho bản viết lại. |
| minor | outdated | Đáp án không nêu phiên bản. Wiki hiện nói codebase đang port sang Go (TypeScript 7.0) và các kỹ thuật điều tra dùng với TypeScript 5.9/6.0, nên 'tsc --generateTrace' và hành vi checker cần gắn phiên bản để không thành sai khi chuyển sang native tsc. | Thêm cụm 'với tsc 5.x/6.0 (JS)' vào ý đo điểm nghẽn, và nói thêm rằng nên đo lại khi dùng trình biên dịch native. |
| minor | interview_fit | Đáp án có 5 gạch đầu dòng nhưng ý thứ hai (cache quan hệ kiểu) là chi tiết nội bộ trình biên dịch, khó chấm; điểm cần chấm nằm ở xung đột thuộc tính và cách đo. | Gộp ý cache vào ý đầu, giữ 4 điểm: khác biệt cấu trúc, xung đột thuộc tính, đánh đổi (declaration merging, không tuyệt đối), cách đo. |

**Kiểm chứng:**
- `supported` Interface extends tạo một object type phẳng duy nhất và phát hiện xung đột thuộc tính ngay khi khai báo
  > Interfaces create a single flat object type that detects property conflicts, which are usually important to resolve!  
  > — https://github.com/microsoft/TypeScript/wiki/Performance
- `supported` Intersection chỉ gộp thuộc tính đệ quy và có trường hợp cho kết quả never
  > Intersections on the other hand just recursively merge properties, and in some cases produce never.  
  > — https://github.com/microsoft/TypeScript/wiki/Performance
- `supported` Quan hệ giữa các interface được cache, còn intersection thì không được cache như một kiểu hoàn chỉnh
  > Type relationships between interfaces are also cached, as opposed to intersection types as a whole.  
  > — https://github.com/microsoft/TypeScript/wiki/Performance
- `supported` Khi kiểm tra với intersection đích, từng thành phần bị kiểm tra trước khi kiểm tra với kiểu đã làm phẳng
  > when checking against a target intersection type, every constituent is checked before checking against the  
  > — https://github.com/microsoft/TypeScript/wiki/Performance
  _Câu gốc kết thúc bằng: the effective/flattened type._
- `supported` Khuyến nghị interface extends thay cho intersection, nhưng không phải quy tắc tuyệt đối
  > Note that the following is not a bullet-proof set of rules. There may be exceptions to each rule depending on your codebase.  
  > — https://github.com/microsoft/TypeScript/wiki/Performance
  _Wiki sửa lần cuối ngày 20/02/2026; đầu trang nói codebase đang được port sang Go (TypeScript 7.0) và các mẹo trên dùng để điều tra với TypeScript 5.9/6.0._
- `supported` Interface có declaration merging nên khai báo trùng tên sẽ tự gộp
  > a type cannot be re-opened to add new properties vs an interface which is always extendable.  
  > — https://www.typescriptlang.org/docs/handbook/2/everyday-types.html
- `supported` Tìm điểm nghẽn bằng tsc --extendedDiagnostics
  > You can run TypeScript with --extendedDiagnostics to get a printout of where the compiler is spending its time.  
  > — https://github.com/microsoft/TypeScript/wiki/Performance
- `supported` Dùng --generateTrace rồi phân tích bằng @typescript/analyze-trace hoặc Chrome/Edge
  > --generateTrace will create an output file that can be analyzed by the @typescript/analyze-trace utility, or within Edge or Chrome.  
  > — https://github.com/microsoft/TypeScript/wiki/Performance
  _Wiki: TypeScript 4.1 trở lên có --generateTrace._

**Độ khó:** chưa đủ hard · hợp level middle — Như đang viết, đây là câu mức medium: nó chấm việc nhớ một đoạn wiki và tên cờ tsc (kiến thức hiếm nhưng là recall, không phải suy luận). Bản viết lại (thêm suy luận về never vs lỗi khai báo, declaration merging, đo trước khi sửa) đưa nó về hard hợp lý cho topic chỉ tới mức middle. Không nên chỉ đổi nhãn sang medium: topic hiện chỉ có 2 hard nên sẽ dưới ngưỡng SC-001; hãy dùng bản viết lại và giữ nhãn hard.
**Dùng trong phỏng vấn:** ~3 phút, 2 ý hỏi, chấm được — Hai ý liên kết (vì sao nhanh hơn, đo bằng gì) trong cùng một sự cố hiệu năng, khoảng 3 phút. Chấm được vì có 4 điểm rõ. Chunk 363 token, trong ngân sách.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu interface extends và type intersection (&) khác nhau thế nào khi ghép kiểu, và biết đo trước khi tối ưu hiệu năng trình biên dịch.
- Ý bắt buộc: Interface extends tạo một object type phẳng và báo lỗi ngay khi hai thuộc tính xung đột; intersection chỉ gộp, có thể ra never mà không báo ở chỗ khai báo.; Trình biên dịch cache quan hệ giữa các interface, còn intersection bị kiểm tra từng thành phần rồi mới kiểm tra kiểu phẳng, nên intersection lồng nhiều làm chậm.; Đây là lời khuyên, không phải luật tuyệt đối; interface còn có declaration merging nên khai báo trùng tên sẽ gộp.; Đo trước khi sửa: tsc --extendedDiagnostics, nếu chưa đủ thì --generateTrace rồi phân tích trace (analyze-trace, Chrome/Edge).
- Dấu hiệu trả lời sai: Nói interface và type hoàn toàn giống nhau, không có khác biệt về hiệu năng hay xung đột.; Đổi hàng loạt sang interface mà không đo bằng extendedDiagnostics hay trace.; Không biết intersection của hai thuộc tính trùng tên nhưng khác kiểu có thể thành never.
- Câu hỏi nối tiếp: Hai type A và B cùng có thuộc tính id nhưng kiểu khác nhau; A & B và interface C extends A, B khác nhau thế nào, và bạn muốn hành vi nào cho model backend?

**Đề xuất sửa:**
- Câu hỏi mới: Backend TypeScript ghép model bằng nhiều intersection (&), tsc và editor chậm hẳn. Interface extends khác intersection thế nào về xung đột thuộc tính và hiệu năng, và bạn đo điểm nghẽn ra sao?
- Đáp án: - Hai cách ghép type được compiler xử lý khác nhau. Interface extends tạo một object type phẳng duy nhất và phát hiện xung đột thuộc tính ngay khi khai báo (thường là điều cần giải quyết: hai thuộc tính trùng tên khác kiểu cho lỗi). Intersection chỉ gộp thuộc tính đệ quy, không báo lỗi ở chỗ khai báo và có trường hợp cho kết quả never.
- Về hiệu năng: quan hệ giữa các interface được cache, còn intersection thì không được cache như một kiểu hoàn chỉnh; khi kiểm tra với một intersection đích thì từng thành phần đều bị kiểm tra trước khi kiểm tra với kiểu đã làm phẳng. Vì vậy tài liệu của TypeScript khuyên dùng interface với extends thay cho type alias ghép bằng &.
- Đây không phải quy tắc tuyệt đối (còn tùy codebase): interface có declaration merging nên khai báo trùng tên sẽ tự gộp.
- Đo trước khi sửa (với tsc 5.x/6.0 viết bằng JS; đo lại nếu chuyển sang compiler native): chạy tsc --extendedDiagnostics để xem compiler tốn thời gian ở đâu (Check time, số Types). Nếu chưa đủ, dùng --generateTrace rồi phân tích file trace bằng @typescript/analyze-trace hoặc trong Chrome, Edge. Sửa theo số đo thay vì đoán.

### de-qa-1422 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Microservices và khả năng chịu lỗi (`java.arch.microservices-resilience`) · ~422 token · hard của topic: 6

**Câu hỏi:** Frontend, backend và API gateway đều retry tối đa 3 lần khi gọi database đang quá tải thì chuyện gì xảy ra, và bạn thiết kế retry cùng timeout thế nào để không khuếch đại lỗi?

**Kết luận:** Đạt: phép tính 4^3 = 64 lần thử, randomized backoff, retry budget, trả mã quá tải và deadline propagation đều khớp SRE Book (Addressing Cascading Failures); chỉ có một chỗ diễn đạt tình huống hơi lỏng.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | interview_fit | Câu hỏi viết 'frontend, backend và API gateway đều retry ... khi gọi database' nhưng ba tầng này gọi nhau theo chuỗi chứ không cùng gọi database; ứng viên có thể hỏi lại hoặc hiểu là ba tầng gọi song song (khi đó không có phép nhân). | Làm rõ: 'frontend gọi gateway, gateway gọi backend, backend gọi database; mỗi tầng retry tối đa 3 lần khi lỗi'. Câu hỏi vẫn dưới 200 ký tự nếu rút gọn phần sau. |

**Kiểm chứng:**
- `supported` Retry ở nhiều tầng nhân lên: số lần thử của request cao nhất bằng tích số lần thử ở mọi tầng xuống tới database
  > a single request at the highest layer may produce a number of attempts as large as the product of the number of attempts at each layer to the lowest layer.  
  > — https://sre.google/sre-book/addressing-cascading-failures/
- `supported` Ba tầng mỗi tầng retry 3 lần (4 lần thử) cho 4^3 = 64 lần thử trên database
  > all issue 3 retries (4 attempts), then a single user action may create 64 attempts (4^3) on the database.  
  > — https://sre.google/sre-book/addressing-cascading-failures/
  _Sách nói backend, frontend và JavaScript layers; đáp án thay bằng frontend, backend, API gateway, cùng cấu trúc ba tầng._
- `supported` Dùng randomized exponential backoff (jitter) để retry không dồn thành đợt sóng đồng bộ
  > Always use randomized exponential backoff when scheduling retries.  
  > — https://sre.google/sre-book/addressing-cascading-failures/
- `supported` Giới hạn số retry mỗi request và đặt retry budget cho cả process; vượt budget thì trả lỗi ngay
  > only allow 60 retries per minute in a process, and if the retry budget is exceeded, don't retry; just fail the request.  
  > — https://sre.google/sre-book/addressing-cascading-failures/
  _Cùng đoạn: Limit retries per request. Don't retry a given request indefinitely._
- `supported` Không retry lỗi vĩnh viễn hay request sai; khi quá tải trả mã riêng để client và các tầng khác lùi lại
  > Return a specific status when overloaded so that clients and other layers back off and do not retry.  
  > — https://sre.google/sre-book/addressing-cascading-failures/
  _Cùng đoạn: Don't retry permanent errors or malformed requests in a client, because neither will ever succeed._
- `supported` Đặt deadline ở tầng cao và truyền xuống (deadline propagation), mọi RPC con dùng chung một deadline tuyệt đối
  > The tree of RPCs emanating from an initial request will all have the same absolute deadline.  
  > — https://sre.google/sre-book/addressing-cascading-failures/
  _Câu trước đó: With deadline propagation, a deadline is set high in the stack (e.g., in the frontend)._
- `supported` Khi quá tải phản hồi trễ hơn deadline của client; công việc server làm bị lãng phí và client retry làm tải tăng thêm
  > there's a good chance the user has given up and refreshed their browser, issuing another request: there's no point in responding to the first one, since it will be ignored!  
  > — https://sre.google/sre-book/addressing-cascading-failures/
  _Ngữ cảnh trích về load shedding; ý lãng phí công việc khi request đã quá hạn cũng nằm ở phần Deadline propagation cùng trang._

**Độ khó:** hard thật · hợp level middle, senior — Cần suy luận khuếch đại lỗi (tích số lần thử), cascading failure và thiết kế retry/timeout cùng nhau; một middle trả lời được phần backoff, senior mới nối được deadline propagation và retry budget.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Hai ý liên kết (hậu quả của retry nhiều tầng và cách thiết kế retry cùng timeout để tránh nó). Must-have 4 điểm, khoảng 4 phút. Chunk 422 token, trong ngân sách Planner.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu vì sao retry ở mọi tầng làm một hệ thống đang quá tải chết nhanh hơn, và biết các biện pháp chặn khuếch đại (một tầng retry, backoff, budget, deadline).
- Ý bắt buộc: Retry nhiều tầng nhân lên: 3 tầng, mỗi tầng 4 lần thử thì database nhận 4^3 = 64 lần thử cho một hành động người dùng, kéo dài sự cố (cascading failure).; Chỉ retry ở một tầng được chọn, các tầng khác fail fast; backoff lũy thừa có jitter, giới hạn retry mỗi request và retry budget cho cả process.; Không retry lỗi vĩnh viễn; khi server quá tải trả mã riêng để các tầng lùi lại thay vì retry.; Đặt deadline ở tầng cao và truyền xuống (deadline propagation) để mọi RPC con dùng chung deadline còn lại; tránh làm việc cho request mà client đã bỏ.
- Dấu hiệu trả lời sai: Cho rằng retry luôn an toàn vì 'thử lại cho chắc', không nhận ra khuếch đại tải.; Mỗi tầng tự đặt timeout cố định dài hơn thời gian còn lại của request gốc.; Retry ngay lập tức, không backoff hay jitter.
- Câu hỏi nối tiếp: Retry budget khác gì giới hạn 3 lần mỗi request, và bạn đặt nó ở client hay server?

### de-qa-1423 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Microservices và khả năng chịu lỗi (`java.arch.microservices-resilience`) · ~481 token · hard của topic: 6

**Câu hỏi:** Saga đặt hàng gồm giữ kho, trừ tiền, tạo vận đơn. Bước tạo vận đơn thất bại thì bù trừ thế nào, và vì sao saga có thể gây dirty read hay lost update?

**Kết luận:** Đạt: compensating transaction, phân loại compensable/pivot/retryable, saga thiếu isolation (lost update, dirty read) và hai biện pháp semantic lock, commutative updates đều khớp trang Saga của Azure Architecture Center; chỉ lưu ý câu hỏi có hai ý và vị trí pivot không được nêu trong đề.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | interview_fit | Câu hỏi có hai ý khá độc lập (cách bù trừ khi bước thất bại; vì sao saga có dirty read/lost update). Must-have cho cả hai khoảng 5 phút, sát ngưỡng. Đề cũng không nêu bước nào là pivot nên đáp án phải rẽ hai nhánh, ứng viên có thể thấy mơ hồ. | Giữ nguyên nếu người phỏng vấn dùng làm câu có hai phần; hoặc nêu rõ 'trừ tiền là pivot' trong đề, hoặc tách phần isolation thành câu follow-up. |
| minor | length | Đáp án 481 token, gần chạm ngân sách Planner (600) nếu Planner lấy thêm snippet khác, nhưng chưa bị cắt. | Có thể rút ý phân loại bước còn một câu ngắn nếu cần chỗ cho snippet khác. |

**Kiểm chứng:**
- `supported` Saga là chuỗi local transaction; khi một bước lỗi, saga chạy compensating transaction để đảo ngược các bước đã commit trước đó
  > If a local transaction fails, the saga performs a series of compensating transactions to reverse the changes that the preceding local transactions made.  
  > — https://learn.microsoft.com/en-us/azure/architecture/patterns/saga
- `supported` Compensation chạy theo thứ tự ngược với các bước đã làm
  > compensating actions run in reverse order to undo completed work  
  > — https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction
  _Nguồn là trang Compensating Transaction của Azure (trang Saga không nói rõ thứ tự ngược)._
- `supported` Pivot là điểm không quay lại; sau pivot, các bước phải đi tới cuối
  > Pivot transactions serve as the point of no return in the saga. After a pivot transaction succeeds, compensable transactions are no longer relevant.  
  > — https://learn.microsoft.com/en-us/azure/architecture/patterns/saga
- `supported` Retryable đứng sau pivot, idempotent, thử lại cho tới khi saga xong
  > Retryable transactions follow the pivot transaction. Retryable transactions are idempotent and help ensure that the saga can reach its final state, even if temporary failures occur.  
  > — https://learn.microsoft.com/en-us/azure/architecture/patterns/saga
- `supported` Compensation cũng có thể thất bại và làm hệ thống không nhất quán, nên phải idempotent, retry được và có giám sát
  > Compensating transactions might not always succeed, which can leave the system in an inconsistent state.  
  > — https://learn.microsoft.com/en-us/azure/architecture/patterns/saga
  _Trang Compensating Transaction: A step might run multiple times when retried, so design each step as an idempotent command._
- `supported` Mỗi service giữ dữ liệu riêng nên không có isolation giữa các saga, gây lost update và dirty read
  > Because each service manages its own data, called participant data, there's no built-in isolation across services.  
  > — https://learn.microsoft.com/en-us/azure/architecture/patterns/saga
  _Cùng trang: Lost updates và Dirty reads được liệt kê là các anomaly điển hình._
- `supported` Dirty read là đọc dữ liệu saga khác đã sửa nhưng chưa hoàn tất
  > Dirty reads: When a saga or transaction reads data that another saga has modified, but the modification isn't complete.  
  > — https://learn.microsoft.com/en-us/azure/architecture/patterns/saga
- `supported` Biện pháp: semantic lock (khóa mức ứng dụng) và commutative updates (áp dụng theo thứ tự nào cũng cùng kết quả)
  > Commutative updates: Design updates so that they can be applied in any order while still producing the same result.  
  > — https://learn.microsoft.com/en-us/azure/architecture/patterns/saga
  _Semantic lock: Use application-level locks when a saga's compensable transaction uses a semaphore to indicate that an update is in progress._

**Độ khó:** hard thật · hợp level middle, senior — Cần suy luận về điểm pivot quyết định hướng xử lý lỗi (bù trừ hay retry) và về anomaly do thiếu isolation; middle trả lời được compensating transaction, senior mới nêu pivot và biện pháp chống anomaly.
**Dùng trong phỏng vấn:** ~5 phút, 2 ý hỏi, chấm được — Hai ý của cùng một chủ đề saga; 4 điểm must-have rõ ràng, khoảng 5 phút.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu saga thay transaction phân tán bằng chuỗi local transaction cùng các bước bù trừ, và hậu quả của việc không có isolation.
- Ý bắt buộc: Khi bước tạo vận đơn lỗi, saga chạy compensating transaction cho các bước đã commit theo thứ tự ngược (hoàn tiền, rồi trả lại hàng giữ kho); đó là bù trừ nghiệp vụ, không phải rollback thật.; Vị trí pivot quyết định cách xử lý: trước pivot thì bù trừ, sau pivot (retryable, idempotent) thì retry tới khi xong.; Compensation cũng có thể thất bại nên phải idempotent, retry được và có giám sát.; Không có isolation giữa các saga nên có lost update và dirty read; giảm bằng semantic lock hoặc commutative updates.
- Dấu hiệu trả lời sai: Nói saga rollback như transaction trong một database.; Bỏ qua việc compensation có thể lỗi hoặc không idempotent.; Cho rằng saga vẫn đảm bảo isolation giống ACID.
- Câu hỏi nối tiếp: Nếu ta cần hiển thị đơn hàng trong lúc saga đang chạy, semantic lock giúp tránh dirty read thế nào và người dùng sẽ thấy trạng thái gì?

### de-qa-1424 · Đạt · tin cậy medium · Có thể chấp nhận

**Topic:** Microservices và khả năng chịu lỗi (`java.arch.microservices-resilience`) · ~353 token · hard của topic: 6

**Câu hỏi:** Service lưu đơn vào database rồi publish event lên broker, đôi lúc crash giữa hai bước làm service khác không nhận event. Outbox pattern sửa thế nào, và vì sao consumer vẫn phải idempotent?

**Kết luận:** Đạt: vấn đề dual write, outbox trong cùng transaction, relay (polling hoặc log tailing) và lý do consumer phải idempotent đều khớp catalog pattern của Chris Richardson; độ tin cậy medium vì nguồn chính là catalog tác giả pattern chứ không phải tài liệu chuẩn hoặc vendor.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | interview_fit | Đáp án không nhắc thứ tự: catalog nêu rõ message phải được gửi theo đúng thứ tự giao dịch (E1 trước E2), một yêu cầu quan trọng của outbox/relay; câu hỏi senior có thể hỏi tiếp về điểm này. | Thêm một dòng: relay phải giữ thứ tự theo aggregate (đọc outbox theo thứ tự commit hoặc dùng partition key theo aggregate id). |
| minor | difficulty | Đây là câu pattern quen thuộc; ở ngưỡng dưới của hard, phần phân biệt nằm ở ý thứ hai (vì sao outbox vẫn cần consumer idempotent). | Giữ nhãn hard; người phỏng vấn nên chấm nặng vào ý at-least-once và khử trùng. |

**Kiểm chứng:**
- `supported` Lưu database và publish broker là hai hệ thống khác nhau, 2PC thường không dùng được
  > 2PC is not an option. The database and/or the message broker might not support 2PC.  
  > — https://microservices.io/patterns/data/transactional-outbox.html
- `supported` Nếu crash giữa hai bước, đơn đã lưu nhưng event mất
  > if a service sends a message after committing the transaction there's no guarantee that it won't crash before sending the message.  
  > — https://microservices.io/patterns/data/transactional-outbox.html
- `supported` Outbox: ghi event vào bảng outbox trong cùng database transaction với việc cập nhật entity; một tiến trình riêng gửi lên broker
  > The solution is for the service that sends the message to first store the message in the database as part of the transaction that updates the business entities. A separate process then sends the messages to the message broker.  
  > — https://microservices.io/patterns/data/transactional-outbox.html
- `supported` Commit thì cả hai cùng có, rollback thì cả hai cùng mất
  > If the database transaction commits then the messages must be sent. Conversely, if the database rolls back, the messages must not be sent  
  > — https://microservices.io/patterns/data/transactional-outbox.html
- `supported` Relay có thể là polling publisher hoặc transaction log tailing
  > There are two patterns for implementing the Message relay: The Transaction log tailing pattern The Polling publisher pattern  
  > — https://microservices.io/patterns/data/transactional-outbox.html
- `supported` Relay có thể crash sau khi publish nhưng trước khi ghi nhận, khởi động lại sẽ publish lại cùng message
  > It might, for example, crash after publishing a message but before recording the fact that it has done so. When it restarts, it will then publish the message again.  
  > — https://microservices.io/patterns/data/transactional-outbox.html
- `supported` Bảo đảm thực tế là at-least-once nên consumer phải idempotent (lưu ID message đã xử lý)
  > As a result, a message consumer must be idempotent, perhaps by tracking the IDs of the messages that it has already processed.  
  > — https://microservices.io/patterns/data/transactional-outbox.html
  _Cụm 'at-least-once' và 'không phải exactly-once' là cách gọi tên của đáp án; nguồn nói Message relay might publish a message more than once._

**Độ khó:** hard thật · hợp level middle, senior — Cần hiểu dual write và lý do exactly-once không đạt được; một middle có kinh nghiệm trả lời phần outbox, senior mới giải thích rõ at-least-once và idempotent consumer. Ở ngưỡng dưới của hard.
**Dùng trong phỏng vấn:** ~3 phút, 2 ý hỏi, chấm được — Hai ý liên kết (outbox sửa gì, vì sao vẫn cần idempotent). 3 điểm must-have, khoảng 3 phút. Chunk 353 token.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu vấn đề ghi hai nơi (database và broker) không cùng transaction và cách outbox đưa việc gửi event vào chung transaction của database.
- Ý bắt buộc: Dual write: lưu database rồi publish broker không có transaction chung, crash giữa chừng làm mất event hoặc lệch dữ liệu; 2PC thường không dùng được.; Outbox: ghi event vào bảng outbox trong cùng transaction với entity; một relay (polling hoặc log tailing) đọc bảng rồi publish và đánh dấu đã xử lý.; Relay có thể crash sau khi publish nhưng trước khi đánh dấu nên message có thể gửi lặp; giao hàng là at-least-once, consumer phải khử trùng (ví dụ lưu ID message đã xử lý).
- Dấu hiệu trả lời sai: Cho rằng outbox cho exactly-once nên consumer không cần idempotent.; Publish lên broker ngay trong transaction database rồi coi như xong.; Dùng 2PC giữa database và broker như giải pháp mặc định.
- Câu hỏi nối tiếp: Làm sao giữ đúng thứ tự event của cùng một đơn hàng khi có nhiều instance relay?

### de-qa-1484 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Transformer và attention (`ai.dl.transformers-attention`) · ~354 token · hard của topic: 3

**Câu hỏi:** Với context dài như 128k, FlashAttention tăng tốc attention bằng cách nào dù vẫn là exact attention, và nó không giảm được phần chi phí nào?

**Kết luận:** Đạt: nội dung khớp bài báo FlashAttention (arXiv 2205.14135): exact attention, tiling giữa HBM và SRAM, bộ nhớ thêm tuyến tính, FLOPs tăng do recomputation, thời gian vẫn bậc hai; phép tính 16 lần chiều dài thành 256 lần ma trận là đúng.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | interview_fit | Đáp án nói 'phần chi phí không giảm' là thời gian bậc hai, nhưng không nhắc KV cache khi serving context 128k vẫn lớn và FlashAttention chủ yếu giúp prefill/training; người phỏng vấn senior có thể hỏi tiếp. | Có thể thêm một câu: FlashAttention giảm IO và bộ nhớ trung gian, không giảm FLOPs bậc hai và không thu nhỏ KV cache. |

**Kiểm chứng:**
- `supported` Self-attention chuẩn có chi phí thời gian và bộ nhớ bậc hai theo độ dài chuỗi
  > Transformers are slow and memory-hungry on long sequences, since the time and memory complexity of self-attention are quadratic in sequence length.  
  > — https://arxiv.org/abs/2205.14135
  _Tính 8k lên 128k là 16 lần nên ma trận n x n lớn khoảng 256 lần (16^2): phép tính số học, không cần nguồn._
- `supported` FlashAttention là thuật toán exact, IO-aware, dùng tiling để giảm số lần đọc/ghi giữa HBM và SRAM trên chip
  > We propose FlashAttention, an IO-aware exact attention algorithm that uses tiling to reduce the number of memory reads/writes between GPU high bandwidth memory (HBM) and GPU on-chip SRAM.  
  > — https://arxiv.org/abs/2205.14135
- `supported` SRAM trên chip nhanh hơn HBM nhiều nhưng nhỏ hơn rất nhiều; nút thắt là truy cập bộ nhớ (IO) không chỉ số phép tính
  > The on-chip SRAM is an order of magnitude faster than HBM but many orders of magnitude smaller in size.  
  > — https://arxiv.org/html/2205.14135
  _Cùng đoạn: operations are increasingly bottlenecked by memory (HBM) accesses._
- `supported` Nhờ ít truy cập HBM, FlashAttention chạy nhanh hơn dù FLOPs tăng do tính lại (recomputation), và bộ nhớ thêm tuyến tính theo độ dài chuỗi
  > Even with the increased FLOPs due to recomputation, our algorithm both runs faster ... and uses less memory —linear in sequence length—than standard attention  
  > — https://arxiv.org/html/2205.14135
  _Câu gốc tiếp: thanks to the massively reduced amount of HBM access._
- `supported` Vì là exact nên thời gian chạy vẫn tăng theo n bình phương, chỉ nhanh hơn đáng kể so với các cài đặt exact khác
  > Runtime grows quadratically with sequence length, but FlashAttention runs significantly faster than exact attention baselines  
  > — https://arxiv.org/html/2205.14135
  _Theorem 1 của bài báo: O(N^2 d) FLOPs và O(N) bộ nhớ thêm (công thức bị hỏng khi trích từ HTML nên không dùng làm quote)._
- `supported` Không thuật toán exact nào cải thiện tiệm cận số truy cập HBM hơn FlashAttention (nên giới hạn là cố hữu)
  > We also provide a lower bound, proving that no exact attention algorithm can asymptotically improve on HBM accesses over all SRAM sizes.  
  > — https://arxiv.org/html/2205.14135

**Độ khó:** hard thật · hợp level middle, senior — Cần hiểu vì sao tối ưu IO (HBM/SRAM) quan trọng hơn giảm FLOPs và phân biệt exact với approximate attention; middle chỉ nêu được 'tiết kiệm bộ nhớ', senior giải thích tiling, recomputation và giới hạn bậc hai.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Hai ý liên kết (FlashAttention nhanh hơn bằng cách nào; phần nào không giảm). Must-have 4 điểm, khoảng 4 phút. Chunk 354 token.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu rằng attention chậm vì đọc/ghi bộ nhớ GPU chứ không chỉ vì số phép tính, và FlashAttention giải quyết phần IO mà không đổi kết quả.
- Ý bắt buộc: Attention chuẩn có thời gian và bộ nhớ bậc hai theo độ dài chuỗi; 8k lên 128k là 16 lần thì ma trận n x n lớn khoảng 256 lần.; Cài đặt chuẩn ghi ma trận n x n ra HBM (chậm) rồi đọc lại nhiều lần nên nút thắt là IO.; FlashAttention (exact) chia Q, K, V thành block, tính trong SRAM nhanh và không ghi ma trận n x n ra HBM; tính lại một số bước (nhiều FLOPs hơn) nhưng ít truy cập HBM hơn, bộ nhớ thêm tuyến tính.; Không giảm được số phép tính bậc hai vì vẫn tính mọi cặp token; 128k vẫn đắt hơn 8k rất nhiều.
- Dấu hiệu trả lời sai: Nói FlashAttention là approximate attention hoặc làm kết quả khác attention chuẩn.; Cho rằng FlashAttention đưa độ phức tạp thời gian xuống tuyến tính.; Chỉ nói 'tiết kiệm bộ nhớ' mà không nhắc HBM và SRAM.
- Câu hỏi nối tiếp: Vì sao FlashAttention phải tính lại attention ở bước backward thay vì lưu ma trận n x n, và đổi lại được gì?

### de-qa-1485 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Transformer và attention (`ai.dl.transformers-attention`) · ~355 token · hard của topic: 3

**Câu hỏi:** Khi serving decoder sinh từng token, vì sao KV cache chiếm nhiều bộ nhớ khi batch lớn và context dài, và multi-query hay grouped-query attention giảm nó ra sao?

**Kết luận:** Đạt: KV cache giảm chi phí attention mỗi bước từ bậc hai xuống tuyến tính và đổi lấy bộ nhớ; MQA dùng chung một cặp K/V, GQA dùng số K/V head trung gian, đúng với bài báo Shazeer 2019, bài GQA 2023 và tài liệu HF Transformers.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | interview_fit | Chưa có công thức hoặc ví dụ số cho dung lượng cache (2 x layers x kv_heads x head_dim x seq x batch x byte); ứng viên senior thường được yêu cầu ước lượng nhanh. | Thêm một dòng công thức dung lượng để câu follow-up ước lượng có cơ sở chấm. |

**Kiểm chứng:**
- `supported` KV cache lưu K, V của các token đã xử lý để khỏi tính lại
  > A key-value (KV) cache eliminates this inefficiency by storing kv pairs derived from the attention layers of previously processed tokens.  
  > — https://raw.githubusercontent.com/huggingface/transformers/main/docs/source/en/cache_explanation.md
  _Bản markdown nguồn của trang huggingface.co/docs/transformers/cache_explanation (trang web không tải được từ máy kiểm tra)._
- `supported` Có cache thì chi phí attention mỗi bước tuyến tính theo độ dài chuỗi, đổi lại bộ nhớ tăng tuyến tính
  > attention cost per step is linear with sequence length (memory grows linearly, but compute/token remains low)  
  > — https://raw.githubusercontent.com/huggingface/transformers/main/docs/source/en/cache_explanation.md
  _Ô đối chiếu cùng bảng: attention cost per step is quadratic with sequence length (khi không có cache)._
- `supported` Cache lưu theo từng layer và kích thước tỉ lệ với batch, số head, độ dài chuỗi và head dim
  > The query (Q), key (K), and value (V) matrices are projections from the input embeddings of shape (b, h, T, d_head).  
  > — https://raw.githubusercontent.com/huggingface/transformers/main/docs/source/en/cache_explanation.md
  _Cùng trang: Attention is calculated independently in each layer of the model, and caching is done on a per-layer basis. Phép nhân theo layer và batch được suy ra từ hai câu này._
- `supported` Decode chậm chủ yếu vì chi phí băng thông bộ nhớ khi đọc lại keys/values mỗi bước
  > due to the memory-bandwidth cost of repeatedly loading the large  
  > — https://arxiv.org/abs/1911.02150
  _Câu gốc: incremental inference ... is often slow, due to the memory-bandwidth cost of repeatedly loading the large keys and values tensors._
- `supported` MQA: mọi query head dùng chung một cặp K/V, giảm kích thước cache, decode nhanh hơn nhiều nhưng có thể giảm chất lượng
  > We verify experimentally that the resulting models can indeed be much faster to decode, and incur only minor quality degradation from the baseline.  
  > — https://arxiv.org/abs/1911.02150
  _Bài báo nói degradation nhẹ; bài GQA nói MQA can lead to quality degradation. Đáp án dùng 'có thể giảm chất lượng', không mâu thuẫn._
- `supported` GQA: số K/V head nằm giữa 1 và số query head; chất lượng gần multi-head, tốc độ gần MQA
  > introduce grouped-query attention (GQA), a generalization of multi-query attention which uses an intermediate (more than one, less than number of query heads) number of key-value heads.  
  > — https://arxiv.org/abs/2305.13245
  _Cùng abstract: We show that uptrained GQA achieves quality close to multi-head attention with comparable speed to MQA._

**Độ khó:** hard thật · hợp level middle, senior — Cần nối hai ý: vì sao decode bị chặn bởi băng thông bộ nhớ và cache lớn theo batch, rồi cách MQA/GQA giảm số K/V head. Một middle biết KV cache, senior giải thích được đánh đổi MQA và GQA.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Hai ý liên kết (cache lớn vì sao; MQA/GQA giảm thế nào). 4 điểm must-have, khoảng 4 phút. Chunk 355 token.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu vì sao KV cache tăng tốc decode nhưng ngốn bộ nhớ GPU khi batch lớn và context dài, và cách giảm số head K/V để thu nhỏ nó.
- Ý bắt buộc: KV cache lưu K, V của mọi token đã sinh để mỗi bước chỉ tính cho token mới; chi phí attention mỗi bước giảm từ bậc hai xuống tuyến tính, đổi lại tốn bộ nhớ tăng theo số token.; Dung lượng cache tỉ lệ với số layer, số K/V head, độ dài context và batch (mỗi request có cache riêng) nên thành nút thắt bộ nhớ GPU.; Mỗi bước decode phải đọc lại toàn bộ K/V nên bị giới hạn bởi băng thông bộ nhớ.; MQA dùng chung một cặp K/V cho mọi query head (cache nhỏ nhất, có thể giảm chất lượng); GQA chia nhóm, K/V head ở giữa 1 và số query head (chất lượng gần MHA, tốc độ gần MQA).
- Dấu hiệu trả lời sai: Nhầm KV cache với cache của kết quả request (response cache).; Cho rằng MQA/GQA giảm số query head hoặc giảm chất lượng không đáng kể trong mọi trường hợp.; Không nhận ra cache nhân theo batch.
- Câu hỏi nối tiếp: Một model 32 layer, 8 K/V head, head dim 128, dùng fp16, context 128k, batch 8: KV cache ước chừng bao nhiêu GB, và GQA giúp được bao nhiêu so với MHA 32 head?

### de-qa-1486 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Transformer và attention (`ai.dl.transformers-attention`) · ~384 token · hard của topic: 3

**Câu hỏi:** Model huấn luyện với context 4k, khi đưa prompt 16k thì chất lượng sụp dù còn đủ bộ nhớ. Vì sao positional encoding gây ra điều này, và ALiBi hay position interpolation xử lý ra sao?

**Kết luận:** Đạt: giải thích lỗi ngoại suy vị trí, ALiBi (penalty theo khoảng cách, train 1024 chạy 2048) và Position Interpolation cho RoPE (co tuyến tính chỉ số vị trí, khoảng 1000 bước fine-tune, LLaMA tới 32768) đều khớp bài báo gốc.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | outdated | Đáp án dừng ở ALiBi (2021) và Position Interpolation (2023). Thực tế các model hiện nay thường mở rộng context bằng các biến thể RoPE scaling (NTK-aware, YaRN) cộng continued pretraining; câu hỏi chỉ nêu ALiBi hoặc PI nên không sai, nhưng ứng viên giỏi có thể nhắc thêm. | Thêm một câu cuối: các kỹ thuật RoPE scaling như YaRN là biến thể của ý tưởng nội suy; không bắt buộc cho điểm. |

**Kiểm chứng:**
- `supported` Mô hình không có recurrence hay convolution nên thông tin thứ tự phải được chèn qua mã hóa vị trí
  > Since our model contains no recurrence and no convolution, in order for the model to make use of the order of the sequence, we must inject some information about the relative or absolute position of the tokens in the sequence.  
  > — https://arxiv.org/html/1706.03762
- `supported` Các phương pháp vị trí đương thời không ngoại suy hiệu quả; đổi cách biểu diễn vị trí thì cho phép ngoại suy
  > We first show that extrapolation can be enabled by simply changing the position representation method, though we find that current methods do not allow for efficient extrapolation.  
  > — https://arxiv.org/abs/2108.12409
- `supported` ALiBi không cộng positional embedding vào token embedding mà trừ penalty tỉ lệ với khoảng cách vào điểm query-key
  > ALiBi does not add positional embeddings to word embeddings; instead, it biases query-key attention scores with a penalty that is proportional to their distance.  
  > — https://arxiv.org/abs/2108.12409
  _Việc phải chọn ALiBi từ lúc pretrain là suy luận hợp lý (đổi cách mã hóa vị trí thì phải train lại), bài báo trình bày ALiBi như phương pháp huấn luyện model mới._
- `supported` Model train ở độ dài ngắn vẫn ngoại suy lên chuỗi dài hơn (train 1024, chạy 2048)
  > trains a 1.3 billion parameter model on input sequences of length 1024 that extrapolates to input sequences of length 2048  
  > — https://arxiv.org/abs/2108.12409
- `supported` Ngoại suy vượt độ dài train với RoPE có thể cho điểm attention lớn bất thường làm hỏng cơ chế attention
  > rather than extrapolating beyond the trained context length which may lead to catastrophically high attention scores that completely ruin the self-attention mechanism.  
  > — https://arxiv.org/abs/2306.15595
- `supported` Position Interpolation co tuyến tính các chỉ số vị trí về khớp cửa sổ gốc, cho model RoPE đã pretrain
  > Position Interpolation linearly down-scales the input position indices to match the original context window size  
  > — https://arxiv.org/abs/2306.15595
- `supported` PI cần fine-tune rất ít (khoảng 1000 bước) và mở rộng LLaMA tới 32768
  > extends the context window sizes of RoPE-based pretrained LLMs such as LLaMA models to up to 32768 with minimal fine-tuning (within 1000 steps)  
  > — https://arxiv.org/abs/2306.15595

**Độ khó:** hard thật · hợp level senior — Cần hiểu vì sao mã hóa vị trí không tổng quát hóa ra ngoài độ dài train và hai hướng sửa khác nhau (đổi cách mã hóa lúc pretrain so với nội suy cho model có sẵn); middle thường chỉ biết 'model chưa thấy vị trí đó'.
**Dùng trong phỏng vấn:** ~5 phút, 2 ý hỏi, chấm được — Nguyên nhân cộng hai hướng sửa là một chuỗi suy luận liên kết, nhưng must-have gồm 4 điểm, khoảng 5 phút, sát ngưỡng. Chunk 384 token.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu vì sao chất lượng sụp khi chạy vượt độ dài đã train dù đủ bộ nhớ (lỗi tổng quát hóa vị trí) và hai cách khác nhau để xử lý.
- Ý bắt buộc: Model chưa từng thấy các vị trí vượt độ dài train; vị trí phải được chèn qua mã hóa vị trí; với RoPE, ngoại suy có thể cho điểm attention lớn bất thường và làm hỏng attention. Đây không phải thiếu bộ nhớ.; ALiBi: không cộng positional embedding mà trừ penalty theo khoảng cách vào điểm query-key; train ngắn vẫn ngoại suy dài hơn (1024 lên 2048); phải chọn từ lúc pretrain.; Position Interpolation: với model RoPE đã pretrain, co tuyến tính chỉ số vị trí về khớp cửa sổ gốc thay vì ngoại suy, cần fine-tune ít (khoảng 1000 bước), mở rộng LLaMA tới 32768.
- Dấu hiệu trả lời sai: Giải thích bằng 'hết bộ nhớ GPU' hoặc 'attention n^2 nên chậm'.; Nói có thể bật ALiBi trên một model đã pretrain bằng RoPE mà không train lại.; Cho rằng position interpolation là kéo giãn context mà không cần fine-tune hay không đổi chất lượng.
- Câu hỏi nối tiếp: Vì sao nội suy vị trí (co lại) an toàn hơn ngoại suy (kéo dài ra) đối với RoPE?

### de-qa-1487 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Context engineering và long context (`ai.llm.context-engineering`) · ~357 token · hard của topic: 3

**Câu hỏi:** Agent gọi LLM nhiều lượt đã bật prompt caching nhưng cache hit rất thấp. Cấu trúc prompt thường sai ở đâu, và việc tóm tắt lịch sử hội thoại ảnh hưởng cache ra sao?

**Kết luận:** Đạt: cache theo prefix, lỗi đặt nội dung đổi liên tục (timestamp, breakpoint trên khối thay đổi), thứ tự tools, system, messages của Anthropic và việc compaction làm mất cache đều khớp tài liệu hiện hành của Anthropic và OpenAI; chỉ thiếu nhắc TTL và ngưỡng token tối thiểu.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | interview_fit | Đáp án chỉ nói về cấu trúc prompt; các nguyên nhân hit thấp khác mà tài liệu Anthropic nêu ngay đầu trang như TTL (5 phút hoặc 1 giờ), ngưỡng token tối thiểu và request tới trước khi cache được ghi chưa được nhắc. Câu hỏi hỏi về 'cấu trúc prompt' nên chưa phải lỗi. | Thêm một dòng cuối: nếu cấu trúc đúng mà hit vẫn thấp, kiểm tra TTL, độ dài tối thiểu của prefix và số request song song; theo dõi cache read/write token trong usage. |

**Kiểm chứng:**
- `supported` Prompt caching hoạt động theo prefix: các request dùng chung phần đầu prompt giống hệt thì tái sử dụng
  > Prompt caching reuses work when requests share the same prompt prefix.  
  > — https://platform.openai.com/docs/guides/prompt-caching
  _Tài liệu OpenAI hiện hành; trang cũng mô tả breakpoint tường minh và chế độ implicit._
- `supported` Đặt cache_control (breakpoint) lên khối thay đổi mỗi request (có timestamp) thì mỗi request ghi cache mới mà không bao giờ đọc được
  > No cache hit. You pay for a fresh cache write on every request and never get a read.  
  > — https://platform.claude.com/docs/en/build-with-claude/prompt-caching
  _Mục Common mistake: Breakpoint on content that changes every request; cách sửa là đặt cache_control ở khối tĩnh cuối cùng._
- `supported` Nội dung ổn định đi trước, nội dung động đi sau; đặt breakpoint ở khối cuối còn giống hệt giữa các request
  > Place cache_control on the last block whose prefix is identical across the requests you want to share a cache.  
  > — https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- `supported` Anthropic cache theo thứ tự tools, system, messages; đổi ở tầng nào thì tầng đó và các tầng sau mất cache
  > the cache follows the hierarchy: tools → system → messages. Changes at each level invalidate that level and all subsequent levels.  
  > — https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- `supported` Lịch sử hội thoại chỉ nên nối thêm, không viết lại các lượt cũ
  > earlier content never changes, so the next request's lookback finds the prior write.  
  > — https://platform.claude.com/docs/en/build-with-claude/prompt-caching
  _Câu đầy đủ nói về cuộc hội thoại tăng dần, nơi nội dung cũ không đổi._
- `supported` Compaction/tóm tắt thay nội dung cũ nên đổi prefix và làm mất cache từ chỗ thay đổi trở đi
  > Replaces earlier conversation content with a compacted context that can prevent reuse from the first changed token onward.  
  > — https://platform.openai.com/docs/guides/prompt-caching
  _Dòng context_management (Compaction) trong bảng những gì làm đổi prefix của OpenAI._
- `supported` Nén theo đợt: xóa/cắt đủ nhiều token mỗi lần để chi phí ghi lại cache đáng giá
  > Tool result clearing: Invalidates cached prompt prefixes when content is cleared. To account for this, clear enough tokens to make the cache invalidation worthwhile.  
  > — https://platform.claude.com/docs/en/build-with-claude/context-editing
  _Khuyến nghị tương ứng của Anthropic cho context editing; ý 'nén theo đợt' là diễn giải của đáp án từ khuyến nghị này._

**Độ khó:** hard thật · hợp level middle, senior — Cần suy luận về cách cache theo prefix tương tác với cấu trúc prompt và việc nén lịch sử; middle biết 'để phần cố định lên đầu', senior giải thích vì sao breakpoint đặt sai thì không bao giờ đọc được và đánh đổi của compaction. Câu này gắn với vendor nhưng đáp án đã nêu rõ Anthropic.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Hai ý liên kết (cấu trúc sai ở đâu; tóm tắt ảnh hưởng cache thế nào). 4 điểm must-have, khoảng 4 phút. Chunk 357 token.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu prompt caching dựa trên prefix giống hệt và biết cách sắp xếp prompt cùng cách nén lịch sử để không phá cache.
- Ý bắt buộc: Cache theo prefix: chỉ cần một thay đổi ở phần đầu thì mọi thứ phía sau mất cache.; Lỗi thường gặp: để timestamp hoặc dữ liệu riêng của người dùng ở đầu prompt hoặc trong system prompt; đặt breakpoint lên khối luôn thay đổi nên chỉ ghi mà không đọc được.; Cách sắp xếp: nội dung ổn định (instruction, tool, tài liệu dùng chung) trước, nội dung động sau; lịch sử chỉ nối thêm, không viết lại lượt cũ.; Tóm tắt hoặc compaction đổi prefix và đặt lại cache, nên nén theo đợt và giữ nguyên phần đầu ổn định.
- Dấu hiệu trả lời sai: Đưa thời gian hiện tại hoặc ID người dùng vào dòng đầu system prompt.; Tóm tắt lại lịch sử mỗi lượt hội thoại mà không tính tới chi phí mất cache.; Đặt breakpoint ở cuối prompt khi cuối prompt luôn đổi.
- Câu hỏi nối tiếp: Khi nào việc tóm tắt lịch sử làm bạn tốn hơn việc giữ nguyên lịch sử và hưởng cache, và bạn tính ngưỡng đó thế nào?

### de-qa-1488 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Đánh giá LLM và hallucination (`ai.llm.evaluation-hallucination`) · ~372 token · hard của topic: 3

**Câu hỏi:** Golden set 60 câu, sau khi đổi prompt số câu đúng tăng từ 47 lên 49. Làm sao biết đó là cải thiện thật chứ không phải nhiễu, khi cả hai phiên bản chấm trên cùng bộ câu hỏi?

**Kết luận:** Đạt: khung super-population, paired analysis, resampling, khuyến cáo không hạ temperature và power analysis đều có trong bài báo Adding Error Bars to Evals (arXiv 2411.00640). Gợi ý nhỏ: đáp án nên nói rõ với điểm nhị phân thì 47 lên 49 gần như chắc chắn là nhiễu.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | factual | Đáp án nói 'rất có thể nằm trong nhiễu' nhưng không tính cụ thể. Với điểm nhị phân (đúng/sai), chênh 49 so với 47 nghĩa là chênh ròng 2 câu; kiểm định exact McNemar trên các cặp bất đồng cho p ít nhất 0,5 (ví dụ 2 câu thắng, 0 câu thua cho p = 0,5), cần chênh ròng khoảng 6 câu (6 thắng, 0 thua) mới… | Thêm một câu ví dụ số: với 60 câu nhị phân, 47 lên 49 không thể có ý nghĩa thống kê dù paired; muốn kết luận cần thêm câu hoặc cải thiện lớn hơn nhiều, và nhớ nêu khoảng tin cậy. |
| minor | interview_fit | Không nhắc nguồn nhiễu thứ hai khi điểm do LLM-as-judge chấm: bản thân judge có sai số và thiên lệch, nên cần cố định judge và, nếu có thể, lặp lại chấm. | Thêm một dòng về nhiễu từ judge nếu bộ chấm là LLM. |

**Kiểm chứng:**
- `supported` Coi golden set là mẫu rút từ tập câu hỏi lớn hơn không nhìn thấy (super-population)
  > Conceptualizing evaluation questions as having been drawn from an unseen super-population, we present formulas for analyzing evaluation data, measuring differences between two models, and planning an evaluation experiment.  
  > — https://arxiv.org/abs/2411.00640
- `supported` Điểm trung bình có sai số chuẩn tính bằng định lý giới hạn trung tâm; báo cáo khoảng tin cậy
  > Computing standard errors of the mean using the Central Limit Theorem  
  > — https://arxiv.org/html/2411.00640
  _Mục recommendation 1 của bài báo._
- `supported` Dùng paired analysis: tính hiệu điểm theo từng câu rồi suy luận thống kê trên hiệu đó
  > When two models are being compared, conducting statistical inference on the question-level paired differences, rather than the population-level summary statistics  
  > — https://arxiv.org/html/2411.00640
- `supported` Phương sai giảm khi điểm hai phiên bản tương quan (cùng nhận định câu dễ, câu khó)
  > We can thus reduce the variance with paired differences as long as the conditional means of the model scores are correlated  
  > — https://arxiv.org/html/2411.00640
- `supported` Giảm nhiễu từ model bằng cách cho mỗi câu trả lời nhiều lần (resampling) rồi lấy điểm trung bình theo câu
  > The first strategy for reducing the expected conditional variance is to resample the model a number of times, and to compute the standard error using the question-level mean scores from the resamples.  
  > — https://arxiv.org/html/2411.00640
- `supported` Đừng hạ temperature chỉ để ổn định kết quả: nó đổi hành vi model và chỉ chuyển phương sai sang chỗ khác
  > However, we advise against this practice, unless the purpose is to study the model at the new temperature. Besides altering the model's behavior, adjusting the sampling temperature may simply shift the conditional variance  
  > — https://arxiv.org/html/2411.00640
  _Mục 3.3 Don't touch the thermostat!_
- `supported` Dùng power analysis để biết cần bao nhiêu câu; nếu không đủ thì thêm câu hoặc không kết luận
  > If the number of questions in the eval is fixed, consumers can calculate the Minimum Detectable Effect and decide whether the eval is worth running.  
  > — https://arxiv.org/html/2411.00640
  _Recommendation 5: Using power analysis to determine whether an eval (or a random subsample) is capable of testing a hypothesis of interest._

**Độ khó:** hard thật · hợp level senior — Cần tư duy thống kê (sai số chuẩn, paired difference, power) áp dụng vào một số liệu cụ thể; middle thường chỉ so hai con số, senior mới tách nhiễu lấy mẫu và nhiễu model.
**Dùng trong phỏng vấn:** ~5 phút, 1 ý hỏi, chấm được — Một câu hỏi (cải thiện thật hay nhiễu) với bốn công cụ liên quan, khoảng 4-5 phút; có 4 điểm chấm được. Chunk 372 token.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Biết rằng so sánh hai điểm trung bình trên bộ câu hỏi nhỏ cần khoảng tin cậy và phép so sánh theo cặp chứ không chỉ nhìn con số lớn hơn.
- Ý bắt buộc: Golden set chỉ là một mẫu: điểm có sai số chuẩn và khoảng tin cậy; hơn kém 2 câu trên 60 rất có thể là nhiễu.; Paired analysis: tính hiệu điểm theo từng câu rồi suy luận trên hiệu đó; sai số nhỏ hơn so sánh hai trung bình độc lập khi hai phiên bản tương quan.; Giảm nhiễu model: chạy mỗi câu nhiều lần rồi lấy trung bình theo câu; đừng hạ temperature chỉ để ổn định.; Power analysis để biết cần bao nhiêu câu; không đủ thì thêm câu hoặc không kết luận, và báo cáo khoảng tin cậy.
- Dấu hiệu trả lời sai: Kết luận 'tăng 2 câu là cải thiện' chỉ vì 49 lớn hơn 47.; Hạ temperature xuống 0 rồi coi như hết nhiễu.; Dùng hai bộ câu hỏi khác nhau cho hai phiên bản.
- Câu hỏi nối tiếp: Nếu điểm chỉ là đúng hoặc sai, kiểm định nào hợp với dữ liệu ghép cặp, và bạn dựa vào những câu nào để tính?

### de-qa-1518 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Docker image và container (`devops.docker.images`) · ~346 token · hard của topic: 2

**Câu hỏi:** Dockerfile COPY file chứa token vào image rồi RUN rm file đó ở lệnh sau, nhưng image vẫn lộ token. Vì sao, và truyền secret lúc build đúng cách thế nào?

**Kết luận:** Đạt: layer bất biến nên RUN rm chỉ thêm lớp ghi nhận xóa, ARG/ENV tồn tại trong image, và cách đúng là RUN --mount=type=secret của BuildKit; tất cả khớp tài liệu Docker và đặc tả OCI. Độ khó ở ngưỡng dưới của hard: các câu trả lời sai phổ biến (ARG, ENV, chỉ multi-stage) đủ phân biệt middle; giữ nhãn hard cũng để topic không dưới ngưỡng SC-001.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | interview_fit | Đáp án không nhắc rằng cách COPY token cũng để lại secret trong build cache và hiện ra trong docker history (ARG), điều tài liệu Dockerfile reference nêu qua cụm 'without baking them into the image or build cache'; multi-stage chỉ an toàn nếu token ở stage không được COPY sang stage cuối. | Thêm một dòng: secret mount không để lại dấu vết ở layer lẫn build cache; multi-stage chỉ bảo vệ khi token nằm ở stage đã bị bỏ lại, token COPY ở stage cuối vẫn lộ. |

**Kiểm chứng:**
- `supported` Mỗi layer bất biến sau khi tạo
  > And each of these layers, once created, are immutable.  
  > — https://docs.docker.com/get-started/docker-concepts/building-images/understanding-image-layers/
- `supported` Mỗi layer ghi lại các thay đổi filesystem (thêm, xóa, sửa)
  > Each layer in an image contains a set of filesystem changes ... additions, deletions, or modifications.  
  > — https://docs.docker.com/get-started/docker-concepts/building-images/understanding-image-layers/
- `supported` RUN rm chỉ thêm một layer ghi nhận việc xóa; nội dung file vẫn nằm trong layer cũ
  > Whiteout files MUST only apply to resources in lower/parent layers.  
  > — https://raw.githubusercontent.com/opencontainers/image-spec/main/layer.md
  _Đặc tả OCI image layer: layer xóa chỉ chứa whiteout entry (Deleted files or directories marked with a whiteout file), file gốc vẫn ở layer thấp hơn. Docker docs không có câu nói thẳng điều này; kết luận là hệ quả của hai câu trên về layer bất biến._
- `supported` ARG và ENV không an toàn để truyền secret vì tồn tại trong image cuối
  > Build arguments and environment variables are inappropriate for passing secrets to your build, because they persist in the final image.  
  > — https://raw.githubusercontent.com/docker/docs/main/content/manuals/build/building/secrets.md
  _Bản markdown nguồn của docs.docker.com/build/building/secrets (trang web không tải được từ máy kiểm tra)._
- `supported` Secret mount lấy secret từ build client và chỉ có tạm thời trong container build suốt lệnh RUN
  > A secret mount takes a secret from the build client and makes it temporarily available inside the build container, for the duration of the build instruction.  
  > — https://raw.githubusercontent.com/docker/docs/main/content/manuals/build/building/secrets.md
- `supported` RUN --mount=type=secret không ghi secret vào image (không vào layer)
  > This mount type allows the build container to access secret values, such as tokens or private keys, without baking them into the image.  
  > — https://docs.docker.com/reference/dockerfile/
  _Bảng mount type trên cùng trang còn nói: without baking them into the image or build cache._
- `supported` Có thêm SSH mount cho việc lấy private Git repository
  > They're commonly used when you need to fetch private Git repositories in your builds.  
  > — https://raw.githubusercontent.com/docker/docs/main/content/manuals/build/building/secrets.md
- `supported` Multi-stage build chỉ COPY --from artifact cần thiết, phần còn lại bị bỏ lại ngoài image cuối
  > You can selectively copy artifacts from one stage to another, leaving behind everything you don't want in the final image.  
  > — https://raw.githubusercontent.com/docker/docs/main/content/manuals/build/building/multi-stage.md

**Độ khó:** hard thật · hợp level middle — Ở ngưỡng dưới của hard: tình huống lỗi cụ thể cần hiểu layer bất biến và biết cơ chế secret mount; câu trả lời sai phổ biến (ARG, ENV, gộp lệnh, chỉ multi-stage) khiến nó đủ phân biệt middle. Không nên hạ xuống medium vì topic chỉ còn 1 hard (dưới SC-001).
**Dùng trong phỏng vấn:** ~3 phút, 2 ý hỏi, chấm được — Hai ý liên kết (vì sao lộ, truyền secret đúng cách), 4 điểm must-have, khoảng 3 phút. Chunk 346 token.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu image là chồng layer bất biến nên xóa file ở lệnh sau không làm nó biến mất, và biết cách truyền secret lúc build mà không để lại dấu vết.
- Ý bắt buộc: Mỗi layer bất biến; COPY tạo layer chứa token, RUN rm chỉ thêm layer ghi nhận xóa, layer cũ vẫn nằm trong image nên ai có image đều lấy lại được token.; ARG và ENV cũng không an toàn vì tồn tại trong image cuối.; Cách đúng: BuildKit secret mount (RUN --mount=type=secret) để secret chỉ có tạm thời trong lệnh RUN và không vào layer; SSH mount cho private Git repository.; Multi-stage bổ trợ: chỉ COPY --from artifact cần thiết sang stage cuối.
- Dấu hiệu trả lời sai: Cho rằng chỉ cần xóa file ở cuối Dockerfile là đủ.; Truyền secret bằng ARG hoặc ENV.; Cho rằng multi-stage luôn che được secret kể cả khi COPY token ở stage cuối.
- Câu hỏi nối tiếp: Làm sao kiểm tra một image đã build có lộ secret trong layer hay không (docker history, dive, scan secret)?

### de-qa-1563 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Bảo mật frontend (`fe.web.security`) · ~331 token · hard của topic: 4

**Câu hỏi:** Site đặt CSP script-src liệt kê domain CDN và Google Analytics nhưng vẫn bị XSS qua script của domain được phép. Vì sao allowlist yếu, và strict CSP với nonce xử lý script bên thứ ba thế nào?

**Kết luận:** Đạt: allowlist CSP khó làm đúng và dễ bị vượt qua, strict CSP dùng nonce mới cho mỗi response, strict-dynamic cho phép script đã có nonce tải tiếp script khác, đánh đổi là tin cậy bắc cầu; tất cả khớp MDN, web.dev. Ý đầu hơi chung chung, nên bổ sung cơ chế cụ thể (unsafe endpoint trên domain được allowlist).

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | interview_fit | Ý đầu của đáp án ('vô tình cho phép domain không an toàn') chép lại nguyên văn mức MDN nhưng không nêu cơ chế XSS qua script của domain được phép, đúng là thứ câu hỏi nêu. Người chấm khó biết ứng viên nói chi tiết có đúng hay không. | Thêm một câu cơ chế: domain trong allowlist (CDN công cộng, domain analytics) thường có endpoint không an toàn, ví dụ endpoint JSONP hoặc thư viện cũ như AngularJS, cho phép kẻ tấn công chạy JavaScript tùy ý dù vẫn nằm trong script-src (ví dụ do người review nêu, nguồn trích dẫn chỉ nói chung là un… |
| minor | interview_fit | Đáp án chưa nhắc các thành phần còn lại của strict CSP (object-src 'none', base-uri 'none') và phương án dự phòng cho trình duyệt cũ; chỉ cần nhắc nếu người phỏng vấn muốn đi sâu. | Có thể thêm một dòng về object-src, base-uri và fallback; không bắt buộc cho điểm. |

**Kiểm chứng:**
- `supported` Allowlist CSP khó làm đúng, thường vô tình cho phép domain không an toàn nên không chặn hiệu quả XSS
  > Allowlist CSPs are hard to get right and often policies inadvertently whitelist unsafe domains, and hence don't provide effective protection against XSS  
  > — https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CSP
  _web.dev nói thêm: host-allowlist-based CSPs ... can be bypassed in most configurations._
- `supported` Phần lớn domain thường được allowlist có endpoint không an toàn, nên allowlist cho phép kẻ tấn công vượt CSP
  > We observe that 14 out of the 15 domains most commonly whitelisted for loading scripts contain unsafe endpoints; as a consequence, 75.81% of distinct policies use script whitelists that allow attackers to bypass CSP.  
  > — https://research.google/pubs/csp-is-dead-long-live-csp-on-the-insecurity-of-whitelists-and-the-future-of-content-security-policy/
  _Bài CCS 2016 (Weichselbaum và cộng sự) mà MDN trích dẫn; làm rõ cơ chế mà đáp án chỉ nói chung._
- `supported` Nonce phải ngẫu nhiên và mới ở mỗi response; nếu đoán được hay cố định thì vô dụng
  > This only works if the number isn't guessable, and is newly generated at runtime for every response.  
  > — https://web.dev/articles/strict-csp
- `supported` Nonce không tự truyền sang script mà script bên thứ ba tải thêm nên policy dễ vỡ
  > If a third-party script loads any additional scripts, or uses any inline scripts, then this will fail, because the third-party script won't pass the nonce or hash through.  
  > — https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CSP
- `supported` strict-dynamic cho phép script đã có nonce hoặc hash tải tiếp các script không cần nonce
  > if a script has a nonce or a hash attached to it, then that script will be allowed to load further scripts which do not themselves have nonces or hashes.  
  > — https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CSP
- `supported` Với strict-dynamic không phải liệt kê domain: allowlist bị bỏ qua
  > At the same time, any allowlist or source expressions such as 'self' or 'unsafe-inline' will be ignored.  
  > — https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/script-src
- `supported` Đánh đổi: nếu script tin cậy tạo thẻ script từ nguồn có thể bị chèn thì CSP không bảo vệ được
  > If there are injections into the locations of dynamically created scripts (document.createElement('script')), including into any library functions that create script DOM nodes based on the values of their arguments.  
  > — https://web.dev/articles/strict-csp
  _Nằm trong danh sách các trường hợp CSP không bảo vệ tốt, kể cả khi dùng nonce hoặc hash, có hay không có strict-dynamic._

**Độ khó:** hard thật · hợp level senior — Cần hiểu vì sao allowlist hỏng, cách nonce chặn XSS và cách strict-dynamic xử lý script bên thứ ba cùng đánh đổi; middle biết 'dùng nonce', senior giải thích được strict-dynamic và giới hạn của nó.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Hai ý liên kết (allowlist yếu ở đâu; strict CSP xử lý bên thứ ba thế nào), 4 điểm must-have, khoảng 4 phút. Chunk 331 token.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu vì sao CSP dạng danh sách domain không đủ chống XSS và cách CSP dựa trên nonce giải quyết, kể cả script bên thứ ba.
- Ý bắt buộc: Allowlist theo domain khó làm đúng, thường vô tình cho phép domain có endpoint không an toàn nên XSS vẫn chạy được script từ domain được phép.; Strict CSP: server sinh nonce ngẫu nhiên mới cho mỗi response, gắn trên các thẻ script tin cậy; script chèn vào không có nonce nên không chạy.; Script bên thứ ba tải thêm script thì nonce không truyền theo; 'strict-dynamic' cho script đã có nonce hoặc hash tải tiếp các script khác, không cần liệt kê domain.; Đánh đổi: tin cậy bắc cầu, nên nếu script tin cậy tạo thẻ script từ dữ liệu có thể bị chèn thì CSP không bảo vệ.
- Dấu hiệu trả lời sai: Dùng nonce cố định cho mọi response.; Cho rằng thêm domain tin cậy vào script-src là đủ an toàn.; Cho rằng CSP thay thế được việc escape output.
- Câu hỏi nối tiếp: Nếu trang tĩnh (không render ở server) thì bạn dùng hash thay nonce thế nào, và khi script đổi thì sao?

### de-qa-1564 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Bảo mật frontend (`fe.web.security`) · ~349 token · hard của topic: 4

**Câu hỏi:** Team chuyển JWT từ localStorage sang cookie httpOnly và tuyên bố đã hết lo XSS. Nhận định này sai ở đâu, và cần thêm biện pháp nào để chống CSRF?

**Kết luận:** Đạt: httpOnly chỉ bảo vệ tính bí mật của cookie, XSS vẫn gửi request kèm cookie; chuyển sang cookie sinh rủi ro CSRF, SameSite đặt tường minh nhưng chỉ là defense in depth cạnh CSRF token. Tất cả khớp OWASP Session Management và HTML5 Security cheat sheet.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | interview_fit | Đáp án không nêu rằng SameSite=Lax vẫn cho phép điều hướng cấp cao nhất cross-site bằng method an toàn, và 'same-site' khác 'same-origin' (subdomain), là lý do SameSite không thay được CSRF token; cũng chưa nói tên mẫu token (synchronizer token, double submit cookie). | Thêm một dòng: Lax cho phép top-level navigation bằng GET nên endpoint đổi trạng thái không được dùng GET; vẫn dùng CSRF token (synchronizer hoặc double submit) và kiểm tra Origin. |

**Kiểm chứng:**
- `supported` Không lưu session identifier ở localStorage vì mọi script cùng origin đều đọc được; cookie httpOnly giảm rủi ro này
  > Do not store session identifiers in local storage as the data is always accessible by JavaScript. Cookies can mitigate this risk using the httpOnly flag.  
  > — https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html
  _Cheat sheet nói session identifier; JWT dùng làm session token được áp dụng tương tự._
- `supported` httpOnly chặn script đọc cookie qua document.cookie
  > The HttpOnly cookie attribute instructs web browsers not to allow scripts (e.g. JavaScript or VBscript) an ability to access the cookies via the DOM document.cookie object.  
  > — https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- `supported` httpOnly chỉ bảo vệ tính bí mật của cookie; kẻ tấn công không dùng được cookie offline
  > The HttpOnly cookie only protects the confidentiality of the cookie; the attacker cannot use it offline, outside of the context of an XSS attack.  
  > — https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- `supported` XSS vẫn gửi được request kèm cookie vì trình duyệt luôn gửi cookie
  > if an XSS attack is combined with a CSRF attack, the requests sent to the web application will include the session cookie, as the browser always includes the cookies when sending requests.  
  > — https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- `supported` Đặt SameSite=Lax hoặc Strict tường minh, không dựa vào mặc định của trình duyệt
  > Session cookies must explicitly set SameSite=Strict (preferred) or SameSite=Lax. Never use SameSite=None without Secure, and do not rely on the browser-default value, which varies across browsers and versions.  
  > — https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- `supported` SameSite chỉ là defense in depth, không thay thế CSRF token
  > Treat SameSite as defense in depth against CSRF, not as a replacement for a CSRF token.  
  > — https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- `supported` Vẫn phải chống XSS (escape/sanitize đầu vào-đầu ra và CSP) dù đã dùng httpOnly
  > Websites should sanitize input and set a CSP, providing defense in depth against XSS.  
  > — https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CSP
  _Cụm 'escape output' là cách gọi của đáp án cho biện pháp sanitize/encode; OWASP XSS Prevention Cheat Sheet được cheat sheet Session Management dẫn tới._

**Độ khó:** hard thật · hợp level middle, senior — Ở ngưỡng dưới của hard: ý then chốt là httpOnly không chặn XSS thực hiện hành động nhân danh người dùng, nhiều middle bỏ sót; phần CSRF/SameSite là kiến thức quen thuộc hơn.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Hai ý liên kết (nhận định sai ở đâu, biện pháp CSRF), 4 điểm must-have, khoảng 4 phút. Chunk 349 token.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu giới hạn của cookie httpOnly (bảo vệ bí mật, không chặn XSS hành động) và rủi ro CSRF khi chuyển sang cookie.
- Ý bắt buộc: Đúng một phần: httpOnly chặn script đọc cookie nên XSS không lấy cắp được token mang đi dùng nơi khác; localStorage thì mọi script cùng origin đọc được.; Nhưng XSS vẫn nguy hiểm: script chèn vào chạy trong trang và gửi request kèm cookie, làm hành động nhân danh người dùng; vẫn phải chống XSS (escape output, CSP).; Cookie làm xuất hiện CSRF vì trình duyệt tự gửi cookie: cần CSRF token.; Đặt SameSite=Lax hoặc Strict tường minh nhưng chỉ coi là defense in depth, không thay token.
- Dấu hiệu trả lời sai: Nói chuyển sang httpOnly là hết lo XSS.; Chỉ dựa vào SameSite mặc định của trình duyệt để chống CSRF.; Không nhận ra cookie bị trình duyệt tự gửi nên có rủi ro CSRF.
- Câu hỏi nối tiếp: Với SameSite=Lax, kẻ tấn công vẫn gửi được loại request cross-site nào, và endpoint đổi trạng thái nên dùng method nào?

### de-qa-1565 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** JavaScript core: scope, closure và this (`fe.js.core-closure-this`) · ~441 token · hard của topic: 2

**Câu hỏi:** Vì sao đổi prototype của object đã tạo bằng setPrototypeOf bị coi là chậm, và nên thay bằng cách nào?

**Kết luận:** Đạt: MDN cảnh báo setPrototypeOf rất chậm, hidden class của V8 chứa tham chiếu prototype và làm định danh shape cho inline cache, ValidityCell của prototype bị vô hiệu khi prototype đổi, và nên dùng Object.create() hoặc class extends; tất cả có nguồn. Gợi ý rút gọn: ý (b) lệch khỏi câu hỏi và chi tiết V8 không cần cho việc chấm.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | Đáp án dài 441 token, gần nhất ngân sách Planner trong lô (600 token cho tối đa 3 snippet) dù chưa bị cắt. Ý (b) về sửa chính một prototype (Object.prototype, ValidityCell) là thao tác khác với setPrototypeOf trên object đã tạo và làm loãng điểm cần chấm. | Rút ý (b) còn một câu (sửa prototype cũng làm inline cache của các object kế thừa miss) hoặc bỏ; giữ ba điểm cần chấm: engine tối ưu theo shape/prototype ổn định, đổi prototype làm shape và inline cache mất hiệu lực lan sang code khác, thay bằng Object.create() hoặc class extends. |
| minor | interview_fit | Thuật ngữ riêng của V8 (HiddenClass, ValidityCell) không nên là thứ chấm: ứng viên dùng thuật ngữ engine-neutral (shape, inline cache, deoptimization) vẫn phải được tính đúng. | Ghi trong junior guide rằng V8 chỉ là ví dụ; must-have viết engine-neutral. |

**Kiểm chứng:**
- `supported` Đổi [[Prototype]] của object là thao tác rất chậm trên mọi engine
  > Changing the [[Prototype]] of an object is, by the nature of how modern JavaScript engines optimize property accesses, currently a very slow operation in every browser and JavaScript engine.  
  > — https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Object/setPrototypeOf
- `supported` Tác động không dừng ở dòng gọi setPrototypeOf mà lan tới mọi code truy cập object có prototype bị đổi
  > the effects of altering inheritance are subtle and far-flung, and are not limited to the time spent in the Object.setPrototypeOf(...) statement  
  > — https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Object/setPrototypeOf
  _Câu gốc tiếp: but may extend to any code that has access to any object whose [[Prototype]] has been altered._
- `supported` Hidden class của V8 lưu số thuộc tính và tham chiếu tới prototype của object
  > This HiddenClass stores meta information about an object, including the number of properties on the object and a reference to the object's prototype.  
  > — https://v8.dev/blog/fast-properties
  _Việc object chuyển sang hidden class khác khi đổi prototype là hệ quả trực tiếp của câu này; blog không nói riêng về setPrototypeOf._
- `supported` Hidden class là định danh shape cho optimizing compiler và inline cache; có shape đã biết thì truy cập thuộc tính được inline
  > The optimizing compiler for instance can directly inline property accesses if it can ensure a compatible objects structure through the HiddenClass.  
  > — https://v8.dev/blog/fast-properties
  _Câu trước đó: HiddenClasses serve as an identifier for the shape of an object and as such a very important ingredient for V8's optimizing compiler and inline caches._
- `supported` ValidityCell của shape prototype bị vô hiệu khi prototype đó hoặc prototype phía trên bị đổi
  > This ValidityCell is invalidated whenever someone changes the associated prototype or any prototype above it.  
  > — https://mathiasbynens.be/notes/prototypes
- `supported` Khi prototype đổi, inline cache miss ở lần chạy kế và hiệu năng kém đi
  > When the prototype is changed, a new shape is allocated and the previous ValidityCell is invalidated. So the Inline Cache misses the next time it's executed, resulting in worse performance.  
  > — https://mathiasbynens.be/notes/prototypes
  _Cùng trang: sửa Object.prototype làm mất inline cache của mọi prototype bên dưới._
- `supported` Nên tạo object với prototype mong muốn ngay từ đầu bằng Object.create()
  > if you are concerned about performance, you should avoid setting the [[Prototype]] of an object. Instead, create a new object with the desired [[Prototype]] using Object.create().  
  > — https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Object/setPrototypeOf
- `supported` class với extends thiết lập prototype lúc định nghĩa nên không cần đổi sau
  > extends sets the prototype for both ChildClass and ChildClass.prototype.  
  > — https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Classes/extends

**Độ khó:** hard thật · hợp level middle, senior — Hỏi 'vì sao' cần hiểu cách engine tối ưu truy cập thuộc tính (internals) chứ không chỉ biết cảnh báo của MDN; middle thường biết 'nên tránh', senior giải thích được hidden class, inline cache và tác động lan rộng. Câu ngắn nên cần được người phỏng vấn hỏi mở thêm.
**Dùng trong phỏng vấn:** ~3 phút, 2 ý hỏi, chấm được — Hai ý liên kết (vì sao chậm, thay bằng gì), ba điểm must-have, khoảng 3 phút; câu hỏi 101 ký tự.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu engine JavaScript tối ưu truy cập thuộc tính dựa trên cấu trúc object ổn định và vì sao đổi prototype sau khi tạo phá tối ưu đó.
- Ý bắt buộc: Engine (như V8) gắn cho mỗi object một hidden class/shape gồm cấu trúc và tham chiếu prototype; inline cache và optimizing compiler dựa vào shape để truy cập thuộc tính nhanh.; setPrototypeOf đổi prototype nên object chuyển sang shape khác, inline cache dựa trên shape cũ miss; MDN gọi đây là thao tác rất chậm trên mọi engine.; Tác động lan tới mọi code truy cập các object có prototype bị đổi, không chỉ dòng gọi setPrototypeOf.; Thay thế: tạo object với prototype mong muốn ngay từ đầu bằng Object.create(), hoặc dùng class với extends.
- Dấu hiệu trả lời sai: Cho rằng chỉ riêng lệnh gọi setPrototypeOf chậm, không ảnh hưởng code khác.; Gán __proto__ hoặc setPrototypeOf trong vòng lặp tạo object.; Giải thích bằng 'bộ nhớ' hay 'garbage collection' mà không nhắc tối ưu truy cập thuộc tính.
- Câu hỏi nối tiếp: Vì sao Object.create(proto) không gặp vấn đề hiệu năng này, trong khi setPrototypeOf lên object có sẵn thì có?

