# Tasks: Kênh voice cho phỏng vấn luyện tập (015)

**Input**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md),
[contracts/voice-service-api.md](contracts/voice-service-api.md), [quickstart.md](quickstart.md)

**Tests**: bắt buộc (constitution VI, SC-006): test không mạng, không key, client Blaze giả bằng `httpx.MockTransport`.
Thư mục gốc code: `apps/voice-service/`. File code < 200 dòng.

## Phase 1: Setup và spike Blaze

- [x] T001 Spike (cần owner đặt `BLAZE_API_KEY` vào `apps/voice-service/.env`; không đọc file, script nạp bằng
  `python-dotenv`; máy này cần `truststore.inject_into_ssl()` trước khi tạo client httpx):
  script tạm trong scratchpad gọi `POST /v1/audio/voice_activity`, `POST /v1/audio/transcriptions`
  (`timestamps=true`, `refine=false`, `keywords`) với 1 file webm và 1 file wav có từ đệm và thuật ngữ, ghi: định dạng
  được nhận, trường response thật (có mốc theo từ / độ tin cậy không), từ đệm có giữ không, độ trễ, giới hạn `keywords`,
  lỗi khi gọi song song (gói Starter 1 luồng)
- [x] T002 Spike TTS: `POST /v1/audio/speech` với `blaze-tts-1.5-realtime`, giọng `HN-Nam-2-BL`, mp3; ghi tên tham số
  đúng, thời gian tới byte đầu, danh sách giọng (`GET /v1/audio/voices`), credit tiêu thụ sau T001–T002 (trên trang
  tài khoản)
- [x] T003 Ghi kết quả T001–T002 vào mục "Kết quả spike" cuối `specs/015-voice-mode/research.md`; chỉnh mặc định trong
  data-model.md (`VOICE_FILLERS_SUPPORTED`, `VOICE_MAX_KEYWORDS`, gọi song song hay tuần tự, cần ffmpeg không)
- [x] T004 Tạo `apps/voice-service/` với `requirements.txt` (fastapi 0.115.6, uvicorn[standard] 0.34.0, pydantic 2.10.4,
  python-multipart 0.0.20, httpx 0.28.1, python-dotenv 1.2.1, prometheus-client 0.25.0), `requirements-dev.txt`
  (`-r requirements.txt`, pytest 8.3.4), `Dockerfile` (theo `apps/ai-service/Dockerfile`, port 8020; thêm ffmpeg chỉ
  nếu T003 kết luận cần), `app/__init__.py`, `tests/__init__.py`, `tests/conftest.py`
- [x] T005 [P] Thêm `.gitignore` gốc: `apps/voice-service/evals/audio/`, `apps/voice-service/evals/out/`

## Phase 2: Foundational

- [x] T006 `apps/voice-service/app/config.py`: `load_dotenv(APP_DIR / ".env")` rồi dataclass đọc env theo bảng "Cấu hình" của data-model.md (mặc định đúng
  bảng), kiểm khoảng hợp lệ (số > 0), `VOICE_TTS_VOICES` tách dấu phẩy, phần tử đầu là mặc định
- [x] T007 [P] `app/api_error.py` (`ApiError(status_code, error, message, details)` như ai-service) và handler trả
  `{error, message, details}`
- [x] T008 [P] `app/security.py`: middleware `X-Internal-Token` theo mẫu `apps/ai-service/app/security.py` (biến
  `VOICE_SERVICE_INTERNAL_TOKEN`, `OPEN_PATHS = {"/api/health", "/metrics"}`, staging/production thiếu token → 503
  `misconfigured`, so sánh hằng thời gian)
- [x] T009 `app/models.py`: Pydantic `SpeechSegment` (`start ≥ 0`, `end > start`), `TurnDeliveryMetrics` (mọi trường
  nullable, `filler_ratio` trong [0,1]), `TranscriptionResult`, `SpeakRequest` (`text` 1–1000 ký tự), `SummaryRequest`,
  `SessionDeliverySummary` theo data-model.md
- [x] T010 `app/blaze_client.py`: `BlazeClient(httpx.AsyncClient)` với `voice_activity(audio, filename, content_type)`,
  `transcribe(audio, ..., keywords, language)`, `speak_stream(text, voice)` (async iterator bytes); header
  `Authorization: Bearer`; retry `VOICE_PROVIDER_RETRIES` cho lỗi mạng / 5xx / 429 với backoff 0.5·2^n; map lỗi theo
  research R8 (402 hoặc 429 có code hết credit → `quota_exceeded`, 429 khác → `provider_rate_limited`, timeout / STT
  202 → `provider_timeout`, 5xx → `provider_error`, 400/415 về file → `invalid_audio`); không log nội dung
- [x] T011 `app/main.py`: tạo app, middleware token, handler lỗi, `GET /api/health` (`provider: blaze | unconfigured`),
  `GET /metrics` (Prometheus: `voice_requests_total{endpoint,status,error}`, `voice_provider_seconds{call}`,
  `voice_audio_seconds_total`), lifespan tạo / đóng `BlazeClient`, include 3 router
- [x] T012 [P] `tests/test_blaze_client.py`: MockTransport — multipart đúng trường, retry 503 rồi thành công, 429 hết
  retry → `provider_rate_limited`, 402 → `quota_exceeded`, 202 → `provider_timeout`, header Bearer có mặt
- [x] T013 [P] `tests/test_security_and_health.py`: thiếu / sai token → 401; health mở; `APP_ENV=staging` thiếu token → 503;
  thiếu `BLAZE_API_KEY` → health `unconfigured`, endpoint khác 503 `provider_unconfigured`

**Checkpoint**: `python -m pytest -q` xanh.

## Phase 3: User Story 1 - Nói thành chữ + chỉ số lượt (P1) 🎯 MVP

**Goal**: `POST /api/voice/transcribe` trả bản ghi, đoạn có tiếng, chỉ số FR-006. **Independent test**: quickstart §3.

- [x] T014 [P] [US1] `app/transcript_tokens.py`: chuẩn hóa (lowercase, bỏ dấu câu, giữ dấu tiếng Việt), `tokens(text)`,
  `count_fillers(tokens, fillers)` khớp cụm dài trước (danh sách research R5), trả số token thuộc từ đệm
- [x] T015 [P] [US1] `app/delivery_metrics.py`: `merge_segments`, `compute_turn_metrics(transcript, segments,
  question_ended_at, recording_started_at, answer_limit_s, topic_id, config) -> (TurnDeliveryMetrics, warnings)` đúng
  bảng FR-006 và research R5: mốc hợp lệ khi đủ hai mốc, `recording_started_at ≥ question_audio_ended_at`, lệch ≤ 10 phút;
  sai → `thinking_time_s=null` + `invalid_client_timestamps`; `filler_ratio=null` + `fillers_unsupported` khi config tắt;
  làm tròn 2/1/3 chữ số
- [x] T016 [P] [US1] `app/audio_validation.py`: đuôi / content-type cho phép (webm, ogg, wav, mp3, m4a), kích thước
  ≤ `VOICE_MAX_UPLOAD_MB` (413 `audio_too_long`), file rỗng / sai loại → 415 `invalid_audio`; `parse_client_time`
  nhận ISO 8601 hoặc epoch ms
- [x] T017 [US1] `app/transcribe_route.py`: đọc form theo contract; `consent_confirmed` khác `true` → 400
  `consent_required` **trước khi** gọi nhà cung cấp; keywords nhận lặp hoặc JSON array, cắt ở `VOICE_MAX_KEYWORDS` +
  `keywords_truncated`; VAD → không đoạn → `no_speech` (không gọi STT); đoạn cuối > `VOICE_MAX_AUDIO_S` → 413; STT
  (tuần tự hoặc song song theo T003) → metrics; ghi thời gian từng lần gọi vào `provider`; không trả `stt_confidence`
- [x] T018 [P] [US1] `tests/test_transcript_tokens.py`: từ đệm đơn và cụm ("kiểu như"), "ạ" cuối câu không tính, thuật
  ngữ tiếng Anh, chuỗi rỗng
- [x] T019 [P] [US1] `tests/test_delivery_metrics.py`: kịch bản 2 của spec US1 (4 s + 1.2 s = 5.2), mốc ngược / thiếu một
  mốc, quãng ngừng đúng ngưỡng 2.0, đoạn chồng nhau, `over_limit` có / không giới hạn, tất định qua 2 lần gọi
- [x] T020 [US1] `tests/test_transcribe_route.py`: MockTransport — luồng đầy đủ, thiếu đồng ý (không có request nào tới
  Blaze), im lặng → `no_speech` không gọi STT, file quá lớn, lỗi Blaze → mã lỗi contract, response không có
  `stt_confidence`, log (caplog) không chứa bản ghi

**Checkpoint**: MVP — quickstart §1–§3 chạy với key thật.

## Phase 4: User Story 2 - Chữ thành tiếng (P2)

**Goal**: `POST /api/voice/speak` stream mp3. **Independent test**: quickstart §4.

- [x] T021 [US2] `app/speak_route.py`: kiểm `text` 1–`VOICE_MAX_TTS_CHARS` (400 `text_too_long`), `voice` trong danh
  sách (400 `invalid_voice`); lỗi trước byte đầu → JSON; sau đó `StreamingResponse(audio/mpeg)` từ `speak_stream`;
  không log văn bản
- [x] T022 [US2] `tests/test_speak_route.py`: MockTransport trả 3 chunk → body ghép đúng, content-type `audio/mpeg`;
  text rỗng / quá dài / giọng lạ không gọi Blaze; Blaze 502 trước stream → JSON `provider_error`

## Phase 5: User Story 3 - Tổng hợp phiên (P2)

**Goal**: `POST /api/voice/session-summary`. **Independent test**: gửi metrics dựng sẵn, không cần audio.

- [x] T023 [P] [US3] `app/session_summary.py`: `summarize(turns, config) -> SessionDeliverySummary`: `stats` (median,
  min, max, n) chỉ cho chỉ số có giá trị; `counts`; 0–4 câu nhận xét tiếng Việt theo mẫu cố định, thứ tự quãng ngừng →
  tốc độ → từ đệm → thời gian suy nghĩ, ngưỡng theo data-model.md; không nhắc điểm kiến thức
- [x] T024 [US3] `app/summary_route.py` + `tests/test_session_summary.py`: kịch bản spec US3 (3/8 lượt), chỉ số rỗng mọi
  lượt không xuất hiện, `turns: []` → `voice_turns: 0`

## Phase 6: User Story 4 - Bộ đo (P3)

**Goal**: số liệu SC-001..SC-004, SC-007. **Independent test**: quickstart §6.

- [x] T025 [P] [US4] `apps/voice-service/evals/wer.py` + `tests/test_wer.py`: Levenshtein theo token (dùng
  `transcript_tokens`), tỷ lệ lỗi âm tiết, tỷ lệ nhận đúng thuật ngữ (thuật ngữ = token của bản chuẩn có trong danh
  sách thuật ngữ của track)
- [x] T026 [US4] `evals/manifest.jsonl` (24 clip `read` theo `evaluator_golden.jsonl`, ≥ 2 người, 4 track + 6 clip
  `free`), `evals/pricing.json` (đơn giá bảng giá 2026-11-25), `evals/README.md` (cách ghi âm, mẫu xác nhận đồng ý của
  người ghi, mã ẩn danh)
- [x] T027 [US4] `evals/run_voice_eval.py`: gọi voice-service theo `--base-url`, chạy STT 2 lần (có / không keywords,
  keywords lấy từ `GET /api/stt/phrases` của ai-service hoặc file cache `evals/phrases/<track>.json`), TTS trên 20 câu
  hỏi golden, p50 / p95, credit ước tính cho phiên 20 phút; xuất markdown `--out` và `evals/out/stt_samples.jsonl`
  (`{id, stt_of, noise: ["real_stt"], answer}`); `--limit` để tiết kiệm credit
- [ ] T028 [US4] Owner + thành viên ghi âm theo manifest (có xác nhận đồng ý); chạy T027; ghi
  `specs/015-voice-mode/eval-results.md` (số file, người ghi ẩn danh, ngày, bảng chỉ số, giới hạn: đọc thành tiếng)
- [ ] T029 [US4] Nhắn AIE xin tùy chọn đường dẫn cho `run_evaluator --stt` (ví dụ `--stt-file`); có rồi thì chạy với
  `evals/out/stt_samples.jsonl` (cần key LLM hợp lệ trong `apps/ai-service/.env`), ghi chênh band từng tiêu chí vào
  eval-results.md (SC-004)

## Phase 7: Polish, tích hợp, tài liệu

- [x] T030 [P] `docker-compose.yml`: khối `voice-service` (build `./apps/voice-service`, container
  `ai_recruit_voice_service`, port `8020:8020`, `env_file: [{path: ./apps/voice-service/.env, required: false}]`, healthcheck `/api/health`, network
  `ai-recruit-network`); `apps/voice-service/.env.example`: `BLAZE_API_KEY=`, `BLAZE_BASE_URL`,
  `VOICE_SERVICE_INTERNAL_TOKEN=`, các `VOICE_*` chính; `.gitignore` đã bỏ qua `**/.env`
- [x] T031 [P] `.github/workflows/ci.yml`: thêm `voice-service` vào `matrix.app` của job `python`
- [x] T032 [P] `docs/architecture/adr/adr-011-voice-service-cho-tuy-chon-a.md` (bối cảnh A8, lý do key phía server,
  phương án bị loại, hệ quả: thêm container, không đổi ai-service)
- [x] T033 [P] `docs/architecture/ai-integration.md` + `docs/architecture/services.md`: thêm voice-service, link contract;
  `apps/voice-service/README.md` (chạy, env, test)
- [ ] T034 Nhắn AIE (FR-003: Blaze không trả độ tin cậy; FR-013: tổng hợp trình bày có thể ghép vào finalize sau) và FSD
  (`stt_raw_text`, `media_consent_at`, mốc client, gọi voice-service) — gửi qua PR description / tin nhắn, lưu bản
  nháp trong PR
- [x] T035 Kiểm mọi file trong `apps/voice-service/` < 200 dòng; `python -m pytest -q` xanh; chạy quickstart §1–§5, §7
  với key thật; review bằng `code-reviewer` (opus) trước khi mở PR-1
  *2026-11-26*: 230 test xanh, mọi file < 200 dòng; quickstart §2–§5, §7 chạy với key thật, đầu vào là clip do TTS
  đọc (chưa có ghi âm người); bộ đo chạy thử `--limit 1` trên service thật ở commit d316ca9 (trước khi sửa theo review,
  phần sửa có test giả lập; kết quả không ghi vào eval-results.md); review: plans/reports/code-reviewer-261126-2112-*
- [x] T036 Cập nhật dòng 015 trong `specs/README.md` và tick task trong file này sau mỗi PR

## Dependencies

- T001–T003 (spike) trước T010, T017, T021 (tên trường / mặc định); T004–T005 song song với spike.
- Phase 2 trước mọi user story. US1 trước US4. US2, US3 độc lập với US1 (US3 chỉ cần `models.py`).
- PR-1 = Phase 1–5 + Phase 7 (trừ T028–T029); PR-2 = Phase 6.

## Parallel

- Phase 2: T007, T008 song song; T012, T013 sau T010–T011.
- US1: T014, T015, T016 song song; T018, T019 song song; US3 (T023) song song với US1.
- Phase 7: T030–T033 song song.

## Implementation Strategy

MVP = Phase 1–3 (nói thành chữ + chỉ số). Sau đó US2, US3 (nhỏ), rồi Phase 7 và mở PR-1. Bộ đo (US4) chạy khi có ghi âm,
PR-2. Hạn 07/12: PR-1 trước 30/11, PR-2 trước 05/12.
