# Implementation Plan: Gợi ý việc làm theo độ tương đồng CV–JD (GĐ1)

**Branch**: spec + plan trên `docs/cv-jd-matching-spec`; code trên `feat/data-pipeline/jd-match-index`,
`feat/ai-service/cv-jd-matching`, `feat/data-pipeline/jd-match-eval` | **Date**: 2026-11-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/017-cv-jd-matching/spec.md`

## Summary

Kết quả GĐ1:
- **Index JD**: lệnh pipeline `index-jd-match` embed văn bản tóm tắt của 365 JD đã chuẩn hóa ở 009 (không gồm danh
  sách kỹ năng), ghi vào `knowledge_chunks` (`source_type = 'job_description'`, dataset `jd-match`) qua đường ghi có
  sẵn của 005 / 012.
- **Gợi ý**: module mới `app/matching/` trong ai-service. Module giữ snapshot vector JD trong bộ nhớ, nhận
  `cv_profile` + track + level, lọc cứng, rồi tính điểm = 0,6·cosine + 0,3·skill_match + 0,1·level_fit. Trả về
  `POST /api/match/jobs` (nội bộ): top-K có phân trang, kèm từng thành phần điểm, `matched_skills`, `missing_skills`.
- **Mock**: chỉ chạy trong ai-service, dùng embedding băm trên chỉ mục mẫu. Không bao giờ ghi vào ai_db.
- **Đánh giá**: 24 CV tổng hợp, 36 JD thật, nhãn 0/1/2. Lệnh `match-eval` tính P@5 / nDCG@5 cho 3 cách tính, độ trễ,
  chi phí, rồi xuất bảng markdown.
- **GĐ2**: chỉ có contract nháp giao FSD.

Quyết định thiết kế: [research.md](research.md).

## Technical Context

**Language/Version**: Python 3.11 (data-pipeline), Python 3.12 (image ai-service), như hiện có

**Primary Dependencies**:
- Đã có: `fastapi`, `pydantic`, `psycopg[binary]`, `openai`, `pyyaml` (ai-service); `psycopg`, `openai`, `httpx`
  (pipeline).
- Khai báo thêm `numpy` vào `apps/ai-service/requirements.txt`. Thư viện này đã được cài sẵn vì `pgvector` phụ thuộc
  vào nó (2.4.6), nên không có thư viện nặng mới.

**Storage**: `ai_db.knowledge_chunks` (Supabase dùng chung), không đổi DDL. Bộ đánh giá nằm ở
`apps/data-pipeline/data/seeds/match_eval/` ([data-model.md](data-model.md))

**Testing**: `pytest` chạy offline (không mạng, không DB, không khóa); dùng kết nối DB giả và embedder giả. ai-service
test bằng FastAPI `TestClient` ở chế độ mock.

**Target Platform**: ai-service trong container (local / VM staging của 014); lệnh pipeline chạy trên máy DE

**Project Type**: web service (endpoint nội bộ) + CLI trong monorepo

**Performance Goals**: phần tính điểm p95 ≤ 500 ms trên toàn bộ chỉ mục (dự kiến < 10 ms nhờ numpy). Toàn bộ request
gồm cả embed CV thì được đo và báo, không có ngưỡng.

**Constraints**:
- File code < 200 dòng.
- Code của AIE chỉ bị sửa ở `app/main.py` (2 dòng).
- Không ghi log văn bản CV.
- Vector giả không vào ai_db.
- Chạy `index-jd-match` từ `main` mới nhất.

**Scale/Scope**: khoảng 360 JD trong chỉ mục; bộ đánh giá 24 CV × khoảng 10 JD, tức khoảng 250 nhãn

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Kiểm tra | Kết quả |
|---|---|---|
| I. Database-per-Service | Pipeline chỉ ghi `ai_db.knowledge_chunks` qua writer có sẵn; ai-service chỉ đọc ai_db của chính nó; không đổi DDL | Đạt |
| II. Gateway & Transport | GĐ1 chỉ có endpoint nội bộ (REST, `X-Internal-Token`), không có route public; GĐ2 khai báo route APISIX sau | Đạt |
| III. Contract-First | Contract ở `contracts/`; PR-2 cập nhật `docs/ai-service/06`, `docs/architecture/ai-integration.md` (sơ đồ Mermaid luồng gợi ý), `data-model.md` §5, `rag-design.md` | Đạt (T027) |
| IV. AI Stateless | ai-service không lưu CV hay vector CV; snapshot JD chỉ là cache đọc; cùng model embedding 1536 chiều | Đạt |
| V. Pipeline tái lập được | Idempotent theo hash, kèm kiểm model (R3); in thống kê; `source_type` + metadata lọc; dữ liệu crawl không vào git (pool chỉ chứa mã JD) | Đạt |
| VI. Quality Gates | pytest cho mọi logic; không secret; env mới có trong `.env.example` của ai-service và pipeline (Python, không vào `turbo.json`) | Đạt |
| VII. Đơn giản | Không thêm service hay bảng; mỗi 5 phút chỉ một kết nối ngắn; là task Stretch (S2-DE-3) | Đạt, làm sau khi các task Bắt buộc của DE ở S4 ổn |
| Quy trình | Spec Kit cho feature của DE; plan link `docs/architecture/*`; branch theo conventions | Đạt |

Kiểm lại sau Phase 1: không có vi phạm. Một thay đổi vào code dùng chung của pipeline (`embedding_client` đếm token)
được che bằng test.

## Project Structure

### Documentation (this feature)

```text
specs/017-cv-jd-matching/
├── spec.md, plan.md, research.md, data-model.md, quickstart.md
├── contracts/
│   ├── match-jobs-api.md          # POST /api/match/jobs
│   ├── pipeline-cli-match.md      # index-jd-match, match-eval-sheet, match-eval
│   └── gd2-job-service-draft.md   # nháp giao FSD
├── checklists/requirements.md
├── eval-results.md                # PR-3, bảng cho báo cáo
└── tasks.md                       # /speckit-tasks
```

### Source Code (repository root)

```text
apps/data-pipeline/
├── pipeline/
│   ├── __main__.py                       # SỬA: đăng ký lệnh qua jd_match_cli
│   ├── embedding_client.py               # SỬA: đếm token embedding (usage)
│   ├── jd_match_cli.py                   # MỚI: parser + handler của 3 lệnh
│   ├── jd_match_text.py                  # MỚI: văn bản embed của JD (R4) + bản ghi (data-model §1)
│   ├── jd_match_index_command.py         # MỚI: index-jd-match (trùng hash, kiểm model, --rebuild)
│   ├── match_eval_data.py                # MỚI: nạp + kiểm cvs / pool / labels
│   ├── match_eval_client.py              # MỚI: gọi POST /api/match/jobs
│   ├── match_eval_metrics.py             # MỚI: P@k, nDCG@k, xếp lại theo thành phần, percentile
│   ├── match_eval_sheet_command.py       # MỚI: bảng soát không có điểm
│   ├── match_eval_command.py             # MỚI: chạy đánh giá
│   └── match_eval_report.py              # MỚI: bảng markdown
├── data/seeds/match_eval/                # MỚI, commit: cvs.json, pool.json, labels.json
└── tests/
    ├── test_jd_match_text.py, test_jd_match_index_command.py
    ├── test_match_eval_metrics.py, test_match_eval_data.py, test_match_eval_command.py
    └── test_skill_dictionary_copy_in_sync.py

apps/ai-service/
├── app/
│   ├── main.py                           # SỬA: include_router(matching_router)
│   └── matching/                         # MỚI
│       ├── __init__.py
│       ├── settings.py                   # MATCH_* + AI_DB_URL, kiểm trọng số
│       ├── models.py                     # request / response pydantic
│       ├── levels_tracks.py              # bảng bậc, track → nhóm, số năm → bậc
│       ├── skill_normalizer.py           # tên → slug theo skill_dictionary.yaml
│       ├── skill_dictionary.yaml         # bản sao của data-pipeline (R6)
│       ├── cv_text.py                    # văn bản embed của CV (R4)
│       ├── hash_embedder.py              # embedding giả tất định (mock)
│       ├── mock_jobs.json                # ~12 JD tự soạn cho mock
│       ├── job_index.py                  # snapshot + nạp từ ai_db / mock + làm mới nền
│       ├── scorer.py                     # lọc cứng, thành phần, điểm, xếp, giải thích (hàm thuần)
│       ├── service.py                    # embed CV (degraded), gọi scorer, phân trang, metadata
│       └── router.py                     # POST /api/match/jobs
├── requirements.txt                      # SỬA: numpy
├── .env.example                          # SỬA: MATCH_*
└── tests/
    ├── fixtures/matching/                # CV mẫu
    └── test_matching_{scorer,levels_tracks,skill_normalizer,settings,job_index,service,router,rag_isolation}.py
```

**Structure Decision**: giữ bố cục hiện có. Ở pipeline, các lệnh nằm trong `pipeline/` và đăng ký qua một module
`*_cli.py` riêng như 012, vì `__main__.py` đã 177 dòng. Ở ai-service, mọi thứ nằm trong package `app/matching/` để
AIE review một chỗ và không chạm agent hay RAG. Tên file Python dùng snake_case theo lệ của repo.

## Thứ tự PR

0. **PR-0** `docs/cv-jd-matching-spec`: spec, plan, tasks, `specs/README.md` (dòng 017), `docs/sprint-plan.md`
   (S2-DE-3 ghi mở rộng 017).
1. **PR-1** `feat/data-pipeline/jd-match-index`: `index-jd-match` + test + đếm token. Không cần AIE. Sau khi merge thì
   chạy index từ `main`.
2. **PR-2** `feat/ai-service/cv-jd-matching`: module `app/matching/` + test + `.env.example` + docs contract / kiến trúc
   + test đồng bộ danh mục. **Cần AIE đồng ý và review.**
3. **PR-3** `feat/data-pipeline/jd-match-eval`: dữ liệu đánh giá, 2 lệnh eval, `eval-results.md`.

## Phân vai

| Việc | Ai làm | Model subagent |
|---|---|---|
| Implement từng task, viết và chạy test | Worker | `sonnet` |
| Soạn 24 CV tổng hợp + chọn pool 36 JD có mẫu âm khó | Worker, DE duyệt | `sonnet` |
| Gán nhãn 0/1/2 | Chờ owner chọn (câu hỏi bên dưới) | — |
| Review code trước mỗi PR (`code-reviewer`) | Reviewer | `opus` |
| Đồng ý dùng `knowledge_chunks` + review PR-2 | AIE | — |

## Complexity Tracking

Không có vi phạm constitution cần giải trình.
