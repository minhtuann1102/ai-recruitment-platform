# Implementation Plan: RAG Knowledge Base — Interview Q&A

**Branch**: `docs/rag-knowledge-base-qa-plan` (plan) → `feat/data-pipeline/qa-offline` → `feat/data-pipeline/qa-index`
→ `feat/data-pipeline/sample-crawler`; seed theo lô `feat/data-pipeline/qa-seed-*` | **Date**: 2026-10-19 |
**Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/005-rag-knowledge-base-qa/spec.md`

## Summary

App Python mới `apps/data-pipeline/` với CLI `python -m pipeline`: `validate` (US1) kiểm seed Q&A theo topic catalog
và giấy phép; `process` (US2) làm sạch NFC → 2 bản ghi/cặp → dedup theo `content_hash`, chạy offline; `index` (US3)
embed bản ghi mới qua API OpenAI-compatible và ghi idempotent vào `knowledge_chunks`, dọn bản cũ cùng `dataset`;
`search` / `eval` (US3, US4) truy hồi chỉ đọc + recall@5 trên golden set; `crawl react-docs` (US5) crawler mẫu tôn
trọng robots.txt. Seed curated ≥ 200 cặp commit trong `data/seeds/interview_qa/`. Đường đọc production (S1-AIE-2)
thuộc AIE, chỉ chia sẻ hợp đồng [knowledge-chunks-io.md](contracts/knowledge-chunks-io.md).

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: `openai` (client OpenAI-compatible), `psycopg[binary]` 3 + `pgvector`, `pyyaml`,
`python-dotenv`, `httpx` + `beautifulsoup4`, `playwright` (import lười, chỉ `--render`); dev: `pytest`

**Storage**: đọc seed JSON + catalog YAML; ghi `ai_db.knowledge_chunks` (PostgreSQL 16 + pgvector, 001 PR #6);
file trung gian `data/raw/`, `data/processed/` (gitignore)

**Testing**: `pytest` offline (validator, làm sạch, chunk, hash/dedup, metric eval, scrub PII, robots với fixture);
DB/API kiểm bằng [quickstart.md](quickstart.md) §4–6

**Target Platform**: máy dev Windows/macOS/Linux; CI `ubuntu-latest` job `python` (đã có, #5)

**Project Type**: CLI / batch data pipeline trong monorepo

**Performance Goals**: 200 cặp end-to-end ≤ 10 phút, chi phí embed < 0,1 USD (SC-006); truy hồi exact scan ~400
bản ghi (không ANN index)

**Constraints**: CI không key, không DB; không tạo/sửa bảng (FR-011); không import code ai-service (research R1);
nghiệm thu catalog đã merge (R5); file code < 200 dòng (constitution VII)

**Scale/Scope**: ≥ 200 cặp → ≥ 400 bản ghi; golden set ≥ 20 truy vấn; crawler 1 nguồn ≥ 50 trang

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Đánh giá | Ghi chú |
|---|---|---|
| I. DB-per-Service | ✅ | Chỉ ghi `ai_db.knowledge_chunks` theo DDL của AIE; không tạo/sửa bảng (FR-011) |
| II. Gateway & Transport | ✅ N/A | Không có endpoint HTTP mới |
| III. Contract-First | ✅ | Hợp đồng ghi/đọc, seed, CLI chốt trong [contracts/](contracts/); không thêm API ai-service |
| IV. AI Stateless | ✅ | Model embedding mặc định `text-embedding-3-small` 1536 chiều qua `LLM_BASE_URL`; tên lưu chuẩn hóa (R2) |
| V. Data Pipeline tái lập | ✅ | Hash dedup trước embed, upsert + dọn theo `dataset` (R4); raw/processed gitignore; thống kê mỗi lần chạy; crawler robots + rate limit + scrub PII |
| VI. Quality Gates | ✅ | pytest cho logic chính chạy trong CI hiện có; không secret; biến mới trong `.env.example` (Python, không cần `turbo.json`) |
| VII. Đơn giản & phạm vi | ✅ | Không ANN index, hybrid, rerank, cache (spec: ngoài phạm vi); không Scrapy cho 1 nguồn (R8); module < 200 dòng |

Post-design re-check (sau Phase 1): ✅ không phát sinh vi phạm; không cần Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/005-rag-knowledge-base-qa/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/
│   ├── qa-seed-format.md          # seed + golden set, luật validate
│   ├── knowledge-chunks-io.md     # hợp đồng ghi (DE) / đọc (AIE)
│   ├── pipeline-cli.md            # lệnh, mã thoát, thống kê, env
│   └── topic-catalog-proposal/    # YAML đề xuất (AIE merge)
├── checklists/requirements.md
└── tasks.md                       # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
apps/data-pipeline/
├── requirements.txt · requirements-dev.txt · .env.example
├── pipeline/
│   ├── __main__.py                  # argparse: validate | process | index | search | eval | crawl
│   ├── settings.py                  # env + tên model chuẩn (R2)
│   ├── topic_catalog_reader.py      # YAML → {topic_id: category} (R5)
│   ├── qa_seed_loader.py            # đọc data/seeds/interview_qa/*.json
│   ├── qa_seed_validator.py         # luật qa-seed-format + báo cáo phân bố (US1)
│   ├── pii_patterns.py              # regex email / số điện thoại (US1, US5)
│   ├── text_cleaning.py             # NFC, HTML, control chars, whitespace (R3)
│   ├── qa_record_builder.py         # 1 cặp → 2 record + content_hash + dedup (US2)
│   ├── run_report.py                # thống kê + ghi JSON
│   ├── embedding_client.py          # batch 100, retry giới hạn (FR-015)
│   ├── knowledge_chunk_writer.py    # preflight, tra hash, insert/update/dọn (R4) — đường ghi duy nhất
│   ├── knowledge_chunk_search.py    # SQL đọc theo contract (search/eval)
│   └── golden_set_eval.py           # kiểm golden set + recall@k (US4)
├── crawlers/
│   ├── polite_fetcher.py            # robots, delay, max pages, httpx | playwright
│   └── react_docs_crawler.py        # nguồn mẫu → raw record (US5)
├── data/
│   ├── seeds/interview_qa/*.json    # commit — seed curated + NOTICE (nguồn, giấy phép)
│   ├── seeds/golden_set.json        # commit
│   ├── raw/  processed/             # gitignore
└── tests/                           # pytest offline + fixtures
.gitignore                           # + apps/data-pipeline/data/{raw,processed}/, .venv
docs/architecture/data-pipeline.md   # §3, §7, §8 trỏ về plan này (cập nhật cùng PR qa-index)
```

**Structure Decision**: Tên module Python dùng snake_case (quy ước ngôn ngữ), tên mô tả rõ trách nhiệm. Không dùng
`processors/` + `pipeline/` tách đôi như phác thảo data-pipeline.md §3 vì S1 chỉ có một nguồn; 009/012 thêm module
`*_record_builder.py` cạnh `qa_record_builder.py` và dùng lại `text_cleaning`, `embedding_client`,
`knowledge_chunk_writer` (tham số hóa `source_type` + `dataset` khi đó).

## Delivery Sequence

| PR | Nội dung | Story | Phụ thuộc | Merge khi |
|---|---|---|---|---|
| `qa-offline` | scaffold, `validate`, `process`, tests, `.gitignore` | US1 (công cụ), US2 | — | CI xanh |
| `qa-seed-*` (nhiều lô) | cặp Q&A theo nhóm + `NOTICE` | US1 (dữ liệu) | `qa-offline` | `validate` sạch; lô Frontend/DevOps/AI mới chờ AIE merge catalog |
| `qa-index` | `index`, `search`, `eval`, golden set | US3, US4 | 001 PR #6 merged, key | quickstart §4–6 trên máy dev |
| `sample-crawler` | `crawl react-docs` | US5 | `qa-offline` | quickstart §7 |

Thứ tự cắt khi trễ (kiểm vào thứ Năm 22/10): US4 chỉ báo cáo với golden set nhỏ → US5 crawl tối thiểu không
`--render`. Không hạ ngưỡng 200 cặp / 50% công khai mà không báo team.

## Complexity Tracking

Không có vi phạm constitution cần biện minh.
