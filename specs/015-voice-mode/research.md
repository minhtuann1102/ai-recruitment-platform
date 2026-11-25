# Research: Kênh voice cho phỏng vấn luyện tập (015)

**Date**: 2026-11-25 · **Spec**: [spec.md](spec.md)

Nguồn thông tin Blaze: trang tài liệu `app.blaze.vn/api/documentation/*` là SPA, nội dung đọc từ bundle JS ngày
2026-11-25 (định nghĩa endpoint, tham số, ví dụ response). Mục nào ghi **[spike]** là chưa xác minh bằng lần gọi thật,
chốt ở task spike (T001–T003 của tasks.md).

## R1. Đặt code ở đâu: service mới `apps/voice-service`

- **Decision**: service FastAPI mới của DE, stateless, nội bộ (token), container `ai_recruit_voice_service`.
- **Rationale**: key Blaze không được ở trình duyệt nên cần proxy phía server kể cả với tùy chọn A. Đặt trong ai-service
  thì phải xin AIE và làm ai-service phình ra; quyết định A8 giữ "ai-service không biết có voice". Ranh giới sở hữu rõ
  (DE), deploy theo quy trình thêm service của 014.
- **Alternatives**: module trong ai-service (cần AIE, đổi A8); chỉ script đo trong data-pipeline (web không có gì để
  gắn); để web gọi thẳng Blaze (lộ key).

## R2. Ngôn ngữ, thư viện

- **Decision**: Python 3.12 trong image (như ai-service), CI chạy 3.11 (như job `python` hiện có). `fastapi`, `uvicorn`,
  `pydantic`, `python-multipart` (nhận file), `httpx` (gọi Blaze, async, stream), `python-dotenv`, `prometheus-client`
  (metrics như ai-service). Pin version giống ai-service. Không thêm thư viện xử lý audio ở bản đầu (xem R6).
- **Rationale**: cùng stack với ai-service, team đã quen; `httpx` đã dùng ở pipeline và test.
- **Alternatives**: SDK Blaze (không thấy tên package công khai; REST đủ dùng).

## R3. Gọi Blaze cho một lượt: VAD trước, STT sau, tuần tự

- **Decision**: `POST /v1/audio/voice_activity` (đoạn có tiếng) rồi `POST /v1/audio/transcriptions` (model mặc định
  `blaze-stt-1.5`, `language=vi`, `timestamps=true`, `keywords`, `refine=false`, `timeout`). VAD không có đoạn nào →
  trả `no_speech`, **không** gọi STT (tiết kiệm credit). Đoạn cuối của VAD vượt giới hạn độ dài → `audio_too_long`
  trước khi gọi STT.
- **Rationale**: ví dụ response STT có `segments` liền nhau (0.0–2.5, 2.5–5.6) nên không lộ quãng ngừng; quãng ngừng
  và thời gian có tiếng phải lấy từ VAD. Gói Starter chỉ cho 1 luồng xử lý cùng lúc nên gọi song song có thể bị từ
  chối; tuần tự an toàn. Nếu gói cho phép, đổi sang song song bằng cấu hình (đo ở spike).
- **Alternatives**: chỉ STT (mất chỉ số quãng ngừng, thời gian có tiếng); STT realtime qua WebSocket (cần client
  stream PCM, thuộc tùy chọn B).
- **[spike]**: VAD có tính credit không; độ trễ VAD + STT với câu trả lời 30–90 giây; STT có trả mốc theo từ khi
  `timestamps=true` không (nếu có thì quãng ngừng tính từ từ, bỏ VAD).

## R4. Không có độ tin cậy nhận dạng

- **Decision**: voice-service không trả `stt_confidence`. Bên gọi không gửi trường này cho ai-service; theo contract
  §7.4, thiếu trường thì ai-service luôn chấm. Báo AIE rằng nhánh hỏi lại theo độ tin cậy không chạy với Blaze.
- **Rationale**: ai-service coi trường này là xác suất thật với ngưỡng 0.6; bịa số thay thế sẽ làm bỏ chấm sai.
- **Alternatives**: suy từ tỷ lệ thời gian có tiếng hoặc độ dài bản ghi (không phải xác suất, không đo được độ đúng).

## R5. Định nghĩa chỉ số trình bày

- **Decision**:
  - Đơn vị đếm: tách bản ghi theo khoảng trắng, bỏ dấu câu; tiếng Việt mỗi token là một âm tiết, thuật ngữ tiếng Anh
    mỗi token là một từ. Gọi chung "âm tiết" trong báo cáo, ghi rõ cách đếm.
  - Tốc độ nói = số âm tiết ÷ thời gian có tiếng (VAD) × 60.
  - Quãng ngừng dài = khoảng giữa hai đoạn VAD liền nhau ≥ `VOICE_LONG_PAUSE_S` (mặc định 2.0).
  - Từ đệm: danh sách cấu hình (`ừm`, `ừ`, `ờ`, `à`, `ơ`, `ạ` đứng một mình không tính, `kiểu như`, `thì là`, `nói chung
    là`), khớp theo cụm token, không phân biệt hoa thường. Tỷ lệ = số token thuộc từ đệm ÷ tổng token.
  - Thời gian suy nghĩ = (`recording_started_at` − `question_audio_ended_at`) + `start` của đoạn VAD đầu tiên; hiệu số
    âm hoặc thiếu mốc → rỗng + cảnh báo `invalid_client_timestamps` / không cảnh báo khi thiếu.
- **Rationale**: tất định, không cần mốc theo từ, test được không mạng.
- **[spike]**: Blaze có giữ từ đệm khi `refine=false` không. Không giữ → `VOICE_FILLERS_SUPPORTED=false`, tỷ lệ từ đệm
  luôn rỗng.

## R6. Định dạng audio đầu vào

- **Decision**: nhận `webm` (opus, mặc định MediaRecorder của Chrome), `ogg`, `wav`, `mp3`, `m4a`; kiểm theo đuôi file
  và content-type, giới hạn kích thước `VOICE_MAX_UPLOAD_MB` (mặc định 10) trước khi gọi Blaze; giới hạn thời lượng
  `VOICE_MAX_AUDIO_S` (mặc định 300) kiểm sau VAD.
- **[spike]**: Blaze có nhận `webm/opus` không. Không nhận → thêm bước đổi sang wav 16 kHz mono bằng `ffmpeg` trong image
  (thêm task), đo thêm thời gian đổi.

## R7. TTS

- **Decision**: `POST /v1/audio/speech` JSON, model mặc định `blaze-tts-1.5-realtime` (rẻ nhất có realtime theo bảng giá:
  ~$0.44/giờ), `response_format=mp3`, giọng mặc định cấu hình (`HN-Nam-2-BL` trong ví dụ tài liệu; danh sách giọng cho
  phép trong env), stream thẳng `audio/mpeg` về bên gọi (proxy theo chunk, không đệm cả file). Văn bản ≤ 1.000 ký tự.
- **Rationale**: bên gọi phát được ngay khi có chunk đầu (SC-003).
- **Alternatives**: SSE base64 (tốn băng thông thêm ~33%, bên gọi phải giải mã); job bất đồng bộ (chậm).
- **[spike]**: tên tham số chính xác (`input`, `voice`, `speed`, `response_format`, `model`) và thời gian tới byte đầu.

## R8. Lỗi, thử lại, hạn mức

- **Decision**: format lỗi giống ai-service `{error, message, details}` (service nội bộ Python, bên gọi là
  interview-service đã có client cho format này). Mã lỗi: `unauthorized` 401, `consent_required` 400, `invalid_audio`
  400 / 415, `audio_too_long` 413, `text_too_long` 400, `invalid_voice` 400, `quota_exceeded` 402 (Blaze 402/429 do
  hết credit), `provider_rate_limited` 429, `provider_timeout` 504, `provider_error` 502. Thử lại tối đa
  `VOICE_PROVIDER_RETRIES` (mặc định 2) cho lỗi mạng, 5xx, 429 với backoff 0.5 s × 2^n; không thử lại 4xx khác. STT trả
  202 (quá `timeout`) → `provider_timeout`.
- **Alternatives**: `{statusCode, message, errorCode, details}` của `docs/conventions.md` (dành cho API public NestJS;
  voice-service không public).

## R9. Bảo mật, riêng tư, log

- **Decision**: middleware `X-Internal-Token` giống `apps/ai-service/app/security.py` (staging/production thiếu token →
  503). Request STT bắt buộc `consent_confirmed=true` (FR-024). Audio chỉ ở bộ nhớ, chuyển tiếp cho Blaze, không ghi
  đĩa. Log: request id, kích thước, thời lượng, model, thời gian từng lần gọi, mã lỗi; không log bản ghi, văn bản câu
  hỏi, keywords. Metrics Prometheus: số request theo endpoint/kết quả, thời gian gọi nhà cung cấp, giây audio đã xử lý.
- **Rationale**: NFR-AI-PRIV11, constitution (không secret trong log), đồng bộ với ai-service.

## R10. Bộ đo

- **Decision**: thư mục `apps/voice-service/evals/`:
  - `manifest.jsonl` (commit): mỗi dòng `{clip_id, golden_id, speaker, kind: read|free, track}`; ghi âm ở
    `apps/voice-service/evals/audio/` (gitignore).
  - Ghi âm loại `read`: người đọc `answer` của một mẫu `apps/ai-service/evals/evaluator_golden.jsonl` → văn bản mẫu là
    bản ghi chuẩn. Loại `free`: nói tự do, chỉ dùng kiểm chỉ số trình bày.
  - `run_voice_eval.py`: gọi voice-service đang chạy (không gọi thẳng Blaze) → tỷ lệ lỗi theo âm tiết (Levenshtein
    trên token sau chuẩn hóa, tự viết, không thêm thư viện), tỷ lệ nhận đúng thuật ngữ (thuật ngữ = token của bản chuẩn
    có trong danh sách `/api/stt/phrases` của track), chạy 2 lần có / không keywords, độ trễ p50/p95, TTS thời gian tới
    byte đầu trên 20 câu hỏi golden, credit ước tính theo bảng giá (giây audio × đơn giá trong config).
  - Xuất `stt_samples.jsonl` (gitignore) cùng định dạng `evaluator_golden_stt.jsonl` (`id`, `stt_of`, `noise: ["real_stt"]`,
    `answer`) cho phần so điểm.
  - So điểm: chạy công cụ của AIE `python -m evals.run_evaluator --stt` với file mẫu do bộ đo xuất. Công cụ hiện đọc file
    cố định (`evals/stt_noise.py: STT_GOLDEN`); nhờ AIE thêm tùy chọn đường dẫn (ví dụ `--stt-file`). Chưa có thì bước
    này chờ, các phần đo khác vẫn chạy.
  - Kết quả ghi `specs/015-voice-mode/eval-results.md`; mã người ghi ẩn danh (`s1`, `s2`).
- **Rationale**: tránh vòng tròn TTS Blaze → STT Blaze; có sẵn nhãn Evaluator; không sửa code AIE.
- **Số lượng**: 24 clip `read` (≥ 2 người, 4 track) + 6 clip `free`.

## R11. ADR, port, CI, deploy

- **ADR**: `docs/architecture/adr/adr-011-voice-service-cho-tuy-chon-a.md` (ADR-009 để dành cho voice-gateway của tùy chọn
  B theo plan của AIE; ADR-010 đã dùng).
- **Port**: `8020` (ai-service 8000; 8011 từng dùng tạm khi chạy ai-service local).
- **CI**: thêm `voice-service` vào matrix job `python` trong `.github/workflows/ci.yml` (constitution VI); test không
  mạng, không key (client Blaze giả qua `httpx.MockTransport`).
- **Compose**: khối `voice-service` cạnh `ai-service`, healthcheck `/api/health`, env từ `.env` (`BLAZE_API_KEY`,
  `VOICE_SERVICE_INTERNAL_TOKEN`...).
- **Staging**: theo FR-019 của 014 (thêm service); không thêm route APISIX ở feature này.

## R12. Credit và thời gian

- Bảng giá Blaze (2026-11-25): STT `stt-async-1.5` ~2.2 credit/phút; TTS realtime 444 credit/giờ audio. Phiên 20 phút,
  ~8 phút ứng viên nói + ~4 phút câu hỏi đọc → ước ~18 + ~30 = ~48 credit/phiên (chưa tính VAD). Gói Starter 1.000
  credit → ~20 phiên. **[spike]** đo credit thật mỗi lần gọi.

## Kết quả spike (2026-11-25, gọi thật, tài khoản của owner)

Âm thanh thử: TTS Blaze đọc câu trả lời mẫu có từ đệm và thuật ngữ (10 s, 15 s, 30 s); ghi âm giọng thật chưa có (xem
"Còn mở"). Số đo trên máy owner qua mạng gia đình, mỗi phép 1–2 lần, chỉ để chọn hướng.

| Hạng mục | Kết quả | Hệ quả |
|---|---|---|
| STT response (`blaze-stt-1.5`, `-3`) | `id, object, status, model, created_at, filename, text, raw_text, segments[{id, startTime, endTime, text, speaker, words[{text, start, end}]}]` | **Có mốc theo từ**; tài liệu ghi sai tên trường (`start/end` của đoạn thực tế là `startTime/endTime`) |
| STT `blaze-stt-1.0` | 2.3 s cho 10 s audio, đoạn `{start, end, text, raw_text}`, **không** có `words`, sai thuật ngữ nhiều hơn | không dùng làm mặc định |
| Độ tin cậy | không có ở mọi mức (đoạn, từ) | giữ R4 |
| Từ đệm | giữ "Ừm", "À", "kiểu như", "nói chung là" khi `refine=false`; mất "Ờ" một lần | `VOICE_FILLERS_SUPPORTED=true`; cần xác nhận trên giọng thật |
| `keywords` | sửa rõ: "thread sai phạm" → "thread-safe", "hash map" → "HashMap", "POST" → "put"; "CAS" vẫn ra "CS" | giữ FR-002; giới hạn độ dài chưa chạm (9 từ) |
| Độ trễ STT batch (1.5) | 10 s audio → 6.3 s; 30 s → 9.4 s (≈ 5 s + 0.15 × độ dài); `timestamps` không đổi độ trễ; `blaze-stt-3` chậm hơn (8.6 s) | **SC-001 (≤ 5 s) không đạt với batch** — xem "Quyết định cần owner" |
| VAD | 0.2–0.4 s; `start/end` là **chuỗi**; thêm `transcription`, `error_msg`, `executing_time`; gộp cả câu 9.6 s thành 1 đoạn | VAD quá thô cho quãng ngừng → chỉ dùng VAD làm cổng "không có tiếng"; quãng ngừng, thời gian có tiếng tính từ mốc theo từ (thay R3/R5) |
| Gọi song song VAD + STT | không bị từ chối | giữ tuần tự mặc định (VAD chặn im lặng để đỡ tốn STT) |
| STT realtime (WebSocket, `blaze-stt-1.5-realtime`) | gửi dần theo nhịp nói: kết quả cuối **2.1 s** sau khi nói xong; gửi cả file một lần: 14 s (xử lý theo thời gian thật); chất lượng kém hơn batch ("thread-safe" → "thoát sếp"), `session.update` (keywords) chỉ nhận khi là tin đầu tiên và tác dụng yếu; sự kiện chỉ có `start_ms/end_ms` theo đoạn, không có mốc theo từ | chỉ nhanh khi client stream audio trong lúc nói (cần web, không còn là "ghi xong mới gửi") |
| TTS `blaze-tts-1.5-realtime` | byte đầu 0.3–0.8 s cho câu ≤ 300 ký tự; content-type `audio/mp3`; `response_format=pcm` + `sample_rate=16000` chạy được | SC-003 đạt |
| `GET /v1/audio/voices` | `[]` (chỉ giọng tự tạo) | danh sách giọng cấu hình tay; `HN-Nam-2-BL` chạy |
| Kết nối | httpx async đôi khi `ConnectError` ở lần nối đầu trên máy này | client có retry ở transport |

Credit: cả spike tốn **15 credit** (≈ 2,3 phút STT batch, ≈ 1 phút STT realtime, ≈ 2 phút audio TTS, vài lần VAD), khớp
bảng giá. Ước một phiên 20 phút (≈ 8 phút ứng viên nói, ≈ 3–4 phút câu hỏi đọc) ≈ 40–50 credit; tài khoản owner có
11.000 credit → đủ bộ đo (~30 clip × 2 lượt) và vài trăm phiên demo (SC-007).

### Giọng thật (2026-11-25, owner tự ghi bằng trình duyệt, webm/opus, 2 clip)

| Hạng mục | sample1 (60 s, cố ý ngập ngừng, Java) | sample2 (23 s, trôi chảy, Docker) |
|---|---|---|
| `webm/opus` | nhận trực tiếp (VAD 1.5 s, STT 200) → **không cần ffmpeg** | như trái |
| STT không keywords | "account code" (ConcurrentHashMap), "trusted" (thread-safe), "CIS" (CAS) | "Doctor English" (Docker image) |
| STT có keywords | đúng ConcurrentHashMap, thread-safe, CAS, synchronized; còn "push" (put) | đúng Docker image; "lớp GUI" (lớp ghi) cả hai lần |
| Từ đệm | giữ "Ừ", "Ừm", "ờ", "kiểu như là", "nói chung"; bản có keywords mất 1 "Ừm" | không có |
| Khoảng trống giữa từ ≥ 1 s | 8 chỗ: 1.2–1.4 s (nghỉ giữa câu), 1.7–2.3 s (chỗ cố ý dừng 2–3 s) | 0 |
| Độ trễ STT | 12.6–14.6 s | 8.3 s |

Hệ quả: keywords là **bắt buộc thực tế** (bên gọi luôn gửi danh sách của track); ngưỡng quãng ngừng dài đổi mặc định
**2.0 → 1.5 s** (tách được nghỉ giữa câu và dừng để nghĩ trên mẫu này; chốt lại trên bộ đo); lỗi kiểu "ghi" → "GUI" là
từ tiếng Việt bị đoán thành tiếng Anh, keywords không sửa được, Evaluator phải chịu (FR-AI-129). Ứng viên bắt đầu nói ở
giây 4.8 của sample1: phần im lặng đầu bản ghi được cộng vào thời gian suy nghĩ đúng như R5.

**Quyết định owner (2026-11-25)**: giữ STT batch `blaze-stt-1.5` (chất lượng, mốc theo từ, keywords), sửa SC-001 theo số
đo; stream realtime để sau khi có web.
