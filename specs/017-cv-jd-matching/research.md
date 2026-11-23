# Research: Gợi ý việc làm theo độ tương đồng CV–JD (017, GĐ1)

Mỗi mục: **Decision** / **Rationale** / **Alternatives considered**. Số liệu đo trên dữ liệu 009 ngày 2026-11-21.

## R1. Chia vị trí code

- **Decision**: index JD và bộ đánh giá nằm ở `apps/data-pipeline` (DE). Lõi chấm điểm và endpoint nội bộ là module
  riêng `apps/ai-service/app/matching/` (DE viết, AIE review). Code của AIE chỉ bị sửa ở `app/main.py`, thêm 2 dòng
  `include_router`.
- **Rationale**: lúc chạy chỉ ai-service được đọc ai_db (constitution I). Hàm embed (`LlmGateway`) và CV Parser cũng ở
  đây. Đường ghi vào `knowledge_chunks` đã có ở pipeline (`knowledge_chunk_writer`, 005 / 012).
- **Alternatives considered**: tạo service mới (constitution VII cấm thêm service khi chưa cần, lại phải viết ADR);
  đặt ở job-service (chưa có, thuộc FSD).

## R2. Nơi lưu vector JD

- **Decision**: lưu trong bảng `ai_db.knowledge_chunks` với `source_type = 'job_description'` và `metadata.dataset =
  'jd-match'`, mỗi JD một dòng. `category`, `difficulty`, `topic_id` để NULL. Thông tin dùng để lọc nằm trong `metadata`.
- **Rationale**: không đổi DDL. Constitution V đã có loại `job_description`, và `data-model.md` §5 ghi index JD là
  Stretch của DE. Đã kiểm: mọi truy vấn RAG đều lọc `source_type` (`repository.py` TOPIC/PAIR/CORPUS/COVERAGE SQL,
  `_filter_where`, `bm25_index.py:45`, mặc định `("interview_qa", "textbook")` ở `models.py:28`).
- **Alternatives considered**: bảng `job_vectors` riêng (phải thêm DDL vào phần của AIE, YAGNI); lưu ở `job_db`
  (job-service chưa có, mà ai-service không được đọc DB đó).

## R3. Định danh bản ghi và idempotency

- **Decision**: `content_hash` = md5 của văn bản đem embed, dùng `qa_record_builder.content_hash`. Lý do: cột là
  `CHAR(32)`, còn hash `sha256:` của 009 không vừa. Trước khi ghi phải kiểm hash trùng giữa các JD: bản trùng bị bỏ và
  được đếm trong thống kê. Sau đó ghi qua `plan_writes` + `write_records` có sẵn, nên JD đổi nội dung thì có hash mới,
  được insert, còn hash cũ bị dọn theo dataset.
- **Model guard**: khi hash đã có, `write_records` chỉ UPDATE metadata chứ không embed lại. Vì vậy
  `index-jd-match` phải đọc các `embedding_model` đang có của dataset. Nếu khác model đang cấu hình thì dừng (mã 1) và
  gợi ý `--rebuild`: xóa dataset rồi index lại.
- **Alternatives considered**: dùng `jd_id` làm khóa (writer định danh bằng hash, đổi sang khóa khác phải sửa đường ghi
  chung).

## R4. Văn bản đem embed

- **Decision**:
  - JD: tiêu đề, "Cấp bậc", "Nhóm", rồi đoạn "Yêu cầu" (hoặc "Công việc", hoặc mô tả nếu thiếu cả hai), toàn bộ cắt còn
    1.200 ký tự.
  - CV: `headline`, rồi mỗi kinh nghiệm (`role` — `summary`), rồi mỗi dự án (`name` — `role` — `summary`), cắt còn 1.200
    ký tự.
  - Cả hai **không** có dòng danh sách kỹ năng.
- **Rationale**: summary của 009 đã có dòng "Kỹ năng". Nếu embed dòng đó thì cosine lặp lại phần skill_match, và phép
  so sánh tách thành phần (ablation) trong bảng đánh giá không còn ý nghĩa. Mô tả công việc vẫn tự nhắc tên công nghệ.
  1.200 ký tự là khoảng 300–400 token, nên chi phí nhỏ.
- **Alternatives considered**: dùng nguyên `sections.summary` của 009 (quá ngắn, lặp kỹ năng); embed toàn văn JD (tốn,
  có đoạn phúc lợi gây nhiễu).

## R5. Cách chạy truy vấn trong ai-service

- **Decision**: giữ một snapshot chỉ mục JD trong bộ nhớ (ma trận numpy đã chuẩn hóa cùng metadata). Request đầu tiên nạp
  snapshot. Sau đó, khi snapshot quá `MATCH_INDEX_REFRESH_S` (mặc định 300 s), một task nền nạp lại, còn request vẫn
  dùng bản cũ, không chờ. Mỗi lần nạp mở **một kết nối ngắn** rồi đóng; chỉ đọc và `statement_timeout` do vai trò
  `aie_reader` trên Supabase ép (`scripts/supabase-ai-db-access.sql`), vì Supavisor bỏ tham số `options` lúc kết nối;
  cờ `default_transaction_read_only=on` + `statement_timeout` trong `options` chỉ là lớp dự phòng. Lần nạp đầu là một
  task dùng chung, mỗi request chờ nó qua `asyncio.shield` với hạn `AI_DB_CONNECT_TIMEOUT_S` + 5 s (quá hạn → 503;
  hủy thẳng psycopg có thể treo). Truy vấn:
  `SELECT content_hash, embedding::text, metadata ... WHERE source_type='job_description' AND
  metadata->>'dataset'='jd-match' AND embedding_model=%s`.
- **Rationale**:
  - Supabase mất khoảng 0,25 s mỗi vòng truy vấn (đo 29/10), còn tính cosine trên 365 × 1536 bằng numpy chưa tới 5 ms.
    Vì vậy bước tính điểm đạt < 500 ms mà không phụ thuộc mạng.
  - Mỗi 5 phút chỉ có một kết nối ngắn, nên không tranh slot của pooler với pool RAG.
  - Không động vào `PgKnowledgeRepository` của AIE, cũng không cần đăng ký adapter pgvector (ép vector sang text).
- **Alternatives considered**: tính điểm bằng SQL `<=>` mỗi request (mỗi lần mất một vòng Supabase); dùng chung pool
  RAG (phải sửa code của AIE, và pool chỉ tồn tại khi `RAG_ENABLED`).
- **Giới hạn**: cách này hợp với vài nghìn JD. Khi GĐ2 có quy mô lớn hơn thì chuyển sang SQL kèm index HNSW (DDL đã
  ghi chú sẵn).

## R6. Danh mục kỹ năng dùng chung

- **Decision**: bản gốc vẫn là `apps/data-pipeline/data/seeds/skill_dictionary.yaml` (của 009). Một bản sao được commit
  ở `apps/ai-service/app/matching/skill_dictionary.yaml`. Test bên pipeline (`test_skill_dictionary_copy_in_sync.py`)
  fail khi hai bản khác nhau. ai-service chỉ cần ánh xạ tên sang slug (khóa NFC, chữ thường, gộp khoảng trắng, giống
  `_key` của 009). Kỹ năng trong CV là dạng thẻ nên không cần `find_in_text`.
- **Rationale**: Docker build context của ai-service là `apps/ai-service`, nên không đọc được file của pipeline. Dùng test
  để giữ hai bản đồng bộ thay cho package dùng chung (YAGNI).
- **Alternatives considered**: package Python dùng chung (monorepo chưa có tooling cho Python); lưu danh mục vào ai_db
  (không có bảng phù hợp).

## R7. Level và track

- **Decision**: dùng bảng bậc và bảng ánh xạ track ở Assumptions của spec. Fresher = 1, gộp với Junior như 009. Level
  ứng viên lấy từ request; nếu không có thì suy từ `total_years_experience` theo `level_from_years` của 009. Nếu CV
  cũng không có số năm thì không lọc theo level, và level_fit = 0,5.
- **Rationale**: dùng một thang chung cho cả hai nguồn level (6 giá trị của JD, 4 giá trị của phỏng vấn).

## R8. Embedding lỗi và chế độ mock

- **Decision**:
  - Thiếu khóa, gateway lỗi, hoặc quá `MATCH_EMBED_TIMEOUT_S` (mặc định 5 s): bỏ thành phần cosine, chia lại trọng số
    theo tỉ lệ w2:w3, bật `degraded` kèm lý do.
  - `MATCH_MOCK=true`: CV được embed bằng `hash_embedder` (băm token vào 1536 chiều rồi chuẩn hóa L2, tất định). Chỉ
    mục lấy từ `app/matching/mock_jobs.json`, khoảng 12 JD tự soạn, không lấy từ dữ liệu crawl. Ở chế độ này không
    đọc ai_db và không gọi `load_llm_settings`.
- **Rationale**: vector giả không bao giờ đi vào ai_db dùng chung. CI và dev chạy được mà không cần khóa hay DB. Khi
  thiếu khóa, hệ thống vẫn trả được kết quả có ích (FR-014).

## R9. Phương pháp đánh giá

- **Decision**:
  - **Pool JD**: 36 JD thật của 009 thuộc 3 nhóm `backend`, `devops`, `ai_data`, mỗi nhóm 12 JD. Trong mỗi nhóm có
    "mẫu âm khó", ví dụ JD Java, Python và Node cùng nằm trong `backend`. As-of được cố định trong `pool.json`.
  - **CV**: 24 CV tổng hợp viết trực tiếp dưới dạng `CvProfile` để bỏ qua sai số của CV Parser, chia 3 nhóm × 4 track
    × 2 level.
  - **Nhãn**: 0 / 1 / 2 cho mọi cặp qua lọc cứng, khoảng 24 × 8–12 ≈ 250 cặp. Người gán xem bảng soát xếp ngẫu nhiên,
    không có điểm của hệ thống.
  - **Chạy**: gọi endpoint thật với `job_ids` = pool, `page_size` = 50. Xếp lại theo từng thành phần để có baseline
    (chỉ skill_match, chỉ cosine), nên không phải chép công thức sang chỗ khác. Lệnh dừng nếu có phản hồi nào bị
    `degraded` hoặc `mock`.
  - **Độ trễ**: phần tính điểm lấy từ `timing_ms.score` của server, toàn bộ request đo phía client, chạy cả khi có và
    không có `job_ids`, 4 vòng.
  - **Chi phí**: token lấy từ `metadata.usage` và run report của index, đơn giá đặt trong cấu hình.
- **Rationale**: có mẫu âm khó thì P@5 mới phân biệt được các cách tính. Xếp lại từ chính các thành phần mà endpoint trả
  về thì DRY và đo đúng code đang chạy.
- **Gán nhãn** (owner chốt 2026-11-22): worker LLM gán mọi cặp theo [label-rubric.md](label-rubric.md); DE gán mù
  khoảng 20% (2 cặp mỗi CV) trên một trang artifact; báo kappa có trọng số (quadratic). Nhãn cuối lấy toàn bộ của LLM (owner chốt 2026-11-22: DE chấm rộng tay hơn, giữ một chuẩn chặt cho cả 264 cặp); nhãn DE chỉ dùng đo đồng thuận.
  `labels.json` ghi `method = "llm+de-blind-20"`. Vì gán nhãn trước khi có endpoint (PR-2), tập cặp qua lọc cứng được
  tính bằng bản sao luật lọc (cùng nhóm, `deadline >= as_of`, lệch bậc ≤ 1, JD không level thì qua). Khi PR-2 merge,
  `match-eval` kiểm hai tập bằng nhau; cặp chênh thì gán bổ sung.
- **Ngôn ngữ** (owner chốt 2026-11-22): 24 CV viết tiếng Việt, tên công nghệ giữ tiếng Anh như CV IT trong nước. JD giữ
  nguyên bản gốc (pool có 18 vi / 17 en / 1 trộn, gần tỉ lệ 009) vì chỉ mục embed bản gốc. Bảng kết quả tách nDCG@5 theo
  cặp cùng ngôn ngữ và khác ngôn ngữ để thấy cosine có bị phạt khi CV và JD khác ngôn ngữ không.
- **Người gán xem toàn văn JD** (mô tả + yêu cầu, không cắt); lần gán LLM đầu cắt 2.500 ký tự làm mất phần yêu cầu của
  một số JD nên bị bỏ, chỉ giữ để so độ ổn định.
- **Sửa rubric một lần** (2026-11-22, sau lần đo kappa đầu = 0,659 trên 48 cặp): CV và JD backend khác ngôn ngữ chính
  → 0, trừ khi JD ghi rõ nhận ngôn ngữ khác (tối đa 1). Lý do: nhà tuyển dụng trong nước lọc theo ngôn ngữ chính; DE
  chấm như vậy từ đầu, rubric cũ lấy "Node → Java" làm ví dụ nhãn 1. 88 cặp backend được LLM gán lại theo rubric mới;
  báo cáo ghi cả kappa trước và sau khi sửa.
- **Phương án đã bỏ**: DE gán toàn bộ (tốn thời gian, nhãn một người); LLM gán + DE soát có xem nhãn LLM (không có số
  đồng thuận độc lập).

## R10. Thứ tự PR

PR-0 docs (spec, plan, tasks, README specs, sprint-plan) → PR-1 index pipeline (không cần AIE) → PR-2 module ai-service
(chờ AIE đồng ý) → PR-3 dữ liệu và kết quả đánh giá. GĐ2 chỉ có contract nháp
([contracts/gd2-job-service-draft.md](contracts/gd2-job-service-draft.md)).
