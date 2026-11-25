# Contract: voice-service (nội bộ)

Base URL nội bộ: `http://voice-service:8020` (compose), local `http://localhost:8020` (compose chỉ publish cổng ra
`127.0.0.1`). Mọi endpoint trừ `GET /api/health` và `GET /metrics` cần header
`X-Internal-Token: <VOICE_SERVICE_INTERNAL_TOKEN>`, kể cả `/docs` và `/openapi.json` khi đã đặt token (máy dev chưa đặt
token thì không kiểm, có cảnh báo; `APP_ENV` staging/production thiếu token → 503 `misconfigured`; staging bắt buộc đặt
`APP_ENV=staging` và token). Không mở ra internet; bên gọi là interview-service / server của web (FSD) hoặc CLI của DE.

Lỗi: `{ "error": "<mã>", "message": "<tiếng Việt>", "details": { ... } }` (giống ai-service). Dữ liệu vào sai (thiếu
trường, sai kiểu / giá trị, JSON hỏng) là `400 invalid_request` (ai-service dùng 422). Mọi endpoint (trừ health, metrics)
có thể trả `401 unauthorized` và `503 misconfigured`; Swagger (`/docs`) liệt kê các mã lỗi của từng endpoint.

## GET /api/health

`200 {"status": "ok", "provider": "blaze" | "unconfigured"}`. `unconfigured` khi thiếu `BLAZE_API_KEY` (`/api/voice/transcribe`
và `/api/voice/speak` trả 503 `provider_unconfigured`; `/api/voice/session-summary` vẫn chạy).

## GET /metrics

Prometheus, không cần token: `voice_requests_total{endpoint,status,error}` (kể cả 401 và lỗi 500 ngoài dự kiến),
`voice_provider_seconds{call}` (`vad`, `stt`, `tts` = tới byte đầu tiên), `voice_audio_seconds_total`. Nhãn chỉ có
endpoint / kết quả / mã lỗi, không có nội dung.

## POST /api/voice/transcribe

`multipart/form-data`:

| Trường | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `audio` | file | có | webm/ogg/wav/mp3/m4a, ≤ `VOICE_MAX_UPLOAD_MB`. Request **phải có `Content-Length`** (không dùng chunked): thiếu → `411 length_required`, quá giới hạn + 64 KB → `413 audio_too_long`, cả hai trước khi đọc body |
| `consent_confirmed` | `true` | có | bên gọi xác nhận đã có đồng ý micro + xử lý giọng nói (FR-024); khác `true` → 400 `consent_required` |
| `keywords` | string, lặp nhiều lần hoặc JSON array | không | lấy từ `GET /api/stt/phrases?track=` của ai-service. Bỏ rỗng / trùng; mỗi thuật ngữ ≤ 64 ký tự (dài hơn bị bỏ); cắt ở `VOICE_MAX_KEYWORDS`; có bỏ hoặc cắt → cảnh báo `keywords_truncated` |
| `question_audio_ended_at` | ISO 8601 hoặc epoch **mili giây** (đồng hồ client) | không | mốc TTS đọc xong câu hỏi. Số thuần < 1.577.836.800.000 (trước 2020, thường là epoch giây) bị coi là không hợp lệ |
| `recording_started_at` | như trên | không | mốc bấm ghi |
| `answer_limit_s` | number > 0 | không | giới hạn thời gian câu của bên gọi |
| `topic_id` | string ≤ 64 ký tự | không | trả lại nguyên trong `metrics` để gộp theo topic |
| `language` | `vi` \| `en` | không | mặc định `vi` |

`200`:

```json
{
  "no_speech": false,
  "transcript": "dạ HashMap thì không thread-safe ...",
  "segments": [{"start": 0.84, "end": 6.2}, {"start": 8.9, "end": 21.4}],
  "metrics": {
    "topic_id": "java.collections",
    "thinking_time_s": 5.2,
    "answer_duration_s": 20.56,
    "over_limit": null,
    "speech_time_s": 17.86,
    "speech_rate_spm": 142.1,
    "long_pause_count": 1,
    "filler_ratio": 0.031
  },
  "warnings": [],
  "provider": {"stt_model": "blaze-stt-1.5", "stt_ms": 2310, "vad_ms": 640}
}
```

- `segments`: các đoạn nói liên tục, giây tính từ đầu file. Tính từ **mốc theo từ của STT**, cắt tại mỗi quãng ngừng
  ≥ `VOICE_LONG_PAUSE_S` (mặc định 1.5 giây); STT không trả mốc theo từ (ví dụ `blaze-stt-1.0`) thì là các đoạn VAD
  với cùng quy tắc. VAD của Blaze thô nên chỉ làm cổng "có tiếng" trước STT.
- Trường `metrics.*` có thể `null` theo bảng FR-006 của spec. `speech_rate_spm` = âm tiết / phút, `null` khi thời gian có
  tiếng < 3 giây. `provider.stt_ms` là `null` khi không gọi STT (`no_speech`).
- `no_speech: true` → `transcript: ""`, `segments: []`, `metrics: null`. Bên gọi báo ứng viên kiểm tra micro hoặc
  chuyển sang chat; không gửi lượt này cho ai-service.
- `warnings`: mã chuỗi: `invalid_client_timestamps` (gửi một mốc, mốc ngược / lệch quá 10 phút / không đọc được; không
  gửi cả hai mốc thì không cảnh báo), `keywords_truncated`, `fillers_unsupported`, `empty_transcript` (có tiếng theo VAD
  nhưng STT trả bản ghi rỗng).
- Không có `stt_confidence` (research R4). Bên gọi gửi `transcript` (hoặc bản ứng viên đã sửa) làm `answer` của
  `/api/next-turn` với `answer_source: "voice"`, không gửi `stt_confidence`; lưu `transcript` gốc vào `stt_raw_text`
  trên `/answer` của interview-service (FR-019).

Lỗi: `400 consent_required | invalid_request`, `401 unauthorized`, `402 quota_exceeded`, `411 length_required`,
`413 audio_too_long` (kể cả khi mốc cuối của tiếng nói theo VAD > `VOICE_MAX_AUDIO_S`; không gọi STT), `415 invalid_audio`,
`429 provider_rate_limited`, `502 provider_error`, `503 provider_unconfigured | misconfigured`, `504 provider_timeout`.
Thử lại nhà cung cấp chỉ khi request chưa tới Blaze (lỗi kết nối, 503, 429 không hết credit); không thử lại sau read
timeout hay 500 / 502 / 504 để không tính phí hai lần.

## POST /api/voice/speak

JSON:

```json
{"text": "HashMap và ConcurrentHashMap khác nhau thế nào?", "voice": "HN-Nam-2-BL"}
```

- `text`: 1–1.000 ký tự, văn bản hoàn chỉnh (`done.question`), không đọc theo token.
- `voice`: tùy chọn, phải nằm trong `VOICE_TTS_VOICES`; không có thì dùng giọng mặc định.

`200 audio/mpeg` (Blaze trả `audio/mp3`, service luôn trả `audio/mpeg`), `Transfer-Encoding: chunked` (phát được ngay
khi có chunk đầu). Lỗi trước khi stream bắt đầu trả JSON như trên (`400 text_too_long | invalid_voice | invalid_request`,
`401`, `402`, `429`, `502`, `503 provider_unconfigured | misconfigured`, `504`). Lỗi giữa chừng: stream bị đóng, bên gọi
coi như lỗi TTS và hiện chữ.

## POST /api/voice/session-summary

JSON:

```json
{"turns": [ <metrics của từng lượt voice, đúng dạng metrics ở trên> ]}
```

Tối đa 200 lượt; `topic_id` ≤ 64 ký tự; giá trị ngoài miền (âm, `filler_ratio` > 1...) → `400 invalid_request`.

`200`:

```json
{
  "voice_turns": 8,
  "stats": {
    "thinking_time_s": {"median": 4.1, "min": 1.2, "max": 9.8, "n": 6},
    "answer_duration_s": {"median": 38.0, "min": 12.5, "max": 71.0, "n": 8},
    "speech_rate_spm": {"median": 150.3, "min": 121.0, "max": 188.4, "n": 8},
    "filler_ratio": {"median": 0.04, "min": 0.0, "max": 0.09, "n": 8}
  },
  "counts": {"turns_with_long_pause": 3, "turns_over_limit": 0, "turns_with_limit": 0},
  "notes": ["3/8 câu trả lời có quãng ngừng dài trên 1.5 giây. ..."]
}
```

- Chỉ số rỗng ở mọi lượt không có trong `stats` và `notes`. `turns: []` → `voice_turns: 0`, `stats: {}`, `notes: []`
  (bên gọi hiển thị "không có dữ liệu voice"). Lỗi: `400 invalid_request`, `401`, `503 misconfigured`.
- `notes`: 0–4 câu theo mẫu cố định (không LLM), trung tính, không chứa điểm kiến thức.
- Không lưu gì. Ghép vào báo cáo là việc của bên gọi.

## Trường mới phía FSD (đề xuất, ghi cho FSD)

`POST /answer` của interview-service thêm `stt_raw_text?: string` (bản STT gốc khi trả lời bằng giọng nói). Cột lưu và
`media_consent_at` do FSD đặt khi viết migration `interview_db`.
