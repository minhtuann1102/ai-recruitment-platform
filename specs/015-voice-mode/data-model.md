# Data Model: 015 voice-mode

voice-service **không có database** và không lưu gì giữa các request. Các entity dưới đây là model trong bộ nhớ /
trong request-response (Pydantic). Định dạng JSON đầy đủ ở [contracts/voice-service-api.md](contracts/voice-service-api.md).

## SpeechSegment

| Trường | Kiểu | Ràng buộc |
|---|---|---|
| `start` | float (giây) | ≥ 0 |
| `end` | float (giây) | > `start` |

Nguồn: VAD của nhà cung cấp, sắp theo `start`, gộp đoạn chồng nhau trước khi tính chỉ số.

## ClientTimestamps (đầu vào tùy chọn)

`question_audio_ended_at`, `recording_started_at`: thời điểm theo đồng hồ client (ISO 8601 hoặc epoch ms). Hợp lệ khi có
cả hai và `recording_started_at ≥ question_audio_ended_at`; lệch > 10 phút cũng coi là không hợp lệ.

## TurnDeliveryMetrics

| Trường | Kiểu | Rỗng khi |
|---|---|---|
| `topic_id` | string? | bên gọi không gửi |
| `thinking_time_s` | float? | thiếu / sai mốc client |
| `answer_duration_s` | float? | không có tiếng |
| `over_limit` | bool? | không có `answer_limit_s` |
| `speech_time_s` | float? | không có tiếng |
| `speech_rate_spm` | float? | không có tiếng hoặc 0 âm tiết |
| `long_pause_count` | int? | không có tiếng |
| `filler_ratio` | float [0,1]? | `VOICE_FILLERS_SUPPORTED=false` hoặc 0 âm tiết |

Làm tròn 2 chữ số (giây) / 1 chữ số (spm) / 3 chữ số (tỷ lệ). Tính tất định từ (bản ghi gốc, segments, mốc, giới hạn,
cấu hình).

## TranscriptionResult

`no_speech: bool`, `transcript: str`, `segments: SpeechSegment[]`, `metrics: TurnDeliveryMetrics?`,
`warnings: str[]`, `provider: {stt_model, stt_ms, vad_ms}`.

Quy tắc: `no_speech` ⇔ VAD không có đoạn nào; khi đó không gọi STT, `metrics = null`.

## SessionDeliverySummary

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `voice_turns` | int | số phần tử đầu vào |
| `stats` | map tên chỉ số → `{median, min, max, n}` | chỉ chỉ số có ≥ 1 giá trị; gồm `thinking_time_s`, `answer_duration_s`, `speech_rate_spm`, `filler_ratio` |
| `counts` | `{turns_with_long_pause, turns_over_limit, turns_with_limit}` | `turns_with_long_pause` = số lượt có `long_pause_count ≥ 1` |
| `notes` | string[] (0–4) | mẫu cố định, thứ tự: quãng ngừng, tốc độ, từ đệm, thời gian suy nghĩ |

Ngưỡng sinh nhận xét (cấu hình, chốt sau đo): quãng ngừng khi ≥ 1/3 số lượt có quãng ngừng dài; tốc độ khi trung vị
< `VOICE_RATE_SLOW_SPM` (100) hoặc > `VOICE_RATE_FAST_SPM` (200); từ đệm khi trung vị > `VOICE_FILLER_NOTE_RATIO`
(0.05); thời gian suy nghĩ khi trung vị > `VOICE_THINKING_NOTE_S` (10).

## Mẫu đo (evals)

`manifest.jsonl`: `{clip_id, golden_id?, speaker, kind: "read" | "free", track}`. `read` bắt buộc `golden_id` (trỏ
`apps/ai-service/evals/evaluator_golden.jsonl`), bản ghi chuẩn = `answer` của mẫu golden. File audio
`evals/audio/<clip_id>.<ext>` (gitignore).

## Cấu hình (env)

Nạp từ `apps/voice-service/.env` (theo mẫu `apps/data-pipeline/pipeline/settings.py`), biến môi trường thật ghi đè.

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `BLAZE_API_KEY` | — | bắt buộc để gọi nhà cung cấp |
| `BLAZE_BASE_URL` | `https://api.blaze.vn` | |
| `VOICE_SERVICE_INTERNAL_TOKEN` | — | token nội bộ |
| `APP_ENV` | `dev` | staging/production bật fail-closed |
| `VOICE_STT_MODEL` | `blaze-stt-1.5` | |
| `VOICE_TTS_MODEL` | `blaze-tts-1.5-realtime` | |
| `VOICE_TTS_VOICES` | `HN-Nam-2-BL` | danh sách cho phép, phần tử đầu là mặc định |
| `VOICE_MAX_UPLOAD_MB` | 10 | |
| `VOICE_MAX_AUDIO_S` | 300 | |
| `VOICE_MAX_TTS_CHARS` | 1000 | |
| `VOICE_PROVIDER_TIMEOUT_S` | 30 | |
| `VOICE_PROVIDER_RETRIES` | 2 | |
| `VOICE_LONG_PAUSE_S` | 1.5 | |
| `VOICE_FILLERS_SUPPORTED` | true | đặt false nếu spike cho thấy Blaze lọc từ đệm |
| `VOICE_MAX_KEYWORDS` | 100 | chốt sau spike |
