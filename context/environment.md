# Môi trường dev

## Chạy test
- Local (Python 3.9, có sẵn venv): `cd apps/ai-service && .venv/bin/python -m pytest -q`
- Đúng bản CI (Python 3.11) bằng Docker:
  `docker run --rm -v "$PWD":/w -w /w/apps/ai-service python:3.11-slim sh -c "pip install -q -r requirements-dev.txt && python -m pytest -q"`
- Tài liệu: `python apps/ai-service/scripts/check_docs.py` (thoát 1 nếu lệch)
- Test tích hợp pgvector (sau Phase 03): marker `integration`, cần DB bật bằng Docker Compose.

## Docker
Docker Desktop cài ở `/Applications/Docker.app`; nếu shell không thấy `docker`, thêm `/Applications/Docker.app/Contents/Resources/bin` vào `PATH`. Nếu lỗi "cannot connect to the Docker API" thì Docker Desktop đang tắt.

## Git và PR
- Git chưa cấu hình `user.name`; username dùng trong tên nhánh là `thang`.
- Remote: `https://github.com/minhtuann1102/ai-recruitment-platform.git`. Push bằng HTTPS đã chạy được.
- **`gh` 2.102.0** cài ở `~/.local/bin/gh` (tải từ bản phát hành chính thức, đã đối chiếu SHA-256, ngày 2026-10-19). Không có `glab`, `brew`. Owner tự chạy `gh auth login` (HTTPS, trình duyệt); khi `gh auth status` báo đã đăng nhập thì mở PR bằng `gh pr create --base main --head <nhánh>`. Chưa đăng nhập thì dùng link `pull/new/<nhánh>`.

## Biến môi trường ai-service (`apps/ai-service/.env`, không commit)
`LLM_API_KEY`, `LLM_BASE_URL` (mặc định OpenRouter), `LLM_MODEL`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`, `LLM_STRUCTURED_OUTPUTS`, `LOG_LLM_IO`, `LLM_MODEL_<AGENT>`, `AGENT_<AGENT>_MODE`, `MOCK_STREAM_DELAY_MS`. Khóa do owner giữ; **không đọc, không in, không commit**.

## ai_db dùng chung (RAG)
DE dựng trên Supabase (PR #32, 9.006 bản ghi). ai-service đọc bằng role `aie_reader`; URI Session pooler (cổng 5432) owner giữ trong `apps/ai-service/.env` (`AI_DB_URL`), cùng `RAG_ENABLED=true`, `AI_DB_CONNECT_TIMEOUT_S=10`. python-dotenv lấy giá trị **đầu tiên** của biến trùng trong `.env`. Đo recall: `python -m evals.run_rag`.

## Cổng
Gateway 9080, ai-service 8000, Postgres host 5534, Redis host 6374. Container prefix `ai_recruit_*`.
