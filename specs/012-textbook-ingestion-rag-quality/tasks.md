---

description: "Task list for 012-textbook-ingestion-rag-quality"
---

# Tasks: Textbook Ingestion & RAG Quality

**Input**: Design documents from `/specs/012-textbook-ingestion-rag-quality/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: constitution VI bắt buộc test cho logic chính của Python app → mỗi module logic có task pytest **offline**
(không mạng, không key, không DB; fixture HTML / markdown / manifest tự soạn, fetcher giả). Crawl thật và DB kiểm bằng
[quickstart.md](quickstart.md).

**Organization**: theo user story, nhưng phase theo **thứ tự giao hàng**: code của US1 và US3 (PR-A) phải xong trước
khi chạy dữ liệu lô thử, vì FR-021 bắt soát đoạn trước khi ghi vào kho. Mọi đường dẫn code tương đối
`apps/data-pipeline/`. Chạy lệnh trong `apps/data-pipeline/` bằng `python -m pipeline <lệnh>` / `python -m pytest`.

## Format: `[ID] [P?] [Ai] [Story] Description`

- **[P]**: chạy song song được (khác file, không phụ thuộc task chưa xong)
- **[Ai]**: `[W]` worker (subagent `model: "sonnet"`); `[R]` reviewer (subagent `code-reviewer`, `model: "opus"`);
  `[DE]` DE tự làm hoặc tự quyết; `[AIE]` việc của AIE
- **[Story]**: US1..US4 theo spec.md; mã `S3-DE-#` để truy vết về sprint plan
- Prompt giao worker MUST kèm work context `c:\Users\NITRO\ai-recruitment-platform`, reports
  `plans/reports/`, plans `plans/` (orchestration protocol), đường dẫn spec này, và mã task
- Task code: worker đọc `research.md` mục được nêu + contract liên quan trước khi viết; mỗi file < 200 dòng; comment
  mô tả; sau khi sửa chạy `python -m pytest -q` và dán kết quả

---

## Phase 1: Setup · PR-A `feat/data-pipeline/textbook-pipeline`

**Purpose**: branch, đường dẫn, thư mục dữ liệu

- [ ] T001 [DE] Merge PR spec/plan (`docs/textbook-ingestion-spec`) sau khi AIE xem; tạo branch `feat/data-pipeline/textbook-pipeline` từ `main` mới nhất
- [x] T002 [W] Thêm hằng vào `pipeline/settings.py` theo data-model.md §1: `TEXTBOOK_SOURCES_DIR = APP_DIR / "data" / "seeds" / "textbook_sources"`, `TEXTBOOK_RAW_DIR = RAW_DIR / "textbook"`, `TEXTBOOK_PROCESSED_DIR = PROCESSED_DIR / "textbook"`, `TEXTBOOK_REVIEW_WORK_DIR = TEXTBOOK_RAW_DIR / "review"`, `TEXTBOOK_DECISIONS_DIR = APP_DIR / "data" / "reviews" / "textbook"`, `TEXTBOOK_SOURCE_TYPE = "textbook"`, `TEXTBOOK_DATASET_PREFIX = "de_textbook_"`, `SYSTEM_DESIGN_CATEGORY = "System Design"`. Kiểm `.gitignore` gốc đã bao `data/raw/` và `data/processed/`; không thêm dòng nếu đã có

---

## Phase 2: Foundational (chặn mọi story)

**Purpose**: parser section dùng chung, đọc catalog, manifest, đăng ký lệnh, sửa đường ghi

- [x] T003 [W] Tạo `crawlers/docs_section_parser.py` (research R5): chuyển `parse_sections`, `_block_text`, `HEADING_LEVELS`, `BLOCK_TAGS`, `NOISE_TAGS` từ `crawlers/react_docs_crawler.py` sang; thêm `content_root(soup, selector: Optional[str])` (selector CSS → `article` → `main`), `parse_html_page(html, selector) -> Optional[{title, sections}]`, và `parse_markdown_page(text) -> {title, sections}` tách theo dòng `#`, `##`, `###` (bỏ qua `#` nằm trong khối ```), cùng cấu trúc `sections[{heading_path, text}]`. `react_docs_crawler.py` import lại, không đổi hành vi
- [x] T004 [P] [W] `tests/test_docs_section_parser.py` + fixture `tests/fixtures/textbook/guide_page.html` (có sidebar, footer, `div#docContent` chứa h1/h2/h3, đoạn văn, khối code), `tests/fixtures/textbook/readme.md`: selector lấy đúng vùng nội dung, bỏ sidebar; `heading_path` đúng 3 cấp; khối code giữ dạng ```; markdown có `#` trong khối code không thành tiêu đề. `tests/test_react_docs_parse.py` vẫn xanh, không sửa
- [x] T005 [P] [W] Tạo `pipeline/textbook_catalog_tracks.py` (research R2): `load_tracks(dirs) -> Dict[track_id, Track]` đọc từng `*.yaml` trong `settings.catalog_dir()`; `Track(track_id, main_category, topic_categories: Dict[topic_id, category], scenario_ids: List[str])`; `main_category` = category xuất hiện nhiều nhất trong `topics` (hòa thì lấy category xuất hiện trước). Không import code ai-service; mã track lấy từ trường định danh của file YAML (đọc `apps/ai-service/app/catalog/java_backend.yaml` để biết tên trường). Lỗi định dạng → `CatalogError` của `topic_catalog_reader`
- [x] T006 [P] [W] `tests/test_textbook_catalog_tracks.py`: trên catalog thật của repo, `main_category` là `Backend` cho `java_backend`, `nodejs_backend`, `python_backend`; `Frontend`, `DevOps`, `AI` cho ba track còn lại; tổng số tình huống 28; `scn.java.flash-sale-inventory` thuộc `java_backend`. Thêm catalog fixture nhỏ cho trường hợp hòa
- [x] T007 [W] Tạo `pipeline/textbook_source_manifest.py` (contract textbook-source-manifest §1–§3, research R11): dataclass `SourcePage`, `Source`; `ALLOWED_LICENSES`; `load_sources(dir) -> List[Source]`; `load_scenario_queries(dir) -> Dict`; `validate_sources(sources, tracks, queries) -> (errors: List[str], warnings: List[str])` hiện thực đủ luật lỗi và cảnh báo ở contract §2 (mỗi thông báo nêu tên file + URL hoặc mã); `dataset_name(source_id)`. Hàm thuần, không I/O ngoài đọc file
- [x] T008 [P] [W] `tests/test_textbook_source_manifest.py` + fixture `tests/fixtures/textbook/sources/` (một nguồn hợp lệ, và mỗi luật lỗi một file sai tối thiểu): mỗi luật lỗi ở contract §2 có một test báo đúng lỗi; nguồn `excluded` thiếu lý do; trang nhiều track khác category chính mà không dùng `System Design`; category `Database` bị từ chối cho trang scenario; cảnh báo khi tình huống có 2 trang, khi track không có nguồn `official`
- [x] T009 [W] Tạo `pipeline/textbook_validate_command.py` (`run_validate_textbook`: in bảng track × nguồn chính thức × trang và tình huống × trang; thoát 1 khi có lỗi, hoặc có cảnh báo cùng `--strict`) và `pipeline/textbook_cli.py` (`add_parsers(sub)` + `HANDLERS` cho 7 lệnh ở contract pipeline-cli-textbook; lệnh chưa hiện thực trỏ tới hàm trả mã 2 kèm thông báo). Sửa `pipeline/__main__.py`: gọi `add_parsers(sub)` và `HANDLERS.update(...)`, không thêm parser trực tiếp (file đang 173 dòng)
- [x] T010 [W] Sửa `pipeline/knowledge_chunk_writer.py` (research R8): `WritePlan` thêm `source_types: Dict[str, str]` (dataset → `source_type`, lấy từ bản ghi trong `plan_writes`); bước dọn dùng `source_types[dataset]` thay hằng `SOURCE_TYPE`. Không đổi chữ ký `plan_writes` / `write_records`
- [x] T011 [P] [W] Thêm vào `tests/test_knowledge_chunk_writer_plan.py`: bản ghi `interview_qa` và `textbook` cùng lần chạy cho `source_types` đúng theo dataset; hash đã có ở dataset khác vào `skip_other`; hash đã có cùng dataset vào `update`. Test cũ giữ nguyên và xanh

**Checkpoint**: `python -m pytest -q` xanh; `python -m pipeline validate-textbook` chạy được trên thư mục manifest rỗng (báo "chưa có nguồn", thoát 0)

---

## Phase 3: User Story 1 (code) - Crawl, cắt đoạn, ghi kho (Priority: P1) · S3-DE-1, S3-DE-2, S3-DE-3, S3-DE-5 · PR-A

**Goal**: `crawl-textbook`, `process-textbook`, `index-textbook` chạy được cho một nguồn

**Independent Test**: quickstart §0, §2, §3 (không có bước soát) trên manifest fixture

- [x] T012 [W] [US1] Tạo `crawlers/textbook_manifest_crawler.py` (research R4): `crawl_source(source, fetch_html, fetch_markdown, now) -> (pages: List[dict], skipped: Dict[url, lý do])`; chỉ duyệt trang `status: use`; `format: html` → `parse_html_page(html, source.content_selector)`, `format: markdown` → đổi URL `github.com/<repo>/blob/<ref>/<path>` thành lời gọi `GithubRawClient.fetch` rồi `parse_markdown_page`; trang trả `None` / rỗng → `skipped` với lý do `fetch_failed`, `robots_disallowed`, `empty`; mỗi trang ra dict theo data-model §2. Không theo link
- [x] T013 [W] [US1] Tạo `pipeline/textbook_crawl_command.py` (`run_crawl_textbook`): kiểm manifest trước (lỗi → 1); bắt buộc `--source`; dựng `PoliteFetcher(base_url=homepage, delay, render)` / `GithubRawClient`; ghi `TEXTBOOK_RAW_DIR/<source_id>/<UTC>.jsonl`; in thống kê (trang trong manifest, tải được, bỏ theo lý do, thời gian); thoát 1 nếu 0 trang, 4 nếu `fetcher.blocked`. Đăng ký vào `textbook_cli.py`
- [x] T014 [P] [W] [US1] `tests/test_textbook_manifest_crawler.py`: fetcher giả trả HTML fixture → đúng số trang, đúng `sections`; URL không có trong manifest không bao giờ được gọi (đếm lời gọi); trang `status: excluded` không được gọi; fetcher trả `None` → vào `skipped`, lô không dừng; nguồn markdown gọi đúng `(repo, path)`
- [x] T015 [P] [W] [US1] Tạo `pipeline/textbook_chunker.py` (research R6): hằng `TARGET_MIN_CHARS = 320`, `TARGET_MAX_CHARS = 1000`, `HARD_MAX_CHARS = 1600`, `MIN_WORDS = 30`; `chunk_page(page) -> List[{heading_path, body}]`: section vừa cỡ → một đoạn; section dài → gói tham lam theo đoạn văn (tách ở dòng trống), khối ``` luôn đi cùng đoạn văn ngay trước; một đoạn văn đơn lẻ vượt `HARD_MAX_CHARS` → cắt ở ranh giới câu; `render_content(title, heading_path, body) -> "<title> > <h2> > <h3>\n\n<body>"`
- [x] T016 [P] [W] [US1] `tests/test_textbook_chunker.py`: section ngắn giữ nguyên; section 5.000 ký tự ra nhiều đoạn, mọi đoạn ≤ `HARD_MAX_CHARS`, nối lại đủ nội dung, không mất câu; khối code không bị tách khỏi đoạn văn trước nó; dòng đầu của `content` là đường dẫn tiêu đề; thuật ngữ và tên hàm giữ nguyên chữ hoa thường
- [x] T017 [P] [W] [US1] Tạo `pipeline/textbook_noise_filter.py` (research R7): `noise_reason(heading_path, body) -> Optional[str]` trả `blocked_heading` (tiêu đề cuối, không phân biệt hoa thường, thuộc danh sách chặn), `code_only` (ký tự trong khối ``` > 70%), `link_list` (hơn nửa số dòng là mục danh sách chỉ có link hoặc dưới 4 từ), `too_short` (< 30 từ ngoài khối code), hoặc `None`
- [x] T018 [P] [W] [US1] `tests/test_textbook_noise_filter.py`: mỗi lý do một ví dụ bị bắt; đoạn giải thích có một khối code ngắn được giữ; đoạn có danh sách gạch đầu dòng dạng câu đầy đủ được giữ; tiêu đề "See Also" bị chặn dù viết hoa
- [x] T019 [W] [US1] Tạo `pipeline/textbook_review_decisions.py` (data-model §4): `load_decisions(source_id) -> Decisions` (file chưa có → rỗng, `approved_by = ""`); `apply_decision(content, decision) -> (content | None, lý do)`: `keep` giữ nguyên, `drop` → `None`, `trim` xóa từng chuỗi `remove` (phải khớp đúng một lần, nếu không → `ValueError` nêu hash), thân còn dưới 30 từ → `None` với `too_short_after_trim`; `merge_decisions(old, new)` giữ quyết định cũ, đặt `approved_by = ""`; `save_decisions`
- [x] T020 [P] [W] [US1] `tests/test_textbook_review_decisions.py`: ba loại quyết định; `trim` với chuỗi không có trong đoạn hoặc có hai lần báo lỗi; cắt xong quá ngắn thành bỏ; gộp giữ quyết định cũ và xóa `approved_by`
- [x] T021 [W] [US1] Tạo `pipeline/textbook_record_builder.py` (data-model §3): `build_records(source, pages, decisions) -> (records, stats)`: mỗi trang → `chunk_page` → `noise_reason` → `clean_text` + `scrub_pii` → `content_hash` (hàm của `qa_record_builder`) → áp quyết định theo hash gốc → bản ghi đủ cột và `metadata` (`review`, `original_hash` khi có); `tracks`, `scenario_ids`, `topic_ids`, `category` lấy từ dòng trang trong manifest; trang có `sections` thì chỉ giữ section có tiêu đề đầu của `heading_path` nằm trong danh sách (cùng một URL được khai nhiều dòng với `sections` khác nhau, luật URL trùng tính theo cặp URL + `sections`); `topic_id` = mã đầu của `topics` hoặc `None`; dedup theo `content_hash` giữ đoạn đầu; `stats` đếm trang vào, đoạn tạo, bỏ theo từng lý do, trùng, chưa có quyết định
- [x] T022 [P] [W] [US1] `tests/test_textbook_record_builder.py`: bản ghi có `source_type = "textbook"`, `difficulty is None`, `metadata.dataset = "de_textbook_<id>"`, `chunk_type = "doc_section"`, đủ `source_url`, `license`, `license_class`, `attribution`, `heading_path`, `tracks`, `scenario_ids` đã sắp; hai trang trùng một đoạn → một bản ghi, `stats["dedup"] == 1`; email cài trong fixture (miền trông thật, vd `lienhe@congty-gia.vn`) bị xóa; đoạn `drop` không có trong kết quả; đoạn `trim` có `review = "trimmed"` và `original_hash`
- [x] T023 [W] [US1] Tạo `pipeline/textbook_process_command.py` (`run_process_textbook`): kiểm manifest; với mỗi nguồn được chọn đọc file thô mới nhất (chưa có → thông báo, thoát 1), `build_records`, ghi `TEXTBOOK_PROCESSED_DIR/<source_id>.jsonl`, in thống kê theo contract; cảnh báo khi tỉ lệ trùng ≥ 5%. Đăng ký lệnh
- [x] T024 [P] [W] [US1] `tests/test_textbook_process_command.py`: chạy với `tmp_path` làm thư mục dữ liệu (monkeypatch hằng `settings`), file thô fixture → file đã xử lý đúng số dòng; chạy hai lần cho cùng nội dung; nguồn chưa crawl → thoát 1
- [x] T025 [W] [US1] Tạo `pipeline/textbook_index_command.py` (`run_index_textbook`, contract pipeline-cli-textbook): bắt buộc `--source`; từ chối (1) khi decisions có `approved_by` rỗng hoặc còn bản ghi thiếu `metadata.review`; tách hàm thuần `check_ready(records, decisions) -> List[str]` và `index_textbook_records(conn, records, embed, probe, stored_model, known_datasets)`: `preflight` → đếm bản ghi theo `source_type` → dừng (1) nếu kho có bản ghi `textbook` thuộc dataset không có trong manifest → `existing_hashes` → `plan_writes` → `probe` chỉ khi có bản ghi mới → `write_records` → đếm lại, in trước / sau và thống kê; thoát 3 khi có embedding lỗi. Dùng `require_index_settings`, `EmbeddingClient` như `db_commands.run_index`. Đăng ký lệnh
- [x] T026 [P] [W] [US1] `tests/test_textbook_index_command.py`: `check_ready` báo lỗi khi `approved_by` rỗng, khi có bản ghi chưa soát; đạt khi đủ. Không test phần cần DB (kiểm ở quickstart §5)

**Checkpoint**: `python -m pytest -q` xanh; trên manifest fixture, `process-textbook` ra file đã xử lý

---

## Phase 4: User Story 3 (code) - Soát đoạn và báo cáo độ phủ (Priority: P2) · S3-DE-4, S4-DE-1 · PR-A

**Goal**: `review-textbook-prepare`, `review-textbook-score`, `coverage-textbook`

**Independent Test**: quickstart §3 (đoạn mồi bị bắt), §4

- [x] T027 [P] [W] [US3] Soạn `data/seeds/textbook_sources/review-canaries.json` (contract §4): 12 đoạn mồi, mỗi loại `nav`, `code_only`, `off_topic`, `reference_table` 3 đoạn, dòng đầu là đường dẫn tiêu đề giả giống đoạn thật, nội dung tự viết (không chép từ docs nào), tiếng Anh, 40–150 từ
- [x] T028 [W] [US3] Tạo `pipeline/textbook_review_prepare.py` (research R9, theo mẫu `qa_scope_check_prepare.py`): chọn bản ghi chưa có trong decisions (theo hash gốc); chia lô `--batch-size` (mặc định 25); mỗi lô chèn 3 đoạn mồi chọn và đặt vị trí theo `--seed`; `item_id` = 12 ký tự đầu của hash (đoạn mồi: hash của nội dung mồi, không phân biệt được với đoạn thật); ghi `TEXTBOOK_REVIEW_WORK_DIR/<source_id>/batch-NN.json` (`[{item_id, content}]`) và `canary-key.json` (`{batch: [item_id]}`); in số đoạn, số lô; không có đoạn cần soát → thông báo, thoát 0. Đăng ký lệnh
- [x] T029 [W] [US3] Tạo `pipeline/textbook_review_score.py`: đọc mọi `judgments-NN.jsonl`; thoát 1 không ghi gì khi thiếu / thừa `item_id`, verdict sai, đoạn mồi không `drop` (in tên các lô phải soát lại), chuỗi `remove` không khớp đúng một lần; đạt thì bỏ đoạn mồi, đổi `item_id` về hash đầy đủ, `merge_decisions` + `save_decisions`, in số `keep` / `trim` / `drop` theo lý do và danh sách `drop` + `trim` (hash, dòng tiêu đề, lý do) để DE duyệt. Đăng ký lệnh
- [x] T030 [P] [W] [US3] `tests/test_textbook_review_prepare.py` + `tests/test_textbook_review_score.py`: mỗi lô có đúng 3 đoạn mồi; cùng seed cho cùng lô; đoạn đã có quyết định không vào lô; lô không lộ trường nào đánh dấu mồi; score thoát 1 khi một đoạn mồi là `keep`, khi thiếu một `item_id`, khi `remove` không khớp; đạt thì file decisions không chứa đoạn mồi và `approved_by` rỗng
- [x] T031 [P] [W] [US3] Tạo `pipeline/textbook_keyword_rank.py` (research R10): `tokenize(text)` theo cùng quy tắc với `apps/ai-service/app/rag/bm25_index.py::tokens` (đọc file đó, chép quy tắc, không import); `Bm25(docs).top(query, k, allow: Callable[[doc], bool])` với công thức BM25 chuẩn (`k1 = 1.5`, `b = 0.75`)
- [x] T032 [W] [US3] Tạo `pipeline/textbook_coverage_command.py` (`run_coverage_textbook`, data-model §5): đọc mọi file đã xử lý + manifest + `scenario-queries.yaml`; đếm theo nguồn, track, tình huống; với mỗi tình huống chạy `Bm25.top(query_en, 3)` giới hạn ở đoạn có `category` thuộc (category chính của track, `System Design`), `keyword_hit` = có đoạn mang mã tình huống trong 3 kết quả; `--db`: embed `query_en`, tìm vector trên kho với `source_type = 'textbook'` và hai category đó, ghi `vector_hit`; ghi `coverage-report.json`, in bảng và `gaps`; `--strict` thoát 1 khi không đạt SC-001 hoặc SC-004. Nếu vượt 200 dòng, tách phần tính vào `pipeline/textbook_coverage_report.py`. Đăng ký lệnh
- [x] T033 [P] [W] [US3] `tests/test_textbook_keyword_rank.py` + `tests/test_textbook_coverage_command.py`: tài liệu chứa đúng thuật ngữ xếp trên tài liệu không chứa; bộ lọc `allow` loại đúng category; báo cáo đếm đúng số đoạn theo tình huống; tình huống 0 đoạn và tình huống trượt truy hồi vào `gaps`; `--strict` thoát 1 khi thiếu

**Checkpoint**: `python -m pytest -q` xanh toàn bộ

---

## Phase 5: Hoàn tất PR-A

- [x] T034 [W] Cập nhật `docs/architecture/data-pipeline.md` phần textbook (§ bảng nguồn S3, cây thư mục, phần Processing, ví dụ lệnh): thay phác thảo cũ (`textbook_processor.py`, `run_textbook_pipeline.sh`, 5000+ chunks) bằng cấu trúc thật và 7 lệnh, link tới `specs/012-textbook-ingestion-rag-quality/contracts/`; không chép lại contract
- [x] T035 [R] `code-reviewer` (opus) review toàn bộ PR-A theo spec + contract; báo cáo vào `plans/reports/`; worker sửa các mục reviewer nêu, chạy lại pytest
- [ ] T036 [DE] Mở PR-A (conventional commit, không nhắc công cụ AI), CI xanh, merge

---

## Phase 6: User Story 1 (dữ liệu) - Lô thử `java_backend` (Priority: P1) 🎯 MVP · PR-B `feat/data-pipeline/textbook-java-backend`

**Goal**: 4 tình huống `scn.java.*` có docs trong kho; AIE đo trước / sau

**Independent Test**: quickstart §1–§5, §7

- [ ] T037 [P] [W] [US1] Kiểm giấy phép + robots theo hướng dẫn A (`contracts/textbook-review-instructions.md`), **mỗi nguồn một worker**, ghi `data/seeds/textbook_sources/<source_id>.yaml` với `pages: []`: `spring-framework`, `spring-boot`, `spring-data-jpa`, `hibernate-orm`, `postgresql`, `system-design-primer`. Worker phải mở trang giấy phép thật và chép câu nguyên văn; không dựa vào bảng ứng viên ở research R11. Giấy phép chỉ để phân loại `open` / `restricted`, không loại nguồn (R11 sửa 2026-11-14); nguồn chỉ bị loại vì lý do truy cập. *(2026-11-14: `postgresql` → `open`, dùng; `spring-framework` kiểm theo luật cũ, đổi thành `restricted`, dùng; `system-design-primer` đang kiểm)*
- [ ] T038 [DE] [US1] Duyệt 6 file nguồn: mở `license_url`, đối chiếu `license_quote` và `license_class`; nguồn bị loại vì truy cập thì quyết có cần nguồn thay không
- [ ] T039 [W] [US1] Lập danh sách trang theo hướng dẫn B cho track `java_backend` (4 tình huống trong `apps/ai-service/app/catalog/java_backend.yaml`) từ các nguồn đã duyệt; ghi `scenario-queries.yaml` cho 4 tình huống; tài liệu Spring / Hibernate dùng category `Backend`, PostgreSQL và System Design Primer dùng `System Design`; `validate-textbook --strict` thoát 0
- [ ] T040 [DE] [US1] Duyệt danh sách trang: đọc lướt từng trang, bỏ trang tham chiếu API hoặc lạc đề, kiểm `why`
- [x] T041 [W] [US1] Chạy lần lượt cho từng nguồn của lô thử: `crawl-textbook --source <S>` (delay mặc định), `process-textbook --source <S>`, `review-textbook-prepare --source <S>`; báo thống kê từng lệnh, số trang bị bỏ kèm lý do, `git status` không có file dưới `data/raw`, `data/processed`. Nguồn bị chặn (mã 4) hoặc `content_selector` sai (0 section): dừng nguồn đó và báo, không đổi cách tải
- [x] T042 [P] [W] [US1] Soát đoạn theo hướng dẫn C, **mỗi `batch-NN.json` một worker**, ghi `judgments-NN.jsonl`
- [x] T043 [W] [US1] `review-textbook-score --source <S>` cho từng nguồn; lô bỏ sót đoạn mồi → giao lại lô đó cho worker khác (T042); tới khi thoát 0. Báo số `keep` / `trim` / `drop` và danh sách `drop` + `trim`
- [x] T044 [DE] [US1] *(2026-11-17: DE bỏ duyệt tay; `review-textbook-score` thoát 0 = qua cổng mồi → `approved_by = "auto:canary-gate"`)* ~~Duyệt danh sách `drop` + `trim` của từng nguồn; đọc mẫu ngẫu nhiên 50 đoạn `keep` (SC-006, không quá 3 đoạn nhiễu; vượt thì siết luật lọc hoặc hướng dẫn C rồi soát lại); điền `approved_by` trong từng `<S>-decisions.json`~~
- [x] T045 [W] [US1] `process-textbook` lại cho các nguồn của lô thử, `coverage-textbook`; báo bảng tình huống × số đoạn × `keyword_hit` và `gaps`. Tình huống dưới 1 đoạn hoặc trượt truy hồi: đề xuất trang bù (quay lại T039 cho tình huống đó)
- [ ] T046 [DE] [US1] Mở PR-B (manifest, `scenario-queries.yaml`, decisions; bảng độ phủ và bảng nguồn × giấy phép trong mô tả PR), merge
- [ ] T047 [DE] [US1] Từ `main` mới nhất: `index-textbook --source <S>` cho từng nguồn, chạy lần hai để xác nhận 0 bản ghi mới, `coverage-textbook --db`, hai câu SQL ở quickstart §5. Cần `.env` có DB + key embedding. Ghi số bản ghi từng `source_type` trước / sau vào task này
- [ ] T048 [DE] [US1] Báo AIE (FR-025): tên dataset, số bản ghi, category đã dùng (`Backend`, `System Design`), việc cần làm (đo nền với cờ tắt → bật `RAG_TEXTBOOK_ENABLED` → khởi động lại → đo lại), kèm 5 câu hỏi ở spec
- [ ] T049 [AIE] [US1] Đo theo quickstart §7; gửi lại tỉ lệ ý có căn cứ ở lượt scenario, độ trễ lúc bắt đầu buổi và theo lượt, trước và sau; trả lời 5 câu hỏi ở spec
- [ ] T050 [DE] [US1] Ghi số đo và quyết định vào task này (FR-024): giữ / đổi `TARGET_*_CHARS`; giữ / đổi cách gán category; nạp tiếp hay dừng. AIE chưa đo được trước 23/11 (hết Sprint 3) → quyết theo `coverage-textbook --db`, ghi rõ chưa có số đo từ ai-service

**Checkpoint**: 4/4 tình huống Java ≥ 1 đoạn trong kho; `interview_qa` không đổi; có quyết định ở T050

---

## Phase 7: User Story 2 - Năm track còn lại (Priority: P2) · PR-C… mỗi track một PR

**Goal**: 28/28 tình huống có docs; 6/6 track có nguồn chính thức

**Independent Test**: quickstart §1–§6; `coverage-textbook --strict`

Chỉ bắt đầu sau T050. Nếu T050 đổi cỡ đoạn: sửa hằng trong `textbook_chunker.py` (PR nhỏ riêng), rồi `process-textbook` + soát phần đoạn mới + `index-textbook` lại các nguồn của lô thử trước khi làm track khác.

Mỗi track lặp đúng chuỗi T037 → T047 (kiểm nguồn [W] → duyệt nguồn [DE] → danh sách trang + truy vấn [W] → duyệt [DE] → crawl / process / prepare [W] → soát [W] → score [W] → duyệt decisions + mẫu 50 đoạn [DE] → process + coverage [W] → PR + index [DE]). Nguồn dùng chung đã duyệt ở track trước không kiểm giấy phép lại, chỉ thêm trang.

- [ ] T051 [US2] Track `nodejs_backend` (4 tình huống; category riêng `Backend`). Ứng viên cần kiểm: Node.js docs, NestJS docs, Redis docs; thêm trang PostgreSQL / System Design Primer nếu tình huống cần
- [ ] T052 [US2] Track `python_backend` (4 tình huống; `Backend`). Ứng viên: Python docs, FastAPI, Django, Celery, SQLAlchemy
- [ ] T053 [US2] Track `devops_engineer` (4 tình huống; `DevOps`). Ứng viên: Kubernetes docs, Docker docs, Prometheus docs
- [ ] T054 [US2] Track `frontend_react` (4 tình huống; `Frontend`). Ứng viên: react.dev (giấy phép đã kiểm ở 005, vẫn ghi `license_url` + `license_quote`), Next.js docs, web.dev, MDN
- [ ] T055 [US2] Track `ai_engineer` (8 tình huống; `AI`). Ứng viên: scikit-learn user guide, Hugging Face docs, OWASP Top 10 for LLM Applications. Track này dễ thiếu nguồn có giấy phép mở: tình huống không đủ trang thì ghi vào `gaps`, không lấy nguồn chưa duyệt
- [ ] T056 [DE] [US2] Sau mỗi track: báo AIE số bản ghi thêm và nhắc khởi động lại ai-service để nạp lại kho từ khóa

**Checkpoint**: `validate-textbook --strict` và `coverage-textbook --strict` thoát 0, hoặc `gaps` còn lại được DE ghi lý do

---

## Phase 8: User Story 3 (dữ liệu) - Báo cáo cuối (Priority: P2) · S3-DE-4, S4-DE-1

- [ ] T057 [W] [US3] Chạy `coverage-textbook --db` trên toàn bộ; soạn `plans/reports/coverage-<ngày>-012-textbook.md`: bảng nguồn × giấy phép × số đoạn, bảng tình huống × số đoạn × `keyword_hit` × `vector_hit`, tổng theo SC-001..SC-005, SC-008, và `gaps`
- [ ] T058 [DE] [US3] Đối chiếu báo cáo với Success Criteria; ghi kết quả từng SC vào task này; SC không đạt thì quyết bù hay chấp nhận kèm lý do

---

## Phase 9: User Story 4 - Topic khó AI tự đặt câu nhiều (Priority: P3)

Chỉ làm khi AIE đã trả lời câu 5 ở spec và các phase trên đã xong.

- [ ] T059 [W] [US4] Với danh sách topic AIE đưa: thêm trang giải thích sâu vào manifest của nguồn đã duyệt, `topics: [<topic_id>]`, `category` = category của topic, `scenarios: []`; chạy chuỗi crawl → process → soát → score
- [ ] T060 [DE] [US4] Duyệt decisions, `index-textbook`, kiểm mỗi topic trong danh sách có ≥ 1 đoạn (`SELECT topic_id, count(*) … WHERE source_type = 'textbook' AND topic_id IS NOT NULL GROUP BY 1`), báo AIE

---

## Phase 10: Polish

- [ ] T061 [W] Cập nhật `docs/sprint-plan.md` (S3-DE-1..3 theo bảng "Thay đổi so với sprint plan" của spec, kèm ghi chú ngày và người chốt) và `specs/README.md` (trạng thái 012); cập nhật `specs/005-rag-knowledge-base-qa/contracts/knowledge-chunks-io.md` nếu có mục liệt kê `source_type` / `dataset` để thêm `de_textbook_*`
- [ ] T062 [DE] Nhắn AIE cập nhật `docs/ai-service/07-data-storage.md` phần Textbook theo thực tế (AIE sở hữu file đó)
- [ ] T063 [DE] Chạy lại toàn bộ quickstart §0–§6 một lượt trên `main`; tick `checklists/requirements.md` mục còn lại

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → (Phase 3 ∥ Phase 4) → Phase 5 → Phase 6 → Phase 7 → Phase 8; Phase 9 và Phase 10 sau cùng.
- Trong Phase 2: T003 → T004; T005 → T006; T007 cần T005; T008 cần T007; T009 cần T007; T010 → T011.
- Trong Phase 3: T012 cần T003, T007; T013 cần T012; T021 cần T015, T017, T019; T023 cần T021; T025 cần T010, T019, T021.
- Trong Phase 4: T028, T029 cần T019, T021; T032 cần T031, T005, T007.
- Phase 6: T037 → T038 → T039 → T040 → T041 → T042 → T043 → T044 → T045 → T046 → T047 → T048 → T049 → T050. T037 không cần code (chỉ cần contract), có thể chạy song song với Phase 2–4.
- Phase 7: năm track độc lập về dữ liệu, nhưng hai track cùng sửa manifest của một nguồn dùng chung thì làm lần lượt.

### Chạy song song

- Code (cùng lúc, khác file): {T003, T005, T010}; rồi {T004, T006, T007, T011}; rồi {T008, T009, T012, T015, T017, T019, T027, T031}; rồi {T013, T014, T016, T018, T020, T021}; rồi {T022, T023, T025, T028, T029}; rồi {T024, T026, T030, T032}; rồi T033. `textbook_cli.py` do T009 tạo; các task sau chỉ thêm một dòng đăng ký, giao cùng một worker hoặc làm lần lượt để tránh xung đột.
- Dữ liệu: T037 chạy 6 worker song song; T042 mỗi lô một worker. Tối đa 4 worker cùng lúc trên máy DE.

## Implementation Strategy

- **MVP** = Phase 1–6: code + lô thử Java trong kho + số đo của AIE. Đủ để trình bày "docs chính thức theo vị trí" cho một vị trí và quyết có nạp tiếp không.
- **Tăng dần**: mỗi track ở Phase 7 là một PR dữ liệu độc lập; dừng sau track nào cũng để lại kho nhất quán.
- **Cắt khi trễ** (constitution VII): bỏ Phase 9 trước; rồi giảm Phase 7 theo thứ tự `ai_engineer`, `frontend_react`, `devops_engineer` (giữ hai track backend còn lại vì dùng chung nguồn với lô thử). Không cắt bước soát và kiểm giấy phép.
