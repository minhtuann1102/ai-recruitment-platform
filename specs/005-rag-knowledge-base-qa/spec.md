# Feature Specification: RAG Knowledge Base — Interview Q&A

**Feature Branch**: `docs/rag-knowledge-base-qa-spec` (spec); branch code đặt ở plan
(theo `docs/conventions.md`; thư mục spec độc lập với branch)

**Created**: 2026-10-13

**Status**: Draft — đã clarify, chờ review PR (AIE + FSD duyệt đổi AC S1-DE-1)

**Owner**: DE (chính) + AIE (đồng sở hữu, review spec) — **Sprint**: 1 (12/10 → 26/10/2026)

**Covers**: S1-DE-1, S1-DE-2, S1-DE-3, S1-DE-4 (DE); S1-AIE-1 (phần ingestion chuyển cho DE); S1-AIE-2 (AIE)

**Input**: User description: "Feature 005 rag-knowledge-base-qa (S1-DE-1..4 + S1-AIE-1..2, owner DE + AIE): thu thập
200+ cặp Q&A phỏng vấn CNTT, setup crawler 1 nguồn mẫu, pipeline clean→chunk→dedup, index Q&A vào ai_db
knowledge_chunks và verify retrieval relevant."

**Nguồn thiết kế**: [`docs/architecture/rag-design.md`](../../docs/architecture/rag-design.md) (đang ở PR #3
`feat/aie`, chưa merge) thay thế phần schema/chunking/dedup của
[`data-pipeline.md`](../../docs/architecture/data-pipeline.md) §4, §7. Spec chỉ ghi phần mới hoặc khác.

## Clarifications

### Session 2026-10-13

- Q: Bộ phân loại Q&A? → A: Theo **topic catalog** của ai-service. Mỗi cặp bắt buộc `topic_id` của một topic trong
  catalog; nhóm kiến thức lấy từ `category` của topic đó. Catalog PR #3 (51 topic, 4 track backend/AI) **mở rộng** theo
  đề xuất [`contracts/topic-catalog-proposal/`](contracts/topic-catalog-proposal/): thêm track `frontend_react` (13
  topic), `devops_engineer` (12 topic) và 14 topic AI cutting-edge cho `ai_engineer` → 6 track, 90 topic (Backend 30,
  AI 25, DevOps 14, Frontend 12, System Design 5, Database 4). Đề xuất đã chạy qua planner + test catalog của AIE.
  Thêm category `Frontend` là thay đổi của AIE.
- Q: Ưu tiên AI? → A: Có — AI chiếm phần lớn nhất sau Backend, nhấn vào chủ đề thực tế hiện nay (fine-tuning, reasoning
  model, context engineering, RAG nâng cao, multi-agent, MCP, inference, multimodal, voice, bảo mật LLM, LLMOps, tiếng
  Việt). Danh sách là đề xuất, đối chiếu lại với JD crawl ở 009. Không tăng ngưỡng tối thiểu riêng cho AI ở S1.
- Q: Nguồn 200+ cặp? → A: Kết hợp. ≥ 50% cặp lấy từ nguồn công khai có giấy phép cho phép sửa đổi và phân phối lại,
  chuẩn hóa sang tiếng Việt xen thuật ngữ Anh; phần còn lại tự soạn (synthetic, có người review). 50 cặp seed của AIE
  chỉ được tính khi DE review đáp án, gán `qa_id` + `topic_id` và nhập vào bộ canonical. Topic AI cutting-edge ít nguồn
  công khai nên chủ yếu synthetic; tỉ lệ 50% chung vẫn khả thi nếu khoảng 2/3 cặp ngoài AI lấy từ nguồn công khai.
- Q: Golden set và ngưỡng? → A: DE soạn truy vấn + nhãn đề xuất, AIE duyệt nhãn. Mục tiêu recall@5 ≥ 0.8; chưa đạt thì
  báo cáo kèm hướng cải thiện, **không chặn merge**.
- Q: Ba thang `level` (`fresher..senior`), độ khó 1–5, nhãn `easy | medium | hard` — pipeline có cần mapping? → A:
  Không. Ba thang có vai trò khác nhau: `level` = cấp ứng viên, cố định cả buổi (chọn topic, trọng số, biên độ khó);
  1–5 = núm agent chỉnh từng lượt (+1 đào sâu, −1 gợi ý); nhãn 3 mức = lưu và lọc RAG. Mapping `1–2 → easy`,
  `3 → medium`, `4–5 → hard` đã định nghĩa ở `docs/ai-service/01` §2.1; chuyển đổi lúc truy hồi là việc của AIE
  (S1-AIE-2). DE chỉ gán nhãn đúng rubric (FR-001).
- Q: Định danh cặp và dấu bộ dữ liệu? → A: `metadata.qa_id` dạng `<dataset>-<NNNN>` (vd `de-qa-0001`), gán khi tạo,
  không đổi, không tái sử dụng; `metadata.dataset` (vd `de_interview_qa`). Cả hai nằm trong JSONB nên không đổi DDL
  của AIE. Dọn bản cũ (FR-013) chỉ trong cùng `dataset`.
- Q: Trùng giữa seed DE và seed AIE? → A (AIE đồng ý): `ai_db` chỉ index **một** bộ `interview_qa` canonical do DE sở
  hữu; AIE ngừng index seed mock khi bộ DE vào kho (vẫn dùng cho test/local). Không còn trùng chéo.
- Q: API key embedding? → A: Thắng giữ key, chia sẻ riêng cho người chạy pipeline (không commit, không đưa vào kênh
  chung). Chi phí ≈ 400 bản ghi × ~150 token ≈ 60k token ≈ 0,001 USD. US1, US2, US5 chạy offline không cần key.
- Q: Phân chia code dùng chung DE/AIE? → A (AIE đồng ý): tách theo đường ghi / đường đọc. Đường ghi (load → clean →
  chunk → dedup → embed → upsert/dọn) thuộc DE, gồm phần ingestion của S1-AIE-1; đường đọc (embed truy vấn, tìm tương
  đồng, tra theo `qa_id`) thuộc AIE (S1-AIE-2). Hợp đồng chung: DDL `knowledge_chunks`, tên model embedding, file YAML
  topic catalog (đọc như dữ liệu). Thay cho đề xuất rag-design §6, §8; đường dẫn code chốt ở `/speckit-plan`.
- Q: Hoàn tất 001 PR-2 trước? → A: Có. Thứ tự: commit spec 005 + PR review → 001 PR-2 (T016–T026, mở khóa `ai_db` cho
  cả team và US3 của 005) → `/speckit-plan` 005. Soạn nội dung Q&A (US1) chạy song song.

### Session 2026-10-19

- Q: Nguồn Q&A — có cần giấy phép? → A (DE quyết định): **Không.** Thu thập (crawl) mọi nguồn Q&A phỏng vấn tìm được,
  kể cả không rõ giấy phép hoặc ND/NC; dịch nội dung không phải tiếng Việt sang tiếng Việt (giữ thuật ngữ Anh). Bỏ
  ngưỡng ≥ 50% nguồn có giấy phép (FR-003, SC-002 cũ). Vẫn giữ: robots.txt, rate limit, xóa PII (constitution V),
  ghi `source` URL + `attribution` cho mỗi cặp.
- Q: Repo public — có commit nội dung crawl? → A: **Không.** Commit trong repo = phân phối lại công khai. Chỉ commit
  code thu thập + danh sách nguồn; nội dung nằm ở `data/raw/` (gitignore) và `ai_db`; tái lập bằng lệnh `collect`.
  Seed curated (`data/seeds/`) chỉ chứa cặp tự soạn hoặc có giấy phép cho phép phân phối lại.
- Q: Review thế nào khi có hàng nghìn cặp dịch máy? → A: Review theo mẫu (vd ~10 cặp ngẫu nhiên mỗi nguồn, đối chiếu
  bản gốc), ghi kết quả; `reviewed_by` từng cặp chỉ bắt buộc với seed curated. Công cụ: lệnh `review-sample` (bảng
  đọc không commit + CSV `cid, verdict, reviewer` commit được).
- Q: Dữ liệu crawl gần như không có câu hard (~1–2%) — giữ "mỗi độ khó ≥ 20%"? → A (DE chốt): **Không.** SC-001 đổi
  thành mỗi topic có level `middle` hoặc `senior` có ≥ 2 cặp `hard` (phiên senior cần câu hard theo từng topic, không
  cần 20% toàn kho). Câu hard thiếu được sinh bằng Claude trong phiên làm việc, bám tài liệu thật (nguồn crawl nâng
  cao, tài liệu chính thức; ghi `grounding_urls`), viết bằng tiếng Việt → vào seed curated (`source = self`,
  `synthetic = true`, commit), DE duyệt (`reviewed_by`, cách duyệt: Session 2026-10-23). Báo AIE vì Interviewer lọc theo độ khó.
- Q: Tách dữ liệu crawl khỏi seed curated? → A: Có. `dataset = de_crawled_qa`, định danh `cr-<nguồn>-<8 hex>` sinh
  từ URL + câu hỏi gốc (nguồn upstream là sự thật, khác `de-qa-NNNN`); dọn bản cũ (FR-013) theo từng dataset.

### Session 2026-10-23

- Q: Duyệt 144 cặp hard tự viết (`de-qa-1000..1262`, T057) thế nào khi DE không tự kiểm chứng được nội dung của mọi
  mảng (Java, Node, Python, DevOps, AI, Frontend)? → A (DE chốt): `reviewed_by = minhtuann1102` nghĩa là DE chấp nhận
  cặp sau một vòng duyệt có bằng chứng, không phải đã tự đọc từng chữ mọi cặp. Điều kiện: (1) mọi cặp qua skill
  `interview-qa-review` (rubric v2), mỗi claim chính có câu trích nguyên văn từ nguồn, kiểm lại bằng `verify_quotes.py`;
  (2) mỗi lô có một cặp mồi cài lỗi, lô để lọt mồi thì bỏ (7/7 mồi bị bắt); (3) mọi vấn đề critical/major đã được sửa
  trong seed trước khi duyệt (gợi ý mức minor không áp); (4) DE đọc kỹ các cặp "phải đọc", toàn bộ các chỗ đã sửa và một
  mẫu cặp chuyển sang Đạt theo rubric v2, phần còn lại chấp nhận theo báo cáo. Chỉ áp cho cặp hard tự viết; seed chuyển
  thể/dịch và dữ liệu crawl giữ quy tắc cũ. Kết quả duyệt: `plans/reports/qa-review/results-*.json` tại commit `eac9b8e`
  (nhánh `chore/qa-review-skill`). Báo AIE.

## User Scenarios & Testing *(mandatory)*

Người dùng trực tiếp của feature là **các agent AI** (Interviewer cần câu hỏi mẫu gần chủ đề, Evaluator cần đáp án
mẫu để chấm) và **thành viên dev** (DE vận hành pipeline, AIE gọi truy hồi). Người dùng cuối (ứng viên luyện phỏng
vấn) hưởng lợi gián tiếp: câu hỏi sát chủ đề hơn, chấm điểm có căn cứ. Hội đồng demo Sprint 1 cần thấy: "RAG tìm Q&A
relevant".

### User Story 1 - Bộ Q&A phỏng vấn chuẩn hóa ≥ 200 cặp theo topic catalog (Priority: P1) · S1-DE-1

DE tạo bộ dữ liệu ≥ 200 cặp câu hỏi/đáp án mẫu phỏng vấn CNTT, mỗi cặp gắn một topic trong topic catalog, có định
danh ổn định, độ khó, ngôn ngữ, nguồn gốc và giấy phép. Bộ dữ liệu là file seed curated được commit vào repo.

**Why this priority**: Không có dữ liệu thì không có gì để index; mọi story khác dùng bộ này làm input. Làm được
ngay, không chờ hạ tầng.

**Independent Test**: Chạy bước kiểm tra dữ liệu trên file seed → báo cáo số cặp theo topic/nhóm/độ khó/nguồn, 0 lỗi
schema, 0 `topic_id` lạ, 0 cặp trùng, 0 thông tin cá nhân, 100% cặp có nguồn.

**Acceptance Scenarios**:

1. **Given** file seed, **When** chạy kiểm tra dữ liệu, **Then** có ≥ 200 cặp hợp lệ, phân bố đạt SC-001, SC-002.
2. **Given** một cặp thiếu trường bắt buộc, có `topic_id` không thuộc catalog, hoặc giấy phép ngoài danh sách cho
   phép, **When** chạy kiểm tra, **Then** cặp đó bị liệt kê kèm lý do, lệnh kết thúc với trạng thái lỗi.
3. **Given** hai cặp có câu hỏi trùng nhau (sau chuẩn hóa khoảng trắng/hoa thường), **When** chạy kiểm tra, **Then**
   báo trùng kèm định danh của cả hai.
4. **Given** một topic trong catalog có < 2 cặp, **When** chạy kiểm tra, **Then** báo topic thiếu.

---

### User Story 2 - Pipeline xử lý offline: load → clean → chunk → dedup (Priority: P1) · S1-DE-3

DE chạy một lệnh biến file Q&A thành danh sách bản ghi sẵn sàng embed: mỗi cặp sinh **2 bản ghi** (`question` chỉ
chứa câu hỏi; `qa_pair` chứa câu hỏi + đáp án), cùng định danh cặp và phân loại. Bước này không cần database hay
API key.

**Why this priority**: Là phần lõi dùng chung cho mọi nguồn sau này (JD ở 009, textbook ở 012). Chạy được offline nên
không bị chặn bởi hạ tầng 001 hay API key.

**Independent Test**: Chạy pipeline ở chế độ chỉ xử lý (không index) trên file seed → nhận file bản ghi đã xử lý +
thống kê; số bản ghi = 2 × số cặp hợp lệ trừ phần dedup.

**Acceptance Scenarios**:

1. **Given** file seed N cặp hợp lệ, **When** chạy chế độ chỉ xử lý, **Then** sinh 2N bản ghi (trừ trùng) và in
   thống kê: số record vào, số bản ghi ra, tỉ lệ dedup, số record bị loại kèm lý do.
2. **Given** nội dung có khoảng trắng thừa, ký tự điều khiển, HTML còn sót, **When** xử lý, **Then** nội dung được
   làm sạch, giữ nguyên dấu tiếng Việt và thuật ngữ tiếng Anh.
3. **Given** chạy lại với cùng input, **When** so sánh output, **Then** kết quả giống hệt (deterministic).

---

### User Story 3 - Index vào kho tri thức và truy hồi được (Priority: P1) · S1-DE-4, S1-AIE-1 (DE), S1-AIE-2 (AIE)

DE chạy pipeline đầy đủ: bản ghi đã xử lý được embed và ghi vào kho tri thức (`knowledge_chunks` trong `ai_db`).
AIE (và DE khi kiểm tra) gửi một truy vấn kèm bộ lọc → nhận top-k bản ghi gần nhất kèm điểm tương đồng; hoặc tra thẳng
đáp án mẫu theo định danh cặp Q&A.

**Why this priority**: Đây là AC của demo Sprint 1 và là đầu vào cho S1-AIE-3/4 (Evaluator chấm điểm có RAG).

**Independent Test**: Hạ tầng local đang chạy + có API key → chạy pipeline đầy đủ → đếm bản ghi theo nguồn/nhóm →
chạy lại lần 2 → số bản ghi không đổi → gửi 5 truy vấn mẫu → kết quả top-5 thuộc đúng chủ đề.

**Acceptance Scenarios**:

1. **Given** kho tri thức rỗng, **When** chạy pipeline đầy đủ với bộ ≥ 200 cặp, **Then** có ≥ 400 bản ghi
   `interview_qa`, ≥ 99% có vector, và thống kê in ra số embedding lỗi.
2. **Given** đã index, **When** chạy lại cùng input, **Then** không phát sinh bản ghi mới và không gọi embed lại cho
   bản ghi đã có.
3. **Given** một cặp Q&A bị sửa đáp án hoặc bị xóa khỏi file seed, **When** chạy lại, **Then** bản cũ không còn
   truy hồi được; bản mới (nếu có) được index.
4. **Given** truy vấn kèm bộ lọc nhóm kiến thức + độ khó, **When** truy hồi, **Then** chỉ trả bản ghi khớp bộ lọc,
   tối đa k kết quả, sắp theo độ tương đồng giảm dần, mỗi kết quả có điểm và định danh cặp.
5. **Given** một định danh cặp Q&A, **When** tra đáp án mẫu, **Then** nhận đúng bản ghi `qa_pair` của cặp đó, không
   qua tìm kiếm tương đồng.
6. **Given** thiếu API key hoặc kho tri thức chưa sẵn sàng, **When** chạy pipeline đầy đủ, **Then** dừng trước khi
   ghi với thông báo rõ nguyên nhân; không ghi dở dang.

---

### User Story 4 - Đo chất lượng truy hồi bằng golden set (Priority: P2) · S1-DE-4 ("verify relevant")

Có bộ truy vấn chuẩn (golden set) ≥ 20 truy vấn, mỗi truy vấn gắn nhãn định danh cặp Q&A đúng **trong kho của ta**,
nhãn đã được AIE duyệt. Một lệnh chạy toàn bộ golden set và báo recall@5 tổng và theo 5 nhóm truy vấn: (a) tiếng Việt
thuần, (b) code-mixed, (c) tiếng Anh, (d) Việt → tài liệu Anh, (e) không dấu.

**Why this priority**: Biến "kết quả relevant" thành con số kiểm chứng được; là baseline để so sánh khi đổi chunking
hoặc model (rag-design §7). Không chặn demo nên đứng sau US3.

**Independent Test**: Chạy lệnh đánh giá trên kho đã index → báo cáo recall@5 theo nhóm + top-3 của từng truy vấn để
xem tay.

**Acceptance Scenarios**:

1. **Given** golden set và kho đã index, **When** chạy đánh giá, **Then** in recall@5 tổng, theo nhóm, và danh sách
   truy vấn trượt.
2. **Given** một truy vấn trong golden set trùng nguyên văn câu hỏi đã index, **When** kiểm tra golden set, **Then**
   truy vấn đó bị từ chối (tránh thổi phồng recall).
3. **Given** recall@5 tổng < 0.8, **When** chạy đánh giá, **Then** báo cáo vẫn được tạo, ghi rõ chưa đạt mục tiêu và
   các nhóm yếu nhất; lệnh không làm hỏng CI.

---

### User Story 5 - Crawler mẫu cho một nguồn (Priority: P2) · S1-DE-2

DE có bộ công cụ crawl dùng lại được ở Sprint 2 (JD) và Sprint 3 (textbook). Sprint này crawl thành công **một nguồn
mẫu**, tuân thủ robots.txt, có giới hạn tốc độ, không lưu thông tin cá nhân; output thô lưu ngoài git và chuyển được
sang định dạng của US1.

**Why this priority**: AC sprint chỉ yêu cầu "crawl được 1 source mẫu"; giá trị chính là sẵn sàng cho 009 (500+ JD).
Không chặn demo Sprint 1.

**Independent Test**: Chạy crawler với giới hạn nhỏ → nhận file thô ≥ 50 record, log cho thấy robots.txt được kiểm
tra, khoảng cách giữa các request ≥ mức cấu hình, không có email/số điện thoại trong output.

**Acceptance Scenarios**:

1. **Given** nguồn cho phép crawl, **When** chạy crawler với giới hạn N trang, **Then** lưu ≥ 50 record thô kèm URL
   và thời điểm crawl, không vượt N trang.
2. **Given** đường dẫn bị robots.txt cấm, **When** crawler gặp, **Then** bỏ qua và ghi log.
3. **Given** trang có email/số điện thoại, **When** lưu record, **Then** các thông tin đó bị loại bỏ.
4. **Given** trang cần JavaScript để hiển thị nội dung, **When** crawl, **Then** vẫn lấy được nội dung.

---

### Edge Cases

- **Định danh không ổn định**: seed mock của AIE (`qa_seed.json`, 50 cặp) chưa có định danh cặp và `topic_id`.
  Nếu định danh sinh từ nội dung thì sửa một chữ là thành cặp mới → bản cũ thành rác. Định danh phải ổn định, gán khi
  tạo cặp.
- **Câu hỏi hợp với nhiều topic** (vd JWT có ở cả track Node.js và Python): gán một `topic_id`; track khác vẫn tìm được
  qua tìm tương đồng lọc theo `category` (rag-design §4.1).
- **Catalog đổi sau khi đã index** (topic bị đổi id hoặc xóa): kiểm tra dữ liệu báo cặp có `topic_id` mồ côi; lần chạy
  sau từ chối cặp đó và dọn bản ghi cũ của nó (FR-013).
- **Trùng gần đúng**: hai câu hỏi khác chữ nhưng cùng ý. Dedup theo hash chỉ bắt trùng tuyệt đối; trùng gần đúng phát
  hiện ở bước kiểm tra dữ liệu (cảnh báo, không tự xóa).
- **Seed mock của AIE còn trong kho** khi bộ DE index lần đầu: pipeline DE không xóa (khác `dataset`, FR-013); AIE gỡ
  theo thỏa thuận ở Clarifications. Trong lúc còn song song, nội dung trùng chỉ giữ một bản và lần chạy báo bản bị bỏ qua.
- **Provider embedding lỗi/giới hạn tốc độ**: lỗi tạm thời phải retry có giới hạn; lỗi còn lại được đếm vào "số
  embedding lỗi", không làm hỏng các bản ghi đã ghi thành công; chạy lại chỉ xử lý phần còn thiếu.
- **Đổi model embedding**: bản ghi cũ phải nhận diện được theo model để embed lại (không trộn vector khác model trong
  một lần truy hồi).
- **Truy vấn không dấu / code-mixed / chéo ngôn ngữ**: chất lượng chưa biết (rag-design §8) — đo ở US4, không chặn
  merge nếu dưới ngưỡng, nhưng phải báo cáo.
- **Prompt injection trong dữ liệu**: nội dung crawl có thể chứa chỉ dẫn kiểu "bỏ qua hướng dẫn trước". Pipeline lưu
  nguyên văn (là dữ liệu); việc cách ly khi đưa vào prompt thuộc AIE (rag-design §5).
- **Kho tri thức chưa có bảng hoặc extension vector**: pipeline báo lỗi rõ, chỉ dẫn tới bước dựng hạ tầng (001).
- **Nguồn crawl đổi cấu trúc HTML**: crawler trả 0 record phải báo lỗi, không lặng lẽ thành công.

## Requirements *(mandatory)*

### Functional Requirements

**Bộ dữ liệu Q&A (US1 · S1-DE-1 · DE)**

- **FR-001**: Bộ dữ liệu MUST có ≥ 200 cặp Q&A hợp lệ; mỗi cặp MUST có: định danh ổn định duy nhất (có tiền tố bộ dữ
  liệu), `topic_id`, câu hỏi, đáp án mẫu, độ khó (`easy | medium | hard`), ngôn ngữ (`vi | en`), nguồn, giấy phép,
  cờ synthetic; tùy chọn: tags. Độ khó MUST gán theo rubric 1–5 của ai-service (`docs/ai-service/02`): `easy` = định
  nghĩa, ví dụ (mức 1–2); `medium` = áp dụng, so sánh, xử lý lỗi (3); `hard` = internals, trade-off ở scale (4–5).
- **FR-002**: `topic_id` MUST là id của một **topic** (không phải scenario) trong topic catalog của ai-service tại thời
  điểm chạy; nhóm kiến thức MUST lấy từ `category` của topic đó, không nhập tay. Danh mục MUST đọc từ catalog, không
  chép cứng. Phạm vi topic theo catalog sau khi áp dụng đề xuất mở rộng (Clarifications Q1).
- **FR-003** *(sửa 2026-10-19)*: Mỗi cặp MUST ghi `source` (URL hoặc `self`) và `attribution` khi lấy từ ngoài; giấy
  phép ghi nếu biết (`unknown` nếu không). Không còn ngưỡng nguồn có giấy phép. Nội dung không có giấy phép phân phối
  lại MUST NOT commit (repo public) — chỉ ở `data/raw/` và `ai_db`. Seed curated: cặp tự soạn có người review. 50 cặp
  seed của AIE chỉ được nhập sau khi DE review và gán `qa_id` + `topic_id`.
- **FR-004**: Đáp án mẫu MUST viết bằng tiếng Việt, giữ nguyên thuật ngữ tiếng Anh (quyết định nhóm, rag-design §9);
  cặp tiếng Anh được phép nhưng MUST gắn `language = en`.
- **FR-005**: MUST có bước kiểm tra dữ liệu: schema, `topic_id` thuộc catalog, giấy phép thuộc danh sách cho phép, trùng
  câu hỏi (tuyệt đối và cảnh báo gần đúng), thông tin cá nhân, phân bố theo topic/nhóm/độ khó/nguồn; lỗi MUST làm lệnh
  thất bại.

**Xử lý offline (US2 · S1-DE-3 · DE)**

- **FR-006**: Pipeline MUST đọc bộ Q&A, làm sạch nội dung (khoảng trắng, ký tự điều khiển, HTML sót) mà không làm mất
  dấu tiếng Việt.
- **FR-007**: Mỗi cặp MUST sinh đúng 2 bản ghi: `question` (chỉ câu hỏi) và `qa_pair` (câu hỏi + đáp án), cùng định
  danh cặp và mọi trường phân loại; nguồn `source_type = interview_qa`. Không cắt nhỏ một cặp.
- **FR-008**: Pipeline MUST dedup theo hash nội dung đã chuẩn hóa **trước** khi embed.
- **FR-009**: Chế độ chỉ xử lý MUST chạy được không cần database và không cần API key; output MUST deterministic.
- **FR-010**: Đường ghi (clean, chunk, dedup, embed, upsert, dọn) MUST chỉ có một bản hiện thực, thuộc DE; đường đọc
  (AIE) MUST NOT ghi vào kho. Hợp đồng chung: schema `knowledge_chunks`, tên model embedding, topic catalog.

**Index & truy hồi (US3 · S1-DE-4, S1-AIE-1 · DE; S1-AIE-2 · AIE)**

- **FR-011**: Pipeline đầy đủ MUST embed bằng model mặc định của constitution (IV) và ghi vào kho tri thức của
  ai-service theo schema `knowledge_chunks` do AIE sở hữu (rag-design §3); MUST NOT tự tạo/sửa bảng.
- **FR-012**: Ghi MUST idempotent: chạy lại cùng input không tạo bản ghi mới và không gọi embed cho bản ghi đã có.
- **FR-013**: Khi một cặp bị sửa hoặc bị xóa khỏi bộ dữ liệu, lần chạy sau MUST loại bản ghi cũ của cặp đó khỏi kết
  quả truy hồi. Việc loại bỏ MUST chỉ áp dụng cho bản ghi có cùng `dataset` với lần chạy; MUST NOT đụng tới bản ghi từ
  bộ dữ liệu khác (seed của AIE, dữ liệu 009/012).
- **FR-014**: Mỗi bản ghi MUST lưu model embedding đã dùng.
- **FR-015**: Lỗi tạm thời từ provider embedding MUST được retry có giới hạn; lỗi còn lại MUST được đếm và báo, không
  làm mất các bản ghi đã thành công.
- **FR-016**: Mỗi lần chạy MUST in thống kê: số record vào, số bản ghi, tỉ lệ dedup, số embedding lỗi, số bản ghi
  thêm/bỏ qua/loại bỏ (constitution V).
- **FR-017**: Truy hồi MUST nhận truy vấn + bộ lọc (nguồn, loại bản ghi, nhóm, độ khó, `topic_id`) + k (mặc định 5) và
  trả bản ghi kèm điểm tương đồng và định danh cặp, sắp giảm dần; MUST log định danh và điểm của mỗi lần gọi
  (rag-design §4).
- **FR-018**: MUST tra được bản ghi `qa_pair` theo định danh cặp mà không qua tìm kiếm tương đồng.
- **FR-019**: Thiếu API key hoặc kho tri thức chưa sẵn sàng MUST dừng trước khi ghi, thông báo rõ nguyên nhân.

**Đánh giá truy hồi (US4 · S1-DE-4 · DE soạn, AIE duyệt)**

- **FR-020**: MUST có golden set ≥ 20 truy vấn phủ đủ 5 nhóm (a)–(e), mỗi truy vấn gắn ≥ 1 định danh cặp đúng trong
  kho của ta và ghi nguồn; truy vấn MUST NOT trùng nguyên văn câu hỏi đã index. DE soạn truy vấn và nhãn; nhãn MUST
  được AIE duyệt trước khi dùng để báo cáo.
- **FR-021**: Lệnh đánh giá MUST báo recall@5 tổng và theo nhóm, cùng top-3 của mỗi truy vấn để review tay. Mục tiêu
  recall@5 ≥ 0.8; chưa đạt MUST được ghi trong báo cáo kèm nhóm yếu nhất, nhưng MUST NOT chặn merge.

**Crawler (US5 · S1-DE-2 · DE)**

- **FR-022**: Crawler MUST kiểm tra robots.txt, có giới hạn tốc độ cấu hình được, giới hạn số trang, và hỗ trợ trang
  cần JavaScript.
- **FR-023**: Crawler MUST NOT lưu thông tin cá nhân (email, số điện thoại người liên hệ); MUST lưu URL nguồn và thời
  điểm crawl cho mỗi record.
- **FR-024**: Dữ liệu thô và đã xử lý MUST nằm ngoài git; chỉ seed curated được commit (constitution V).
- **FR-025**: Crawler trả 0 record MUST báo lỗi.

### Key Entities

- **Interview Q&A Item**: một cặp hỏi/đáp mẫu; định danh ổn định, `topic_id`, câu hỏi, đáp án, độ khó, ngôn ngữ, tags,
  nguồn, giấy phép, synthetic. Nhóm kiến thức suy ra từ topic.
- **Topic (catalog, AIE sở hữu)**: id, track, category, levels; DE chỉ đọc.
- **Knowledge Chunk**: một bản ghi trong kho tri thức; nội dung, loại (`question | qa_pair`), nguồn
  (`interview_qa`), nhóm, độ khó, `topic_id`, ngôn ngữ, định danh cặp, `dataset`, hash nội dung, vector, model
  embedding. Một Q&A Item → hai Knowledge Chunk.
- **Pipeline Run Report**: thống kê một lần chạy (vào/ra/dedup/lỗi embed/thêm/bỏ qua/loại) và danh sách record bị
  loại kèm lý do.
- **Golden Query**: truy vấn, nhóm (a–e), bộ lọc, định danh cặp đúng, nguồn, trạng thái duyệt.
- **Crawl Source**: tên, URL gốc, giấy phép/điều khoản, chính sách robots, giới hạn tốc độ; **Raw Record**: nội dung
  thô, URL, thời điểm crawl.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Bộ dữ liệu có ≥ 200 cặp hợp lệ; 100% có `topic_id` thuộc catalog; mỗi topic trong catalog lúc nghiệm thu
  có ≥ 2 cặp; mỗi topic có level `middle`/`senior` có ≥ 2 cặp `hard` *(sửa 2026-10-19, thay "mỗi mức độ khó ≥ 20%")*.
- **SC-002** *(sửa 2026-10-19)*: 100% cặp có `source`; 0 cặp chứa thông tin cá nhân; 0 cặp trùng tuyệt đối; 0 nội
  dung crawl trong git; review mẫu được ghi lại cho mỗi nguồn.
- **SC-003**: Kho tri thức có ≥ 400 bản ghi `interview_qa` sau một lần chạy; ≥ 99% có vector; tỉ lệ dedup < 5%.
- **SC-004**: Chạy lại cùng input: 0 bản ghi mới, 0 lời gọi embed.
- **SC-005**: Golden set ≥ 20 truy vấn, 100% nhãn được AIE duyệt; recall@5 tổng và theo nhóm (a)–(e) được báo; mục
  tiêu recall@5 tổng ≥ 0.8.
- **SC-006**: Toàn bộ pipeline cho 200 cặp chạy xong ≤ 10 phút trên máy dev; chi phí embed < 0,1 USD.
- **SC-007**: Thành viên khác (AIE) chạy lại toàn bộ trên máy họ chỉ theo hướng dẫn, ≤ 5 lệnh, không cần hỏi DE.
- **SC-008**: Crawler mẫu lưu ≥ 50 record từ 1 nguồn, 0 truy cập vào đường dẫn robots.txt cấm, 0 email/số điện thoại.
- **SC-009**: Demo Sprint 1: AIE truy hồi được câu hỏi/đáp án mẫu liên quan cho ≥ 4/5 truy vấn demo.

## Assumptions

- **Phụ thuộc 001 (chặn US3, US4)**: `ai_db` + extension vector chưa có trên `main` (001 T016–T017 chưa làm, PR-1 #2
  chưa merge). US1, US2, US5 làm được ngay; US3/US4 chờ 001 PR-2.
- **Phụ thuộc AIE**: DDL `knowledge_chunks` (AIE sở hữu, đặt cuối `scripts/init-databases.sh` theo constitution I)
  và topic catalog đều đang ở PR #3 `feat/aie`. Nếu PR #3 đổi schema hoặc catalog, spec/plan cập nhật theo.
- **Đổi AC sprint**: AC S1-DE-1 trong `docs/sprint-plan.md` chuyển sang phân loại theo topic catalog (6 nhóm, có
  Frontend và AI); `data-pipeline.md` §4 cập nhật cùng PR. Team duyệt qua PR review.
- **Phụ thuộc catalog mở rộng**: FR-002 từ chối `topic_id` lạ, nên Q&A cho topic Frontend, DevOps và AI mới chỉ qua
  kiểm tra/index được sau khi AIE merge các YAML đề xuất. DE soạn nội dung theo id đề xuất ngay; id cần AIE chốt sớm vì
  đổi id sau phải gắn lại nhãn.
- **Chiều sâu ngoài S1**: DB/System Design còn mỏng (4–5 topic); có thể thêm topic "transaction & isolation" và
  "caching & scaling" cho mỗi track backend sau khi có số liệu từ JD (009).
- **Giấy phép**: nếu dùng nội dung CC BY-SA, file seed phát hành theo CC BY-SA (share-alike) và ghi rõ trong tài liệu
  của seed.
- **API key embedding**: Thắng giữ; CI không dùng key thật (001 FR-011).
- **Ngoài phạm vi**: `job_description` (crawl/index JD → 009;
  rag-design xếp là Stretch, AI chưa dùng); `textbook` (→ 012, kể cả `tech_notes_seed.json` của AIE); ANN index, hybrid
  search, rerank, cache truy hồi (rag-design: chỉ thêm khi số đo cần); seed `job_db`.
- **Seed mock của AIE** (`qa_seed.json`) không dùng làm golden set.
- **Nguồn crawl mẫu** (US5) chọn ở plan/research sau khi kiểm tra robots.txt và điều khoản; ưu tiên nguồn đóng góp được
  Q&A công khai cho US1 (FR-003) hoặc JD cho 009.
- Quy mô ~400 bản ghi: truy hồi quét toàn bộ (không index ANN) vẫn đủ nhanh (rag-design §3).
- **Lệch phát hiện khi review (báo AIE/FSD; ngoài phạm vi DE, 005 không sửa file của họ)**:
  1. Biên độ khó theo level lệch giữa docs và code: Middle docs 2–4 / code `(2, 5)`; Senior docs 2–5 / code `(3, 5)`
     (`docs/ai-service/01` §2.1 vs `LEVEL_CONFIG` trong `models_common.py`) — AIE.
  2. Mapping 1–5 → nhãn 3 mức mới có trong docs, chưa có hàm trong code; S1-AIE-2 cần khi lọc — AIE.
  3. Contract interview-service còn mô hình trước ADR-008: `POST /sessions` nhận `category` + `difficulty` (có
     "Frontend"), `interview_sessions` lưu category/difficulty; ai-service nhận `track` + `level`. Danh sách track ứng
     viên chọn tăng từ 4 lên 6 (thêm `frontend_react`, `devops_engineer`) — ảnh hưởng contract session và UI của FSD.
  4. `TurnInfo.difficulty` (số 1–5) chưa có cột tương ứng trong `interview_turns` — FSD.
  5. `qa_seed.json` của AIE thiếu `qa_id` và `topic_id`; 10 cặp Frontend gán được `fe.*` khi track Frontend merge — AIE.
  6. Thêm `"Frontend"` vào `Category` (`app/catalog/models.py`), danh sách category trong `rag-design.md` §3 và
     `data-model.md` (`knowledge_chunks.category`); review + merge 3 file trong `contracts/topic-catalog-proposal/`.
     Track mới còn cần: keyword trong `_TRACK_HINTS` (`mock_cv_parser.py`), nếu không `track_relevance` luôn `low` và
     phase intro không dùng dự án trong CV; cập nhật enum `track` trong `docs/ai-service/01`, `07`, `README` — AIE.
  7. FR-002 chỉ cho `topic_id` trỏ tới topic, không tới scenario (scenario không có `category`) → phase scenario không
     có `interview_qa` theo topic và không dùng được fallback theo category. Cần AIE xác nhận phase scenario không dựa
     vào `interview_qa` — AIE.
