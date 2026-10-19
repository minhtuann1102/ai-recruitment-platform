# Quickstart: kiểm chứng RAG Knowledge Base — Interview Q&A

Checklist nghiệm thu theo story và kịch bản demo Sprint 1. Bash (Git Bash trên Windows), chạy trong
`apps/data-pipeline/`. Lệnh và mã thoát: [contracts/pipeline-cli.md](contracts/pipeline-cli.md).

## 0. Chuẩn bị (SC-007: ≤ 5 lệnh)

```bash
cd apps/data-pipeline
python -m venv .venv && . .venv/Scripts/activate      # Linux/macOS: . .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env                                   # §4–6: điền LLM_API_KEY (xin riêng, không commit)
```

## 1. Bộ dữ liệu (US1, SC-001, SC-002) — offline

```bash
python -m pipeline validate --strict
```

Kỳ vọng: thoát 0; báo cáo ≥ 200 cặp, mọi topic ≥ 2 cặp, mỗi độ khó ≥ 20%, công khai ≥ 50%, 0 trùng, 0 PII.
Kiểm luật lỗi: `pytest tests -k validator` (fixture thiếu trường, `topic_id` lạ, giấy phép NC, câu trùng, topic thiếu).

## 1b. Thu thập + dịch (US1, quyết định 2026-10-19)

```bash
GITHUB_TOKEN=$(gh auth token) python -m pipeline collect          # ~4.800 cặp -> data/raw/collected_qa/
python -m pipeline enrich --per-source 3 \
  --extra-catalog ../../specs/005-rag-knowledge-base-qa/contracts/topic-catalog-proposal   # thử; bỏ --per-source để chạy hết (cần key)
```

Kỳ vọng: `collect` thoát 0; `enrich` in số cặp dịch được / bị loại theo lý do + chi phí ước tính. Nội dung chỉ nằm ở
`data/raw/` (gitignore) — `git status` không thấy file dữ liệu.

## 2. Xử lý offline (US2, FR-009) — không DB, không key

```bash
python -m pipeline process && sha256sum data/processed/interview_qa.jsonl
python -m pipeline process && sha256sum data/processed/interview_qa.jsonl   # cùng hash = deterministic
```

Kỳ vọng: `chunks_out = 2 × records_in − trùng`; `dedup_ratio < 5%` (SC-003).

## 3. Test tự động (CI)

```bash
pytest -q
```

## 4. Index (US3, SC-003, SC-004, SC-006) — cần `docker compose up -d` (001) và key

```bash
python -m pipeline index      # lần 1: inserted ≥ 400, embed_errors = 0, ≤ 10 phút
python -m pipeline index      # lần 2: embedded = 0, inserted = 0
docker exec ai_recruit_db psql -U postgres -d ai_db -tAc \
  "SELECT metadata->>'chunk_type', count(*), count(embedding) FROM knowledge_chunks
   WHERE source_type='interview_qa' AND metadata->>'dataset'='de_interview_qa' GROUP BY 1;"
```

Sửa đáp án một cặp + xóa một cặp khỏi seed → `index` → `updated/deleted` đúng, `search` không còn trả bản cũ
(US3-3). Đổi `LLM_API_KEY` thành rỗng → `index` thoát 2, bảng không đổi (US3-6).

## 5. Truy hồi (US3-4, US3-5, SC-009 demo)

```bash
python -m pipeline search "event loop trong Node.js chạy thế nào" --category Backend --difficulty medium
python -m pipeline search "useEffect cleanup" --chunk-type qa_pair
```

Kỳ vọng: ≤ k kết quả, điểm giảm dần, đúng bộ lọc, mỗi dòng có `qa_id`. Demo: 5 truy vấn soạn trước, ≥ 4/5 có top-5
đúng chủ đề. Tra theo `qa_id` (US3-5) là đường đọc của AIE (`app/rag/`), kiểm khi S1-AIE-2 xong.

## 6. Golden set (US4, SC-005)

```bash
python -m pipeline eval
```

Kỳ vọng: recall@5 tổng + 5 nhóm (a)–(e), truy vấn trượt, top-3 mỗi truy vấn; ghi rõ "chưa đạt 0.8" nếu thấp; thoát 0.

## 7. Crawler mẫu (US5, SC-008) — không DB, không key

```bash
python -m pipeline crawl react-docs --max-pages 60 --delay 1
```

Kỳ vọng: ≥ 50 record có `url` + `crawled_at`; log có dòng kiểm robots.txt; khoảng cách request ≥ 1 s;
`grep -cE '[[:alnum:]._%+-]+@[[:alnum:].-]+\.[a-z]{2,}' data/raw/react_docs/*.jsonl` = 0. Trang cần JS: thêm `--render`
(cần `playwright install chromium` một lần).
