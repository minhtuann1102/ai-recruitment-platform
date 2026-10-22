# Nghiên cứu thị trường: AI mock interview kỹ thuật (đồ án)

Ngày: 2026-10-22 · Phạm vi: đối thủ toàn cầu + VN, cảm nhận ứng viên, best practice LLM-as-judge, gợi ý khác biệt hóa
Lưu ý chung: giá và tính năng lấy từ blog so sánh, phần lớn do vendor viết. Số liệu chưa đối chiếu trang chính thức đánh dấu **[chưa kiểm chứng]**.

---

## 1. Bối cảnh đối thủ

### 1.1 Bảng so sánh (toàn cầu)

| Sản phẩm | Đối tượng | Modality | Độ sâu feedback | Minh bạch điểm | Giá (theo nguồn, mâu thuẫn) | Ghi chú |
|---|---|---|---|---|---|---|
| Google Interview Warmup | Người tìm việc, mọi ngành (không kỹ thuật sâu) | Text + voice | Thấp: đếm từ lặp, từ khóa, filler, gợi ý cách nói | Không chấm điểm, không đúng/sai | Miễn phí; chỉ US (bài 2022) | Không đánh giá nội dung kỹ thuật. [9to5google](https://9to5google.com/2022/05/17/google-interview-warmup/) |
| Final Round AI | Ứng viên đi phỏng vấn thật | Copilot live + mock | Trung bình, bị chê "generic" | Thấp | $25–150/th **[chưa kiểm chứng]**; free trial mâu thuẫn | Trọng tâm copilot trong buổi thật. Trustpilot có phàn nàn tự gia hạn/hoàn tiền. [Four-Leaf](https://four-leaf.ai/blog/final-round-ai-alternatives), [Interview Drills](https://interviewdrills.com/blog/best-ai-mock-interview-tools), [Trustpilot](https://ie.trustpilot.com/review/finalroundai.com) |
| Yoodli | Diễn thuyết, phỏng vấn hành vi | Video/voice | Mạnh về delivery (um, tốc độ), yếu về nội dung | Trung bình (metric giọng) | Free 5 phiên; Pro ~$8–20/th **[chưa kiểm chứng]** | Người dùng: "không chấm câu trả lời có thể hiện competency". [Four-Leaf](https://four-leaf.ai/blog/best-mock-interview-platforms-2026) |
| Huru | Mobile-first, người tìm việc đại chúng | Video/voice | Phân tích giọng (pitch, filler, ngữ pháp), không feedback người | Thấp–TB | $24.99/th; free mâu thuẫn; Trustpilot 3.4 | Không luyện code. [FRAI blog (đối thủ viết)](https://www.finalroundai.com/blog/huru-review-pros-cons) |
| Pramp / Exponent | Dev, peer-to-peer | Video peer | Phụ thuộc người luyện cùng; không có AI | Không | Pramp 5 phiên/tháng miễn phí; Exponent $12–99/th **[mâu thuẫn]** | Chất lượng partner không đều. [Nguồn tổng hợp](https://www.finalroundai.com/blog/pramp-review-pros-cons) (blog đối thủ) |
| Interviewing.io | Dev, phỏng vấn người thật | Video, người | Cao (người) | Có (người chấm) | Từ ~$179/buổi **[chưa kiểm chứng]** | Tham chiếu chất lượng, không phải AI. [Four-Leaf](https://four-leaf.ai/blog/best-mock-interview-platforms-2026) |
| Micro1 AI Interviewer | **Nhà tuyển dụng** (sàng lọc kỹ sư) | Video/AI | Không dành cho ứng viên luyện | Không công bố cho ứng viên | — | Công ty nói tỷ lệ qua vòng người tăng ~50% vs 10–15% (tự báo, chưa kiểm chứng). [VentureBeat](https://venturebeat.com/ai/how-micro1s-ai-interviewer-could-make-tech-hiring-more-efficient-and-fair) |
| Mercor AI interview | **Nhà tuyển dụng** | AI + onsite | Không | Không | — | Ứng viên 2024: AI hỏi sâu theo câu trả lời, không có offer. [GeeksForGeeks](https://www.geeksforgeeks.org/?p=1189743) |
| AceRound AI | Dev, copilot + mock | Copilot live + mock | Mock có follow-up thích ứng, nguồn mâu thuẫn về mức feedback | Thấp | Free 30 phút; $14.90 tuần / $29.90 tháng **[mâu thuẫn]** | Hỗ trợ HackerRank/LeetCode trong buổi thật. Cần cân nhắc đạo đức (xem mục 4). [AceRound](https://www.aceround.app/blog/aceround-vs-final-round-ai) |
| Coding-AI (algoaim, Interview Codes, Cognao) | Dev SWE | Coding + AI interviewer | Có chấm code, feedback chi tiết | Chưa rõ | Chưa rõ | Khá gần sản phẩm này về cấu trúc (Gemini chạy hội thoại). [algoaim](https://ai.google.dev/competition/projects/algoaim?hl=vi), [Interview Codes](https://aipure.ai/vn/products/interview-codes) |

### 1.2 Thị trường Việt Nam

- **VietnamWorks AI Screening**: chấm hồ sơ theo title, skill, kinh nghiệm, học vấn; nhà tuyển dụng thêm tối đa 5 tiêu chí. Phía nhà tuyển dụng, không phỏng vấn ứng viên. [VietnamWorks FAQ](https://faq.vietnamworks.com/employers-en/new-updated-features/use-vietnamworks-ai-to-evaluate-candidates)
- **TopCV Toppy AI**: sourcing, sàng lọc, chấm điểm ứng viên; phía nhà tuyển dụng. [TopCV Business](https://tuyendung.topcv.vn/en)
- **ITviec**: không thấy thông tin AI interview trong kết quả tìm kiếm.
- **AI mock interview tiếng Việt**: tìm không thấy sản phẩm xác nhận. Kết quả chủ yếu là sản phẩm quốc tế hoặc blog marketing (AceRound, AIPure). Không có thông tin giá hay hỗ trợ tiếng Việt. **[Khoảng trống cần khảo sát thủ công: Google Play/App Store VN, nhóm Facebook dev VN.]**
- Bối cảnh: ứng viên VN dùng AI trợ giúp ngay trong phỏng vấn thật, nhà tuyển dụng lo ngại. [VnReview](https://vnreview.vn/threads/tuyen-dung-ky-su-phan-mem-cuoc-chien-ai-va-gia-tri-that-cua-tu-duy-con-nguoi.87514/)

### 1.3 Kết luận định vị

- Không thấy sản phẩm nào kết hợp: **tiếng Việt xen thuật ngữ Anh + chấm 4 tiêu chí theo level + đối chiếu JD + báo cáo có trích dẫn + riêng tư với nhà tuyển dụng**.
- Đối thủ chia 3 nhóm: (a) delivery/giọng (Yoodli, Huru), (b) copilot gian lận-rủi ro (Final Round, AceRound), (c) sàng lọc phía nhà tuyển dụng (Micro1, Mercor, VietnamWorks, TopCV).

---

## 2. Ứng viên nghĩ gì (phàn nàn và kỳ vọng)

- **Phản đối AI interview nói chung**: Reddit tháng 8/2025 có thread phản đối AI-only interview với >17k upvote; chủ đề: thay thế phán đoán người, bot lỗi, "hố đen" không phản hồi. Nguồn vendor, dùng thận trọng. [TalentPronto](https://www.talentpronto.ai/answers/do-candidates-hate-ai-interviews)
- **Nghiên cứu học thuật 2026**: phân tích 18k bài Reddit (2023–2025, 11 subreddit) + 17 phỏng vấn sâu. Đây là nguồn hệ thống nhất. [arXiv 2601.02775](https://arxiv.org/html/2601.02775v1)
- **Feedback chung chung** là phàn nàn lặp lại nhất với mock tool (Final Round, G2 AI Interview Companion). [Interview Drills](https://interviewdrills.com/blog/best-ai-mock-interview-tools), [G2](https://www.g2.com/products/ai-interview-companion)
- **Delivery vs nội dung**: người dùng Yoodli chê chỉ chấm giọng, không chấm câu trả lời. [Four-Leaf](https://four-leaf.ai/blog/best-mock-interview-platforms-2026)
- **Micro1 (Capterra 2026)**: khen quy trình mượt, câu hỏi đúng vai trò; chê thiếu đồng cảm với ứng viên lo lắng, giọng cứng, câu hỏi lặp/dài, yêu cầu chia sẻ toàn màn hình gây khó chịu. [Capterra](https://www.capterra.com/p/10030872/micro1/reviews/?page=9)
- **Kỳ vọng ngầm** (suy ra từ các phàn nàn, chưa có khảo sát định lượng): feedback cụ thể theo câu trả lời, biết mình thiếu gì, không bị chấm bí ẩn, không bị ghi lại/chia sẻ không báo trước.
- Điểm số: một nguồn cho rằng điểm AI đủ nhất quán để theo dõi tiến bộ cá nhân nhưng chưa đủ hiệu chuẩn để so sánh giữa người. [Four-Leaf / nguồn tổng hợp](https://four-leaf.ai/blog/best-mock-interview-platforms-2026) **[chưa kiểm chứng]**

---

## 3. Best practice LLM-as-interviewer và LLM-as-judge

### 3.1 Độ tin cậy của judge

- **Verbosity bias**: audit 2026 trên MT-Bench, 21 judge, dưới 0.011 với hầu hết; tác giả nói không chứng minh đã loại bỏ dưới rubric khác. [arXiv 2606.19544](https://arxiv.org/html/2606.19544v1). Kết luận: **đo lại trên câu trả lời phỏng vấn**, không giả định.
- **Position bias**: biến thiên lớn theo model (0.002 đến 0.192). Dùng khi so sánh A/B; với chấm điểm đơn lẻ (pointwise) ít áp dụng hơn. [arXiv 2606.19544](https://arxiv.org/html/2606.19544v1)
- **Self-preference / perplexity**: judge ưa output có perplexity thấp, kể cả không tự sinh. Nên dùng judge khác họ với generator nếu có thể. [ResearchGate (Self-Preference Bias)](https://www.researchgate.net/publication/385353198_Self-Preference_Bias_in_LLM-as-a-Judge)
- **Run-to-run variance**: nhiều nghiên cứu chỉ chạy 1 lần mỗi điều kiện; đo lặp là cần thiết. [arXiv 2606.13685](https://arxiv.org/pdf/2606.13685)
- **Shortcut/ẩn**: judge có thể dựa vào tín hiệu bề mặt không được nêu trong rubric (nguồn tham khảo: [arXiv 2509.26072](https://arxiv.org/html/2509.26072v1)). Một nghiên cứu khác ước tính ~55% biến thiên điểm không giải thích được bằng tiêu chí đã nêu (Feuer et al. 2025, trích trong Autorubric). [Autorubric](https://arxiv.org/html/2603.00077v1)

### 3.2 Rubric và anchor

- **Thang rời rạc, ngắn (3–5 mức), có mô tả hành vi** thay cho điểm số liên tục. Autorubric khuyến nghị; xáo trộn thứ tự option giảm biến thiên. [Autorubric](https://arxiv.org/html/2603.00077v1)
- **Anchor theo mức**: judge phân biệt đúng/sai câu trả lời mẫu chỉ 73.3% khi không có tham chiếu; 97.5% khi có đáp án vàng. Suy ra: **mỗi tiêu chí cần câu trả lời mẫu cho từng mức**. [arXiv 2608.04463](https://arxiv.org/pdf/2608.04463)
- **Hiệu chuẩn hậu kỳ**: hồi quy tuyến tính với ~100 mẫu người chấm; flow phức tạp cần ~1.500. Với đồ án, 100 mẫu là khả thi. [arXiv 2605.09227](https://arxiv.org/pdf/2605.09227)
- **Ensemble nhiều lần chấm**: giảm biến thiên, không chắc tăng độ đúng với judge mạnh. Chi phí tăng tương ứng. [Autorubric](https://arxiv.org/html/2603.00077v1)

### 3.3 Đồng thuận người–LLM

- Chấm câu trả lời mở: người–người ~0.8, người–LLM ~0.7 (kappa thấp hơn ~0.1). [Rubric study, arXiv 2608.21850](https://arxiv.org/pdf/2608.21850) (chỉ xem tóm tắt)
- Phỏng vấn thích ứng (đánh giá chuyên gia): Fleiss' kappa 0.67–0.93 giữa người chấm **hành vi interviewer**. [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC13324750/). Không thấy số LLM-người trực tiếp cho điểm ứng viên.
- SparkMe: Krippendorff α = 0.65 giữa 3 người. [arXiv 2602.21136](https://arxiv.org/pdf/2602.21136)
- **Kết luận**: đồng thuận LLM–người thường thấp hơn người–người. Ngưỡng ±1 band 90% (BRD BO-3) có thể khó đạt nếu rubric chủ quan; cần đo baseline người–người trước khi cam kết.

### 3.4 Áp dụng cho dự án (tóm tắt)

1. Anchor mẫu cho mọi (tiêu chí × level × mức).
2. Bằng chứng trích dẫn bắt buộc; code tính tổng điểm (đã có trong BR-06).
3. Đo test–retest trên transcript cố định.
4. Hoán thứ tự/độ dài khi so sánh cặp; đo, không giả định.
5. Judge khác họ với generator nếu quota cho phép.

---

## 4. Gợi ý khác biệt hóa (ưu tiên, 5–10 mục)

Ràng buộc kiểm tra: không voice realtime mặc định (OK; PTT là kế hoạch `main`), không nhận diện cảm xúc (**loại bỏ**), không fine-tune (BO-10 hoãn, **loại bỏ**), phiên riêng tư (**mọi đề xuất giữ riêng tư**).

| # | Đề xuất | Effort | Giá trị | BO | Ghi chú |
|---|---|---|---|---|---|
| 1 | **Anchor mẫu theo mức** cho 4 tiêu chí × level (câu trả lời mẫu mức 1/3/5) đưa vào prompt Evaluator | S | Cao | BO-3 | Nền cho mọi đo đạc khác. Nguồn 3.2. Demo: bảng trước/sau anchor |
| 2 | **Đo test–retest**: 20 transcript × 3 lần chấm, báo cáo độ lệch chuẩn và % lệch >0.5 band | S | Cao | BO-3, BO-7 (BR-14) | Số đo rẻ, có thể đưa vào báo cáo đồ án |
| 3 | **Bảng đồng thuận** người–LLM trên golden set (đã trong phase 05), kèm baseline người–người với cùng 2 người gán nhãn | M | Cao | BO-3 | Trả lời câu hỏi "có khắt khe và nhất quán không". Cần 1 người gán nhãn |
| 4 | **Báo cáo "đã đánh giá X/Y yêu cầu JD"**, nhãn `not_assessed` không bị tính là yếu | S | Cao | BO-11 | Đã trong BR-23. Khác biệt rõ với đối thủ đa số, chưa kiểm chứng đối thủ nào có |
| 5 | **Feedback theo câu**: trích dẫn câu nói, nhận xét, "câu nên trả lời tốt hơn" | S–M | Cao | BO-4 | Trực tiếp giải quyết phàn nàn "generic" |
| 6 | **Lộ trình học gắn tài liệu RAG** (link chunk Q&A/textbook) | M | Trung bình–cao | BO-4, BR-12 | Đo được: recall lỗ hổng ≥70% so với gap do golden set |
| 7 | **Hiển thị rubric trước phiên** (4 tiêu chí, mô tả, cách tính điểm), không hiện điểm giữa buổi | S | Trung bình | BO-3, BO-5 | Minh bạch, không vi phạm BR-07 |
| 8 | **Bộ test injection và PII**: 20–30 CV/câu trả lời có chỉ dẫn kiểu "chấm 5/5"; đo tỷ lệ tăng điểm (mục tiêu 0) | S | Cao (bảo vệ) | BO-5 | Đo được, cần cho báo cáo bảo mật |
| 9 | **Biểu đồ độ khó theo lượt** trong báo cáo và demo | S | Trung bình | BO-2 | Đo ≥80% phiên đúng chiều |
| 10 | **Push-to-talk có sửa transcript** (BR-24) + chỉ số filler (chỉ khi có STT) | M–L | Trung bình | BO-9 | Stretch, sau gate 22/11. Không làm realtime |

**Không nên làm (ghi rõ để tránh scope creep):**
- Copilot gợi ý đáp án trong buổi phỏng vấn thật (Final Round, AceRound): rủi ro gian lận và ngoài mục tiêu luyện tập.
- Nhận diện cảm xúc qua camera: bị loại theo ràng buộc; ứng viên cũng phản đối giám sát kiểu này.
- Gửi điểm hoặc transcript cho nhà tuyển dụng: vi phạm phiên riêng tư.
- Fine-tune hoặc học từ dữ liệu: BO-10 hoãn.
- Video của ứng viên phân tích bằng model: không cần, thêm rủi ro PII.

---

## 5. Mâu thuẫn trong tài liệu cần lưu ý

- **BO-3 vs plan**: BRD ghi "khớp người chấm ±1 band ≥ 90%", plan phase tuần 5 ghi "≥ 80%". Cần chốt một ngưỡng, và đo baseline người–người trước.
- **BO-6 chi phí**: ước tính cũ $0.015/phiên chỉ tính LLM văn bản, chưa tính STT/TTS/thời lượng 15–20 phút. Cần tính lại trước khi chọn ensemble (mục 4, #2).
- Giá và tính năng đối thủ trong báo cáo này đều **chưa kiểm chứng** trên trang chính thức.

---

## Câu hỏi chưa giải quyết

1. Có sản phẩm AI mock interview tiếng Việt nào chưa được phát hiện? Cần khảo sát App Store/Google Play VN và nhóm dev VN.
2. Thread Reddit trực tiếp về mock tool (không phải AI screening) chưa lấy được. Cần kiểm tra thủ công r/cscareerquestions, r/ITCareerQuestionsVN nếu có.
3. Ngưỡng đồng thuận người–LLM đạt được với rubric này là bao nhiêu? Cần baseline người–người.
4. Team có đồng ý tốn 2x chi phí Evaluator (ensemble) để demo độ ổn định không?
5. Người gán nhãn golden set: ai, bao nhiêu mẫu (đề xuất ≥100 mẫu để hiệu chuẩn)?
6. Ngưỡng ±1 band: 90% (BRD) hay 80% (plan)?
7. Giá đối thủ: cần xác minh trực tiếp từ trang chính thức trước khi đưa vào báo cáo cuối.

## Nguồn chính (truy cập 2026-10-22)

- [Four-Leaf: Final Round alternatives](https://four-leaf.ai/blog/final-round-ai-alternatives) · [Four-Leaf: best platforms 2026](https://four-leaf.ai/blog/best-mock-interview-platforms-2026)
- [Interview Drills: best AI mock tools](https://interviewdrills.com/blog/best-ai-mock-interview-tools)
- [9to5Google: Interview Warmup](https://9to5google.com/2022/05/17/google-interview-warmup/)
- [FRAI: Huru review](https://www.finalroundai.com/blog/huru-review-pros-cons) · [FRAI: Pramp review](https://www.finalroundai.com/blog/pramp-review-pros-cons) (blog đối thủ)
- [AceRound vs FRAI](https://www.aceround.app/blog/aceround-vs-final-round-ai)
- [VentureBeat: Micro1](https://venturebeat.com/ai/how-micro1s-ai-interviewer-could-make-tech-hiring-more-efficient-and-fair) · [Capterra: micro1](https://www.capterra.com/p/10030872/micro1/reviews/?page=9) · [GeeksForGeeks: Mercor 2024](https://www.geeksforgeeks.org/?p=1189743)
- [TalentPronto](https://www.talentpronto.ai/answers/do-candidates-hate-ai-interviews) · [arXiv 2601.02775](https://arxiv.org/html/2601.02775v1)
- [VietnamWorks AI Screening](https://faq.vietnamworks.com/employers-en/new-updated-features/use-vietnamworks-ai-to-evaluate-candidates) · [TopCV Business](https://tuyendung.topcv.vn/en) · [VnReview](https://vnreview.vn/threads/tuyen-dung-ky-su-phan-mem-cuoc-chien-ai-va-gia-tri-that-cua-tu-duy-con-nguoi.87514/)
- [arXiv 2606.19544](https://arxiv.org/html/2606.19544v1) · [arXiv 2606.13685](https://arxiv.org/pdf/2606.13685) · [Autorubric arXiv 2603.00077](https://arxiv.org/html/2603.00077v1) · [arXiv 2608.04463](https://arxiv.org/pdf/2608.04463) · [arXiv 2605.09227](https://arxiv.org/pdf/2605.09227) · [PMC AI interviewer](https://pmc.ncbi.nlm.nih.gov/articles/PMC13324750/) · [arXiv 2602.21136 SparkMe](https://arxiv.org/pdf/2602.21136)
- BRD nội bộ: `docs/ai-service/requirements/01-brd.md` (BO-1..BO-11, BR-01..BR-24)
