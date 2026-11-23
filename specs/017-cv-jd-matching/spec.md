# Feature Specification: Gợi ý việc làm theo độ tương đồng CV–JD

**Feature Branch**: `docs/cv-jd-matching-spec` (spec); branch code đặt ở plan (theo `docs/conventions.md`; thư mục spec
độc lập với branch)

**Created**: 2026-11-21

**Status**: Draft — FR-018, FR-025 chốt 2026-11-21; AIE đồng ý dùng `knowledge_chunks` 2026-11-22 (Phụ thuộc)

**Owner**: DE (chính), AIE review phần trong `apps/ai-service` — **Sprint**: 4 (23/11 → 07/12/2026), **Stretch**

**Covers**: S2-DE-3 (Index JD vào ai_db, Stretch) mở rộng thành gợi ý CV–JD. Đảo quyết định 009 NC-2 ("JD không
embed", 2026-10-24) với lý do mới: JD được embed để **gợi ý việc làm**, vẫn **không** vào RAG phỏng vấn.

**Input**: User description: "Gợi ý việc làm / ứng viên dựa trên độ tương đồng CV–JD, không dùng GNN/GCN hay
collaborative filtering (chưa có dữ liệu tương tác). GĐ1 (DE làm, không phụ thuộc FSD): lõi tính điểm trong ai-service,
lọc cứng track / level ±1 / còn hạn, score = 0.6·cosine + 0.3·skill_match + 0.1·level_fit (trọng số trong config), kỹ
năng chuẩn hóa theo danh mục của 009, embedding cùng model RAG lưu ở ai_db, idempotent theo content hash, embedding giả
tất định cho CI, endpoint nội bộ X-Internal-Token trả top-K kèm matched/missing skills và từng thành phần điểm; bộ đánh
giá 20–30 CV + ~30 JD tổng hợp có nhãn, P@5 / nDCG@5 so baseline chỉ-skill, đo p50/p95 và chi phí. GĐ2 (chờ FSD
007/008/013): endpoint public qua job-service/APISIX có RBAC Candidate/Employer, đồng bộ khi Job duyệt / CV upload,
cache Redis, màn hình Employer; liên kết luyện phỏng vấn theo JD dùng missing_skills. Kết quả luyện phỏng vấn không
dùng để xếp hạng hay hiển thị cho Employer."

**Nguồn thiết kế**: bản ghi JD chuẩn hóa và danh mục kỹ năng của 009
([`contracts/jd-record-formats.md`](../009-jd-crawling-seeding/contracts/jd-record-formats.md)), bảng
`knowledge_chunks` ([`docs/architecture/data-model.md`](../../docs/architecture/data-model.md) §5,
[`rag-design.md`](../../docs/architecture/rag-design.md)), `CvProfile` / CV Parser
([`docs/ai-service/02`](../../docs/ai-service/02-multi-agent-architecture-and-prompts.md) §3.3.1), contract nội bộ
ai-service ([`docs/ai-service/06`](../../docs/ai-service/06-api-contract.md)). Spec chỉ ghi phần mới hoặc khác.

**Bối cảnh**: phần "tuyển dụng" của đề tài chưa có thành phần AI nào; phần AI hiện chỉ ở phỏng vấn luyện tập. Hệ
thống chưa có dữ liệu tương tác (xem, lưu, ứng tuyển) nên không dùng lọc cộng tác hay mô hình đồ thị; gợi ý dựa trên
nội dung CV và JD. Hiện trạng 2026-11-21: job-service, applications, interview-service và web chưa có trên `main` hay
branch nào, nên feature chia hai giai đoạn: **GĐ1** chạy được và đo được chỉ với ai-service + dữ liệu 009; **GĐ2** nối
vào sản phẩm khi FSD có 007 / 008 / 013.

## Clarifications

### Session 2026-11-21

- Q: Hiển thị điểm phù hợp? → A: ứng viên thấy điểm (tổng và thành phần); nhà tuyển dụng **không thấy điểm và không
  thấy thứ hạng**, chỉ thấy kỹ năng khớp / thiếu, danh sách theo thứ tự trung tính. Điểm không bao giờ vào report luyện
  tập.
- Q: Nhà tuyển dụng thấy ứng viên nào (GĐ2)? → A: ứng viên đã ứng tuyển tin đó **và** ứng viên bật `is_open_to_work`
  (cần "CV mặc định" ở phía FSD).

## User Scenarios & Testing *(mandatory)*

Tác nhân: **ứng viên** (xem việc phù hợp), **nhà tuyển dụng** (xem ứng viên phù hợp, GĐ2), **job-service** (gọi lõi gợi
ý, GĐ2), **DE** (index, vận hành, đánh giá).

### User Story 1 - Index JD để gợi ý (Priority: P1, GĐ1)

DE chạy lệnh index trên tập JD đã chuẩn hóa của 009. Mỗi JD có một bản tóm tắt có cấu trúc được embed và lưu kèm thông
tin lọc (track, level, hạn nộp, kỹ năng). Chạy lại trên cùng dữ liệu không tốn thêm lượt embed và không sinh bản trùng;
JD đổi nội dung thì được embed lại; JD bị bỏ khỏi tập thì bị gỡ khỏi chỉ mục.

**Why this priority**: không có chỉ mục JD thì không có gợi ý; là phần thuần DE, không cần ai khác.

**Independent Test**: index 365 JD của 009 → chỉ mục có 1 bản ghi cho mỗi JD đủ điều kiện, thống kê in số vào / số embed
/ số bỏ qua; chạy lại ngay → 0 lượt embed, số bản ghi không đổi.

**Acceptance Scenarios**:

1. **Given** tập JD 009, **When** index lần đầu, **Then** mỗi JD có track xác định được có đúng một bản ghi với vector,
   model embedding, track, level, hạn nộp, danh sách kỹ năng; JD không có track bị bỏ qua và được đếm trong thống kê.
2. **Given** chỉ mục đã có, **When** chạy lại với dữ liệu không đổi, **Then** 0 lượt gọi embedding, 0 bản ghi mới.
3. **Given** một JD đổi mô tả, **When** chạy lại, **Then** chỉ JD đó được embed lại và bản cũ bị thay.
4. **Given** chỉ mục đã có JD, **When** truy vấn RAG của phỏng vấn (Q&A, textbook), **Then** không bao giờ trả bản ghi JD.

---

### User Story 2 - Gợi ý việc làm từ CV (Priority: P1, GĐ1)

Một dịch vụ nội bộ gửi hồ sơ CV đã phân tích (kết quả CV Parser hiện có), track mục tiêu và (tùy chọn) level mục tiêu.
Hệ thống trả danh sách JD phù hợp nhất, mỗi JD kèm điểm tổng, từng thành phần điểm, kỹ năng khớp và kỹ năng còn thiếu.
Ở GĐ1 người gọi là script demo / trang dev; ở GĐ2 là job-service.

**Why this priority**: là giá trị chính của feature, demo được ngay trên dữ liệu 009 mà không cần FSD.

**Independent Test**: gửi một CV backend Java mức middle với as-of cố định → nhận ≤ K JD cùng track, level lệch ≤ 1 bậc,
còn hạn tại as-of, xếp theo điểm giảm dần; mỗi JD có `matched_skills`, `missing_skills` khớp đúng công thức.

**Acceptance Scenarios**:

1. **Given** CV và track mục tiêu, **When** gọi gợi ý, **Then** mọi JD trả về cùng track, còn hạn tại as-of, lệch level
   tối đa N bậc (mặc định 1, cấu hình được).
2. **Given** kết quả, **When** kiểm tra một JD bất kỳ, **Then** điểm tổng = w1·cosine + w2·skill_match + w3·level_fit
   với trọng số đang cấu hình, và skill_match = số kỹ năng khớp / số kỹ năng của JD.
3. **Given** CV ghi "Spring Boot", "springboot", "spring-boot", **When** chuẩn hóa, **Then** cả ba thành một kỹ năng và
   khớp với JD yêu cầu Spring Boot.
4. **Given** dịch vụ embedding lỗi hoặc quá hạn, **When** gọi gợi ý, **Then** vẫn trả kết quả chỉ từ skill_match và
   level_fit, có cờ báo đã giảm chất lượng, không lỗi 500.
5. **Given** không JD nào qua lọc cứng, **When** gọi gợi ý, **Then** trả danh sách rỗng kèm tổng 0, không lỗi.
6. **Given** chạy ở chế độ mock (không có khóa embedding), **When** gọi hai lần cùng input, **Then** hai kết quả giống hệt
   nhau và có cờ mock.

---

### User Story 3 - Đánh giá chất lượng gợi ý (Priority: P2, GĐ1)

DE chạy một lệnh đánh giá trên bộ dữ liệu cố định (CV tổng hợp + JD thật của 009 có nhãn mức liên quan) và nhận bảng
markdown: Precision@5, nDCG@5 của cách tính đầy đủ so với baseline chỉ so kỹ năng (và chỉ cosine), độ trễ p50 / p95,
chi phí embedding. Bảng dùng trực tiếp cho báo cáo đồ án.

**Why this priority**: biến "gợi ý hợp lý" thành số liệu; chứng minh phần embedding có đóng góp so với so kỹ năng.

**Independent Test**: chạy lệnh đánh giá → file markdown có đủ các chỉ số ở SC-001 đến SC-003, kèm mô tả bộ dữ liệu
(số CV, số JD, số cặp có nhãn, ngày as-of, model embedding).

**Acceptance Scenarios**:

1. **Given** bộ dữ liệu có nhãn, **When** chạy đánh giá, **Then** báo P@5 và nDCG@5 trung bình trên các CV cho ít nhất
   ba cách: đầy đủ, chỉ skill_match, chỉ cosine.
2. **Given** chạy đánh giá ở chế độ mock, **When** bắt đầu, **Then** lệnh từ chối chạy (số đo trên vector giả vô nghĩa).
3. **Given** chạy đánh giá hai lần trên cùng dữ liệu, **When** so bảng, **Then** chỉ số chất lượng giống nhau.

---

### User Story 4 - Ứng viên xem "Việc làm phù hợp" trên web (Priority: P3, GĐ2)

Ứng viên đã đăng nhập mở trang "Việc làm phù hợp" và thấy danh sách tin đã duyệt, còn hạn, phù hợp CV của mình, mỗi tin
có lý do (kỹ năng khớp, kỹ năng còn thiếu), có phân trang.

**Why this priority**: cần job-service, CV lưu trữ và web của FSD (007, 008, 013).

**Independent Test**: ứng viên có CV, hệ thống có tin đã duyệt cùng track → trang trả danh sách có phân trang; ứng viên
khác không xem được gợi ý của người này.

**Acceptance Scenarios**:

1. **Given** ứng viên có CV, **When** mở trang, **Then** thấy tin đã duyệt, còn hạn, theo thứ tự điểm, kèm lý do.
2. **Given** ứng viên chưa có CV, **When** mở trang, **Then** thấy hướng dẫn tải CV, không lỗi.
3. **Given** tin bị đóng, hết hạn hoặc bị gỡ duyệt, **When** ứng viên mở lại trang, **Then** tin đó không còn xuất hiện.

---

### User Story 5 - Nhà tuyển dụng xem "Ứng viên phù hợp" cho tin của mình (Priority: P3, GĐ2)

Nhà tuyển dụng mở một tin của mình và thấy các ứng viên trong phạm vi được phép (FR-025) đã qua lọc cứng với tin, mỗi
người kèm kỹ năng khớp và còn thiếu. Nhà tuyển dụng **không** thấy điểm hay thứ hạng (FR-018).

**Why this priority**: cần dữ liệu ứng tuyển, CV và "CV mặc định" phía FSD (008, 004).

**Independent Test**: tin có ba ứng viên đã ứng tuyển và một ứng viên bật `is_open_to_work` cùng track → nhà tuyển dụng
sở hữu tin thấy bốn người theo thứ tự trung tính, không có số điểm; nhà tuyển dụng khác bị từ chối.

**Acceptance Scenarios**:

1. **Given** tin thuộc nhà tuyển dụng A, **When** A mở danh sách ứng viên phù hợp, **Then** chỉ thấy ứng viên trong phạm
   vi FR-025, mỗi người có kỹ năng khớp / thiếu, không có điểm, không có số thứ hạng, thứ tự không theo điểm.
2. **Given** ứng viên tắt `is_open_to_work` và chưa ứng tuyển tin của A, **When** A mở danh sách, **Then** không thấy
   ứng viên đó.
3. **Given** nhà tuyển dụng B, **When** mở danh sách của tin thuộc A, **Then** bị từ chối.
4. **Given** ứng viên đã luyện phỏng vấn, **When** A xem danh sách, **Then** không thấy bất kỳ dữ liệu luyện tập nào và
   thứ hạng không đổi so với khi ứng viên chưa luyện.

---

### User Story 6 - Luyện phỏng vấn theo một tin (Priority: P4, GĐ2, tùy chọn)

Từ một tin được gợi ý, ứng viên bấm "Luyện phỏng vấn cho vị trí này"; buổi luyện tập dùng JD của tin đó và ưu tiên các
kỹ năng còn thiếu.

**Why this priority**: ai-service đã nhận JD cho buổi luyện tập (BR-23); phần còn lại là nối giao diện và interview-
service, không thuộc DE.

**Independent Test**: bắt đầu buổi từ một tin có `missing_skills` → plan của buổi có topic tương ứng các kỹ năng thiếu map
được về catalog.

**Acceptance Scenarios**:

1. **Given** tin có kỹ năng thiếu map được về topic, **When** bắt đầu buổi, **Then** các topic đó được ưu tiên.

### Edge Cases

- CV không có kỹ năng nào nhận diện được → skill_match = 0 với mọi JD; kết quả chỉ theo cosine và level, có ghi chú.
- JD không có kỹ năng nhận diện được (5/365 bản ghi 009) → skill_match = 0, ghi chú "JD không nêu kỹ năng".
- JD không có level (37/365) → không bị lọc theo level, level_fit = 0,5.
- JD không có track (5/365) hoặc track `mobile_fullstack` (20/365, chưa có track phỏng vấn tương ứng) → không gợi ý được
  qua track mục tiêu hiện có; ghi trong thống kê index.
- 218/365 JD 009 đã hết hạn tại 2026-11-21 → lọc "còn hạn" theo ngày as-of; demo và đánh giá dùng as-of cố định.
- Kỹ năng CV ngoài danh mục → bỏ khỏi so khớp, đếm vào `unknown_skills_count` (không trả tên, tránh lộ dữ liệu CV thô).
- Trọng số cấu hình không cộng bằng 1 hoặc âm → service từ chối khởi động với lỗi cấu hình rõ ràng.
- Chỉ mục có vector của model embedding khác model đang cấu hình → chỉ so vector cùng model; lệch thì báo cần index lại.
- CV hoặc JD chứa chỉ dẫn (prompt injection) → không ảnh hưởng: phần gợi ý không gọi LLM sinh văn bản.
- K hoặc trang vượt giới hạn → 422 với mã lỗi, không cắt ngầm.

## Requirements *(mandatory)*

### Functional Requirements

**Index JD (US1)**

- **FR-001**: Mỗi JD MUST có đúng một bản ghi chỉ mục, nội dung embed là bản tóm tắt có cấu trúc dựng tất định từ trường
  đã chuẩn hóa của 009 (tiêu đề, level, nhóm, phần yêu cầu / công việc cắt ngắn); MUST NOT embed toàn văn JD. Danh sách
  kỹ năng **không** đưa vào văn bản embed (ở cả JD và CV) để cosine không lặp lại skill_match (research R4).
- **FR-002**: Vector JD MUST dùng cùng model và số chiều với RAG (constitution IV) và lưu tên model; so khớp MUST chỉ so
  vector cùng model.
- **FR-003**: Index MUST idempotent theo content hash: dữ liệu không đổi → 0 lượt embed, 0 bản trùng; nội dung đổi → embed
  lại và thay bản cũ; JD không còn trong tập nguồn → gỡ khỏi chỉ mục.
- **FR-004**: Bản ghi JD MUST nằm trong kho tri thức hiện có với loại nguồn `job_description` (constitution V), kèm thông
  tin lọc: mã JD, track, level, hạn nộp, danh sách kỹ năng (slug), cờ synthetic. Mọi truy vấn RAG của phỏng vấn MUST NOT
  trả bản ghi loại này (có test).
- **FR-005**: Mỗi lần index MUST in thống kê: số JD vào, số embed mới, số bỏ qua do không đổi, số bị loại (thiếu track),
  số gỡ, số lỗi embedding (constitution V).

**Gợi ý (US2)**

- **FR-006**: Endpoint nội bộ MUST nhận: hồ sơ CV theo cấu trúc CV Parser hiện có, track mục tiêu (bắt buộc, theo track
  phỏng vấn), level mục tiêu (tùy chọn), ngày as-of (tùy chọn, mặc định hôm nay), trang và kích thước trang. Endpoint
  MUST yêu cầu `X-Internal-Token` như các endpoint nội bộ khác.
- **FR-007**: Lọc cứng trước khi tính điểm: cùng track; hạn nộp ≥ as-of; lệch level ≤ N bậc (mặc định 1, cấu hình được),
  JD không có level thì không lọc theo level; chỉ JD trong chỉ mục (GĐ1: mọi JD 009 coi là đã duyệt; GĐ2: chỉ mục chỉ
  chứa tin đã duyệt, FR-022).
- **FR-008**: Điểm = w1·cosine(CV, JD) + w2·skill_match + w3·level_fit; mặc định 0,6 / 0,3 / 0,1, đặt trong cấu hình;
  trọng số MUST ≥ 0 và cộng bằng 1. cosine kẹp về [0, 1].
- **FR-009**: Kỹ năng JD = danh sách slug của bản ghi 009 (mọi kỹ năng nhận diện trong tiêu đề, mô tả, thẻ; 009 không tách
  bắt buộc / ưu tiên). Kỹ năng CV = tên kỹ năng, công nghệ trong kinh nghiệm và dự án của hồ sơ CV, chuẩn hóa qua **cùng
  danh mục kỹ năng của 009** (bí danh, không phân biệt hoa thường). skill_match = |JD ∩ CV| / |JD|; JD rỗng → 0.
- **FR-010**: level_fit = 1 khi cùng bậc, 0,5 khi lệch 1 bậc, 0 khi lệch hơn; JD không có level → 0,5. Bậc theo bảng
  thứ tự ở Assumptions. Level ứng viên = level mục tiêu nếu có, không thì suy từ số năm kinh nghiệm theo cùng ngưỡng 009.
- **FR-011**: Vector CV MUST tính theo cùng cách dựng tóm tắt (FR-001) từ hồ sơ CV và MUST NOT lưu (ai-service stateless,
  constitution IV); nội dung CV MUST NOT ghi log, chỉ ghi số lượng và độ trễ.
- **FR-012**: Mỗi kết quả MUST có: mã JD, tiêu đề, track, level, điểm tổng, ba thành phần điểm, `matched_skills`,
  `missing_skills` (tên hiển thị). Phản hồi MUST có: tổng số JD qua lọc, trang, as-of, trọng số dùng, model embedding,
  số kỹ năng CV ngoài danh mục, cờ `degraded` và cờ `mock`.
- **FR-013**: Thứ tự MUST tất định: điểm giảm dần, hòa thì theo mã JD; tổng số kết quả trả tối đa M (mặc định 50).
- **FR-014**: Lỗi embedding hoặc quá hạn MUST chuyển sang điểm không có cosine (chuẩn hóa lại w2, w3 cho cộng bằng 1),
  bật `degraded`; lỗi chỉ mục (không đọc được DB) MUST trả lỗi theo format lỗi nội bộ hiện có của ai-service.
- **FR-015**: Chế độ mock (bật cờ mock) MUST dùng vector giả tất định cùng số chiều, sinh từ nội dung, trên một chỉ mục
  JD mẫu nhỏ nằm trong code; vector giả MUST NOT được ghi vào ai_db. Không bật mock mà thiếu khóa embedding → kết quả
  `degraded` (FR-014).
- **FR-016**: Lỗi đầu vào MUST trả 422 với mã lỗi riêng: track không hợp lệ, level không hợp lệ, trang hoặc kích thước
  trang ngoài giới hạn, as-of sai định dạng.

**Ràng buộc chung**

- **FR-017**: Kết quả luyện phỏng vấn (điểm, report, lộ trình) MUST NOT là đầu vào tính điểm và MUST NOT hiển thị cho
  nhà tuyển dụng (BRU-10, A12).
- **FR-018**: Ứng viên MAY thấy điểm tổng và ba thành phần trên trang gợi ý của mình. Phần dành cho nhà tuyển dụng MUST
  NOT chứa điểm, thành phần điểm hay số thứ hạng, và thứ tự hiển thị MUST NOT theo điểm (vd theo thời gian ứng tuyển);
  chỉ có kỹ năng khớp / thiếu. Điểm MUST NOT xuất hiện trong report luyện tập (016 FR-018).

**Đánh giá (US3)**

- **FR-019**: Bộ đánh giá MUST gồm 20–30 CV tổng hợp (không dùng dữ liệu cá nhân thật, chỉ ghi vào repo bản đã soát) và
  ≥ 30 JD thật lấy từ 009, chọn sao cho mỗi CV có ≥ 10 JD qua lọc cứng tại as-of cố định của bộ đánh giá.
- **FR-020**: Mỗi cặp CV × JD qua lọc cứng MUST có nhãn mức liên quan 0 / 1 / 2 (không / một phần / phù hợp), gán trước
  khi xem kết quả của hệ thống; ghi người gán.
- **FR-021**: Lệnh đánh giá MUST tính P@5 (liên quan = nhãn ≥ 1) và nDCG@5 (theo nhãn 0 / 1 / 2) cho cách đầy đủ, chỉ
  skill_match, chỉ cosine; đo độ trễ p50 / p95 cho (a) tính điểm khi đã có vector và (b) toàn bộ yêu cầu gồm embed CV; báo
  số token và chi phí embedding cho index toàn bộ JD và cho mỗi yêu cầu; xuất bảng markdown. MUST từ chối chạy ở chế độ mock.

**GĐ2 (chờ FSD; contract viết sẵn trong plan, giao FSD)**

- **FR-022**: job-service MUST đồng bộ chỉ mục: thêm / cập nhật khi tin được duyệt hoặc sửa, gỡ khi tin bị đóng, hết hạn
  hoặc bị gỡ duyệt.
- **FR-023**: Endpoint public qua APISIX MUST có RBAC: Candidate chỉ xem gợi ý của chính mình; Employer chỉ xem ứng viên
  phù hợp cho tin của mình (constitution II).
- **FR-024**: Kết quả gợi ý MAY được cache theo (người dùng | tin) có thời hạn; cache MUST bị xóa khi CV hoặc tin đổi.
- **FR-025**: Nhà tuyển dụng chỉ thấy (a) ứng viên đã ứng tuyển tin đó và (b) ứng viên bật `is_open_to_work` có CV mặc
  định, qua lọc cứng với tin. Ứng viên tắt `is_open_to_work` MUST biến khỏi nhóm (b) ngay lần xem sau. FSD cần thêm "CV
  mặc định" cho ứng viên (004 / 008).
- **FR-027**: Nhóm (b) cần vector CV lưu sẵn (không thể embed mọi ứng viên mỗi lần xem). **Chốt 2026-11-23: lưu ở DB
  của service sở hữu CV** (cùng `cv_profile`), không lưu ở ai_db nên không cần sửa constitution IV; GĐ1 không lưu vector
  CV (FR-011). Chi tiết đường ghi (ai embed, lúc nào) chốt ở plan GĐ2.
- **FR-026** *(tùy chọn)*: Bắt đầu buổi luyện tập từ một tin MUST truyền JD của tin và danh sách kỹ năng thiếu để Planner
  ưu tiên (US6).

### Key Entities

- **Bản ghi JD trong chỉ mục**: mã JD (GĐ1: mã 009; GĐ2: mã tin của job-service), vector, model embedding, content hash,
  track, level, hạn nộp, kỹ năng (slug), cờ synthetic.
- **Hồ sơ CV** (đầu vào, không lưu): kỹ năng, công nghệ trong kinh nghiệm và dự án, số năm kinh nghiệm, tiêu đề.
- **Danh mục kỹ năng**: slug, tên hiển thị, bí danh, nhóm (của 009).
- **Kết quả gợi ý**: mã JD, điểm tổng, ba thành phần, kỹ năng khớp, kỹ năng thiếu.
- **Bộ đánh giá**: CV tổng hợp, JD chọn từ 009, nhãn CV × JD (0 / 1 / 2), as-of, người gán.
- **Báo cáo đánh giá**: chỉ số theo từng cách tính, độ trễ, chi phí, mô tả bộ dữ liệu.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Trên bộ đánh giá, cách tính đầy đủ có nDCG@5 cao hơn baseline chỉ so kỹ năng; báo trung thực cả khi không
  đạt (kèm phân tích lỗi trên vài CV).
- **SC-002**: Khi vector JD đã có, 95% yêu cầu gợi ý trên toàn bộ chỉ mục 009 hoàn tất phần tính điểm trong ≤ 500 ms;
  thời gian toàn bộ yêu cầu (gồm embed CV) được đo và báo.
- **SC-003**: Chi phí embedding cho index toàn bộ JD và cho mỗi yêu cầu được báo bằng số token và tiền.
- **SC-004**: 100% kết quả trên bộ đánh giá thỏa lọc cứng (track, hạn, level) và có `matched_skills` / `missing_skills`
  khớp với skill_match.
- **SC-005**: Index lại dữ liệu không đổi tốn 0 lượt embed và không sinh bản trùng.
- **SC-006**: 0 truy vấn RAG phỏng vấn trả bản ghi JD (test tự động).
- **SC-007**: CI chạy toàn bộ test của feature không cần khóa API; cùng input ở chế độ mock cho kết quả giống hệt.

## Assumptions

- **Bảng bậc level** (dùng cho lọc và level_fit): Intern = 0; Junior / fresher / junior = 1 (009 gộp fresher vào
  Junior); Mid / middle = 2; Senior / senior = 3; Lead = 4; Manager = 5. JD không có level: không lọc, level_fit = 0,5.
- **Ánh xạ track phỏng vấn → nhóm JD của 009**: `java_backend`, `nodejs_backend`, `python_backend` → `backend`;
  `frontend_react` → `frontend`; `devops_engineer` → `devops`; `ai_engineer` → `ai_data`. Nhóm `mobile_fullstack` chưa
  có track phỏng vấn nên chưa được gợi ý.
- **Suy level từ số năm** (khi không có level mục tiêu): cùng ngưỡng `level_from_years` của 009 (< 3 năm Junior, < 5 Mid,
  còn lại Senior).
- **As-of**: mặc định ngày hiện tại; demo GĐ1 và bộ đánh giá dùng một ngày cố định ghi trong dữ liệu đánh giá.
- **Người gán nhãn**: DE gán; nếu có người thứ hai (FSD hoặc AIE) thì báo thêm độ đồng thuận. Một người gán là hạn chế
  ghi rõ trong báo cáo (dễ lạc quan vì cùng người viết CV tổng hợp và gán nhãn).
- **Không dùng LLM sinh văn bản** trong gợi ý; chỉ dùng embedding. CV đầu vào đã qua CV Parser (đã redact thông tin liên
  hệ).
- **Model**: embedding mặc định theo constitution IV (`text-embedding-3-small`, 1536 chiều).

### Phụ thuộc

- **AIE (ai-service, `knowledge_chunks`)**: dùng bảng hiện có với `source_type = 'job_description'` (đã có trong
  constitution V, không đổi DDL); endpoint và module mới trong `apps/ai-service` do DE viết, AIE review. Cần AIE đồng ý
  trước khi code. Đã kiểm 2026-11-21: mọi truy vấn RAG hiện có lọc `source_type` (`app/rag/repository.py`,
  `app/rag/bm25_index.py`, mặc định `interview_qa` + `textbook` ở `app/rag/models.py`).
- **Danh mục kỹ năng 009** nằm ở `apps/data-pipeline/data/seeds/skill_dictionary.yaml`; ai-service cần đọc cùng danh mục
  (cách chia sẻ chốt ở plan, không chép hai bản lệch nhau).
- **Tài liệu**: cập nhật `docs/architecture/data-model.md` §5 và `rag-design.md` (JD được index cho gợi ý), sprint-plan
  S2-DE-3, `specs/README.md`, `docs/ai-service/06` (endpoint mới) trong PR tương ứng (constitution III).
- **FSD (GĐ2)**: job-service (007), applications + CV (008), web (013).
- **AIE + FSD (US6, tùy chọn)**: Planner nhận danh sách kỹ năng thiếu.

### Ngoài phạm vi

- Lọc cộng tác, mô hình đồ thị (GNN / GCN), học từ hành vi người dùng (chưa có dữ liệu tương tác).
- Fine-tune model embedding; reranker bằng LLM.
- Tìm kiếm ứng viên tự do cho nhà tuyển dụng (ngoài phạm vi tin của họ và FR-025).
- Thông báo / email gợi ý việc làm.
