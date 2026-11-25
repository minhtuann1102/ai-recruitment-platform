# ADR-011: Thêm `voice-service` phía server cho tùy chọn A (voice là lớp kênh)

**Ngày:** 2026-11-25  
**Trạng thái:** Proposed (spec 015; chuyển Accepted khi PR-1 được duyệt)  
**Liên quan:** [spec 015](../../../specs/015-voice-mode/spec.md), [research.md](../../../specs/015-voice-mode/research.md) R1; quyết định A8 (2026-10-15) trong [docs/ai-service/README.md](../../ai-service/README.md); [ai-integration.md](../ai-integration.md) §10; ADR-004, ADR-007

## Bối cảnh

Quyết định A8: chat văn bản là lõi, voice là lớp kênh (TTS đọc câu hỏi, STT bấm-để-nói, ứng viên được sửa bản ghi trước khi gửi, không lưu audio). `ai-service` đã nhận bản ghi STT như văn bản (`answer_source: "voice"`) và **không biết có voice**. Chưa có nhà cung cấp STT/TTS thật; nhà cung cấp chọn là Blaze (xử lý tại Việt Nam, cam kết không lưu dữ liệu).

Khóa nhà cung cấp không được nằm ở trình duyệt, nên kể cả với tùy chọn A vẫn cần một điểm phía server gọi Blaze. Điểm này còn phải tính chỉ số trình bày (thời gian suy nghĩ, tốc độ nói, quãng ngừng, từ đệm) từ mốc thời gian của STT, việc mà `ai-service` không nên biết.

## Quyết định

Thêm service thứ 7 `apps/voice-service` (FastAPI, stateless, **nội bộ**, port 8020, DE sở hữu):

- `POST /api/voice/transcribe`: VAD chặn lượt không có tiếng, rồi STT kèm danh sách thuật ngữ; trả bản ghi gốc, đoạn có tiếng, chỉ số trình bày của lượt (tính bằng code). Bắt buộc cờ `consent_confirmed`.
- `POST /api/voice/speak`: proxy stream mp3 từ TTS Blaze.
- `POST /api/voice/session-summary`: gộp chỉ số các lượt thành nhận xét theo mẫu cố định (không LLM, tách khỏi điểm kiến thức).
- Khóa Blaze chỉ đọc từ biến môi trường của service; token nội bộ `X-Internal-Token` như `ai-service`; không ghi audio ra đĩa, không log bản ghi hay văn bản câu hỏi.

Contract: [voice-service-api.md](../../../specs/015-voice-mode/contracts/voice-service-api.md). Bên gọi là `interview-service` (hoặc phần server của web) do FSD làm; service không có route public ở gateway cho đến khi FSD khai báo.

## Phương án đã loại

| Phương án | Lý do loại |
|---|---|
| Module voice trong `ai-service` | Cần AIE đồng ý, đổi A8 ("ai-service không biết có voice"), làm service LLM phình ra và lẫn trách nhiệm sở hữu |
| Trình duyệt gọi thẳng Blaze | Lộ khóa API |
| Chỉ script đo trong `data-pipeline` | Web / interview-service không có gì để gắn vào |
| Realtime hai chiều (tùy chọn B) | Cần client stream PCM và voice-gateway; nhóm chưa chốt (ADR-009 để dành cho hướng này) |

## Hệ quả

- Thêm một container (`ai_recruit_voice_service`), một job trong ma trận Python của CI (test không mạng, không key), một dòng trong `docker-compose.yml`; thêm vào staging theo quy trình "thêm service" của spec 014. **Vi phạm có chủ ý** nguyên tắc đơn giản (constitution VII): có task S4-DE-5 cần.
- `ai-service` và contract hiện có **không đổi**. Bên gọi gửi `transcript` (hoặc bản đã sửa) vào `/api/next-turn` như chat, không gửi `stt_confidence` (Blaze không trả; nhánh hỏi lại theo độ tin cậy của `ai-service` không chạy với nhà cung cấp này).
- FSD cần thêm `stt_raw_text` trên `/answer` và `media_consent_at` (lưu lời đồng ý micro / xử lý giọng nói); voice-service không lưu gì nên không tự kiểm được đồng ý, đó là điều kiện trước của bên gọi.
- Rủi ro vận hành: phụ thuộc một nhà cung cấp ngoài (hết credit, giới hạn tốc độ, độ trễ STT ~5 s + 0,15 × độ dài audio theo lần thử 2026-11-25); mọi lỗi trả mã phân biệt để bên gọi chuyển sang chat mà không mất lượt.
- Chỉ số tính từ mốc theo từ của STT, VAD của Blaze chỉ làm cổng "có tiếng"; nếu đổi model STT không trả mốc theo từ thì quay về đoạn VAD (độ chính xác quãng ngừng giảm).
