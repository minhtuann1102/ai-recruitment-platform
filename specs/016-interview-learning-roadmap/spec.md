# Feature Specification: Lộ trình học từ kết quả phỏng vấn

**Feature Branch**: `docs/interview-learning-roadmap-spec` (spec, đề xuất); branch code đặt ở plan
(theo `docs/conventions.md`; thư mục spec độc lập với branch)

**Created**: 2026-10-21

**Status**: Draft — chờ AIE đồng ý ranh giới với Reporter (S3-AIE-1) trước `/speckit-clarify`

**Owner**: DE (chính), AIE review — **Sprint**: 3 (09/11 → 23/11/2026)

**Covers**: S3-DE-6 (đề xuất, chưa có trong `docs/sprint-plan.md`); phần `improvements` + `study_plan` của
S3-AIE-1 (chuyển từ AIE sang DE nếu AIE đồng ý)

**Input**: User description: "Feature 016 interview-learning-roadmap (owner DE, AIE review): sau buổi phỏng vấn luyện
tập, một agent có tool (vòng lặp giới hạn) sinh phần `improvements` + `study_plan` của report `/api/finalize` từ kết quả
phỏng vấn (input chính), CV (`cv_profile`, kỹ năng tự khai) và JD (`jd_profile`, tùy chọn). Phân loại kỹ năng 5 nhóm,
lộ trình theo giai đoạn kèm tài liệu (RAG textbook 012 + catalog resources), bài luyện (Q&A 005 độ khó +1), evidence
hoàn thành = phỏng vấn lại đạt ngưỡng; phần dự án intro tách kỹ năng trình bày vs lỗ hổng kỹ thuật map tech→topic_id;
đo chất lượng lộ trình. Tham khảo ý tưởng PathPlannerAI nhưng input là kết quả phỏng vấn."

**Nguồn thiết kế**: cấu trúc report [`docs/ai-service/05`](../../docs/ai-service/05-rubric-and-final-report.md) §6.4,
Reporter [`docs/ai-service/02`](../../docs/ai-service/02-multi-agent-architecture-and-prompts.md) §3.3.5, request
`/api/finalize` [`docs/ai-service/06`](../../docs/ai-service/06-api-contract.md), candidate state và policy
[`docs/ai-service/04`](../../docs/ai-service/04-adaptive-loop-and-candidate-state.md). Spec chỉ ghi phần mới hoặc khác.

**Bối cảnh**: tên đề tài là "AI Agent phỏng vấn", nhưng hiện mọi agent chạy theo luồng do code định sẵn. Feature này
thêm một thành phần **tự quyết các bước tìm kiếm** ở chỗ an toàn nhất: sau buổi, khi điểm đã do code tính và không bị
ép latency. Khác sản phẩm tham khảo (PathPlannerAI: CV + JD → skill gap → roadmap), input chính ở đây là **bằng chứng
ứng viên đã thể hiện trong phỏng vấn**, không chỉ kỹ năng tự khai.

## Clarifications

### Session 2026-10-21

- Q: Phạm vi của DE trong report? → A: `improvements` + `study_plan` và đo chất lượng lộ trình. AIE giữ Evaluator từng
  lượt, phần điểm do code tính, `summary`, `strengths`, `topic_comments`, `turn_comments`.
- Q: Input? → A: kết quả phỏng vấn là input chính; CV (kỹ năng tự khai) và JD (mục tiêu, tùy chọn) là phụ.
- Q: Ai xem lộ trình? → A: chỉ ứng viên (A12: phiên luyện tập riêng tư). Phần dành cho nhà tuyển dụng (chống gian lận,
  tiêu chí riêng của nhà tuyển dụng) ngoài phạm vi.
- Q: Đặt ở Planner hay sau buổi? → A: sau buổi (bước tổng kết). Planner chạy trước khi có kết quả nên không làm được
  lộ trình cải thiện; quyết định sai ở Planner làm hỏng cả buổi, còn lỗi ở bước tổng kết chỉ ảnh hưởng phần nhận xét.
- Q: Có đổi thứ tự phase không? → A: không trong feature này. Luồng `intro → technical → scenario → wrap_up` giữ nguyên;
  đề xuất chọn dự án để hỏi theo điểm yếu gửi AIE riêng.

## User Scenarios & Testing *(mandatory)*

Tác nhân: **ứng viên** (đọc lộ trình sau buổi), **AIE** (tích hợp vào bước tổng kết), **DE** (vận hành, đo chất lượng).

### User Story 1 - Lộ trình cải thiện từ kết quả phỏng vấn (Priority: P1)

Sau buổi, ứng viên mở report và thấy phần "Cần cải thiện" và "Lộ trình học". Mỗi mục nêu một điểm yếu cụ thể kèm lượt
hỏi làm bằng chứng, việc cần làm, tài liệu đọc, câu luyện tập và tiêu chí hoàn thành. Với từng điểm yếu, hệ thống tự
quyết tìm gì, tự đánh giá kết quả có khớp không, chưa khớp thì tìm lại theo cách khác, trong giới hạn số bước và thời
gian.

**Why this priority**: là phần agentic demo được độc lập, không cần CV, JD, textbook (012) hay thay đổi phía FSD.

**Independent Test**: chạy bước tổng kết trên một phiên mẫu có hai topic yếu (đánh giá từng lượt có sẵn) → report có
`improvements` và `study_plan` đúng cấu trúc hiện có; mọi tài liệu và câu luyện truy được về nguồn.

**Acceptance Scenarios**:

1. **Given** phiên có topic yếu kèm hiểu sai được Evaluator ghi nhận, **When** tổng kết, **Then** có mục "cần cải thiện"
   nêu đúng chỗ hiểu sai với lượt bằng chứng tồn tại, và mục lộ trình có việc cần làm, ≥ 1 tài liệu, ≥ 1 câu luyện ở độ
   khó cao hơn mức ứng viên đã đạt một bậc (khi kho có).
2. **Given** kết quả tìm lần đầu không khớp topic, **When** hệ thống tự đánh giá, **Then** nó tìm lại bằng cách khác
   trong giới hạn bước; vẫn không có thì dùng tài liệu của topic trong danh mục và ghi rõ.
3. **Given** tìm kiếm hoặc LLM lỗi, quá giới hạn bước hoặc thời gian, **When** tổng kết, **Then** report vẫn có lộ trình
   theo cách dự phòng (chọn tài liệu từ danh mục topic như hiện nay), phần điểm và phần nhận xét khác không bị ảnh hưởng.
4. **Given** mọi topic đều tốt, **When** tổng kết, **Then** lộ trình đề xuất nâng cao (độ khó cao hơn một bậc), không
   bịa điểm yếu.
5. **Given** buổi kết thúc sớm hoặc < 6 lượt được chấm, **When** tổng kết, **Then** lộ trình chỉ dựa trên topic đã chấm và
   ghi rõ độ tin cậy thấp.

---

### User Story 2 - Phân loại kỹ năng theo bằng chứng (Priority: P2)

Ứng viên thấy kỹ năng của mình chia theo độ chắc của bằng chứng: **đã chứng minh** (thể hiện tốt trong phỏng vấn),
**cần củng cố** (yếu hoặc phải gợi ý), **CV khai nhưng phỏng vấn chưa vững**, **chưa kiểm tra** (CV hoặc JD có nhắc
nhưng buổi này chưa hỏi), **ngoài catalog** (không có dữ liệu để làm lộ trình). Lộ trình xếp ưu tiên theo nhóm này.

**Why this priority**: là điểm khác biệt chính so với cách suy kỹ năng chỉ từ CV, nhưng cần CV và JD có mặt ở bước tổng
kết (đổi contract, xem Phụ thuộc).

**Independent Test**: phiên mẫu có CV khai Kafka với bằng chứng dự án, topic tương ứng yếu, và JD yêu cầu một kỹ năng
không được hỏi → kỹ năng Kafka vào nhóm "CV khai nhưng chưa vững" với ưu tiên cao; kỹ năng JD vào "chưa kiểm tra".

**Acceptance Scenarios**:

1. **Given** topic có điểm cao, **When** phân loại, **Then** vào "đã chứng minh" và không có mục cải thiện.
2. **Given** CV ghi kỹ năng có bằng chứng công việc hoặc dự án, topic tương ứng yếu, **When** phân loại, **Then** vào
   "CV khai nhưng phỏng vấn chưa vững" và được ưu tiên cao hơn topic yếu không khai trong CV.
3. **Given** kỹ năng trong CV hoặc JD map được sang topic nhưng không được hỏi, **When** phân loại, **Then** vào "chưa
   kiểm tra", **không** bị gọi là yếu; lộ trình chỉ gợi ý luyện topic này ở buổi sau.
4. **Given** yêu cầu JD không map được sang topic, **When** phân loại, **Then** vào "ngoài catalog", chỉ liệt kê.
5. **Given** không có CV và JD, **When** phân loại, **Then** chỉ dùng hai nhóm dựa trên phỏng vấn, không lỗi.

---

### User Story 3 - Phần dự án và kinh nghiệm (Priority: P3)

Phase intro hỏi một dự án hoặc kinh nghiệm trong CV. Kết quả phần này được tách hai loại: **kỹ năng trình bày dự án**
(vai trò của mình, lý do chọn công nghệ, kết quả đo được, theo yêu cầu của từng level) và **lỗ hổng kỹ thuật lộ ra khi
kể dự án** (vd kể dùng Kafka nhưng không giải thích được xử lý message trùng).

**Why this priority**: intro chỉ có một topic, trọng số thấp; giá trị cao nhất của nó là bằng chứng cho nhóm "CV khai
nhưng chưa vững" ở US2.

**Independent Test**: phiên mẫu có intro yếu về trình bày và có một hiểu sai kỹ thuật về công nghệ của dự án → hai mục
lộ trình khác loại: một checklist chuẩn bị trình bày, một mục kỹ thuật có tài liệu và câu luyện.

**Acceptance Scenarios**:

1. **Given** intro yếu ở tiêu chí trình bày, **When** tổng kết, **Then** mục lộ trình là việc cần chuẩn bị theo checklist
   của level, không kèm tài liệu kỹ thuật.
2. **Given** lỗ hổng kỹ thuật trong phần dự án và công nghệ map được sang topic, **When** tổng kết, **Then** có mục lộ
   trình kỹ thuật như US1; không map được thì ghi "ngoài catalog".
3. **Given** bất kỳ phiên nào, **When** tổng kết, **Then** không có câu phán xét trung thực về kinh nghiệm ("có thể
   không làm thật"); chỉ mô tả "chưa giải thích được X".
4. **Given** intro dùng câu hỏi chung (không có CV), **When** tổng kết, **Then** chỉ có phần trình bày.

---

### User Story 4 - Đo chất lượng lộ trình (Priority: P2)

DE chạy đánh giá trên một bộ phiên mẫu cố định và nhận báo cáo chỉ số: trích dẫn truy được, vi phạm luật, tỉ lệ dùng dự
phòng, thời gian chạy, và điểm của người chấm; so được lộ trình agent với lộ trình dự phòng.

**Why this priority**: biến "lộ trình hữu ích" thành số liệu cho báo cáo đồ án; chứng minh phần agentic có giá trị hơn
cách hiện có.

**Independent Test**: chạy đánh giá trên bộ phiên mẫu → báo cáo có đủ các chỉ số ở Success Criteria.

**Acceptance Scenarios**:

1. **Given** bộ phiên mẫu, **When** chạy đánh giá, **Then** báo tỉ lệ trích dẫn truy được, số vi phạm từng luật (topic
   chưa hỏi bị gọi yếu, link ngoài nguồn, kết luận tuyển, phán xét trung thực), tỉ lệ dự phòng và thời gian.
2. **Given** hai người chấm, **When** tổng hợp, **Then** báo điểm hữu ích trung bình, độ đồng thuận, và tỉ lệ phiên mà
   lộ trình agent được ưa hơn lộ trình dự phòng (so mù).

---

### User Story 5 - Xác nhận hoàn thành bằng phỏng vấn lại (Priority: P4, Stretch)

Mỗi mục lộ trình có tiêu chí hoàn thành: phỏng vấn lại topic đó và đạt ngưỡng. Khi ứng viên luyện lại, hệ thống tự xác
nhận mục nào đã hoàn thành, thay vì để ứng viên tự đánh dấu.

**Why this priority**: là luận điểm khác biệt mạnh nhất, nhưng cần lưu dữ liệu xuyên phiên ở interview-service và
Planner nhận topic cần tập trung (FSD + AIE).

**Independent Test**: hai phiên liên tiếp cùng ứng viên, phiên hai hỏi lại topic yếu và đạt ngưỡng → mục tương ứng ở
lộ trình phiên một được đánh dấu hoàn thành.

**Acceptance Scenarios**:

1. **Given** lộ trình phiên trước có mục topic X, **When** phiên sau hỏi X và đạt ngưỡng, **Then** mục X được ghi là đã
   hoàn thành kèm phiên làm bằng chứng.

### Edge Cases

- Mọi lượt đều bị chấm lỗi (degraded) → không sinh lộ trình cải thiện, ghi lý do; report vẫn có điểm.
- Ứng viên kết thúc ngay sau intro → chỉ có phần dự án.
- Nhiều điểm yếu trùng tag hoặc trải nhiều topic → gộp thành một mục.
- Hơn 5 điểm yếu → giữ 5 mục ưu tiên cao nhất (giới hạn `improvements` ≤ 5 theo `docs/ai-service/05` §6.4; code
  Reporter trên `main` cắt còn 3 — số cuối chốt với AIE).
- Kho không có câu khó hơn cho topic → câu luyện cùng mức hoặc bỏ, ghi rõ.
- CV hoặc JD chứa chỉ dẫn (prompt injection) → chỉ là dữ liệu, không đổi hành vi hay luật.
- Câu trả lời của ứng viên chứa chỉ dẫn → thành phần lộ trình không bao giờ thấy nguyên văn câu trả lời.
- Track có topic chưa có tài liệu trong danh mục → mục lộ trình chỉ có việc cần làm và câu luyện.
- Textbook (012) chưa index → chỉ dùng danh mục topic và Q&A.

## Requirements *(mandatory)*

### Functional Requirements

**Lộ trình (US1)**

- **FR-001**: Sau khi điểm đã tính, hệ thống MUST sinh `improvements` (≤ 5) và `study_plan` theo cấu trúc report hiện
  có (`docs/ai-service/05` §6.4); feature MUST NOT tính hay sửa điểm.
- **FR-002**: Mỗi mục cần cải thiện MUST dựa trên kết quả đánh giá từng lượt (ý thiếu, hiểu sai, phải gợi ý) và ghi lượt
  bằng chứng tồn tại trong phiên.
- **FR-003**: Mỗi mục lộ trình MUST có: điểm yếu liên quan, mức ưu tiên, việc cần làm hành động được (vd "ôn rollback
  rules với checked exception", không phải "học thêm Spring"), tài liệu, câu luyện tập (khi kho có), tiêu chí hoàn thành.
- **FR-004**: Với từng điểm yếu, hệ thống MUST tự quyết các bước tìm tài liệu và câu luyện: tìm, tự đánh giá độ khớp,
  tìm lại cách khác khi không khớp. Số bước và tổng thời gian MUST có giới hạn cố định, nằm trong ngân sách thời gian
  của bước tổng kết.
- **FR-005**: Mọi tài liệu và câu luyện được trích MUST đến từ kết quả tìm trong kho tri thức hoặc danh mục topic; hệ
  thống MUST NOT tự viết link. Mục trích không truy được MUST bị loại trước khi trả report.
- **FR-006**: Câu luyện MUST lấy từ bộ Q&A cùng topic, độ khó cao hơn mức ứng viên đã đạt một bậc khi có; không có thì
  cùng mức và ghi rõ.
- **FR-007**: Lỗi tìm kiếm, lỗi LLM, vượt giới hạn bước hoặc thời gian, hay output không hợp lệ MUST chuyển về lộ trình
  dự phòng (chọn tài liệu từ danh mục topic như hiện nay). Lỗi ở phần này MUST NOT làm hỏng phần điểm hay phần nhận xét.
- **FR-008**: Thành phần sinh lộ trình MUST NOT nhận nguyên văn câu trả lời của ứng viên; chỉ nhận kết quả đã qua
  Evaluator, hồ sơ CV đã redact (đánh dấu không tin cậy), yêu cầu JD đã trích và danh mục topic (giữ tính chất chống
  injection của Reporter, `docs/ai-service/02` §Reporter).
- **FR-009**: Mỗi lần chạy MUST ghi nhật ký: số bước, các truy vấn đã dùng, id kết quả được chọn, có dùng dự phòng
  không, thời gian. Nhật ký MUST NOT chứa dữ liệu cá nhân.

**Phân loại (US2)**

- **FR-010**: Hệ thống MUST xếp mỗi kỹ năng hoặc topic vào đúng một trong năm nhóm: đã chứng minh, cần củng cố, CV khai
  nhưng phỏng vấn chưa vững, chưa kiểm tra, ngoài catalog.
- **FR-011**: Topic hoặc kỹ năng không được hỏi MUST NOT bị gọi là yếu (BRU-19); nhóm "chưa kiểm tra" chỉ được gợi ý
  luyện ở buổi sau.
- **FR-012**: Thứ tự ưu tiên MUST xác định bằng luật, không do LLM tự đặt: yêu cầu JD `must` > `nice` > còn lại; cùng mức
  thì hiểu sai > thiếu ý > phải gợi ý; "CV khai nhưng chưa vững" được nâng một bậc; hòa thì theo level của topic.
- **FR-013**: Ánh xạ kỹ năng trong CV hoặc công nghệ của dự án sang topic MUST tất định và kiểm tra được; không map được
  thì vào "ngoài catalog".
- **FR-014**: Không có CV và JD → chỉ dùng hai nhóm dựa trên phỏng vấn, không lỗi.

**Dự án (US3)**

- **FR-015**: Kết quả phase intro MUST tách (a) kỹ năng trình bày, chấm theo hàng "Dự án" của rubric theo level
  (`docs/ai-service/05`), cho ra việc cần chuẩn bị theo checklist của level; (b) lỗ hổng kỹ thuật, map sang topic theo
  FR-013, cho ra mục lộ trình như FR-003.
- **FR-016**: Lộ trình MUST NOT phán xét trung thực của kinh nghiệm; chỉ mô tả điều ứng viên chưa giải thích được.
- **FR-017**: Dự án hoặc kinh nghiệm trong CV không được hỏi MUST vào "chưa kiểm tra".

**Ràng buộc chung**

- **FR-018**: Lộ trình chỉ hiển thị cho ứng viên (A12); MUST NOT có kết luận tuyển hay không tuyển, hay % phù hợp CV–JD
  (BR-23).
- **FR-019**: Lộ trình viết tiếng Việt, giữ thuật ngữ tiếng Anh, cùng giọng văn với Reporter.
- **FR-020**: Report có trường mới (nhóm kỹ năng, câu luyện, tiêu chí hoàn thành) hay không: [NEEDS CLARIFICATION: v1
  được thêm trường mới vào report (tăng `schema_version`, FE ở 013 hiển thị) hay phải gói gọn trong cấu trúc hiện có
  (đưa vào `actions` dạng chữ)?]

**Đo chất lượng (US4)**

- **FR-021**: MUST có cách chạy đánh giá trên một bộ phiên mẫu cố định, báo các chỉ số ở SC-001 đến SC-007; bộ phiên mẫu
  MUST NOT chứa dữ liệu ứng viên thật.
- **FR-022**: Đánh giá thủ công MUST có hai người chấm theo thang 1–5 (đúng điểm yếu, cụ thể, khả thi), so mù lộ trình
  agent với lộ trình dự phòng.

**Hoàn thành (US5)**

- **FR-023**: Mỗi mục lộ trình MUST nêu tiêu chí hoàn thành: phỏng vấn lại topic đó và đạt ngưỡng (xem Assumptions).
- **FR-024**: Xác nhận hoàn thành xuyên phiên: [NEEDS CLARIFICATION: thuộc feature này (cần interview-service lưu lộ
  trình phiên trước và Planner nhận topic cần tập trung) hay feature này chỉ nêu tiêu chí, phần xác nhận để Stretch?]

### Key Entities

- **Kết quả phỏng vấn** (input chính): đánh giá từng lượt (band 4 tiêu chí, ý đã nêu, ý thiếu, hiểu sai, tag điểm
  mạnh/yếu, có gợi ý không), điểm từng topic, plan (topic, nguồn `cv | catalog | scenario | generic`, tham chiếu CV).
- **Hồ sơ CV** (đã redact, không tin cậy): kỹ năng kèm loại bằng chứng (`work | project | education | listed`), dự án và
  kinh nghiệm kèm công nghệ.
- **Yêu cầu JD**: `must` / `nice`, mỗi yêu cầu map sang topic hoặc `out_of_catalog`.
- **Nhóm kỹ năng**: topic hoặc kỹ năng, nhóm (FR-010), bằng chứng.
- **Mục cần cải thiện**: điểm yếu, lý do, lượt bằng chứng.
- **Mục lộ trình**: điểm yếu, ưu tiên, việc cần làm, tài liệu (id truy được), câu luyện (id cặp Q&A), tiêu chí hoàn
  thành.
- **Nhật ký chạy**: số bước, truy vấn, id được chọn, dự phòng, thời gian.
- **Bộ phiên mẫu đánh giá**: phiên giả lập (giỏi / trung bình / yếu, nhiều track) kèm đánh giá từng lượt.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% tài liệu và câu luyện trong lộ trình truy được về kết quả tìm kiếm hoặc danh mục topic; 0 link do hệ
  thống tự viết.
- **SC-002**: 0 vi phạm trên bộ phiên mẫu cho cả ba luật: topic chưa hỏi bị gọi yếu, kết luận tuyển hoặc % phù hợp,
  phán xét trung thực.
- **SC-003**: 100% lần gây lỗi giả (tìm kiếm lỗi, LLM lỗi, quá thời gian) vẫn ra report có lộ trình hợp lệ.
- **SC-004**: Ở 95% số buổi, ứng viên nhận report đầy đủ, kể cả lộ trình, trong ngân sách hiện có của bước tổng kết
  (90 giây).
- **SC-005**: ≥ 90% điểm yếu có bằng chứng (hiểu sai hoặc trả lời yếu) thuộc 5 ưu tiên cao nhất có mục lộ trình tương
  ứng.
- **SC-006**: Trên ≥ 12 phiên mẫu (giỏi / trung bình / yếu × ≥ 2 track), điểm hữu ích trung bình của hai người chấm
  ≥ 4/5.
- **SC-007**: Khi so mù, lộ trình agent được ưa hơn lộ trình dự phòng ở ≥ 70% số phiên mẫu.

## Assumptions

- **Ngưỡng hoàn thành**: band ≥ 3.0 trên thang 0–4 của Evaluator (ngưỡng "strong" của policy); khác thang điểm topic
  0–10 hiển thị trong report.
- **Thứ tự học**: theo `levels` của topic trong danh mục; nếu AIE thêm trường tiên quyết vào danh mục thì dùng thêm.
- **Textbook**: v1 chạy không cần 012 (danh mục topic + Q&A 005); textbook bổ sung khi 012 index xong.
- **Checklist trình bày dự án** theo level do DE soạn, AIE duyệt, bám hàng "Dự án" của rubric.
- **Vị trí chạy**: trong bước tổng kết, sau khi code tính điểm, song song với Reporter của AIE.
- **Bộ phiên mẫu**: dùng ứng viên giả lập tầng 3 của AIE (`docs/ai-service/09`); chưa có thì DE dựng phiên mẫu từ
  đánh giá có sẵn.
- **Người chấm thứ hai**: một thành viên khác của team (như golden set của 005).
- **Model**: LLM và embedding mặc định theo constitution IV.

### Phụ thuộc

- **AIE (ranh giới)**: Reporter thôi sinh `improvements` / `study_plan`, hoặc phần của 016 ghi đè; cập nhật
  `docs/ai-service/02` §3.3.5 và `05` §6.4 (tài liệu của AIE, 016 không tự sửa).
  **Hiện trạng 2026-10-24** (PR #22 merged 2026-10-22): Reporter LLM trên `main` đã sinh `improvements` (code cắt ≤ 3,
  có `evidence_turns`) và `study_plan` (≤ 3 mục: `topic`, `priority` `high | medium`, `actions` 2–3 việc, không URL),
  có bản dự phòng tính bằng code (`apps/ai-service/app/report_scoring.py`). 016 vì vậy là **thay / nâng cấp** phần này
  (vòng tool có RAG + tài liệu + câu luyện), không thêm mới; bản dự phòng của AIE giữ làm fallback.
- **AIE + FSD (contract)**: request `/api/finalize` đã có `jd_profile` (FR-AI-056, PR #22, dùng cho khối
  `requirements`) nhưng chưa có `cv_profile` (chỉ gửi ở `/api/start`). US2, US3 cần thêm `cv_profile` vào request
  `/api/finalize`: đổi `docs/ai-service/06` và interview-service cùng PR (constitution III). US1 không cần.
- **AIE (đường đọc RAG, S1-AIE-2)**: tìm kiếm dùng đường đọc của AIE; 016 không viết đường đọc riêng.
- **005**: Q&A đã index, có câu khó cho các topic middle/senior (T057).
- **012** (tùy chọn): textbook.
- **FSD (013)**: hiển thị trường mới nếu FR-020 cho phép.
- **AIE (tầng 3)**: ứng viên giả lập cho US4.

### Ngoài phạm vi

- Phần dành cho nhà tuyển dụng: chống gian lận (S5-8), tiêu chí riêng của nhà tuyển dụng, chia sẻ kết quả (A12).
- Theo dõi tiến độ dài hạn và trang tiến độ riêng.
- Ưu tiên theo nhu cầu thị trường tính từ JD crawl (009): hướng sau.
- Đổi thứ tự phase, chọn dự án để hỏi theo điểm yếu: đề xuất riêng gửi AIE.
- Fine-tune, học tăng cường (README ai-service §1.4).
- Điểm % phù hợp CV–JD.
