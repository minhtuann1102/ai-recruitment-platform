# Rubric gán nhãn CV × JD (017, US3)

Dùng chung cho người gán LLM và DE. Gán **trước** khi xem kết quả hệ thống, không xem điểm hay thứ hạng.

Câu hỏi cho mỗi cặp: *"Nếu ứng viên này nộp vào tin này, nhà tuyển dụng có muốn gọi phỏng vấn không?"*

Đánh giá **toàn bộ mức phù hợp**, không chỉ đếm kỹ năng trùng:

1. **Công việc chính**: vai trò và trách nhiệm của JD có giống việc ứng viên đã làm (kinh nghiệm, dự án) không.
2. **Stack cốt lõi**: ngôn ngữ / nền tảng chính của JD (vd Java + Spring, Kubernetes, Spark) ứng viên có dùng thực tế
   không. Kỹ năng phụ (Git, Docker, SQL cơ bản) ít trọng số.
3. **Độ chín**: số năm và phạm vi việc của ứng viên có hợp yêu cầu của JD không.

| Nhãn | Nghĩa | Dấu hiệu |
|---|---|---|
| **2** phù hợp | Đáng gọi phỏng vấn ngay | Cùng loại công việc, có stack cốt lõi, độ chín hợp hoặc lệch nhẹ |
| **1** một phần | Có thể cân nhắc | Cùng mảng nhưng lệch stack cốt lõi có thể chuyển được, hoặc đúng stack nhưng lệch rõ về độ chín / trọng tâm công việc (khác ngôn ngữ lập trình chính: xem lưu ý) |
| **0** không | Không nên gọi | Khác loại công việc (vd data analyst vs ML engineer platform), thiếu gần hết stack cốt lõi |

Lưu ý:
- **Khác ngôn ngữ lập trình chính** (vd CV Node × JD Java, CV Python × JD .NET): nhãn **0**. Chỉ khi JD ghi rõ chấp
  nhận ngôn ngữ khác ("Java / C# / Go hoặc tương đương", "không giới hạn ngôn ngữ") thì tối đa **1**. Lý do: nhà tuyển
  dụng trong nước lọc CV theo ngôn ngữ chính (owner chốt 2026-11-22, sửa rubric sau lần đo kappa đầu).
- Không cộng điểm vì CV và JD dùng chung từ ngữ chung chung ("team work", "Agile").
- JD không ghi cấp bậc: xét độ chín qua phần yêu cầu (số năm, trách nhiệm).
- Phân vân giữa hai nhãn thì chọn nhãn thấp hơn.
