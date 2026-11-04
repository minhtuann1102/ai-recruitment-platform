# Đề xuất cột đồng ý cho `interview_db` (gửi FSD)

> **Trạng thái:** Đề xuất của AIE (04/11), chờ FSD quyết. Chỉ là tài liệu: ai-service không đọc, không ghi các cột này và không đổi contract. Nguồn: FR-AI-110, FR-AI-111, FR-AI-130, FR-AI-131 ([02](../../../docs/ai-service/requirements/02-functional-requirements.md)), câu hỏi mở số 9 ở cùng file, G13 ở [11 §khoảng trống](../../../docs/ai-service/11-architecture-l2-containers.md), BRD BRU-14 và BRU-16, [phase 08](../phase-08-voice-and-learning.md) bước 4.

## 1. Vì sao nên thêm ngay ở migration giai đoạn 1

- Voice tùy chọn A (push-to-talk) gửi âm thanh tới nhà cung cấp STT bên thứ ba. Đây là xử lý dữ liệu cá nhân cho mục đích mới, nên cần lưu lại thời điểm ứng viên đồng ý (FR-AI-110, Nghị định 13/2023 và Luật Bảo vệ dữ liệu cá nhân, R-9 / P7).
- Học từ dữ liệu đang hoãn (giai đoạn 3), nhưng phiên từ hôm nay trở đi sẽ là nguồn dữ liệu duy nhất. Thiếu cột thì không chứng minh được phiên nào có đồng ý, và toàn bộ phiên cũ mặc định bị loại (FR-AI-130).
- Hai cột nullable thêm vào bảng có sẵn: không khóa bảng lâu, không cần backfill, mặc định là "không đồng ý".

## 2. Cột đề xuất (bảng `interview_sessions`)

| Cột | Kiểu | Mặc định | Ý nghĩa | Ai ghi | Ai đọc |
|---|---|---|---|---|---|
| `media_consent_at` | `timestamptz` NULL | NULL | Lúc ứng viên đồng ý gửi giọng nói tới nhà cung cấp STT. NULL thì FE không bật micro | interview-service, khi FE báo đồng ý | FE (bật nút micro), báo cáo kiểm toán |
| `learning_consent_at` | `timestamptz` NULL | NULL | Lúc ứng viên đồng ý cho dùng phiên (đã ẩn danh) để cải thiện model. NULL thì phiên **không bao giờ** vào tập huấn luyện | interview-service, checkbox riêng, không tích sẵn | Script trích dữ liệu huấn luyện (giai đoạn 3) |

```sql
ALTER TABLE interview_sessions
  ADD COLUMN media_consent_at    timestamptz NULL,
  ADD COLUMN learning_consent_at timestamptz NULL;
```

Cách dùng giống `cv_consent_at` (NFR-AI-PRIV05) đã có, nên không phát sinh mẫu mới.

## 3. Quy tắc đi kèm

| Quy tắc | Nguồn | Cơ chế cưỡng chế |
|---|---|---|
| Chưa có `media_consent_at` thì FE không gọi API micro của trình duyệt | FR-AI-110 | FE: test e2e kiểm không có `getUserMedia` trước khi đồng ý (`deterministic-check` khi có test; hiện `unenforced`) |
| Từ chối hoặc thu hồi vẫn hoàn tất phiên bằng chat | FR-AI-111 | FE: test e2e (`unenforced` cho tới khi có `apps/web`) |
| Thu hồi `learning_consent_at` thì đặt lại NULL và xóa phiên khỏi tập đã trích | FR-AI-130, 131 | Script trích lọc `learning_consent_at IS NOT NULL` (`deterministic-check` khi script tồn tại; hiện `unenforced` vì giai đoạn 3 hoãn) |
| Không hỏi gộp: CV, micro, học là ba lần đồng ý tách biệt | BRU-14, BRU-16, PRIV05 | `human-gate` ở review UI |
| ai-service không nhận và không cần các cột này | Constitution IV | Contract không có field (`deterministic-check` qua test schema) |

## 4. Câu hỏi mở cho FSD

1. **Camera có cần cột riêng không?** Video chỉ hiển thị cục bộ (FR-AI-112, A-6), không rời trình duyệt. AIE đề xuất **không lưu** đồng ý camera ở server, chỉ giữ trong phiên trình duyệt. Nếu FSD muốn lưu theo FR-AI-110 chữ cái, thêm `camera_consent_at` thay vì dùng chung `media_consent_at` (một cột không phân biệt được camera và micro).
2. **Lưu phiên bản nội dung thông báo?** Để chứng minh ứng viên đã đọc nội dung nào (nhà cung cấp STT có thể đổi), có thể thêm `consent_notice_version varchar` dùng chung cho các lần đồng ý. AIE nghiêng về thêm, nhưng đây là quyết định pháp lý và sản phẩm.
3. **Thu hồi micro giữa phiên có cần ghi lại không?** Đề xuất: không (YAGNI). FE tắt micro và chuyển sang chat; `media_consent_at` giữ nguyên làm bằng chứng đã từng đồng ý.
4. **Endpoint ghi cờ:** thêm field vào request tạo phiên, hay `PATCH /sessions/:id/consent`? Thuộc contract của interview-service, FSD và DE quyết.

## 5. Việc của AIE sau khi FSD chốt

- Sửa ERD ở [07](../../../docs/ai-service/07-data-storage.md), cột "Hiện trạng" của G13 ở 11, câu hỏi mở số 9 ở 02.
- Không đổi code ai-service.
