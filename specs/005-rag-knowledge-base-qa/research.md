# Research: RAG Knowledge Base — Interview Q&A

Mỗi mục: Decision / Rationale / Alternatives. **VERIFY** = kiểm chứng lúc implement.

## R1. Vị trí code và ranh giới ghi / đọc

- **Decision**: Đường ghi (validate → clean → chunk → dedup → embed → ghi/dọn) nằm trong `apps/data-pipeline/`
  (constitution: data pipeline Python đặt tại đây), package `pipeline`. Đường đọc production (`retrieve`, tra theo
  `qa_id`) là `apps/ai-service/app/rag/` của AIE (S1-AIE-2). Hai bên không import code của nhau; hợp đồng chung chỉ là
  [contracts/knowledge-chunks-io.md](contracts/knowledge-chunks-io.md), DDL `knowledge_chunks` và file YAML catalog.
- **Rationale**: FR-010. Hai app có `requirements.txt` riêng và chạy riêng trong CI; import chéo kéo theo dependency
  của nhau. Thay đề xuất "dùng chung `chunking.py` + `repository.py`" ở rag-design §6, §8 (đã chốt ở Clarifications).
- **Read-only cho DE**: lệnh `search` và `eval` của pipeline có một câu SQL tìm kiếm chỉ đọc, viết đúng hợp đồng
  đọc (cosine `<=>`, cùng bộ lọc, lọc `embedding_model`). Đây là công cụ kiểm chứng của DE (US3 "5 truy vấn mẫu",
  US4), không thay `retrieve()` của AIE. Nếu AIE thêm xử lý truy vấn (rewrite, rerank), báo cáo eval ghi rõ là đo
  tầng embedding + lưu trữ.
- **Alternatives**: eval gọi `retrieve()` của AIE qua import → phụ thuộc chéo, AIE chưa có code S1-AIE-2. Endpoint
  HTTP truy hồi trong ai-service → thêm API không có trong contract (constitution III). Bị loại.

## R2. Model embedding: giá trị lưu chuẩn và provider

- **Decision**: Cột `embedding_model` luôn lưu **tên chuẩn không có tiền tố provider**: `text-embedding-3-small`
  (khớp default của DDL). Env `EMBEDDING_MODEL` giữ tên theo provider (OpenRouter: `openai/text-embedding-3-small`);
  tên chuẩn = phần sau dấu `/` cuối. Đường đọc MUST lọc `embedding_model = <tên chuẩn>` và dùng cùng model cho truy vấn.
- **Rationale**: ai-service mặc định OpenRouter (`openai/...`), DDL mặc định tên OpenAI. Không chốt thì đường đọc
  lọc theo một chuỗi, đường ghi lưu chuỗi khác → truy hồi trả rỗng mà không báo lỗi.
- **Provider**: client OpenAI-compatible (`openai` SDK, `base_url` từ `LLM_BASE_URL`), cùng tên env với ai-service
  (`LLM_API_KEY`, `LLM_BASE_URL`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`).
- **VERIFY**: key Thắng chia sẻ gọi được endpoint `/embeddings` của provider đó (OpenRouter hay OpenAI) và trả 1536
  chiều. Lệnh `index` gọi thử 1 lần trong preflight; lỗi → dừng trước khi ghi (FR-019). Nếu OpenRouter không phục vụ
  embeddings: đặt `LLM_BASE_URL=https://api.openai.com/v1`, `EMBEDDING_MODEL=text-embedding-3-small`.

## R3. `content_hash`, chuẩn hóa và dedup

- **Decision**: Một hàm duy nhất `content_hash(content) = md5(lower(strip(content)))` tính trên `content` **đã làm
  sạch**; bước làm sạch chuẩn hóa Unicode **NFC** trước tiên. Dedup trong lần chạy theo hash, trước embed (FR-008).
- **Rationale**: khớp comment DDL (`md5(lower(trim(content)))`). Văn bản tiếng Việt dán từ nhiều nguồn trộn NFC/NFD
  ("ệ" một hay ba code point) → không NFC thì hai câu giống hệt có hash khác, dedup và kiểm tra trùng đều trượt.
  Hash chỉ tính ở Python, DB không tính lại, nên khác biệt `lower()` Python/Postgres không ảnh hưởng.
- **Làm sạch** (FR-006): NFC → bỏ thẻ HTML sót (`html.parser` stdlib, giữ text) → unescape entity → bỏ ký tự điều
  khiển (trừ `\n`, `\t`) → gộp khoảng trắng trong dòng, tối đa 1 dòng trống → strip. Giữ nguyên code block và dấu.
- **Trùng gần đúng** (FR-005, chỉ cảnh báo): so câu hỏi đã chuẩn hóa (lower, bỏ dấu, bỏ dấu câu) bằng
  `difflib.SequenceMatcher` ratio ≥ 0.9. 200 cặp → ~20k phép so, chạy < 1 s.
- **Alternatives**: MinHash/embedding similarity → thừa ở quy mô này (YAGNI).

## R4. Ghi idempotent và dọn bản cũ (FR-012, FR-013)

- **Decision**: Theo thứ tự trong một lần `index`:
  1. Preflight (FR-019): có key, kết nối DB được, có extension `vector` và bảng `knowledge_chunks`, embed thử 1 chuỗi.
     Lỗi → thoát mã 2, chưa ghi gì.
  2. Tra hash đã có: `SELECT content_hash, metadata->>'dataset' FROM knowledge_chunks WHERE content_hash = ANY(...)`.
  3. Hash mới → embed theo batch (100) → `INSERT ... ON CONFLICT (content_hash) DO NOTHING`, commit theo batch.
  4. Hash đã có, **cùng `dataset`** → `UPDATE` các cột phân loại + `metadata` (đổi `topic_id`/độ khó/tags mà nội dung
     không đổi), không embed lại.
  5. Hash đã có, **khác `dataset`** (vd seed mock của AIE) → bỏ qua, đếm vào "skipped (dataset khác)".
  6. Dọn: `DELETE FROM knowledge_chunks WHERE source_type = 'interview_qa' AND metadata->>'dataset' = :dataset AND
     content_hash <> ALL(:hashes_of_this_run)`. **Chỉ chạy khi lần này 0 embedding lỗi**; có lỗi thì báo
     "cleanup skipped" để không xóa bản cũ khi bản mới chưa vào kho.
- **Rationale**: SC-004 (chạy lại: 0 bản ghi mới, 0 lời gọi embed) nhờ bước 2. Sửa đáp án → hash `qa_pair` đổi → bản
  mới vào, bản cũ bị dọn ở bước 6. Xóa cặp khỏi seed → cả hai bản bị dọn. Không đụng dataset khác (FR-013).
- **Đổi model embedding**: S1 chỉ một model; FR-014 lưu tên model là đủ để nhận diện. Embed lại khi đổi model để dành
  cho lúc có quyết định đổi model (constitution IV: cần ADR).
- **Alternatives**: xóa hết dataset rồi ghi lại → embed lại toàn bộ mỗi lần, vi phạm SC-004. Bị loại.

## R5. Đọc topic catalog như dữ liệu

- **Decision**: Đọc trực tiếp `apps/ai-service/app/catalog/*.yaml` bằng `pyyaml`, chỉ lấy `topics[].id` và
  `topics[].category` (bỏ `scenarios` — FR-002). Thư mục mặc định qua env `CATALOG_DIR`. Cờ `--extra-catalog <dir>`
  cho phép soạn trước với YAML đề xuất trong [contracts/topic-catalog-proposal/](contracts/topic-catalog-proposal/);
  **nghiệm thu SC-001 MUST chạy không có cờ này**, trên catalog đã merge.
- **Rationale**: không import code ai-service (R1). Catalog mở rộng chưa merge (51 → 90 topic) nên cần soạn song song.
- **Lưu ý**: `Category` của ai-service chưa có `Frontend`; cột `category` là `VARCHAR`, không ràng buộc, nên pipeline
  ghi được. Thêm `Frontend` vào code catalog là việc của AIE (spec, lệch phát hiện #6).

## R6. Nguồn Q&A công khai và luật tính quota (FR-003)

- **Danh sách giấy phép cho phép (tường minh)**: `CC0-1.0`, `MIT`, `Apache-2.0`, `CC-BY-4.0`, `CC-BY-SA-4.0`,
  `CC-BY-SA-2.5` (MDN, nếu dùng). Mọi giá trị khác, kể cả GPL, `NOASSERTION`, ND/NC → lỗi kiểm tra.
- **Luật tính 50% công khai**: cặp chỉ tính là công khai khi **cả câu hỏi và đáp án** lấy/chuyển thể từ nguồn có giấy
  phép trên (`synthetic = false`, có `source` URL + `attribution`). Lấy câu hỏi từ nguồn công khai nhưng tự soạn đáp
  án → `synthetic = true`, **không tính**. Dịch/chuyển thể sang tiếng Việt vẫn là cặp công khai (giấy phép cho phép
  sửa đổi).
- **Nguồn đã kiểm giấy phép qua GitHub API (2026-10-19)**:

  | Nhóm | Nguồn | Giấy phép | Có đáp án | Ghi chú |
  |---|---|---|---|---|
  | Frontend | sudheerj/reactjs-interview-questions | MIT | có | tiếng Anh, hàng trăm cặp |
  | Frontend | lydiahallie/javascript-questions | MIT | có | câu đố output JS |
  | Frontend | react.dev (docs) | CC-BY-4.0 | chuyển thể | nguồn crawl mẫu US5 (R8) |
  | Backend Python | DevLoversTeam/python-interview-questions | MIT | có | tiếng Ukraina, ~250 cặp |
  | Backend Python | yakimka/python_interview_questions | MIT | có | tiếng Nga |
  | Backend Node | DevLoversTeam/nodejs-interview-questions | MIT | có | tiếng Ukraina, ~100 cặp |
  | Backend Java | codefarm0/Spring-Boot-Interview-Question-Answers | MIT | có | ít |
  | AI (ML cổ điển) | alexeygrigorev/data-science-interviews (`theory.md`) | CC-BY-4.0 | có | |
  | System Design | donnemartin/system-design-primer | CC-BY-4.0 | chuyển thể | |
  | DevOps | jakshi/devops-interview-questions | Apache-2.0 | **không** | đáp án tự soạn → synthetic |
  | Frontend | h5bp/Front-end-Developer-Interview-Questions | MIT | **không** | đáp án tự soạn → synthetic |

  **Loại**: bregman-arie/devops-exercises (CC BY-NC-ND 3.0), ByteByteGoHq/system-design-101 (CC BY-NC-ND 4.0),
  arialdomartini/Back-End-Developer-Interview-Questions (GPL-2.0, ngoài danh sách), các repo không có giấy phép
  (sudheerj/javascript-interview-questions, chiphuyen/ml-interviews-book, ...).
- **Khả thi**: Java backend, Database, DevOps, AI cutting-edge gần như phải tự soạn. Đạt ≥ 50% công khai khi lấy
  > 2 cặp/topic ở Frontend, Python, Node, ML, System Design (~110 cặp). Catalog 90 topic × 2 = 180 cặp tối thiểu.
- **Giấy phép của seed**: nếu có nội dung CC BY-SA thì cả bộ seed phát hành CC BY-SA 4.0 (tương thích MIT, CC BY,
  Apache-2.0 khi gộp). File `NOTICE` trong thư mục seed liệt kê nguồn + giấy phép + tác giả.

## R7. Định dạng seed và tổ chức file

- **Decision**: Seed là thư mục `apps/data-pipeline/data/seeds/interview_qa/`, mỗi file JSON là một mảng cặp (chia
  theo nhóm, vd `frontend.json`, `backend-python.json`); loader đọc mọi `*.json` theo thứ tự tên file. Định dạng:
  [contracts/qa-seed-format.md](contracts/qa-seed-format.md). `dataset = de_interview_qa`, `qa_id = de-qa-NNNN`.
- **Rationale**: file nhỏ dễ review trong PR và soạn song song; một file 200+ cặp gây xung đột merge.
- **Seed mock của AIE** (`apps/ai-service/data/seeds/qa_seed.json`): chỉ nhập khi DE review đáp án và gán
  `qa_id` + `topic_id` (FR-003); không dùng làm golden set.

## R8. Crawler mẫu (US5)

- **Decision**: Nguồn mẫu **react.dev** (`/learn`, `/reference`): nội dung CC BY 4.0 (`LICENSE-DOCS.md` của
  reactjs/react.dev), robots.txt `Disallow:` rỗng (2026-10-19). Record thô = URL, tiêu đề, text theo heading,
  thời điểm crawl → `data/raw/react_docs/*.jsonl`. DE chuyển thể một phần thành cặp Q&A Frontend (`synthetic = false`,
  `license = CC-BY-4.0`) → đóng góp quota công khai; dữ liệu còn lại dùng lại cho textbook (012).
- **Công cụ**: `httpx` + `BeautifulSoup` cho trang tĩnh; `playwright` (Chromium) cho trang cần JS, import lười để CI
  không cần trình duyệt. `urllib.robotparser` kiểm robots trước mỗi URL; khoảng nghỉ cấu hình được (mặc định 1 s);
  giới hạn số trang; user-agent ghi tên dự án. Scrub email/số điện thoại bằng regex trước khi lưu (FR-023). 0 record →
  thoát lỗi (FR-025).
- **Alternatives**: Scrapy → nặng cho 1 nguồn mẫu; 009 (500+ JD) cân nhắc lại khi cần concurrency. MDN Glossary
  (CC BY-SA 2.5) → share-alike, dự phòng. Trang JD (topcv, itviec) → điều khoản/robots chưa kiểm, để 009.
- **VERIFY**: robots.txt và cấu trúc HTML react.dev lúc chạy; Playwright cài được trên Windows (`playwright install
  chromium`).

## R9. Golden set và cách đo (US4)

- **Decision**: File `apps/data-pipeline/data/seeds/golden_set.json` (commit; thay vị trí
  `apps/ai-service/tests/rag_golden.json` ở rag-design §7 vì DE soạn và chạy). Recall@5 của một truy vấn =
  |nhãn ∩ `qa_id` trong top-5 bản ghi| / |nhãn|; tổng = trung bình. Tìm trên `interview_qa` cả hai `chunk_type`.
  Lệnh `eval` luôn thoát 0 khi chạy xong (FR-021: không chặn CI/merge); thoát khác 0 chỉ khi lỗi cấu hình.
- **Kiểm tra golden set**: truy vấn trùng nguyên văn (sau chuẩn hóa) một câu hỏi trong seed → lỗi (US4-2); nhãn trỏ
  tới `qa_id` không tồn tại → lỗi; mỗi nhóm (a)–(e) có ≥ 1 truy vấn; `approved_by` rỗng → báo cáo ghi "nhãn chưa duyệt".

## R10. Test và CI

- **Decision**: `pytest` chỉ test logic offline (US1, US2, eval metric, scrub PII, robots với fixture). Không gọi
  mạng, không cần key, không cần DB. Khi `apps/data-pipeline/requirements.txt` xuất hiện, job `python` của CI (#5) tự
  chạy. Ghi/đọc DB kiểm chứng bằng [quickstart.md](quickstart.md) §4–5 trên máy dev.
- **Rationale**: constitution VI (Python service MUST có test cho logic chính) + CI không dùng secret (001 FR-011).
- **Dependencies** (pin trong `requirements.txt`): `openai`, `psycopg[binary]` 3, `pgvector`, `pyyaml`,
  `python-dotenv`, `httpx`, `beautifulsoup4`, `playwright`. Dev: `pytest`.
