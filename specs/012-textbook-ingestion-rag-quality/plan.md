# Implementation Plan: Textbook Ingestion & RAG Quality

**Branch**: spec + plan trên `docs/textbook-ingestion-spec`; code trên `feat/data-pipeline/textbook-pipeline`; dữ liệu
mỗi lô trên `feat/data-pipeline/textbook-<track>` | **Date**: 2026-11-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/012-textbook-ingestion-rag-quality/spec.md`

## Summary

Nạp docs chính thức dạng giải thích vào `knowledge_chunks` (`source_type = 'textbook'`) cho 28 tình huống `scn.*` của 6
track, bắt đầu bằng lô thử `java_backend`. Cách làm: manifest nguồn commit được (giấy phép, robots, danh sách trang
theo tình huống) → crawl đúng các URL trong manifest → cắt đoạn theo section kèm đường dẫn tiêu đề → lọc nhiễu bằng
luật → worker soát từng đoạn có đoạn mồi → báo cáo độ phủ và kiểm tra truy hồi → ghi vào kho bằng đường ghi của 005,
mỗi nguồn một dataset. Dùng lại `PoliteFetcher`, `GithubRawClient`, parser section của crawler react.dev, `clean_text`,
`scrub_pii`, `content_hash`, `knowledge_chunk_writer`. Quyết định thiết kế: [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.11 (như `apps/data-pipeline` hiện có)

**Primary Dependencies**: đã có trong `requirements.txt`: `httpx`, `beautifulsoup4`, `playwright` (chỉ khi `--render`),
`pyyaml`, `psycopg`, `pgvector`, `openai` (embedding). Không thêm dependency.

**Storage**: `ai_db.knowledge_chunks` trên Supabase dùng chung (chỉ ghi qua `knowledge_chunk_writer`); file YAML / JSON
/ JSONL dưới `apps/data-pipeline/data/` ([data-model.md](data-model.md) §1)

**Testing**: `pytest` offline: không mạng, không DB, không key (005 R10); HTML và markdown mẫu trong `tests/fixtures/`

**Target Platform**: máy DE (Windows 11, Git Bash / PowerShell); lệnh chạy trong `apps/data-pipeline/`

**Project Type**: CLI trong monorepo (`python -m pipeline <lệnh>`)

**Performance Goals**: không có mục tiêu tốc độ; crawl nghỉ ≥ 1 giây giữa request; một nguồn dưới 60 trang

**Constraints**: file code < 200 dòng; không commit dữ liệu thô và đã xử lý; chỉ tải URL trong manifest; `index-textbook`
không đổi bản ghi `interview_qa` / `job_description`; chạy `index` từ `main` mới nhất

**Scale/Scope**: 28 tình huống × 3–5 trang ≈ 85–140 trang; 300–1.500 đoạn; khoảng 10–15 nguồn

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Kiểm tra | Kết quả |
|---|---|---|
| I. Database-per-Service | Chỉ ghi `ai_db.knowledge_chunks`, bám DDL của AIE, không tạo / sửa bảng | Đạt |
| II. Gateway & Transport | Không có route hay service mới | Không áp dụng |
| III. Contract-First | Contract dữ liệu mới ghi ở `contracts/`; cập nhật `docs/architecture/data-pipeline.md` trong PR code | Đạt (task T034) |
| IV. AI Stateless | Không đụng ai-service; chỉ thêm bản ghi vào bảng ai-service sở hữu, đúng `source_type` đã định nghĩa | Đạt |
| V. Pipeline tái lập được | Idempotent qua `content_hash` + upsert theo dataset; dữ liệu thô / đã xử lý ngoài git; mỗi lần chạy in thống kê; robots + rate limit + xóa PII; mỗi đoạn có `source_type`, `category`, `chunk_type` | Đạt |
| V. Quality gates | Embedding non-null ≥ 99% (đếm ở `index-textbook`); dedup < 5% (in ở `process-textbook`, vượt thì rà manifest); số chunk tối thiểu 6.000 đã đạt bằng kho hiện có (8.356) | Đạt |
| VI. Quality Gates | pytest cho logic chính (manifest, cắt đoạn, lọc nhiễu, soát, độ phủ, kế hoạch ghi); không secret; env mới: không có | Đạt |
| VII. Đơn giản | Không thêm service, dependency hay bảng; S3-DE-1..3 thu hẹp (ghi ở spec) | Đạt |
| Quy trình | Spec Kit cho feature của DE; plan link `docs/architecture/*`; branch theo `docs/conventions.md` | Đạt |

Kiểm lại sau Phase 1: không phát sinh vi phạm. Một thay đổi vào code dùng chung của 005 (`write_records` dọn theo
`source_type` của bản ghi, R8) được che bằng test hiện có + test mới.

## Project Structure

### Documentation (this feature)

```text
specs/012-textbook-ingestion-rag-quality/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── textbook-source-manifest.md      # định dạng manifest, luật kiểm
│   ├── pipeline-cli-textbook.md         # 7 lệnh, mã thoát
│   └── textbook-review-instructions.md  # hướng dẫn cố định cho worker (A giấy phép, B danh sách trang, C soát đoạn)
├── checklists/requirements.md
└── tasks.md                             # /speckit-tasks
```

### Source Code (repository root)

```text
apps/data-pipeline/
├── crawlers/
│   ├── docs_section_parser.py           # MỚI: parse_sections tách từ react_docs_crawler + bộ chọn CSS + markdown
│   ├── react_docs_crawler.py            # SỬA: import parser dùng chung
│   └── textbook_manifest_crawler.py     # MỚI: tải đúng URL trong manifest (html / markdown)
├── pipeline/
│   ├── __main__.py                      # SỬA: đăng ký lệnh qua textbook_cli
│   ├── knowledge_chunk_writer.py        # SỬA: dọn theo source_type của bản ghi (R8)
│   ├── settings.py                      # SỬA: đường dẫn textbook
│   ├── textbook_cli.py                  # MỚI: add_parsers + bảng handler của 7 lệnh
│   ├── textbook_catalog_tracks.py       # MỚI: track, category chính, tình huống đọc từ YAML catalog
│   ├── textbook_source_manifest.py      # MỚI: nạp + kiểm manifest, truy vấn tình huống
│   ├── textbook_validate_command.py     # MỚI: validate-textbook
│   ├── textbook_crawl_command.py        # MỚI: crawl-textbook
│   ├── textbook_chunker.py              # MỚI: section -> đoạn (R6)
│   ├── textbook_noise_filter.py         # MỚI: luật lọc nhiễu (R7)
│   ├── textbook_record_builder.py       # MỚI: đoạn -> bản ghi (data-model §3), dedup
│   ├── textbook_review_decisions.py     # MỚI: đọc / gộp / áp quyết định soát
│   ├── textbook_process_command.py      # MỚI: process-textbook
│   ├── textbook_review_prepare.py       # MỚI: review-textbook-prepare
│   ├── textbook_review_score.py         # MỚI: review-textbook-score
│   ├── textbook_keyword_rank.py         # MỚI: BM25 nhỏ cho kiểm tra truy hồi (R10)
│   ├── textbook_coverage_command.py     # MỚI: coverage-textbook
│   └── textbook_index_command.py        # MỚI: index-textbook
├── data/
│   ├── seeds/textbook_sources/          # MỚI, commit: <source_id>.yaml, scenario-queries.yaml, review-canaries.json
│   ├── reviews/textbook/                # MỚI, commit: <source_id>-decisions.json
│   ├── raw/textbook/                    # ngoài git
│   └── processed/textbook/              # ngoài git
└── tests/
    ├── fixtures/textbook/               # MỚI: HTML, markdown, manifest mẫu
    └── test_textbook_*.py               # MỚI: một file test mỗi module logic
```

**Structure Decision**: giữ nguyên bố cục `apps/data-pipeline` (crawler trong `crawlers/`, lệnh và logic trong
`pipeline/`, mỗi module một trách nhiệm dưới 200 dòng, tên có tiền tố `textbook_`). `__main__.py` đang 173 dòng nên mọi
parser và handler mới nằm trong `textbook_cli.py`, `__main__.py` chỉ gọi một hàm đăng ký.

## Phân vai (R12)

| Việc | Ai làm | Model subagent |
|---|---|---|
| Implement từng phase code, viết + chạy test | Worker | `sonnet` |
| Kiểm giấy phép + robots từng nguồn (hướng dẫn A) | Worker, mỗi nguồn một worker | `sonnet` |
| Lập danh sách trang + truy vấn tình huống cho một track (hướng dẫn B) | Worker | `sonnet` |
| Soát đoạn theo lô (hướng dẫn C) | Worker, mỗi lô một worker | `sonnet` |
| Review code trước PR (`code-reviewer`) | Reviewer | `opus` |
| Duyệt manifest; duyệt `drop` / `trim` và điền `approved_by`; đọc mẫu 50 đoạn; quyết nạp tiếp sau lô thử | DE | — |
| Bật `RAG_TEXTBOOK_ENABLED`, khởi động lại ai-service, đo trước / sau | AIE | — |

## Thứ tự PR

1. **PR-A** `feat/data-pipeline/textbook-pipeline`: toàn bộ code + test + contract docs; không cần mạng hay DB để
   review. Đoạn mồi (`review-canaries.json`) đi cùng PR này.
2. **PR-B** `feat/data-pipeline/textbook-java-backend`: manifest các nguồn của lô thử, `scenario-queries.yaml` cho 4
   tình huống Java, decisions đã duyệt, bảng độ phủ dán trong mô tả PR. `index-textbook` chạy từ `main` sau khi merge.
3. **PR-C…** mỗi track còn lại một PR dữ liệu như PR-B, sau khi DE ghi quyết định của lô thử (FR-024).

## Complexity Tracking

Không có vi phạm constitution cần giải trình.
