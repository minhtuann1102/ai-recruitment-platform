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
- **Không có `gh`, `glab`, `brew`**: mở PR bằng link `pull/new/<nhánh>`. Cài `gh` và `gh auth login` thì tự động hóa được.

## Biến môi trường ai-service (`apps/ai-service/.env`, không commit)
`LLM_API_KEY`, `LLM_BASE_URL` (mặc định OpenRouter), `LLM_MODEL`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`, `LLM_TIMEOUT_SECONDS`, `MOCK_STREAM_DELAY_MS`. Khóa do owner giữ; **không đọc, không in, không commit**.

## Cổng
Gateway 9080, ai-service 8000, Postgres host 5534, Redis host 6374. Container prefix `ai_recruit_*`.
