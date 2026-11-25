# Implementation Plan: Kênh voice cho phỏng vấn luyện tập

**Branch**: spec + plan trên `docs/voice-mode-spec`; code trên `feat/voice-service/voice-mode` | **Date**: 2026-11-25 |
**Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/015-voice-mode/spec.md`

## Summary

Service mới `apps/voice-service` (FastAPI, stateless, nội bộ) giữ key Blaze phía server:

- `POST /api/voice/transcribe`: VAD → (có tiếng) STT với danh sách thuật ngữ → bản ghi gốc + đoạn có tiếng + chỉ số trình
  bày của lượt (tính bằng code). Bắt buộc cờ đồng ý. Không trả `stt_confidence`.
- `POST /api/voice/speak`: proxy stream mp3 từ TTS Blaze.
- `POST /api/voice/session-summary`: gộp chỉ số các lượt + nhận xét theo mẫu, không lưu.
- Bộ đo `apps/voice-service/evals/`: lỗi nhận dạng, thuật ngữ, độ trễ, credit, xuất mẫu STT cho công cụ Evaluator của AIE.

Quyết định: [research.md](research.md). Contract: [contracts/voice-service-api.md](contracts/voice-service-api.md).

## Technical Context

**Language/Version**: Python 3.12 (image), 3.11 (CI), như ai-service

**Primary Dependencies**: `fastapi`, `uvicorn[standard]`, `pydantic`, `python-multipart`, `httpx`, `python-dotenv`,
`prometheus-client` (pin cùng version ai-service). Dev: `pytest`.

**Storage**: không (stateless; ghi âm bộ đo trong thư mục gitignore)

**Testing**: pytest, client Blaze giả bằng `httpx.MockTransport`, `fastapi.testclient`; không mạng, không key

**Target Platform**: Linux container (Docker Compose local + VM staging của 014)

**Project Type**: web-service nội bộ + script đo

**Performance Goals**: SC-001 (bản ghi + chỉ số ≤ 5 s p95 cho câu ≤ 90 s), SC-003 (byte âm thanh đầu ≤ 1.5 s p95)

**Constraints**: không lưu / log audio, bản ghi, văn bản câu hỏi; file code < 200 dòng; gói Starter của Blaze 1 luồng
cùng lúc (gọi tuần tự); ~12 ngày tới 07/12

**Scale/Scope**: demo + bộ đo ~30 clip; vài phiên đồng thời

## Constitution Check

| Nguyên tắc | Đánh giá |
|---|---|
| I. Service tự chủ, DB-per-service | Đạt: không DB, không đọc / ghi DB service khác |
| II. Gateway duy nhất | Đạt: service nội bộ, không route public ở feature này; khi FSD cần public thì khai báo APISIX ở feature của FSD |
| III. Contract-first | Đạt: contract trong `contracts/`, link từ `docs/architecture/ai-integration.md` cùng PR code; FastAPI tự sinh OpenAPI (Swagger) |
| IV. AI stateless, dữ liệu phỏng vấn thuộc interview-service | Đạt: voice-service không lưu; `stt_raw_text` lưu ở interview-service (FSD); ai-service không đổi |
| V. Pipeline tái lập | Không áp dụng (không ghi ai_db); bộ đo chạy lại được theo manifest |
| VI. Quality gates | Đạt khi thêm `voice-service` vào matrix job `python` của CI, test không mạng |
| VII. Đơn giản, phạm vi | **Thêm service**: có task S4-DE-5 cần, lý do ở Complexity Tracking + ADR-011. **Lệch có chủ ý**: Stretch S4-DE-5 làm trước Bắt buộc S4-DE-3 (deploy staging, 014 còn chờ `/speckit-tasks`, làm được); S4-DE-1 xong qua 012, S4-DE-2 chờ FSD. Owner chọn voice trước ngày 2026-11-25 và chấp nhận rủi ro cho 014; voice-service theo đường "thêm service" của 014 nên không làm 014 nặng thêm |

Kiểm lại sau Phase 1: không đổi.

## Project Structure

### Documentation (this feature)

```text
specs/015-voice-mode/
├── spec.md, plan.md, research.md, data-model.md, quickstart.md
├── contracts/voice-service-api.md
├── checklists/requirements.md
├── eval-results.md        # bộ đo ghi (US4)
└── tasks.md               # /speckit-tasks
```

### Source Code

```text
apps/voice-service/
├── Dockerfile, requirements.txt, requirements-dev.txt, README.md
├── app/
│   ├── main.py                    # FastAPI app, router, health, metrics, error handler
│   ├── config.py                  # đọc env (data-model.md §Cấu hình)
│   ├── api_error.py               # ApiError {error, message, details}
│   ├── security.py                # X-Internal-Token (theo mẫu ai-service)
│   ├── models.py                  # Pydantic: SpeechSegment, TurnDeliveryMetrics, TranscriptionResult, Summary
│   ├── blaze_client.py            # httpx: vad(), transcribe(), speak_stream(); retry + map lỗi
│   ├── audio_validation.py        # đuôi / content-type / kích thước
│   ├── transcript_tokens.py       # chuẩn hóa, tách token, đếm âm tiết, khớp từ đệm
│   ├── delivery_metrics.py        # TurnDeliveryMetrics từ (bản ghi, segments, mốc, giới hạn, config)
│   ├── session_summary.py         # gộp + nhận xét theo mẫu
│   ├── transcribe_route.py        # POST /api/voice/transcribe
│   ├── speak_route.py             # POST /api/voice/speak
│   └── summary_route.py           # POST /api/voice/session-summary
├── evals/
│   ├── manifest.jsonl             # commit; audio/ và out/ gitignore
│   ├── wer.py                     # Levenshtein theo token, tỷ lệ thuật ngữ
│   ├── run_voice_eval.py          # gọi service, đo, xuất markdown + stt_samples.jsonl
│   └── pricing.json               # đơn giá credit (bảng giá 2026-11-25)
└── tests/                         # test_* cho từng module, client Blaze giả
```

Sửa thêm: `docker-compose.yml` (khối `voice-service`), `.env.example`, `.github/workflows/ci.yml` (matrix),
`.gitignore` (audio, out), `docs/architecture/adr/adr-011-voice-service-cho-tuy-chon-a.md`,
`docs/architecture/ai-integration.md` (link contract), `docs/architecture/services.md` (thêm dòng service),
`specs/README.md`.

**Structure Decision**: một service Python theo khuôn ai-service (thư mục `app/`, `tests/`, `evals/`), tên module
snake_case theo quy ước Python của repo.

## Phân PR

1. **PR-0 docs**: spec + plan + research + contracts + tasks (nhánh `docs/voice-mode-spec`).
2. **PR-1 voice-service**: spike ghi kết quả vào research → code + test + compose + CI + ADR + docs kiến trúc.
3. **PR-2 bộ đo**: evals + manifest + `eval-results.md` (sau khi có ghi âm).

## Rủi ro

| Rủi ro | Ảnh hưởng | Giảm thiểu |
|---|---|---|
| Blaze không nhận webm/opus | US1 với ghi âm từ trình duyệt | spike T001; thêm ffmpeg đổi sang wav |
| Blaze lọc từ đệm | 1 chỉ số rỗng | `VOICE_FILLERS_SUPPORTED=false`, spec đã cho phép |
| Hết credit gói Starter | dừng đo / demo | đo credit ở spike, báo owner nạp; bộ đo có `--limit` |
| 2 lần gọi tuần tự làm chậm | SC-001 | đo ở spike; nếu gói cho phép thì gọi song song |
| AIE chưa thêm tùy chọn file cho `run_evaluator --stt` | thiếu số SC-004 | nhắn sớm; phần đo khác không phụ thuộc |
| Key LLM ai-service hết hạn | thiếu số SC-004 | owner thay key trước PR-2 |

## Complexity Tracking

| Vi phạm | Vì sao cần | Phương án đơn giản hơn bị loại vì |
|---|---|---|
| Thêm service thứ 7 (`voice-service`) | Key Blaze phải ở server; giữ A8 "ai-service không biết có voice"; ranh giới sở hữu DE | Module trong ai-service: cần AIE đồng ý, đổi A8; web gọi thẳng Blaze: lộ key |
