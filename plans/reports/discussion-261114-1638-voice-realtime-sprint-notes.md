# Voice realtime: ghi chú thảo luận trước sprint voice

- **Ngày ghi:** 2026-11-14
- **Người đề xuất:** Tuấn (DE)
- **Trạng thái:** ghi chú để thảo luận, **chưa được team chốt**. Voice hội thoại realtime hiện vẫn nằm ngoài phạm vi
  theo [docs/ai-service/README.md](../../docs/ai-service/README.md) (mục ngoài phạm vi) và
  [01-brd.md](../../docs/ai-service/requirements/01-brd.md) ("chỉ làm nếu owner xác nhận tùy chọn B").
- **Cần đồng ý của:** Thắng (AIE, thangp97) cho ai-service; Tùng (FSD, hoangtunggg) cho web và interview-service.

**Đề xuất này đảo lại quyết định của team ngày 2026-10-15** (mục A8 trong README của ai-service): chat văn bản là
lõi, voice là lớp kênh Stretch ở S4, STT bấm-để-nói, ứng viên được sửa bản ghi trước khi gửi. Muốn đi theo hướng dưới
đây thì phải sửa A8 và spec 015 (chưa viết).

## 1. Hướng đề xuất

Chuyển phỏng vấn luyện tập sang voice hai chiều, kiểu "rảnh tay, lần lượt từng người nói": AI đọc câu hỏi, ứng viên
nói, hệ thống tự nhận ra ứng viên nói xong. Không làm ngắt lời ở giai đoạn đầu.

Lý do: gõ chữ cho phép ứng viên sắp xếp, sửa câu trả lời; nói thì không sửa được và có áp lực thời gian, sát phỏng
vấn thật hơn.

## 2. Hiện trạng

- Voice tùy chọn A đã có: TTS đọc câu hỏi, STT kiểu bấm-để-nói. Bản ghi giọng nói đi vào `/api/next-turn` như văn bản
  ([voice_turn.py](../../apps/ai-service/app/voice_turn.py)).
- Đã có: chuẩn hóa thuật ngữ phiên âm, chặn lượt không thu được tiếng, bỏ chấm khi độ tin cậy STT thấp, hỏi lại tối
  đa 1 lần mỗi topic rồi gợi ý gõ chat.
- Ngưỡng độ tin cậy STT (0.6) là giả định, chưa đo trên dịch vụ thật. Dịch vụ STT chưa chọn.
- Độ trễ phản hồi (đo 2026-11-09): p50 3.97 s, p95 6.73 s, Evaluator chiếm khoảng 70%
  ([08-latency-and-cost.md](../../docs/ai-service/08-latency-and-cost.md)).

## 3. Việc cần thêm

ai-service gần như không đổi. Việc mới nằm ở web và tầng trung gian.

| Việc | Thay cho |
|---|---|
| Nhận giọng nói liên tục (STT streaming) | Ghi âm xong mới gửi |
| Tự phát hiện ứng viên nói xong | Nút bấm-để-nói |
| Đọc câu hỏi ngay khi chữ đầu tiên sinh ra (TTS streaming) | Chờ đủ câu mới đọc |
| Tắt micro khi AI đang nói | (mới) tránh tiếng vọng, không cần hủy phát âm giữa chừng |
| Đồng hồ đếm ngược cho từng câu, hết giờ thì chốt lượt | (mới) |

Không cần LangGraph cho phần này. Nếu dùng framework thì là loại chuyên cho voice (LiveKit Agents, Pipecat), cần
đánh giá riêng.

## 4. Vấn đề phải giải quyết

1. **Khoảng lặng sau khi ứng viên nói xong.** Độ trễ hiện tại cộng thời gian xác nhận hết lượt và khởi động TTS là
   khoảng 5 giây trở lên; hội thoại bằng giọng nói thường cần khoảng dưới 1 giây mới tự nhiên (ước lượng chung,
   chưa đo). Hướng xử lý:
   - Rẻ: AI nói một câu đệm ngắn trong lúc Evaluator chạy.
   - Triệt để: rút gọn output của Evaluator, hoặc tách phần phân loại nhanh cho policy khỏi phần nhận xét chi tiết
     (việc của AIE).
2. **Phát hiện hết lượt.** Câu trả lời kỹ thuật có nhiều quãng ngừng để nghĩ. Ngưỡng im lặng ngắn thì cắt ngang, dài
   thì thêm độ trễ. Đề xuất: ngưỡng 1.5–2 giây, giữ nút "tôi nói xong" làm dự phòng.
3. **Chọn dịch vụ STT.** Cần: streaming, nhận tốt tiếng Việt lẫn thuật ngữ tiếng Anh, trả mốc thời gian theo từng
   từ, giữ lại từ đệm (cho mục 7).
4. **Loop im lặng.** Hiện micro không thu được tiếng thì báo lỗi và giữ nguyên lượt, vì ứng viên phải bấm nút mới
   thu lại. Khi rảnh tay, micro tự mở lại nên im lặng hoặc tiếng ồn có thể lặp vô hạn. Cần trần: sau 2–3 lần không
   thu được tiếng thì tạm dừng phiên hoặc chuyển sang chat. Bộ đếm phải nằm trong state của phiên, vì ai-service
   không lưu gì giữa các lượt.

## 5. Voice 100% hay voice mặc định

Tuấn muốn voice 100%. Khuyến nghị khi thảo luận: **voice mặc định, chat chỉ là đường dự phòng khi kỹ thuật hỏng.**

Vướng mắc nếu bỏ hẳn chat:

- Mất lối thoát khi micro kém, chỗ ồn, giọng khó nhận: ứng viên không hoàn thành được phiên.
- Điểm số đo cả chất lượng STT: thuật ngữ tiếng Anh trong câu tiếng Việt dễ bị nhận sai, ứng viên bị trừ điểm oan.
- Golden set và 43 mẫu Evaluator đều là văn bản, không còn đại diện cho sản phẩm nếu không đo thêm đường voice.
- Câu hỏi dạng viết code, viết truy vấn không hợp với nói. Chưa kiểm tra ngân hàng câu hỏi có dạng này không.

Cách đạt mục tiêu mà không cấm chat:

- Không hiện bản ghi cho ứng viên sửa; nói xong là gửi.
- Đồng hồ đếm ngược từng câu.
- Chat chỉ mở sau khi STT thất bại vài lần liên tiếp; lượt đó đánh dấu "trả lời bằng chữ" trong báo cáo.

Dù giao diện thế nào, **giữ đường văn bản ở ai-service**: toàn bộ eval và test tự động chạy bằng chữ.

## 6. Ngắt lời (hoãn)

| | Ứng viên ngắt lời AI | AI ngắt lời ứng viên lạc đề |
|---|---|---|
| Cần gì | Phát hiện ứng viên lên tiếng, dừng phát âm của AI | Đánh giá câu trả lời khi ứng viên còn đang nói |
| Độ khó | Vừa (FR-AI-126, mức Could) | Cao |
| Rủi ro | Thấp | Ngắt nhầm người đang dẫn vào ý chính |

- Lạc đề hiện đã được xử lý ở cuối lượt: lần đầu hỏi lại, lần hai chuyển chủ đề
  ([04-adaptive-loop-and-candidate-state.md](../../docs/ai-service/04-adaptive-loop-and-candidate-state.md)).
- Nếu sau này làm AI ngắt lời: kiểm tra phần đã nói mỗi khoảng 20 giây, chỉ ngắt khi lạc đề qua hai lần kiểm tra
  hoặc vượt giới hạn thời gian của câu.
- Thứ tự nếu làm: ứng viên ngắt lời AI trước, AI ngắt lời ứng viên sau cùng hoặc để hướng phát triển.

## 7. Phân tích thêm từ voice

Thêm nhóm chỉ số về cách trình bày, tính bằng code từ mốc thời gian, **báo cáo tách riêng khỏi điểm kiến thức**.

| Chỉ số | Cần gì từ STT |
|---|---|
| Thời gian từ lúc hỏi xong đến lúc bắt đầu trả lời | Mốc đầu lượt |
| Độ dài câu trả lời so với giới hạn, có hết giờ không | Mốc đầu và cuối lượt |
| Tốc độ nói (từ mỗi phút) | Mốc đầu và cuối lượt |
| Tỷ lệ từ đệm ("ừm", "à", "kiểu như") | Bản ghi giữ từ đệm |
| Số quãng ngừng dài giữa câu | Mốc thời gian theo từng từ |

Không làm: đoán cảm xúc hoặc độ tự tin từ giọng, chấm phát âm hoặc giọng vùng miền, cộng chỉ số trình bày vào điểm
kiến thức.

Ba chỉ số đầu làm được ngay khi có voice; hai chỉ số sau phụ thuộc dịch vụ STT.

## 8. Eval cho voice

- Cùng một câu trả lời, gõ chữ và nói ra có được chấm giống nhau không (đo tác động của lỗi STT lên điểm).
- Tỷ lệ lượt bị bỏ chấm vì độ tin cậy STT thấp, trên dịch vụ thật.
- Tỷ lệ bị cắt ngang do phát hiện hết lượt sai.
- Độ trễ từ lúc ứng viên nói xong đến lúc nghe tiếng AI (p50, p95).
- Số lần chạm trần loop im lặng.

## 9. Thứ tự đề xuất

1. Hoàn thiện agentic và eval trên luồng theo lượt hiện tại (baseline, bảng ablation).
2. Voice realtime rảnh tay, không ngắt lời; voice mặc định, chat dự phòng.
3. Ba chỉ số trình bày đơn giản.
4. Ứng viên ngắt lời AI.
5. AI ngắt lời ứng viên, hai chỉ số trình bày còn lại: hướng phát triển nếu không kịp.

Đồ án kết thúc 12/2026, nên bước 2 trở đi cần cân với thời gian còn lại.

## Câu hỏi chưa có lời đáp

- Team có đồng ý đưa voice realtime trở lại phạm vi không (tùy chọn B trong BRD)?
- Voice 100% hay voice mặc định có chat dự phòng?
- Dùng dịch vụ STT/TTS nào; có dùng framework voice không, hay tự viết?
- Ngân sách độ trễ cho voice là bao nhiêu, và Evaluator rút được đến đâu?
- Ngân hàng câu hỏi có câu dạng viết code, viết truy vấn không; nếu có thì xử lý thế nào khi không còn ô nhập chữ?
- Tầng nhận giọng nói liên tục đặt ở đâu: web, interview-service, hay một voice-gateway riêng?
- Mentor có yêu cầu gì về voice hoặc về mức "realtime" không?
