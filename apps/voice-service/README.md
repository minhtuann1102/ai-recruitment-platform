# voice-service

Service FastAPI **nội bộ**, stateless, giữ khóa Blaze phía server cho kênh voice của phỏng vấn luyện tập (spec 015, [ADR-011](../../docs/architecture/adr/adr-011-voice-service-cho-tuy-chon-a.md)).

- `POST /api/voice/transcribe`: audio → VAD (chặn lượt không có tiếng) → STT → bản ghi gốc + đoạn có tiếng + chỉ số trình bày của lượt.
- `POST /api/voice/speak`: văn bản câu hỏi → stream `audio/mpeg` từ TTS.
- `POST /api/voice/session-summary`: chỉ số các lượt → tổng hợp phiên + nhận xét theo mẫu cố định (không LLM).
- `GET /api/health`, `GET /metrics` (Prometheus).

**Contract (request, response, mã lỗi):** [specs/015-voice-mode/contracts/voice-service-api.md](../../specs/015-voice-mode/contracts/voice-service-api.md). Swagger khi chạy: `http://localhost:8020/docs`.

## Chạy

```bash
cd apps/voice-service
pip install -r requirements-dev.txt
cp .env.example .env          # tự điền BLAZE_API_KEY; không commit, không dán key vào chat
uvicorn app.main:app --port 8020
curl -s localhost:8020/api/health   # {"status":"ok","provider":"blaze"}  (unconfigured nếu thiếu key)
```

Docker Compose (từ thư mục gốc repo): `docker compose up -d --build voice-service` (đọc `apps/voice-service/.env`, thiếu file vẫn lên và báo `unconfigured`).

Máy có kiểm tra TLS chặn giữa (`CERTIFICATE_VERIFY_FAILED`): cài bằng `pip install --use-feature=truststore -r requirements-dev.txt`, cài riêng `pip install truststore` (chỉ cho máy đó, không thêm vào `requirements.txt`) và chạy service qua lệnh dưới đây. Phải bật `truststore.inject_into_ssl()` **trước khi** import `app.main`, vì client httpx tạo ngữ cảnh SSL ngay lúc import:

```bash
python -c "import truststore; truststore.inject_into_ssl(); import uvicorn; uvicorn.run('app.main:app', port=8020)"
```

## Thử nhanh

```bash
curl -s -X POST localhost:8020/api/voice/transcribe -H "X-Internal-Token: $VOICE_SERVICE_INTERNAL_TOKEN" \
  -F audio=@sample.webm -F consent_confirmed=true -F keywords=HashMap -F keywords=ConcurrentHashMap \
  -F question_audio_ended_at=1764079200000 -F recording_started_at=1764079204000
curl -s -X POST localhost:8020/api/voice/speak -H "Content-Type: application/json" \
  -H "X-Internal-Token: $VOICE_SERVICE_INTERNAL_TOKEN" -d '{"text":"HashMap và ConcurrentHashMap khác nhau thế nào?"}' -o question.mp3
```

Không đặt `VOICE_SERVICE_INTERNAL_TOKEN` (máy dev) thì bỏ header; `APP_ENV=staging|production` mà thiếu token thì service trả 503 `misconfigured`.

## Cấu hình (biến môi trường)

Nạp từ `apps/voice-service/.env`, biến môi trường thật ghi đè. Giá trị sai (số ≤ 0, `true/false` sai) làm service không khởi động. Mặc định và ý nghĩa: [data-model.md](../../specs/015-voice-mode/data-model.md) mục "Cấu hình"; mẫu: [.env.example](.env.example).

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `BLAZE_API_KEY` | — | bắt buộc để gọi nhà cung cấp |
| `BLAZE_BASE_URL` | `https://api.blaze.vn` | |
| `VOICE_SERVICE_INTERNAL_TOKEN`, `APP_ENV` | —, `dev` | token nội bộ. **Staging / production bắt buộc đặt `APP_ENV=staging` (hoặc `production`) và token**: để `APP_ENV=dev` mà không có token thì service nhận mọi request không xác thực |
| `VOICE_STT_MODEL`, `VOICE_STT_REFINE` | `blaze-stt-1.5`, `false` | `refine=false` giữ từ đệm |
| `VOICE_TTS_MODEL`, `VOICE_TTS_VOICES` | `blaze-tts-1.5-realtime`, `HN-Nam-2-BL` | danh sách giọng cho phép, phần tử đầu là mặc định |
| `VOICE_MAX_UPLOAD_MB`, `VOICE_MAX_AUDIO_S`, `VOICE_MAX_TTS_CHARS`, `VOICE_MAX_KEYWORDS` | 10, 300, 1000, 100 | giới hạn đầu vào; `VOICE_MAX_AUDIO_S` kiểm trên mốc cuối của tiếng nói, không phải độ dài tệp |
| `VOICE_PROVIDER_TIMEOUT_S`, `VOICE_PROVIDER_RETRIES`, `VOICE_PROVIDER_BACKOFF_S` | 30, 2, 0.5 | `timeout` của STT = giá trị này; thử lại có backoff `0.5 × 2^n` (xem "Thử lại" dưới) |
| `VOICE_LONG_PAUSE_S`, `VOICE_FILLERS_SUPPORTED`, `VOICE_FILLERS` | 1.5, `true`, danh sách R5 | chỉ số trình bày |
| `VOICE_RATE_SLOW_SPM`, `VOICE_RATE_FAST_SPM`, `VOICE_FILLER_NOTE_RATIO`, `VOICE_THINKING_NOTE_S` | 100, 200, 0.05, 10 | ngưỡng sinh nhận xét cuối phiên |

Test `tests/test_config_matches_docs.py` kiểm bảng ở data-model.md, `.env.example` và mặc định trong code khớp nhau.

## Thử lại nhà cung cấp

Chỉ thử lại khi request chưa tới Blaze hoặc Blaze chưa xử lý: lỗi kết nối (`ConnectError`, `ConnectTimeout`), 503, 429 không phải hết credit. **Không** thử lại sau read timeout, lỗi đọc / ghi giữa chừng hay 500 / 502 / 504: Blaze có thể đã nhận audio và tính phí, gửi lại sẽ tính phí lần nữa và kéo dài thời gian chờ. STT chạy quá `timeout` (HTTP 202) trả 504 `provider_timeout`.

## Chỉ số trình bày

Tính bằng code, tất định, trên **bản ghi gốc** (không trên bản ứng viên đã sửa). Mốc thời gian lấy từ `words` của STT (VAD của Blaze thô nên chỉ làm cổng "có tiếng"); STT không trả `words` (ví dụ `blaze-stt-1.0`) thì dùng đoạn VAD với cùng công thức. Xem `app/delivery_metrics.py`.

- độ dài câu trả lời = cuối từ cuối − đầu từ đầu; quãng ngừng dài = khoảng trống giữa hai từ liền nhau ≥ `VOICE_LONG_PAUSE_S`; `segments` trả về là các đoạn liên tục cắt tại quãng ngừng dài;
- thời gian có tiếng = độ dài − tổng quãng ngừng dài; tốc độ nói = số token ÷ thời gian có tiếng × 60 (token tách theo khoảng trắng, mỗi token một âm tiết hoặc một từ), rỗng khi thời gian có tiếng < 3 giây;
- thời gian suy nghĩ = (`recording_started_at` − `question_audio_ended_at`) + đầu từ đầu; mốc là ISO 8601 hoặc epoch **mili giây** (số thuần trước năm 2020 bị coi là sai, tránh nhầm epoch giây). Không gửi cả hai mốc → rỗng; thiếu một / ngược / lệch quá 10 phút / không đọc được → rỗng + cảnh báo `invalid_client_timestamps`.

## Riêng tư và giới hạn đã biết

- Audio chỉ ở bộ nhớ: `/api/voice/transcribe` **bắt buộc có `Content-Length`** (thiếu → 411 `length_required`, quá giới hạn + 64 KB → 413 trước khi đọc body) và ngưỡng cuộn ra đĩa của Starlette được nâng bằng `VOICE_MAX_UPLOAD_MB`, nên không body nào cuộn ra đĩa (có test chặn `SpooledTemporaryFile.rollover` cho cả body lớn lẫn body chunked). Bên gọi là server nên luôn biết độ dài; không dùng chunked.
- Log chỉ có mã request, kích thước, thời lượng, model, thời gian từng lần gọi, mã lỗi; không có bản ghi, văn bản câu hỏi, thuật ngữ hay tên tệp. Có test caplog ở mức DEBUG. Lỗi ngoại lệ chưa bắt thì uvicorn vẫn ghi traceback đầy đủ (Starlette ném lại), nên các đường xử lý chính trả `ApiError` thay vì để lỗi lọt ra.
- Không bao giờ trả `stt_confidence` (Blaze không trả); không có chỉ số về con người.
- `VOICE_MAX_AUDIO_S` không phải giới hạn độ dài tệp: dùng mốc cuối của tiếng nói. Tệp 10 MB webm/opus có thể dài hàng chục phút im lặng sau đoạn nói, và STT tính phí cả tệp. Muốn chặn thật cần đọc container (chưa làm).
- Swagger (`/docs`, `/openapi.json`) cần `X-Internal-Token` khi đã đặt token; `/api/health` và `/metrics` mở. `/metrics` chỉ có số đếm và thời gian theo endpoint / mã lỗi, không có nội dung.
- Quãng ngừng theo từ phụ thuộc mốc thời gian của model STT; đo lại khi đổi model.

## Test

```bash
cd apps/voice-service
python -m pytest -q
```

Không cần mạng hay key: client Blaze được thay bằng `httpx.MockTransport` với response đúng hình dạng thật (spike 2026-11-25). CI chạy lệnh này trong job `python` (ma trận `voice-service`).

Bộ đo (`evals/`): `evals/wer.py` (lỗi âm tiết, nhận đúng thuật ngữ) đã có; script chạy đo và manifest thuộc PR-2 (spec 015 US4).
