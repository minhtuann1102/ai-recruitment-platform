---

description: "Task list for feature 017 cv-jd-matching (GĐ1)"
---

# Tasks: Gợi ý việc làm theo độ tương đồng CV–JD (GĐ1)

**Input**: Design documents from `/specs/017-cv-jd-matching/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md),
[contracts/](contracts/)

**Tests**: bắt buộc. Owner yêu cầu unit test + integration test; constitution VI đòi Python service có test cho logic
chính. Mọi test chạy offline: không mạng, không DB, không khóa.

**Organization**: một phase cho mỗi user story GĐ1, mỗi phase ứng với một PR (plan "Thứ tự PR"). US4–US6 thuộc GĐ2, chỉ
có contract nháp, không có task code.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: chạy song song được (khác file, không phụ thuộc task chưa xong)
- Đường dẫn tính từ gốc repo

---

## Phase 1: Setup — PR-0 `docs/cv-jd-matching-spec`

- [x] T001 Thêm dòng 017 vào bảng ở `specs/README.md`, gồm: Sprint S4, Owner DE (AIE review phần ai-service), Spec Kit,
  Task S2-DE-3 (mở rộng), Phụ thuộc 009 + 005, Trạng thái "Spec + plan + tasks (2026-11-21), Stretch; chờ AIE đồng ý
  dùng `knowledge_chunks`".
- [x] T002 [P] Sửa dòng S2-DE-3 trong `docs/sprint-plan.md`: ghi mở rộng thành gợi ý CV–JD (spec 017, 2026-11-21) và
  việc đảo 009 NC-2 với lý do "embed JD cho gợi ý việc làm, vẫn không vào RAG phỏng vấn". Vẫn giữ nhãn Stretch.

---

## Phase 2: Foundational

- [x] T003 Cho `EmbeddingClient.embed` trong `apps/data-pipeline/pipeline/embedding_client.py` cộng dồn
  `response.usage.prompt_tokens` vào thuộc tính `total_tokens` (khởi tạo 0, provider không trả `usage` thì giữ nguyên).
  Thêm test vào `apps/data-pipeline/tests/test_embedding_client.py` dùng client OpenAI giả. Không đổi chữ ký `embed`.

**Checkpoint**: test pipeline hiện có vẫn xanh.

---

## Phase 3: User Story 1 — Index JD để gợi ý (P1) — PR-1 `feat/data-pipeline/jd-match-index`

**Goal**: mỗi JD 009 có track xác định được có đúng một dòng trong `knowledge_chunks` (`source_type =
'job_description'`, `metadata.dataset = 'jd-match'`). Chạy lại thì không embed lại.

**Independent Test**: chạy `index-jd-match` hai lần trên kết nối giả, lần 2 có `embedded = 0`, `inserted = 0`; chạy thật
theo [quickstart.md](quickstart.md) §3.

### Tests (viết trước, phải fail trước khi implement)

- [x] T004 [P] [US1] Test văn bản và bản ghi trong `apps/data-pipeline/tests/test_jd_match_text.py`:
  - văn bản có tiêu đề, "Cấp bậc", "Nhóm", đoạn yêu cầu, hoặc công việc / mô tả khi thiếu;
  - **không** có dòng "Kỹ năng";
  - cắt ≤ 1.200 ký tự;
  - `content_hash` 32 ký tự md5 (`qa_record_builder.content_hash`);
  - metadata đủ khóa `dataset, chunk_type, jd_id, title, group, level, deadline, skills, synthetic`;
  - `category`, `difficulty`, `topic_id` là None, `source_type` là `job_description`;
  - JD `group = null` bị loại với lý do `no_group`;
  - `language` cắt còn 5 ký tự.
- [x] T005 [P] [US1] Test lệnh trong `apps/data-pipeline/tests/test_jd_match_index_command.py`, dùng kết nối DB giả và
  embedder giả:
  - hai JD trùng hash → giữ JD có hạn nộp muộn nhất (bằng nhau thì JD đầu), `skipped_duplicate_hash = 1`;
  - dataset có `embedding_model` khác cấu hình → mã thoát 1, không gọi embed;
  - `--rebuild` xóa dataset `jd-match` (chỉ dòng `source_type = 'job_description'`) rồi ghi lại;
  - lỗi embed → mã 3, không dọn;
  - thống kê có `embedding_tokens`.

### Implementation

- [x] T006 [US1] Viết `apps/data-pipeline/pipeline/jd_match_text.py` (< 200 dòng): `build_match_text(jd) -> str` và
  `build_match_record(jd) -> (record | None, reason | None)` theo data-model §1 và research R4.
- [x] T007 [US1] Viết `apps/data-pipeline/pipeline/jd_match_index_command.py`. Thứ tự:
  1. Nạp `data/processed/jd_normalized.jsonl`.
  2. Dựng bản ghi, kiểm trùng hash.
  3. `require_index_settings`, `preflight`.
  4. Đọc `SELECT DISTINCT embedding_model ... WHERE source_type='job_description' AND metadata->>'dataset'='jd-match'`;
     lệch thì mã 1, trừ khi có `--rebuild`.
  5. `plan_writes` + `write_records` với `stored_model`.
  6. Run report qua `run_report`.
  Mã thoát theo [contracts/pipeline-cli-match.md](contracts/pipeline-cli-match.md).
- [x] T008 [US1] Viết `apps/data-pipeline/pipeline/jd_match_cli.py` (`add_parsers`, `HANDLERS`; lúc này chỉ có
  `index-jd-match [--rebuild] [--limit N]`) và đăng ký vào `apps/data-pipeline/pipeline/__main__.py` bằng một dòng
  import + `HANDLERS.update` như `textbook_cli`.
- [x] T009 [US1] Thêm mục "Index JD cho gợi ý (017)" vào `docs/architecture/data-pipeline.md`: lệnh, dataset, văn bản
  embed, kiểm model, link contract.
- [ ] T010 [US1] Chạy `pytest` của pipeline, review bằng `code-reviewer` (opus), mở PR-1. Sau khi merge: chạy
  `python -m pipeline index-jd-match` hai lần từ `main` mới nhất, dán thống kê vào PR (SC-005).

**Checkpoint**: chỉ mục JD có trong ai_db; RAG phỏng vấn không đổi.

---

## Phase 4: User Story 2 — Gợi ý việc làm từ CV (P1) — PR-2 `feat/ai-service/cv-jd-matching`

**Goal**: `POST /api/match/jobs` theo [contracts/match-jobs-api.md](contracts/match-jobs-api.md).

**Independent Test**: `TestClient` ở chế độ mock trả kết quả tất định, đúng lọc cứng và công thức; quickstart §2 và §4.

**Điều kiện trước khi mở PR**: AIE đồng ý (nội dung nhắn ở báo cáo plan).

### Tests (viết trước)

- [x] T011 [P] [US2] Viết `apps/ai-service/tests/test_matching_levels_tracks.py`:
  - bảng bậc: Intern 0; Junior / fresher / junior 1; Mid / middle 2; Senior / senior 3; Lead 4; Manager 5; None → None;
  - ánh xạ 6 track → nhóm;
  - số năm < 3 → 1, < 5 → 2, còn lại → 3; không có số năm → None.
- [x] T012 [P] [US2] Viết `apps/ai-service/tests/test_matching_skill_normalizer.py`: "Spring Boot", "springboot",
  "spring-boot" cho cùng slug (theo bí danh có trong YAML); tên ngoài danh mục được đếm unknown; khóa so khớp dùng NFC,
  chữ thường, gộp khoảng trắng.
- [x] T013 [P] [US2] Viết `apps/ai-service/tests/test_matching_scorer.py`:
  - lọc cùng nhóm, `deadline >= as_of`, lệch bậc ≤ `max_level_gap`, JD không level thì không lọc;
  - `cosine = max(0, cos)`;
  - `skill_match = |S_jd ∩ S_cv| / |S_jd|`, S_jd rỗng → 0 kèm note `jd_no_skills`;
  - `level_fit` 1 / 0,5 / 0, thiếu level → 0,5;
  - chế độ degraded: không có cosine, trọng số w2:w3 được chuẩn hóa lại;
  - thứ tự điểm giảm dần, hòa thì theo `job_id`; trần `max_results`.
- [x] T014 [P] [US2] Viết `apps/ai-service/tests/test_matching_settings.py`: mặc định `0.6,0.3,0.1`; trọng số âm, tổng
  ≠ 1 hoặc sai định dạng → `ConfigError`; mock không cần `AI_DB_URL` hay `LLM_API_KEY`.
- [x] T015 [P] [US2] Viết `apps/ai-service/tests/test_matching_job_index.py`:
  - parse dòng ai_db (`embedding::text`, metadata) thành snapshot đã chuẩn hóa L2;
  - lần nạp đầu lỗi → `match_index_unavailable`;
  - snapshot cũ → trả bản cũ ngay, nạp nền; nạp nền lỗi thì giữ bản cũ;
  - mock nạp `mock_jobs.json`;
  - dùng hàm `connect` giả.
- [x] T016 [P] [US2] Viết `apps/ai-service/tests/test_matching_router.py` (`MATCH_MOCK=true`):
  - thiếu token → 401;
  - track lạ → 422 `unknown_track`;
  - `page_size = 51` → 422 `invalid_request`;
  - hai lần gọi giống hệt nhau, `metadata.mock = true`;
  - item khớp lọc cứng, `matched_skills` / `missing_skills` khớp `skill_match`;
  - trang vượt `total` → `items` rỗng;
  - `job_ids` giới hạn đúng tập JD.
- [x] T017 [P] [US2] Viết `apps/ai-service/tests/test_matching_rag_isolation.py`: mọi SQL đọc `knowledge_chunks` trong
  `app/rag/repository.py` đều lọc `source_type` khác `job_description`; `SearchFilters()` mặc định không có
  `job_description`; `bm25_index` loại chunk `job_description` (SC-006).
- [x] T018 [P] [US2] Viết `apps/ai-service/tests/test_matching_service.py`: gateway giả ném lỗi hoặc quá
  `MATCH_EMBED_TIMEOUT_S` → `degraded = true` với `degraded_reason` tương ứng, vẫn trả kết quả; log không chứa văn bản
  CV (dùng caplog); có `timing_ms.embed`, `score`, `total` và `usage.embedding_tokens`.

### Implementation

- [x] T019 [US2] Viết `apps/ai-service/app/matching/levels_tracks.py` và `settings.py`:
  - đọc `MATCH_MOCK`, `MATCH_WEIGHTS`, `MATCH_MAX_LEVEL_GAP`, `MATCH_MAX_RESULTS`, `MATCH_INDEX_REFRESH_S`,
    `MATCH_EMBED_TIMEOUT_S`, `AI_DB_URL`, `AI_DB_CONNECT_TIMEOUT_S`, `EMBEDDING_MODEL` (qua `stored_model_name`);
  - không phụ thuộc `RAG_ENABLED`.
- [x] T020 [US2] Chép `apps/data-pipeline/data/seeds/skill_dictionary.yaml` sang
  `apps/ai-service/app/matching/skill_dictionary.yaml`. Viết `skill_normalizer.py`: `normalize(names) -> (slugs,
  unknown_count)`, `display_name(slug)`. Thêm `apps/data-pipeline/tests/test_skill_dictionary_copy_in_sync.py` so nội
  dung hai file.
- [x] T021 [US2] Viết `apps/ai-service/app/matching/cv_text.py`: văn bản embed của CV theo R4 (không có danh sách kỹ
  năng, ≤ 1.200 ký tự) và tập kỹ năng CV từ `skills[].name`, `experiences[].tech`, `projects[].tech`.
- [x] T022 [US2] Viết `apps/ai-service/app/matching/hash_embedder.py` (băm token vào 1536 chiều, chuẩn hóa L2, tất
  định) và `mock_jobs.json` (~12 JD tự soạn, phủ 4 nhóm và đủ level, có JD hết hạn và JD không level). Không lấy nội dung
  crawl.
- [x] T023 [US2] Viết `apps/ai-service/app/matching/job_index.py`:
  - snapshot (data-model §2);
  - nạp qua một kết nối psycopg async ngắn, read-only (`default_transaction_read_only=on`, `statement_timeout`), đóng
    ngay;
  - SQL lọc `source_type`, `dataset`, `embedding_model`;
  - làm mới nền khi tuổi > `MATCH_INDEX_REFRESH_S`, có khóa để không nạp chồng.
- [x] T024 [US2] Viết `apps/ai-service/app/matching/scorer.py` (hàm thuần, numpy) và `models.py` (pydantic request /
  response đúng contract: `page_size` 1–50, `job_ids` ≤ 200, `level` ∈ fresher | junior | middle | senior, `as_of`
  dạng date).
- [x] T025 [US2] Viết `apps/ai-service/app/matching/service.py`:
  - embed CV qua `get_gateway().embed` với `asyncio.wait_for(MATCH_EMBED_TIMEOUT_S)`, kèm `UsageCollector`;
  - lỗi cấu hình hay provider → degraded; ở chế độ mock dùng `hash_embedder`;
  - gọi scorer, phân trang, dựng metadata;
  - chỉ log số lượng và thời gian.
- [x] T026 [US2] Viết `apps/ai-service/app/matching/router.py` (`POST /api/match/jobs`, `ApiError` cho `unknown_track`
  và `match_index_unavailable`), thêm `include_router` vào `apps/ai-service/app/main.py`. Thêm `numpy` (pin `2.4.6`)
  vào `apps/ai-service/requirements.txt` và các biến `MATCH_*` có comment vào `apps/ai-service/.env.example`.
- [x] T027 [US2] Cập nhật docs (constitution III):
  - `docs/ai-service/06-api-contract.md`: chép contract endpoint;
  - `docs/architecture/ai-integration.md`: thêm sơ đồ Mermaid luồng gợi ý (pipeline index → ai_db → snapshot → scorer
    → endpoint; GĐ2 job-service nét đứt);
  - `docs/architecture/data-model.md` §5 và `docs/architecture/rag-design.md`: `job_description` được index cho gợi ý,
    không vào RAG.
- [x] T028 [US2] Chạy `pytest` của ai-service (toàn bộ, không chỉ test matching) và kiểm quickstart §2 ở chế độ mock.
  Review bằng `code-reviewer` (opus), mở PR-2, gắn AIE làm reviewer.

**Checkpoint**: endpoint chạy ở chế độ mock và chế độ thật (quickstart §4); RAG phỏng vấn không đổi.

---

## Phase 5: User Story 3 — Đánh giá chất lượng gợi ý (P2) — PR-3 `feat/data-pipeline/jd-match-eval`

**Goal**: `specs/017-cv-jd-matching/eval-results.md` có P@5 / nDCG@5 của 3 cách tính, độ trễ p50 / p95 và chi phí.

**Independent Test**: test metric với số tính tay; quickstart §5.

**Phụ thuộc**: PR-1 đã index, PR-2 đã merge hoặc chạy được ở local với `AI_DB_URL` + khóa.

### Tests (viết trước)

- [x] T029 [P] [US3] Viết `apps/data-pipeline/tests/test_match_eval_metrics.py`: P@5 với nhãn ≥ 1; nDCG@5 với gain =
  nhãn (ví dụ tính tay); danh sách < 5 phần tử; xếp lại theo thành phần, hòa theo `job_id`; percentile p50 / p95.
- [x] T030 [P] [US3] Viết `apps/data-pipeline/tests/test_match_eval_data.py`: kiểm schema `cvs.json` / `pool.json` /
  `labels.json`; nhãn chỉ nhận 0 / 1 / 2; thiếu nhãn cho cặp qua lọc hoặc thừa nhãn → lỗi có liệt kê.
- [x] T031 [P] [US3] Viết `apps/data-pipeline/tests/test_match_eval_command.py` với client giả:
  - phản hồi `degraded` hoặc `mock` → mã 4, không ghi bảng;
  - bảng soát không có điểm hay thứ hạng, thứ tự JD theo seed cố định;
  - bảng markdown có đủ các mục.

### Implementation

- [x] T032 [US3] Viết `apps/data-pipeline/pipeline/match_eval_data.py`, `match_eval_client.py` (httpx, header
  `X-Internal-Token`, timeout) và `match_eval_metrics.py`. Thêm `AI_SERVICE_URL`, `AI_SERVICE_INTERNAL_TOKEN`,
  `EMBEDDING_PRICE_PER_1M` vào `apps/data-pipeline/.env.example`.
- [x] T033 [US3] Viết `apps/data-pipeline/pipeline/match_eval_sheet_command.py`, `match_eval_command.py`,
  `match_eval_report.py`. Đăng ký `match-eval-sheet` và `match-eval` vào `jd_match_cli.py`.
- [x] T034 [US3] Soạn `apps/data-pipeline/data/seeds/match_eval/pool.json`: as-of cố định và 36 mã JD thật, 12 mỗi
  nhóm `backend` / `devops` / `ai_data`, có mẫu âm khó (Java, Python, Node cùng `backend`; JD lệch level), mọi JD còn
  hạn tại as-of. Worker `sonnet` đề xuất, DE duyệt.
- [x] T035 [US3] Soạn `apps/data-pipeline/data/seeds/match_eval/cvs.json`: 24 `CvProfile` tổng hợp (3 nhóm × 4 hồ sơ ×
  2 level), không có tên, liên hệ hay công ty thật. Mỗi CV phải có ≥ 10 JD trong pool qua lọc cứng. Worker `sonnet`
  soạn, DE duyệt.
- [ ] T036 [US3] Gán nhãn theo research R9 (chốt 2026-11-22): worker LLM gán mọi cặp qua lọc cứng theo
  [label-rubric.md](label-rubric.md), DE gán mù ~2 cặp mỗi CV trên trang artifact, tính kappa; nhãn cuối = nhãn LLM.
  Lưu `apps/data-pipeline/data/seeds/match_eval/labels.json` (ghi `labeled_by`, `method`, kappa). Khi có
  `match-eval-sheet`, kiểm tập cặp của endpoint trùng tập đã gán.
- [ ] T037 [US3] Chạy `match-eval --rounds 4` với ai-service ở chế độ thật, commit
  `specs/017-cv-jd-matching/eval-results.md`. Nếu SC-001 không đạt thì phân tích lỗi trên 3 CV. Review, mở PR-3.

**Checkpoint**: có bảng số liệu cho báo cáo đồ án.

---

## Phase 6: GĐ2 (US4–US6) — chưa có task code

Contract nháp [contracts/gd2-job-service-draft.md](contracts/gd2-job-service-draft.md) giao FSD. Khi FSD có 007 / 008 /
013 thì chạy lại `/speckit-plan` cho GĐ2 (chốt FR-027: nơi lưu vector CV).

---

## Phase 7: Polish & Cross-Cutting

- [ ] T038 Cập nhật trạng thái 017 trong `specs/README.md` sau mỗi PR merge, và tick task trong file này.
- [ ] T039 [P] Ghi thay đổi vào `docs/project-changelog.md` (nếu file có) khi PR-2 và PR-3 merge.

---

## Dependencies & Execution Order

- Phase 1 không phụ thuộc gì. T003 (Phase 2) chặn T007.
- **US1** (T004–T010) độc lập với US2. **US2** (T011–T028) chạy được song song với US1 ở chế độ mock, nhưng quickstart
  §4 cần US1 đã index. US2 mở PR khi AIE đồng ý.
- **US3** cần US1 (đã index) và US2 (endpoint thật). T034, T035 soạn dữ liệu được song song với US2.
- Trong mỗi story: test → module thuần → service → endpoint / lệnh → docs → review.

### Parallel Opportunities

- T004 ∥ T005; T011–T018 (8 file test khác nhau); T029–T031; T034 ∥ T035 ∥ phần code của US2.
- Ví dụ US2: worker A viết T011 + T019, worker B viết T012 + T020, worker C viết T013 + T024. Sau đó một worker viết
  T023 → T025 → T026.

## Implementation Strategy

- **MVP** = US1 + US2: index thật và endpoint trả gợi ý, demo được bằng curl hoặc script.
- Sau đó US3 để có số liệu cho báo cáo. GĐ2 chờ FSD.
- Mỗi phase là một PR; review bằng `code-reviewer` trước khi mở PR; test đỏ thì không mở PR.
