# Feature Specification: Kênh voice cho phỏng vấn luyện tập

**Feature Branch**: `docs/voice-mode-spec` (spec); branch code đặt ở plan (theo `docs/conventions.md`; thư mục spec
độc lập với branch)

**Created**: 2026-11-25

**Status**: Draft

**Owner**: DE — **Sprint**: 4 (23/11 → 07/12/2026), **Stretch** (S4-DE-5)

**Covers**: S4-DE-5 (Voice mode), phạm vi quyết định A8 ngày 2026-10-15
([`docs/ai-service/README.md`](../../docs/ai-service/README.md) §A8): chat văn bản là lõi, voice là lớp kênh; TTS đọc
câu hỏi, STT bấm-để-nói, ứng viên được sửa bản ghi trước khi gửi, giữ bản STT gốc và bản sửa, không lưu audio.

**Input**: User description: "Kênh voice cho phỏng vấn luyện tập, không làm FE. Service mới của DE giữ key nhà cung
cấp phía server: nói thành chữ kèm chỉ số trình bày theo lượt, chữ thành tiếng, gộp chỉ số theo phiên. Chỉ số trình
bày: thời gian suy nghĩ, độ dài câu trả lời, tốc độ nói, quãng ngừng dài, tỷ lệ từ đệm; tách khỏi điểm kiến thức, chỉ
ứng viên xem. Không phân tích con người (tuổi, giới tính, cảm xúc, phát âm), không chống gian lận, không realtime.
Bộ đo trên tập ghi âm có đồng ý; nghiệm thu bằng lệnh dòng lệnh và script đo."

**Nguồn thiết kế**: contract nội bộ ai-service §7.4 (`answer_source`, `stt_confidence`, lỗi `voice_no_speech`,
`GET /api/stt/phrases`) trong [`docs/ai-service/06-api-contract.md`](../../docs/ai-service/06-api-contract.md); FR-AI-120
đến 129 trong [`02-functional-requirements.md`](../../docs/ai-service/requirements/02-functional-requirements.md);
ghi chú thảo luận voice ngày 2026-11-14
([`plans/reports/discussion-261114-1638-voice-realtime-sprint-notes.md`](../../plans/reports/discussion-261114-1638-voice-realtime-sprint-notes.md))
§7 (chỉ số trình bày), §8 (eval). Spec chỉ ghi phần mới hoặc khác.

**Bối cảnh**:

- Phía ai-service (AIE) đã xong phần của tùy chọn A: bản ghi STT đi vào `/api/next-turn` như văn bản, đổi thuật ngữ
  phiên âm, chặn lượt không có tiếng, Evaluator chịu được bản ghi nhiễu (FR-AI-129). Chưa có nhà cung cấp STT/TTS thật;
  `/dev/play` dùng Web Speech API của trình duyệt.
- Key của nhà cung cấp không được nằm ở trình duyệt, nên kể cả với tùy chọn A vẫn cần một điểm phía server gọi nhà
  cung cấp. Đây là lý do có service mới (constitution VII: thêm service khi có task cần, task là S4-DE-5).
- Nhà cung cấp: **Blaze** (owner đã có tài khoản; mentor là đơn vị voice AI). Blaze cam kết không lưu dữ liệu (audio,
  bản ghi) sau khi xử lý, xử lý tại Việt Nam.
- Ghi nhận: gate go/no-go ngày 22/11 trong plan của AIE
  ([phase-08](../../plans/20261019-1100-ai-interview-brd-implementation/phase-08-voice-and-learning.md)) có điều kiện
  (c) "giao diện của FSD có hoặc đúng tiến độ" **chưa đạt** (2026-11-25: chưa có web, interview-service). Owner vẫn làm
  phần Stretch này, giới hạn ở phía server và bộ đo, nghiệm thu không cần giao diện. Còn khoảng 12 ngày tới hết S4.

## User Scenarios & Testing *(mandatory)*

Tác nhân: **bên gọi** (interview-service hoặc phần server của web khi FSD làm; trước đó là lệnh dòng lệnh của DE),
**ứng viên** (người nói, người đọc nhận xét trình bày), **DE** (vận hành, đo).

### User Story 1 - Nói câu trả lời, nhận bản ghi và chỉ số trình bày (Priority: P1)

Ứng viên bấm để nói, nói câu trả lời, thả nút. Bên gọi gửi đoạn ghi âm (kèm tùy chọn: track để lấy danh sách thuật ngữ,
mốc lúc câu hỏi đọc xong, mốc lúc bắt đầu ghi, giới hạn thời gian câu). Hệ thống trả bản ghi gốc, các đoạn có tiếng
kèm mốc thời gian, và chỉ số trình bày của lượt đó. Bên gọi hiện bản ghi cho ứng viên sửa, rồi gửi câu trả lời vào
luồng phỏng vấn như chat.

**Why this priority**: là phần cốt lõi của kênh voice; không có thì không có voice.

**Independent Test**: chạy lệnh với một file ghi âm mẫu; nhận bản ghi tiếng Việt có thuật ngữ tiếng Anh và đủ trường
chỉ số; chạy lại cùng file cho cùng chỉ số (trừ phần phụ thuộc nhà cung cấp).

**Acceptance Scenarios**:

1. **Given** file ghi âm 40 giây trả lời câu hỏi backend, **When** gửi kèm danh sách thuật ngữ của track
   `python_backend`, **Then** nhận bản
   ghi, danh sách đoạn có tiếng và chỉ số: độ dài câu trả lời, thời gian có tiếng, tốc độ nói, số quãng ngừng dài, tỷ lệ
   từ đệm (hoặc rỗng nếu không đo được), thời gian suy nghĩ rỗng (không gửi mốc).
2. **Given** cùng file kèm mốc "câu hỏi đọc xong" và "bắt đầu ghi" cách nhau 4 giây, và giọng nói bắt đầu ở giây thứ
   1.2 của bản ghi, **When** gửi, **Then** thời gian suy nghĩ = 5.2 giây.
3. **Given** file chỉ có tiếng ồn hoặc im lặng, **When** gửi, **Then** nhận kết quả "không có tiếng" rõ ràng, bản ghi
   rỗng, không có chỉ số, để bên gọi báo ứng viên kiểm tra micro hoặc chuyển sang chat.
4. **Given** nhà cung cấp lỗi hoặc quá thời gian sau số lần thử lại giới hạn, **When** gửi, **Then** nhận lỗi có mã
   phân biệt được (lỗi nhà cung cấp, hết hạn mức, file không hợp lệ) để bên gọi chuyển sang chat mà không mất lượt.

---

### User Story 2 - Nghe câu hỏi bằng giọng nói (Priority: P2)

Bên gọi gửi văn bản câu hỏi (đã hoàn chỉnh, tức `done.question` của ai-service). Hệ thống trả âm thanh dạng stream
để phát ngay khi có phần đầu, giọng tiếng Việt, chọn được giọng trong danh sách cấu hình.

**Why this priority**: TTS là nửa còn lại của kênh voice theo A8, nhưng không có nó ứng viên vẫn đọc được câu hỏi.

**Independent Test**: gửi một câu hỏi mẫu, lưu stream ra file, nghe được câu hỏi đầy đủ; đo thời gian tới phần âm
thanh đầu tiên.

**Acceptance Scenarios**:

1. **Given** câu hỏi tiếng Việt có thuật ngữ tiếng Anh dài 200 ký tự, **When** gửi, **Then** nhận stream âm thanh phát
   được, phần đầu tới trong ngưỡng SC-003.
2. **Given** văn bản rỗng hoặc dài quá giới hạn, **When** gửi, **Then** bị từ chối với lỗi rõ ràng, không gọi nhà cung
   cấp.

---

### User Story 3 - Nhận xét trình bày cuối phiên (Priority: P2)

Cuối phiên, bên gọi gửi danh sách chỉ số của các lượt voice. Hệ thống trả bản tổng hợp: giá trị tiêu biểu của từng
chỉ số, số lượt vượt ngưỡng, và vài câu nhận xét trung tính bằng tiếng Việt sinh bằng code (không dùng LLM). Bên gọi
đặt bản tổng hợp vào một mục riêng của báo cáo, tách khỏi điểm kiến thức, chỉ ứng viên xem.

**Why this priority**: là phần giá trị mới của voice so với chat; cần US1 trước.

**Independent Test**: gửi danh sách chỉ số dựng sẵn (không cần audio), nhận tổng hợp đúng theo công thức; danh sách
rỗng (hoặc toàn lượt chat, bên gọi không gửi lượt nào) trả `voice_turns: 0`, `stats` và `notes` rỗng.

**Acceptance Scenarios**:

1. **Given** 8 lượt, 3 lượt có quãng ngừng dài, **When** gộp, **Then** tổng hợp ghi "3/8 lượt" và có câu nhận xét về
   quãng ngừng.
2. **Given** các lượt không có thời gian suy nghĩ (bên gọi không gửi mốc), **When** gộp, **Then** chỉ số đó không xuất
   hiện trong nhận xét, không báo 0.

---

### User Story 4 - Bộ đo chất lượng voice (Priority: P3)

DE chạy script đo trên tập ghi âm nhỏ có đồng ý của người ghi, kèm bản ghi chuẩn gõ tay. Script báo: tỷ lệ lỗi nhận
dạng, tỷ lệ nhận đúng thuật ngữ (có và không có danh sách thuật ngữ), độ trễ STT và TTS (p50, p95), chênh lệch điểm
Evaluator giữa bản gõ tay và bản STT của cùng câu trả lời (qua ai-service), chi phí ước tính mỗi phiên. Kết quả ghi
vào một file kết quả trong thư mục spec, dùng cho báo cáo đồ án.

**Why this priority**: cho số liệu đưa vào báo cáo và chốt các ngưỡng; không chặn US1–US3 chạy được.

**Independent Test**: chạy script trên tập đo; ra bảng số; chạy lại cho cùng kết quả phần tính toán (phần độ trễ thay
đổi theo mạng).

**Acceptance Scenarios**:

1. **Given** tập ghi âm và bản ghi chuẩn, **When** chạy đo, **Then** có bảng chỉ số theo từng file và tổng hợp, ghi rõ
   số file, người ghi (mã ẩn danh), ngày đo.
2. **Given** có thêm tập tổng hợp (âm thanh sinh bằng TTS), **When** chạy đo, **Then** kết quả tập tổng hợp báo riêng,
   không gộp vào số chính.

---

### Edge Cases

- Bản ghi chỉ có từ đệm ("ừm", "à"): trả bản ghi như nhà cung cấp trả; việc chặn lượt là của ai-service
  (`voice_no_speech`), không lặp lại ở đây.
- Mốc client không hợp lệ (bắt đầu ghi trước khi câu hỏi đọc xong, hoặc thiếu một trong hai mốc): thời gian suy nghĩ
  rỗng, kèm cảnh báo trong kết quả, không lỗi cả request.
- Ứng viên bấm ghi trong lúc câu hỏi còn đang phát: như mốc không hợp lệ ở trên.
- File quá dài (vượt giới hạn cấu hình, mặc định 5 phút) hoặc định dạng không hỗ trợ: từ chối trước khi gọi nhà cung
  cấp.
- Hết hạn mức tài khoản nhà cung cấp: lỗi mã riêng, ghi log mức cảnh báo để DE biết nạp thêm.
- Bản ghi trộn tiếng Việt và tiếng Anh: không ép một ngôn ngữ; tốc độ nói đếm theo âm tiết / từ cách nhau bởi khoảng
  trắng (tiếng Việt tính âm tiết).
- Nhà cung cấp trả mốc thời gian theo đoạn mà không theo từ: quãng ngừng tính giữa các đoạn có tiếng (từ phát hiện
  tiếng nói), không cần mốc theo từ.
- Nhà cung cấp lọc mất từ đệm: tỷ lệ từ đệm luôn rỗng (theo cấu hình đặt sau khi thử), không báo 0.
- Ứng viên sửa bản ghi: chỉ số tính trên bản ghi gốc; ai-service nhận bản đã sửa (đúng contract §7.4).
- Request nhận dạng thiếu cờ xác nhận đồng ý (FR-024): từ chối, không gửi âm thanh tới nhà cung cấp.

## Requirements *(mandatory)*

### Functional Requirements

**Chuyển giọng nói thành chữ (US1)**

- **FR-001**: Hệ thống MUST nhận một đoạn ghi âm câu trả lời (định dạng phổ biến từ trình duyệt và file mẫu; danh sách
  chốt ở plan) cùng các tùy chọn: danh sách thuật ngữ, mốc "câu hỏi đọc xong", mốc "bắt đầu ghi", giới hạn thời gian câu (giây), và
  trả về bản ghi gốc, danh sách đoạn có tiếng (bắt đầu, kết thúc, giây tính từ đầu bản ghi), chỉ số trình bày của lượt.
- **FR-002**: Hệ thống MUST nhận một danh sách thuật ngữ tùy chọn do **bên gọi** gửi (bên gọi lấy từ
  `GET /api/stt/phrases?track=` của ai-service, vì bên gọi đã nói chuyện với ai-service) và đưa vào yêu cầu nhận dạng để
  tăng độ đúng thuật ngữ. voice-service không gọi ai-service và không chép danh mục thuật ngữ. Danh sách dài quá giới
  hạn của nhà cung cấp (chưa xác minh, chốt ở plan) thì cắt theo thứ tự bên gọi gửi và ghi cảnh báo.
- **FR-003**: Hệ thống MUST NOT trả hay bịa trường độ tin cậy nhận dạng (`stt_confidence`) vì nhà cung cấp không trả.
  Bên gọi không gửi `stt_confidence` cho ai-service; theo contract §7.4, thiếu trường này thì ai-service luôn chấm. Nhánh
  hỏi lại vì độ tin cậy thấp của ai-service vì vậy không chạy với nhà cung cấp này (ghi vào báo AIE).
- **FR-004**: Khi đoạn ghi âm không có tiếng nói, hệ thống MUST trả kết quả "không có tiếng" (cờ riêng, bản ghi rỗng,
  không chỉ số) thay vì lỗi.
- **FR-005**: Lỗi nhà cung cấp MUST được thử lại có giới hạn (số lần và thời gian chờ cấu hình được), sau đó trả lỗi
  theo mã phân biệt: `provider_error`, `provider_timeout`, `quota_exceeded`, `invalid_audio`, `audio_too_long`.

**Chỉ số trình bày theo lượt (US1)**

- **FR-006**: Hệ thống MUST tính các chỉ số sau bằng code, tất định với cùng đầu vào (bản ghi gốc + mốc theo từ của nhà
  cung cấp + mốc client). *Sửa 2026-11-25 sau spike*: mốc theo từ thay cho đoạn có tiếng (VAD quá thô); không có mốc
  theo từ thì dùng đoạn có tiếng với cùng công thức:

  | Chỉ số | Định nghĩa | Rỗng khi |
  |---|---|---|
  | Thời gian suy nghĩ (giây) | (mốc bắt đầu ghi − mốc câu hỏi đọc xong) + thời điểm từ đầu tiên | thiếu mốc, mốc không hợp lệ |
  | Độ dài câu trả lời (giây) | từ đầu từ đầu tiên tới cuối từ cuối cùng | không có tiếng |
  | Vượt giới hạn | độ dài > giới hạn bên gọi gửi | bên gọi không gửi giới hạn |
  | Thời gian có tiếng (giây) | độ dài câu trả lời − tổng các quãng ngừng dài | không có tiếng |
  | Tốc độ nói (âm tiết / phút) | số âm tiết hoặc từ (tách theo khoảng trắng) của bản ghi gốc ÷ thời gian có tiếng | không có tiếng |
  | Số quãng ngừng dài | số khoảng trống giữa hai từ liền nhau ≥ ngưỡng (mặc định 1.5 giây, cấu hình; sửa sau spike); không có mốc theo từ thì dùng khoảng giữa các đoạn có tiếng | không có tiếng |
  | Tỷ lệ từ đệm | số từ đệm (danh sách cấu hình: "ừm", "ờ", "à", "kiểu như", "nói chung là"...; bỏ "thì là" sau giọng thật vì là cách nói bình thường) ÷ tổng số âm tiết | nhà cung cấp lọc từ đệm (cấu hình) |

- **FR-007**: Chỉ số MUST tính trên bản ghi **gốc** của nhà cung cấp, không trên bản ứng viên đã sửa.
- **FR-008**: Hệ thống MUST NOT tính hay trả bất kỳ chỉ số nào về con người: tuổi, giới tính, cảm xúc, độ tự tin, chất
  lượng phát âm, giọng vùng miền.

**Chữ thành tiếng (US2)**

- **FR-009**: Hệ thống MUST nhận văn bản câu hỏi và trả âm thanh tiếng Việt dạng stream, giọng chọn theo tên trong danh
  sách cấu hình (mặc định một giọng). Văn bản rỗng hoặc dài quá giới hạn (mặc định 1.000 ký tự) bị từ chối trước khi
  gọi nhà cung cấp.
- **FR-010**: Hệ thống chỉ đọc văn bản hoàn chỉnh bên gọi gửi; không đọc theo từng token của stream câu hỏi (A8: tránh
  lệch khi ai-service gửi sự kiện `replace`).

**Tổng hợp theo phiên (US3)**

- **FR-011**: Hệ thống MUST nhận danh sách chỉ số các lượt (đúng định dạng FR-006, có thể kèm mã topic) và trả: số lượt
  voice, trung vị và khoảng của từng chỉ số, số lượt có quãng ngừng dài, số lượt vượt giới hạn, và 0–4 câu nhận xét
  trung tính bằng tiếng Việt theo mẫu cố định trong code. Không lưu gì giữa các request.
- **FR-012**: Chỉ số rỗng ở mọi lượt MUST không xuất hiện trong nhận xét. Danh sách rỗng trả `voice_turns: 0`, thống kê
  rỗng và không có nhận xét (`notes: []`); bên gọi hiển thị "không có dữ liệu voice" (không phải chuỗi do service trả).
- **FR-013**: Bản tổng hợp MUST NOT chứa hay ảnh hưởng điểm kiến thức. Ghép bản tổng hợp vào báo cáo là việc của bên
  gọi (hoặc thay đổi sau của AIE ở `/api/finalize`); spec này không giả định `/api/finalize` có mục đó.

**Bảo mật, riêng tư, vận hành**

- **FR-014**: Mọi endpoint trừ health MUST yêu cầu token nội bộ (cùng cơ chế với ai-service, header `X-Internal-Token`;
  staging/production thiếu token thì đóng cửa). Service không mở ra internet trực tiếp; route public (nếu có) do FSD
  khai báo ở gateway khi làm interview-service / web.
- **FR-015**: Hệ thống MUST NOT ghi audio ra đĩa hay kho lưu trữ, và MUST NOT ghi nội dung bản ghi hay văn bản câu hỏi
  vào log; log chỉ có mã request, độ dài audio, thời gian xử lý, mã lỗi, model.
- **FR-016**: Key nhà cung cấp chỉ đọc từ biến môi trường phía server; `.env.example` có tên biến, không có giá trị.
- **FR-024**: Âm thanh của ứng viên chỉ được gửi tới nhà cung cấp khi ứng viên đã đồng ý dùng micro và đồng ý cho nhà
  cung cấp đã khai báo xử lý giọng nói (NFR-AI-PRIV09, PRIV11; lời đồng ý nêu rõ nơi xử lý: Blaze, tại Việt Nam, không
  lưu). voice-service không lưu trạng thái nên không tự kiểm được: contract ghi đây là **điều kiện trước** của bên gọi,
  và request nhận dạng MUST có cờ xác nhận bên gọi đã có đồng ý (thiếu cờ thì từ chối, không gọi nhà cung cấp). Lưu
  `media_consent_at` là việc của FSD (đề xuất cột đã gửi FSD ngày 04/11). Không dùng âm thanh, giọng điệu để chấm điểm
  (PRIV12).
- **FR-017**: Service MUST có health endpoint, chạy được bằng Docker Compose cùng hạ tầng local, và thêm được vào
  staging theo quy trình "thêm service" của 014 (FR-019 của 014).
- **FR-018**: Có ADR ngắn ghi quyết định thêm service voice phía server cho tùy chọn A (lý do: key không ở trình
  duyệt; ai-service giữ "không biết có voice"); số ADR chốt ở plan (ADR-009 đang được plan của AIE dành cho voice-gateway
  realtime của tùy chọn B).

**Contract với bên gọi (chốt tên theo A8)**

- **FR-019**: Tên trường tùy chọn cho bản STT gốc trên `/answer` của interview-service là `stt_raw_text` (A8 để spec 015
  chốt tên). interview-service lưu cả `stt_raw_text` và câu trả lời đã sửa; tỷ lệ phần bị sửa là một số đo độ chính xác
  STT. Việc lưu thuộc FSD; voice-service không lưu.
- **FR-020**: Contract của voice-service (request, response, mã lỗi, sự kiện stream) MUST được ghi trong
  `docs/architecture/ai-integration.md` hoặc file contract riêng được link từ đó, cùng PR với code (constitution III).

**Bộ đo (US4)**

- **FR-021**: Script đo MUST nhận thư mục ghi âm + bản ghi chuẩn và báo: tỷ lệ lỗi theo âm tiết, tỷ lệ nhận đúng
  thuật ngữ (thuật ngữ lấy từ bản ghi chuẩn khớp danh sách của track) có và không có danh sách thuật ngữ, độ trễ STT
  (p50, p95), thời gian tới phần âm thanh TTS đầu tiên (p50, p95), chi phí credit ước tính cho một phiên 20 phút.
- **FR-022**: Bộ đo MUST có phần so điểm dùng lại công cụ đo Evaluator của AIE (`apps/ai-service/evals/run_evaluator.py`,
  chế độ `--stt`, không sửa code của AIE): mỗi ghi âm là một người đọc câu trả lời của một mẫu golden Evaluator, bản STT
  được ghi thành mẫu cùng định dạng `evaluator_golden_stt.jsonl` (`stt_of` trỏ về mẫu gốc), rồi báo chênh lệch band từng
  tiêu chí giữa bản sạch và bản STT. Nếu công cụ cần thêm tùy chọn đọc file mẫu khác thì nhờ AIE, không tự sửa.
- **FR-023**: Ghi âm của bộ đo MUST nằm ngoài git (thư mục gitignore), có xác nhận đồng ý của người ghi; kết quả chỉ ghi
  mã người ghi ẩn danh. Tập tổng hợp (âm thanh sinh bằng TTS) báo riêng, không làm số chính.

### Key Entities

- **Kết quả nhận dạng lượt**: bản ghi gốc, danh sách đoạn có tiếng (bắt đầu, kết thúc), cờ không có tiếng, chỉ số trình
  bày của lượt, cảnh báo (mốc không hợp lệ...), model nhận dạng, thời gian xử lý.
- **Chỉ số trình bày lượt**: các trường FR-006, mỗi trường có thể rỗng; kèm mã topic nếu bên gọi gửi.
- **Tổng hợp trình bày phiên**: số lượt voice, thống kê từng chỉ số, đếm lượt vượt ngưỡng, danh sách câu nhận xét.
- **Mẫu đo**: file ghi âm, bản ghi chuẩn, track, câu hỏi, mã người ghi, cờ tổng hợp hay ghi thật.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Ứng viên nhận bản ghi và chỉ số sau khi thả nút trong ≤ 10 giây ở p95 với câu trả lời ≤ 30 giây, và
  ≤ 20 giây với câu ≤ 90 giây (đo bằng bộ đo US4). *Sửa 2026-11-25 sau spike*: nhận dạng sau khi ghi xong của nhà cung
  cấp mất khoảng 5 giây + 0,15 × độ dài câu; mục tiêu cũ ≤ 5 giây chỉ đạt được bằng stream audio trong lúc nói (cần
  web, để sau). Bên gọi hiện trạng thái "đang nhận dạng".
- **SC-002**: Trên tập ghi âm thật, ≥ 85% thuật ngữ kỹ thuật được nhận đúng khi có danh sách thuật ngữ; báo cả con số
  khi không có danh sách để thấy mức cải thiện.
- **SC-003**: Câu hỏi ≤ 300 ký tự bắt đầu phát tiếng trong ≤ 1.5 giây ở p95.
- **SC-004**: ≥ 80% lượt có band Evaluator của bản STT lệch ≤ 1 so với bản gõ tay ở mọi tiêu chí (cùng chuẩn ±1 band
  của gate Evaluator).
- **SC-005**: Kiểm tra sau một lượt chạy quickstart: không có file audio nào được ghi trên máy chạy service, log không
  chứa nội dung bản ghi.
- **SC-006**: Cùng một bộ đầu vào (bản ghi + đoạn có tiếng + mốc), chỉ số và bản tổng hợp giống hệt nhau qua các lần
  chạy; test tự động chạy không cần mạng và không cần key.
- **SC-007**: Chi phí credit ước tính cho một phiên voice 20 phút được đo và ghi trong kết quả; tài khoản hiện có đủ
  cho bộ đo và demo (con số chốt sau khi đo).
- **SC-008**: Một người trong nhóm chạy quickstart (dựng service, gửi file mẫu, nghe TTS, chạy đo) chỉ theo hướng dẫn,
  không phải hỏi DE.

## Assumptions

- Nhà cung cấp là Blaze; thông tin API lấy từ trang tài liệu của Blaze ngày 2026-11-25 (nhận dạng trả bản ghi và mốc
  theo đoạn, không trả độ tin cậy; có phát hiện đoạn có tiếng; TTS stream). Các điểm **chưa xác minh bằng lần gọi
  thật**: nhận dạng có giữ từ đệm không, có mốc theo từ không, độ trễ thực tế với tiếng Việt xen thuật ngữ, credit
  tiêu thụ, giới hạn độ dài danh sách thuật ngữ, gói tài khoản (gói miễn phí chỉ cho 1 luồng xử lý cùng lúc, mà mỗi
  lượt có thể cần 2 lần gọi: nhận dạng và phát hiện đoạn có tiếng, vì đoạn trong kết quả nhận dạng liền nhau, không lộ
  quãng ngừng). Plan chạy một lần thử ngắn (owner tự đặt key vào `.env`) trước khi chốt FR-006 dòng từ đệm và các
  ngưỡng.
- Tập đo: khoảng 20–30 ghi âm thật bởi thành viên nhóm (có đồng ý), mỗi ghi âm là người đọc câu trả lời của một mẫu
  golden Evaluator, nên văn bản mẫu chính là bản ghi chuẩn (không phải gõ tay) và có sẵn nhãn để so điểm. Giới hạn: đọc
  thành tiếng ít từ đệm và quãng ngừng hơn nói tự nhiên, nên chỉ số trình bày được kiểm thêm trên vài câu trả lời nói tự
  do (không cần bản ghi chuẩn). Số lượng chốt ở plan.
- Ngưỡng quãng ngừng dài 1.5 giây (đổi từ 2.0 sau khi thử giọng thật 2026-11-25) và danh sách từ đệm là mặc định, chỉnh
  sau khi đo.
- Thời gian suy nghĩ tính theo đồng hồ của client cho hai mốc, nên không bị lệch giờ giữa máy.
- Trước khi có interview-service và web, bên gọi là lệnh dòng lệnh / script của DE. Không làm giao diện, không sửa
  `/dev/play` (code của AIE).
- Ngôn ngữ mặc định tiếng Việt, cho phép tiếng Anh xen kẽ.

## Out of Scope

- Đoán tuổi, giới tính, cảm xúc, độ tự tin từ giọng; chấm phát âm hay giọng vùng miền (công bằng trong tuyển dụng;
  quyết định nhóm). Dù nhà cung cấp có API cho các việc này.
- Chống gian lận: phát hiện giọng giả, phát hiện người nhắc bài, tách người nói.
- Đánh giá độ mạch lạc hay cấu trúc nội dung câu trả lời (việc của Evaluator, AIE).
- Hội thoại realtime rảnh tay, tự phát hiện hết lượt, ngắt lời (tùy chọn B, đề xuất 2026-11-14 chưa được nhóm chốt).
  Nhà cung cấp có kênh realtime để làm sau nếu nhóm chốt.
- Giao diện ghi âm / phát âm thanh, route public qua gateway, lưu bản ghi vào `interview_db` (FSD).
- Nhân bản giọng nói.

## Dependencies

- **AIE**: báo rằng nhà cung cấp không trả độ tin cậy nên nhánh hỏi lại theo `stt_confidence` không chạy (FR-003); xin
  ý kiến nếu AIE muốn ghép bản tổng hợp trình bày vào `/api/finalize` sau này (FR-013). Bộ đo FR-022 chạy công cụ
  đo Evaluator của AIE (cần key LLM hợp lệ trong `apps/ai-service/.env`; key trên máy owner đã hết hạn ngày 2026-11-23).
- **FSD**: trường `stt_raw_text` trên `/answer`, lưu bản gốc + bản sửa, gọi voice-service, gửi hai mốc thời gian và danh
  sách thuật ngữ; lấy và lưu đồng ý micro / xử lý giọng nói (`media_consent_at`, FR-024) trước khi ghi âm; route gateway
  khi có web.
- **014**: quy trình thêm service vào staging.
- **Owner**: key Blaze trong `.env` (không commit, không dán vào chat).
