# Quickstart: 015 voice-mode

Kiểm chứng feature chạy đầu-cuối không cần giao diện. Contract: [contracts/voice-service-api.md](contracts/voice-service-api.md).

## 0. Chuẩn bị

- Python 3.11+, Docker (tùy chọn).
- Trong `.env` ở gốc repo (tự thêm, không commit, không dán key vào chat): `BLAZE_API_KEY=...`, tùy chọn
  `VOICE_SERVICE_INTERNAL_TOKEN=...`.
- Một file ghi âm ngắn trả lời câu hỏi kỹ thuật, ví dụ `sample.webm` (ghi bằng điện thoại hay trình duyệt đều được).

## 1. Test không mạng (CI làm y hệt)

```bash
cd apps/voice-service
pip install -r requirements-dev.txt
python -m pytest -q
```

Kỳ vọng: tất cả test đạt, không cần key, không gọi mạng.

## 2. Chạy service

```bash
cd apps/voice-service
uvicorn app.main:app --port 8020          # hoặc: docker compose up -d voice-service
curl -s localhost:8020/api/health         # {"status":"ok","provider":"blaze"}
```

## 3. Nói thành chữ

```bash
curl -s -X POST localhost:8020/api/voice/transcribe \
  -H "X-Internal-Token: $VOICE_SERVICE_INTERNAL_TOKEN" \
  -F audio=@sample.webm -F consent_confirmed=true \
  -F keywords=HashMap -F keywords=ConcurrentHashMap \
  -F question_audio_ended_at=1764079200000 -F recording_started_at=1764079204000
```

Kỳ vọng: `transcript` tiếng Việt có thuật ngữ, `segments`, `metrics.thinking_time_s` ≈ 4 + giây bắt đầu nói. Gửi lại
không có `consent_confirmed` → `400 consent_required`. Gửi file im lặng → `no_speech: true`.

## 4. Chữ thành tiếng

```bash
curl -s -X POST localhost:8020/api/voice/speak -H "Content-Type: application/json" \
  -H "X-Internal-Token: $VOICE_SERVICE_INTERNAL_TOKEN" \
  -d '{"text":"HashMap và ConcurrentHashMap khác nhau thế nào?"}' -o question.mp3
```

Kỳ vọng: `question.mp3` nghe được câu hỏi.

## 5. Tổng hợp phiên

Gửi mảng `metrics` của vài lượt ở bước 3 tới `POST /api/voice/session-summary`; kỳ vọng `stats`, `counts`, `notes`
khớp tay.

## 6. Bộ đo

```bash
cd apps/voice-service
python -m evals.run_voice_eval --base-url http://localhost:8020 --out ../../specs/015-voice-mode/eval-results.md
```

Cần ghi âm trong `evals/audio/` theo `evals/manifest.jsonl`. Phần so điểm Evaluator: xem hướng dẫn trong
`eval-results.md` (chạy công cụ của AIE với file `evals/out/stt_samples.jsonl`, cần key LLM hợp lệ).

## 7. Riêng tư

Sau bước 3–4: `git status` không có file audio mới ngoài `evals/audio/` (gitignore); log của service không chứa nội dung
bản ghi hay văn bản câu hỏi.
