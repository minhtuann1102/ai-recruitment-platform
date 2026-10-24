# Các chỗ đã sửa trong seed cặp hard (nhánh `fix/data-pipeline/hard-pair-review-fixes`)

Đọc file này thay cho trang duyệt: trang duyệt vẫn hiện câu hỏi/đáp án **trước khi sửa**.
Mỗi cặp: vấn đề major/critical mà bản sửa xử lý, rồi từng chỗ sửa (cũ → mới).
Chỉ sửa vấn đề critical/major; gợi ý mức minor (kể cả đề xuất tách câu hỏi mà rubric v2 hạ xuống minor)
không áp dụng. Câu chữ mới do Claude viết: hãy đọc như một bản nháp cần duyệt.

- 38 cặp có thay đổi; 1112 và 1120 không đổi seed (claim đã xác minh tại máy, chuyển sang Đạt).
- Cặp golden (đáp án đổi thì cần chạy lại golden eval): de-qa-1008, de-qa-1012, de-qa-1020, de-qa-1167, de-qa-1252.

## frontend

### de-qa-1251

- **[major · factual]** Câu 'Nếu gộp cả hai bằng AbortSignal.any(...) thì không còn phân biệt bằng tên lỗi được nữa' sai: signal gộp lấy reason của signal abort trước, và fetch reject với reason đó. Evaluator dùng đáp án này sẽ trừ điểm ứng viên nói đúng rằng vẫn bắt được err.name === 'TimeoutError'. Đáp án còn tự mâu thuẫn: code dùng any() nhưng mục phân loại lỗi lại dựa vào AbortError/TimeoutError.
- **claim unverified:** fetch không có timeout mặc định nên spinner có thể quay mãi
- **claim contradicted:** Gộp bằng AbortSignal.any([ctrl.signal, AbortSignal.timeout(5000)]) thì không còn phân biệt timeout với hủy bằng tên lỗi
- **Không đổi câu hỏi** dù reviewer đề xuất tách (rubric v2 không còn tính câu hỏi là quá rộng).

**Sửa 1 — cũ:**

> `fetch` không có timeout mặc định. Nó chỉ reject

**Sửa 1 — mới:**

> Fetch API không có tùy chọn timeout; không tự đặt thì request chậm có thể treo rất lâu. `fetch` chỉ reject

**Sửa 2 — cũ:**

> Nếu gộp cả hai bằng `AbortSignal.any([ctrl.signal, AbortSignal.timeout(5000)])` thì không còn phân biệt bằng tên lỗi được nữa. Lúc đó phải kiểm tra signal nào đã aborted hoặc đọc `signal.reason`.

**Sửa 2 — mới:**

> Khi gộp cả hai bằng `AbortSignal.any([ctrl.signal, AbortSignal.timeout(5000)])`, signal gộp mang reason của signal bị abort trước, nên fetch vẫn reject với `TimeoutError` (hết giờ) hoặc `AbortError` (bị hủy) và vẫn phân loại theo `err.name` được.

### de-qa-1252 · golden

- **[major · length]** Chunk ~732 token, vượt budget 600. Điểm cắt (~1800 ký tự) rơi vào giữa mục 3 (next/dynamic); toàn bộ mục 4 về suppressHydrationWarning bị mất, trong khi câu hỏi hỏi thẳng 'khi nào dùng suppressHydrationWarning'. Planner sẽ nhận snippet thiếu đúng ý được hỏi.

**Sửa 1 — cũ:**

> - Dữ liệu phụ thuộc thời gian, múi giờ, locale: `new Date()`, `toLocaleString()` (server chạy UTC, client ở giờ Việt Nam).
> - Nhánh `typeof window !== 'undefined'`, hoặc đọc `localStorage`/`matchMedia` ngay trong render.
> - Browser extension sửa DOM; iOS tự biến số điện thoại thành link (tắt bằng meta `format-detection`).
> - CDN/edge sửa HTML (ví dụ auto minify), hoặc thư viện CSS-in-JS cấu hình sai.
> - HTML lồng sai (`<div>` trong `<p>`, `<a>` trong `<a>`): parser trình duyệt tự sửa DOM nên lệch với cây React. Lỗi này thường gặp ở mọi người dùng.

**Sửa 1 — mới:**

> - Thời gian, múi giờ, locale: `new Date()`, `toLocaleString()` (server chạy UTC, client ở giờ Việt Nam).
> - API chỉ có ở trình duyệt đọc ngay trong render: nhánh `typeof window`, `localStorage`, `matchMedia`.
> - Môi trường sửa DOM: browser extension, iOS tự biến số điện thoại thành link, CDN/edge sửa HTML. (HTML lồng sai như `<div>` trong `<p>` cũng gây mismatch, nhưng thường ở mọi người dùng.)

**Sửa 2 — cũ:**

> **Chẩn đoán:** đọc diff trong dev overlay, tái hiện với timezone/locale khác, thử trình duyệt không có extension, theo dõi lỗi client trong production.

**Sửa 2 — mới:**

> **Chẩn đoán:** đọc diff trong dev overlay, tái hiện với timezone/locale khác.

**Sửa 3 — cũ:**

>  React cũng không đảm bảo sẽ vá các thuộc tính bị lệch.

**Sửa 3 — mới:**

> *(xóa)*

**Sửa 4 — cũ:**

> Cái giá là component render hai lần và UI có thể "nhảy" sau hydrate.

**Sửa 4 — mới:**

> Đổi lại component render hai lần, UI có thể "nhảy".

**Sửa 5 — cũ:**

>  Phần đó mất HTML prerender (ảnh hưởng SEO và hiển thị ban đầu).

**Sửa 5 — mới:**

>  Phần đó mất HTML prerender.

### de-qa-1255

- **[major · factual]** Claim cốt lõi cho triệu chứng thứ hai (rollback bằng snapshot toàn list xóa mất thay đổi của mutation khác) không có nguồn xác nhận; đây là suy luận. Đáp án cũng không nói rằng invalidate trong onSettled thường kéo state đúng từ server về sau, nên trình bày như mất dữ liệu vĩnh viễn.
- **claim unverified:** Rollback bằng snapshot toàn list của mutation A (chụp trước B) xóa mất thay đổi hợp lệ của B khi A lỗi
- **Lưu ý:** Không áp ý đổi tên 'onMutateResult' trong đề xuất vì chưa có câu trích nguồn.

**Sửa 1 — cũ:**

> Snapshot toàn cục không kết hợp được khi có nhiều mutation đồng thời.

**Sửa 1 — mới:**

> Snapshot toàn cục không kết hợp được khi có nhiều mutation đồng thời. Lỗi này thường chỉ tạm thời: invalidate trong `onSettled` sẽ refetch state đúng từ server, nhưng UI vẫn sai trong khoảng đó (và sai hẳn nếu bỏ invalidate).

### de-qa-1258

- **[major · factual]** Claim then chốt cho type guard sơ sài ('compiler narrow theo boolean mà không kiểm chứng thân hàm') chưa có nguồn chính thức xác nhận. Nó có vẻ đúng, nhưng theo rubric một claim chưa xác minh thì chưa đạt.
- **claim unverified:** Compiler không kiểm chứng thân guard có kiểm đủ hay không, nên guard sơ sài thực chất là phép cast trá hình

**Sửa 1 — cũ:**

> Compiler narrow theo kết quả boolean mà không kiểm chứng thân hàm có kiểm tra đủ hay không. Guard sơ sài thực chất là một phép cast trá hình.

**Sửa 1 — mới:**

> TypeScript narrow theo kết quả true/false của guard mỗi khi nó được gọi; kiểm tra trong thân guard đủ hay chưa là trách nhiệm của người viết. Guard chỉ kiểm `'id' in x` vẫn để lọt dữ liệu sai.

### de-qa-1260

- **[major · factual]** Câu 'Vẫn phải ... chủ động trả focus khi đóng: lưu document.activeElement trước khi mở, đừng mặc định trình duyệt sẽ làm' mâu thuẫn với HTML spec: <dialog> lưu 'previously focused element' khi mở và trình duyệt focus lại nó khi đóng dialog modal. Evaluator dùng đáp án này có thể trừ điểm ứng viên nói đúng rằng showModal()/close() tự trả focus.
- **claim contradicted:** Với <dialog> native vẫn phải tự lưu document.activeElement và trả focus khi đóng, đừng mặc định trình duyệt sẽ làm
- **Không đổi câu hỏi** dù reviewer đề xuất tách (rubric v2 không còn tính câu hỏi là quá rộng).

**Sửa 1 — cũ:**

> Vẫn phải tự lo nhãn và chủ động trả focus khi đóng: lưu `document.activeElement` trước khi mở, đừng mặc định trình duyệt sẽ làm.

**Sửa 1 — mới:**

> Vẫn phải tự lo nhãn (`aria-labelledby`). Theo HTML spec, khi đóng dialog modal trình duyệt tự trả focus về phần tử đã focus trước khi mở; chỉ cần tự xử lý khi phần tử đó không còn hoặc luồng cần focus chỗ khác, và nên kiểm thử trên trình duyệt mục tiêu.

## devops

### de-qa-1203

- **[major · length]** ~806 token; điểm cắt 600 token rơi giữa nguyên nhân 7. Mất NetworkPolicy, bước 'cô lập lỗi: gọi thẳng PodIP:port từ Pod khác' (ý quan trọng nhất của quy trình) và phần phòng ngừa.

**Sửa 1 — cũ:**

> Lỗi chỉ xảy ra với một phần request nghĩa là trong pool có vài endpoint xấu.

**Sửa 1 — mới:**

> Lỗi chỉ xảy ra với một phần request nghĩa là trong pool có vài endpoint xấu.
>
> **Cô lập lỗi trước:** gọi thẳng từng `PodIP:port` từ một Pod khác để tách lỗi của Service khỏi lỗi của Pod. Image distroless không có shell thì thêm ephemeral container: `kubectl debug -it <pod> --image=busybox --target=<container>`.

**Sửa 2 — cũ:**

> ; hoặc port khai báo dạng chuỗi `"9376"` thay vì số

**Sửa 2 — mới:**

> *(xóa)*

**Sửa 3 — cũ:**

> 5. **Restart thường xuyên** (cột `RESTARTS`) gây lỗi ngắt quãng.
> 6. **Lúc rollout:** app thoát ngay khi nhận SIGTERM trong lúc các node chưa cập nhật rule, nên request bị refused.
> 7. **kube-proxy hỏng trên một node:** lỗi chỉ xuất hiện với client ở node đó. Kiểm `iptables-save | grep payments` hoặc `ipvsadm -ln` trên node và đọc log kube-proxy.
> 8. **NetworkPolicy** chặn traffic từ một số namespace.
>
> **Cô lập lỗi:** gọi thẳng từng `PodIP:port` từ một Pod khác để tách lỗi của Service khỏi lỗi của Pod.
> - Image distroless không có shell: dùng `kubectl debug -it <pod> --image=busybox --target=<container>` để thêm ephemeral container dùng chung process namespace với container đích.
> - Debug trên bản sao Pod mà không đụng Pod thật: dùng `kubectl debug <pod> --copy-to=<tên> --share-processes`.

**Sửa 3 — mới:**

> 5. **Khác:** app thoát ngay khi nhận SIGTERM lúc rollout trong khi các node chưa cập nhật rule; Pod restart thường xuyên (cột `RESTARTS`); kube-proxy hỏng trên một node (lỗi chỉ với client ở node đó: `iptables-save | grep payments` hoặc `ipvsadm -ln`, log kube-proxy); NetworkPolicy chặn traffic từ một số namespace.

### de-qa-1206

- **[major · outdated]** Đáp án đưa `terraform state mv` làm cách chính để chuyển resource sang state khác. Trên backend remote (S3, HCP Terraform) cách này không áp dụng trực tiếp; option sang file khác là legacy, chỉ cho local state. Ứng viên trả lời theo cách hiện đại có thể bị chấm lệch.
- **claim outdated:** Chuyển resource sang state khác bằng `terraform state mv`
- **Lưu ý:** Không áp nửa câu về `terraform_remote_state` trong đề xuất vì chưa có câu trích nguồn.

**Sửa 1 — cũ:**

>   - Sang state khác: `terraform state mv`, hoặc import vào state mới rồi `state rm` ở state cũ.

**Sửa 1 — mới:**

>   - Sang state khác: `import` block ở state mới, rồi `removed` block hoặc `terraform state rm` ở state cũ (`state mv` sang file state khác là option legacy, chỉ cho local state).

### de-qa-1211

- **[major · interview_fit]** Đề không nêu loại load balancer và kể kết quả 'mọi target bị đánh unhealthy, hệ thống sập hẳn'. Đáp án lại chỉ đưa ví dụ ALB, vốn fail open nên sẽ không rút hết target. Ứng viên nêu fail open có thể bị chấm là mâu thuẫn với đề, còn ứng viên nói 'LB rút hết' thì sai với ALB.
- **Lưu ý:** Câu hỏi thu hẹp KHÁC đề xuất: reviewer đề xuất nhắc cả nginx upstream, nhưng nginx bản mở chỉ có passive check (không gọi /health), nên câu mới chỉ giữ readiness probe của Kubernetes.

**Câu hỏi cũ:**

> Endpoint `/health` dùng cho load balancer kiểm tra luôn kết nối tới DB và Redis. Một lần DB chậm vài phút, mọi target bị đánh unhealthy và hệ thống sập hẳn, kể cả các endpoint không cần DB. Phân tích failure mode này và thiết kế lại health check ở tầng load balancer/proxy.

**Câu hỏi mới:**

> Endpoint `/health` của API kiểm tra luôn kết nối tới DB và Redis, và được dùng làm readiness probe trên Kubernetes. Một lần DB chậm vài phút, mọi Pod bị đánh NotReady và hệ thống sập hẳn, kể cả các endpoint không cần DB. Phân tích failure mode này và thiết kế lại health check.

**Sửa 1 — cũ:**

> **Hành vi khác nhau giữa các load balancer:**
> - **ALB:** khi mọi target trong target group đều unhealthy, ALB **fail open**, tức là route tới tất cả target bất kể trạng thái health. Health check sâu vì vậy không bảo vệ được gì khi sự cố là chung, chỉ gây nhiễu và chậm hồi phục.

**Sửa 1 — mới:**

> **Vì sao sập hẳn:** Pod NotReady bị gỡ khỏi endpoint của Service; mọi Pod cùng NotReady thì Service không còn endpoint nào để route.
>
> **Đối chiếu ALB:** khi mọi target trong target group đều unhealthy, ALB **fail open**, tức là route tới tất cả target bất kể trạng thái health. Dù vậy, health check sâu vẫn không bảo vệ được gì khi sự cố là chung, chỉ gây nhiễu và chậm hồi phục.

### de-qa-1217

- **[major · length]** ~685 token; điểm cắt rơi ngay đầu mục 'Giữ build đúng và an toàn' (build phải đúng khi cache miss, chống cache poisoning từ PR không tin cậy). Đây là vế thứ hai của câu hỏi nên snippet của Planner thiếu ý bắt buộc.

**Sửa 1 — cũ:**

> **Giữ build đúng và an toàn**
> - Cache chỉ là tối ưu: build phải cho kết quả đúng ngay cả khi cache miss. Định kỳ build không dùng cache để phát hiện phụ thuộc ngầm.
> - Chống cache poisoning: cache do PR không tin cậy ghi ra không được dùng cho build release. Build release chạy trên branch được bảo vệ.

**Sửa 1 — mới:**

> *(xóa)*

**Sửa 2 — cũ:**

> **Đo trước khi tối ưu:** đo thời gian từng stage và tỉ lệ cache hit, rồi tối ưu chỗ tốn nhiều nhất.

**Sửa 2 — mới:**

> **Đo trước khi tối ưu:** đo thời gian từng stage và tỉ lệ cache hit, rồi tối ưu chỗ tốn nhiều nhất.
>
> **Giữ build đúng và an toàn**
> - Cache chỉ là tối ưu: build phải cho kết quả đúng ngay cả khi cache miss. Định kỳ build không dùng cache để phát hiện phụ thuộc ngầm.
> - Chống cache poisoning: cache do PR không tin cậy ghi ra không được dùng cho build release. Build release chạy trên branch được bảo vệ.

**Sửa 3 — cũ:**

> - Cache không được truy cập quá 7 ngày sẽ bị xóa; giới hạn mặc định 10 GB mỗi repo.

**Sửa 3 — mới:**

> *(xóa)*

## java

### de-qa-1105

- **[major · length]** Chunk ~680 token; điểm cắt 600 token rơi ngay trước 'Trade-off' của ZGC, trong khi câu hỏi yêu cầu nêu trade-off. Snippet của Planner mất đúng ý được hỏi.
- **Không đổi câu hỏi** dù reviewer đề xuất tách (rubric v2 không còn tính câu hỏi là quá rộng).

**Sửa 1 — cũ:**

> Cách G1 làm việc: G1 (collector mặc định) chia heap thành các region bằng nhau, mỗi pause sơ tán (copy) object sống của một tập region. Khi old gen vượt ngưỡng Initiating Heap Occupancy (mặc định 45%, có cơ chế adaptive), G1 chạy concurrent marking rồi sang pha space-reclamation gồm các mixed collection sơ tán thêm region old. G1 nhắm mục tiêu pause mềm -XX:MaxGCPauseMillis, mặc định 200 ms; nó không phải collector real-time.

**Sửa 1 — mới:**

> Cách G1 làm việc: G1 (collector mặc định) chia heap thành các region, mỗi pause sơ tán (copy) object sống của một tập region; khi old gen vượt ngưỡng Initiating Heap Occupancy, G1 chạy concurrent marking rồi các mixed collection sơ tán thêm region old. -XX:MaxGCPauseMillis (mặc định 200 ms) chỉ là mục tiêu mềm; G1 không phải collector real-time.

**Sửa 2 — cũ:**

> Tune G1: đặt MaxGCPauseMillis gần SLO (mỗi pause làm ít việc hơn, đổi lại GC chạy dày hơn, tốn throughput); tăng headroom heap; tăng G1HeapRegionSize (lũy thừa 2, 1–32 MB) để buffer lớn không còn humongous; giảm cấp phát trong code. Mỗi lần đổi một tham số rồi đo lại bằng GC log và p99 thật.

**Sửa 2 — mới:**

> Tune G1: đặt MaxGCPauseMillis gần SLO (đổi lại GC chạy dày hơn, tốn throughput); tăng headroom heap; tăng G1HeapRegionSize (lũy thừa 2, 1–32 MB) để buffer lớn không còn humongous; giảm cấp phát; mỗi lần đổi một tham số rồi đo lại.

**Sửa 3 — cũ:**

> Khi nào chọn ZGC: cần pause rất thấp, không phụ thuộc kích thước heap. ZGC làm gần hết việc đồng thời với ứng dụng; JEP 439 đặt mục tiêu pause không vượt 1 ms, heap từ vài trăm MB tới nhiều TB. Generational ZGC có từ JDK 21 (-XX:+UseZGC -XX:+ZGenerational) và là chế độ mặc định của -XX:+UseZGC từ JDK 23. Trade-off: tốn thêm CPU cho thread GC đồng thời, cần headroom bộ nhớ; nếu tốc độ cấp phát vượt tốc độ thu gom, thread ứng dụng bị allocation stall và latency vẫn tăng. Workload ưu tiên throughput (batch) thường hợp với G1 hoặc Parallel GC hơn.

**Sửa 3 — mới:**

> Khi nào chọn ZGC: cần pause rất thấp, không phụ thuộc kích thước heap. Trade-off: tốn thêm CPU cho thread GC đồng thời, cần headroom bộ nhớ; nếu tốc độ cấp phát vượt tốc độ thu gom, thread ứng dụng bị allocation stall và latency vẫn tăng. Workload ưu tiên throughput (batch) thường hợp với G1 hoặc Parallel GC hơn. ZGC làm gần hết việc đồng thời với ứng dụng; JEP 439 đặt mục tiêu pause không vượt 1 ms, heap từ vài trăm MB tới nhiều TB. Generational ZGC có từ JDK 21 (-XX:+UseZGC -XX:+ZGenerational) và là chế độ mặc định của -XX:+UseZGC từ JDK 23.

### de-qa-1113

- **[major · length]** Chunk ~802 token; điểm cắt 600 token rơi đúng đầu đoạn 'Khi nào tắt CSRF an toàn', nên snippet mất hẳn một ý được hỏi trực tiếp.
- **Không đổi câu hỏi** dù reviewer đề xuất tách (rubric v2 không còn tính câu hỏi là quá rộng).

**Sửa 1 — cũ:**

> Luồng request: servlet container không biết bean Spring, nên Spring đăng ký DelegatingFilterProxy như một Filter chuẩn, và nó ủy quyền (lookup lazy) cho bean FilterChainProxy. FilterChainProxy là điểm vào của Spring Security: chọn SecurityFilterChain phù hợp, đồng thời làm việc bắt buộc như xóa SecurityContext để tránh leak và áp HttpFirewall. Chỉ chain đầu tiên khớp request được gọi; các chain sau bị bỏ qua dù cũng khớp.

**Sửa 1 — mới:**

> Luồng request: servlet container không biết bean Spring, nên Spring đăng ký DelegatingFilterProxy như một Filter chuẩn, và nó ủy quyền (lookup lazy) cho bean FilterChainProxy. FilterChainProxy chọn SecurityFilterChain phù hợp; chỉ chain đầu tiên khớp request được gọi, các chain sau bị bỏ qua dù cũng khớp.

**Sửa 2 — cũ:**

> Trong một chain, filter chạy theo thứ tự cố định, ví dụ SecurityContextHolderFilter, CsrfFilter, các filter xác thực, ExceptionTranslationFilter, AuthorizationFilter. ExceptionTranslationFilter chuyển AuthenticationException (chưa xác thực) cho AuthenticationEntryPoint, với API thường là 401 kèm header WWW-Authenticate, với web là redirect tới trang login; còn AccessDeniedException (đã xác thực nhưng thiếu quyền) đi tới AccessDeniedHandler, thường trả 403.

**Sửa 2 — mới:**

> Trong chain, ExceptionTranslationFilter chuyển AuthenticationException (chưa xác thực) thành 401 với API hoặc redirect tới trang login với web; AccessDeniedException (đã xác thực nhưng thiếu quyền) thường thành 403.

**Sửa 3 — cũ:**

> Khi nào tắt CSRF an toàn: Spring khuyến nghị bật CSRF cho mọi request có thể được trình duyệt của người dùng xử lý, chỉ nên tắt khi service hoàn toàn phục vụ client không phải trình duyệt. Mấu chốt là trình duyệt có tự đính kèm credential không: token trong header Authorization do code client tự gắn thì không bị CSRF theo cách đó. Nhưng stateless không đồng nghĩa an toàn: nếu JWT nằm trong cookie, hoặc dùng basic auth, trình duyệt tự gửi credential và ứng dụng vẫn dễ bị CSRF. Ngoài ra GET, HEAD, OPTIONS, TRACE phải chỉ đọc thì CSRF protection mới có tác dụng. Vì vậy chỉ tắt CSRF trên chain API dùng bearer header, không tắt toàn cục.

**Sửa 3 — mới:**

> Khi nào tắt CSRF an toàn: Spring khuyến nghị bật CSRF cho mọi request có thể được trình duyệt của người dùng xử lý. Mấu chốt là trình duyệt có tự đính kèm credential không: token trong header Authorization do code client tự gắn thì không bị CSRF theo cách đó; nhưng nếu JWT nằm trong cookie hoặc dùng basic auth, trình duyệt tự gửi credential và ứng dụng vẫn dễ bị CSRF. Vì vậy chỉ tắt CSRF trên chain API dùng bearer header, không tắt toàn cục.

### de-qa-1114

- **[major · length]** Chunk ~837 token; điểm cắt 600 token rơi ở ý 4 (ordering), mất phần thiết kế starter và toàn bộ phần debug được hỏi trực tiếp.
- **Không đổi câu hỏi** dù reviewer đề xuất tách (rubric v2 không còn tính câu hỏi là quá rộng).

**Sửa 1 — cũ:**

>  Auto-configuration là non-invasive: ứng dụng tự định nghĩa bean (ví dụ DataSource) thì phần mặc định tương ứng rút lui.

**Sửa 1 — mới:**

> *(xóa)*

**Sửa 2 — cũ:**

>  Tài liệu yêu cầu auto-configuration chỉ được nạp qua file imports, đặt trong package riêng, không bao giờ là mục tiêu component scan và không tự bật component scan (dùng @Import cụ thể).

**Sửa 2 — mới:**

>  Auto-configuration phải nằm trong package riêng, chỉ nạp qua file imports, không bao giờ bị component scan.

**Sửa 3 — cũ:**

> 3. @ConditionalOnBean/@ConditionalOnMissingBean đánh giá dựa trên những gì đã xử lý tới thời điểm đó, nên chỉ nên dùng trên auto-configuration. Kiểu trả về của @Bean nên cụ thể nhất có thể để điều kiện so khớp đúng.
> 4. Phụ thuộc giữa các auto-configuration: dùng before/after trên @AutoConfiguration (hoặc @AutoConfigureBefore/After). Thứ tự này chỉ quyết định thứ tự đăng ký bean definition, không phải thứ tự tạo bean.
>
> Thiết kế starter: tên module không bắt đầu bằng spring-boot (acme-spring-boot-starter); property gom vào @ConfigurationProperties("acme") với namespace riêng, có Javadoc cho từng trường để sinh metadata cho IDE; không dùng namespace của Boot như spring, server, management.
>
> Debug: chạy với --debug để in conditions report (điều kiện nào khớp, không khớp và lý do). Tắt auto-configuration không mong muốn bằng @SpringBootApplication(exclude = ...) hoặc spring.autoconfigure.exclude. Kiểm thử bằng ApplicationContextRunner: dựng context với từng tổ hợp classpath, bean, property rồi khẳng định bean có hay không, thay vì phải khởi động cả ứng dụng.

**Sửa 3 — mới:**

> 3. @ConditionalOnBean/@ConditionalOnMissingBean đánh giá dựa trên những gì đã xử lý tới thời điểm đó, nên chỉ dùng trên auto-configuration, với kiểu trả về @Bean cụ thể nhất có thể. Thứ tự giữa các auto-configuration đặt bằng before/after trên @AutoConfiguration; nó chỉ quyết định thứ tự đăng ký bean definition, không phải thứ tự tạo bean.
>
> Debug: chạy với --debug để in conditions report (điều kiện nào khớp, không khớp và lý do). Kiểm thử bằng ApplicationContextRunner: dựng context với từng tổ hợp classpath, bean, property rồi khẳng định bean có hay không, thay vì khởi động cả ứng dụng. Tắt auto-configuration không mong muốn bằng @SpringBootApplication(exclude = ...) hoặc spring.autoconfigure.exclude.
>
> Thiết kế starter: tên module không bắt đầu bằng spring-boot (acme-spring-boot-starter); property gom vào @ConfigurationProperties("acme") với namespace riêng, không dùng namespace của Boot như spring, server, management.

### de-qa-1115

- **[major · length]** Chunk ~819 token; điểm cắt 600 token rơi giữa phần chẩn đoán, mất cách dùng Actuator env và toàn bộ phần tổ chức config/secret được hỏi trực tiếp.
- **Không đổi câu hỏi** dù reviewer đề xuất tách (rubric v2 không còn tính câu hỏi là quá rộng).

**Sửa 1 — cũ:**

> Thứ tự ưu tiên (nguồn sau ghi đè nguồn trước, rút gọn): default properties, @PropertySource, config data (application.*), OS environment variables, Java system properties, SPRING_APPLICATION_JSON, command line arguments; trong test còn có properties của @SpringBootTest, @DynamicPropertySource, @TestPropertySource.

**Sửa 1 — mới:**

> Thứ tự ưu tiên (nguồn sau ghi đè nguồn trước, rút gọn): default properties, @PropertySource, config data (application.*), OS environment variables, Java system properties, SPRING_APPLICATION_JSON, command line arguments.

**Sửa 2 — cũ:**

> 4. Khai báo spring.profiles.active trong file theo profile hoặc document có spring.config.activate.on-profile: cấu hình này không hợp lệ.
> 5. Giá trị đặt bằng @PropertySource có ưu tiên thấp hơn application.* và được nạp lúc context refresh, quá muộn cho logging.* và spring.main.*.

**Sửa 2 — mới:**

> 4. Khai báo spring.profiles.active trong file theo profile (hoặc document có spring.config.activate.on-profile) là cấu hình không hợp lệ.

**Sửa 3 — cũ:**

> - Gom cấu hình vào @ConfigurationProperties có kiểu, kèm validation để fail-fast khi thiếu hoặc sai giá trị; dùng profile group (production gồm proddb, prodmq) thay vì liệt kê nhiều profile rời rạc.
> - Hạn chế số tầng ghi đè và quy ước rõ nguồn sự thật cho từng nhóm property.

**Sửa 3 — mới:**

> - Gom cấu hình vào @ConfigurationProperties có kiểu, kèm validation để fail-fast; dùng profile group thay vì nhiều profile rời rạc; hạn chế số tầng ghi đè.

### de-qa-1118

- **[major · length]** Chunk ~818 token; điểm cắt 600 token rơi đúng đầu ý 'Database thật thay H2', mất toàn bộ phần Testcontainers mà câu hỏi nêu tên, cùng trade-off.
- **Không đổi câu hỏi** dù reviewer đề xuất tách (rubric v2 không còn tính câu hỏi là quá rộng).

**Sửa 1 — cũ:**

> Cơ chế: Spring TestContext lưu ApplicationContext trong một cache static, khóa bởi tổ hợp cấu hình: classes/locations, initializers, context customizers (gồm @DynamicPropertySource và các bean override như @MockitoBean, @MockitoSpyBean), active profiles, @TestPropertySource... Test class có cùng tổ hợp dùng chung context; khác một chi tiết là phải dựng context mới. Cache chỉ có tác dụng khi các test chạy trong cùng process (fork riêng cho từng test class sẽ vô hiệu hóa nó); mặc định giữ tối đa 32 context, vượt thì loại theo LRU.

**Sửa 1 — mới:**

> Cơ chế: Spring TestContext lưu ApplicationContext trong một cache static, khóa bởi tổ hợp cấu hình (classes, initializers, context customizers gồm @DynamicPropertySource và bean override như @MockitoBean, active profiles, @TestPropertySource...). Test class có cùng tổ hợp dùng chung context; khác một chi tiết là phải dựng context mới. Cache chỉ có tác dụng trong cùng process; mặc định giữ tối đa 32 context, vượt thì loại theo LRU.

**Sửa 2 — cũ:**

> - Test slice: @WebMvcTest chỉ nạp hạ tầng MVC và bean web (controller, @ControllerAdvice, converter, filter...), collaborator thay bằng @MockitoBean; @DataJpaTest chỉ nạp JPA, mặc định mỗi test chạy trong transaction và rollback. Nhanh, cô lập lỗi, nhưng không bắt được lỗi nối giữa các lớp.
> - Chuẩn hóa vài base class hoặc meta-annotation có cùng tập mock và profile để tăng cache hit; thay @DirtiesContext bằng dọn dữ liệu chủ động.
> - Database thật thay H2:

**Sửa 2 — mới:**

> - Test slice: @WebMvcTest chỉ nạp hạ tầng MVC và bean web, collaborator thay bằng @MockitoBean; @DataJpaTest chỉ nạp JPA, mặc định mỗi test chạy trong transaction và rollback. Nhanh, nhưng không bắt được lỗi nối giữa các lớp.
> - Database thật thay H2:

**Sửa 3 — cũ:**

> - @SpringBootTest với RANDOM_PORT:

**Sửa 3 — mới:**

> - Chuẩn hóa vài base class hoặc meta-annotation có cùng tập mock và profile để tăng cache hit; thay @DirtiesContext bằng dọn dữ liệu chủ động.
> - @SpringBootTest với RANDOM_PORT:

### de-qa-1119

- **[major · interview_fit]** Rubric v2 vẫn tính là quá rộng (3 ý độc lập, ~5 phút): ba triệu chứng có ba cơ chế khác nhau: ngữ nghĩa spy, strict stubbing, và giới hạn của mock so với test tích hợp. Câu hỏi có 3 ý hỏi (phân biệt mock/stub/spy, pitfall Mockito, khi nào thay bằng test tích hợp).
- **[major · length]** Chunk ~743 token; điểm cắt 600 token rơi ngay sau tiêu đề 'Khi nào thay bằng test tích hợp', mất toàn bộ ý được hỏi trực tiếp này.

**Câu hỏi cũ:**

> Unit test Mockito của OrderService đều xanh, nhưng production lỗi vì câu query JPA sai và vì cổng thanh toán trả lỗi khác với mô phỏng. Trong test còn có `when(spy.calculate(...))` ném exception khó hiểu và nhiều stub thừa. Phân biệt mock, stub, spy; nêu các pitfall khi dùng Mockito và khi nào nên thay mock bằng test tích hợp.

**Câu hỏi mới:**

> Unit test Mockito của OrderService đều xanh, nhưng production lỗi vì câu query JPA sai và vì cổng thanh toán trả lỗi khác với mô phỏng. Vì sao test không bắt được, và khi nào bạn thay mock bằng test tích hợp?

**Sửa 1 — cũ:**

> Phân biệt:
> - Stub: test double trả câu trả lời dựng sẵn để đưa code đang test vào trạng thái cần thử, ví dụ when(repo.findById(1L)).thenReturn(...); test kiểm tra kết quả hoặc trạng thái.
> - Mock: test double mà test kiểm tra tương tác, ví dụ verify(gateway).charge(...); hợp với side effect ra ngoài (gửi email, publish event). Trong Mockito, một mock có thể vừa stub vừa verify.
> - Spy: bọc object thật, mặc định gọi method thật, chỉ ghi đè vài method. Tài liệu Mockito khuyên dùng spy cẩn thận và thỉnh thoảng, ví dụ với code legacy; partial mock không nên dùng cho code mới thiết kế tốt.
>
> Pitfall:
> 1. when(spy.calculate(x)) gọi method thật ngay lúc stub, có thể ném exception hoặc gây side effect. Với spy dùng doReturn(v).when(spy).calculate(x). Method final trên spy cũng gây rắc rối và không verify được.
> 2. Stub thừa, tham số lệch: Mockito mặc định "loose"; bật strict stubbing (Strictness.STRICT_STUBS, có tích hợp qua MockitoExtension của JUnit 5) để báo stub không dùng và argument mismatch.
> 3. Over-mocking: verify từng lời gọi nội bộ làm test dính chặt vào cài đặt, refactor là vỡ dù hành vi không đổi. Chỉ verify tương tác có ý nghĩa nghiệp vụ ở biên; với value object hay collection, dùng object thật.
> 4. Mock thứ mình không kiểm soát (repository JPA, client của bên thứ ba): mock chỉ phản ánh giả định của người viết test, nên JPQL sai, mapping sai, constraint DB hay lỗi thật của gateway không bao giờ lộ ra.

**Sửa 1 — mới:**

> Vì sao test không bắt được: mock thứ mình không kiểm soát (repository JPA, client của bên thứ ba) chỉ phản ánh giả định của người viết test, nên JPQL sai, mapping sai, constraint DB hay lỗi thật của gateway không bao giờ lộ ra. Over-mocking làm tệ hơn: verify từng lời gọi nội bộ làm test dính chặt vào cài đặt, refactor là vỡ dù hành vi không đổi; chỉ verify tương tác có ý nghĩa nghiệp vụ ở biên.

**Sửa 2 — cũ:**

> Tiêu chí: test phải đỏ khi hành vi sai và giữ xanh khi chỉ cài đặt thay đổi.

**Sửa 2 — mới:**

> Tiêu chí: test phải đỏ khi hành vi sai và giữ xanh khi chỉ cài đặt thay đổi.
>
> Kiến thức nền cho follow-up:
> - Stub trả câu trả lời dựng sẵn, test kiểm tra kết quả hoặc trạng thái; mock là test double mà test kiểm tra tương tác (verify(gateway).charge(...)).
> - Spy bọc object thật, mặc định gọi method thật; when(spy.calculate(x)) gọi method thật ngay lúc stub, nên với spy dùng doReturn(v).when(spy).calculate(x). Tài liệu Mockito khuyên dùng spy cẩn thận và thỉnh thoảng, ví dụ với code legacy.
> - Stub thừa, tham số lệch: bật strict stubbing (Strictness.STRICT_STUBS, có tích hợp qua MockitoExtension của JUnit 5) để báo stub không dùng và argument mismatch.

### de-qa-1121

- **[major · length]** Chunk ~782 token; điểm cắt 600 token rơi ngay đầu phần 'Vì sao tách DTO khỏi entity', nên snippet mất hẳn ý hỏi thứ hai.

**Sửa 1 — cũ:**

> - ProblemDetail chứa cả trường chuẩn lẫn không chuẩn; mọi exception có sẵn của Spring MVC implement ErrorResponse nên tự mang status và body.
> - Một @RestControllerAdvice kế thừa ResponseEntityExceptionHandler: lớp này đã xử lý mọi exception của Spring MVC (ví dụ MethodArgumentNotValidException khi @Valid thất bại) thành ProblemDetail. Thêm @ExceptionHandler cho exception nghiệp vụ (OrderNotFound thành 404, InsufficientStock thành 409) và handler cuối cho Exception: log đầy đủ kèm trace id, response chỉ có thông điệp chung.
> - Spring Boot có property spring.mvc.problemdetails.enabled; nếu tự viết advice để thay xử lý một exception có sẵn, phải xếp nó trước handler do Boot cấu hình.
> - Trường mở rộng thêm qua map properties của ProblemDetail (Jackson trải thành thuộc tính JSON cấp cao nhất) hoặc subclass. title/detail có thể resolve qua MessageSource để đa ngôn ngữ; tài liệu Spring khuyên tùy biến để không lộ chi tiết cài đặt.
> - Đóng gói thành thư viện dùng chung để mọi service có cùng contract.

**Sửa 1 — mới:**

> - Mọi exception có sẵn của Spring MVC implement ErrorResponse nên tự mang status và body ProblemDetail.
> - Một @RestControllerAdvice kế thừa ResponseEntityExceptionHandler (đã xử lý exception của Spring MVC, ví dụ MethodArgumentNotValidException khi @Valid thất bại). Thêm @ExceptionHandler cho exception nghiệp vụ (OrderNotFound thành 404, InsufficientStock thành 409) và handler cuối cho Exception: log đầy đủ kèm trace id, response chỉ có thông điệp chung.
> - Trường mở rộng thêm qua map properties của ProblemDetail; tài liệu Spring khuyên tùy biến title/detail để không lộ chi tiết cài đặt. Đóng gói thành thư viện dùng chung để mọi service có cùng contract.

## nodejs

### de-qa-1003

- (chỉ claim chưa có nguồn, không có issue major)
- **claim unverified:** --max-old-space-size không giới hạn bộ nhớ Buffer
- **Không đổi câu hỏi** dù reviewer đề xuất tách (rubric v2 không còn tính câu hỏi là quá rộng).

**Sửa 1 — cũ:**

> process.memoryUsage() tính nó vào external và arrayBuffers, còn --max-old-space-size không giới hạn phần này.

**Sửa 1 — mới:**

> process.memoryUsage() tính nó vào external và arrayBuffers.

### de-qa-1005

- (chỉ claim chưa có nguồn, không có issue major)
- **claim unverified:** Trong container, số core process nhìn thấy thường là của host chứ không phải CPU limit
- **Không đổi câu hỏi** dù reviewer đề xuất tách (rubric v2 không còn tính câu hỏi là quá rộng).

**Sửa 1 — cũ:**

> - Với CPU limit nhỏ (vd 1 core), nhiều worker trong pod chỉ tranh nhau quota; số core process nhìn thấy thường là của máy host chứ không phải limit của container.

**Sửa 1 — mới:**

> - Với CPU limit nhỏ (vd 1 core), nhiều worker trong pod chỉ tranh nhau quota; đặt số worker tường minh thay vì suy từ số core mà process nhìn thấy.

### de-qa-1008 · golden

- (chỉ claim chưa có nguồn, không có issue major)
- **claim unverified:** Fixed window cho phép burst gần gấp đôi limit quanh biên cửa sổ; sliding log tốn bộ nhớ theo số request
- **Không đổi câu hỏi** dù reviewer đề xuất tách (golden, giữ câu hỏi).

**Sửa 1 — cũ:**

> Nhược điểm là burst ở biên: client có thể gửi gần gấp đôi limit trong khoảng ngắn quanh lúc chuyển cửa sổ.

**Sửa 1 — mới:**

> Nhược điểm là burst ở biên: client gửi đủ limit ở cuối cửa sổ này rồi thêm đủ limit ở đầu cửa sổ sau, tức gần gấp đôi limit trong khoảng ngắn quanh lúc chuyển cửa sổ.

### de-qa-1012 · golden

- **[major · length]** 711 token; bị cắt câu 'Sửa: transaction ngắn, side effect sau commit, statement/lock timeout, tính pool theo max_connections' — đây là phần trả lời vế 'pool cạn' của câu hỏi.

**Sửa 1 — cũ:**

>  Đơn giản và nhanh nhất cho bộ đếm.

**Sửa 1 — mới:**

> *(xóa)*

**Sửa 2 — cũ:**

> ; đúng nhưng giảm throughput khi tranh chấp cao, và phải khóa theo thứ tự nhất quán để tránh deadlock.

**Sửa 2 — mới:**

> ; đúng nhưng giảm throughput khi tranh chấp cao.

**Sửa 3 — cũ:**

> 3. Khóa lạc quan: cột version, UPDATE ... WHERE version = $v, không có dòng nào được cập nhật thì retry; hợp khi xung đột hiếm.
> 4. Repeatable Read hoặc Serializable: DB phát hiện xung đột và trả lỗi serialization (SQLSTATE 40001); ứng dụng phải retry cả transaction từ đầu, ORM thường không tự retry.
> Thêm CHECK (remaining >= 0) hoặc unique constraint làm lưới an toàn cuối cùng.

**Sửa 3 — mới:**

> 3. Khóa lạc quan (cột version, retry khi không cập nhật được dòng nào) khi xung đột hiếm; hoặc Repeatable Read/Serializable: DB trả lỗi serialization (SQLSTATE 40001), ứng dụng phải retry cả transaction, ORM thường không tự retry. Thêm CHECK (remaining >= 0) làm lưới an toàn cuối cùng.

**Sửa 4 — cũ:**

> - Transaction giữ một connection từ BEGIN tới COMMIT. Gọi HTTP (cổng thanh toán, gửi email) hoặc chờ lock lâu bên trong transaction làm connection bị giữ, pool nhỏ nhanh chóng cạn.

**Sửa 4 — mới:**

> - Transaction giữ một connection từ BEGIN tới COMMIT; gọi HTTP (cổng thanh toán, email) hoặc chờ lock lâu bên trong transaction làm pool nhỏ nhanh chóng cạn.

### de-qa-1020 · golden

- **[major · length]** Phần cắt ở 600 token rơi vào mục 'Lưu ở client': mất ý chống CSRF cho endpoint refresh và ý giữ access token trong bộ nhớ thay vì localStorage, trong khi câu hỏi hỏi trực tiếp nơi lưu token.
- **Không đổi câu hỏi** dù reviewer đề xuất tách (golden, giữ câu hỏi).

**Sửa 1 — cũ:**

>  RFC 9700 (OAuth 2.0 Security BCP) yêu cầu refresh token của public client phải sender-constrained hoặc dùng rotation, và nên hết hạn khi client không hoạt động một thời gian.

**Sửa 1 — mới:**

>  RFC 9700 yêu cầu refresh token của public client phải sender-constrained hoặc dùng rotation.

**Sửa 2 — cũ:**

> - Thu hồi chủ động (logout, đổi mật khẩu): xóa cả chuỗi. Muốn chặn access token ngay thì cần denylist theo jti (vd trong Redis) tới khi token hết hạn, đánh đổi tính stateless.

**Sửa 2 — mới:**

> - Thu hồi chủ động (logout, đổi mật khẩu): xóa cả chuỗi; chặn access token ngay thì cần denylist theo jti, đánh đổi tính stateless.

**Sửa 3 — cũ:**

>  Có thể cho khoảng ân hạn rất ngắn cho race hợp lệ.

**Sửa 3 — mới:**

> *(xóa)*

### de-qa-1021

- (chỉ claim chưa có nguồn, không có issue major)
- **claim unverified:** JWKS: chỉ lấy khóa từ URL cấu hình sẵn, cache, giới hạn refetch khi gặp kid lạ
- **Không đổi câu hỏi** dù reviewer đề xuất tách (rubric v2 không còn tính câu hỏi là quá rộng).

**Sửa 1 — cũ:**

> 5. Xoay vòng khóa với JWKS: chọn khóa theo kid

**Sửa 1 — mới:**

> 5. Xoay vòng khóa với JWKS (thực hành phổ biến, RFC 8725 không quy định): chọn khóa theo kid

## python

### de-qa-1065

- **[major · length]** Chunk ~767 token, vượt 600. Đoạn 'Health check' (liveness không gọi DB, readiness fail khi shutdown) nằm hoàn toàn trong phần bị cắt, trong khi câu hỏi hỏi trực tiếp về health check.
- **[major · factual]** Claim 'nproc trả số CPU của node chứ không phải CPU limit' là nguyên nhân chính của 65 worker nhưng chưa tìm được nguồn; hành vi của nproc với cgroup CPU quota có thể khác theo phiên bản coreutils.
- **claim unverified:** nproc trong container thường trả số CPU của node, không theo CPU limit

**Sửa 1 — cũ:**

> Vì sao ra 65 worker: nproc trong container thường trả số CPU của node chứ không phải CPU limit.

**Sửa 1 — mới:**

> Vì sao ra 65 worker: nproc in số processing unit mà process được phép dùng (theo affinity), không nhất thiết phản ánh CPU limit kiểu quota của Kubernetes; trên node 32 core nó có thể trả 32, nên 2 × 32 + 1 = 65.

**Sửa 2 — cũ:**

> ; tài liệu nhấn mạnh worker không tương ứng với số client, thường 4–12 worker đã chịu được tải lớn, và quá nhiều worker còn làm giảm throughput.

**Sửa 2 — mới:**

> ; quá nhiều worker còn làm giảm throughput.

**Sửa 3 — cũ:**

> - Worker class: module uvicorn.workers đã deprecated, chuyển sang package uvicorn-worker; hoặc chạy uvicorn --workers (uvicorn dùng spawn, không pre-fork).

**Sửa 3 — mới:**

> *(xóa)*

**Sửa 4 — cũ:**

> - max_requests kèm max_requests_jitter: khởi động lại worker sau một số request để hạn chế hậu quả rò rỉ bộ nhớ, jitter tránh mọi worker restart cùng lúc; không thay cho sửa leak.
> - preload_app: nạp code trước khi fork, nhưng không được mở kết nối DB hay thread trước fork.
> - Sau reverse proxy: bật proxy headers và chỉ tin IP của proxy (forwarded-allow-ips).
>
> Health check: liveness chỉ kiểm tra process còn phản hồi (không gọi DB, tránh restart dây chuyền); readiness kiểm tra phụ thuộc thiết yếu và trả lỗi khi đang shutdown.

**Sửa 4 — mới:**

> Health check: liveness chỉ kiểm tra process còn phản hồi (không gọi DB, tránh restart dây chuyền); readiness kiểm tra phụ thuộc thiết yếu và trả lỗi khi đang shutdown.
>
> Thêm nếu còn thời gian: module uvicorn.workers đã deprecated, chuyển sang package uvicorn-worker (hoặc chạy uvicorn --workers); max_requests kèm max_requests_jitter khởi động lại worker sau một số request để hạn chế hậu quả rò rỉ bộ nhớ (không thay cho sửa leak); preload_app không được mở kết nối DB hay thread trước fork.

### de-qa-1068

- **[major · interview_fit]** Rubric v2 vẫn tính là quá rộng (3 ý độc lập, ~6 phút): ba triệu chứng có ba cơ chế khác nhau: patch nơi tra cứu tên, autospec, AsyncMock. Câu hỏi nêu 3 triệu chứng và yêu cầu giải thích 4 chủ đề riêng: 4 yêu cầu, quá rộng cho 3–5 phút.
- **claim unverified:** Mock ở ranh giới hệ thống, tránh mock thứ mình sở hữu và rẻ để chạy thật

**Câu hỏi cũ:**

> Một test dùng `@patch('app.payments.stripe_client.charge')` nhưng vẫn gọi API thật; test khác mock `send_email` và pass, trong khi production lỗi vì hàm thật đã đổi chữ ký; còn mock cho hàm async thì `await` báo lỗi. Giải thích nguyên tắc patch đúng chỗ, autospec, mock hàm async, và khi nào nên tránh mock.

**Câu hỏi mới:**

> Một test dùng `@patch('app.payments.stripe_client.charge')` nhưng vẫn gọi API thật; test khác mock `send_email` và pass, trong khi production lỗi vì hàm thật đã đổi chữ ký. Giải thích nguyên nhân của từng lỗi và cách sửa.

**Sửa 1 — cũ:**

> 3. Mock async: khi không truyền new, patch tự dùng AsyncMock nếu đối tượng bị patch là async function; kết quả gọi là awaitable và có các assert_awaited_*. Lỗi hay gặp là tự gán MagicMock cho hàm async nên giá trị trả về không await được.
>
> 4. Khi nào tránh mock:
> - Thứ bạn sở hữu và rẻ để chạy thật (hàm thuần, repository với DB test): mock khiến test chỉ kiểm tra cách gọi, không kiểm tra hành vi.
> - Mock ở ranh giới hệ thống (HTTP ra ngoài, cổng thanh toán, thời gian, random). Tốt hơn nữa là bọc client bên thứ ba sau interface của mình rồi fake interface đó, hoặc dùng thư viện chặn HTTP để kiểm tra request thật được gửi đi.
> - Ưu tiên assert kết quả và hành vi hơn assert_called_with từng tham số, để refactor không làm vỡ test vô ích.
>
> 5. Gắn với pytest: tạo patch qua fixture (monkeypatch hoặc mocker) để tự hoàn tác sau mỗi test, tránh patch thủ công rò sang test khác. Bổ sung contract test hoặc integration test với sandbox của đối tác để bắt thay đổi API mà mock không thể phát hiện.

**Sửa 1 — mới:**

> Follow-up liên quan:
> - Mock hàm async: khi không truyền new, patch tự dùng AsyncMock nếu đối tượng bị patch là async function; tự gán MagicMock cho hàm async thì giá trị trả về không await được.
> - Thực hành (khuyến nghị, không phải quy định): mock ở ranh giới hệ thống (HTTP ra ngoài, cổng thanh toán, thời gian), tránh mock thứ mình sở hữu và rẻ để chạy thật; tạo patch qua fixture (monkeypatch hoặc mocker) để tự hoàn tác sau mỗi test; bổ sung contract test hoặc integration test với sandbox của đối tác để bắt thay đổi API mà mock không phát hiện.

## ai-1

### de-qa-1150

- **[major · outdated]** Đáp án ghi 'Protocol error (JSON-RPC) cho ... tham số sai'. Từ spec 2025-11-25, lỗi validate input phải trả về dạng tool execution error (isError: true) để model tự sửa; protocol error chỉ còn cho unknown tool và request sai schema.
- **[major · outdated]** Câu 'Với HTTP, mất kết nối không có nghĩa request bị hủy' chỉ đúng tới 2025-11-25. Ở revision 2026-07-28, server phải coi việc đóng response stream là hủy request.
- **[major · length]** 661 token, vượt budget 600; phần bị cắt là human-in-the-loop và prompt injection, đúng ý câu hỏi hỏi tới.
- **claim outdated:** Tham số sai (invalid arguments) được báo bằng protocol error JSON-RPC.
- **claim outdated:** Với HTTP, mất kết nối không có nghĩa request bị hủy.
- **Không đổi câu hỏi** dù reviewer đề xuất tách (rubric v2 không còn tính câu hỏi là quá rộng).

**Sửa 1 — cũ:**

> - Có `outputSchema` + `structuredContent` để client validate kết quả.

**Sửa 1 — mới:**

> *(xóa)*

**Sửa 2 — cũ:**

> - Protocol error (JSON-RPC) cho tool không tồn tại, tham số sai.
> - Lỗi nghiệp vụ trả trong result với `isError: true`,

**Sửa 2 — mới:**

> - Protocol error (JSON-RPC) cho tool không tồn tại hoặc request sai cấu trúc.
> - Tham số sai giá trị và lỗi nghiệp vụ trả trong result với `isError: true` (từ spec 2025-11-25, lỗi validate input là tool execution error),

**Sửa 3 — cũ:**

> - Client đặt timeout. Với HTTP, mất kết nối không có nghĩa request bị hủy; thao tác có thể đã chạy, nên cần idempotency và tool tra trạng thái.

**Sửa 3 — mới:**

> - Client đặt timeout. Side effect có thể đã xảy ra trước khi client hủy hoặc mất kết nối, nên cần idempotency và tool tra trạng thái.

**Sửa 4 — cũ:**

> - Annotation mô tả hành vi tool chỉ là gợi ý, client phải coi là không tin cậy nếu server không tin cậy.

**Sửa 4 — mới:**

> *(xóa)*

### de-qa-1151

- **[major · outdated]** Mục Streamable HTTP và mục vận hành mô tả Mcp-Session-Id, GET stream, resume qua Last-Event-ID, hủy bằng notification. Revision 2026-07-28 (latest) đã bỏ session, GET endpoint, resumability; đóng response stream = hủy request.
- **claim outdated:** Endpoint POST/GET; session qua header Mcp-Session-Id.
- **claim outdated:** Mất kết nối không đồng nghĩa hủy request (client gửi notification hủy riêng); stream resume qua Last-Event-ID.
- **Lưu ý:** Không áp ý 'state chéo lời gọi dùng handle' trong đề xuất vì chưa có câu trích nguồn.

**Sửa 1 — cũ:**

> - Server là tiến trình độc lập phục vụ nhiều client qua một endpoint POST/GET, có thể dùng SSE để stream và gửi notification.
> - Session qua header `Mcp-Session-Id`, phiên bản qua `MCP-Protocol-Version`. Transport này thay cho HTTP+SSE cũ.

**Sửa 1 — mới:**

> - Server là tiến trình độc lập phục vụ nhiều client qua một HTTP endpoint, có thể dùng SSE để stream. Transport này thay cho HTTP+SSE cũ.
> - Khác nhau theo revision: tới 2025-11-25 có session qua header `Mcp-Session-Id`, GET stream và resume qua `Last-Event-ID`; revision 2026-07-28 bỏ session và GET stream endpoint, stream bị đứt thì client gửi lại thành request mới.

**Sửa 2 — cũ:**

> 6. Vận hành: instance stateful cần sticky session hoặc state bên ngoài. Mất kết nối không đồng nghĩa hủy request (client gửi notification hủy riêng); stream có thể resume qua `Last-Event-ID`. Thêm rate limit, audit log.

**Sửa 2 — mới:**

> 6. Vận hành: đặt state ngoài instance (DB/cache), hoặc sticky session nếu dùng revision còn session. Mất kết nối có bị coi là hủy hay không tùy revision (2025-06-18 thì không; 2026-07-28 thì đóng stream là hủy), nên tool có side effect cần idempotency. Thêm rate limit, audit log.

### de-qa-1154

- **[major · length]** 658 token, vượt 600; phần bị cắt là mục Warmup, Phục hồi và đánh đổi — warmup là một biện pháp câu hỏi hỏi tới.
- **Không đổi câu hỏi** dù reviewer đề xuất tách (rubric v2 không còn tính câu hỏi là quá rộng).

**Sửa 1 — cũ:**

> **Phân loại triệu chứng**
> - NaN ngay từ đầu: thường do lỗi số (log(0), chia cho 0) hoặc model không tương thích fp16.
> - Loss spike sau một thời gian: thường do learning rate quá lớn, một batch bất thường hoặc gradient nổ.

**Sửa 1 — mới:**

> **Phân loại triệu chứng**: NaN ngay từ đầu thường do lỗi số (log(0), chia cho 0) hoặc model không tương thích fp16; loss spike sau một thời gian thường do learning rate quá lớn, batch bất thường hoặc gradient nổ.

**Sửa 2 — cũ:**

> - Autocast chạy phần lớn op ở dtype thấp để nhanh; các op như reduction vẫn cần dải động của fp32.

**Sửa 2 — mới:**

> *(xóa)*

**Sửa 3 — cũ:**

> - Đầu huấn luyện, tham số và moment của Adam chưa ổn định, learning rate lớn ngay dễ phân kỳ.

**Sửa 3 — mới:**

> - Đầu huấn luyện, dùng learning rate lớn ngay dễ phân kỳ.

### de-qa-1155

- **[major · factual]** Mục BatchNorm dẫn tới việc coi SyncBatchNorm là cách sửa mặc định. Trong kịch bản tăng số GPU, batch mỗi GPU thường giữ nguyên; Goyal cố ý giữ BN theo từng worker (n=32) và nói không nên tính BN trên mọi worker. Grader có thể phạt ứng viên trả lời đúng theo paper.
- **claim contradicted:** Batch mỗi GPU nhỏ làm thống kê BN nhiễu, nên chuyển sang SyncBatchNorm khi tăng batch bằng data parallel.
- **Không đổi câu hỏi** dù reviewer đề xuất tách (rubric v2 không còn tính câu hỏi là quá rộng).

**Sửa 1 — cũ:**

> - Với data parallel, BatchNorm mặc định tính thống kê trên batch của từng GPU.
> - Batch mỗi GPU nhỏ thì mean/variance nhiễu, ảnh hưởng chất lượng.
> - SyncBatchNorm tính mean và std trên mọi mini-batch trong process group; chuyển bằng `convert_sync_batchnorm` trước khi bọc DDP. Đổi lại có thêm chi phí giao tiếp giữa GPU.

**Sửa 1 — mới:**

> - Với data parallel, BatchNorm mặc định tính thống kê trên batch của từng GPU. Goyal và cộng sự giữ batch mỗi worker cố định (n = 32) khi tăng số worker và tính BN theo từng worker; họ lưu ý không nên tính thống kê BN trên mọi worker, vừa để giảm giao tiếp vừa để giữ nguyên hàm loss được tối ưu.
> - Vì vậy khi tăng số GPU, giữ batch mỗi GPU đủ lớn. SyncBatchNorm (tính mean và std trên mọi mini-batch trong process group, chuyển bằng `convert_sync_batchnorm` trước khi bọc DDP) chỉ cân nhắc khi batch mỗi GPU thực sự quá nhỏ, đổi lại chi phí giao tiếp giữa GPU.

### de-qa-1156

- **[major · length]** 686 token, vượt 600; phần bị cắt gồm cuối continuous batching, toàn bộ GQA và câu đánh đổi — GQA là ý câu hỏi hỏi trực tiếp.
- **Không đổi câu hỏi** dù reviewer đề xuất tách (rubric v2 không còn tính câu hỏi là quá rộng).

**Sửa 1 — cũ:**

> - Khi decode, mỗi token mới phải attend tới K, V của mọi token trước. KV cache lưu K, V lại để khỏi tính lại.
> - Bộ nhớ KV tăng tuyến tính theo độ dài chuỗi nhân số request đang chạy.

**Sửa 1 — mới:**

> - Khi decode, mỗi token mới phải attend tới K, V của mọi token trước; KV cache lưu K, V lại để khỏi tính lại, và bộ nhớ của nó tăng tuyến tính theo độ dài chuỗi nhân số request đang chạy.

**Sửa 2 — cũ:**

> - PagedAttention (vLLM) chia KV cache thành block chứa số token cố định, lưu không liên tục, dùng block table ánh xạ logic sang vật lý như virtual memory.
> - Kết quả: lãng phí gần như bằng 0. Các sample chia sẻ KV của prompt nhờ copy-on-write.
> - Khi hết bộ nhớ, hệ preempt request bằng cách swap ra CPU hoặc tính lại sau.

**Sửa 2 — mới:**

> - PagedAttention (vLLM) chia KV cache thành block chứa số token cố định, lưu không liên tục, dùng block table ánh xạ logic sang vật lý như virtual memory; lãng phí gần như bằng 0.

### de-qa-1159

- **[major · outdated]** Strict mode, parallel_tool_calls, tool_choice/allowed_tools là tham số của OpenAI API nhưng đáp án viết như chuẩn chung (chỉ ghi vendor ở ý '20 tool'). Grader có thể phạt ứng viên dùng Anthropic/Gemini. Domain pitfalls yêu cầu ghi vendor hoặc viết trung lập.
- **Không đổi câu hỏi** dù reviewer đề xuất tách (rubric v2 không còn tính câu hỏi là quá rộng).

**Sửa 1 — cũ:**

> Model có thể gọi song song nhiều tool; tắt bằng `parallel_tool_calls: false`

**Sửa 1 — mới:**

> Model có thể gọi song song nhiều tool; với OpenAI API, tắt bằng `parallel_tool_calls: false`

**Sửa 2 — cũ:**

> - Bật strict mode để arguments luôn tuân schema. Điều kiện: mọi object có `additionalProperties: false` và mọi field nằm trong `required`.
> - Strict chỉ bảo đảm cú pháp,

**Sửa 2 — mới:**

> - Bật chế độ ép schema nếu provider hỗ trợ để arguments luôn tuân schema (với OpenAI API là strict mode, điều kiện: mọi object có `additionalProperties: false` và mọi field nằm trong `required`).
> - Ép schema chỉ bảo đảm cú pháp,

**Sửa 3 — cũ:**

> - Dùng `tool_choice` theo bước của workflow: `auto`, `required`, ép một hàm cụ thể, chỉ cho phép một tập con, hoặc `none`.

**Sửa 3 — mới:**

> - Giới hạn tập tool theo bước của workflow (với OpenAI API: `tool_choice` là `auto`, `required`, ép một hàm cụ thể, chỉ cho phép một tập con, hoặc `none`).

### de-qa-1167 · golden

- **[major · factual]** 'giữ α/r khi đổi r' trái với paper LoRA: paper đặt α bằng r đầu tiên rồi không tune, hệ số α/r (với α cố định) giúp ít phải tune lại khi đổi r. Grader có thể phạt ứng viên nói đúng theo paper.
- **[major · interview_fit]** Rubric v2 vẫn tính là quá rộng (3 ý độc lập, ~6 phút): ba mạch riêng: cơ chế và bộ nhớ, ảnh hưởng inference, khi nào không đủ so với full fine-tuning. Câu hỏi có 5 ý (cơ chế, vì sao giảm bộ nhớ, siêu tham số, inference, khi nào không đủ).
- **[major · length]** 625 token, vượt 600; phần bị cắt là cuối mục 'Khi LoRA không đủ' — đúng một ý câu hỏi hỏi trực tiếp.
- **claim contradicted:** Giữ α/r khi đổi r để ít phải tune lại.
- **Lưu ý:** Golden: giữ nguyên câu hỏi dù rubric v2 vẫn tính là quá rộng; cần báo Thắng.

**Sửa 1 — cũ:**

>  Cập nhật được scale theo α/r.

**Sửa 1 — mới:**

> *(xóa)*

**Sửa 2 — cũ:**

> - Giả thuyết nền: thay đổi trọng số khi thích nghi có "intrinsic rank" thấp.

**Sửa 2 — mới:**

> *(xóa)*

**Sửa 3 — cũ:**

> α là độ lớn cập nhật (giữ α/r khi đổi r để ít phải tune lại);

**Sửa 3 — mới:**

> update được nhân với α/r, và paper đặt α bằng giá trị r thử đầu tiên rồi không tune α nữa, nhờ hệ số α/r nên khi đổi r ít phải tune lại siêu tham số;

**Sửa 4 — cũ:**

> **Inference**: merge BA vào W0 thì không thêm latency, nhưng khi đó khó phục vụ nhiều adapter khác nhau trong cùng batch; giữ unmerged để phục vụ đa adapter, đổi lại thêm chút tính toán.

**Sửa 4 — mới:**

> **Inference**: merge BA vào W0 thì không thêm latency; giữ unmerged để phục vụ nhiều adapter trong cùng batch, đổi lại thêm chút tính toán.

### de-qa-1168

- **[major · length]** 656 token, vượt 600; phần bị cắt là cuối mục 'Đánh giá sau fine-tune' và câu đánh đổi — một ý câu hỏi hỏi trực tiếp.
- **Không đổi câu hỏi** dù reviewer đề xuất tách (rubric v2 không còn tính câu hỏi là quá rộng).

**Sửa 1 — cũ:**

> **Dữ liệu SFT**
> - Ví dụ chất lượng cao, đại diện phân phối thật (lượt hỏi đáp mẫu, bản chấm điểm), đa dạng, đã khử trùng.
> - Người review và loại bỏ PII.
> - Tách tập test không trùng câu hỏi với tập train, tránh leakage.
>
> **Chống forgetting**
> - Fine-tune hẹp có thể làm giảm năng lực chung.
> - LoRA giữ năng lực ngoài miền tốt hơn full fine-tuning, đổi lại học miền mới kém hơn.
> - Trộn thêm dữ liệu instruction tổng quát; learning rate thấp, ít epoch, early stopping theo tập validation.

**Sửa 1 — mới:**

> **Dữ liệu SFT**: ví dụ chất lượng cao, đại diện phân phối thật (lượt hỏi đáp mẫu, bản chấm điểm), đa dạng, đã khử trùng và loại PII; tách tập test không trùng câu hỏi với tập train.
>
> **Chống forgetting**: fine-tune hẹp có thể làm giảm năng lực chung; LoRA giữ năng lực ngoài miền tốt hơn full fine-tuning (đổi lại học miền mới kém hơn); trộn dữ liệu instruction tổng quát, learning rate thấp, ít epoch, early stopping.

### de-qa-1173

- **[major · outdated]** JSON mode, trường refusal, trạng thái incomplete/max_output_tokens là API của OpenAI nhưng đáp án viết như chuẩn chung; domain pitfalls yêu cầu ghi vendor hoặc viết trung lập.
- **claim outdated:** Request đầu tiên với một schema mới có thêm độ trễ.
- **Không đổi câu hỏi** dù reviewer đề xuất tách (rubric v2 không còn tính câu hỏi là quá rộng).

**Sửa 1 — cũ:**

> - Structured Outputs: bảo đảm tuân schema.
>   - Ràng buộc:

**Sửa 1 — mới:**

> - Structured outputs (chế độ ép schema của provider, ví dụ Structured Outputs của OpenAI): bảo đảm tuân schema.
>   - Với OpenAI, ràng buộc:

**Sửa 2 — cũ:**

>   - Request đầu tiên với một schema mới có thêm độ trễ vì API phải xử lý schema.

**Sửa 2 — mới:**

> *(xóa)*

**Sửa 3 — cũ:**

> - Khi model từ chối vì lý do an toàn, response có trường `refusal` thay vì JSON theo schema.

**Sửa 3 — mới:**

> - Khi model từ chối vì lý do an toàn, response không theo schema (với OpenAI API là trường `refusal`).

**Sửa 4 — cũ:**

> - Chạm giới hạn token thì response ở trạng thái incomplete (lý do `max_output_tokens`), JSON dở dang.

**Sửa 4 — mới:**

> - Chạm giới hạn token thì JSON dở dang (với OpenAI API: response ở trạng thái incomplete, lý do `max_output_tokens`).

## ai-2

### de-qa-1177

- **[major · length]** 687 token, vượt 600; phần bị cắt là phần lớn mục 'Bẫy vận hành' và 'Quyết định' — câu hỏi hỏi trực tiếp về bẫy.
- **Không đổi câu hỏi** dù reviewer đề xuất tách (rubric v2 không còn tính câu hỏi là quá rộng).

**Sửa 1 — cũ:**

> - Với Anthropic, `budget_tokens` đặt thủ công là mục tiêu chứ không phải trần cứng; ở các model mới, cách này được thay bằng adaptive thinking điều chỉnh qua tham số effort, nên cần kiểm tra tài liệu của đúng model đang dùng. Tăng budget thì lợi ích giảm dần trong khi latency tăng. Tác vụ đơn giản bắt đầu thấp rồi tăng dần, đo chất lượng ở mỗi mức.
> - Với OpenAI: phải chừa đủ chỗ cho reasoning cộng output. Nếu chạm giới hạn, response ở trạng thái incomplete và có thể vẫn tính tiền input cùng reasoning mà không có output hiển thị.
>
> **Prompt**
> - Nêu mục tiêu, ràng buộc và định dạng đầu ra rõ ràng; không cần mô tả từng bước trung gian.
> - Effort là núm tinh chỉnh, không phải cách chính để cứu chất lượng.

**Sửa 1 — mới:**

> - Bắt đầu thấp rồi tăng dần, đo chất lượng ở mỗi mức; tăng budget thì lợi ích giảm dần trong khi latency tăng. Với Anthropic, `budget_tokens` là mục tiêu chứ không phải trần cứng, và model mới chuyển sang adaptive thinking qua tham số effort: kiểm tra tài liệu của đúng model đang dùng.
> - Với OpenAI: phải chừa đủ chỗ cho reasoning cộng output; chạm giới hạn thì response incomplete và có thể vẫn tính tiền input cùng reasoning mà không có output hiển thị.

### de-qa-1186

- **[major · interview_fit]** Rubric v2 vẫn tính là quá rộng (1 ý độc lập, ~6 phút): một quy trình nhưng sáu bước, mỗi bước kèm loại lỗi nó bắt: các ý bắt buộc vẫn cần khoảng 6 phút. Câu hỏi liệt kê 6 bước (versioning/registry, validation offline, shadow, canary, A/B, rollback) và hỏi thêm mỗi bước bắt lỗi gì.
- **[major · length]** 670 token, vượt 600; phần bị cắt là mục Rollback, 'Sau rollout' và câu đánh đổi — rollback là bước câu hỏi hỏi trực tiếp.

**Câu hỏi cũ:**

> Trình bày quy trình đưa một phiên bản model mới ra production an toàn: versioning và model registry, validation offline, shadow deployment, canary, A/B test và rollback. Mỗi bước bắt được loại lỗi nào mà bước khác bỏ sót?

**Câu hỏi mới:**

> Trong quy trình đưa model mới ra production, shadow deployment, canary và A/B test mỗi bước bắt được loại lỗi nào mà bước khác bỏ sót, và bạn rollback thế nào?

**Sửa 1 — cũ:**

> **Versioning và registry**
> - Mỗi model gắn version dữ liệu, code, hyperparameter và metric (metadata, lineage); artifact bất biến.
> - Bắt: không tái lập được, không biết model đang chạy là gì. Đây là điều kiện để audit và rollback.
>
> **Data validation trước train**
> - Kiểm schema và phân phối dữ liệu mới; bất thường thì dừng pipeline.
> - Bắt: dữ liệu train lỗi trước khi nó thành model lỗi.
>
> **Model validation offline**
> - So metric trên holdout với model đang chạy, theo từng lát; kiểm tra calibration và công bằng giữa các nhóm.
> - Bắt: model tệ hơn về chất lượng dự đoán.
>
> **Kiểm tra tương thích serving**
> - Cùng feature pipeline, latency, bộ nhớ, contract input/output.
> - Bắt: training-serving skew, lỗi tích hợp.

**Sửa 1 — mới:**

> **Trước khi lên traffic thật** (nền cho follow-up): versioning và registry (version dữ liệu, code, hyperparameter, metric; artifact bất biến) để tái lập và rollback; validation dữ liệu trước train; validation model offline so với model đang chạy theo từng lát; kiểm tương thích serving (feature pipeline, latency, contract) để bắt training-serving skew.

### de-qa-1188

- **[major · outdated]** threshold/prefix_padding_ms/silence_duration_ms, semantic_vad/eagerness và tên sự kiện (input_audio_buffer.speech_started, conversation.item.truncate) là API của OpenAI Realtime nhưng đáp án viết như chuẩn chung; domain pitfalls yêu cầu ghi vendor hoặc viết trung lập.
- **Không đổi câu hỏi** dù reviewer đề xuất tách (rubric v2 không còn tính câu hỏi là quá rộng).

**Sửa 1 — cũ:**

> **VAD dựa trên khoảng lặng (server VAD)**
> Chia audio theo các khoảng im lặng, với ba tham số:

**Sửa 1 — mới:**

> **VAD dựa trên khoảng lặng**
> Chia audio theo các khoảng im lặng. Với OpenAI Realtime API (server VAD) có ba tham số:

**Sửa 2 — cũ:**

> - `eagerness`: `low`

**Sửa 2 — mới:**

> - Với OpenAI Realtime API, `eagerness`: `low`

**Sửa 3 — cũ:**

> **Barge-in**
> 1.

**Sửa 3 — mới:**

> **Barge-in** (tên sự kiện theo OpenAI Realtime API)
> 1.

### de-qa-1193

- **[major · interview_fit]** Rubric v2 vẫn tính là quá rộng (2 ý độc lập, ~6 phút): hai lỗi gốc nhưng năm kỹ thuật kèm chi phí và cách đo: các ý bắt buộc vẫn cần khoảng 6 phút. Câu hỏi đòi chọn và giải thích 5 kỹ thuật (contextual chunking, parent-document, query rewriting, multi-query, HyDE) kèm chi phí và cách đo.
- **[major · length]** 683 token, vượt 600; phần bị cắt là mục 'Đo' (recall@k theo lát, thêm từng kỹ thuật một) — câu hỏi hỏi trực tiếp.
- **Lưu ý:** Câu hỏi mới giữ lại ví dụ 'doanh thu tăng 3%' của câu cũ (đề xuất bỏ ví dụ).

**Câu hỏi cũ:**

> Phân tích lỗi cho thấy hệ RAG trượt vì hai lý do: chunk mất ngữ cảnh (đoạn "doanh thu tăng 3% so với quý trước" không nêu công ty hay thời gian), và truy vấn người dùng ngắn, mơ hồ, diễn đạt khác tài liệu. Chọn và giải thích các kỹ thuật phù hợp: contextual chunking, parent-document retrieval, query rewriting, multi-query, HyDE; nêu chi phí và cách đo.

**Câu hỏi mới:**

> Phân tích lỗi cho thấy hệ RAG trượt vì hai lý do: chunk mất ngữ cảnh (đoạn "doanh thu tăng 3% so với quý trước" không nêu công ty hay thời gian), và truy vấn người dùng ngắn, mơ hồ, diễn đạt khác tài liệu. Bạn chọn kỹ thuật nào cho từng lỗi, và đo hiệu quả ra sao?

**Sửa 1 — cũ:**

>   - Kết quả báo cáo: tỷ lệ truy hồi thất bại trong top-20 (1 − recall@20) giảm 35%; giảm 49% khi kết hợp BM25 theo ngữ cảnh; 67% khi thêm rerank.

**Sửa 1 — mới:**

>   - Anthropic báo cáo tỷ lệ truy hồi thất bại trong top-20 giảm 35%, tới 67% khi kết hợp BM25 theo ngữ cảnh và rerank.

**Sửa 2 — cũ:**

> - HyDE: LLM viết tài liệu giả định trả lời câu hỏi, encoder embed nó để tìm tài liệu thật tương tự. Chi tiết sai trong tài liệu giả bị nút thắt dense embedding lọc bớt; phương pháp zero-shot, vượt Contriever. Rủi ro: miền mà LLM không biết khiến tài liệu giả lệch hướng.

**Sửa 2 — mới:**

> - HyDE: LLM viết tài liệu giả định trả lời câu hỏi, embed nó để tìm tài liệu thật tương tự; rủi ro ở miền LLM không biết, tài liệu giả lệch hướng.

### de-qa-1196

- **[major · length]** 660 token, vượt 600; phần bị cắt là cuối mục Đánh đổi (chặn nhầm, đo precision/recall guardrail) — câu hỏi hỏi trực tiếp về tỷ lệ chặn nhầm.
- **Không đổi câu hỏi** dù reviewer đề xuất tách (rubric v2 không còn tính câu hỏi là quá rộng).

**Sửa 1 — cũ:**

> **Mô hình mối đe dọa** (OWASP Top 10 cho LLM 2025): prompt injection (LLM01), rò rỉ thông tin nhạy cảm (LLM02), xử lý output không đúng (LLM05), excessive agency (LLM06), rò rỉ system prompt (LLM07), tiêu thụ tài nguyên không giới hạn (LLM10).

**Sửa 1 — mới:**

> **Mô hình mối đe dọa** (OWASP Top 10 cho LLM 2025): prompt injection, rò rỉ thông tin nhạy cảm và system prompt, xử lý output không đúng, excessive agency.

**Sửa 2 — cũ:**

> classifier phát hiện injection, jailbreak (giảm rủi ro, không loại trừ)

**Sửa 2 — mới:**

> classifier phát hiện injection (giảm rủi ro, không loại trừ)

