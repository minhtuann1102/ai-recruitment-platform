# context/

Ghi chú để người và trợ lý AI **nhớ ngữ cảnh làm việc giữa các phiên**: quy trình, quyết định đã chốt, trạng thái hiện tại, cách chạy test. Không chứa bí mật (khóa API, `.env`).

| File | Nội dung |
|---|---|
| [workflow.md](workflow.md) | Quy trình bắt buộc: nhánh, commit, push, PR, đồng bộ tài liệu, test |
| [decisions.md](decisions.md) | Quyết định của owner đã chốt và mặc định còn chờ xác nhận |
| [project-state.md](project-state.md) | Ảnh chụp trạng thái: nhánh, PR, việc đang làm |
| [environment.md](environment.md) | Lệnh chạy test, Docker, biến môi trường, hạn chế của máy dev |

**Quy tắc cập nhật:** đổi quy trình hoặc quyết định thì sửa file tương ứng **trong cùng PR** với thay đổi đó. `project-state.md` cập nhật mỗi lần xong một việc.
