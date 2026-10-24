# context/

Ghi chú để người và trợ lý AI **nhớ ngữ cảnh làm việc giữa các phiên**: quy trình, quyết định đã chốt, trạng thái hiện tại, cách chạy test. Không chứa bí mật (khóa API, `.env`).

| File | Nội dung |
|---|---|
| [workflow.md](workflow.md) | Quy trình bắt buộc: nhánh, commit, push, PR, đồng bộ tài liệu, test |
| [decisions.md](decisions.md) | Quyết định của owner đã chốt và mặc định còn chờ xác nhận |
| [project-state.md](project-state.md) | Ảnh chụp trạng thái: nhánh, PR, việc đang làm |
| [environment.md](environment.md) | Lệnh chạy test, Docker, biến môi trường, hạn chế của máy dev |
| [quality-criteria.md](quality-criteria.md) | Golden set hiện có, tiêu chí câu hỏi khớp level và tự nhiên, số đo văn phong Interviewer |
| [de-data-assessment.md](de-data-assessment.md) | Đánh giá dữ liệu DE trong ai_db: độ phủ, chất lượng, giấy phép, đủ hay chưa |
| [next-phase-plan.md](next-phase-plan.md) | Kế hoạch giai đoạn tiếp theo: đo chất lượng, làm sạch và tận dụng dữ liệu DE |

**Quy tắc cập nhật (bắt buộc, owner nhắc lại 2026-10-24):** mọi thay đổi (code, dữ liệu, quyết định, quy trình, số đo) đều phải cập nhật tài liệu liên quan (`context/` và `docs/`) **trong cùng PR** với thay đổi đó. `project-state.md` cập nhật mỗi lần xong một việc; số đo mới thì cập nhật file đánh giá tương ứng.
