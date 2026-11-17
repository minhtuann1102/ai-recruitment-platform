# Research: Textbook Ingestion & RAG Quality

Mỗi mục: Decision / Rationale / Alternatives. **VERIFY** = kiểm chứng lúc implement. Phần đọc code ghi ngày
2026-11-14, trên `main` sau PR #89.

## R1. Tập dữ liệu theo nguồn, không theo track

- **Decision**: mỗi nguồn một `metadata.dataset = "de_textbook_<source_id>"` (ví dụ `de_textbook_postgresql`). Một lô
  (track) là một nhóm nguồn. Trang dùng chung cho track sau được thêm vào manifest của nguồn đó rồi `index-textbook`
  lại nguồn đó.
- **Rationale**: `knowledge_chunk_writer.plan_writes` phân nhánh theo `(content_hash, dataset)`: cùng dataset thì
  `UPDATE` metadata (không embed lại), khác dataset thì bỏ qua. Nếu dataset theo track, trang PostgreSQL nạp ở track
  Java sẽ bị bỏ qua ở track Node.js và metadata không ghi được track thứ hai (trái FR-017). Dataset theo nguồn thì lần
  nạp sau cập nhật `tracks`, `scenario_ids` qua nhánh `UPDATE`.
- **Alternatives**: dataset theo track (loại, lý do trên); một dataset chung `de_textbook` (loại: nạp lại một nguồn
  phải có đủ dữ liệu thô của mọi nguồn, nếu không bước dọn sẽ xóa nguồn khác).

## R2. Giá trị `category`

- **Decision**: `category` của trang ghi trong manifest, chỉ nhận: category chính của track mà trang phục vụ, hoặc
  `System Design`. Lệnh kiểm manifest tính category chính của từng track từ catalog (category xuất hiện nhiều nhất
  trong `topics`) và báo lỗi nếu trang khai category khác hai giá trị đó, hoặc khai nhiều track khác category chính mà
  không dùng `System Design`. Trang của US4 (gắn `topic_ids`) lấy category của topic.
- **Rationale**: phase scenario tìm với `categories = (category chính, "System Design")`
  (`apps/ai-service/app/plan_snippets.py`, `scenario_categories`; `turn_reference_snippets._filters`). Category chính
  hiện là: `java_backend`, `nodejs_backend`, `python_backend` → `Backend`; `frontend_react` → `Frontend`;
  `devops_engineer` → `DevOps`; `ai_engineer` → `AI`. Đoạn ghi `Database` không bao giờ được scenario tìm thấy.
  `content_hash` là khóa duy nhất nên một đoạn chỉ có một category; tài liệu dùng chung phải vào `System Design`.
- **Alternatives**: chép cứng bảng category vào pipeline (loại: lệch khi AIE sửa catalog); ghi `Database` cho docs
  PostgreSQL (loại: scenario không thấy).
- **VERIFY**: đọc lại `scenario_categories` trước khi nạp lô thử.

## R3. Manifest nguồn

- **Decision**: một file YAML mỗi nguồn tại `apps/data-pipeline/data/seeds/textbook_sources/<source_id>.yaml`, được
  commit. Thêm `scenario-queries.yaml` cùng thư mục: mỗi `scn.*` một truy vấn tiếng Anh và 3–6 thuật ngữ, dùng cho
  kiểm tra truy hồi. Định dạng: [contracts/textbook-source-manifest.md](contracts/textbook-source-manifest.md).
- **Rationale**: `data/seeds/` là nơi dữ liệu curated nhỏ được commit (constitution V); YAML đã là dependency
  (`pyyaml`), dễ review trong PR. Truy vấn tiếng Anh cần vì tiêu đề tình huống là tiếng Việt còn docs tiếng Anh, tìm
  bằng từ khóa với tiêu đề gốc sẽ trượt.
- **Alternatives**: một file chung cho mọi nguồn (loại: xung đột khi nhiều worker cùng sửa); CSV (loại: danh sách
  lồng `tracks`, `scenarios` khó ghi).

## R4. Crawl theo manifest

- **Decision**: `crawl-textbook --source <id>` chỉ tải URL có `status: use` trong manifest, không theo link. Trang
  HTML dùng `PoliteFetcher` (robots, nghỉ, `--render`); nguồn nằm trên GitHub (`format: markdown`, ví dụ System Design
  Primer) dùng `GithubRawClient`. Kết quả ghi `data/raw/textbook/<source_id>/<UTC>.jsonl`, mỗi dòng một trang.
- **Rationale**: danh sách trang đã được duyệt là ranh giới giấy phép và phạm vi (FR-007); không theo link thì số
  request bằng số trang, crawl lại cho kết quả giống nhau. Hai client đã có test.
- **Alternatives**: crawl theo tiền tố như `react_docs_crawler` (loại: kéo cả trang tham chiếu API, trái FR-003).

## R5. Tách section dùng chung

- **Decision**: chuyển `parse_sections` và các hằng liên quan từ `crawlers/react_docs_crawler.py` sang
  `crawlers/docs_section_parser.py`, nhận thêm bộ chọn CSS vùng nội dung (`content_selector` trong manifest, mặc định
  `article`, rồi `main`). `react_docs_crawler.py` import lại hàm này. Nguồn markdown: tách theo dòng tiêu đề `#`,
  `##`, `###` thành cùng cấu trúc `sections[{heading_path, text}]`.
- **Rationale**: DRY; mỗi site docs đặt nội dung trong khối khác nhau nên cần bộ chọn theo nguồn.
  `tests/test_react_docs_parse.py` giữ hành vi cũ.
- **Alternatives**: viết parser riêng cho từng site (loại: lặp code); thư viện chuyển HTML sang markdown (loại: thêm
  dependency cho việc parser hiện có đã làm).
- **VERIFY**: bộ chọn của từng nguồn do worker lập manifest tìm và kiểm trên một trang thật.

## R6. Cắt đoạn và cỡ đoạn

- **Decision**: mỗi section thành một hoặc nhiều đoạn; dòng đầu của đoạn là đường dẫn tiêu đề (`Tên trang > H2 > H3`).
  Ước lượng token = số ký tự / 4. Mục tiêu 320–1.000 ký tự phần thân, tối đa 1.600. Section dài hơn tối đa thì gói
  tham lam theo đoạn văn; khối code luôn đi cùng đoạn văn đứng ngay trước nó. Section dưới 30 từ bị bỏ
  (`too_short`). Ba hằng số nằm trong `textbook_chunker.py`, đổi sau lô thử.
- **Rationale**: lượt chấm lấy tối đa 3 đoạn trong 600 token (`TURN_K, TURN_TOKENS` trong
  `turn_reference_snippets.py`), nên đoạn trên ~200 token sẽ bị cắt hoặc chiếm chỗ đoạn khác; đoạn ngắn một ý cũng
  hợp BM25. Không thêm thư viện đếm token: sai số của ước lượng không ảnh hưởng quyết định.
- **Alternatives**: cắt cửa sổ trượt cố định có chồng lấn (loại: cắt ngang ý, sinh đoạn gần trùng); một section một
  đoạn bất kể độ dài (loại: section hướng dẫn dài vài nghìn chữ).

## R7. Lọc nhiễu tự động

- **Decision**: bỏ đoạn và đếm theo lý do khi: tiêu đề cuối thuộc danh sách chặn (`see also`, `table of contents`,
  `release notes`, `changelog`, `next steps`, `further reading`, `feedback`, `what's next`); tỉ lệ ký tự trong khối code
  trên 70%; hơn một nửa số dòng là mục danh sách chỉ có link; dưới 30 từ. Lọc trước bước soát của worker.
- **Rationale**: các loại này nhận ra được bằng luật, không cần worker; giảm số đoạn phải soát.
- **Alternatives**: giao hết cho worker (loại: tốn lượt soát cho thứ luật làm được).

## R8. Sửa nhỏ ở đường ghi

- **Decision**: `write_records` dọn bản ghi cũ theo `source_type` của bản ghi trong lần chạy thay cho hằng
  `SOURCE_TYPE = "interview_qa"`: `WritePlan` giữ thêm `source_types: {dataset: source_type}`. Lệnh
  `index-textbook --source <id>` dựng bản ghi từ file đã xử lý của nguồn đó rồi gọi `preflight`, `existing_hashes`,
  `plan_writes`, `write_records` sẵn có.
- **Rationale**: `_DELETE_SQL` hiện lọc `source_type = 'interview_qa'`, nên bản ghi `textbook` lỗi thời không bao giờ
  được dọn. Bước dọn vẫn giới hạn theo dataset có mặt trong lần chạy, nên `index` của Q&A không xóa `textbook` và
  ngược lại (FR-019).
- **Alternatives**: viết đường ghi riêng cho textbook (loại: lặp logic đã có test).
- **VERIFY**: test `plan_writes` + dọn với hai `source_type`; đếm bản ghi từng `source_type` trước và sau trên kho
  thật ở lô thử.

## R9. Soát đoạn bằng worker

- **Decision**: hai lệnh theo mẫu `scope-check-prepare` / `scope-check-score` của 005.
  `review-textbook-prepare --source <id>` chia đoạn thành lô 25, chèn 3 đoạn mồi mỗi lô ở vị trí theo seed, ghi
  `data/raw/textbook/review/<source_id>/batch-NN.json`. Worker ghi `judgments-NN.jsonl`, mỗi đoạn một kết luận:
  `keep`, `drop` (kèm lý do), hoặc `trim` (kèm danh sách chuỗi con nguyên văn cần cắt).
  `review-textbook-score --source <id>` kiểm đủ đoạn, kiểm mọi đoạn mồi là `drop`, kiểm chuỗi `trim` có thật trong
  đoạn, rồi ghi `data/reviews/textbook/<source_id>-decisions.json` (khóa theo `content_hash`, được commit sau khi DE
  duyệt). `process-textbook` áp quyết định; `index-textbook` từ chối đoạn chưa có quyết định.
- **Rationale**: `trim` chỉ cắt, không viết lại, nên giữ nguyên chữ của docs và máy kiểm được. Đoạn mồi là cách 005
  dùng để phát hiện worker dễ dãi. Quyết định khóa theo hash nên crawl lại nội dung không đổi thì không phải soát lại.
- **Alternatives**: cho worker viết lại đoạn (loại: thành nội dung tự viết, trái "Ngoài phạm vi"); chỉ soát mẫu
  (loại: tối đa 1.500 đoạn, soát hết được).
- Hướng dẫn worker: [contracts/textbook-review-instructions.md](contracts/textbook-review-instructions.md).

## R10. Báo cáo độ phủ và kiểm tra truy hồi

- **Decision**: `coverage-textbook` chạy offline trên các đoạn đã xử lý: số đoạn theo nguồn, track, tình huống; tình
  huống dưới 1 và dưới 3 đoạn; bảng nguồn × giấy phép; kiểm tra từ khóa bằng BM25 tự cài đặt nhỏ
  (`textbook_keyword_rank.py`) với truy vấn tiếng Anh của từng tình huống, lọc theo hai category của track, đạt khi
  có đoạn mang mã tình huống đó trong 3 kết quả đầu. Thêm `--db`: lặp lại bằng tìm vector trên kho thật.
- **Rationale**: tìm theo lượt của ai-service là BM25 nên kiểm tra từ khóa là phép đo sát nhất, lại chạy được trước
  khi tốn embedding. Pipeline không import code ai-service (005 R1), nên cần bản BM25 riêng; tách từ theo cùng quy tắc
  với `app/rag/bm25_index.tokens`.
- **Alternatives**: chỉ đo vector (loại: không phản ánh đường theo lượt); thêm thư viện `rank_bm25` (loại: khoảng 40
  dòng tự viết là đủ).
- **Giới hạn**: bản BM25 của pipeline xấp xỉ bản của ai-service; số đo chính thức là của AIE (SC-007).

## R11. Giấy phép

- **Decision (sửa 2026-11-14, DE chốt: "làm đồ án, khi nào bán thì tính sau")**: giấy phép không còn là lý do loại
  nguồn. Mỗi nguồn ghi `license_class`:
  - `open`: `license` thuộc danh sách mở: `CC0-1.0`, CC-BY và CC-BY-SA mọi phiên bản, `MIT`, `Apache-2.0`,
    `BSD-2-Clause`, `BSD-3-Clause`, `PSF-2.0`, `PostgreSQL`.
  - `restricted`: mọi trường hợp khác (điều khoản riêng, chỉ phi thương mại, "All rights reserved", giấy phép chỉ nêu
    mã nguồn, không tìm thấy tuyên bố). `license` ghi `LicenseRef-<tên>` cho điều khoản riêng hoặc `NOASSERTION` khi
    không tìm thấy.
  Cả hai loại đều `status: use`. Manifest vẫn ghi `license_url` và `license_quote` nguyên văn (không tìm thấy tuyên bố
  thì `license_quote` ghi câu bản quyền ở chân trang và `license_url` là trang đó). `license_class` chép vào
  `metadata` của từng đoạn. Nguồn chỉ bị loại vì truy cập: robots cấm đường dẫn docs, site trả 403 / trang thử thách,
  nội dung sau đăng nhập hoặc trả phí, điều khoản cấm đích danh thu thập tự động (cùng ranh giới với 009).
- **Rationale**: đồ án học thuật, nội bộ, không thu phí, không công bố lại nội dung; cùng mức rủi ro DE đã chấp nhận ở
  009 (itviec §2.2). Bản kiểm đầu tiên theo luật chặt đã loại Spring Framework, nguồn mà đề cương nêu đích danh, dù
  thông báo của Spring cho phép sao chép không thu phí kèm dòng bản quyền. Giữ bằng chứng và `license_class` để khi
  thương mại hóa chỉ cần lọc `license_class = 'restricted'` ra khỏi kho rồi rà lại từng nguồn.
- **Ghi nguồn đầy đủ**: giấy phép yêu cầu kèm nguyên văn thông báo (ví dụ PostgreSQL: dòng bản quyền + đoạn cấp phép +
  hai đoạn miễn trừ) được lưu nguyên văn trong `data/seeds/textbook_sources/notices/<source_id>.txt`; `attribution`
  của đoạn ghi dòng bản quyền và tên file thông báo.
- **Alternatives**: giữ danh sách cho phép chặt (loại: mất Spring, lệch đề cương); bỏ hẳn việc ghi giấy phép (loại:
  không lọc lại được về sau, và SC-003 cần giấy phép trên từng đoạn).
- **Nguồn ứng viên, CHƯA kiểm giấy phép** (worker kiểm ở T-manifest, không dùng bảng này làm bằng chứng):

| Track | Ứng viên chính thức | Dùng chung (`System Design`) |
|---|---|---|
| `java_backend` (lô thử) | Spring Framework reference, Spring Boot reference, Spring Data JPA, Hibernate ORM | PostgreSQL docs, System Design Primer |
| `nodejs_backend` | Node.js docs (Learn / Guides), NestJS docs | Redis docs, PostgreSQL docs |
| `python_backend` | Python docs, FastAPI docs, Django docs, Celery docs, SQLAlchemy docs | PostgreSQL docs |
| `frontend_react` | react.dev (CC-BY-4.0, đã kiểm ở 005), Next.js docs, web.dev, MDN | — |
| `devops_engineer` | Kubernetes docs, Docker docs, Prometheus docs | — |
| `ai_engineer` | scikit-learn user guide, Hugging Face docs, OWASP Top 10 for LLM Applications | — |

## R12. Phân vai worker và người quyết

- **Decision**: worker (subagent `model: "sonnet"`): kiểm giấy phép và robots từng nguồn, lập manifest theo tình
  huống, soạn truy vấn tiếng Anh, soát đoạn, implement từng phase code, chạy test. Người duyệt (DE, hoặc subagent
  `model: "opus"` cho `code-reviewer`): duyệt manifest, duyệt danh sách `drop` / `trim`, đọc mẫu 50 đoạn (SC-006),
  review code trước PR, quyết nạp tiếp sau lô thử.
- **Rationale**: quy tắc "Subagent Models" trong `CLAUDE.md`: việc làm hoặc kiểm từng mục theo hướng dẫn là worker;
  việc quyết cách làm hoặc đánh giá cả task là planner / reviewer.

## R13. Lô thử

- **Decision**: `java_backend`, 4 tình huống: `scn.java.order-api-crud`, `scn.java.flash-sale-inventory`,
  `scn.java.payment-idempotency`, `scn.java.slow-query-incident`. Nhóm nguồn dự kiến: tài liệu Spring (category
  `Backend`), PostgreSQL và System Design Primer (category `System Design`).
- **Rationale**: `docs/ai-service/07-data-storage.md` xếp Java/Spring ưu tiên; bốn tình huống trải từ CRUD tới đồng
  thời, idempotency và điều tra truy vấn chậm, đủ để thử cả tài liệu riêng lẫn tài liệu dùng chung.
- **Alternatives**: `frontend_react` vì đã có crawler react.dev (loại: Frontend bị hạ ưu tiên, và crawler cũ đi theo
  tiền tố chứ không theo manifest).

## R14. ai-service đọc bản ghi `textbook` thế nào

- **Finding**: `Chunk.dedup_key = qa_id or id` nên bản ghi không có `qa_id` không bị gộp nhầm; ai-service đọc
  `metadata.source_url`, `metadata.license`, `metadata.chunk_type`; kho BM25 nạp mọi bản ghi `source_type = 'textbook'`
  (`rag/repository.py`); bộ lọc `difficulty` khớp cả bản ghi `difficulty` NULL; truy vấn vector lọc theo
  `embedding_model`.
- **Decision**: `metadata.chunk_type = "doc_section"`, không ghi `qa_id`; `embedding_model` lấy từ
  `require_index_settings().stored_model` như Q&A.
- **VERIFY**: sau lô thử, AIE xác nhận log `bm25_corpus_loaded` tăng đúng số bản ghi đã nạp.
