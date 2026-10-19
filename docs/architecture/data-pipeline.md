# Data Pipeline — DE Track

> Tài liệu cho DE (Data Engineer + DevOps). Mô tả toàn bộ pipeline thu thập, xử lý, và index dữ liệu vào ai_db phục vụ RAG.

## 1. Tổng quan

```
Nguồn dữ liệu                  Xử lý                    Lưu trữ
─────────────                  ──────                   ────────
Interview Q&A (curated)  ──┐
Job Descriptions (crawl) ──┼──▶ clean → chunk ──▶ embed ──▶ ai_db (pgvector)
Textbook/Tutorial        ──┘   → dedup → tag          knowledge_chunks
```

**Embedding model:** `text-embedding-3-small` (OpenAI, 1536 dims)
**Vector store:** PostgreSQL + pgvector extension (`ai_db`)
**Target total:** ~6000+ chunks sau Sprint 3

## 2. Nguồn dữ liệu

| Sprint | Loại | Nguồn | Volume | source_type |
|---|---|---|---|---|
| S1 | Interview Q&A | Curated thủ công + public datasets | 200+ cặp Q&A | `interview_qa` |
| S2 | Job Descriptions | Crawl: topcv.vn, itviec.com | 500+ JD | `job_description` |
| S3 | Textbook/Tutorial | Node.js, React, PostgreSQL docs; CS fundamentals; System Design | 5000+ chunks | `textbook` |

---

## 3. Cấu trúc thư mục

```
apps/data-pipeline/
├── crawlers/
│   ├── jd_crawler.py          # Scrapy spider crawl JD từ IT job sites
│   └── docs_crawler.py        # Crawl technical documentation
├── processors/
│   ├── qa_processor.py        # Xử lý Interview Q&A (JSON/CSV → chunks)
│   ├── jd_processor.py        # Xử lý Job Description text → chunks
│   └── textbook_processor.py  # Xử lý docs/tutorial → chunks theo section
├── pipeline/
│   ├── embedder.py            # Gọi OpenAI text-embedding-3-small
│   ├── indexer.py             # Upsert chunks vào ai_db (pgvector)
│   └── deduper.py             # Phát hiện và loại bỏ chunks trùng
├── data/
│   ├── raw/                   # Dữ liệu thô sau crawl (gitignore)
│   ├── processed/             # Chunks sau clean (gitignore)
│   └── seeds/
│       └── qa_seed.json       # Q&A curated ban đầu (commit được)
├── scripts/
│   ├── run_qa_pipeline.sh     # S1: chạy Q&A ingestion
│   ├── run_jd_pipeline.sh     # S2: chạy JD crawl + ingestion
│   └── run_textbook_pipeline.sh # S3: chạy textbook ingestion
├── requirements.txt           # scrapy, playwright, openai, psycopg2, python-dotenv
└── .env.example               # OPENAI_API_KEY, AI_DB_URL
```

---

## 4. Sprint 1 — Interview Q&A

### Nguồn dữ liệu
- 200+ cặp Q&A phỏng vấn CNTT: ≥ 50% từ nguồn công khai có giấy phép cho phép sửa đổi và phân phối lại (CC0, MIT,
  Apache-2.0, CC BY, CC BY-SA; không dùng ND/NC hoặc không rõ giấy phép), phần còn lại tự soạn (`synthetic: true`,
  có review)
- Phân loại theo **topic catalog** (`apps/ai-service/app/catalog/*.yaml`): mỗi cặp bắt buộc `topic_id`, `category`
  suy ra từ topic (`Backend`, `Frontend`, `Database`, `System Design`, `DevOps`, `AI`). Track Frontend, DevOps và các
  topic AI mới: xem đề xuất trong `specs/005-rag-knowledge-base-qa/contracts/topic-catalog-proposal/`
- Mỗi topic ≥ 2 cặp. Difficulty `easy | medium | hard` theo rubric 1–5 của ai-service: easy = định nghĩa, ví dụ
  (1–2); medium = áp dụng, so sánh, xử lý lỗi (3); hard = internals, trade-off ở scale (4–5)

Yêu cầu đầy đủ: [specs/005-rag-knowledge-base-qa](../../specs/005-rag-knowledge-base-qa/spec.md).

### Format seed Q&A

```json
[
  {
    "qa_id": "de-qa-0001",
    "topic_id": "node.core.event-loop",
    "question": "Giải thích các pha của event loop trong Node.js?",
    "answer": "Event loop gồm các pha ...",
    "difficulty": "medium",
    "language": "vi",
    "tags": ["event-loop"],
    "source": "https://github.com/...",
    "license": "MIT",
    "synthetic": false
  }
]
```

`qa_id` gán khi tạo, không đổi, không tái sử dụng. Pipeline ghi thêm `metadata.dataset` để chỉ dọn bản ghi của
chính bộ dữ liệu đó.

### Processing

Mỗi cặp sinh 2 bản ghi `question` (chỉ câu hỏi) và `qa_pair` (câu hỏi + đáp án), cùng `qa_id`, `topic_id`,
`category`, `difficulty`, `language` (cột thật, không chỉ trong JSONB). Chi tiết chunking và schema:
[rag-design.md](rag-design.md) §2, §3.

**Output Sprint 1:** ~400+ chunks (200 Q&A × 2 chunks/cặp) → index vào ai_db.

---

## 5. Sprint 2 — Job Descriptions

### Crawl (`crawlers/jd_crawler.py`)

Dùng Scrapy + Playwright (cho JS-rendered pages):

```python
# Target sites
CRAWL_TARGETS = [
    {"site": "topcv.vn", "url": "https://www.topcv.vn/tim-viec-lam-it", "max_pages": 50},
    {"site": "itviec.com", "url": "https://itviec.com/it-jobs", "max_pages": 50},
]

# Fields cần extract
JD_FIELDS = ["title", "company", "description", "requirements", "skills", "location", "salary_range"]
```

**Verify crawl:**
```bash
cd apps/data-pipeline
python -m scrapy crawl jd_spider -o data/raw/jd_raw.json --logfile logs/crawl.log
# Expect: >= 500 records trong jd_raw.json
```

### Processing (`jd_processor.py`)

Mỗi JD tách thành chunks theo section:

```python
SECTION_PATTERNS = {
    "requirements": ["yêu cầu", "requirements", "required skills"],
    "responsibilities": ["trách nhiệm", "responsibilities", "job description"],
    "benefits": ["quyền lợi", "benefits", "we offer"],
}

def process_jd(jd: dict) -> list[dict]:
    chunks = []
    # Chunk 1: Title + Company + Skills summary
    chunks.append({
        "content": f"{jd['title']} tại {jd['company']}. Skills: {', '.join(jd.get('skills', []))}",
        "source_type": "job_description",
        "metadata": {"company": jd["company"], "title": jd["title"], "chunk_type": "summary"},
    })
    # Chunk 2+: Mỗi section riêng
    for section_name, content in extract_sections(jd["description"]).items():
        if len(content) > 50:
            chunks.append({
                "content": content[:1000],  # max 1000 chars/chunk
                "source_type": "job_description",
                "metadata": {"company": jd["company"], "section": section_name, "chunk_type": "section"},
            })
    return chunks
```

**Output Sprint 2:** ~1500+ chunks từ 500 JD (avg ~3 chunks/JD) → index vào ai_db. Seed 200 job postings vào `job_db` dùng JD data.

---

## 6. Sprint 3 — Textbook/Tutorial

### Nguồn

| Nguồn | URL/Method | Category | Ước tính chunks |
|---|---|---|---|
| Node.js docs | https://nodejs.org/en/docs | Backend | ~300 |
| React docs | https://react.dev/learn | Frontend | ~400 |
| PostgreSQL docs | https://www.postgresql.org/docs | Database | ~500 |
| NestJS docs | https://docs.nestjs.com | Backend | ~300 |
| System Design Primer | GitHub README crawl | System Design | ~200 |
| CS fundamentals | Curate thủ công | General | ~300 |
| Golang/Python basics | Curate thủ công | Backend | ~200 |

### Processing (`textbook_processor.py`)

```python
CHUNK_SIZE = 512    # tokens
CHUNK_OVERLAP = 50  # tokens

def process_doc(raw_text: str, metadata: dict) -> list[dict]:
    # Chunk theo section header (h2/h3) nếu có
    # Fallback: sliding window 512 tokens với overlap 50
    chunks = chunk_by_headers(raw_text) or sliding_window(raw_text, CHUNK_SIZE, CHUNK_OVERLAP)
    return [
        {
            "content": chunk,
            "source_type": "textbook",
            "metadata": {**metadata, "chunk_index": i},
        }
        for i, chunk in enumerate(chunks)
    ]
```

**Output Sprint 3:** ~2000-5000+ chunks → index vào ai_db. Target tổng ai_db: **6000+ chunks** covering Backend, Frontend, DB, System Design.

---

## 7. Embedding & Indexing

> **Lỗi thời một phần:** code dưới đây là phác thảo ban đầu. `ON CONFLICT DO NOTHING` không có tác dụng khi bảng
> không có ràng buộc unique, và schema đã đổi (cột `category`, `difficulty`, `topic_id`, `content_hash UNIQUE`...).
> Dùng [rag-design.md](rag-design.md) §3 và [specs/005](../../specs/005-rag-knowledge-base-qa/spec.md) FR-011–FR-016;
> thiết kế indexer chốt ở plan 005.

### `pipeline/embedder.py`

```python
from openai import OpenAI
import time

client = OpenAI()  # reads OPENAI_API_KEY

def embed_chunks(chunks: list[dict], batch_size: int = 100) -> list[dict]:
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        texts = [c["content"] for c in batch]
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=texts,
        )
        for j, item in enumerate(response.data):
            batch[j]["embedding"] = item.embedding
        time.sleep(0.1)  # tránh rate limit
    return chunks
```

**Chi phí ước tính:** text-embedding-3-small ~$0.02/1M tokens. 6000 chunks × 300 tokens avg = 1.8M tokens → ~$0.036 total.

### `pipeline/indexer.py`

```python
import psycopg2
from pgvector.psycopg2 import register_vector

def upsert_chunks(chunks: list[dict], conn_str: str):
    conn = psycopg2.connect(conn_str)
    register_vector(conn)
    cur = conn.cursor()
    cur.executemany(
        """
        INSERT INTO knowledge_chunks (content, embedding, source_type, metadata)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT DO NOTHING
        """,
        [(c["content"], c["embedding"], c["source_type"], json.dumps(c["metadata"]))
         for c in chunks],
    )
    conn.commit()
```

### `pipeline/deduper.py`

```python
import hashlib

def dedup_chunks(chunks: list[dict]) -> list[dict]:
    # Content-hash dedup trước khi embed (tiết kiệm API calls)
    seen = set()
    result = []
    for chunk in chunks:
        h = hashlib.md5(chunk["content"].strip().lower().encode()).hexdigest()
        if h not in seen:
            seen.add(h)
            result.append(chunk)
    return result
```

---

## 8. Chạy pipeline

### Sprint 1 — Q&A

```bash
cd apps/data-pipeline
cp .env.example .env   # điền OPENAI_API_KEY, AI_DB_URL

python pipeline/run.py \
  --source qa \
  --input data/seeds/qa_seed.json \
  --verify
```

### Sprint 2 — JD

```bash
# Step 1: Crawl
python -m scrapy crawl jd_spider -o data/raw/jd_raw.json

# Step 2: Process + embed + index
python pipeline/run.py \
  --source jd \
  --input data/raw/jd_raw.json \
  --verify
```

### Sprint 3 — Textbook

```bash
python pipeline/run.py \
  --source textbook \
  --input data/raw/textbook/ \
  --verify
```

**Verify sau mỗi pipeline:**
```bash
# Kiểm tra số chunks đã index
docker exec ai_recruit_db psql -U postgres -d ai_db \
  -c "SELECT source_type, COUNT(*) FROM knowledge_chunks GROUP BY source_type;"

# Test semantic search
python pipeline/test_search.py --query "REST API design best practices" --top_k 5
```

---

## 9. Quality Gates

| Metric | Mức tối thiểu | Cách đo |
|---|---|---|
| Số chunks indexed | 200 (S1), 1500 (S2), 6000 (S3) | `SELECT COUNT(*) FROM knowledge_chunks` |
| Retrieval relevance | Golden set ≥ 20 queries, recall@5 ≥ 0.8 (mục tiêu, báo cáo, không chặn merge) + xem tay top-3 | lệnh đánh giá golden set (spec 005 US4) |
| Chunk coverage | S1: mỗi topic trong catalog ≥ 2 cặp Q&A. S3: theo `category` — chốt lại ở 012 | `GROUP BY category, topic_id` |
| Embedding success rate | >= 99% chunks có embedding not null | `SELECT COUNT(*) WHERE embedding IS NULL` |
| Dedup ratio | < 5% trùng lặp | log từ deduper |

---

## 10. Seed job_db từ JD data (Sprint 2)

Dùng JD crawled để seed `job_postings` trong `job_db`:

```python
# scripts/seed_job_db.py
# Map crawled JD → job_postings schema
# 200 bản ghi với skills, location, salary_range thực tế
# Chạy sau khi jd_crawler hoàn thành
```

---

## 11. Phụ thuộc

| Task | Phụ thuộc |
|---|---|
| S1-DE-1 (Q&A index) | S0-AIE-2: ai_db + pgvector đã tạo |
| S2-DE-1 (JD crawl) | Không (crawl độc lập) |
| S2-DE-3 (JD index) | S2-DE-1 xong, S1-AIE-1 RAG ingestion pipeline đã test |
| S2-DE-4 (seed job_db) | S2-DE-1 crawl xong, FSD job-service entities đã tạo |
| S3-DE-3 (textbook index) | S2-DE-3 xong (pipeline đã stable) |
| S3-DE-4 (RAG quality eval) | S3-AIE-1 full agentic E2E chạy được |
