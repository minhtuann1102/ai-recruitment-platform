# Feature Specification: Textbook Ingestion & RAG Quality

**Feature Branch**: `docs/textbook-ingestion-spec` (spec); branch code đặt ở plan (theo `docs/conventions.md`; thư mục
spec độc lập với branch)

**Created**: 2026-11-14

**Status**: Draft — chờ AIE trả lời mục "Câu hỏi cho AIE" (đều đã có mặc định, không chặn lô thử)

**Owner**: DE (AIE review) — **Sprint**: 3–4 (09/11 → 07/12/2026)

**Covers**: S3-DE-1, S3-DE-2, S3-DE-3, S3-DE-4, S3-DE-5, S4-DE-1 (phạm vi thu hẹp, xem "Thay đổi so với sprint plan")

**Input**: User description: "Nạp tài liệu kỹ thuật chính thức (`source_type = 'textbook'`) vào `knowledge_chunks` để
ai-service có căn cứ chấm giai đoạn scenario và các câu đào sâu AI tự đặt, đồng thời làm tài liệu gợi ý cho lộ trình
học (016). Chọn trang dạng giải thích từ docs chính thức của đủ 6 track, đi ngược từ các tình huống `scn.*` trong
catalog; không nạp trang tham chiếu API. Làm theo lô: nạp thử một track, AIE bật cờ và đo, rồi mới nạp phần còn lại."

**Nguồn thiết kế**: [`docs/architecture/data-pipeline.md`](../../docs/architecture/data-pipeline.md);
[`docs/ai-service/07-data-storage.md`](../../docs/ai-service/07-data-storage.md) §Textbook;
[`docs/ai-service/03-orchestrator-state-machine.md`](../../docs/ai-service/03-orchestrator-state-machine.md) §4.3 (phase
`scenario`); đường ghi và crawler của [spec 005](../005-rag-knowledge-base-qa/spec.md) (FR-006–FR-016, FR-022–FR-025);
đề xuất agentic gửi AIE [`plans/reports/aie-request-261114-1057-agentic-ai-service.md`](../../plans/reports/aie-request-261114-1057-agentic-ai-service.md)
§11, §13. Spec chỉ ghi phần mới hoặc khác.

## Bối cảnh (kiểm tra 2026-11-14)

- **Đề cương nộp GVHD** cam kết nguồn tri thức RAG gồm "documentation chính thức của các công nghệ theo vị trí đã
  chọn" cùng bộ câu hỏi kèm đáp án. Phần Q&A đã có (005); phần docs chính thức chưa có bản ghi nào.
- **Chỗ đang thiếu căn cứ**: phase `scenario` chỉ đọc `textbook`, không đọc `interview_qa`
  (`apps/ai-service/app/turn_reference_snippets.py`, `plan_snippets.py`), nên hiện chấm không có tài liệu nào. Trọng số
  của phase này trong điểm cuối là 0,25 (fresher) tới 0,45 (senior). Số đo 30/10: tỉ lệ ý có căn cứ của câu AI tự đặt
  0,63, của câu lấy từ kho 0,88.
- **Chỗ không cần nạp**: câu dễ và trung bình lấy từ kho đã có đáp án chuẩn và DE đã soát với docs khi làm 005.
- **Catalog ai-service có 28 tình huống**: Java 4, Node.js 4, Python 4, Frontend 4, DevOps 4, AI 8. Mỗi tình huống chỉ
  có `id`, tiêu đề và cấp bậc, không có đáp án mẫu.
- **Bộ lọc scenario lấy hai category**: category chính của track (category xuất hiện nhiều nhất trong các topic của
  track) và `System Design` (`plan_snippets.scenario_categories`). Java, Node.js và Python cùng có category chính là
  `Backend`; còn lại `Frontend`, `DevOps`, `AI`. Hệ quả: đoạn ghi `System Design` được mọi track tìm thấy; đoạn ghi
  `Database` không được phase scenario tìm thấy; docs của ba track backend nằm chung nhóm `Backend`, nên docs Spring
  có thể được trả về cho tình huống Node.js.
- **ai-service đã viết sẵn đường cho `textbook`**: kho BM25 nạp mọi bản ghi `textbook`, bản ghi `difficulty` trống vẫn
  khớp bộ lọc, cờ `RAG_TEXTBOOK_ENABLED` mặc định tắt. Tìm theo lượt chỉ dùng BM25 (không embed), lấy tối đa 3 đoạn
  trong ngân sách 600 token.

## Thay đổi so với sprint plan (DE chốt 2026-11-14, chờ team xác nhận)

| Task | Sprint plan ghi | Spec này làm |
|---|---|---|
| S3-DE-1 | 10+ nguồn textbook / tutorial | Nguồn chính thức cho đủ 6 track + 1 nguồn bổ sung về đánh đổi; chỉ trang giải thích |
| S3-DE-2 | Chunk theo chapter / section, có `difficulty_hint` | Chunk theo section, một ý một đoạn; không gán độ khó |
| S3-DE-3 | ~5.000+ chunk | Vài trăm tới ~1.500 chunk, đo bằng độ phủ tình huống |
| S3-DE-4, S3-DE-5, S4-DE-1 | Đánh giá RAG, dedup, review chất lượng | Giữ nguyên, áp cho tập `textbook` |

Quality Gate số chunk tối thiểu của constitution (6.000 ở sprint này) đã đạt bằng kho hiện có (8.356 bản ghi sau PR
\#87), nên thu hẹp không làm trượt gate. Đề cương nộp GVHD không ghi số lượng docs.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Lô thử một track, từ danh sách trang tới kho (Priority: P1)

DE chọn một track, lập danh sách trang docs chính thức ứng với từng tình huống của track đó, kiểm giấy phép, crawl, cắt
đoạn và ghi vào kho. AIE bật cờ, chạy vài phiên và đo: phase scenario đã có tài liệu chưa, độ trễ đổi bao nhiêu.

**Why this priority**: Là lát cắt nhỏ nhất chứng minh được toàn bộ đường đi và trả lời câu hỏi còn treo (docs có nâng
tỉ lệ ý có căn cứ không, cỡ đoạn có hợp không) trước khi bỏ công cho năm track còn lại. Xong riêng story này đã đáp
ứng một phần cam kết trong đề cương.

**Independent Test**: Chạy pipeline cho track thử trên máy DE; đếm trong kho thấy bản ghi `textbook` của track đó, số
bản ghi `interview_qa` không đổi; mỗi tình huống của track có ít nhất một đoạn được gắn; truy vấn mẫu bằng tiêu đề tình
huống trả về đoạn đã gắn.

**Acceptance Scenarios**:

1. **Given** danh sách trang của track thử đã ghi giấy phép và kết quả robots cho từng nguồn, **When** DE chạy crawl,
   **Then** chỉ các URL trong danh sách được tải, URL bị robots cấm bị bỏ qua kèm log, dữ liệu thô nằm ngoài git.
2. **Given** dữ liệu thô của track thử, **When** DE chạy bước xử lý, **Then** mỗi đoạn có nguồn, giấy phép, track, mã
   tình huống được gắn và không đoạn nào chỉ gồm menu, mục lục hay khối code không có lời giải thích.
3. **Given** các đoạn đã xử lý, **When** DE ghi vào kho, **Then** số bản ghi `interview_qa` trước và sau bằng nhau, và
   chạy lại lần hai không thêm bản ghi nào.
4. **Given** kho đã có `textbook` của track thử, **When** AIE bật cờ và chạy phiên của track đó, **Then** các lượt
   scenario có tài liệu đối chiếu, và AIE ghi lại số đo trước / sau.

---

### User Story 2 - Nạp năm track còn lại (Priority: P2)

Sau khi DE xem số đo của lô thử và chỉnh cỡ đoạn nếu cần, DE lập danh sách trang cho năm track còn lại và nạp theo từng
lô, mỗi lô một track.

**Why this priority**: Hoàn tất cam kết "theo vị trí đã chọn" của đề cương và phủ đủ 28 tình huống. Xếp sau US1 vì cách
cắt đoạn có thể đổi sau số đo đầu tiên.

**Independent Test**: Báo cáo độ phủ cho thấy 6/6 track có nguồn chính thức và 28/28 tình huống có ít nhất một đoạn;
nạp lại một track không làm đổi số bản ghi của track khác.

**Acceptance Scenarios**:

1. **Given** lô thử đã xong, **When** DE nạp track thứ hai, **Then** bản ghi của track thử không bị xóa hay sửa.
2. **Given** một trang dùng chung cho nhiều track (ví dụ tài liệu cơ sở dữ liệu cho ba track backend), **When** nạp
   track sau, **Then** kho vẫn chỉ có một bản của mỗi đoạn, đoạn đó được cập nhật đủ các track cùng mã tình huống nó
   phục vụ, và không tạo lại embedding.
3. **Given** một nguồn bị robots cấm, chặn truy cập tự động hoặc nằm sau đăng nhập, **When** lập danh sách, **Then**
   nguồn đó bị loại và ghi lý do, tình huống liên quan được bù bằng nguồn khác; nguồn có điều khoản riêng nhưng truy
   cập được thì vẫn dùng và được ghi loại `restricted`.

---

### User Story 3 - Soát chất lượng và báo cáo độ phủ (Priority: P2)

DE cho worker soát từng đoạn theo hướng dẫn cố định (giữ / sửa / bỏ), có đoạn mồi để kiểm worker, rồi xuất báo cáo: mỗi
tình huống có bao nhiêu đoạn, truy vấn theo tình huống có tìm ra đoạn đã gắn không, bảng nguồn và giấy phép.

**Why this priority**: Đoạn nhiễu làm BM25 trả kết quả lạc, kéo chất lượng chấm xuống thay vì lên. Báo cáo độ phủ là
bằng chứng cho S3-DE-4 và S4-DE-1, và là thứ đưa vào báo cáo đồ án.

**Independent Test**: Chạy bước soát trên một lô có cài sẵn đoạn mồi; mọi đoạn mồi bị đánh dấu bỏ; báo cáo liệt kê đủ
28 tình huống với số đoạn và kết quả truy vấn.

**Acceptance Scenarios**:

1. **Given** một lô đoạn có cài đoạn mồi (mục lục, khối code trơ, đoạn lạc chủ đề), **When** worker soát, **Then**
   mọi đoạn mồi bị đánh dấu bỏ; lô nào bỏ sót đoạn mồi thì phải soát lại.
2. **Given** kho đã nạp, **When** DE chạy báo cáo, **Then** tình huống chưa có đoạn nào hoặc truy vấn không tìm ra đoạn
   đã gắn được nêu tên để bù.

---

### User Story 4 - Bù tài liệu cho topic khó mà AI tự đặt câu nhiều (Priority: P3)

Khi AIE cung cấp danh sách topic mà Planner phải tự đặt câu nhiều nhất, DE thêm trang giải thích sâu cho các topic đó.

**Why this priority**: Phục vụ câu đào sâu ở phase technical. Phụ thuộc số liệu từ AIE và lợi ích nhỏ hơn scenario vì
câu chính của các topic này đã có đáp án từ kho.

**Independent Test**: Với mỗi topic trong danh sách AIE đưa, kho có ít nhất một đoạn `textbook` gắn topic đó.

**Acceptance Scenarios**:

1. **Given** danh sách topic từ AIE, **When** DE nạp trang bổ sung, **Then** mỗi topic trong danh sách có ít nhất một
   đoạn và các đoạn tuân cùng quy tắc nguồn, giấy phép, cỡ đoạn như phần scenario.

---

### Edge Cases

- Trang docs đổi URL hoặc trả 404 lúc crawl: bỏ qua, ghi log, đánh dấu trong danh sách để thay trang khác; không dừng
  cả lô.
- Trang cần render JavaScript mới có nội dung: thử chế độ render đã có ở 005; vẫn rỗng thì loại trang.
- Site chặn truy cập tự động (403, captcha): loại nguồn, không né chặn.
- Một section rất dài (bài hướng dẫn nhiều nghìn chữ): cắt theo đoạn văn trong section, mỗi đoạn mang đường dẫn tiêu
  đề để đọc riêng vẫn hiểu.
- Section chỉ có code, bảng tham số hay danh sách link: bỏ.
- Đoạn trùng nội dung với đáp án Q&A đã có trong kho (Q&A 005 có cặp chuyển thể từ react.dev): giữ bản ghi cũ, không
  ghi đè, đếm vào thống kê trùng.
- Một tình huống không tìm được trang chính thức nào truy cập được: dùng nguồn bổ sung; vẫn không có thì ghi là
  chưa phủ trong báo cáo, không tự viết nội dung thay docs.
- AIE chưa đo được lô thử trong thời gian của sprint: DE dùng kết quả truy vấn mẫu của chính mình để quyết định nạp
  tiếp, ghi rõ là chưa có số đo từ ai-service.
- Bản ghi `textbook` cũ còn sót trong kho từ thử nghiệm trước: báo cáo trước khi ghi, không tự xóa bản ghi không thuộc
  lô đang chạy.

## Requirements *(mandatory)*

### Functional Requirements

**Chọn nguồn và giấy phép**

- **FR-001**: Mỗi lô MUST có một danh sách trang được commit, mỗi dòng ghi: URL, tên nguồn, track, mã tình huống hoặc
  topic mà trang phục vụ, giấy phép, đường dẫn tới nơi công bố giấy phép, ngày kiểm.
- **FR-002**: Mỗi track trong 6 track MUST có ít nhất một nguồn là tài liệu chính thức của công nghệ thuộc track đó.
  Nguồn không chính thức chỉ được dùng làm bổ sung cho phần đánh đổi và thiết kế hệ thống.
- **FR-003**: Danh sách trang MUST đi từ tình huống ra: mỗi tình huống `scn.*` nhắm 3–5 trang. Trang chỉ liệt kê hàm,
  tham số, kiểu trả về MUST NOT được đưa vào.
- **FR-004**: Điều khoản của mỗi nguồn MUST được ghi lại nguyên văn và phân loại: `open` (giấy phép mở cho phép sao
  chép kèm ghi nguồn) hoặc `restricted` (điều khoản riêng, chỉ phi thương mại, giữ mọi quyền, hoặc không tìm thấy
  tuyên bố). Cả hai loại đều được dùng cho mục đích đồ án, nội bộ, không thu phí (DE chốt 2026-11-14); phân loại đi
  theo từng đoạn vào kho để lọc lại được nếu sản phẩm thương mại hóa. Nguồn chỉ bị loại vì lý do truy cập: robots cấm,
  site chặn truy cập tự động, nội dung sau đăng nhập hoặc trả phí, hoặc điều khoản cấm đích danh việc thu thập tự động.
- **FR-005**: Việc kiểm giấy phép và robots MUST xong và được ghi lại trước lần crawl đầu tiên của nguồn đó.

**Crawl**

- **FR-006**: Crawl MUST tuân các ràng buộc của 005 (FR-022–FR-025): đọc robots.txt, nghỉ giữa request, có giới hạn số
  trang, không đăng nhập, không né cơ chế chặn, không lưu thông tin cá nhân.
- **FR-007**: Crawl MUST chỉ tải các URL có trong danh sách trang, không tự đi theo link.
- **FR-008**: Dữ liệu thô và dữ liệu đã xử lý MUST NOT được commit; chỉ commit danh sách trang và báo cáo.

**Cắt đoạn và làm sạch**

- **FR-009**: Nội dung MUST được cắt theo section của trang; mỗi đoạn nói về một ý và mang đường dẫn tiêu đề (tên
  trang và các tiêu đề cha) để đọc riêng vẫn hiểu.
- **FR-010**: Cỡ đoạn MUST nằm trong giới hạn đủ để ba đoạn vừa ngân sách tài liệu của một lượt chấm; mặc định mục tiêu
  80–250 token, tối đa 400 (chờ AIE xác nhận, xem "Câu hỏi cho AIE").
- **FR-011**: Thuật ngữ tiếng Anh, tên hàm, tên lệnh và ví dụ code đi kèm lời giải thích MUST được giữ nguyên; không
  dịch nội dung.
- **FR-012**: Đoạn chỉ gồm điều hướng, mục lục, ghi chú phiên bản, khối code không có lời giải thích hoặc bảng tham số
  MUST bị bỏ.
- **FR-013**: Mọi đoạn MUST qua bước xóa thông tin cá nhân đã có của pipeline.
- **FR-014**: Đoạn trùng nội dung MUST bị loại trước khi tạo embedding, kể cả trùng với bản ghi đã có trong kho thuộc
  tập dữ liệu khác.

**Dữ liệu ghi vào kho**

- **FR-015**: Mỗi đoạn MUST có `source_type = 'textbook'`; ngôn ngữ; cùng mô hình embedding với `interview_qa`.
  `category` MUST là một trong hai giá trị mà phase scenario tìm: category chính của track (đọc từ catalog ai-service,
  từ chối giá trị không có trong catalog) cho tài liệu riêng của công nghệ thuộc track, hoặc `System Design` cho tài
  liệu dùng chung nhiều track (cơ sở dữ liệu, cache, hàng đợi, thiết kế hệ thống). `topic_id` và `difficulty` để
  trống; riêng đoạn của US4 có `topic_id` và lấy category của topic đó.
- **FR-016**: Metadata của mỗi đoạn MUST có: định danh tập dữ liệu, URL nguồn, giấy phép, loại giấy phép (`open` /
  `restricted`), dòng ghi nguồn, tiêu đề
  trang, đường dẫn tiêu đề, danh sách track, danh sách mã tình huống mà đoạn phục vụ.
- **FR-017**: Một trang phục vụ nhiều track MUST chỉ tạo một bản của mỗi đoạn, ghi đủ các track và mã tình huống; nếu
  các track đó khác category chính thì trang MUST dùng category `System Design`.
- **FR-018**: Ghi vào kho MUST dùng đường ghi của 005, chạy từ `main` mới nhất, và MUST idempotent: chạy lại cùng đầu
  vào không thêm bản ghi.
- **FR-019**: Mỗi nguồn MUST có định danh tập dữ liệu riêng để nạp lại hoặc gỡ một nguồn không đụng tới nguồn khác, và
  MUST NOT làm đổi bản ghi `interview_qa` hay `job_description`. Một lô (một track) là một nhóm nguồn; nguồn dùng chung
  được bổ sung trang khi nạp track sau.
- **FR-020**: Mỗi lần chạy MUST in thống kê: số trang vào, số đoạn, số đoạn bị bỏ theo từng lý do, tỉ lệ trùng, số
  embedding lỗi, số bản ghi của từng `source_type` trước và sau.

**Soát chất lượng và báo cáo**

- **FR-021**: Mọi đoạn MUST được soát theo hướng dẫn cố định với ba kết luận giữ / sửa / bỏ trước khi ghi vào kho. Mỗi
  lô soát MUST có đoạn mồi; lô bỏ sót đoạn mồi MUST soát lại. DE duyệt danh sách bỏ và sửa.
- **FR-022**: Hệ thống MUST xuất báo cáo độ phủ: số đoạn theo track, theo tình huống, theo nguồn; tình huống chưa có
  đoạn nào; bảng nguồn kèm giấy phép.
- **FR-023**: Hệ thống MUST chạy được kiểm tra truy hồi: với mỗi tình huống, truy vấn bằng tiêu đề tình huống và báo
  có đoạn đã gắn với tình huống đó trong ba kết quả đầu hay không, theo cả cách tìm bằng từ khóa lẫn bằng vector.

**Triển khai theo lô**

- **FR-024**: Track thử MUST được nạp và đo trước; các track còn lại chỉ nạp sau khi DE đã xem số đo và ghi quyết định
  (giữ hay đổi cỡ đoạn, nguồn).
- **FR-025**: Sau khi nạp, DE MUST báo AIE số bản ghi thêm, tên tập dữ liệu, và việc cần làm phía ai-service (bật cờ,
  khởi động lại để nạp kho từ khóa), cùng cập nhật `docs/architecture/data-pipeline.md`, `docs/sprint-plan.md` và
  `specs/README.md`.

### Key Entities

- **Danh sách trang (source manifest)**: file được commit của mỗi lô; mỗi dòng là một trang với nguồn, track, tình
  huống hoặc topic phục vụ, giấy phép và bằng chứng giấy phép, trạng thái (dùng / loại kèm lý do).
- **Nguồn**: một bộ tài liệu (ví dụ tài liệu chính thức của một framework); có tên, giấy phép, kết quả robots, loại
  (chính thức / bổ sung).
- **Trang thô**: nội dung một trang sau crawl, gồm tiêu đề và các section; nằm ngoài git.
- **Đoạn textbook**: đơn vị ghi vào kho; nội dung một ý kèm đường dẫn tiêu đề, phân loại theo category của track, có
  nguồn, giấy phép, danh sách track và tình huống.
- **Tình huống (`scn.*`)**: mục trong catalog ai-service, do AIE sở hữu; spec này chỉ đọc.
- **Kết luận soát**: giữ / sửa / bỏ cho từng đoạn, kèm lý do; đoạn mồi là đoạn nhiễu cài sẵn để kiểm worker.
- **Báo cáo độ phủ**: bảng tình huống × số đoạn × kết quả truy hồi, và bảng nguồn × giấy phép.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 28/28 tình huống trong catalog có ít nhất 1 đoạn được gắn; ít nhất 80% tình huống có từ 3 đoạn trở lên.
- **SC-002**: 6/6 track có ít nhất một nguồn là tài liệu chính thức của công nghệ thuộc track.
- **SC-003**: 100% đoạn trong kho có URL nguồn và giấy phép; 0 đoạn đến từ nguồn không có trong danh sách đã duyệt.
- **SC-004**: Với ít nhất 80% tình huống, truy vấn bằng tiêu đề tình huống trả về một đoạn đã gắn với tình huống đó
  trong ba kết quả đầu.
- **SC-005**: Sau mỗi lần ghi, số bản ghi `interview_qa` và `job_description` không đổi; chạy lại lần hai thêm 0 bản
  ghi.
- **SC-006**: 100% đoạn mồi bị bước soát đánh dấu bỏ; trong mẫu ngẫu nhiên 50 đoạn sau soát do DE đọc, không quá 3 đoạn
  là nhiễu.
- **SC-007**: Lô thử có số đo trước / sau do AIE ghi lại cho phase scenario (tỉ lệ ý có căn cứ, độ trễ lúc bắt đầu
  buổi và theo lượt), và quyết định của DE về việc nạp tiếp được ghi kèm số đo đó.
- **SC-008**: Tổng số đoạn `textbook` nằm trong khoảng 300–1.500; vượt thì DE rà lại danh sách trang trước khi nạp
  thêm.

## Câu hỏi cho AIE (đã có mặc định, không chặn lô thử)

| # | Câu hỏi | Mặc định nếu chưa có trả lời |
|---|---|---|
| 1 | Cỡ đoạn bao nhiêu thì hợp tìm theo lượt? | 80–250 token, tối đa 400 (FR-010) |
| 2 | Ba track backend chung category `Backend`, và mọi track cùng thấy `System Design`: có cần lọc thêm theo track hoặc mã tình huống không? | DE ghi sẵn track và mã tình huống trong metadata (FR-016); AIE dùng hay không tùy số đo |
| 3 | Track nào nạp thử trước? | `java_backend` (4 tình huống; `07-data-storage.md` đã xếp Java/Spring ưu tiên) |
| 4 | Kho từ khóa trong bộ nhớ chịu được thêm bao nhiêu bản ghi? | Trần 1.500 đoạn (SC-008) |
| 5 | Topic nào Planner phải tự đặt câu nhiều nhất? (cho US4) | Chưa có số liệu thì US4 chưa làm |

## Assumptions

- Cách cắt đoạn và cỡ đoạn chốt sau lô thử; đổi cỡ đoạn nghĩa là xử lý và ghi lại lô thử, chấp nhận được vì lô nhỏ.
- Docs giữ nguyên tiếng Anh. Việc khớp với câu trả lời tiếng Việt dựa vào thuật ngữ tiếng Anh ứng viên dùng và bước
  viết lại truy vấn sẵn có của ai-service lúc bắt đầu buổi.
- Docs chỉ làm căn cứ ủng hộ khi chấm; việc cho docs bác ý sai của ứng viên do AIE quyết, ngoài phạm vi spec này.
- Điều khoản của từng nguồn được kiểm và ghi vào danh sách trang trước khi crawl; spec không khẳng định trước giấy phép của
  nguồn nào ngoài System Design Primer (CC-BY-4.0, đã ghi ở 005).
- Việc lặp theo danh sách (kiểm giấy phép, lập danh sách trang, soát đoạn) giao worker theo hướng dẫn cố định; DE duyệt
  kết quả. Mô hình dùng cho worker ghi ở plan.
- Lộ trình học (016) dùng lại được các đoạn này qua URL nguồn; tích hợp vào 016 thuộc spec 016.
- Kho là `ai_db` dùng chung trên Supabase như 005; chi phí embedding cho tối đa 1.500 đoạn ngắn là nhỏ.

## Ngoài phạm vi

- Trang tham chiếu API và tài liệu cho câu dễ / trung bình đã có đáp án trong kho.
- Dịch docs sang tiếng Việt; tự viết nội dung thay cho docs.
- Thay đổi phía ai-service: bật cờ, lọc theo mã tình huống, Evaluator tự tra cứu, cho docs bác ý sai, golden set cho
  truy vấn scenario (AIE sở hữu).
- Viết thêm câu hỏi khó cho kho Q&A (thuộc 005).
- Crawl định kỳ, cập nhật khi docs đổi phiên bản.
