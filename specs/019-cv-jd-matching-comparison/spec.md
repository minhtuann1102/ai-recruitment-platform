# Feature Specification: So sánh có kiểm soát các cách chấm phù hợp CV–JD trên bộ test do người gán

**Feature Branch**: `docs/cv-jd-matching-comparison-spec` (spec); branch code đặt ở plan

**Created**: 2026-11-26

**Status**: Draft — GĐ1 (bộ test khóa) chốt 2026-11-26: DE (owner) chốt rubric, nhãn dương, thiết kế bộ cặp; FSD chỉ gán nhãn

**Owner**: DE (chốt mọi quyết định thiết kế); FSD chỉ là người gán thứ 2 và cung cấp checkpoint BiGRU. **Sprint**: 4, **Stretch**
(mở rộng S2-DE-3, theo 017)

**Input**: User description: "Nghiên cứu so sánh có kiểm soát giữa 4 cách chấm độ phù hợp CV–JD trên cùng một bộ test
khóa do người gán nhãn: luật trùng kỹ năng, Siamese BiGRU + attention tự train của FSD, embedding pretrained + bộ
chấm của 017, hybrid. GĐ1 = bộ test khóa ~200 cặp; chấm 4 hệ và tối ưu BiGRU là GĐ sau." (bản đầy đủ: lượt chat
2026-11-26).

**Bối cảnh**: nhóm có hai hệ gợi ý CV–JD chồng nhau. (a) 017 (repo này): embedding pretrained + trùng kỹ năng + độ
chín, nDCG@5 0,883 trên 264 cặp nhãn LLM có DE kiểm (kappa 0,718), nhưng 24 CV cho khoảng tin cậy chứa 0. (b) FSD
(`final_recruitment_project/ml-service`): Siamese BiGRU tự train trên dữ liệu Qwen tiếng Anh, nhãn dương sinh bằng
luật trùng ≥60% kỹ năng bắt buộc; mọi bộ đánh giá hiện có (300 / 208 / 128 / 96 cặp) có nhãn do script, nên không
bộ nào kết luận được chất lượng thật, và việc "trùng kỹ năng thắng neural" trên holdout là vòng tròn. Spec này tạo
**một thước đo chung, độc lập** cho cả hai.

**Câu hỏi nghiên cứu**: với CV–JD ngành IT tiếng Việt / tiếng Anh và ít nhãn, một model nhẹ tự train có cộng thêm giá
trị so với luật trùng kỹ năng và embedding pretrained không, và ở loại cặp nào?

## Phạm vi theo giai đoạn

- **GĐ1 (spec này chi tiết)**: bộ test khóa ≈200 cặp, người gán độc lập, đầu vào cố định, khóa bằng SHA-256.
- **GĐ2 (chỉ chốt nguyên tắc ở đây, chi tiết ở plan sau)**: chấm 4 hệ trên bộ test, báo cáo so sánh.
- **GĐ3 (ngoài spec, việc riêng của FSD/DE)**: tối ưu BiGRU (hàng đợi concurrency, loss xếp hạng). Mọi cải tiến chỉ
  chọn trên dữ liệu dev, rồi chấm lại một lần trên bộ test.

## Clarifications

### Session 2026-11-26

- Q: Ngôn ngữ CV? → A: mỗi CV gốc có bản tiếng Việt và bản tiếng Anh; JD giữ ngôn ngữ gốc. Dịch là bước chuẩn bị dữ
  liệu, không phải gán nhãn.
- Q: Người gán thứ 2? → A: FSD (chủ hệ BiGRU), đối trọng với DE (chủ 017).
- Q: Ai chốt rubric, nhãn dương, thiết kế bộ cặp, cách đưa JD vào BiGRU? → A: DE (owner) chốt hết; FSD chỉ gán
  nhãn, không duyệt. Hạn chế ghi trong báo cáo: rubric do tác giả 017 viết (giảm thiểu ở FR-015a).
- Q: Tài liệu đặt ở đâu? → A: spec mới 019, không sửa 017.

## User Scenarios & Testing *(mandatory)*

Tác nhân: **DE** (chốt thiết kế, dựng bộ cặp, gán nhãn A, khóa, chấm mọi hệ), **FSD** (gán nhãn B), **hội đồng
đồ án** (đọc kết quả).

### User Story 1 - Dựng bộ cặp và đầu vào cố định (Priority: P1)

DE chạy một lệnh có seed. Lệnh chọn CV và JD theo luật cố định (không nhìn điểm của hệ nào), tạo bản CV tiếng Anh,
render CV và JD thành văn bản cố định, kiểm tra mọi cặp đều chấm được bởi cả hai hệ, rồi xuất bộ cặp chưa có nhãn kèm
mã băm.

**Why this priority**: mọi bước sau dựa trên bộ cặp; sai ở đây (rò rỉ, cặp không chấm được, chọn thiên vị) làm hỏng
cả so sánh.

**Independent Test**: chạy lệnh hai lần cùng seed ra cùng mã băm; báo cáo thống kê cho thấy 0 trùng với dữ liệu 017,
mọi cặp ≤ 30.000 ký tự, phân bố track / ngôn ngữ đúng thiết kế.

**Acceptance Scenarios**:

1. **Given** 84 CV ứng viên và JD đã index, **When** chạy lệnh dựng bộ cặp với seed cố định, **Then** ra đúng số cặp
   thiết kế, cùng mã băm ở lần chạy lại.
2. **Given** bộ cặp, **When** chạy kiểm tra chấm được, **Then** cả hai hệ nhận mọi cặp và bước kiểm tra **chỉ ghi
   nhận / từ chối, không ghi điểm**.
3. **Given** một JD trùng nội dung với JD trong pool 017, **When** dựng bộ cặp, **Then** JD đó bị loại.

---

### User Story 2 - Chốt rubric và lô luyện tập (Priority: P1)

DE chốt rubric (dựa trên rubric 017 thêm lựa chọn "không đủ thông tin"), định nghĩa nhãn dương cho chỉ số nhị phân
và thiết kế lấy mẫu. Hai rater gán thử một lô luyện tập lấy từ dev 017 (không thuộc bộ test) để FSD quen rubric; DE
đọc các chỗ lệch và chốt rubric bản cuối (có số phiên bản, ngày) trước lô gán chính. FSD không duyệt, chỉ gán.

**Why this priority**: hai rater phải hiểu cùng một rubric trước khi gán thật, nếu không kappa thấp vì hiểu khác chứ
không vì cặp khó.

**Independent Test**: có bản rubric cuối có số phiên bản và ngày chốt, sớm hơn thời điểm mở lô gán chính.

**Acceptance Scenarios**:

1. **Given** rubric nháp, **When** hai rater gán lô luyện tập 20 cặp, **Then** có bảng lệch và rubric cuối ghi các
   điểm đã thống nhất.
2. **Given** rubric cuối chưa chốt, **When** muốn mở lô gán chính, **Then** không mở.

---

### User Story 3 - Gán mù độc lập, đo đồng thuận, phân xử (Priority: P1)

Mỗi rater gán toàn bộ cặp trên trang gán mù: chỉ thấy văn bản CV (bản tiếng Việt) và JD, không thấy track, level,
nhóm, hay điểm; thứ tự ngẫu nhiên riêng cho từng rater. Sau khi cả hai xong, đo weighted kappa, phân xử từng cặp lệch,
lưu cả nhãn thô của hai người và nhãn cuối.

**Why this priority**: đây là phần duy nhất bộ hiện có không có.

**Independent Test**: file nhãn có 2 cột nhãn thô + nhãn cuối + ghi chú phân xử; báo cáo kappa, tỉ lệ khớp tuyệt đối,
tỉ lệ lệch ≤1 mức.

**Acceptance Scenarios**:

1. **Given** rater A đã gán xong, **When** rater B gán, **Then** B không xem được nhãn của A (và ngược lại).
2. **Given** kappa dưới sàn, **When** công bố, **Then** áp dụng quy tắc dưới sàn (FR-014), không âm thầm gán lại.

---

### User Story 4 - Khóa bộ test (Priority: P1)

DE ghi file nhãn cuối, tính SHA-256 cho bộ cặp, đầu vào cố định và nhãn, ghi manifest. Từ đây không ai sửa nhãn
hay dùng bộ test để chỉnh ngưỡng, trọng số, hay chọn checkpoint.

**Independent Test**: manifest có mã băm và ngày khóa; ngày khóa sớm hơn mọi file điểm của các hệ (GĐ2).

**Acceptance Scenarios**:

1. **Given** bộ test đã khóa, **When** có người sửa một nhãn, **Then** kiểm tra mã băm báo lệch.

---

### User Story 5 - Chấm 4 hệ và báo cáo (Priority: P2, GĐ2)

Chấm luật trùng kỹ năng, BiGRU, embedding 017, các bản hybrid trên cùng bộ test khóa; báo cáo theo FR-020…FR-024.

**Why this priority**: là mục đích cuối, nhưng phụ thuộc bộ test khóa và checkpoint của FSD.

**Independent Test**: một bảng kết quả, mọi số chạy lại được từ lệnh trong quickstart.

### Edge Cases

- Track frontend chỉ có 8 JD thật (5 en, 3 vi): CV frontend dùng chung 8 JD này; ghi rõ trong báo cáo, không bù bằng
  JD tổng hợp.
- JD không có cấp bậc hoặc không có danh sách kỹ năng: vẫn được chọn nếu cả hai hệ chấm được; ghi cờ để phân tích.
- Rater chọn "không đủ thông tin": cặp bị loại khỏi chỉ số sau phân xử nếu cả phân xử cũng xác nhận; nếu >10% cặp bị
  loại thì xem lại bộ render văn bản trước khi khóa (và chỉ được dựng lại bằng seed mới, trước khi bất kỳ hệ nào chấm).
- Bản dịch CV sai nghĩa (vd dịch tên công nghệ): DE kiểm mẫu ngẫu nhiên; tên công nghệ giữ nguyên, không dịch.
- Phân bố nhãn quá lệch (vd <15% nhãn 2 trong tập cùng track): phát hiện trước khi khóa; được bổ sung cặp bằng seed
  mới theo cùng luật, gán mù như cũ.
- Một hệ từ chối một cặp ở GĐ2 dù đã qua kiểm tra chấm được: tính là dự đoán sai cho hệ đó, báo cáo riêng số cặp bị
  từ chối.

## Requirements *(mandatory)*

### Functional Requirements

**Dựng bộ cặp (US1)**

- **FR-001**: CV MUST lấy từ 84 CV ứng viên tổng hợp (T040 của 017); MUST NOT trùng 24 CV đánh giá của 017.
- **FR-002**: JD MUST là JD thật (không tổng hợp), nằm trong tập JD đã index cho gợi ý của 017; MUST loại 36 JD pool
  017 và mọi JD trùng nội dung với chúng.
- **FR-003**: Thiết kế mặc định 30 CV (5 / track × 6 track, trải level) × 7 JD = **210 cặp**: mỗi CV 5 JD cùng nhóm
  (trong đó ≥2 lệch level ≥2 bậc nếu có), 1 JD nhóm lân cận, 1 JD nhóm xa. Trộn JD tiếng Việt / tiếng Anh theo tỉ lệ
  có sẵn của từng nhóm.
- **FR-004**: Chọn cặp MUST bằng script có seed, chỉ dựa trên siêu dữ liệu (track, nhóm, level, ngôn ngữ), MUST NOT
  dùng điểm của bất kỳ hệ nào.
- **FR-005**: Mỗi CV MUST có bản tiếng Việt và bản tiếng Anh cùng nội dung; tên công nghệ giữ nguyên. Bản dịch được
  sinh ở bước chuẩn bị dữ liệu, ghi cách sinh, DE kiểm mẫu ≥20% CV.
- **FR-006**: Đầu vào cho các hệ MUST cố định trước khi có nhãn: một bộ render CV → văn bản, một bộ chuyển JD → dạng
  tin tuyển dụng mà BiGRU đọc, một bộ chuyển JD → đầu vào bộ chấm 017. Kết quả render MUST lưu kèm mã băm; mọi hệ đọc
  từ đó, không tự render lại.
- **FR-007**: Mọi cặp MUST ≤ 30.000 ký tự mỗi phía; MUST qua kiểm tra chấm được của cả hai hệ (chỉ chấp nhận / từ
  chối, không lưu điểm).
- **FR-008**: Chạy lại cùng seed và cùng đầu vào MUST ra cùng mã băm.

**Rubric và người gán (US2, US3)**

- **FR-009**: Rubric MUST dựa trên rubric 017 (thang 0 / 1 / 2, câu hỏi "nhà tuyển dụng có muốn gọi phỏng vấn
  không"), thêm lựa chọn "không đủ thông tin"; có số phiên bản.
- **FR-010**: Định nghĩa nhãn dương cho chỉ số nhị phân MUST chốt trước khi gán. Mặc định: dương = nhãn 2; báo cáo phụ
  với dương = nhãn ≥1.
- **FR-011**: DE MUST chốt rubric, định nghĩa nhị phân, thiết kế lấy mẫu và cách đưa JD vào BiGRU trước lô gán chính,
  ghi phiên bản và ngày. Cách đưa JD vào BiGRU MUST bám đúng mã `server.analyze` hiện có của FSD (đọc mã, không đoán).
- **FR-012**: Lô luyện tập (20 cặp) MUST lấy từ dev 017, không thuộc bộ test.
- **FR-013**: Gán MUST mù: trang chỉ hiện văn bản CV (bản tiếng Việt) và JD, không track / level / nhóm / điểm / nhãn
  người kia; thứ tự ngẫu nhiên riêng mỗi rater.
- **FR-014**: Đồng thuận MUST đo bằng weighted kappa (quadratic), kèm khớp tuyệt đối và lệch ≤1 mức. Sàn = **0,60**.
  Dưới sàn: vẫn phân xử và khóa, nhưng bộ test MUST ghi "độ tin cậy thấp", kết luận GĐ2 MUST ghi là tạm thời, và bộ
  test MUST NOT dùng làm cổng bật tính năng của FSD. Không gán lại để kéo kappa lên.
- **FR-015**: Mỗi cặp lệch MUST được hai rater bàn; không thống nhất thì DE quyết. Lưu nhãn thô A, nhãn thô B, nhãn
  cuối, người quyết, ghi chú.
- **FR-015a**: Vì DE vừa viết rubric vừa là chủ 017, báo cáo GĐ2 MUST có thêm kết quả trên **tập hai người khớp ngay
  từ đầu** (A = B) và trên **nhãn thô của FSD**, để kiểm tra kết luận không phụ thuộc phân xử của DE.

**Khóa và kỷ luật dùng (US4)**

- **FR-016**: Manifest MUST ghi SHA-256 của bộ cặp, đầu vào cố định, nhãn cuối, phiên bản rubric, seed, ngày khóa.
- **FR-017**: MUST NOT chạy bất kỳ hệ nào trên bộ test (trừ kiểm tra chấp nhận ở FR-007) trước khi khóa.
- **FR-018**: Ngưỡng, trọng số, checkpoint MUST chỉ chọn trên dữ liệu dev: 264 cặp 017 cho 017; validation nội bộ và
  ngưỡng 0,5 đã khai báo cho BiGRU. Bộ test MUST NOT dùng để chỉnh.
- **FR-019**: CV tổng hợp không chứa thông tin cá nhân thật; JD chỉ lưu nội dung tin, không thông tin liên hệ.

**Chấm và báo cáo (GĐ2, nguyên tắc)**

- **FR-020**: Hệ so sánh: (1) luật trùng kỹ năng tất định, (2) BiGRU chỉ neural, (3) embedding 017 chỉ cosine, (3b)
  cùng bộ chấm 017 nhưng embedding sentence-transformers đa ngôn ngữ (model theo đề cương, chọn trên dev theo
  `plans/261126-2235-embedding-model-comparison/plan.md`), (4a) hybrid của BiGRU theo trọng số đã khai báo của FSD,
  (4b) điểm đầy đủ của 017. Không train thêm model nào; (3b) dùng model pretrained có sẵn, chỉ để kiểm chứng việc
  lệch đề cương (OpenAI thay cho sentence-transformers).
- **FR-021**: Chỉ số chính tính trên tập **cùng nhóm**: nDCG theo từng CV và độ chính xác xếp cặp theo từng CV. Chỉ
  số phụ trên toàn bộ: macro F1 / F1 lớp dương, precision, recall, ma trận nhầm lẫn, Spearman.
- **FR-022**: Khoảng tin cậy MUST tính bằng paired bootstrap theo CV (mỗi CV là một đơn vị), cho hiệu số giữa từng
  cặp hệ.
- **FR-023**: Báo cáo MUST có bảng 2×2 ngôn ngữ CV × ngôn ngữ JD, và độ nhất quán theo ngôn ngữ (cùng cặp, đổi bản
  CV vi ↔ en).
- **FR-024**: Báo cáo MUST tách kết quả bộ test (độc lập) khỏi kết quả trên bộ synthetic / chẩn đoán của FSD (phủ
  định, nhồi từ khóa); không gộp.

### Key Entities

- **Cặp test**: id, CV gốc, phiên bản ngôn ngữ CV, JD, loại cặp (cùng nhóm / lân cận / xa), ngôn ngữ JD, cờ (JD
  thiếu level / kỹ năng).
- **Đầu vào cố định**: văn bản CV đã render, JD ở dạng cho BiGRU, JD ở dạng cho 017, mã băm từng phần.
- **Nhãn**: id cặp, nhãn thô A, nhãn thô B (0 / 1 / 2 / không đủ thông tin), nhãn cuối, ghi chú phân xử.
- **Rubric**: phiên bản, nội dung, ngày DE chốt.
- **Manifest khóa**: các mã băm, seed, phiên bản rubric, ngày khóa, kappa, cờ "độ tin cậy thấp" nếu có.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Bộ test có 200–220 cặp hợp lệ; 0 CV trùng 017, 0 JD trùng pool 017 (kể cả trùng nội dung); 100% cặp
  được cả hai hệ chấp nhận.
- **SC-002**: Mỗi rater gán xong bộ chính trong ≤3 giờ.
- **SC-003**: Weighted kappa giữa DE và FSD được báo cáo; mục tiêu ≥0,60 (dưới sàn xử lý theo FR-014).
- **SC-004**: Ngày khóa trong manifest sớm hơn mọi file điểm của GĐ2; kiểm tra mã băm khớp ở mọi lần chấm.
- **SC-005**: Tập cùng nhóm có cả ba mức nhãn, mỗi mức ≥15% số cặp (kiểm trước khi khóa).
- **SC-006** (GĐ2): Báo cáo trả lời được câu hỏi nghiên cứu bằng hiệu số có khoảng tin cậy cho từng cặp hệ, và
  phân tích theo loại cặp, kể cả khi BiGRU không hơn.

## Assumptions

- 84 CV ứng viên (T040, đã merge #111) đủ để chọn 30 CV, 5 / track; CV là `CvProfile` tiếng Việt.
- Rater thấy bản CV tiếng Việt; nhãn áp cho cả bản tiếng Anh vì bản dịch giữ nguyên nội dung. Vì vậy 210 cặp nhãn
  cho 420 lượt chấm (mỗi cặp × 2 phiên bản CV), không tốn thêm công gán.
- Dịch CV bằng LLM ở bước chuẩn bị dữ liệu được chấp nhận; ràng buộc "không AI API ngoài" của FSD áp cho model và lúc
  chạy, không áp cho chuẩn bị dữ liệu offline. Ghi rõ trong báo cáo.
- Trang gán mù, công cụ tạo sheet và script đo đồng thuận của 017 được dùng lại.
- FSD gửi checkpoint BiGRU (`artifacts/`, `artifacts-v2/`) trước GĐ2; DE chấm cả v1 và v2 đúng như được gửi, không
  chỉnh. GĐ1 không cần checkpoint, chỉ cần mã của FSD (giới hạn ký tự, dạng JD) có sẵn ở repo FSD.
- Thời gian ước lượng: dựng bộ cặp ~1 ngày DE; lô luyện tập + duyệt ~1 buổi; gán ~3 giờ / rater; phân xử ~1 giờ.
- Hạn cứng đồ án 21/12/2026; đây là Stretch, chỉ làm khi việc Bắt buộc của sprint xong (constitution VII).
- Không commit / push / CI trong phạm vi việc này cho tới khi owner yêu cầu.

## Phụ thuộc

- 017: tập JD đã index, bộ chấm, 264 cặp dev, rubric, trang gán mù, script đồng thuận.
- 009: JD chuẩn hóa (nhóm, level, ngôn ngữ, kỹ năng).
- FSD: gán nhãn B (lô luyện tập + lô chính, GĐ1); gửi checkpoint BiGRU (GĐ2).
