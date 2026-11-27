# Rubric gán nhãn CV × JD — 019 v1 (DE chốt 2026-11-26)

Dựa trên [rubric 017](../017-cv-jd-matching/label-rubric.md), thêm lựa chọn **u**. Gán độc lập, không xem điểm của hệ
nào, không hỏi nhãn của người kia.

Câu hỏi cho mỗi cặp: *"Nếu ứng viên này nộp vào tin này, nhà tuyển dụng có muốn gọi phỏng vấn không?"*

Đánh giá **toàn bộ mức phù hợp**, không chỉ đếm kỹ năng trùng:

1. **Công việc chính**: vai trò và trách nhiệm của JD có giống việc ứng viên đã làm (kinh nghiệm, dự án) không.
2. **Stack cốt lõi**: ngôn ngữ / nền tảng chính của JD (vd Java + Spring, Kubernetes, Spark) ứng viên có dùng thực tế
   không. Kỹ năng phụ (Git, Docker, SQL cơ bản) ít trọng số.
3. **Độ chín**: số năm và phạm vi việc của ứng viên có hợp yêu cầu của JD không.

| Nhãn | Nghĩa | Dấu hiệu |
|---|---|---|
| **2** phù hợp | Đáng gọi phỏng vấn ngay | Cùng loại công việc, có stack cốt lõi, độ chín hợp hoặc lệch nhẹ |
| **1** một phần | Có thể cân nhắc | Cùng mảng nhưng lệch stack cốt lõi có thể chuyển được, hoặc đúng stack nhưng lệch rõ về độ chín / trọng tâm công việc |
| **0** không | Không nên gọi | Khác loại công việc, thiếu gần hết stack cốt lõi, hoặc khác ngôn ngữ lập trình chính (xem lưu ý) |
| **u** không đủ thông tin | Không xét được | JD hoặc CV thiếu thông tin đến mức không xét được cả ba tiêu chí trên (vd JD chỉ có tiêu đề) |

Lưu ý:
- **Khác ngôn ngữ lập trình chính** (vd CV Node × JD Java): nhãn **0**. Chỉ khi JD ghi rõ chấp nhận ngôn ngữ khác thì
  tối đa **1**.
- Không cộng điểm vì CV và JD dùng chung từ ngữ chung chung ("team work", "Agile").
- Kỹ năng chỉ **liệt kê** mà không có kinh nghiệm hay dự án dùng nó thì yếu hơn kỹ năng có bằng chứng.
- JD không ghi cấp bậc: xét độ chín qua phần yêu cầu (số năm, trách nhiệm).
- Phân vân giữa hai nhãn thì chọn nhãn thấp hơn. **u** không dùng cho trường hợp phân vân.
- JD tiếng Anh hay tiếng Việt không ảnh hưởng nhãn.
