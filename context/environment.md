# Môi trường dev

## Chạy test
- Local (Python 3.9, có sẵn venv): `cd apps/ai-service && .venv/bin/python -m pytest -q`
- **Venv cục bộ Python 3.9 không cài được `requirements.txt` hiện tại** (`langfuse==5.0.4`, `psycopg-pool==3.3.3`, ghi nhận 2026-10-31): `import app` lỗi nếu chưa xử lý.
- Không có Docker thì dựng Python 3.11 bằng `uv venv --python 3.11` rồi `uv pip install -r requirements-dev.txt`.
- Đúng bản CI (Python 3.11) bằng Docker:
  `docker run --rm -v "$PWD":/w -w /w/apps/ai-service python:3.11-slim sh -c "pip install -q -r requirements-dev.txt && python -m pytest -q"`
- Tài liệu: `python apps/ai-service/scripts/check_docs.py` (thoát 1 nếu lệch)
- Test tích hợp pgvector (sau Phase 03): marker `integration`, cần DB bật bằng Docker Compose.

## Chạy thử một buổi phỏng vấn thật (bạn là ứng viên)
Không cần interview-service hay giao diện: `evals/play.py` gọi ai-service như interview-service sẽ gọi.
- In-process: `cd apps/ai-service && AGENT_EVALUATOR_MODE=llm AGENT_INTERVIEWER_MODE=llm AGENT_PLANNER_MODE=llm AGENT_REPORTER_MODE=llm .venv/bin/python -m evals.play --track java_backend --level junior`
- Qua server: chạy `.venv/bin/python -m uvicorn app.main:app --port 8000` (cùng các biến `AGENT_*_MODE=llm`, `RAG_ENABLED=true`) rồi `.venv/bin/python -m evals.play --base-url http://localhost:8000`. Swagger: `http://localhost:8000/docs` (khi chưa đặt token nội bộ).
- Enter 2 lần để gửi câu trả lời, `/end` để kết thúc; báo cáo hiện sau khi kết thúc, phiên lưu ở `plans/reports/play-*.json` (git bỏ qua). Thời gian trong phiên là giả lập.
- Giao diện web: chạy server như trên (thêm `AGENT_CV_PARSER_MODE=llm AGENT_JD_PARSER_MODE=llm` nếu muốn thử CV/JD) rồi mở `http://localhost:8000/dev/play`. Trang giữ plan/state/turns như interview-service, cho tải CV, dán JD, chọn đồng hồ thật hoặc giả lập, bật xem điểm từng lượt (debug), tải phiên JSON. Bảng "Luồng hệ thống" bên phải ghi từng request: các bước, mốc event meta/token đầu/done, độ trễ và token từng agent, quyết định policy, fallback, plan kèm số đoạn RAG. Trang tự trả 404 khi `APP_ENV` là staging/production; API vẫn cần `X-Internal-Token` nếu máy có đặt (nhập trên trang).

## Đo chất lượng câu hỏi (Phase A)
`cd apps/ai-service`, rồi: `python -m evals.sim_style <file phiên>` (văn phong), `python -m evals.question_set export --out <csv>` (phiếu người chấm), `python -m evals.judge_interviewer` (LLM-judge, cần `LLM_API_KEY`). Chi tiết: `context/quality-criteria.md`.

## Đo TTFT
Chạy in-process thì `ttft_s` bằng tổng thời gian lượt (ASGI đệm body). Đo TTFT phải dùng `python -m evals.simulate --serve` hoặc `--base-url`.

## Hook của repo
Repo có hook Node trong `.claude/hooks/` (chỉ chạy khi máy có Node; Node v24 cài ở `~/.local/node` từ 2026-10-24). `scout-block` chặn đường dẫn trong `.claude/config/adf-ignore.txt`; đã thêm `!.venv` để chạy được Python của ai-service.

## Docker
Docker Desktop cài ở `/Applications/Docker.app`; nếu shell không thấy `docker`, thêm `/Applications/Docker.app/Contents/Resources/bin` vào `PATH`. Nếu lỗi "cannot connect to the Docker API" thì Docker Desktop đang tắt.

## Git và PR
- Git chưa cấu hình `user.name`; username dùng trong tên nhánh là `thang`.
- Remote: `https://github.com/minhtuann1102/ai-recruitment-platform.git`. Push bằng HTTPS đã chạy được.
- **`gh` 2.102.0** cài ở `~/.local/bin/gh` (tải từ bản phát hành chính thức, đã đối chiếu SHA-256, ngày 2026-10-19). Không có `glab`, `brew`. Owner tự chạy `gh auth login` (HTTPS, trình duyệt); khi `gh auth status` báo đã đăng nhập thì mở PR bằng `gh pr create --base main --head <nhánh>`. Chưa đăng nhập thì dùng link `pull/new/<nhánh>`.

## Biến môi trường ai-service (`apps/ai-service/.env`, không commit)
`LLM_API_KEY`, `LLM_BASE_URL` (mặc định OpenRouter), `LLM_MODEL`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`, `LLM_STRUCTURED_OUTPUTS`, `LOG_LLM_IO`, `LOG_LEVEL`, `LOG_FORMAT`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL`, `LANGFUSE_TRACING_ENABLED`, `LLM_MODEL_<AGENT>`, `AGENT_<AGENT>_MODE`, `MOCK_STREAM_DELAY_MS`. Khóa do owner giữ; **không đọc, không in, không commit**.

## ai_db dùng chung (RAG)
DE dựng trên Supabase (PR #32, 9.006 bản ghi). ai-service đọc bằng role `aie_reader`; URI Session pooler (cổng 5432) owner giữ trong `apps/ai-service/.env` (`AI_DB_URL`), cùng `AI_DB_CONNECT_TIMEOUT_S=10`; `RAG_ENABLED` mặc định bật (PR #52). Cờ khác xem `apps/ai-service/.env.example`: `RAG_HYBRID`, `RAG_TURN_RETRIEVAL`, `RAG_COOLDOWN_S`. python-dotenv lấy giá trị **đầu tiên** của biến trùng trong `.env`. Đo recall: `python -m evals.run_rag`.

## Cổng
Gateway 9080, ai-service 8000, Postgres host 5534, Redis host 6374. Container prefix `ai_recruit_*`.
