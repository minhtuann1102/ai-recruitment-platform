# Bản nháp sửa constitution (gộp vào PR ratify)

> Constitution đang **Proposed**. Sửa trực tiếp trong PR ratify rẻ hơn amend sau khi đã ratify (amend cần ≥ 2/3 thành viên, gồm owner workstream bị ảnh hưởng). Hướng xử lý này **đã được owner chấp nhận (2026-10-19)**; file constitution chưa được sửa, các đoạn dưới sẽ đưa vào PR ratify. Lý do và bối cảnh: [BRD §0.3](../../../docs/ai-service/requirements/01-brd.md).

## 1. Principle IV: cập nhật tên ADR và contract (cần làm bất kể chọn voice nào)

**Trước** (`.specify/memory/constitution.md`, mục IV):
> ai-service là stateless processor: nhận lịch sử qua request, trả kết quả theo contract `start` / `next-turn` / `finalize` (ADR-007), MUST NOT lưu phiên.

**Sau:**
> ai-service là stateless processor: nhận plan, state và ngữ cảnh qua request, trả kết quả theo contract `cv/parse` / `jd/parse` / `start` / `next-turn` / `finalize` (ADR-008), MUST NOT lưu phiên.

Lý do: ADR-007 đã bị ADR-008 thay thế; contract có thêm `cv/parse` và `jd/parse`.

## 2. Principle V: thêm đường dữ liệu huấn luyện (chỉ khi làm học từ dữ liệu, hiện hoãn)

**Giữ nguyên** các quy tắc về `knowledge_chunks`. **Thêm** vào cuối mục V:
> Dữ liệu dùng để fine-tune hoặc để agent học MUST: chỉ lấy từ phiên có cờ đồng ý riêng (`learning_consent_at`), đã ẩn danh (không tên, liên hệ, tên công ty), lưu ngoài `knowledge_chunks`, và tách hoàn toàn khỏi golden set dùng để đánh giá. Transcript, `cv_profile`, file CV MUST NOT vào `knowledge_chunks` trong mọi trường hợp.

Ngoài ra sửa dòng `source_type` cho khớp thực tế:
**Trước:** `source_type` (`interview_qa | job_description | textbook`)
**Sau:** `source_type` (`interview_qa | textbook`; `job_description` chỉ khi index JD Stretch của DE, và không agent nào dùng)

## 3. Principle VII: cho phép framework có điều kiện

**Trước:**
> YAGNI / KISS / DRY. Không thêm service, hạ tầng hay abstraction khi chưa có task cần.

**Sau:** (thêm một dòng ngay sau)
> Agent framework hoặc hạ tầng voice-agent chỉ được dùng khi có ADR nêu lý do, đã thử spike, và không thay thế logic điều phối (orchestrator, policy, tổng hợp điểm) vốn phải test được không cần framework.

## 4. Principle II: kênh media (chỉ nếu chọn voice tùy chọn B)

**Thêm** vào mục II một dòng:
> Ngoại lệ có ADR: kênh âm thanh thời gian thực giữa trình duyệt và voice-gateway dùng giao thức của hạ tầng voice-agent đã chọn; voice-gateway không sở hữu dữ liệu và gọi interview-service bằng đúng contract của chat.

Với voice tùy chọn A (mặc định) **không cần sửa mục II**.

## 5. Còn lại không cần sửa

II, III, IV (ngoài mục 1), VI không đổi. Không cần ADR mới cho tùy chọn A.
