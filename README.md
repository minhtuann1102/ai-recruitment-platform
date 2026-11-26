# AI Recruitment Platform: AI + Data

Phần AI và dữ liệu của hệ thống tuyển dụng IT có phỏng vấn luyện tập bằng AI Agentic. **Đồ án tốt nghiệp**, nhóm 3 người, 09/2026 → 12/2026.

Backend nền tảng (auth, user, job, interview, notification) và frontend nằm ở repo của FSD:
[hoangtunggg/final_recruitment_project](https://github.com/hoangtunggg/final_recruitment_project). Repo này chỉ chứa các service
Python mà backend đó gọi tới, cùng pipeline dữ liệu nạp kho RAG cho chúng.

## Thành phần

| Thư mục | Vai trò | Owner |
|---|---|---|
| [apps/ai-service/](apps/ai-service/) | FastAPI: phỏng vấn AI nhiều agent (Interviewer, Evaluator, Planner, Reporter), RAG, chấm CV–JD | AIE |
| [apps/voice-service/](apps/voice-service/) | FastAPI nội bộ: STT / TTS qua Blaze, chỉ số trình bày (spec 015) | DE |
| [apps/data-pipeline/](apps/data-pipeline/) | Crawl, chuẩn hóa, embed Q&A / giáo trình / JD vào `ai_db` (spec 005, 009, 012) | DE |

Kho RAG `ai_db` (Postgres + pgvector, bảng `knowledge_chunks`) dùng chung trên Supabase. Postgres trong compose chỉ là bản local để dev data-pipeline.

```
Backend FSD (repo khác) ──REST──► ai-service ──► voice-service
                                      │
                                      ▼
                            ai_db (Supabase, pgvector) ◄── data-pipeline
```

## Chạy local

Yêu cầu: Python 3.11, Docker Compose.

```bash
cp .env.example .env                       # Postgres local
cp apps/voice-service/.env.example apps/voice-service/.env   # BLAZE_API_KEY
docker compose up -d --build               # db (ai_db local) + ai-service :8000 (mock) + voice-service :8020
```

ai-service trong compose chạy cấu hình mặc định (mock, không đọc `.env`). Chạy với LLM / RAG thật: xem
[docs/ai-service/README.md](docs/ai-service/README.md) và [context/environment.md](context/environment.md). voice-service:
[apps/voice-service/README.md](apps/voice-service/README.md). data-pipeline: `apps/data-pipeline/.env.example`.

```bash
cd apps/<app> && pip install -r requirements-dev.txt && python -m pytest -q
```

| Lệnh | Mô tả |
|---|---|
| `make up` / `make down` | Bật / tắt compose |
| `make db` | Shell vào container Postgres |
| `make db-ensure` | Chạy lại `scripts/init-databases.sh` trên volume cũ |

## CI

`.github/workflows/ci.yml` chạy `pytest` cho `ai-service`, `data-pipeline`, `voice-service` ở mọi PR và push lên `main`.

## Tài liệu

- [docs/ai-service/](docs/ai-service/): thiết kế ai-service (agent, orchestrator, API contract, đánh giá)
- [docs/architecture/](docs/architecture/): kiến trúc toàn hệ thống và ADR (gồm cả phần nay thuộc repo FSD)
- [specs/](specs/): feature theo Spec Kit (xem [specs/README.md](specs/README.md))
- [docs/conventions.md](docs/conventions.md): branch, commit, PR, format lỗi API

## License

MIT
