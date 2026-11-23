# Quickstart: kiểm feature 017 (GĐ1)

Contract: [match-jobs-api](contracts/match-jobs-api.md), [pipeline-cli-match](contracts/pipeline-cli-match.md).

## 1. Offline (CI, không khóa, không DB)

```bash
cd apps/ai-service && pytest tests/test_matching_*.py -q
cd apps/data-pipeline && pytest tests/test_jd_match_*.py tests/test_match_eval_*.py tests/test_skill_dictionary_copy_in_sync.py -q
```

Kỳ vọng: test xanh.
- Chế độ mock (`MATCH_MOCK=true`) cho cùng kết quả qua hai lần gọi.
- Test chứng minh truy vấn RAG không trả bản ghi `job_description`.

## 2. Dev không khóa: chế độ mock

```bash
cd apps/ai-service && MATCH_MOCK=true AI_SERVICE_INTERNAL_TOKEN=dev uvicorn app.main:app --port 8000
curl -s -X POST localhost:8000/api/match/jobs -H "X-Internal-Token: dev" -H "Content-Type: application/json" \
  -d @tests/fixtures/matching/cv-java-middle.json
```

Kỳ vọng: 200, `metadata.mock = true`. Mọi item có `group = backend`; `matched_skills` và `missing_skills` khớp với
`components.skill_match`.

## 3. Index thật (DE, cần `.env` của pipeline với quyền ghi ai_db)

```bash
cd apps/data-pipeline
python -m pipeline index-jd-match          # lần 1: embedded ≈ 360
python -m pipeline index-jd-match          # lần 2: embedded = 0, inserted = 0
```

Kỳ vọng: mã thoát 0. Thống kê có `skipped_no_group = 5`. Lần 2 không gọi embedding (SC-005).

## 4. Gợi ý thật (ai-service với `AI_DB_URL` + `LLM_API_KEY`)

Gọi như bước 2 nhưng không bật `MATCH_MOCK`, thêm `"as_of": "2026-11-01"`. Kỳ vọng:
- `metadata.mock = false`, `degraded = false`.
- `timing_ms.score` < 500.
- Không có JD nào có `deadline` < as-of.

## 5. Đánh giá (PR-3)

```bash
cd apps/data-pipeline
python -m pipeline match-eval-sheet --out data/processed/match_eval/   # gán nhãn → data/seeds/match_eval/labels.json
python -m pipeline match-eval --rounds 4
```

Kỳ vọng: file `specs/017-cv-jd-matching/eval-results.md` có:
- P@5 và nDCG@5 của 3 cách tính;
- độ trễ p50 / p95 của phần tính điểm và của toàn bộ request;
- chi phí index và chi phí mỗi request;
- mô tả bộ dữ liệu và hạn chế.

Chạy lại lần 2 cho cùng các chỉ số chất lượng. Phân tích viết tay nằm ở `eval-analysis.md` (lệnh không ghi đè).

## Ghi chú chạy local trên Windows

- Máy có phần mềm chặn TLS (lỗi `CERTIFICATE_VERIFY_FAILED` / `Connection error.`): bọc lệnh để dùng kho chứng chỉ
  Windows, không đổi code: `python -c "import truststore, runpy, sys; truststore.inject_into_ssl(); sys.argv=['pipeline', 'index-jd-match']; runpy.run_module('pipeline', run_name='__main__')"` (cài `truststore` vào venv nếu thiếu).
- ai-service chế độ thật trên Windows: psycopg async cần `asyncio.WindowsSelectorEventLoopPolicy()` trước khi gọi
  `uvicorn.run` (Docker / Linux không cần).
