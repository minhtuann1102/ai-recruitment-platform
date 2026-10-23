---

description: "Task list for 005-rag-knowledge-base-qa"
---

# Tasks: RAG Knowledge Base — Interview Q&A

**Input**: Design documents from `/specs/005-rag-knowledge-base-qa/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: constitution VI bắt buộc test cho logic chính của Python app → mỗi story có task pytest **offline** (không
mạng, không key, không DB; research R10). DB/API kiểm chứng bằng [quickstart.md](quickstart.md).

**Organization**: theo user story; PR theo Delivery Sequence của [plan.md](plan.md). Mọi đường dẫn code tương đối
`apps/data-pipeline/`. Chạy lệnh trong `apps/data-pipeline/` bằng `python -m pipeline <lệnh>` / `python -m pytest`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: chạy song song được (khác file, không phụ thuộc task chưa xong)
- **[Story]**: US1..US5 theo spec.md; mã `S1-DE-#` để truy vết về sprint plan

---

## Phase 1: Setup · PR `feat/data-pipeline/qa-offline`

**Purpose**: khung app Python, chạy được trong job `python` của CI (#5)

- [X] T001 Tạo branch `feat/data-pipeline/qa-offline` từ `main`; tạo thư mục `apps/data-pipeline/{pipeline,crawlers,tests/fixtures,data/seeds/interview_qa}` với `pipeline/__init__.py`, `crawlers/__init__.py`
- [X] T002 Tạo `apps/data-pipeline/requirements.txt` pin phiên bản: `openai==2.48.0`, `psycopg[binary]`, `pgvector==0.4.2`, `pyyaml==6.0.3`, `python-dotenv==1.2.1`, `httpx`, `beautifulsoup4`, `playwright==1.64.0`, `psycopg[binary]==3.3.6`, `httpx==0.28.1`, `beautifulsoup4==4.15.0` (bản ổn định 2026-10-19); `requirements-dev.txt` = `-r requirements.txt` + `pytest==8.3.4`
- [X] T003 [P] Tạo `apps/data-pipeline/.env.example` đúng bảng Env trong `contracts/pipeline-cli.md` (`LLM_API_KEY` trống, `LLM_BASE_URL`, `EMBEDDING_MODEL=openai/text-embedding-3-small`, `EMBEDDING_DIMENSIONS=1536`, `AI_DB_URL=postgresql://postgres:secret@localhost:5534/ai_db`, `CATALOG_DIR=../ai-service/app/catalog`)
- [X] T004 [P] Thêm vào `.gitignore` gốc: `apps/data-pipeline/data/raw/`, `apps/data-pipeline/data/processed/`, `apps/data-pipeline/.venv/`
- [X] T005 [P] Tạo `apps/data-pipeline/tests/conftest.py` (fixture đường dẫn `tests/fixtures/`) và `tests/fixtures/catalog/sample_track.yaml` (2 topic khác category + 1 scenario) để test không phụ thuộc catalog thật

---

## Phase 2: Foundational (chặn mọi story)

**Purpose**: module dùng chung cho US1, US2, US5 và CLI

- [X] T006 `pipeline/settings.py`: đọc env bằng `python-dotenv` (không bắt buộc key khi import); hàm `canonical_embedding_model(name)` trả phần sau dấu `/` cuối (`openai/text-embedding-3-small` → `text-embedding-3-small`, research R2); hàm `require_index_settings()` báo lỗi rõ khi thiếu `LLM_API_KEY` hoặc `AI_DB_URL`
- [X] T007 [P] `pipeline/topic_catalog_reader.py`: đọc mọi `*.yaml` trong `CATALOG_DIR` (+ các thư mục `--extra-catalog`) bằng `pyyaml`, trả `{topic_id: category}` chỉ từ `topics[]`, **bỏ `scenarios[]`** (FR-002); id trùng giữa file → lỗi
- [X] T008 [P] `pipeline/text_cleaning.py`: `clean_text()` theo thứ tự NFC → bỏ thẻ HTML (`html.parser`, giữ text) → `html.unescape` → bỏ ký tự điều khiển trừ `\n`, `\t` → gộp khoảng trắng trong dòng, tối đa 1 dòng trống → strip (research R3); `normalize_for_compare()` = lower + bỏ dấu (NFD bỏ combining mark, `đ`→`d`) + bỏ dấu câu, dùng cho trùng gần đúng và golden set
- [X] T009 [P] `pipeline/pii_patterns.py`: `find_pii(text)` / `scrub_pii(text)` với regex email và số điện thoại (VN `+84`/`0` + 9–10 số, có/không dấu cách, chấm, gạch); không bắt nhầm số phiên bản, port, năm
- [X] T010 `pipeline/__main__.py`: argparse 6 lệnh `validate | process | index | search | eval | crawl` với cờ và mã thoát đúng bảng `contracts/pipeline-cli.md`; lệnh chưa làm in "not implemented" và thoát 2
- [X] T011 [P] Tests `tests/test_text_cleaning.py` (chuỗi NFD và NFC cho cùng kết quả; HTML sót bị bỏ; giữ "Thuật toán", "idempotent", code `a<b`), `tests/test_pii_patterns.py`, `tests/test_topic_catalog_reader.py` (scenario id không có trong map)

**Checkpoint**: `python -m pytest -q` xanh; `python -m pipeline --help` liệt kê 6 lệnh

---

## Phase 3: User Story 1 — Bộ Q&A ≥ 200 cặp theo topic catalog (P1) 🎯 MVP · S1-DE-1

**Goal**: seed hợp lệ ≥ 200 cặp, phân bố đạt SC-001, SC-002

**Independent Test**: `python -m pipeline validate --strict` thoát 0 trên catalog đã merge (quickstart §1)

### Công cụ (PR `qa-offline`)

- [X] T012 [US1] `pipeline/qa_seed_loader.py`: đọc mọi `data/seeds/interview_qa/*.json` theo thứ tự tên file, mỗi file là mảng; lỗi JSON báo tên file + vị trí; giữ provenance (file, index) cho thông báo lỗi
- [X] T013 [US1] `pipeline/qa_seed_rules.py`: luật **mức cặp** trong `contracts/qa-seed-format.md` — `qa_id` khớp `^de-qa-\d{4}$`; `topic_id` thuộc map catalog; `question` ≥ 10 ký tự, `answer` ≥ 30 ký tự sau `clean_text`; `difficulty ∈ {easy, medium, hard}`; `language ∈ {vi, en}`; `license` thuộc `LICENSE_ALLOWLIST = {CC0-1.0, MIT, Apache-2.0, CC-BY-4.0, CC-BY-SA-4.0, CC-BY-SA-2.5}`; `source ≠ "self"` thì phải là URL và có `attribution`; `synthetic=false` mà `source = "self"` → lỗi; **mọi cặp** thiếu `reviewed_by` → lỗi; cặp `self` khác `DATASET_LICENSE` (`CC-BY-4.0`) → lỗi; cặp `CC-BY-SA-*` khi bộ seed chưa BY-SA → lỗi; PII trong `question`/`answer` → lỗi. Trả danh sách `(qa_id, rule, level, message)`
- [X] T014 [US1] `pipeline/qa_seed_validator.py`: luật **mức tập** — `qa_id` trùng (lỗi); câu hỏi trùng tuyệt đối sau `clean_text` + lower, báo cả hai `qa_id` (lỗi); gần trùng `difflib.SequenceMatcher` ratio ≥ 0.9 trên `normalize_for_compare` (cảnh báo); topic < 2 cặp, tổng < 200, độ khó nào < 20%, tỉ lệ `synthetic=false` < 50% → cảnh báo, thành lỗi khi `--strict`; báo cáo phân bố theo topic / category / difficulty / language / license / nguồn / synthetic
- [X] T015 [US1] Nối lệnh `validate [--strict] [--extra-catalog DIR]` trong `pipeline/__main__.py`: in lỗi, cảnh báo, báo cáo; thoát 1 khi có lỗi
- [X] T016 [P] [US1] `tests/test_qa_seed_validator.py` với fixture `make_pair` trong `tests/conftest.py`: US1-1 seed hợp lệ thoát 0; US1-2 thiếu trường / `topic_id` lạ / giấy phép `CC-BY-NC-4.0` bị liệt kê kèm lý do, thoát 1; US1-3 hai câu chỉ khác hoa thường + khoảng trắng → báo cả hai `qa_id`; US1-4 topic có 1 cặp → báo thiếu (lỗi khi `--strict`)
- [X] T017 [US1] Tạo `data/seeds/interview_qa/NOTICE`: giấy phép của bộ seed (`CC-BY-4.0`; đổi `CC-BY-SA-4.0` nếu dùng nguồn BY-SA), danh sách nguồn + giấy phép + tác giả theo research R6; bảng dải `qa_id` theo file (T018–T023, T025) để soạn song song không trùng id

### Dữ liệu (PR `feat/data-pipeline/qa-seed-<nhóm>`, mỗi lô `validate` sạch trước khi mở PR)

Luật chung: đáp án tiếng Việt giữ thuật ngữ Anh (FR-004); độ khó theo rubric (FR-001); chuyển thể từ nguồn ghi
`source` URL + `license` + `attribution`, `synthetic=false` chỉ khi cả hỏi lẫn đáp từ nguồn; đáp án tự soạn
`synthetic=true`; **mọi cặp** có `reviewed_by`; mỗi topic ≥ 2 cặp. **Mỗi topic đúng một lô** theo tiền tố id của track (topic
category Database/System Design nằm trong lô của track chứa nó); nguồn CC BY/Apache dùng được ở mọi lô.
**Mục tiêu tổng ≥ 224 cặp, công khai ≥ 122 (≥ 54%)** để vài cặp bị loại/dedup không kéo xuống dưới 200 / 50%; theo
dõi tỉ lệ công khai trong báo cáo `validate` sau mỗi lô.

**Review thật**: chỉ điền `reviewed_by` sau khi người review đã đọc đáp án; cặp `synthetic=false` dịch từ tiếng
Ukraina/Nga/Trung cũng phải được đọc đối chiếu nghĩa với bản gốc. Giờ review của DE là giới hạn chính của US1.
Ngoại lệ: cặp hard tự viết (T056) duyệt theo spec Clarification Session 2026-10-23 (xem T057).

- [ ] T018 [P] [US1] **BỎ (2026-10-19, thay bằng T050–T054)** `data/seeds/interview_qa/backend-nodejs.json` (`de-qa-0001..0099`): 13 topic `node.*` (sàn 26), mục tiêu ≥ 32 cặp, ≥ 24 công khai từ DevLoversTeam/nodejs-interview-questions (MIT) + system-design-primer (CC-BY-4.0) cho `node.arch.*`, `node.data.*`
- [ ] T019 [P] [US1] **BỎ (2026-10-19, thay bằng T050–T054)** `data/seeds/interview_qa/backend-python.json` (`de-qa-0100..0199`): 12 topic `py.*` (sàn 24), mục tiêu ≥ 32 cặp, ≥ 24 công khai từ DevLoversTeam/python-interview-questions, yakimka/python_interview_questions (MIT)
- [ ] T020 [P] [US1] **BỎ (2026-10-19, thay bằng T050–T054)** `data/seeds/interview_qa/backend-java.json` (`de-qa-0200..0299`): 14 topic `java.*` (sàn 28), mục tiêu ≥ 32 cặp, ≥ 14 công khai từ crossoverJie/JCSprout, codefarm0/Spring-Boot-Interview-Question-Answers (MIT), system-design-primer cho `java.arch.*`, `java.data.*`
- [ ] T021 [P] [US1] **BỎ (2026-10-19, thay bằng T050–T054)** `data/seeds/interview_qa/ai.json` (`de-qa-0300..0399`): 12 topic `ai.*` hiện có (sàn 24) + 14 topic đề xuất khi AIE merge (sàn tổng 52), mục tiêu ≥ 56 cặp, ≥ 22 công khai từ alexeygrigorev/data-science-interviews `theory.md` (CC-BY-4.0); AI cutting-edge chủ yếu tự soạn
- [ ] T022 [P] [US1] **BỎ (2026-10-19, thay bằng T050–T054)** `data/seeds/interview_qa/devops.json` (`de-qa-0400..0499`): 12 topic `devops.*` đề xuất (sàn 24), mục tiêu ≥ 28 cặp; câu hỏi jakshi/devops-interview-questions (Apache-2.0, ghi `source` + `attribution`) + đáp án tự soạn → `synthetic=true`
- [ ] T023 [P] [US1] **BỎ (2026-10-19, thay bằng T050–T054)** `data/seeds/interview_qa/frontend.json` (`de-qa-0500..0599`): 13 topic `fe.*` đề xuất (sàn 26), mục tiêu ≥ 44 cặp, ≥ 38 công khai từ sudheerj/reactjs-interview-questions, lydiahallie/javascript-questions (MIT), react.dev (CC-BY-4.0, dữ liệu US5). T021 (phần đề xuất), T022, T023 chạy `validate --extra-catalog ../../specs/005-rag-knowledge-base-qa/contracts/topic-catalog-proposal` tới khi AIE merge
- [ ] T024 [US1] **BỎ (2026-10-19)** **Quyết định 22/10**: AIE đã merge catalog đề xuất chưa? Chưa → SC-001 tính trên 51 topic hiện có: T022–T023 không được tính, bù đủ 200 cặp và ≥ 50% công khai bằng cặp công khai thêm ở T018, T019 (DevLoversTeam còn ~250 + ~100 cặp chưa dùng), T021 (ML); báo team ngay quyết định này
- [ ] T025 [US1] (tùy chọn, lấp topic thiếu) Review 50 cặp `apps/ai-service/data/seeds/qa_seed.json`: cặp đạt thì gán `qa_id` (dải `de-qa-0600..0649`) + `topic_id`, `source="self"`, `synthetic=true`, `reviewed_by`, thêm vào `data/seeds/interview_qa/aie-reviewed.json` (FR-003)
- [ ] T026 [US1] Nghiệm thu: `validate --strict` **không** `--extra-catalog`, trên catalog đã merge → thoát 0; ghi báo cáo phân bố vào PR (SC-001, SC-002)

### Thu thập + dịch (quyết định DE 2026-10-19: crawl mọi nguồn, không cần giấy phép, dịch sang tiếng Việt; nội dung
không commit vì repo public — spec Clarifications)

- [X] T050 [US1] `crawlers/qa_markdown_parsers.py`, `crawlers/qa_sources.py`, `crawlers/github_raw_client.py`, `pipeline/collect_command.py`: lệnh `collect` qua GitHub API (rate limit, xóa PII, cắt đáp án > 4000 ký tự) — 2026-10-19: 4.840 cặp / 44 nguồn (en 4.349, uk 350, ru 141)
- [X] T051 [US1] `pipeline/llm_enricher.py`, `pipeline/enrich_command.py`: lệnh `enrich` — LLM dịch sang tiếng Việt giữ thuật ngữ Anh + code, gán `topic_id` từ catalog + độ khó, kiểm code fence, chạy tiếp được, ghi `_rejected.jsonl`; dataset `de_crawled_qa` tách khỏi seed curated
- [X] T052 [US1] (2026-10-19/20: DeepSeek `deepseek-chat` dịch 4.4k cặp ~10 tệ; hết tiền ở 115 cặp cuối → 2 subagent Sonnet dịch, gộp qua `parse_response` — bản dịch lưu ở `data/raw/agent_translations/`, chạy lại `enrich` có key sẽ dịch lại bằng API; kết quả: 4.359 cặp hợp lệ, hard 42) Có key: `enrich --extra-catalog ../../specs/005-rag-knowledge-base-qa/contracts/topic-catalog-proposal --per-source 3` (~130 cặp) → đọc thử chất lượng dịch + gán topic → chạy toàn bộ; ghi token + chi phí vào PR
- [ ] T053 [US1] Review mẫu ~10 cặp ngẫu nhiên / nguồn, đối chiếu `question_original`/`answer_original`; nguồn dịch kém → sửa prompt hoặc bỏ nguồn (cách ghi kết quả: chốt với DE)
- [ ] T054 [US1] `validate --strict` trên seed curated + dữ liệu crawl: mọi topic ≥ 2 cặp, mỗi topic middle/senior ≥ 2 cặp hard (SC-001 sửa 2026-10-19); topic thiếu → thêm nguồn vào `qa_sources.py` hoặc cặp tự soạn vào seed curated

- [X] T055 [US1] `pipeline/qa_seed_validator.py`, `pipeline/topic_catalog_reader.py`: thay luật "mỗi độ khó ≥ 20%" bằng `hard_coverage` — topic có level middle/senior phải có ≥ 2 cặp hard; `review-sample` cho review mẫu bản dịch
- [X] T056 [US1] (2026-10-20: 144 cặp hard — node 22, python 22, java 22, ai 47, devops 18, frontend 13; viết bởi subagent Opus + 1 cặp GIL bởi phiên chính; `validate` báo sau khi duyệt: 0 topic thiếu hard, 0 topic mỏng; lệnh `review-seed` / `approve-seed` hỗ trợ duyệt) Sau `enrich` đầy đủ (+ `--only doocs-advanced-java --only genai-60`): đếm cặp hard theo topic; với topic thiếu, Claude viết câu hard tiếng Việt bám tài liệu thật (crawl nâng cao, docs chính thức) vào `data/seeds/interview_qa/hard-<track>.json` (dải `qa_id` trong `NOTICE`), `source = self`, `synthetic = true`, `grounding_urls`; làm theo nhóm track, mỗi lô `validate` sạch trước khi commit
- [ ] T057 [US1] Duyệt 144 cặp hard theo spec Clarification Session 2026-10-23: skill `interview-qa-review` (rubric v2) + cặp mồi, áp đề xuất sửa vào seed; DE đọc nhóm "phải đọc", diff các cặp đã sửa và mẫu cặp Đạt theo v2, rồi `approve-seed --reviewer minhtuann1102`; báo AIE về SC-001 mới (Interviewer lọc theo độ khó) và giới hạn 600 token snippet của Planner

**Checkpoint**: ≥ 200 cặp hợp lệ (crawl + curated), mọi topic ≥ 2 cặp, mỗi topic middle/senior ≥ 2 cặp hard

---

## Phase 4: User Story 2 — Pipeline offline load → clean → chunk → dedup (P1) · S1-DE-3 · PR `qa-offline`

**Goal**: một lệnh biến seed thành bản ghi sẵn sàng embed, không DB, không key, deterministic

**Independent Test**: quickstart §2 (`process` hai lần, cùng sha256; `chunks_out = 2 × records_in − trùng`)

- [X] T027 [US2] `pipeline/qa_record_builder.py`: cặp hợp lệ → 2 record theo `contracts/knowledge-chunks-io.md` (`question`: câu hỏi đã làm sạch; `qa_pair`: `"{question}\n\n{answer}"`; `source_type=interview_qa`; `category` từ catalog; `metadata` đúng 7 khóa `qa_id, chunk_type, dataset=de_interview_qa, tags, source_url (null khi source="self"), license, synthetic`); `content_hash(content) = md5(lower(strip(content)))`; cặp lỗi mức cặp (T013) bị **loại kèm lý do, chạy tiếp**; câu hỏi trùng tuyệt đối giữ `qa_id` nhỏ hơn; dedup theo hash giữ record đầu theo thứ tự (`qa_id`, `chunk_type`)
- [X] T028 [US2] `pipeline/run_report.py`: bộ đếm `records_in, records_rejected (+ qa_id, lý do), chunks_out, dedup_ratio` (+ khóa của `index` ở T034), in khối thống kê, ghi `data/processed/run-report-<lệnh>-<UTC timestamp>.json`
- [X] T029 [US2] Nối lệnh `process [--extra-catalog DIR]`: ghi `data/processed/interview_qa.jsonl` sắp theo (`qa_id`, `chunk_type`), `json.dumps(..., ensure_ascii=False, sort_keys=True)`, không timestamp trong file → deterministic (FR-009); thoát 1 chỉ khi không đọc được seed/catalog
- [X] T030 [P] [US2] `tests/test_qa_record_builder.py`: US2-1 N cặp → 2N record, cặp lỗi bị loại có lý do; US2-2 khoảng trắng / ký tự điều khiển / HTML được làm sạch, giữ dấu; US2-3 chạy hai lần cho bytes giống hệt; câu NFD và NFC cho cùng `content_hash`
- [X] T031 [US2] (PR #8, CI xanh: data-pipeline 18s; seed còn rỗng nên quickstart §1–2 thoát 1 đúng thiết kế — kiểm lại với lô seed đầu) Mở PR `qa-offline` (Phase 1–4 công cụ): CI xanh; quickstart §1–3 trên seed hiện có

**Checkpoint**: PR `qa-offline` merged — soạn seed theo lô có công cụ kiểm tra

---

## Phase 5: User Story 3 — Index vào kho và truy hồi (P1) · S1-DE-4, S1-AIE-1 (DE) · PR `feat/data-pipeline/qa-index`

**Goal**: ≥ 400 bản ghi trong `knowledge_chunks`, idempotent, dọn bản cũ, truy hồi có lọc

**Independent Test**: quickstart §4–5

**Phụ thuộc**: 001 PR #6 merged (bảng `knowledge_chunks`), key từ Thắng (research R2 VERIFY)

- [X] T032 [US3] `pipeline/embedding_client.py`: `openai.OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY, max_retries=3, timeout=30)`; `embed(texts)` theo batch 100, trả vector hoặc lỗi theo batch (không ném, để đếm — FR-015); `probe()` embed 1 chuỗi, kiểm `len == EMBEDDING_DIMENSIONS`
- [X] T033 [US3] `pipeline/knowledge_chunk_writer.py` — đường ghi duy nhất (FR-010), theo research R4: preflight không gọi API (key có, `psycopg` kết nối được, `pg_extension` có `vector`, `to_regclass('knowledge_chunks')` không null; lỗi → thoát 2, chưa ghi); tra `content_hash, metadata->>'dataset'` đã có; hàm thuần `plan_writes(records, existing, dataset)` → `new | update_same_dataset | skip_other_dataset | delete_hashes`; có `new` thì `probe()` trước lần ghi đầu (lỗi → thoát 2); embed + `INSERT ... ON CONFLICT (content_hash) DO NOTHING` commit theo batch, `embedding_model` = tên chuẩn; `UPDATE content, category, difficulty, topic_id, language, metadata` cho `update_same_dataset` (gồm `content` vì hash bỏ qua hoa/thường); chạy riêng cho từng dataset `de_interview_qa`, `de_crawled_qa` (dọn FR-013 theo dataset); `DELETE ... WHERE source_type='interview_qa' AND metadata->>'dataset'=:dataset AND content_hash <> ALL(:hashes)` chỉ khi 0 embedding lỗi. Không tạo/sửa bảng (FR-011)
- [X] T034 [US3] Nối lệnh `index`: chạy `process` → writer; thêm vào run report `embedded, embed_errors, inserted, updated, skipped_same, skipped_other_dataset, deleted, cleanup`; mã thoát 0 / 1 / 2 / 3 theo `contracts/pipeline-cli.md`
- [X] T035 [US3] `pipeline/knowledge_chunk_search.py` + nối lệnh `search`: embed truy vấn, SQL `1 - (embedding <=> :q)` với bộ lọc `source_type, metadata->>'chunk_type', category, difficulty, topic_id` + luôn `embedding_model = <tên chuẩn>`; lấy dư `4k`, giữ bản ghi điểm cao nhất mỗi `qa_id`, cắt còn `k` (mặc định 5); log `qa_id` + điểm (FR-017); chỉ đọc
- [X] T036 [P] [US3] `tests/test_knowledge_chunk_writer_plan.py` (offline, hàm thuần): chạy lại → 0 `new`; sửa đáp án → `qa_pair` mới + hash cũ trong `delete`; hash thuộc dataset khác → `skip`, không bao giờ trong `delete`; đổi `topic_id` cùng nội dung → `update`. `tests/test_knowledge_chunk_search_dedup.py`: dedup theo `qa_id` trước khi cắt k
- [X] T037 [US3] (2026-10-20: index thật bằng OpenAI `text-embedding-3-small`: 8.718 bản ghi, 0 lỗi embed, 8 phút; chạy lại 0 embed; 5 truy vấn demo đúng topic 5/5, trúng câu 4/5 — N+1 Hibernate chỉ có câu hard chờ duyệt) Chạy quickstart §4–5 trên máy dev (DB từ `docker compose up -d`): lần 1 `inserted ≥ 400`, ≥ 99% có vector, ≤ 10 phút (SC-003, SC-006); lần 2 `embedded = 0`, `inserted = 0` (SC-004); sửa + xóa một cặp (US3-3); key rỗng → thoát 2, bảng không đổi (US3-6); 5 truy vấn demo ≥ 4/5 đúng chủ đề (SC-009). Ghi kết quả + chi phí vào PR

**Checkpoint**: demo Sprint 1 "RAG tìm Q&A relevant" chạy được

---

## Phase 6: User Story 4 — Golden set recall@5 (P2) · S1-DE-4 · PR `qa-index`

**Goal**: recall@5 tổng và theo 5 nhóm, báo cáo không chặn merge

**Independent Test**: quickstart §6

- [ ] T038 [US4] `data/seeds/golden_set.json`: ≥ 20 truy vấn `gq-NNN`, mỗi nhóm `vi | mixed | en | vi_to_en | no_diacritics` ≥ 1 (nên ≥ 4), `expected_qa_ids` trỏ seed, `source="handwritten"`, không trùng nguyên văn câu hỏi seed (`contracts/qa-seed-format.md` § Golden set)
- [ ] T039 [US4] `pipeline/golden_set_eval.py` + nối lệnh `eval`: kiểm golden set (truy vấn trùng câu hỏi seed sau `normalize_for_compare` → lỗi US4-2; `qa_id` không tồn tại → lỗi; thiếu nhóm → lỗi); hàm thuần `recall_at_k(expected, retrieved_qa_ids, k)` = |nhãn ∩ top-k| / |nhãn|; dùng `knowledge_chunk_search` (dedup `qa_id`); in recall tổng + theo nhóm + truy vấn trượt + top-3; ghi `data/processed/eval-<timestamp>.json`; ghi "chưa đạt 0.8" + nhóm yếu nhất nếu thấp; nhãn chưa duyệt → ghi rõ; thoát 0 khi chạy xong (FR-021)
- [ ] T040 [P] [US4] `tests/test_golden_set_eval.py`: `recall_at_k` (trúng / trượt / nhiều nhãn); truy vấn trùng câu hỏi seed bị từ chối; thiếu nhóm bị báo
- [ ] T041 [US4] Nhờ AIE duyệt nhãn → điền `approved_by` (FR-020, SC-005); chạy `eval`, dán bảng recall vào PR

---

## Phase 7: User Story 5 — Crawler mẫu (P2) · S1-DE-2 · PR `feat/data-pipeline/sample-crawler`

**Goal**: crawl react.dev ≥ 50 record, tôn trọng robots, rate limit, không PII; dùng lại cho 009/012

**Independent Test**: quickstart §7

- [ ] T042 [US5] `crawlers/polite_fetcher.py`: `urllib.robotparser` đọc `robots.txt` một lần, log "robots checked" + bỏ URL bị cấm kèm log (US5-2); nghỉ ≥ `--delay` giây giữa request (mặc định 1); dừng ở `--max-pages`; user-agent `ai-recruit-data-pipeline/0.1 (+repo URL)`; tải bằng `httpx`, chế độ `--render` dùng `playwright` Chromium import lười (US5-4)
- [ ] T043 [US5] `crawlers/react_docs_crawler.py`: bắt đầu `https://react.dev/learn`, `https://react.dev/reference/react`, theo link cùng domain dưới hai tiền tố đó; tách nội dung chính theo h1/h2/h3 → `sections[{heading_path, text}]`; `scrub_pii` mọi text (FR-023); ghi `data/raw/react_docs/<UTC timestamp>.jsonl` với `url, title, sections, crawled_at, license="CC-BY-4.0"`; 0 record → thoát 1 (FR-025)
- [ ] T044 [US5] Nối lệnh `crawl react-docs [--max-pages N] [--delay S] [--render]` trong `pipeline/__main__.py`
- [ ] T045 [P] [US5] `tests/test_polite_fetcher.py` (robots cấm `/private` với fixture → bỏ qua; đồng hồ giả kiểm khoảng nghỉ ≥ delay; không vượt max pages) và `tests/test_react_docs_parse.py` (HTML fixture → sections đúng heading path; email/số điện thoại bị scrub)
- [ ] T046 [US5] Chạy quickstart §7 (≥ 50 record, SC-008); ghi log robots + thời gian vào PR; chuyển thể một phần record thành cặp Frontend cho T023

---

## Phase 8: Polish & Cross-Cutting

- [ ] T047 [P] Cập nhật `docs/architecture/data-pipeline.md` §3, §7, §8: thay phác thảo lỗi thời bằng cấu trúc thật + lệnh `python -m pipeline`, link `specs/005-rag-knowledge-base-qa/contracts/`
- [ ] T048 [P] Cập nhật `specs/README.md` (Trạng thái 005) và `spec.md` (Status) khi PR merge
- [ ] T049 Nhờ AIE chạy quickstart §0–§5 trên máy họ chỉ theo hướng dẫn, ≤ 5 lệnh (SC-007); sửa hướng dẫn nếu phải hỏi DE

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (P1)** → **Foundational (P2)** → **US1 công cụ (T012–T017)** và **US2 (T027–T030)** → PR `qa-offline` (T031)
- **US1 dữ liệu (T018–T023)**: soạn ngay từ T017 (dải `qa_id`), kiểm bằng `validate` sau T015; T021 (phần AI mới),
  T022, T023 cần AIE merge catalog đề xuất mới nghiệm thu được (T026); T024 quyết định phương án ngày 22/10
- **US3**: cần T029 + 001 PR #6 merged + key. **US4**: cần T035 (search) + seed đủ để gắn nhãn
- **US5**: chỉ cần Phase 2 (T009 scrub, T010 CLI); độc lập với US3/US4
- **Polish** sau khi các PR merge

### Timeline đề xuất (hạn 26/10)

| Ngày | Việc |
|---|---|
| T3 20/10 | T001–T017; bắt đầu T018 (Node) |
| T4 21/10 | T027–T031 (mở PR `qa-offline`); T019 (Python) |
| T5 22/10 | **Mốc kiểm cắt phạm vi** + T024 (catalog merge?); T020–T021; T032–T035 nếu #6 merged + có key |
| T6 23/10 | T036–T037 (index + demo); T038 |
| T7 24/10 | T039–T041; T042–T046; T022–T023 (nếu catalog đã merge) |
| CN 25/10 | T026 nghiệm thu seed, T047–T049, buffer |
| T2 26/10 | Demo Sprint 1 |

**Thứ tự cắt nếu 22/10 trễ** (plan.md): US4 → golden set nhỏ, chỉ báo cáo (T038–T041 rút gọn); US5 → crawl tĩnh,
bỏ `--render` (T042 bỏ playwright). Catalog chưa merge ngày 22/10 → phương án T024. Không hạ 200 cặp / 50% công
khai mà không báo team.

### Parallel Opportunities

- T003 ∥ T004 ∥ T005; T007 ∥ T008 ∥ T009 (khác file)
- T018 ∥ T019 ∥ T020 ∥ T021 ∥ T022 ∥ T023 (mỗi lô một file, dải `qa_id` riêng)
- Tests [P] (T011, T016, T030, T036, T040, T045) viết song song với module của story đó
- Nhánh US5 (T042–T046) song song với US3/US4

---

## Parallel Example: User Story 1 (dữ liệu)

```bash
Task: "Soạn backend-nodejs.json, de-qa-0001..0099"           # T018
Task: "Soạn backend-python.json, de-qa-0100..0199"           # T019
Task: "Soạn backend-java.json, de-qa-0200..0299"             # T020
```

---

## Implementation Strategy

### MVP

Phase 1–4 (`qa-offline`) + lô seed Node/Python → `validate`, `process` chạy được, CI xanh. Tiếp theo US3 (T032–T037)
= demo Sprint 1. US4, US5 là P2, cắt trước nếu trễ.

### Incremental Delivery

`qa-offline` → các lô `qa-seed-*` → `qa-index` (US3 + US4) → `sample-crawler` (US5); mỗi PR tự kiểm chứng bằng mục
quickstart tương ứng và không làm hỏng PR trước.

---

## Notes

- Commit Conventional Commits, scope `data-pipeline` (vd `feat(data-pipeline): add qa seed validator`)
- Không commit `.env`, `data/raw/`, `data/processed/`; key embedding xin riêng Thắng
- Mỗi file Python < 200 dòng; vượt thì tách theo trách nhiệm (constitution VII)
- Đường đọc production (`retrieve`, tra `qa_id`) là S1-AIE-2 của AIE — không làm trong tasks này
