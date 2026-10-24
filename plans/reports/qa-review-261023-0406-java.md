# Báo cáo duyệt cặp Q&A — java (2026-10-23 04:08)

> Báo cáo do Claude tạo bằng skill `interview-qa-review`: **chỉ là gợi ý kèm bằng chứng**. Các cặp này cũng do Claude viết, nên người reviewer (cùng họ model) có thể chung điểm mù. Quyết định và `reviewed_by` thuộc về người duyệt.

**22/22 cặp đã duyệt** · Đạt 9 · Cần sửa 13 · Bỏ 0 · tin cậy cao 19 / vừa 2 / thấp 1

**Phân loại cho người duyệt:** Phải đọc 3 · Chỉ hình thức 10 (câu hỏi quá rộng, quá dài: nội dung đúng) · Có thể chấp nhận 9

**Kiểm tra trích dẫn nguyên văn:** khớp 136 · không khớp 1 · không kiểm được từ máy này 0

## Cặp mồi (kiểm tra người reviewer)

| qa_id | Lỗi cài sẵn | Gợi ý nhận được | Bắt được? |
|---|---|---|---|
| de-qa-1122 | Nói ConcurrentHashMap chấp nhận value null như HashMap (sai: CHM không cho key/value null, put(k, null) ném NullPointerException) | Cần sửa: [critical] Ý 1 khẳng định ConcurrentHashMap nhận value null 'giống HashMap'. Thực tế put(id, null) ném NullPointerException. Đây là điểm ch… | có |

## Tổng hợp

| qa_id | Topic | Gợi ý | Tin cậy | Nhóm | Vấn đề chính | Token | Golden |
|---|---|---|---|---|---|---|---|
| de-qa-1100 | Java Collections và HashMap | Đạt | high | Có thể chấp nhận | [minor] Chunk ~690 token, vượt budget 600. Điểm cắt rơi giữa ý khắc phục 3; mất phần capacity = expected / 0.75 và ý 4 (Comparable). Các ý … | 690 | 2 |
| de-qa-1101 | Java Collections và HashMap | Cần sửa | high | Chỉ hình thức | [major] Câu hỏi có 3 ý hỏi (vì sao sai, sửa thế nào, lưu ý khi dùng computeIfAbsent) và đáp án có 5 lưu ý phụ, khó trả lời gọn trong 3–5 ph… | 740 |  |
| de-qa-1102 | Đa luồng và concurrency | Đạt | high | Có thể chấp nhận | [minor] Chunk ~710 token; điểm cắt 600 token rơi vào cách sửa 4 (final field) và mất đoạn 'Bài học'. Các ý bắt buộc (data race, cách sửa vo… | 710 | 1 |
| de-qa-1103 | Đa luồng và concurrency | Đạt | high | Có thể chấp nhận | [minor] Chunk ~788 token; điểm cắt 600 token rơi vào ý 4 (bulkhead), mất ý 5–6 và đoạn virtual thread. Các ý bắt buộc (commonPool, executor… | 788 |  |
| de-qa-1104 | JVM, bộ nhớ và Garbage Collection | Đạt | high | Có thể chấp nhận | [minor] Ghi JFR 'overhead thấp nên dùng được trên production' đúng cho việc ghi recording, nhưng tài liệu nói dump với path-to-gc-roots=tru… | 692 | 1 |
| de-qa-1105 | JVM, bộ nhớ và Garbage Collection | Cần sửa | high | Chỉ hình thức | [major] Câu hỏi có 4 ý hỏi (đọc log, tune G1, khi nào chuyển ZGC, trade-off), quá rộng cho 3–5 phút. | 680 |  |
| de-qa-1106 | JPA và Hibernate | Cần sửa | high | Chỉ hình thức | [major] Câu hỏi có 3 ý hỏi (giải thích N+1, vì sao cách sửa sai, các chiến lược đúng kèm trade-off) và đáp án liệt kê 6 chiến lược, khó trả… | 732 | 1 |
| de-qa-1107 | JPA và Hibernate | Đạt | high | Có thể chấp nhận | [minor] Chunk ~727 token; điểm cắt 600 token rơi vào ý 6 (StatelessSession), mất ý 6–7. Nguyên nhân và các ý viết lại chính (chunk + flush/… | 727 |  |
| de-qa-1108 | SQL, index và tối ưu truy vấn | Đạt | high | Có thể chấp nhận | [minor] Chunk ~711 token; điểm cắt 600 token rơi vào cuối ý xử lý 3, mất ý 4–5 và câu về BEGIN/ROLLBACK. Ý bắt buộc (so estimate/actual, nh… | 711 |  |
| de-qa-1109 | SQL, index và tối ưu truy vấn | Đạt | high | Có thể chấp nhận | [minor] Chunk ~663 token; điểm cắt 600 token rơi vào trade-off thứ 2, mất 3 trade-off cuối (đảo chiều cho trang trước, index theo kiểu sort… | 663 | 1 |
| de-qa-1110 | Spring @Transactional | Đạt | high | Có thể chấp nhận | [minor] Chunk ~790 token; điểm cắt 600 token rơi cuối cách sửa (c) của hiện tượng 2, mất phần 'Lưu ý thêm'. Hai hiện tượng và cách sửa nằm … | 790 | 1 |
| de-qa-1111 | Spring @Transactional | Cần sửa | high | Chỉ hình thức | [major] Câu hỏi yêu cầu phân tích lost update và so sánh 4 cách (atomic update, pessimistic, optimistic, nâng isolation): tính theo rubric … | 746 | 1 |
| de-qa-1112 | Spring Security, JWT và OAuth2 | Cần sửa | low | Phải đọc | [major] Câu hỏi có 3 ý hỏi lớn (cách validate JWT, vì sao khó thu hồi, thiết kế access/refresh gồm thời hạn, rotation, lưu trữ và trade-off… | 733 | 1 |
| de-qa-1113 | Spring Security, JWT và OAuth2 | Cần sửa | high | Chỉ hình thức | [major] Câu hỏi có 3 ý hỏi (luồng qua DelegatingFilterProxy/FilterChainProxy/SecurityFilterChain, cách tách hai chain, khi nào tắt CSRF an … | 802 |  |
| de-qa-1114 | Spring Boot auto-configuration và profi… | Cần sửa | high | Chỉ hình thức | [major] Câu hỏi có 3 ý hỏi lớn (cơ chế gồm tìm, điều kiện, thứ tự; cách viết đúng; cách debug), quá rộng cho 3–5 phút. | 837 |  |
| de-qa-1115 | Spring Boot auto-configuration và profi… | Cần sửa | high | Chỉ hình thức | [major] Câu hỏi có 4 ý hỏi (thứ tự ưu tiên, nguyên nhân, chẩn đoán, tổ chức config/secret), quá rộng cho 3–5 phút. | 819 |  |
| de-qa-1116 | Spring IoC và Dependency Injection | Cần sửa | high | Chỉ hình thức | [major] Câu hỏi có 3 ý hỏi (vì sao trước chạy được, vì sao constructor injection không giải, xử lý từ tạm thời tới đúng thiết kế). | 743 |  |
| de-qa-1117 | Spring IoC và Dependency Injection | Đạt | high | Có thể chấp nhận | [minor] Chunk ~793 token; điểm cắt 600 token rơi ở cách sửa thứ nhất của lỗi 2, mất cách sửa sao chép context và đoạn 'Nguyên tắc chung'. H… | 793 |  |
| de-qa-1118 | Unit test với JUnit và Mockito | Cần sửa | high | Chỉ hình thức | [major] Câu hỏi có 3 ý hỏi (cơ chế caching, nguyên nhân chậm, tổ chức lại gồm slice, Testcontainers, trade-off), quá rộng cho 3–5 phút. | 818 |  |
| de-qa-1119 | Unit test với JUnit và Mockito | Cần sửa | medium | Chỉ hình thức | [major] Câu hỏi có 3 ý hỏi (phân biệt mock/stub/spy, pitfall Mockito, khi nào thay bằng test tích hợp). | 743 |  |
| de-qa-1120 | Thiết kế REST API với Spring MVC | Cần sửa | medium | Phải đọc | [major] Câu hỏi yêu cầu thiết kế kèm 3 phần liệt kê (lưu trữ, status code từng tình huống, trade-off); tính theo rubric là 3 ý hỏi, vượt mứ… | 693 | 1 |
| de-qa-1121 | Thiết kế REST API với Spring MVC | Cần sửa | high | Phải đọc | [major] Chunk ~782 token; điểm cắt 600 token rơi ngay đầu phần 'Vì sao tách DTO khỏi entity', nên snippet mất hẳn ý hỏi thứ hai. | 782 |  |

## Ảnh hưởng nếu sửa hoặc bỏ

- de-qa-1101: bỏ thì topic còn < 2 cặp hard (SC-001)
- de-qa-1105: bỏ thì topic còn < 2 cặp hard (SC-001)
- de-qa-1106: bỏ thì topic còn < 2 cặp hard (SC-001), là nhãn golden set g15 (báo Thắng nếu đổi nội dung)
- de-qa-1111: bỏ thì topic còn < 2 cặp hard (SC-001), là nhãn golden set g05 (báo Thắng nếu đổi nội dung)
- de-qa-1112: bỏ thì topic còn < 2 cặp hard (SC-001), là nhãn golden set g22 (báo Thắng nếu đổi nội dung)
- de-qa-1113: bỏ thì topic còn < 2 cặp hard (SC-001)
- de-qa-1114: bỏ thì topic còn < 2 cặp hard (SC-001)
- de-qa-1115: bỏ thì topic còn < 2 cặp hard (SC-001)
- de-qa-1116: bỏ thì topic còn < 2 cặp hard (SC-001)
- de-qa-1118: bỏ thì topic còn < 2 cặp hard (SC-001)
- de-qa-1119: bỏ thì topic còn < 2 cặp hard (SC-001)
- de-qa-1120: bỏ thì topic còn < 2 cặp hard (SC-001), là nhãn golden set g03 (báo Thắng nếu đổi nội dung)
- de-qa-1121: bỏ thì topic còn < 2 cặp hard (SC-001)
- 22/22 cặp dài hơn 600 token: snippet của Planner sẽ bị cắt (de-qa-1100, de-qa-1101, de-qa-1102, de-qa-1103, de-qa-1104, de-qa-1105, de-qa-1106, de-qa-1107, de-qa-1108, de-qa-1109, de-qa-1110, de-qa-1111, de-qa-1112, de-qa-1113, de-qa-1114, de-qa-1115, de-qa-1116, de-qa-1117, de-qa-1118, de-qa-1119, de-qa-1120, de-qa-1121).

## Việc cho người duyệt

- **Phải đọc** (3): de-qa-1112, de-qa-1120, de-qa-1121. Sai kiến thức, lỗi thời, chưa kiểm chứng được, tin cậy thấp, hoặc trích dẫn không khớp nguyên văn. Đọc phần kiểm chứng; chỗ Claude bác bỏ chính nguồn mà cặp trích thì Claude cũng có thể sai.
- **Chỉ hình thức** (10): de-qa-1101, de-qa-1105, de-qa-1106, de-qa-1111, de-qa-1113, de-qa-1114, de-qa-1115, de-qa-1116, de-qa-1118, de-qa-1119. Nội dung đúng; vấn đề là câu hỏi quá rộng hoặc quá dài. Sửa hay giữ là lựa chọn của bạn.
- **Có thể chấp nhận** (9): de-qa-1100, de-qa-1102, de-qa-1103, de-qa-1104, de-qa-1107, de-qa-1108, de-qa-1109, de-qa-1110, de-qa-1117. Mọi ý đã có trích dẫn; chấp nhận dựa trên bằng chứng là quyết định của bạn.
- Có nhãn golden set (9): de-qa-1100, de-qa-1102, de-qa-1104, de-qa-1106, de-qa-1109, de-qa-1110, de-qa-1111, de-qa-1112, de-qa-1120. Sửa câu hỏi thì giữ các thuật ngữ chính.

## Chi tiết từng cặp

### de-qa-1100 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Java Collections và HashMap (`java.core.collections-hashmap`) · ~690 token · hard của topic: 2 · golden: g01, g20

**Câu hỏi:** Một service giữ HashMap<OrderKey, Order> vài trăm nghìn entry; profiling cho thấy get/put ngày càng chậm và CPU cao. OrderKey tự viết hashCode() chỉ dựa trên một trường có rất ít giá trị khác nhau. Dựa vào cơ chế bên trong HashMap (hash spreading, resize, treeify), hãy giải thích vì sao chậm và cách khắc phục.

**Kết luận:** Đúng và bám sát mã nguồn OpenJDK: hash spreading, resize, ngưỡng treeify 8/6/64 và vai trò của Comparable đều có trích dẫn. Chỉ còn vấn đề nhỏ về độ dài và cách diễn đạt ngưỡng treeify.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | Chunk ~690 token, vượt budget 600. Điểm cắt rơi giữa ý khắc phục 3; mất phần capacity = expected / 0.75 và ý 4 (Comparable). Các ý bắt buộc (hashCode kém, cơ chế treeify, viết lại hashCode) vẫn nằm trước điểm cắt. | Gộp phần 'Chẩn đoán' vào một câu và rút ý 3 thành 'dùng HashMap.newHashMap(expected) (JDK 19+) hoặc capacity ≈ expected/0.75'. |
| minor | factual | 'Bucket đạt 8 node thì thành cây' hơi lệch: mã nguồn treeify khi thêm phần tử vào bin đã có ít nhất 8 node (tức bin có 9 node sau khi thêm). | Viết 'khi thêm vào bin đã có từ 8 node (TREEIFY_THRESHOLD)'. |

**Kiểm chứng:**
- `supported` hash() trộn bit cao xuống bằng h ^ (h >>> 16)
  > return (key == null) ? 0 : (h = key.hashCode()) ^ (h >>> 16);  
  > — https://raw.githubusercontent.com/openjdk/jdk/master/src/java.base/share/classes/java/util/HashMap.java
  _Comment: "So we apply a transform that spreads the impact of higher bits downward."_
- `supported` Capacity mặc định 16 (lũy thừa của 2), load factor mặc định 0.75
  > static final int DEFAULT_INITIAL_CAPACITY = 1 << 4; // aka 16  
  > — https://raw.githubusercontent.com/openjdk/jdk/master/src/java.base/share/classes/java/util/HashMap.java
  _Cùng file: "static final float DEFAULT_LOAD_FACTOR = 0.75f;" và "The default initial capacity - MUST be a power of two."_
- `supported` Vượt capacity × load factor thì rehash sang bảng khoảng gấp đôi; entry giữ index hoặc dịch một offset lũy thừa 2
  > When the number of entries in the hash table exceeds the product of the load factor and the current capacity, the hash table is rehashed (that is, internal data structures are rebuilt) so that the hash table has approximately twice the number of buckets.  
  > — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/HashMap.html
  _Mã nguồn resize(): "elements from each bin must either stay at same index, or move with a power of two offset in the new table."_
- `supported` TREEIFY_THRESHOLD = 8; bảng dưới 64 bucket thì resize thay vì treeify
  > Replaces all linked nodes in bin at index for given hash unless table is too small, in which case resizes instead.  
  > — https://raw.githubusercontent.com/openjdk/jdk/master/src/java.base/share/classes/java/util/HashMap.java
  _Cùng file: "static final int TREEIFY_THRESHOLD = 8;", "static final int MIN_TREEIFY_CAPACITY = 64;" và "Bins are converted to trees when adding an element to a bin with at least this many nodes."_
- `supported` Cây bị tách khi resize mà còn ≤ 6 node thì trở lại danh sách (UNTREEIFY_THRESHOLD = 6)
  > The bin count threshold for untreeifying a (split) bin during a resize operation.  
  > — https://raw.githubusercontent.com/openjdk/jdk/master/src/java.base/share/classes/java/util/HashMap.java
  _static final int UNTREEIFY_THRESHOLD = 6;_
- `supported` Cây sắp theo hashCode; khi trùng hash chỉ dùng compareTo nếu key Comparable, nếu không thì mất lợi ích
  > To ameliorate impact, when keys are Comparable, this class may use comparison order among keys to help break ties.  
  > — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/HashMap.html
  _Mã nguồn: "ordered primarily by hashCode, but in the case of ties, if two elements are of the same "class C implements Comparable<C>", type then their compareTo method is used for ordering."_
- `supported` Duyệt map tốn thời gian tỉ lệ capacity + size, nên không đặt capacity quá lớn
  > Iteration over collection views requires time proportional to the "capacity" of the HashMap instance (the number of buckets) plus its size (the number of key-value mappings).  
  > — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/HashMap.html

**Độ khó:** hard thật · hợp level middle, senior — Đòi hỏi chẩn đoán từ triệu chứng và hiểu internals (spreading, treeify, Comparable), không chỉ định nghĩa.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Hai ý hỏi (vì sao chậm, cách sửa) với khoảng 5 điểm chấm rõ ràng.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu cách HashMap chọn bucket và chuyện gì xảy ra khi hashCode phân bố kém.
- Ý bắt buộc: hashCode chỉ dựa trên trường ít giá trị nên nhiều key dồn vào cùng bucket, get/put thoái hóa; index = hash & (n-1); hash() trộn bit cao xuống nhưng không cứu được khi hashCode trùng hẳn; Bin dài thì treeify (ngưỡng 8, bảng ≥ 64 bucket), nhưng cây chỉ giúp nhiều khi key Comparable; Sửa: hashCode dùng đủ các trường của equals, key immutable; Khai báo capacity trước khi biết số lượng để tránh resize liên tục
- Dấu hiệu trả lời sai: Nói tăng load factor hay capacity sẽ giải quyết được hashCode trùng; Sửa hashCode nhưng không giữ contract với equals; Cho rằng treeify luôn làm thao tác O(log n) bất kể key có Comparable hay không
- Câu hỏi nối tiếp: Nếu key do client bên ngoài gửi lên (có thể cố tình tạo va chạm), bạn phòng thủ thế nào?

### de-qa-1101 · Cần sửa · tin cậy high · Chỉ hình thức

**Topic:** Java Collections và HashMap (`java.core.collections-hashmap`) · ~740 token · hard của topic: 2

**Câu hỏi:** Code cache dùng ConcurrentHashMap viết `if (!map.containsKey(k)) map.put(k, loadExpensive(k));` và bộ đếm viết `counts.put(k, counts.get(k) + 1)`. Dưới tải cao, loadExpensive bị gọi trùng và số đếm bị thiếu. Vì sao ConcurrentHashMap "thread-safe" mà vẫn sai, sửa thế nào, và cần lưu ý gì khi dùng computeIfAbsent?

**Kết luận:** Nội dung đúng và khớp javadoc ConcurrentHashMap (atomic từng thao tác, computeIfAbsent, merge/LongAdder, recursive update). Cần fix vì câu hỏi gồm 3 ý hỏi, quá rộng cho 3–5 phút; các ý phụ 4–5 bị cắt khỏi snippet.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| major | interview_fit | Câu hỏi có 3 ý hỏi (vì sao sai, sửa thế nào, lưu ý khi dùng computeIfAbsent) và đáp án có 5 lưu ý phụ, khó trả lời gọn trong 3–5 phút và khó chấm theo ưu tiên. | Giữ 2 ý: 'Vì sao vẫn sai và sửa thế nào?'; chuyển phần lưu ý computeIfAbsent thành follow-up. |
| minor | length | Chunk ~740 token; điểm cắt 600 token rơi giữa lưu ý 4, mất lưu ý 4–5 (size/mappingCount, happens-before). Ý bắt buộc (check-then-act không atomic, computeIfAbsent, merge/LongAdder, hàm mapping ngắn) vẫn nằm trước điểm cắt. | Bỏ lưu ý 4–5 hoặc gộp thành một câu. |
| minor | factual | Gợi ý lưu CompletableFuture<V> làm value là pattern phổ biến nhưng không có trong javadoc; không nên là điểm chấm bắt buộc. | Ghi rõ đây là một lựa chọn (ví dụ Caffeine/AsyncCache) chứ không phải yêu cầu. |

**Kiểm chứng:**
- `supported` computeIfAbsent thực hiện atomic; hàm mapping được gọi đúng một lần nếu key vắng, không gọi nếu đã có
  > The entire method invocation is performed atomically. The supplied function is invoked exactly once per invocation of this method if the key is absent, else not at all.  
  > — https://raw.githubusercontent.com/openjdk/jdk/master/src/java.base/share/classes/java/util/concurrent/ConcurrentHashMap.java
  _Javadoc bản HTML trên docs.oracle.com bị cắt trước phần method detail, nên trích từ javadoc trong mã nguồn JDK._
- `supported` Trong lúc hàm mapping chạy, một số cập nhật của thread khác có thể bị chặn, nên hàm phải ngắn
  > Some attempted update operations on this map by other threads may be blocked while computation is in progress  
  > — https://raw.githubusercontent.com/openjdk/jdk/master/src/java.base/share/classes/java/util/concurrent/ConcurrentHashMap.java
  _Câu đầy đủ dài hơn giới hạn trích của công cụ; đây là đoạn nguyên văn đầu câu._
- `supported` Hàm mapping không được sửa chính map; recursive update có thể ném IllegalStateException
  > The mapping function must not modify this map during computation.  
  > — https://raw.githubusercontent.com/openjdk/jdk/master/src/java.base/share/classes/java/util/concurrent/ConcurrentHashMap.java
  _@throws: "IllegalStateException if the computation detectably attempts a recursive update to this map that would otherwise never complete"_
- `supported` Mẫu bộ đếm: ConcurrentHashMap<String, LongAdder> với computeIfAbsent(...).increment()
  > A ConcurrentHashMap can be used as a scalable frequency map (a form of histogram or multiset) by using LongAdder values and initializing via computeIfAbsent.  
  > — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ConcurrentHashMap.html
- `supported` Không cho phép null làm key hoặc value
  > Like Hashtable but unlike HashMap, this class does not allow null to be used as a key or value.  
  > — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ConcurrentHashMap.html
- `supported` size/isEmpty/containsValue chỉ là trạng thái tạm thời khi có cập nhật đồng thời, dùng để giám sát chứ không điều khiển logic
  > Otherwise the results of these methods reflect transient states that may be adequate for monitoring or estimation purposes, but not for program control.  
  > — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ConcurrentHashMap.html
  _Về mappingCount, mã nguồn: "This method should be used instead of {@link #size} because a ConcurrentHashMap may..." (câu bị cắt khi trích)._
- `supported` Đọc không chặn; cập nhật một key happens-before lần đọc thấy giá trị đó
  > (More formally, an update operation for a given key bears a happens-before relation with any (non-null) retrieval for that key reporting the updated value.)  
  > — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ConcurrentHashMap.html

**Độ khó:** hard thật · hợp level middle, senior — Phân biệt thread-safe từng thao tác với atomic chuỗi thao tác, cộng các bẫy của compute*: lý luận chứ không chỉ nhớ.
**Dùng trong phỏng vấn:** ~5 phút, 3 ý hỏi, chấm được — Có điểm chấm rõ nhưng 3 ý hỏi, vượt mức 2 của rubric.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu rằng 'thread-safe' của ConcurrentHashMap chỉ áp dụng cho từng lời gọi, không cho chuỗi lời gọi.
- Ý bắt buộc: containsKey rồi put, hay get rồi put là check-then-act/read-modify-write, không atomic; Sửa cache bằng computeIfAbsent (atomic, hàm gọi đúng một lần khi key vắng); Sửa bộ đếm bằng merge(k, 1L, Long::sum) hoặc LongAdder qua computeIfAbsent; Hàm mapping phải ngắn, không gọi I/O chậm, không sửa chính map
- Dấu hiệu trả lời sai: Bọc bằng synchronized quanh từng lời gọi riêng lẻ mà vẫn tách check và act; Cho rằng ConcurrentHashMap làm mọi đoạn code dùng nó trở nên an toàn; Gọi computeIfAbsent lồng nhau trên cùng map
- Câu hỏi nối tiếp: loadExpensive mất 2 giây; gọi nó trong computeIfAbsent trên map nóng thì có vấn đề gì và bạn thiết kế lại ra sao?

**Đề xuất sửa:**
- Câu hỏi mới: Code cache dùng ConcurrentHashMap viết `if (!map.containsKey(k)) map.put(k, loadExpensive(k));` và bộ đếm viết `counts.put(k, counts.get(k) + 1)`. Dưới tải cao, loadExpensive bị gọi trùng và số đếm bị thiếu. Vì sao ConcurrentHashMap "thread-safe" mà vẫn sai, và sửa thế nào?
- Đáp án: Giữ phần nguyên nhân và cách sửa; rút 'Lưu ý' còn 2 ý (hàm mapping ngắn, không sửa chính map). Bỏ lưu ý 3–5 khỏi đáp án hoặc gộp thành một câu; chuyển phần computeIfAbsent nâng cao sang follow-up.

### de-qa-1102 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Đa luồng và concurrency (`java.core.concurrency`) · ~710 token · hard của topic: 2 · golden: g14

**Câu hỏi:** Vì sao double-checked locking cho lazy singleton mà không khai báo volatile lại sai theo Java Memory Model, dù phần khởi tạo đã nằm trong synchronized? Giải thích bằng quan hệ happens-before và nêu các cách sửa cùng trade-off.

**Kết luận:** Giải thích DCL bằng happens-before chính xác theo JLS §17.4.5, các cách sửa (volatile, holder idiom, enum/eager) đều có cơ sở trong JLS. Chỉ có vấn đề nhỏ về độ dài.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | Chunk ~710 token; điểm cắt 600 token rơi vào cách sửa 4 (final field) và mất đoạn 'Bài học'. Các ý bắt buộc (data race, cách sửa volatile/holder/enum) nằm trước điểm cắt. | Bỏ cách sửa 4 hoặc rút đoạn 'Bài học' thành một câu. |

**Kiểm chứng:**
- `supported` Unlock monitor happens-before mọi lần lock sau đó trên cùng monitor
  > An unlock on a monitor happens-before every subsequent lock on that monitor.  
  > — https://docs.oracle.com/javase/specs/jls/se21/html/jls-17.html
- `supported` Ghi volatile happens-before mọi lần đọc sau của biến đó (cơ sở của cách sửa 1)
  > A write to a volatile field (§8.3.1.4) happens-before every subsequent read of that field.  
  > — https://docs.oracle.com/javase/specs/jls/se21/html/jls-17.html
  _Cùng mục: start() và join() cũng tạo cạnh happens-before._
- `supported` Đọc instance ngoài lock không có cạnh happens-before nên là data race
  > When a program contains two conflicting accesses (§17.4.1) that are not ordered by a happens-before relationship, it is said to contain a data race.  
  > — https://docs.oracle.com/javase/specs/jls/se21/html/jls-17.html
- `supported` Holder idiom: class được khởi tạo lazy ở lần truy cập static field đầu tiên, JVM đồng bộ việc khởi tạo
  > Because the Java programming language is multithreaded, initialization of a class or interface requires careful synchronization, since some other thread may be trying to initialize the same class or interface at the same time.  
  > — https://docs.oracle.com/javase/specs/jls/se21/html/jls-12.html
  _§12.4.1: "A class or interface T will be initialized immediately before the first occurrence of any one of the following" ... "A static field declared by T is used and the field is not a constant variable"._
- `supported` Final field: thread thấy reference sau khi constructor xong sẽ thấy đúng giá trị các trường final
  > A thread that can only see a reference to an object after that object has been completely initialized is guaranteed to see the correctly initialized values for that object's final fields.  
  > — https://docs.oracle.com/javase/specs/jls/se21/html/jls-17.html
- `supported` Lớp java.util.concurrent mở rộng bảo đảm happens-before
  > The methods of all classes in java.util.concurrent and its subpackages extend these guarantees to higher-level synchronization.  
  > — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/package-summary.html

**Độ khó:** hard thật · hợp level middle, senior — Phải lý luận bằng JMM (happens-before, reordering), không chỉ nhớ 'thêm volatile'.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Hai ý hỏi (vì sao sai, cách sửa + trade-off), 4–5 điểm chấm rõ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu visibility và happens-before trong Java Memory Model, không chỉ mutual exclusion.
- Ý bắt buộc: Lần đọc đầu tiên nằm ngoài synchronized nên không có cạnh happens-before tới các lệnh ghi trong constructor; Đó là data race: reference có thể được thấy trước khi các trường ghi xong, thread khác thấy object chưa khởi tạo đủ; Sửa 1: khai báo volatile (ghi volatile happens-before đọc volatile); Sửa 2: holder idiom dựa vào khởi tạo class lazy và được JVM đồng bộ; Sửa 3: enum hoặc eager nếu tạo object rẻ
- Dấu hiệu trả lời sai: Nói synchronized bên trong là đủ vì đã khóa; Nghĩ volatile chỉ để 'không cache biến' mà không nhắc thứ tự/happens-before; Cho rằng lỗi không xảy ra trên x86 nên không cần sửa
- Câu hỏi nối tiếp: Nếu mọi trường của Config đều là final thì DCL không volatile có an toàn không? Vì sao vẫn không nên dựa vào đó?

### de-qa-1103 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Đa luồng và concurrency (`java.core.concurrency`) · ~788 token · hard của topic: 2

**Câu hỏi:** Một API aggregator gọi song song 3 service downstream bằng CompletableFuture.supplyAsync(() -> restClient.call(...)) mà không truyền Executor. Khi một downstream chậm, latency toàn service tăng, kể cả những chỗ dùng parallel stream. Bạn phân tích nguyên nhân và thiết kế lại phần thực thi bất đồng bộ thế nào?

**Kết luận:** Phân tích đúng: supplyAsync không truyền Executor chạy trên commonPool dùng chung với parallel stream, blocking I/O làm cạn worker. Quy tắc ThreadPoolExecutor, rejection policy, timeout đều khớp javadoc. Chỉ có vấn đề nhỏ về độ dài và số ý.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | Chunk ~788 token; điểm cắt 600 token rơi vào ý 4 (bulkhead), mất ý 5–6 và đoạn virtual thread. Các ý bắt buộc (commonPool, executor riêng có queue giới hạn, rejection, timeout) nằm trước điểm cắt. | Bỏ ý 5–6 (xử lý lỗi, callback) hoặc chuyển sang follow-up; rút đoạn virtual thread còn một câu. |
| minor | interview_fit | Đáp án có 6 ý thiết kế cộng virtual thread, hơi dài cho một câu 4–5 phút; người chấm nên ưu tiên 3–4 ý đầu. | Đánh dấu ý 1–3 là bắt buộc, phần còn lại là điểm cộng. |
| minor | factual | Ý virtual thread (JDK 21) chưa được kiểm chứng trong lần duyệt này, nhưng không phải ý chấm chính. | Giữ ngắn và ghi rõ JDK 21+. |

**Kiểm chứng:**
- `supported` Method *Async không truyền Executor chạy trên ForkJoinPool.commonPool() (trừ khi parallelism < 2 thì tạo Thread mới)
  > All async methods without an explicit Executor argument are performed using the ForkJoinPool.commonPool() (unless it does not support a parallelism level of at least two, in which case, a new Thread is created to run each task).  
  > — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/CompletableFuture.html
- `supported` Common pool dùng chung cho mọi ForkJoinTask không submit vào pool cụ thể (gồm parallel stream)
  > The common pool is used by any ForkJoinTask that is not explicitly submitted to a specified pool.  
  > — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ForkJoinPool.html
  _Việc parallel stream dùng common pool là chi tiết cài đặt, không nêu trong trang này._
- `supported` ForkJoinPool không bảo đảm bù thread khi gặp blocking I/O
  > However, no such adjustments are guaranteed in the face of blocked I/O or other unmanaged synchronization.  
  > — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ForkJoinPool.html
- `supported` ThreadPoolExecutor: đủ core thì ưu tiên queue; queue đầy mới tạo thêm tới max, vượt thì reject; queue không giới hạn làm max vô tác dụng
  > If a request cannot be queued, a new thread is created unless this would exceed maximumPoolSize, in which case, the task will be rejected.  
  > — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ThreadPoolExecutor.html
  _Về queue không giới hạn: "(And the value of the maximumPoolSize therefore doesn't have any effect.)"_
- `supported` AbortPolicy mặc định ném RejectedExecutionException; CallerRunsPolicy cho thread gọi tự chạy task, tạo backpressure
  > In ThreadPoolExecutor.CallerRunsPolicy, the thread that invokes execute itself runs the task. This provides a simple feedback control mechanism that will slow down the rate that new tasks are submitted.  
  > — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ThreadPoolExecutor.html
  _"In the default ThreadPoolExecutor.AbortPolicy, the handler throws a runtime RejectedExecutionException upon rejection."_
- `supported` orTimeout/completeOnTimeout; timeout của future không hủy được I/O đang chạy nên cần timeout ở HTTP client
  > Since (unlike FutureTask) this class has no direct control over the computation that causes it to be completed, cancellation is treated as just another form of exceptional completion.  
  > — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/CompletableFuture.html
  _orTimeout: "Exceptionally completes this CompletableFuture with a TimeoutException if not otherwise completed before the given timeout."_
- `supported` join() ném CompletionException, get() ném ExecutionException; callback không async có thể chạy trên thread hoàn tất future
  > Actions supplied for dependent completions of non-async methods may be performed by the thread that completes the current CompletableFuture, or by any other caller of a completion method.  
  > — https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/CompletableFuture.html
  _"this class also defines methods join() and getNow(T) that instead throw the CompletionException directly in these cases."_

**Độ khó:** hard thật · hợp level middle, senior — Chẩn đoán từ triệu chứng (latency lan sang parallel stream) và thiết kế executor/bulkhead/timeout: lý luận về thread pool.
**Dùng trong phỏng vấn:** ~5 phút, 2 ý hỏi, chấm được — Hai ý hỏi; điểm chấm rõ nhưng nhiều, cần ưu tiên.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu async mặc định chạy trên thread pool nào và vì sao blocking I/O trên pool dùng chung gây nghẽn lan rộng.
- Ý bắt buộc: supplyAsync không truyền Executor chạy trên ForkJoinPool.commonPool(), pool dùng chung với parallel stream; Common pool ít thread và không bù thread khi task block I/O, nên một downstream chậm làm mọi việc khác xếp hàng; Dùng executor riêng cho I/O, truyền tường minh, queue có giới hạn và rejection policy rõ ràng; Timeout từng nhánh (orTimeout/completeOnTimeout) kèm timeout ở HTTP client; Bulkhead: tách pool hoặc giới hạn đồng thời theo downstream
- Dấu hiệu trả lời sai: Tăng parallelism của common pool là đủ; Dùng LinkedBlockingQueue không giới hạn rồi tin maximumPoolSize sẽ tăng thread; Nghĩ orTimeout hủy được lời gọi HTTP đang block
- Câu hỏi nối tiếp: Nếu chuyển sang virtual thread thì còn cần bulkhead không, và giới hạn đồng thời đặt ở đâu?

### de-qa-1104 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** JVM, bộ nhớ và Garbage Collection (`java.core.jvm-memory-gc`) · ~692 token · hard của topic: 2 · golden: g02

**Câu hỏi:** Một service Java chạy vài ngày thì ném OutOfMemoryError: Java heap space, restart xong lại ổn một thời gian. Làm sao phân biệt memory leak với heap cấu hình quá nhỏ, và quy trình thu thập, phân tích bằng chứng trên production của bạn ra sao?

**Kết luận:** Đúng theo Troubleshooting Guide JDK 21: phân biệt leak và heap nhỏ, HeapDumpOnOutOfMemoryError, histogram định kỳ, JFR OldObjectSample. Còn một sắc thái nhỏ: dump với path-to-gc-roots=true có overhead cỡ một full GC, không 'thấp' như ghi.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | factual | Ghi JFR 'overhead thấp nên dùng được trên production' đúng cho việc ghi recording, nhưng tài liệu nói dump với path-to-gc-roots=true tốn overhead cỡ một full GC. | Thêm: 'dump với path-to-gc-roots=true tốn cỡ một full GC, nên chọn thời điểm'. |
| minor | length | Chunk ~692 token; điểm cắt 600 token rơi vào cuối danh sách nguyên nhân, mất đoạn 'Khắc phục'. Hai ý được hỏi (phân biệt leak/heap nhỏ và quy trình thu thập/phân tích) nằm trước điểm cắt. | Rút đoạn 'Khắc phục' còn một câu hoặc rút danh sách nguyên nhân hay gặp còn 3 mục. |

**Kiểm chứng:**
- `supported` 'Java heap space' chỉ nói không cấp phát được object, không tự chứng minh leak; có thể chỉ là heap quá nhỏ
  > This error does not necessarily imply a memory leak. The problem can be as simple as a configuration issue, where the specified heap size (or the default size, if it is not specified) is insufficient for the application.  
  > — https://docs.oracle.com/en/java/javase/21/troubleshoot/troubleshooting-memory-leaks.html
- `supported` Leak kiểu Java là vô tình giữ reference khiến object không được thu hồi
  > the message might indicate that the application is unintentionally holding references to objects, which prevents the objects from being garbage collected. This is the Java language equivalent of a memory leak.  
  > — https://docs.oracle.com/en/java/javase/21/troubleshoot/troubleshooting-memory-leaks.html
- `supported` -XX:+HeapDumpOnOutOfMemoryError lấy heap dump đúng lúc lỗi
  > You can use the -XX:+HeapDumpOnOutOfMemoryError Java option to dump the Java heap of a process when it fails with a java.lang.OutOfMemoryError error.  
  > — https://docs.oracle.com/en/java/javase/21/troubleshoot/troubleshooting-memory-leaks.html
- `supported` jcmd GC.class_histogram lấy định kỳ để thấy class nào tăng đều
  > If a sequence of histograms is obtained (for example, every two minutes), then you might be able to see a trend that can lead to further analysis.  
  > — https://docs.oracle.com/en/java/javase/21/troubleshoot/troubleshooting-memory-leaks.html
- `supported` JFR OldObjectSample cho thời điểm cấp phát, stack trace và đường tới GC root
  > This event contains the time of allocation, the allocation stack trace, and the path back to the GC root.  
  > — https://docs.oracle.com/en/java/javase/21/troubleshoot/troubleshooting-memory-leaks.html
  _Cùng trang: "Setting path-to-gc-roots=true creates overhead, similar to a full garbage collection"._
- `supported` Classloader leak thường cho OOM Metaspace
  > If the Metaspace for class metadata is exhausted, a java.lang.OutOfMemoryError error with a detail message Metaspace is thrown.  
  > — https://docs.oracle.com/en/java/javase/21/troubleshoot/troubleshooting-memory-leaks.html
  _"Information about class loaders and the number of classes loaded by them can be very helpful in diagnosing memory leaks related to Metaspace"_

**Độ khó:** hard thật · hợp level middle, senior — Chẩn đoán trên production bằng dữ liệu (live set sau GC, histogram, dump), không chỉ định nghĩa OOM.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Hai ý hỏi, 4–5 điểm chấm rõ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Biết phân biệt leak với heap quá nhỏ bằng bằng chứng, và biết thu bằng chứng an toàn trên production.
- Ý bắt buộc: OOM Java heap space không tự chứng minh leak; Nhìn heap sau GC theo thời gian: mức đáy tăng dần là leak, phẳng là thiếu heap hoặc spike; Bật HeapDumpOnOutOfMemoryError và GC log từ trước; Histogram định kỳ hoặc JFR OldObjectSample để thấy object sống lâu; Phân tích dump bằng dominator tree / retained size và đường tới GC root
- Dấu hiệu trả lời sai: Tăng -Xmx là xong; Chụp heap dump liên tục trên production mà không nghĩ tới pause và disk; Nhầm OOM Metaspace với leak heap
- Câu hỏi nối tiếp: Heap dump cho thấy một HashMap static giữ 2 GB; bạn tìm ai đang thêm vào nó và sửa thế nào?

### de-qa-1105 · Cần sửa · tin cậy high · Chỉ hình thức

**Topic:** JVM, bộ nhớ và Garbage Collection (`java.core.jvm-memory-gc`) · ~680 token · hard của topic: 2

**Câu hỏi:** Service có heap 24 GB, SLO p99 latency 50 ms; GC log của G1 cho thấy pause 150–300 ms ở các mixed collection và thỉnh thoảng có Full GC. Bạn đọc log để tìm nguyên nhân thế nào, tune G1 ra sao, và khi nào chuyển sang ZGC? Nêu trade-off.

**Kết luận:** Các fact về G1 và ZGC đều đúng và có version (IHOP 45%, MaxGCPauseMillis 200 ms, humongous, JEP 439/474). Cần fix vì câu hỏi có 4 ý hỏi và phần trade-off được hỏi trực tiếp lại nằm sau điểm cắt 600 token.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| major | interview_fit | Câu hỏi có 4 ý hỏi (đọc log, tune G1, khi nào chuyển ZGC, trade-off), quá rộng cho 3–5 phút. | Thu hẹp còn 2 ý: 'Đọc log tìm nguyên nhân pause dài/Full GC thế nào, và khi nào bạn chuyển sang ZGC (trade-off)?'; chuyển phần tune G1 sang follow-up. |
| major | length | Chunk ~680 token; điểm cắt 600 token rơi ngay trước 'Trade-off' của ZGC, trong khi câu hỏi yêu cầu nêu trade-off. Snippet của Planner mất đúng ý được hỏi. | Rút đoạn 'Cách G1 làm việc' còn 2 câu và đưa trade-off (CPU, headroom, allocation stall) lên ngay sau 'Khi nào chọn ZGC'. |
| minor | outdated | Cờ -XX:+ZGenerational đã bị deprecate ở JDK 23 (JEP 474); ở các bản mới hơn chế độ non-generational có thể đã bị bỏ hẳn (chưa fetch kiểm chứng JEP tương ứng). Đáp án nêu đúng version nhưng nên nói rõ cờ chỉ cần trên JDK 21–22. | Viết: 'JDK 21–22 cần thêm -XX:+ZGenerational; từ JDK 23 chỉ cần -XX:+UseZGC.' |

**Kiểm chứng:**
- `supported` G1 là collector mặc định
  > G1 is the default collector.  
  > — https://docs.oracle.com/en/java/javase/21/gctuning/garbage-first-g1-garbage-collector1.html
- `supported` IHOP mặc định 45%, có cơ chế adaptive
  > By default, the initiating value is set to 45%.  
  > — https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html
  _GC tuning guide: "G1 by default automatically determines an optimal IHOP ... This feature is called Adaptive IHOP."_
- `supported` MaxGCPauseMillis là mục tiêu mềm, mặc định 200 ms; G1 không phải real-time
  > This is a soft goal, and the JVM will make its best effort to achieve it. The specified value doesn't adapt to your heap size. By default, for G1 the maximum pause time target is 200 milliseconds.  
  > — https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html
  _Tuning guide: "The Garbage-First collector is not a real-time collector."_
- `supported` Evacuation failure có thể dẫn tới Full GC compact toàn heap tại chỗ, rất chậm
  > If this assumption doesn't hold, then G1 will eventually schedule a Full GC. This type of collection performs in-place compaction of the entire heap. This might be very slow.  
  > — https://docs.oracle.com/en/java/javase/21/gctuning/garbage-first-g1-garbage-collector1.html
  _"When the application keeps alive so much memory so that an evacuation can't find enough space to copy to, an evacuation failure occurs."_
- `supported` Humongous: object ≥ nửa region, cấp phát thành chuỗi region liền ở old gen, thường chỉ thu hồi ở Cleanup hoặc Full GC
  > Generally, humongous objects can be reclaimed only at the end of marking during the Cleanup pause, or during Full GC if they became unreachable.  
  > — https://docs.oracle.com/en/java/javase/21/gctuning/garbage-first-g1-garbage-collector1.html
  _"Humongous objects are objects larger or equal the size of half a region." Ngoại lệ: eager reclaim cho mảng primitive (G1EagerReclaimHumongousObjects, mặc định bật)._
- `supported` G1HeapRegionSize là lũy thừa 2 từ 1 đến 32 MB
  > The value is a power of 2 and can range from 1 MB to 32 MB.  
  > — https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html
  _Theo man page JDK 21._
- `supported` JEP 439 (JDK 21): mục tiêu pause không quá 1 ms, bật bằng -XX:+UseZGC -XX:+ZGenerational
  > Pause times should not exceed 1 millisecond,  
  > — https://openjdk.org/jeps/439
  _Cùng trang: "$ java -XX:+UseZGC -XX:+ZGenerational ..."; Release 21._
- `supported` Generational là chế độ mặc định của -XX:+UseZGC từ JDK 23
  > Make Generational ZGC the default mode of ZGC by changing the default value of the ZGenerational option from false to true.  
  > — https://openjdk.org/jeps/474
  _Release 23. JEP cũng deprecate option ZGenerational._

**Độ khó:** hard thật · hợp level senior — Đọc GC log, chọn tham số và so sánh collector theo SLO: kiến thức vận hành sâu, thiên senior.
**Dùng trong phỏng vấn:** ~6 phút, 4 ý hỏi, chấm được — Điểm chấm rõ nhưng 4 ý hỏi, vượt 2.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu cơ chế G1 đủ để giải thích pause dài/Full GC và biết khi nào cần collector pause thấp như ZGC.
- Ý bắt buộc: Mixed pause dài do sơ tán region old chứa nhiều object sống; Full GC thường do evacuation failure hoặc marking bắt đầu muộn; Full GC của G1 compact cả heap, rất chậm; Humongous object (≥ nửa region) gây lãng phí và Full GC; tăng region size hoặc giảm buffer lớn; MaxGCPauseMillis là mục tiêu mềm (mặc định 200 ms), không bảo đảm; ZGC khi cần pause rất thấp không phụ thuộc heap; trả giá bằng CPU, headroom, có thể allocation stall
- Dấu hiệu trả lời sai: Đặt MaxGCPauseMillis=10 rồi tin G1 sẽ đạt; Nghĩ ZGC không bao giờ làm tăng latency; Tăng heap mà không xem live set và tốc độ cấp phát
- Câu hỏi nối tiếp: Sau khi chuyển ZGC, p99 vẫn vượt SLO và log có 'Allocation Stall'. Bạn làm gì tiếp?

**Đề xuất sửa:**
- Câu hỏi mới: Service có heap 24 GB, SLO p99 latency 50 ms; GC log của G1 cho thấy pause 150–300 ms ở các mixed collection và thỉnh thoảng có Full GC. Bạn đọc log để tìm nguyên nhân thế nào, và khi nào bạn chuyển sang ZGC thay vì tune tiếp G1 (nêu trade-off)?
- Đáp án: Rút 'Cách G1 làm việc' còn 2 câu; giữ phần đọc log; gộp 'Tune G1' thành một câu; đưa trade-off ZGC lên trước điểm cắt; ghi 'JDK 21–22 cần -XX:+ZGenerational, từ JDK 23 là mặc định'.

### de-qa-1106 · Cần sửa · tin cậy high · Chỉ hình thức

**Topic:** JPA và Hibernate (`java.data.jpa-hibernate`) · ~732 token · hard của topic: 2 · golden: g15

**Câu hỏi:** Endpoint liệt kê 20 đơn hàng kèm danh sách item và tên khách hàng sinh ra 41 câu SQL. Một dev sửa bằng `JOIN FETCH o.items` kèm phân trang thì số câu giảm nhưng memory và thời gian tăng khi bảng lớn. Giải thích N+1, vì sao cách sửa đó sai, và các chiến lược fetch đúng cùng trade-off.

**Kết luận:** Nội dung đúng theo tài liệu Hibernate 6.6 (N+1, phân trang in-memory khi join fetch collection, batch/subselect fetching, lazy mặc định). Cần fix vì câu hỏi gồm 3 ý hỏi lớn, quá rộng cho 3–5 phút.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| major | interview_fit | Câu hỏi có 3 ý hỏi (giải thích N+1, vì sao cách sửa sai, các chiến lược đúng kèm trade-off) và đáp án liệt kê 6 chiến lược, khó trả lời gọn và khó chấm theo ưu tiên. | Hỏi 2 ý: 'Vì sao JOIN FETCH items kèm phân trang làm chậm và tốn RAM, và bạn sửa thế nào?'; phần giải thích N+1 coi như nền, các chiến lược phụ (subselect, DTO) thành follow-up. |
| minor | length | Chunk ~732 token; điểm cắt 600 token rơi ở cuối chiến lược 4 (batch fetching), mất subselect, DTO projection và phần phòng ngừa. Ý bắt buộc (N+1, phân trang in-memory, truy vấn hai bước, to-one join fetch) nằm trước điểm cắt. | Bỏ chiến lược 5–6 và phần phòng ngừa hoặc gộp thành một câu. |
| minor | factual | Ý 'viết test khẳng định số câu SQL' là thực hành tốt nhưng tài liệu Hibernate không nêu; tài liệu chỉ nhắc statistics/log slow query. | Viết 'bật hibernate.generate_statistics hoặc log SQL trong test để đếm số câu'. |

**Kiểm chứng:**
- `supported` N+1 là nguyên nhân phổ biến nhất khiến code truy cập dữ liệu chậm
  > Without question, the most common cause of poorly-performing data access code in Java programs  
  > — https://raw.githubusercontent.com/hibernate/hibernate-orm/6.6/documentation/src/main/asciidoc/introduction/Tuning.adoc
  _Bản HTML html_single bị cắt trước chương 7 khi fetch; trích từ file nguồn asciidoc chính thức nhánh 6.6._
- `supported` Join fetch collection kèm phân trang khiến limit áp dụng trong bộ nhớ; FAIL_ON_PAGINATION_OVER_COLLECTION_FETCH biến thành exception
  > When pagination is used in combination with a fetch join applied to a collection or many-valued association, the limit must be applied in-memory instead of on the database.  
  > — https://docs.hibernate.org/orm/6.6/javadocs/org/hibernate/cfg/QuerySettings.html
  _"When enabled, this setting specifies that an exception should be thrown for any query which would result in the limit being applied in-memory."_
- `supported` Join fetch hai collection cùng lúc tạo tích Descartes
  > Joining both collections in a single query would result in a cartesian product of tables  
  > — https://raw.githubusercontent.com/hibernate/hibernate-orm/6.6/documentation/src/main/asciidoc/introduction/Tuning.adoc
- `supported` Hầu hết association nên LAZY; EAGER không phải cách chữa
  > Almost all associations should be lazy.  
  > — https://docs.hibernate.org/orm/6.6/introduction/html_single/Hibernate_Introduction.html
  _Trang gọi eager mặc định của @ManyToOne trong JPA là misfeature._
- `supported` Batch fetching giảm nhẹ chứ không giải quyết triệt để N+1
  > While batch fetching might _mitigate_ problems involving N+1 selects, it won't solve them.  
  > — https://raw.githubusercontent.com/hibernate/hibernate-orm/6.6/documentation/src/main/asciidoc/introduction/Tuning.adoc
- `supported` Subselect fetching nạp association bằng một câu select kèm khóa truy vấn lại trong subselect
  > where an association is fetched using a subsequent `select` with keys re-queried in a subselect  
  > — https://raw.githubusercontent.com/hibernate/hibernate-orm/6.6/documentation/src/main/asciidoc/introduction/Tuning.adoc

**Độ khó:** hard thật · hợp level middle, senior — Phải hiểu vì sao join fetch collection phá phân trang và chọn chiến lược fetch theo use case.
**Dùng trong phỏng vấn:** ~5 phút, 3 ý hỏi, chấm được — Có điểm chấm rõ nhưng 3 ý hỏi, vượt 2.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu N+1 và cách chọn chiến lược fetch trong Hibernate/JPA cho danh sách có phân trang.
- Ý bắt buộc: N+1: 1 câu lấy cha + mỗi association lazy bị chạm lại thêm 1 câu; vấn đề là số round trip; Join fetch collection nhân dòng nên Hibernate phải phân trang trong bộ nhớ; To-one (customer) join fetch an toàn với phân trang; Collection + phân trang: truy vấn hai bước (trang ID rồi join fetch theo ID) hoặc batch fetching; Association để LAZY, chọn fetch theo use case; EAGER không chữa N+1
- Dấu hiệu trả lời sai: Đổi sang FetchType.EAGER để hết N+1; Join fetch nhiều collection trong một query; Cho rằng batch fetching xóa hẳn N+1
- Câu hỏi nối tiếp: Màn hình chỉ đọc cần 3 cột từ order và tổng số item; bạn có cần load entity không?

**Đề xuất sửa:**
- Câu hỏi mới: Endpoint liệt kê 20 đơn hàng kèm danh sách item và tên khách hàng sinh ra 41 câu SQL. Một dev sửa bằng `JOIN FETCH o.items` kèm phân trang thì số câu giảm nhưng memory và thời gian tăng khi bảng lớn. Vì sao cách sửa đó sai, và bạn sẽ fetch thế nào cho đúng?
- Đáp án: Giữ đoạn N+1 thành một câu nền; giữ phần 'vì sao sai' và chiến lược 1–4; bỏ chiến lược 5–6 và phần phòng ngừa (hoặc chuyển thành follow-up).

### de-qa-1107 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** JPA và Hibernate (`java.data.jpa-hibernate`) · ~727 token · hard của topic: 2

**Câu hỏi:** Job đồng bộ 1 triệu bản ghi viết bằng Spring Data JPA trong một @Transactional duy nhất: đọc từng entity, sửa vài trường rồi lưu. Job chạy chậm dần rồi chết vì OutOfMemoryError. Phân tích nguyên nhân dựa trên persistence context và dirty checking, và bạn viết lại job thế nào?

**Kết luận:** Phân tích đúng theo User Guide Hibernate 6.6: persistence context giữ mọi entity, cần flush()/clear() theo chunk, JDBC batching bị tắt với IDENTITY, StatelessSession. Chỉ còn vấn đề nhỏ về độ dài và hai ý phụ chưa kiểm chứng.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | Chunk ~727 token; điểm cắt 600 token rơi vào ý 6 (StatelessSession), mất ý 6–7. Nguyên nhân và các ý viết lại chính (chunk + flush/clear, JDBC batching, đọc theo khóa, transaction ngắn) nằm trước điểm cắt. | Gộp ý 5–7 thành một dòng 'lựa chọn khác: read-only, StatelessSession, bulk UPDATE'. |
| minor | factual | Hai ý phụ chưa kiểm chứng trong lần duyệt: read-only bỏ dirty checking (ý 5) và bulk UPDATE đi vòng qua persistence context (ý 7); trang Batching.adoc không nói rõ ý 7. Cả hai đúng theo hiểu biết chung nhưng không nên là điểm chấm bắt buộc. | Giữ là điểm cộng; nếu giữ ý 7, dẫn tài liệu HQL bulk operations. |

**Kiểm chứng:**
- `supported` Mọi entity nằm trong session-level cache (first-level cache), loop lớn có thể OOM
  > Hibernate caches all the newly inserted Person instances in the session-level cache  
  > — https://raw.githubusercontent.com/hibernate/hibernate-orm/6.6/documentation/src/main/asciidoc/userguide/chapters/batch/Batching.adoc
  _Ví dụ trong tài liệu dẫn tới OutOfMemoryException; tài liệu nói về insert, cùng cơ chế áp dụng cho entity được load._
- `supported` Gọi flush() rồi clear() định kỳ để giới hạn first-level cache
  > employ methods flush() and clear() to the session regularly, to control the size of the first-level cache.  
  > — https://raw.githubusercontent.com/hibernate/hibernate-orm/6.6/documentation/src/main/asciidoc/userguide/chapters/batch/Batching.adoc
- `supported` Flush mode AUTO flush trước query JPQL/HQL chồng lấn với thay đổi chưa ghi
  > prior to executing a JPQL/HQL query that overlaps with the queued entity actions  
  > — https://raw.githubusercontent.com/hibernate/hibernate-orm/6.6/documentation/src/main/asciidoc/userguide/chapters/flushing/Flushing.adoc
  _Dirty checking: "The dirty checking mechanism is responsible for determining if a managed entity has been modified since it was first loaded."_
- `supported` hibernate.jdbc.batch_size bật JDBC batching
  > Controls the maximum number of statements Hibernate will batch together before asking the driver to execute the batch.  
  > — https://raw.githubusercontent.com/hibernate/hibernate-orm/6.6/documentation/src/main/asciidoc/userguide/chapters/batch/Batching.adoc
- `supported` Hibernate âm thầm tắt insert batching khi dùng IDENTITY generator
  > Hibernate disables insert batching at the JDBC level transparently if you use an identity identifier generator.  
  > — https://raw.githubusercontent.com/hibernate/hibernate-orm/6.6/documentation/src/main/asciidoc/userguide/chapters/batch/Batching.adoc
- `supported` StatelessSession: không persistence context, không dirty checking, collection bị bỏ qua, dễ data aliasing
  > there's no transactional write-behind or automatic dirty checking.  
  > — https://raw.githubusercontent.com/hibernate/hibernate-orm/6.6/documentation/src/main/asciidoc/userguide/chapters/batch/Batching.adoc
  _Cùng trang: "collections are ignored by a stateless session," và "stateless sessions are vulnerable to data aliasing effects."_

**Độ khó:** hard thật · hợp level middle, senior — Phải nối triệu chứng (chậm dần rồi OOM) với persistence context và dirty checking, rồi thiết kế lại batch.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Hai ý hỏi (nguyên nhân, viết lại), điểm chấm rõ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu persistence context giữ entity tới khi clear và hệ quả với job batch lớn.
- Ý bắt buộc: Mọi entity load trong transaction nằm trong first-level cache tới khi clear, nên heap tăng tuyến tính; Mỗi lần flush phải dirty-check toàn bộ entity managed nên càng chạy càng chậm; Chia chunk, flush() + clear() sau mỗi chunk; Bật hibernate.jdbc.batch_size; IDENTITY tắt insert batching; Đọc theo khóa hoặc stream, mỗi chunk một transaction ngắn
- Dấu hiệu trả lời sai: Tăng -Xmx là giải pháp; Gọi save() từng entity là đủ để giải phóng bộ nhớ; Dùng OFFSET sâu để phân trang 1 triệu bản ghi
- Câu hỏi nối tiếp: Job chết ở bản ghi 600 nghìn; làm sao chạy lại mà không xử lý trùng?

### de-qa-1108 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** SQL, index và tối ưu truy vấn (`java.data.sql-index-tuning`) · ~711 token · hard của topic: 2

**Câu hỏi:** Một query PostgreSQL JOIN orders với customers, lọc `country = 'VN' AND city = 'Hanoi'`, trước chạy 50 ms nhưng sau khi dữ liệu tăng mất 20 giây. EXPLAIN ANALYZE cho thấy Nested Loop với ước lượng rows=12 ở phía ngoài nhưng thực tế 180000 dòng. Bạn đọc plan này thế nào và xử lý ra sao?

**Kết luận:** Đọc plan và chẩn đoán underestimate do giả định độc lập giữa các cột là chính xác theo tài liệu PostgreSQL; cách sửa bằng extended statistics, statistics target, BEGIN/ROLLBACK đều có trích dẫn. Chỉ có vấn đề nhỏ về độ dài.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | Chunk ~711 token; điểm cắt 600 token rơi vào cuối ý xử lý 3, mất ý 4–5 và câu về BEGIN/ROLLBACK. Ý bắt buộc (so estimate/actual, nhân loops, giả định độc lập, ANALYZE và CREATE STATISTICS) nằm trước điểm cắt. | Rút phần 'Ba chiến lược join' còn một câu (chỉ cần Nested Loop) để giữ ý 4–5. |

**Kiểm chứng:**
- `supported` EXPLAIN ANALYZE chạy thật và in số dòng, thời gian thực cạnh ước lượng
  > With this option, EXPLAIN actually executes the query, and then displays the true row counts and true run time accumulated within each plan node, along with the same estimates that a plain EXPLAIN shows.  
  > — https://www.postgresql.org/docs/current/using-explain.html
- `supported` Node chạy nhiều lần: actual time/rows là trung bình mỗi lần, nhân loops để ra tổng
  > In such cases, the loops value reports the total number of executions of the node, and the actual time and rows values shown are averages per-execution.  
  > — https://www.postgresql.org/docs/current/using-explain.html
  _"Multiply by the loops value to get the total time actually spent in the node."_
- `supported` Nested Loop quét phía trong mỗi dòng phía ngoài; tốt khi phía trong có index trên khóa join
  > The right relation is scanned once for every row found in the left relation. This strategy is easy to implement but can be very time consuming. (However, if the right relation can be scanned with an index scan, this can be a good strategy.  
  > — https://www.postgresql.org/docs/current/planner-optimizer.html
  _Cùng trang mô tả hash join và merge join khớp với đáp án._
- `supported` Planner mặc định coi các điều kiện độc lập, gây underestimate khi cột phụ thuộc nhau
  > without knowledge of the functional dependency, the query planner will assume that the conditions are independent, resulting in underestimating the result size.  
  > — https://www.postgresql.org/docs/current/planner-stats.html
- `supported` Extended statistics loại dependencies chỉ áp dụng cho điều kiện bằng hoặc IN với hằng số
  > Functional dependencies are currently only applied when considering simple equality conditions that compare columns to constant values, and IN clauses with constant values.  
  > — https://www.postgresql.org/docs/current/planner-stats.html
  _Trang cũng mô tả ndistinct và MCV cho tổ hợp cột._
- `supported` ALTER TABLE ... SET STATISTICS tăng số most-common values lưu cho cột
  > can be set on a column-by-column basis using the ALTER TABLE SET STATISTICS command, or globally by setting the default_statistics_target configuration variable.  
  > — https://www.postgresql.org/docs/current/planner-stats.html
- `supported` EXPLAIN ANALYZE cho UPDATE/DELETE nên bọc BEGIN ... ROLLBACK
  > If you want to analyze a data-modifying query without changing your tables, you can roll the command back afterwards, for example:  
  > — https://www.postgresql.org/docs/current/using-explain.html

**Độ khó:** hard thật · hợp level middle, senior — Đọc plan thật, tìm gốc ước lượng sai và chọn cách sửa phù hợp: debugging cụ thể, không phải định nghĩa.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Hai ý hỏi (đọc plan, xử lý), 4–5 điểm chấm rõ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Biết đọc EXPLAIN ANALYZE và nhận ra planner chọn sai plan vì ước lượng số dòng sai.
- Ý bắt buộc: So estimated rows với actual rows là bước quan trọng nhất; node trong loop phải nhân loops; Planner tin phía ngoài 12 dòng nên chọn Nested Loop, thực tế 180000 lần quét phía trong; Ước lượng sai vì coi country và city độc lập trong khi city gần như quyết định country; Sửa: ANALYZE, CREATE STATISTICS (dependencies) ON country, city, rồi ANALYZE; Xác nhận lại estimate sát actual sau khi sửa
- Dấu hiệu trả lời sai: Tắt enable_nestloop toàn cục để 'chữa'; Chỉ thêm index mà không nhìn vào estimate; Chạy EXPLAIN ANALYZE cho DELETE trên production mà không ROLLBACK
- Câu hỏi nối tiếp: Nếu điều kiện là city IN (SELECT ...) thay vì hằng số thì extended statistics còn giúp không?

### de-qa-1109 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** SQL, index và tối ưu truy vấn (`java.data.sql-index-tuning`) · ~663 token · hard của topic: 2 · golden: g04

**Câu hỏi:** API danh sách giao dịch dùng `ORDER BY created_at DESC LIMIT 20 OFFSET :offset`. Trang đầu nhanh nhưng trang thứ 5000 mất vài giây, và người dùng thấy bản ghi bị lặp hoặc mất khi có dữ liệu mới chèn vào. Giải thích nguyên nhân và thiết kế keyset pagination, gồm index cần tạo và các trade-off.

**Kết luận:** Đúng và đủ: OFFSET phải tính rồi bỏ các dòng bị skip, ORDER BY phải duy nhất, keyset bằng row comparison, index (account_id, created_at, id) đều khớp tài liệu PostgreSQL. Chỉ có vấn đề nhỏ về độ dài.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | Chunk ~663 token; điểm cắt 600 token rơi vào trade-off thứ 2, mất 3 trade-off cuối (đảo chiều cho trang trước, index theo kiểu sort, bản ghi mới trước cursor). Nguyên nhân, query keyset, index và trade-off chính (không nhảy trang) vẫn nằm trước điểm cắt. | Rút đoạn giải thích row constructor còn một câu để giữ đủ trade-off. |

**Kiểm chứng:**
- `supported` Các dòng bị OFFSET bỏ qua vẫn phải được tính trong server nên OFFSET lớn chậm
  > The rows skipped by an OFFSET clause still have to be computed inside the server; therefore a large OFFSET might be inefficient.  
  > — https://www.postgresql.org/docs/current/queries-limit.html
- `supported` ORDER BY phải tạo thứ tự duy nhất, nếu không tập con trả về không dự đoán được (cần tie-breaker id)
  > When using LIMIT, it is important to use an ORDER BY clause that constrains the result rows into a unique order. Otherwise you will get an unpredictable subset of the query's rows.  
  > — https://www.postgresql.org/docs/current/queries-limit.html
- `supported` So sánh row constructor xét từ trái sang phải, dừng ở cặp khác nhau đầu tiên
  > For the <, <=, > and >= cases, the row elements are compared left-to-right, stopping as soon as an unequal or null pair of elements is found.  
  > — https://www.postgresql.org/docs/current/functions-comparisons.html
- `supported` Index nhiều cột: cột so sánh bằng đứng đầu rồi tới cột range/sắp xếp
  > The exact rule is that equality constraints on leading columns, plus any inequality constraints on the first column that does not have an equality constraint, will always be used to limit the portion of the index that is scanned.  
  > — https://www.postgresql.org/docs/current/indexes-multicolumn.html
- `supported` ORDER BY + LIMIT n với index khớp thì lấy thẳng n dòng đầu, không sort toàn bộ; index quét ngược phục vụ DESC
  > if there is an index matching the ORDER BY, the first n rows can be retrieved directly, without scanning the remainder at all.  
  > — https://www.postgresql.org/docs/current/indexes-ordering.html
  _"The index can also be scanned backward, producing output satisfying ORDER BY x DESC"_
- `supported` ORDER BY trộn ASC/DESC cần index khai báo chiều tương ứng
  > There is no way to get that ordering from a plain index, but it is possible if the index is defined as (x ASC, y DESC) or (x DESC, y ASC).  
  > — https://www.postgresql.org/docs/current/indexes-ordering.html

**Độ khó:** hard thật · hợp level middle, senior — Cần hiểu vì sao OFFSET chậm và sai, thiết kế cursor có tie-breaker và index đúng thứ tự.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Hai ý hỏi (nguyên nhân, thiết kế keyset kèm index/trade-off), điểm chấm rõ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu giới hạn của OFFSET pagination và cách thiết kế keyset pagination đúng.
- Ý bắt buộc: OFFSET vẫn phải đọc rồi bỏ các dòng phía trước, trang càng sâu càng chậm; OFFSET đếm theo vị trí nên dữ liệu chèn/xóa làm lặp hoặc mất bản ghi; created_at không duy nhất, cần thêm id làm tie-breaker; Keyset: WHERE (created_at, id) < (:lastCreatedAt, :lastId) ORDER BY created_at DESC, id DESC LIMIT 20; Index (account_id, created_at, id); trade-off: không nhảy tới trang tùy ý
- Dấu hiệu trả lời sai: Chỉ dùng WHERE created_at < :last mà không có tie-breaker; Index (created_at) mà quên account_id đứng đầu; Cho rằng tăng LIMIT hoặc cache sẽ giải quyết trang sâu
- Câu hỏi nối tiếp: Màn hình cần nút 'trang trước'; bạn viết query thế nào với cùng index?

### de-qa-1110 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Spring @Transactional (`java.spring.transaction`) · ~790 token · hard của topic: 2 · golden: g07

**Câu hỏi:** Trong OrderService, placeOrder() có @Transactional; bên trong nó gọi this.writeAudit() được đánh dấu @Transactional(propagation = REQUIRES_NEW), và gọi paymentService.charge() (@Transactional mặc định) trong try/catch để "nuốt" lỗi thanh toán. Kết quả: audit bị rollback cùng đơn hàng, và lúc commit lại nhận UnexpectedRollbackException. Giải thích từng hiện tượng và cách sửa.

**Kết luận:** Giải thích đúng cả hai hiện tượng (self-invocation bỏ qua proxy; REQUIRED dùng chung transaction vật lý nên rollback-only dẫn tới UnexpectedRollbackException), khớp tài liệu Spring. Chỉ có vấn đề nhỏ về độ dài.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | Chunk ~790 token; điểm cắt 600 token rơi cuối cách sửa (c) của hiện tượng 2, mất phần 'Lưu ý thêm'. Hai hiện tượng và cách sửa nằm trước điểm cắt. | Bỏ hoặc rút phần 'Lưu ý thêm' còn một câu (rollback rule mặc định). |

**Kiểm chứng:**
- `supported` Ở proxy mode chỉ lời gọi từ ngoài qua proxy được chặn; self-invocation không có transaction
  > This means that self-invocation (in effect, a method within the target object calling another method of the target object) does not lead to an actual transaction at runtime even if the invoked method is marked with @Transactional.  
  > — https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/annotations.html
- `supported` Dùng AspectJ mode nếu cần self-invocation có transaction
  > Consider using AspectJ mode (see the mode attribute in the following table) if you expect self-invocations to be wrapped with transactions as well.  
  > — https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/annotations.html
- `supported` REQUIRED: mỗi method một logical scope nhưng chung physical transaction; rollback-only ở scope trong ảnh hưởng scope ngoài, dẫn tới UnexpectedRollbackException
  > So a rollback-only marker set in the inner transaction scope does affect the outer transaction’s chance to actually commit.  
  > — https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/tx-propagation.html
  _"A corresponding UnexpectedRollbackException is thrown at that point."_
- `supported` REQUIRES_NEW dùng transaction vật lý độc lập; NESTED dùng savepoint, chỉ với JDBC resource transaction
  > This setting is typically mapped onto JDBC savepoints, so it works only with JDBC resource transactions.  
  > — https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/tx-propagation.html
  _REQUIRES_NEW: "always uses an independent physical transaction for each affected transaction scope"_
- `supported` REQUIRES_NEW có thể làm cạn connection pool và deadlock; pool lớn hơn số thread đồng thời ít nhất 1
  > Do not use PROPAGATION_REQUIRES_NEW unless your connection pool is appropriately sized, exceeding the number of concurrent threads by at least 1.  
  > — https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/tx-propagation.html
- `supported` Mặc định chỉ RuntimeException và Error gây rollback; checked exception không
  > Checked exceptions that are thrown from a transactional method do not result in a rollback in the default configuration.  
  > — https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/rolling-back.html
- `supported` Từ Spring 6.0, method protected/package-private cũng được áp transaction với class-based proxy
  > As of 6.0, protected or package-visible methods can also be made transactional for class-based proxies by default.  
  > — https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/annotations.html
  _Trang không nói rõ private bị loại trừ; đó là suy ra._

**Độ khó:** hard thật · hợp level middle, senior — Debug hai hiện tượng cụ thể dựa trên cơ chế proxy và propagation, không chỉ định nghĩa.
**Dùng trong phỏng vấn:** ~5 phút, 2 ý hỏi, chấm được — Hai ý hỏi (giải thích, sửa) cho hai hiện tượng; 4–5 điểm chấm rõ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu @Transactional hoạt động qua proxy và cách propagation REQUIRED/REQUIRES_NEW chia sẻ transaction.
- Ý bắt buộc: this.writeAudit() là self-invocation, không qua proxy nên REQUIRES_NEW bị bỏ qua; Sửa: tách sang bean khác, TransactionTemplate, hoặc AspectJ mode; charge() REQUIRED dùng chung transaction vật lý; exception ném ra khỏi proxy đánh dấu rollback-only; placeOrder nuốt exception rồi commit nên Spring rollback và ném UnexpectedRollbackException; Sửa tùy nghiệp vụ: không nuốt lỗi, hoặc REQUIRES_NEW/NESTED cho charge, hoặc trả kết quả thay vì exception
- Dấu hiệu trả lời sai: Nói REQUIRES_NEW trên method cùng class vẫn có tác dụng; Đề xuất bắt exception kỹ hơn để tránh UnexpectedRollbackException mà không hiểu rollback-only; Cho rằng checked exception cũng rollback mặc định
- Câu hỏi nối tiếp: Nếu đổi charge() sang REQUIRES_NEW, khi tải cao có rủi ro gì với connection pool?

### de-qa-1111 · Cần sửa · tin cậy high · Chỉ hình thức

**Topic:** Spring @Transactional (`java.spring.transaction`) · ~746 token · hard của topic: 2 · golden: g05

**Câu hỏi:** Endpoint trừ tồn kho làm `Product p = repo.findById(id); p.setStock(p.getStock() - qty);` trong một @Transactional trên PostgreSQL. Khi flash sale, hệ thống bán vượt số lượng tồn. Phân tích lost update dưới isolation mặc định và so sánh các cách khắc phục: atomic update, pessimistic lock, optimistic lock, nâng isolation level.

**Kết luận:** Các fact đều đúng theo tài liệu PostgreSQL, Spring và Hibernate (Read Committed mặc định, UPDATE đánh giá lại WHERE, lỗi serialization phải retry, @Version, @Lock). Cần fix vì câu hỏi liệt kê 4 cách cần so sánh cộng phần phân tích, quá rộng theo rubric.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| major | interview_fit | Câu hỏi yêu cầu phân tích lost update và so sánh 4 cách (atomic update, pessimistic, optimistic, nâng isolation): tính theo rubric là 5 ý hỏi, quá nhiều cho 3–5 phút. | Bỏ danh sách 4 cách khỏi câu hỏi: 'Phân tích lost update và bạn chọn cách khắc phục nào cho flash sale, vì sao?'; các cách còn lại làm follow-up. |
| minor | length | Chunk ~746 token; điểm cắt 600 token rơi cuối cách 4, mất câu về isolation bị bỏ qua khi REQUIRED và đoạn 'Lựa chọn' (kết luận so sánh). | Rút mô tả từng cách còn 1–2 câu và đưa đoạn 'Lựa chọn' lên trước điểm cắt. |

**Kiểm chứng:**
- `supported` Read Committed là isolation mặc định của PostgreSQL
  > Read Committed is the default isolation level in PostgreSQL.  
  > — https://www.postgresql.org/docs/current/transaction-iso.html
- `supported` Ở Read Committed, UPDATE chờ transaction đang sửa dòng kết thúc rồi đánh giá lại WHERE trên phiên bản mới, nên atomic conditional update không bán vượt
  > The search condition of the command (the WHERE clause) is re-evaluated to see if the updated version of the row still matches the search condition.  
  > — https://www.postgresql.org/docs/current/transaction-iso.html
  _Câu trước: "the would-be updater will wait for the first updating transaction to commit or roll back (if it is still in progress)."_
- `supported` REPEATABLE READ/SERIALIZABLE làm transaction sau thất bại với lỗi serialization (40001), ứng dụng phải retry
  > Applications using this level must be prepared to retry transactions due to serialization failures.  
  > — https://www.postgresql.org/docs/current/transaction-iso.html
  _Repeatable Read: "ERROR: could not serialize access due to concurrent update"; Serializable: "which always return with an SQLSTATE value of '40001'"._
- `supported` Spring Data JPA dùng @Lock trên query method để chọn lock mode
  > To specify the lock mode to be used, you can use the @Lock annotation on query methods, as shown in the following example:  
  > — https://docs.spring.io/spring-data/jpa/reference/jpa/locking.html
  _Ví dụ trên trang dùng LockModeType.READ; PESSIMISTIC_WRITE là giá trị chuẩn của JPA, trang không nêu riêng._
- `supported` @Version: Hibernate tăng version mỗi lần cập nhật và phát hiện cập nhật xung đột, transaction thua bị rollback
  > Here, the version property is mapped to the version column, and the entity manager uses it to detect conflicting updates  
  > — https://raw.githubusercontent.com/hibernate/hibernate-orm/6.6/documentation/src/main/asciidoc/userguide/chapters/locking/Locking.adoc
  _"If the check reveals conflicting modifications, the committing transaction rolls back." Phù hợp tình huống "read-often-write-sometimes"._
- `supported` Isolation trong @Transactional bị âm thầm bỏ qua khi tham gia transaction ngoài (trừ khi validateExistingTransaction)
  > By default, a participating transaction joins the characteristics of the outer scope, silently ignoring the local isolation level, timeout value, or read-only flag (if any).  
  > — https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/tx-propagation.html

**Độ khó:** hard thật · hợp level middle, senior — Phải hiểu hành vi isolation thực tế của PostgreSQL và trade-off các cơ chế lock.
**Dùng trong phỏng vấn:** ~5 phút, 5 ý hỏi, chấm được — Điểm chấm rõ nhưng quá nhiều ý được liệt kê sẵn trong câu hỏi.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu lost update ở tầng ứng dụng và các cách chống bán vượt tồn kho.
- Ý bắt buộc: Read Committed mặc định; hai transaction đọc cùng giá trị rồi ghi đè nhau (lost update); @Transactional không chặn được read-modify-write ở Java; Atomic UPDATE ... SET stock = stock - :qty WHERE stock >= :qty và kiểm tra số dòng bị ảnh hưởng; Pessimistic lock (FOR UPDATE) cho xung đột cao, optimistic (@Version) cho xung đột thấp; Nâng isolation thì phải retry khi lỗi serialization
- Dấu hiệu trả lời sai: Nói @Transactional hay synchronized trong Java là đủ; Optimistic lock là lựa chọn tốt nhất cho flash sale; Nâng isolation mà không chuẩn bị retry
- Câu hỏi nối tiếp: Với atomic update, nếu cần ghi thêm bảng order_items trong cùng transaction thì có rủi ro gì?

**Đề xuất sửa:**
- Câu hỏi mới: Endpoint trừ tồn kho làm `Product p = repo.findById(id); p.setStock(p.getStock() - qty);` trong một @Transactional trên PostgreSQL. Khi flash sale, hệ thống bán vượt số lượng tồn. Vì sao, và bạn chọn cách khắc phục nào, vì sao?
- Đáp án: Giữ phần nguyên nhân; đặt atomic update làm đáp án chính; rút pessimistic/optimistic/isolation thành mỗi cách 1 câu trade-off; đưa đoạn 'Lựa chọn' lên trước.

### de-qa-1112 · Cần sửa · tin cậy low · Phải đọc

**Topic:** Spring Security, JWT và OAuth2 (`java.security.spring-security-jwt`) · ~733 token · hard của topic: 2 · golden: g22

**Câu hỏi:** Bạn thiết kế xác thực cho SPA và mobile app gọi Spring Boot API bằng JWT access token, với yêu cầu: logout hoặc khóa tài khoản phải có hiệu lực nhanh, token bị đánh cắp phải hạn chế được thiệt hại. Trình bày cách resource server validate JWT, vì sao JWT khó thu hồi, và thiết kế access/refresh token (thời hạn, rotation, lưu trữ) cùng trade-off.

**Kết luận:** Phần validate JWT khớp tài liệu Spring Security và yêu cầu RFC 9700 về refresh token cho public client có trích dẫn. Cần fix vì câu hỏi có 3 ý hỏi lớn; chi tiết reuse detection của rotation và phần lưu trữ trên trình duyệt chưa kiểm chứng được (không đọc được mục 4.14 của RFC 9700).

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| major | interview_fit | Câu hỏi có 3 ý hỏi lớn (cách validate JWT, vì sao khó thu hồi, thiết kế access/refresh gồm thời hạn, rotation, lưu trữ và trade-off), quá rộng cho 3–5 phút. | Hỏi 2 ý: 'Vì sao JWT khó thu hồi, và bạn thiết kế access/refresh token thế nào để logout/khóa tài khoản có hiệu lực nhanh?'; phần validate JWT thành follow-up. |
| major | factual | Hai ý thuộc thiết kế (reuse detection của rotation, lưu trữ trên trình duyệt) chưa kiểm chứng được bằng trích dẫn. | Người duyệt đối chiếu RFC 9700 §4.14 và OWASP; nếu đúng thì giữ nguyên, nên dẫn §4.14 trong grounding_urls kèm anchor. |
| minor | length | Chunk ~733 token; điểm cắt 600 token rơi đầu ý 5 (lưu trữ), mất phần lưu trữ và đoạn 'Trade-off cốt lõi' dù câu hỏi yêu cầu cả hai. | Rút đoạn 'Validate JWT' còn 2 câu để phần lưu trữ và trade-off nằm trước điểm cắt. |

**Kiểm chứng:**
- `supported` Resource server dùng issuer-uri để tìm public key (JWK Set) và validate chữ ký
  > Resource Server will use this property to further self-configure, discover the authorization server’s public keys, and subsequently validate incoming JWTs.  
  > — https://docs.spring.io/spring-security/reference/servlet/oauth2/resource-server/jwt.html
- `supported` Mặc định kiểm iss, exp, nbf với clock skew 60 giây
  > By default, Resource Server configures a clock skew of 60 seconds.  
  > — https://docs.spring.io/spring-security/reference/servlet/oauth2/resource-server/jwt.html
  _"Resource Server will default to verifying the iss claim as well as the exp and nbf timestamp claims."_
- `supported` Scope được map thành authority tiền tố SCOPE_, tùy biến bằng JwtAuthenticationConverter
  > Map each scope to an authority with the prefix SCOPE_.  
  > — https://docs.spring.io/spring-security/reference/servlet/oauth2/resource-server/jwt.html
  _"Spring Security ships with JwtAuthenticationConverter, which is responsible for converting a Jwt into an Authentication."_
- `supported` RFC 9700: refresh token của public client phải sender-constrained hoặc dùng rotation
  > Refresh tokens for public clients MUST be sender-constrained or use refresh token rotation as described in Section 4.14.  
  > — https://www.rfc-editor.org/rfc/rfc9700.html
- `unverified` Rotation: refresh token cũ bị dùng lại thì server thu hồi refresh token đang hoạt động của chuỗi
  _WebFetch không trả về nội dung mục 4.14 của RFC 9700 (thử 3 lần với offset khác nhau). Đúng theo hiểu biết chung nhưng chưa có câu trích._
- `unverified` localStorage dễ bị đọc khi có XSS; cookie HttpOnly/SameSite cần chống CSRF
  _Hết ngân sách fetch cho cặp này; nên kiểm bằng OWASP HTML5 Security / Session Management Cheat Sheet._

**Độ khó:** hard thật · hợp level middle, senior — Thiết kế có trade-off giữa stateless và thu hồi tức thì, cộng bảo mật lưu trữ.
**Dùng trong phỏng vấn:** ~6 phút, 3 ý hỏi, chấm được — Điểm chấm rõ nhưng 3 ý hỏi lớn.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu JWT được kiểm cục bộ nên khó thu hồi, và cách dùng access/refresh token để cân bằng.
- Ý bắt buộc: Resource server kiểm chữ ký bằng public key của issuer và kiểm exp/nbf/iss cục bộ; Vì kiểm cục bộ, token hợp lệ tới khi hết hạn dù đã logout; Access token ngắn hạn, scope/audience hẹp là cơ chế giới hạn thiệt hại chính; Refresh token lưu phía server để thu hồi được; public client dùng rotation hoặc sender-constrained; Thu hồi tức thì cần denylist hoặc introspection, đổi lại mất một phần stateless
- Dấu hiệu trả lời sai: Access token sống nhiều ngày cho tiện; Nghĩ logout phía client là đủ để vô hiệu token; Lưu refresh token trong localStorage mà không nhắc rủi ro XSS
- Câu hỏi nối tiếp: Admin khóa tài khoản lúc 10:00; access token 15 phút. Làm sao chặn ngay các request sau 10:00?

**Đề xuất sửa:**
- Câu hỏi mới: Bạn thiết kế xác thực cho SPA và mobile app gọi Spring Boot API bằng JWT access token, với yêu cầu: logout hoặc khóa tài khoản phải có hiệu lực nhanh, token bị đánh cắp phải hạn chế được thiệt hại. Vì sao JWT khó thu hồi, và bạn thiết kế access/refresh token thế nào?
- Đáp án: Rút phần validate JWT còn 1–2 câu làm nền; giữ ý 1–4; rút ý lưu trữ còn 1 câu và đưa 'Trade-off cốt lõi' lên trước điểm cắt.

### de-qa-1113 · Cần sửa · tin cậy high · Chỉ hình thức

**Topic:** Spring Security, JWT và OAuth2 (`java.security.spring-security-jwt`) · ~802 token · hard của topic: 2

**Câu hỏi:** Một ứng dụng Spring Boot vừa có trang admin đăng nhập bằng form (session cookie) vừa có REST API /api/** dùng JWT bearer token. Sau khi thêm cấu hình, API trả 401/403 bất ngờ và có người đề xuất tắt CSRF toàn cục. Giải thích request đi qua DelegatingFilterProxy, FilterChainProxy và SecurityFilterChain thế nào, cách tách hai chain, và khi nào tắt CSRF là an toàn.

**Kết luận:** Nội dung đúng theo tài liệu Spring Security (DelegatingFilterProxy, FilterChainProxy, chain đầu tiên khớp, ExceptionTranslationFilter, khuyến nghị CSRF). Cần fix vì có 3 ý hỏi và toàn bộ phần 'khi nào tắt CSRF an toàn' nằm sau điểm cắt 600 token.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| major | interview_fit | Câu hỏi có 3 ý hỏi (luồng qua DelegatingFilterProxy/FilterChainProxy/SecurityFilterChain, cách tách hai chain, khi nào tắt CSRF an toàn), quá rộng cho 3–5 phút. | Hỏi 2 ý: 'Vì sao API trả 401/403 và bạn tách hai chain thế nào? Có nên tắt CSRF toàn cục không?'; phần luồng DelegatingFilterProxy làm follow-up. |
| major | length | Chunk ~802 token; điểm cắt 600 token rơi đúng đầu đoạn 'Khi nào tắt CSRF an toàn', nên snippet mất hẳn một ý được hỏi trực tiếp. | Rút đoạn luồng request và thứ tự filter còn 2–3 câu, đưa kết luận CSRF (chỉ tắt trên chain API dùng bearer header) lên trước. |

**Kiểm chứng:**
- `supported` Servlet container không biết bean Spring; DelegatingFilterProxy ủy quyền cho bean Filter, lookup lazy
  > You can register DelegatingFilterProxy through the standard Servlet container mechanisms but delegate all the work to a Spring Bean that implements Filter.  
  > — https://docs.spring.io/spring-security/reference/servlet/architecture.html
  _"Another benefit of DelegatingFilterProxy is that it allows delaying looking up Filter bean instances."_
- `supported` FilterChainProxy ủy quyền qua SecurityFilterChain, xóa SecurityContext tránh leak, áp HttpFirewall
  > For example, it clears out the SecurityContext to avoid memory leaks.  
  > — https://docs.spring.io/spring-security/reference/servlet/architecture.html
  _"It also applies Spring Security's HttpFirewall to protect applications against certain types of attacks."_
- `supported` Chỉ SecurityFilterChain đầu tiên khớp được gọi
  > Only the first SecurityFilterChain that matches is invoked.  
  > — https://docs.spring.io/spring-security/reference/servlet/architecture.html
- `supported` ExceptionTranslationFilter: AuthenticationException tới AuthenticationEntryPoint (redirect login hoặc WWW-Authenticate), AccessDeniedException tới AccessDeniedHandler
  > The AuthenticationEntryPoint is used to request credentials from the client. For example, it might redirect to a log in page or send a WWW-Authenticate header.  
  > — https://docs.spring.io/spring-security/reference/servlet/architecture.html
  _"Otherwise, if it is an AccessDeniedException, then Access Denied. The AccessDeniedHandler is invoked to handle access denied."_
- `supported` Bật logging org.springframework.security=TRACE để chẩn đoán 401/403
  > If you come across a 401 or 403 error, it is very likely that you will find a log message that will help you understand what is going on.  
  > — https://docs.spring.io/spring-security/reference/servlet/architecture.html
- `supported` Spring khuyến nghị bật CSRF cho mọi request trình duyệt có thể xử lý; chỉ tắt khi chỉ phục vụ client không phải trình duyệt
  > Our recommendation is to use CSRF protection for any request that could be processed by a browser by normal users. If you are creating a service that is used only by non-browser clients, you likely want to disable CSRF protection.  
  > — https://docs.spring.io/spring-security/reference/features/exploits/csrf.html
- `supported` Stateless không đồng nghĩa an toàn: credential trong cookie hoặc basic auth vẫn bị CSRF; method an toàn phải chỉ đọc
  > What if my application is stateless? That does not necessarily mean you are protected.  
  > — https://docs.spring.io/spring-security/reference/features/exploits/csrf.html
  _"Applications that use basic authentication are also vulnerable to CSRF attacks." Trang không nhắc JWT theo tên; ví dụ là cookie tự chứa toàn bộ trạng thái xác thực._

**Độ khó:** hard thật · hợp level middle, senior — Debug cấu hình nhiều chain và lý luận CSRF theo cách trình duyệt gửi credential.
**Dùng trong phỏng vấn:** ~6 phút, 3 ý hỏi, chấm được — Điểm chấm rõ nhưng 3 ý hỏi.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu cách Spring Security chọn filter chain và vì sao CSRF phụ thuộc vào việc trình duyệt tự gửi credential.
- Ý bắt buộc: DelegatingFilterProxy nối servlet container với bean FilterChainProxy; Chỉ SecurityFilterChain đầu tiên khớp được chạy, nên thứ tự @Order quan trọng; Chain API: securityMatcher("/api/**"), order nhỏ hơn, JWT resource server, STATELESS, tắt CSRF chỉ ở đây; Chain web: formLogin, session, giữ CSRF; Chỉ tắt CSRF khi credential nằm trong header do code tự gắn, không phải cookie
- Dấu hiệu trả lời sai: Tắt CSRF toàn cục vì 'API stateless'; Đặt chain web không securityMatcher trước chain API; Nhầm 401 (chưa xác thực) với 403 (thiếu quyền)
- Câu hỏi nối tiếp: Nếu SPA lưu JWT trong cookie HttpOnly thay vì header thì chain API cần thay đổi gì?

**Đề xuất sửa:**
- Câu hỏi mới: Một ứng dụng Spring Boot vừa có trang admin đăng nhập bằng form (session cookie) vừa có REST API /api/** dùng JWT bearer token. Sau khi thêm cấu hình, API trả 401/403 bất ngờ và có người đề xuất tắt CSRF toàn cục. Vì sao lỗi, bạn tách cấu hình thế nào, và có nên tắt CSRF toàn cục không?
- Đáp án: Rút đoạn luồng request và thứ tự filter còn 2–3 câu; giữ phần tách hai chain; đưa phần CSRF (rút còn 3 câu) lên trước điểm cắt.

### de-qa-1114 · Cần sửa · tin cậy high · Chỉ hình thức

**Topic:** Spring Boot auto-configuration và profile (`java.spring.boot-autoconfig`) · ~837 token · hard của topic: 2

**Câu hỏi:** Bạn viết starter nội bộ acme-spring-boot-starter tự cấu hình một AcmeClient. Vài service báo bean AcmeClient tự khai báo của họ bị trùng hoặc bị bỏ qua, service khác lỗi khởi động vì không có thư viện Acme trên classpath. Giải thích cơ chế auto-configuration (cách Boot tìm, đánh giá điều kiện, thứ tự), cách viết đúng và cách debug.

**Kết luận:** Mọi fact về auto-configuration đều khớp tài liệu Spring Boot (file imports, không component scan, điều kiện bean, ordering, đặt tên starter). Cần fix vì câu hỏi có 3 ý hỏi lớn và phần debug (được hỏi trực tiếp) nằm sau điểm cắt 600 token.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| major | interview_fit | Câu hỏi có 3 ý hỏi lớn (cơ chế gồm tìm, điều kiện, thứ tự; cách viết đúng; cách debug), quá rộng cho 3–5 phút. | Hỏi 2 ý: 'Vì sao các lỗi này xảy ra và bạn sửa starter thế nào?'; cách debug làm follow-up. |
| major | length | Chunk ~837 token; điểm cắt 600 token rơi ở ý 4 (ordering), mất phần thiết kế starter và toàn bộ phần debug được hỏi trực tiếp. | Rút ý 3–4 còn một câu, bỏ phần đặt tên module; giữ 1 câu debug (--debug conditions report, ApplicationContextRunner) trước điểm cắt. |

**Kiểm chứng:**
- `supported` Boot đọc file META-INF/spring/...AutoConfiguration.imports, mỗi dòng một class
  > Spring Boot checks for the presence of a META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports file within your published jar.  
  > — https://docs.spring.io/spring-boot/reference/features/developing-auto-configuration.html
- `supported` Auto-configuration chỉ nạp qua file imports, package riêng, không bị component scan, không tự bật component scan
  > Auto-configurations must be loaded only by being named in the imports file. Make sure that they are defined in a specific package space and that they are never the target of component scanning.  
  > — https://docs.spring.io/spring-boot/reference/features/developing-auto-configuration.html
- `supported` @ConditionalOnBean/OnMissingBean đánh giá theo những gì đã xử lý; chỉ dùng trên auto-configuration (được nạp sau bean người dùng)
  > we recommend using only @ConditionalOnBean and @ConditionalOnMissingBean annotations on auto-configuration classes (since these are guaranteed to load after any user-defined bean definitions have been added).  
  > — https://docs.spring.io/spring-boot/reference/features/developing-auto-configuration.html
  _"these conditions are evaluated based on what has been processed so far."_
- `supported` Kiểu trả về @Bean nên cụ thể nhất có thể; gom @Bean phụ thuộc thư viện vào nested @Configuration có @ConditionalOnClass
  > When declaring a @Bean method, provide as much type information as possible in the method’s return type.  
  > — https://docs.spring.io/spring-boot/reference/features/developing-auto-configuration.html
  _Trang có ví dụ nested @Configuration với @ConditionalOnClass(SomeService.class)._
- `supported` Thứ tự before/after chỉ ảnh hưởng thứ tự định nghĩa bean, không phải thứ tự tạo bean
  > the order in which auto-configuration classes are applied only affects the order in which their beans are defined.  
  > — https://docs.spring.io/spring-boot/reference/features/developing-auto-configuration.html
- `supported` Tên module không bắt đầu bằng spring-boot; không dùng namespace server, management, spring
  > Do not start your module names with spring-boot, even if you use a different Maven groupId.  
  > — https://docs.spring.io/spring-boot/reference/features/developing-auto-configuration.html
  _"do not include your keys in the namespaces that Spring Boot uses (such as server, management, spring, and so on)."_
- `supported` --debug in conditions report; exclude bằng @SpringBootApplication(exclude) hoặc spring.autoconfigure.exclude
  > Doing so enables debug logs for a selection of core loggers and logs a conditions report to the console.  
  > — https://docs.spring.io/spring-boot/reference/using/auto-configuration.html
  _"you can also control the list of auto-configuration classes to exclude by using the spring.autoconfigure.exclude property."_

**Độ khó:** hard thật · hợp level middle, senior — Phải hiểu thứ tự đánh giá điều kiện và vì sao component scan làm hỏng auto-configuration.
**Dùng trong phỏng vấn:** ~6 phút, 3 ý hỏi, chấm được — Điểm chấm rõ nhưng 3 ý hỏi lớn.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu cách Spring Boot nạp và đánh giá auto-configuration, đủ để viết starter không đè bean của người dùng.
- Ý bắt buộc: Auto-configuration được liệt kê trong file AutoConfiguration.imports và chạy sau bean người dùng; Bean bị trùng/bỏ qua do thiếu @ConditionalOnMissingBean hoặc class bị component scan quét trúng; Lỗi thiếu thư viện: dùng @ConditionalOnClass, gom @Bean vào nested @Configuration; @ConditionalOnBean/OnMissingBean chỉ dùng trên auto-configuration, kiểu trả về cụ thể; Debug bằng --debug (conditions report), test bằng ApplicationContextRunner
- Dấu hiệu trả lời sai: Đặt auto-configuration dưới package gốc của ứng dụng cho tiện; Dùng @ConditionalOnMissingBean trong @Configuration thường của người dùng; Nghĩ @AutoConfigureAfter quyết định thứ tự tạo bean
- Câu hỏi nối tiếp: Viết test nào để chứng minh AcmeClient của người dùng thắng bean mặc định của starter?

**Đề xuất sửa:**
- Câu hỏi mới: Bạn viết starter nội bộ acme-spring-boot-starter tự cấu hình một AcmeClient. Vài service báo bean AcmeClient tự khai báo của họ bị trùng hoặc bị bỏ qua, service khác lỗi khởi động vì không có thư viện Acme trên classpath. Vì sao, và bạn sửa starter thế nào?
- Đáp án: Giữ phần cơ chế (rút gọn) và nguyên nhân 1–2; gộp ý 3–4 thành một câu; rút phần thiết kế starter và debug còn 2 câu, đặt trước điểm cắt.

### de-qa-1115 · Cần sửa · tin cậy high · Chỉ hình thức

**Topic:** Spring Boot auto-configuration và profile (`java.spring.boot-autoconfig`) · ~819 token · hard của topic: 2

**Câu hỏi:** Sau khi deploy lên Kubernetes, service vẫn kết nối DB staging dù image có application-prod.yml và pod đặt SPRING_PROFILES_ACTIVE=prod. Trình bày thứ tự ưu tiên của externalized configuration và profile trong Spring Boot, các nguyên nhân khả dĩ, cách chẩn đoán, và cách tổ chức config cùng secret cho hợp lý.

**Kết luận:** Thứ tự ưu tiên property source, thứ tự config data, quy tắc profile đều khớp tài liệu Spring Boot. Cần fix vì câu hỏi có 4 ý hỏi và phần chẩn đoán/tổ chức config, secret nằm sau điểm cắt 600 token.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| major | interview_fit | Câu hỏi có 4 ý hỏi (thứ tự ưu tiên, nguyên nhân, chẩn đoán, tổ chức config/secret), quá rộng cho 3–5 phút. | Hỏi 2 ý: 'Nguyên nhân khả dĩ là gì và bạn chẩn đoán thế nào?'; thứ tự ưu tiên là kiến thức nền trong đáp án, phần tổ chức config/secret làm follow-up. |
| major | length | Chunk ~819 token; điểm cắt 600 token rơi giữa phần chẩn đoán, mất cách dùng Actuator env và toàn bộ phần tổ chức config/secret được hỏi trực tiếp. | Rút đoạn thứ tự ưu tiên còn các mục liên quan (config data < env var < command line) và nguyên nhân 4–5 còn một câu, để phần chẩn đoán nằm trước điểm cắt. |
| minor | factual | Ý relaxed binding (SPRING_DATASOURCE_URL ứng với spring.datasource.url) và endpoint env của Actuator chưa có câu trích trong lần duyệt (trang external-config bị cắt trước mục relaxed binding). | Giữ nguyên; người duyệt có thể đối chiếu mục 'Binding From Environment Variables'. |

**Kiểm chứng:**
- `supported` Thứ tự ưu tiên: default < @PropertySource < config data < OS env < system properties < SPRING_APPLICATION_JSON < command line < test properties
  > Config data (such as application.properties files).  
  > — https://docs.spring.io/spring-boot/reference/features/external-config.html
  _Danh sách 15 mục trên trang: mục 3 là config data, mục 5 "OS environment variables.", mục 11 "Command line arguments." Nguồn sau ghi đè nguồn trước._
- `supported` Config data: application.* trong jar < application-{profile}.* trong jar < application.* ngoài jar < application-{profile}.* ngoài jar
  > Profile-specific application properties outside of your packaged jar (application-{profile}.properties and YAML variants).  
  > — https://docs.spring.io/spring-boot/reference/features/external-config.html
  _Đây là mục 4 (cao nhất) của danh sách thứ tự config data._
- `supported` spring.profiles.active theo cùng thứ tự, nguồn cao nhất thắng và thay thế; spring.profiles.include để cộng thêm
  > This means that you can specify active profiles in application.properties and then replace them by using the command line switch.  
  > — https://docs.spring.io/spring-boot/reference/features/profiles.html
  _"The spring.profiles.include property can be used to add active profiles on top of those activated by the spring.profiles.active property."_
- `supported` spring.profiles.active không hợp lệ trong file theo profile hoặc document on-profile
  > This means they cannot be included in profile specific files or documents activated by spring.config.activate.on-profile.  
  > — https://docs.spring.io/spring-boot/reference/features/profiles.html
- `supported` @PropertySource được nạp lúc context refresh, quá muộn cho logging.* và spring.main.*
  > This is too late to configure certain properties such as logging.* and spring.main.* which are read before refresh begins.  
  > — https://docs.spring.io/spring-boot/reference/features/external-config.html
- `supported` configtree: đọc Secret mount thành file; profile group (production gồm proddb, prodmq)
  > you need to use the configtree: prefix so that Spring Boot knows it needs to expose all the files as properties.  
  > — https://docs.spring.io/spring-boot/reference/features/external-config.html
  _Profile group: "we can create a production group that consists of our proddb and prodmq profiles." (profiles.html)_

**Độ khó:** hard thật · hợp level middle, senior — Debug cấu hình thật trên Kubernetes dựa trên thứ tự ưu tiên, không chỉ nhớ danh sách.
**Dùng trong phỏng vấn:** ~6 phút, 4 ý hỏi, chấm được — Điểm chấm rõ nhưng 4 ý hỏi.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu thứ tự ưu tiên externalized configuration để tìm vì sao giá trị trong application-prod.yml bị ghi đè.
- Ý bắt buộc: Biến môi trường và command line thắng mọi file application*.yml, kể cả file theo profile; File ngoài jar thắng file cùng loại trong jar; Nguyên nhân hay gặp: env var SPRING_DATASOURCE_URL còn sót, ConfigMap mount application.yml, entrypoint đặt lại profile; spring.profiles.active nguồn cao nhất thay thế chứ không cộng; không dùng trong file theo profile; Chẩn đoán: log profile active, Actuator env để xem property lấy từ nguồn nào
- Dấu hiệu trả lời sai: Nghĩ file application-prod.yml luôn thắng vì profile prod đang active; Đóng gói secret production vào jar; Mở Actuator env công khai không che giá trị
- Câu hỏi nối tiếp: Bạn tổ chức secret DB cho prod thế nào để không nằm trong image và vẫn đổi được không cần build lại?

**Đề xuất sửa:**
- Câu hỏi mới: Sau khi deploy lên Kubernetes, service vẫn kết nối DB staging dù image có application-prod.yml và pod đặt SPRING_PROFILES_ACTIVE=prod. Nguyên nhân khả dĩ là gì, và bạn chẩn đoán thế nào?
- Đáp án: Rút thứ tự ưu tiên còn các nguồn liên quan; giữ nguyên nhân 1–3, gộp 4–5; giữ phần chẩn đoán; chuyển phần 'Tổ chức' sang follow-up hoặc rút còn 1 câu.

### de-qa-1116 · Cần sửa · tin cậy high · Chỉ hình thức

**Topic:** Spring IoC và Dependency Injection (`java.spring.ioc-di`) · ~743 token · hard của topic: 2

**Câu hỏi:** Sau khi nâng Spring Boot từ 2.5 lên bản mới, ứng dụng không khởi động được vì BeanCurrentlyInCreationException giữa OrderService và PaymentService (inject chéo bằng field @Autowired). Vì sao trước đây vẫn chạy, vì sao constructor injection không tự giải được vòng phụ thuộc, và bạn xử lý thế nào từ tạm thời tới đúng về thiết kế?

**Kết luận:** Đúng theo tài liệu Spring Framework và release notes Boot 2.6 (circular reference bị cấm mặc định, constructor injection không phá được vòng, cờ allow-circular-references). Cần fix vì câu hỏi có 3 ý hỏi, vượt mức 2 của rubric.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| major | interview_fit | Câu hỏi có 3 ý hỏi (vì sao trước chạy được, vì sao constructor injection không giải, xử lý từ tạm thời tới đúng thiết kế). | Gộp thành 2 ý: 'Vì sao bản nâng cấp làm lộ lỗi này, và bạn xử lý thế nào từ tạm thời tới đúng thiết kế?'; ý constructor injection làm follow-up. |
| minor | length | Chunk ~743 token; điểm cắt 600 token rơi ở cách sửa 3(b), mất (c) và đoạn khuyến nghị constructor injection. Ý bắt buộc (Boot 2.6 cấm vòng, cờ tạm thời, tách service thứ ba) nằm trước điểm cắt. | Rút đoạn 'Rủi ro của việc phá vòng' còn một câu. |
| minor | factual | Ý @Lazy/ObjectProvider che vòng phụ thuộc và rủi ro B giữ bản thô thay vì proxy chưa được kiểm chứng bằng trích dẫn trong lần duyệt; đúng theo hiểu biết chung, không phải điểm chấm chính. | Giữ là điểm cộng. |

**Kiểm chứng:**
- `supported` Từ Spring Boot 2.6, circular reference bị cấm mặc định
  > Circular references between beans are now prohibited by default.  
  > — https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-2.6-Release-Notes
- `supported` spring.main.allow-circular-references=true khôi phục hành vi 2.5, chỉ là giải pháp cuối
  > circular references can be allowed again by setting spring.main.allow-circular-references to true  
  > — https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-2.6-Release-Notes
  _Release notes: "you are strongly encouraged to update your configuration to break the dependency cycle."_
- `supported` Constructor injection hai chiều tạo vòng không giải được, container ném BeanCurrentlyInCreationException
  > the Spring IoC container detects this circular reference at runtime, and throws a BeanCurrentlyInCreationException.  
  > — https://docs.spring.io/spring-framework/reference/core/beans/dependencies/factory-collaborators.html
- `supported` Setter/field injection phá vòng bằng cách inject một bean chưa khởi tạo xong (con gà quả trứng)
  > a circular dependency between bean A and bean B forces one of the beans to be injected into the other prior to being fully initialized itself (a classic chicken-and-egg scenario).  
  > — https://docs.spring.io/spring-framework/reference/core/beans/dependencies/factory-collaborators.html
- `supported` Spring khuyến nghị constructor injection: immutable, dependency không null, bean trả về đã khởi tạo đầy đủ
  > The Spring team generally advocates constructor injection, as it lets you implement application components as immutable objects and ensures that required dependencies are not null.  
  > — https://docs.spring.io/spring-framework/reference/core/beans/dependencies/factory-collaborators.html
  _"a large number of constructor arguments is a bad code smell, implying that the class likely has too many responsibilities"_

**Độ khó:** hard thật · hợp level middle, senior — Phải hiểu cơ chế early reference của container và lý do thiết kế; topic chỉ tới middle nhưng có middle nên vẫn hợp lệ.
**Dùng trong phỏng vấn:** ~5 phút, 3 ý hỏi, chấm được — Điểm chấm rõ nhưng 3 ý hỏi.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu vòng phụ thuộc giữa bean và vì sao Spring Boot 2.6 bắt đầu chặn nó.
- Ý bắt buộc: Field/setter injection cho phép container inject một bean chưa khởi tạo xong để phá vòng; Từ Boot 2.6 circular reference bị cấm mặc định nên lỗi lộ ra khi nâng cấp; Constructor injection không có tham chiếu sớm nên container ném BeanCurrentlyInCreationException; Tạm thời: allow-circular-references=true hoặc @Lazy, kèm kế hoạch sửa; Đúng thiết kế: tách service thứ ba, dùng event, hoặc gộp class
- Dấu hiệu trả lời sai: Coi allow-circular-references=true là cách sửa lâu dài; Chuyển hết sang field injection để 'hết lỗi'; Không nhận ra vòng phụ thuộc là lỗi thiết kế
- Câu hỏi nối tiếp: Nếu dùng event để đảo chiều, PaymentService xử lý lỗi thanh toán thế nào khi OrderService đã commit?

**Đề xuất sửa:**
- Câu hỏi mới: Sau khi nâng Spring Boot từ 2.5 lên bản mới, ứng dụng không khởi động được vì BeanCurrentlyInCreationException giữa OrderService và PaymentService (inject chéo bằng field @Autowired). Vì sao bản nâng cấp làm lộ lỗi này, và bạn xử lý thế nào từ tạm thời tới đúng về thiết kế?
- Đáp án: Giữ đáp án, gộp đoạn 'Vì sao constructor injection không giải được' vào phần cách xử lý thành 1–2 câu; rút đoạn 'Rủi ro' còn một câu.

### de-qa-1117 · Đạt · tin cậy high · Có thể chấp nhận

**Topic:** Spring IoC và Dependency Injection (`java.spring.ioc-di`) · ~793 token · hard của topic: 2

**Câu hỏi:** Một singleton ReportService inject bean prototype ReportBuilder (giữ state theo từng lần build) và bean request-scope CurrentTenant. Trên production, dữ liệu báo cáo giữa các request bị trộn lẫn, còn job @Scheduled gọi ReportService thì lỗi vì không có request đang hoạt động. Giải thích nguyên nhân theo bean scope và các cách khắc phục.

**Kết luận:** Giải thích đúng cả hai lỗi theo tài liệu Spring (prototype chỉ được inject một lần vào singleton; request scope cần scoped proxy và thread phải gắn request). Các cách sửa ObjectProvider, @Lookup, truyền tham số đều có trích dẫn. Chỉ có vấn đề nhỏ về độ dài và một chi tiết CGLIB.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| minor | length | Chunk ~793 token; điểm cắt 600 token rơi ở cách sửa thứ nhất của lỗi 2, mất cách sửa sao chép context và đoạn 'Nguyên tắc chung'. Hai nguyên nhân và cách sửa lỗi 1 nằm trước điểm cắt; cách sửa lỗi 2 chỉ còn một phần. | Rút phần @Lookup còn một câu và bỏ ý 'new trong method' để cách sửa lỗi 2 nằm trước điểm cắt. |
| minor | factual | Trang Spring chỉ khẳng định @SessionScope mặc định TARGET_CLASS; với @RequestScope chưa có câu trích trong lần duyệt (thực tế cũng TARGET_CLASS). | Viết '@RequestScope/@SessionScope dùng proxy CGLIB (TARGET_CLASS) mặc định' là chấp nhận được; không biến thành điểm chấm. |

**Kiểm chứng:**
- `supported` Prototype inject vào singleton chỉ được tạo một lần, là instance duy nhất singleton nhận
  > The prototype instance is the sole instance that is ever supplied to the singleton-scoped bean.  
  > — https://docs.spring.io/spring-framework/reference/core/beans/factory-scopes.html
- `supported` Inject ObjectFactory/ObjectProvider và gọi getObject() mỗi lần cần
  > allowing for a getObject() call to retrieve the current instance on demand every time it is needed — without holding on to the instance or storing it separately.  
  > — https://docs.spring.io/spring-framework/reference/core/beans/factory-scopes.html
- `supported` @Lookup: Spring sinh subclass CGLIB; class/method không final; không dùng được với @Bean factory method
  > A further key limitation is that lookup methods do not work with factory methods and in particular not with @Bean methods in configuration classes  
  > — https://docs.spring.io/spring-framework/reference/core/beans/dependencies/factory-method-injection.html
  _"the class that the Spring bean container subclasses cannot be final, and the method to be overridden cannot be final, either."_
- `supported` Spring không gọi destroy callback cho prototype; client tự giải phóng
  > in the case of prototypes, configured destruction lifecycle callbacks are not called.  
  > — https://docs.spring.io/spring-framework/reference/core/beans/factory-scopes.html
- `supported` Scoped proxy có cùng public interface, lấy target thật từ scope hiện tại rồi ủy quyền
  > you need to inject a proxy object that exposes the same public interface as the scoped object but that can also retrieve the real target object from the relevant scope (such as an HTTP request) and delegate method calls onto the real object.  
  > — https://docs.spring.io/spring-framework/reference/core/beans/factory-scopes.html
  _CGLIB: "CGLIB proxies do not intercept private methods." @SessionScope: "Defaults to {@link ScopedProxyMode#TARGET_CLASS}."_
- `supported` Thread không gắn request (job @Scheduled) thì proxy không lấy được target và ném exception
  > IllegalStateException - if no RequestAttributes object is bound to the current thread  
  > — https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/web/context/request/RequestContextHolder.html
  _Lớp này "expose the web request in the form of a thread-bound RequestAttributes object"; request scope dựa vào nó._

**Độ khó:** hard thật · hợp level middle, senior — Nối triệu chứng production với vòng đời và scope của bean; topic chỉ tới middle nhưng hợp lệ.
**Dùng trong phỏng vấn:** ~4 phút, 2 ý hỏi, chấm được — Hai ý hỏi (nguyên nhân, cách sửa) cho hai lỗi, điểm chấm rõ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu bean scope và chuyện gì xảy ra khi bean scope ngắn được inject vào singleton.
- Ý bắt buộc: Prototype inject vào singleton chỉ tạo một lần, nên mọi request dùng chung builder có state; Sửa: ObjectProvider.getObject() mỗi lần, @Lookup, hoặc new trực tiếp; Request scope trong singleton cần scoped proxy lấy target theo request của thread hiện tại; Job @Scheduled không có request gắn thread nên proxy ném exception; Sửa: truyền tenantId tường minh hoặc nguồn tenant riêng cho job
- Dấu hiệu trả lời sai: Đổi ReportService thành prototype để hết trộn dữ liệu; Nghĩ prototype tự tạo mới mỗi lần gọi method; Truyền chính proxy request-scope sang thread @Async
- Câu hỏi nối tiếp: Nếu ReportBuilder giữ connection hay file handle, ai đóng nó khi dùng prototype?

### de-qa-1118 · Cần sửa · tin cậy high · Chỉ hình thức

**Topic:** Unit test với JUnit và Mockito (`java.testing.junit-mockito`) · ~818 token · hard của topic: 2

**Câu hỏi:** Bộ test Spring Boot của team chạy 25 phút; log cho thấy ApplicationContext bị khởi tạo lại hàng chục lần. Các test class dùng @SpringBootTest với tổ hợp @MockitoBean khác nhau, vài class có @DirtiesContext, còn test repository chạy trên H2. Giải thích cơ chế context caching của Spring TestContext, nguyên nhân chậm, và cách tổ chức lại test (test slice, Testcontainers) cùng trade-off.

**Kết luận:** Cơ chế context caching, cache key, @DirtiesContext, slice test, cảnh báo Testcontainers đều khớp tài liệu Spring. Cần fix vì có 3 ý hỏi và phần Testcontainers (được hỏi trực tiếp) nằm sau điểm cắt 600 token.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| major | interview_fit | Câu hỏi có 3 ý hỏi (cơ chế caching, nguyên nhân chậm, tổ chức lại gồm slice, Testcontainers, trade-off), quá rộng cho 3–5 phút. | Hỏi 2 ý: 'Vì sao context bị dựng lại nhiều lần, và bạn tổ chức lại bộ test thế nào?'; phần H2 vs Testcontainers làm follow-up. |
| major | length | Chunk ~818 token; điểm cắt 600 token rơi đúng đầu ý 'Database thật thay H2', mất toàn bộ phần Testcontainers mà câu hỏi nêu tên, cùng trade-off. | Rút đoạn cơ chế còn 2 câu (cache key gồm bean override; tối đa 32, LRU) và đưa ý H2 → Testcontainers lên trước. |
| minor | factual | Ý @DataJpaTest mặc định transactional và rollback chưa có câu trích (trang bị cắt trước mục đó); đúng theo hiểu biết chung. | Giữ nguyên. |
| minor | outdated | @MockitoBean/@MockitoSpyBean có từ Spring Framework 6.2 (Boot 3.4) thay cho @MockBean cũ; đáp án không nêu version, codebase cũ vẫn dùng @MockBean với cùng vấn đề cache key. | Thêm '(Boot 3.4+, trước đó là @MockBean)'. |

**Kiểm chứng:**
- `supported` Cache key gồm classes/locations, initializers, context customizers (@DynamicPropertySource, @MockitoBean, @MockitoSpyBean), profiles, @TestPropertySource
  > contextCustomizers (from ContextCustomizerFactory) – this includes @DynamicPropertySource methods, bean overrides (such as @TestBean, @MockitoBean, @MockitoSpyBean etc.), as well as various features from Spring Boot's testing support.  
  > — https://docs.spring.io/spring-framework/reference/testing/testcontext-framework/ctx-management/caching.html
- `supported` Cache là static; test chạy ở process riêng (fork từng class) làm mất tác dụng cache
  > if tests run in separate processes, the static cache is cleared between each test execution, which effectively disables the caching mechanism.  
  > — https://docs.spring.io/spring-framework/reference/testing/testcontext-framework/ctx-management/caching.html
- `supported` Mặc định tối đa 32 context, loại theo LRU
  > The size of the context cache is bounded with a default maximum size of 32. Whenever the maximum size is reached, a least recently used (LRU) eviction policy is used to evict and close stale contexts.  
  > — https://docs.spring.io/spring-framework/reference/testing/testcontext-framework/ctx-management/caching.html
- `supported` @DirtiesContext xóa context khỏi cache, test sau phải dựng lại; log DEBUG org.springframework.test.context.cache để xem thống kê
  > This instructs Spring to remove the context from the cache and rebuild the application context before running the next test that requires the same application context.  
  > — https://docs.spring.io/spring-framework/reference/testing/testcontext-framework/ctx-management/caching.html
  _"you can set the log level for the org.springframework.test.context.cache logging category to DEBUG."_
- `supported` @WebMvcTest chỉ nạp hạ tầng MVC và bean web, không quét @Component thường
  > Regular @Component and @ConfigurationProperties beans are not scanned when the @WebMvcTest annotation is used.  
  > — https://docs.spring.io/spring-boot/reference/testing/spring-boot-applications.html
- `supported` RANDOM_PORT: client và server ở transaction khác nhau nên @Transactional trên test không rollback dữ liệu server
  > the HTTP client and server run in separate threads and, thus, in separate transactions. Any transaction initiated on the server does not roll back in this case.  
  > — https://docs.spring.io/spring-boot/reference/testing/spring-boot-applications.html
- `supported` Container static của JUnit extension bị dừng sau test class trong khi context cache còn dùng lại; nên quản lý container như Spring bean. @ServiceConnection ghi đè property kết nối
  > For this reason, you should prefer managing containers as Spring beans or importing container declarations when the application context should remain usable for as long as it is cached.  
  > — https://docs.spring.io/spring-boot/reference/testing/testcontainers.html
  _"the connection details take precedence over any connection-related configuration properties."_

**Độ khó:** hard thật · hợp level middle, senior — Chẩn đoán test chậm theo cơ chế cache key và tổ chức lại test pyramid; topic chỉ tới middle nhưng hợp lệ.
**Dùng trong phỏng vấn:** ~6 phút, 3 ý hỏi, chấm được — Điểm chấm rõ nhưng 3 ý hỏi lớn.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu vì sao test Spring Boot chậm khi context không được dùng lại, và cách tổ chức test hợp lý.
- Ý bắt buộc: Spring cache ApplicationContext theo cache key; khác bean override hay profile là dựng context mới; @MockitoBean khác nhau giữa các class và @DirtiesContext làm mất cache hit; Dùng slice test (@WebMvcTest, @DataJpaTest) thay @SpringBootTest khi chỉ cần một lớp; Chuẩn hóa base class có cùng tập mock để tăng cache hit; H2 khác PostgreSQL; dùng Testcontainers với @ServiceConnection cho test repository
- Dấu hiệu trả lời sai: Thêm @DirtiesContext để 'test sạch hơn'; Chạy fork mỗi test class một JVM cho nhanh; Tin test xanh trên H2 là đủ cho PostgreSQL
- Câu hỏi nối tiếp: Bạn đo cache hit/miss của context thế nào để biết thay đổi có hiệu quả?

**Đề xuất sửa:**
- Câu hỏi mới: Bộ test Spring Boot của team chạy 25 phút; log cho thấy ApplicationContext bị khởi tạo lại hàng chục lần. Các test class dùng @SpringBootTest với tổ hợp @MockitoBean khác nhau, vài class có @DirtiesContext, còn test repository chạy trên H2. Vì sao context bị dựng lại nhiều lần, và bạn tổ chức lại bộ test thế nào?
- Đáp án: Rút đoạn cơ chế còn 2 câu; giữ nguyên nhân 1–3; trong phần tổ chức lại, đưa ý Testcontainers lên ngay sau slice test và bỏ ý RANDOM_PORT hoặc chuyển sang follow-up.

### de-qa-1119 · Cần sửa · tin cậy medium · Chỉ hình thức

**Topic:** Unit test với JUnit và Mockito (`java.testing.junit-mockito`) · ~743 token · hard của topic: 2

**Câu hỏi:** Unit test Mockito của OrderService đều xanh, nhưng production lỗi vì câu query JPA sai và vì cổng thanh toán trả lỗi khác với mô phỏng. Trong test còn có `when(spy.calculate(...))` ném exception khó hiểu và nhiều stub thừa. Phân biệt mock, stub, spy; nêu các pitfall khi dùng Mockito và khi nào nên thay mock bằng test tích hợp.

**Kết luận:** Phân biệt mock/stub/spy và pitfall when(spy...) đúng theo Mockito javadoc và định nghĩa Meszaros. Cần fix vì có 3 ý hỏi, phần 'khi nào thay bằng test tích hợp' nằm sau điểm cắt, và câu 'Mockito mặc định loose' dễ gây hiểu nhầm khi dùng MockitoExtension.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| major | interview_fit | Câu hỏi có 3 ý hỏi (phân biệt mock/stub/spy, pitfall Mockito, khi nào thay bằng test tích hợp). | Hỏi 2 ý: 'Vì sao unit test xanh mà production vẫn lỗi, và khi nào bạn thay mock bằng test tích hợp?'; phân biệt mock/stub/spy và pitfall spy làm follow-up. |
| major | length | Chunk ~743 token; điểm cắt 600 token rơi ngay sau tiêu đề 'Khi nào thay bằng test tích hợp', mất toàn bộ ý được hỏi trực tiếp này. | Rút phần phân biệt còn 3 dòng ngắn và pitfall còn 2–3 ý để phần test tích hợp nằm trước điểm cắt. |
| minor | factual | 'Mockito mặc định loose' dễ gây hiểu nhầm: khi dùng MockitoExtension, strict stubs là mặc định (chưa có câu trích trong lần duyệt), nên stub thừa sẽ làm test lỗi chứ không im lặng. | Viết: 'Với mock() thuần thì stub thừa không bị báo; MockitoExtension mặc định dùng strict stubs nên báo UnnecessaryStubbingException.' |

**Kiểm chứng:**
- `supported` Stub trả câu trả lời dựng sẵn; mock kiểm tra tương tác (behavior verification)
  > Of these kinds of doubles, only mocks insist upon behavior verification.  
  > — https://martinfowler.com/articles/mocksArentStubs.html
  _"Stubs provide canned answers to calls made during the test". Nguồn thứ cấp (bài viết của Martin Fowler trích Meszaros)._
- `supported` Spy nên dùng cẩn thận và thỉnh thoảng, ví dụ với code legacy; không dùng partial mock cho code mới thiết kế tốt
  > Real spies should be used carefully and occasionally, for example when dealing with legacy code.  
  > — https://javadoc.io/static/org.mockito/mockito-core/5.14.2/org/mockito/Mockito.html
  _Cùng trang: "I wouldn't use partial mocks for new, test-driven and well-designed code."_
- `supported` when(spy...) có thể không dùng được; dùng họ doReturn/doThrow/doAnswer
  > Sometimes it's impossible or impractical to use when(Object) for stubbing spies.  
  > — https://javadoc.io/static/org.mockito/mockito-core/5.14.2/org/mockito/Mockito.html
  _Trang khuyên dùng doReturn|Answer|Throw() thay thế._
- `supported` Method final trên spy gây rắc rối và không verify được
  > Watch out for final methods.  
  > — https://javadoc.io/static/org.mockito/mockito-core/5.14.2/org/mockito/Mockito.html
  _Trang giải thích Mockito không mock method final nên stub/verify trên spy gặp vấn đề._
- `supported` Strict stubbing báo stub thừa và argument mismatch; tích hợp qua MockitoExtension
  > Strict stubbing reports unnecessary stubs, detects stubbing argument mismatch and makes the tests more DRY  
  > — https://javadoc.io/static/org.mockito/mockito-core/5.14.2/org/mockito/Mockito.html
  _Mục 40: "Strict stubbing with JUnit5 Extension - org.mockito.junit.jupiter.MockitoExtension"._

**Độ khó:** hard thật · hợp level middle, senior — Nối triệu chứng production với giới hạn của mock; định nghĩa thì dễ nhưng phần chẩn đoán là lý luận.
**Dùng trong phỏng vấn:** ~5 phút, 3 ý hỏi, chấm được — Điểm chấm rõ nhưng 3 ý hỏi.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu test double nào dùng khi nào và giới hạn của unit test dùng mock.
- Ý bắt buộc: Stub trả kết quả dựng sẵn (kiểm trạng thái); mock để verify tương tác; Spy gọi method thật; when(spy.x()) gọi method thật lúc stub, dùng doReturn().when(spy); Mock thứ mình không kiểm soát (repository, gateway) chỉ phản ánh giả định nên không bắt được JPQL sai hay lỗi gateway thật; Thay bằng @DataJpaTest + Testcontainers cho query, WireMock/contract test cho HTTP client; Strict stubbing để bắt stub thừa và argument lệch
- Dấu hiệu trả lời sai: Mock repository JPA rồi tin query đúng; Verify từng lời gọi nội bộ; Dùng spy cho code mới thay vì tách dependency
- Câu hỏi nối tiếp: Bạn viết test nào để chắc OrderService xử lý đúng khi gateway trả 502 hoặc timeout?

**Đề xuất sửa:**
- Câu hỏi mới: Unit test Mockito của OrderService đều xanh, nhưng production lỗi vì câu query JPA sai và vì cổng thanh toán trả lỗi khác với mô phỏng. Vì sao test không bắt được, và khi nào bạn thay mock bằng test tích hợp?
- Đáp án: Rút phần phân biệt mock/stub/spy còn 3 dòng; giữ pitfall 4 (mock thứ mình không kiểm soát) làm ý chính, gộp pitfall 1–3 thành 1–2 câu; đưa phần test tích hợp lên trước điểm cắt; sửa câu 'mặc định loose'.

### de-qa-1120 · Cần sửa · tin cậy medium · Phải đọc

**Topic:** Thiết kế REST API với Spring MVC (`java.web.rest-api-design`) · ~693 token · hard của topic: 2 · golden: g03

**Câu hỏi:** API POST /payments tạo giao dịch; mobile client tự retry khi timeout nên thỉnh thoảng khách bị trừ tiền hai lần. Dựa trên ngữ nghĩa HTTP method, thiết kế cơ chế chống trùng bằng idempotency key: cách lưu trữ, status code cho từng tình huống, và các trade-off.

**Kết luận:** Thiết kế idempotency key và status code khớp draft IETF (400/409/422, trả lại kết quả cũ, UUID, công bố thời hạn). Cần fix vì câu hỏi liệt kê 3 phần (lưu trữ, status code, trade-off) và câu trích RFC 9110 về retry chưa kiểm chứng trực tiếp được (trang bị cắt), chỉ có nguồn thứ cấp MDN.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| major | interview_fit | Câu hỏi yêu cầu thiết kế kèm 3 phần liệt kê (lưu trữ, status code từng tình huống, trade-off); tính theo rubric là 3 ý hỏi, vượt mức 2. | Hỏi: 'Thiết kế cơ chế chống trùng bằng idempotency key thế nào, và xử lý request trùng đến khi bản gốc còn đang chạy ra sao?'; status code chi tiết và trade-off làm follow-up. |
| major | factual | Câu dẫn RFC 9110 về việc client không nên tự retry method không idempotent chưa có trích dẫn trực tiếp (trang RFC bị cắt khi fetch); chỉ có nguồn thứ cấp MDN cho phần định nghĩa. | Người duyệt đối chiếu RFC 9110 §9.2.2; nếu đúng thì giữ nguyên. |
| minor | length | Chunk ~693 token; điểm cắt 600 token rơi trong trade-off thứ 2, mất phương án PUT /payments/{id} và ghi chú ETag/If-Match. Các ý bắt buộc (ngữ nghĩa POST, lưu key với UNIQUE, status code) nằm trước điểm cắt. | Bỏ ý ETag (thuộc chủ đề kiểm soát đồng thời) để giữ phương án PUT trước điểm cắt. |

**Kiểm chứng:**
- `supported` PUT, DELETE và các method an toàn là idempotent; POST không
  > All safe methods are idempotent, as well as PUT and DELETE.  
  > — https://developer.mozilla.org/en-US/docs/Glossary/Idempotent
  _Nguồn thứ cấp. MDN: "The POST and PATCH methods are not guaranteed to be idempotent." Bản rfc-editor.org và httpwg.org của RFC 9110 đều bị cắt trước §9.2.2 khi fetch._
- `unverified` Idempotent có thể tự lặp lại khi lỗi kết nối; client không nên tự retry POST trừ khi biết request idempotent
  _Chỉ đọc được câu ở RFC 9110 §2.4: "Some requests can be automatically retried by a client in the event of an underlying connection failure, as described in Section 9.2.2"; phần SHOULD NOT retry của §9.2.2 không đọc được._
- `supported` Key nên là UUID hoặc định danh ngẫu nhiên tương tự
  > It is RECOMMENDED that a UUID [RFC4122] or a similar random identifier be used as an idempotency key.  
  > — https://www.ietf.org/archive/id/draft-ietf-httpapi-idempotency-key-header-07.html
  _Draft hết hạn 18 April 2026, khớp với ghi chú 'đã hết hạn' trong đáp án._
- `supported` Lặp lại sau khi hoàn tất: trả kết quả lần trước, kể cả lỗi; có thể dùng fingerprint payload
  > The resource SHOULD respond with the result of the previously completed operation, success or an error.  
  > — https://www.ietf.org/archive/id/draft-ietf-httpapi-idempotency-key-header-07.html
  _"An idempotency fingerprint MAY be used in conjunction with an idempotency key to determine the uniqueness of a request."_
- `supported` Thiếu key: 400; cùng key payload khác: 422; request gốc đang xử lý: 409
  > the resource SHOULD reply with an HTTP 409 status code with body containing problem description.  
  > — https://www.ietf.org/archive/id/draft-ietf-httpapi-idempotency-key-header-07.html
  _400: "the resource SHOULD reply with an HTTP 400 status code with body containing a link pointing to relevant documentation." 422: "the resource SHOULD reply with a HTTP 422 status code"._
- `supported` Thời hạn lưu key công bố trong tài liệu API
  > The resource SHOULD define such expiration policy and publish it in the documentation.  
  > — https://www.ietf.org/archive/id/draft-ietf-httpapi-idempotency-key-header-07.html

**Độ khó:** hard thật · hợp level middle, senior — Thiết kế có xử lý đồng thời (unique constraint, trạng thái đang xử lý) và side effect bên ngoài, không chỉ định nghĩa idempotent.
**Dùng trong phỏng vấn:** ~5 phút, 3 ý hỏi, chấm được — Điểm chấm rõ nhưng 3 phần liệt kê.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Hiểu vì sao retry POST gây trùng và cách dùng idempotency key để chống trùng an toàn.
- Ý bắt buộc: POST không idempotent; timeout không cho biết server đã xử lý chưa; Client sinh key ngẫu nhiên (UUID) cho mỗi thao tác, dùng lại khi retry; Server lưu (client, key, fingerprint, trạng thái, response) với UNIQUE, ghi 'đang xử lý' trước; Trùng sau khi xong: trả lại kết quả cũ; đang xử lý: 409; payload khác: 422; thiếu key: 400; Gọi cổng thanh toán cũng phải idempotent hoặc có đối soát
- Dấu hiệu trả lời sai: Chỉ kiểm tra key bằng SELECT rồi INSERT mà không có unique constraint; Trả lỗi khi gặp key trùng đã hoàn tất thay vì trả lại kết quả; Nghĩ lưu key trong Redis là đủ an toàn tuyệt đối
- Câu hỏi nối tiếp: Server crash sau khi gọi cổng thanh toán nhưng trước khi lưu response; request retry tới thì xử lý thế nào?

**Đề xuất sửa:**
- Câu hỏi mới: API POST /payments tạo giao dịch; mobile client tự retry khi timeout nên thỉnh thoảng khách bị trừ tiền hai lần. Thiết kế cơ chế chống trùng bằng idempotency key thế nào, và xử lý request trùng đến khi bản gốc còn đang chạy ra sao?
- Đáp án: Giữ phần ngữ nghĩa HTTP và thiết kế 1–3; rút trade-off còn 2 ý (chi phí lưu trữ, side effect bên ngoài); bỏ ý ETag.

### de-qa-1121 · Cần sửa · tin cậy high · Phải đọc

**Topic:** Thiết kế REST API với Spring MVC (`java.web.rest-api-design`) · ~782 token · hard của topic: 2

**Câu hỏi:** Bạn chuẩn hóa xử lý lỗi cho hơn chục service Spring MVC: hiện mỗi controller tự try/catch, có chỗ trả 200 kèm body lỗi, có chỗ lộ stack trace và tên cột DB, client không phân biệt được lỗi validation với lỗi hệ thống. Thiết kế error contract và global exception handling thế nào, và vì sao việc tách DTO khỏi entity là một phần của thiết kế đó?

**Kết luận:** Nội dung đúng theo RFC 9457, tài liệu Spring MVC (ProblemDetail, ErrorResponse, ResponseEntityExceptionHandler, spring.mvc.problemdetails.enabled) và OWASP về mass assignment. Cần fix vì toàn bộ phần 'vì sao tách DTO' (ý hỏi thứ hai) nằm sau điểm cắt 600 token.

| Mức | Loại | Vấn đề | Cách sửa |
|---|---|---|---|
| major | length | Chunk ~782 token; điểm cắt 600 token rơi ngay đầu phần 'Vì sao tách DTO khỏi entity', nên snippet mất hẳn ý hỏi thứ hai. | Rút phần cơ chế Spring MVC còn 3 gạch (ProblemDetail/ErrorResponse, advice kế thừa ResponseEntityExceptionHandler + handler cuối cho Exception, không lộ chi tiết) và đưa 2–3 lý do tách DTO quan trọng nhất (mass assignment, lộ cột nội bộ, lazy loading khi serialize) lên trước điểm cắt. |
| minor | factual | Ý serialize entity JPA gây LazyInitializationException/N+1 và đệ quy vô hạn chưa có câu trích trong lần duyệt; đúng theo hiểu biết chung. | Giữ nguyên. |
| minor | interview_fit | Phần Spring Boot property và thư viện dùng chung là chi tiết phụ, làm đáp án dài. | Chuyển thành điểm cộng. |

**Kiểm chứng:**
- `supported` Problem Details (RFC 9457) gồm type, title, status, detail, instance, cho phép trường mở rộng **(quote không có nguyên văn trên trang nguồn)**
  > The "type" member is a JSON string containing a URI reference that identifies the problem type.  
  > — https://www.rfc-editor.org/rfc/rfc9457.html
  _Cùng mục 3.1 định nghĩa title, status, detail, instance; mục 3.2: "Problem type definitions MAY extend the problem details object with additional members"._
- `supported` ProblemDetail chứa cả trường chuẩn và không chuẩn; mọi exception Spring MVC implement ErrorResponse
  > this allows exceptions to encapsulate and expose the details of how they map to an HTTP response. All Spring MVC exceptions implement this.  
  > — https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-ann-rest-exceptions.html
  _"ProblemDetail — representation for an RFC 9457 problem detail; a simple container for both standard fields defined in the spec, and for non-standard ones."_
- `supported` @ControllerAdvice kế thừa ResponseEntityExceptionHandler xử lý mọi exception Spring MVC thành ProblemDetail
  > ResponseEntityExceptionHandler — convenient base class for an @ControllerAdvice that handles all Spring MVC exceptions, and any ErrorResponseException, and renders an error response with a body.  
  > — https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-ann-rest-exceptions.html
- `supported` spring.mvc.problemdetails.enabled; advice tự viết phải xếp trước handler của Boot
  > You'll need to ensure your handler is ordered ahead of the one configured by Spring Boot whose order is 0.  
  > — https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-ann-rest-exceptions.html
  _"In Spring Boot, the spring.mvc.problemdetails.enabled property autoconfigures a ResponseEntityExceptionHandler"_
- `supported` Trường mở rộng qua map properties (Jackson trải thành thuộc tính cấp cao nhất) hoặc subclass; tùy biến để không lộ chi tiết cài đặt
  > It is also good practice to customize the problem details for Spring MVC exceptions to avoid revealing implementation details.  
  > — https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-ann-rest-exceptions.html
  _Properties map: "ensures this "properties" Map is unwrapped and rendered as top level JSON properties in the response"._
- `supported` Bind request thẳng vào entity gây mass assignment; dùng DTO
  > An architectural approach is to create Data Transfer Objects and avoid binding input directly to domain objects.  
  > — https://cheatsheetseries.owasp.org/cheatsheets/Mass_Assignment_Cheat_Sheet.html

**Độ khó:** hard thật · hợp level middle, senior — Thiết kế contract dùng chung cho nhiều service và lý do kiến trúc tách DTO; topic chỉ tới middle nhưng hợp lệ.
**Dùng trong phỏng vấn:** ~5 phút, 2 ý hỏi, chấm được — Hai ý hỏi, điểm chấm rõ.

**Hướng dẫn cho người duyệt junior**
- Câu này kiểm tra: Biết thiết kế error response nhất quán cho REST API và hiểu vì sao không trả/nhận entity trực tiếp.
- Ý bắt buộc: Dùng Problem Details (RFC 9457): type, title, status, detail, instance + errorCode, lỗi theo field; Status code đúng ngữ nghĩa, không trả 200 kèm body lỗi; Một @RestControllerAdvice kế thừa ResponseEntityExceptionHandler, thêm handler cho exception nghiệp vụ và handler cuối cho Exception; Không lộ stack trace/tên cột; log đầy đủ kèm trace id; Tách DTO: chống mass assignment, không lộ cột nội bộ, contract ổn định khi đổi schema
- Dấu hiệu trả lời sai: Mỗi controller tự try/catch; Trả exception.getMessage() thẳng cho client; Bind @RequestBody vào entity JPA
- Câu hỏi nối tiếp: Client cần hiển thị lỗi validation theo từng field bằng nhiều ngôn ngữ; bạn mở rộng ProblemDetail thế nào?

**Đề xuất sửa:**
- Đáp án: Rút phần 'Cơ chế trong Spring MVC' còn 3 gạch; bỏ ý thư viện dùng chung và chi tiết spring.mvc.problemdetails.enabled (hoặc gộp 1 câu); đưa phần 'Vì sao tách DTO' (3 lý do chính) lên trước điểm cắt 600 token.

