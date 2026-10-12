# BRD — Business Requirements Document: AI Interview Service

| Mục | Giá trị |
|---|---|
| Phiên bản | 0.1 (Draft, chờ team review) |
| Ngày | 2026-10-12 |
| Owner | AIE |
| Reviewer | FSD, DE |
| Phạm vi | Phần AIE: `apps/ai-service` và phần tích hợp liên quan trong `interview-service` cho tính năng luyện phỏng vấn kỹ thuật bằng AI |
| Tài liệu liên quan | [FR](02-functional-requirements.md) · [NFR](03-non-functional-requirements.md) · [Kiến trúc L2](../11-architecture-l2-containers.md) · [Design doc](../README.md) · [ADR-008](../../architecture/adr/adr-008-evaluator-per-turn-orchestrator.md) |

> **Quy ước nguồn.** Mọi yêu cầu bám các tài liệu đã có trong repo (design doc `docs/ai-service`, constitution, sprint plan). Chỗ nào là con số giả định hoặc đề xuất chưa được team xác nhận thì ghi rõ **(giả định)** hoặc **(đề xuất)**. Các con số đó chưa được đo bằng dữ liệu thật.

## 1. Mục đích

Tài liệu mô tả **vì sao** và **cho ai** phần AI phỏng vấn được xây dựng, mục tiêu kinh doanh cần đạt, phạm vi, ràng buộc và tiêu chí thành công. Cách làm (FR, NFR, kiến trúc) nằm ở các tài liệu liên quan.

## 2. Bối cảnh và vấn đề

**Bối cảnh.** AI Recruitment Platform là hệ thống tuyển dụng trực tuyến ngành CNTT, đồ án tốt nghiệp của nhóm 3 người, thực hiện 09/2026 đến 12/2026 (hạn cứng 21/12/2026). Nền tảng phục vụ ba nhóm người dùng: Candidate (tìm việc, ứng tuyển, luyện phỏng vấn), Employer (đăng tin, quản lý ứng viên), Admin (quản trị). Tính năng khác biệt của nền tảng là **phỏng vấn luyện tập bằng AI Agentic**.

**Vấn đề cần giải quyết.**

| # | Vấn đề | Hệ quả với ứng viên |
|---|---|---|
| P1 | Ứng viên IT ít có cơ hội luyện phỏng vấn kỹ thuật **có phản hồi cụ thể** trước khi phỏng vấn thật | Vào phỏng vấn thật mà không biết mình yếu ở đâu |
| P2 | Bộ câu hỏi cố định không thích ứng với trình độ: người giỏi bị hỏi dễ, người yếu bị hỏi quá khó | Buổi luyện tập kém giá trị |
| P3 | Phỏng vấn thử với người thật tốn thời gian và phụ thuộc người có kinh nghiệm | Khó luyện lặp lại |
| P4 | Điểm số do LLM chấm dễ **dễ dãi, thiếu nhất quán, bịa căn cứ** | Ứng viên tin sai vào năng lực của mình |
| P5 | CV và câu trả lời của ứng viên là đầu vào không tin cậy (có thể chứa chỉ dẫn tác động tới hệ thống) | Điểm bị thao túng, dữ liệu cá nhân bị lộ |

## 3. Mục tiêu kinh doanh

| ID | Mục tiêu | Giải quyết | Thước đo thành công |
|---|---|---|---|
| BO-1 | Mô phỏng một buổi phỏng vấn kỹ thuật **gần thực tế**, bám vào CV thật của ứng viên | P1, P3 | Câu hỏi intro bám dự án trong CV khi có CV; judge LLM chấm độ tự nhiên ≥ 4.0/5 (đề xuất) |
| BO-2 | Hệ thống **thích ứng** sau mỗi câu trả lời (hỏi sâu, gợi ý, hạ hoặc tăng độ khó, đổi chủ đề) | P2 | Quỹ đạo độ khó đúng chiều ở ≥ 80% phiên giả lập (đề xuất) |
| BO-3 | Chấm điểm **khắt khe, có căn cứ, nhất quán** theo chuẩn của level | P4 | Khớp người chấm ±1 band ≥ 90%, độ lệch khoan dung trong [−0.3, +0.3] (đề xuất) |
| BO-4 | Báo cáo cuối buổi đủ cụ thể để ứng viên biết **học gì tiếp** | P1 | Recall lỗ hổng ≥ 70%, không có điểm mạnh sai (đề xuất) |
| BO-5 | **Bảo vệ** dữ liệu cá nhân và chống thao túng điểm | P5 | 0 PII trong log và đầu vào LLM; injection không làm tăng điểm (100% bộ test adversarial) |
| BO-6 | Vận hành với **chi phí thấp** trong khả năng của đồ án | Ràng buộc | Chi phí ước tính ≈ $0.015/phiên chuẩn (giả định); cảnh báo khi > $0.10/phiên |
| BO-7 | **Demo chạy được end-to-end** trước hạn đồ án, đủ số liệu để đưa vào báo cáo | Ràng buộc | Feature freeze 06/12/2026, demo trên staging; bảng chỉ số đánh giá đưa vào báo cáo |
| BO-8 | Mở rộng thêm **vị trí phỏng vấn mới** mà không đổi kiến trúc | Tương lai | Thêm vị trí = thêm một file catalog, test tự nhận |

## 4. Phạm vi

### 4.1 Trong phạm vi

- Phỏng vấn kỹ thuật dạng **chat văn bản** tiếng Việt, giữ thuật ngữ tiếng Anh.
- Vị trí (track) theo topic catalog: `java_backend`, `python_backend`, `nodejs_backend`, `ai_engineer`. *Design doc gốc chỉ ghi MVP là Java và Node.js; ba vị trí còn lại do AIE bổ sung vào catalog, **cần team xác nhận**.*
- Level: Fresher, Junior, Middle, Senior. Thời lượng 15 đến 45 phút, mặc định 30.
- Dùng lại **CV đã nộp ở job-service** (PDF hoặc DOCX), khuyến nghị nhưng không bắt buộc.
- Năm vai trò agent: CV Parser, Planner, Evaluator, Interviewer, Reporter, điều phối bằng code.
- Streaming câu hỏi qua SSE.
- Báo cáo cuối buổi: điểm theo phần và theo tiêu chí, điểm mạnh, cần cải thiện, lộ trình học, điểm và nhận xét từng câu.
- Knowledge base RAG gồm `interview_qa` và `textbook`.
- Chống prompt injection từ CV, câu trả lời và nội dung RAG; redact PII trước khi gửi LLM.
- Xử lý lỗi LLM bằng retry giới hạn và fallback.
- Bộ đánh giá chất lượng: golden set cho Evaluator, ứng viên giả lập chạy end-to-end.
- Ghi nhận token, latency và chi phí theo phiên.

### 4.2 Ngoài phạm vi

| Hạng mục | Lý do hoặc hướng sau này |
|---|---|
| Job Description làm đầu vào cho AI | Quyết định của team ngày 2026-10-06. Index JD vào `ai_db` là Stretch của DE |
| Voice, video, nhận diện cảm xúc | Không kịp 8 tuần |
| Live coding, chạy code ứng viên | Cần sandbox |
| OCR CV dạng ảnh scan | Báo lỗi `cv_unreadable`, cho phép phỏng vấn không CV |
| Vị trí ngoài các track trên (Frontend, DevOps, Data, QA, Mobile) | Kiến trúc hỗ trợ, thêm bằng catalog, không làm trong 8 tuần |
| Employer xem kết quả luyện tập của ứng viên | Cần cơ chế consent riêng; phiên luyện tập mặc định riêng tư |
| Chống gian lận (copy-paste, tra cứu) | Stretch S5-8 |
| Fine-tune model, agent tự học từ dữ liệu | Không đủ dữ liệu và thời gian |
| Dùng agent framework (LangGraph, CrewAI, AutoGen) | State machine tự viết đủ dùng (constitution VII) |
| Giao diện web (`apps/web`) | Thuộc workstream FSD |

## 5. Các bên liên quan

| Bên | Vai trò | Quan tâm chính |
|---|---|---|
| **Candidate** | Người dùng chính | Phỏng vấn tự nhiên, phản hồi hữu ích và công bằng, dữ liệu CV được bảo vệ |
| **Employer** | Người dùng nền tảng | Không dùng phiên luyện tập trong MVP; có thể xem kết quả khi có consent (tương lai) |
| **Admin** | Quản trị | Quản lý danh mục và bộ câu hỏi (topic catalog và Q&A hiện là file trong repo, do AIE và DE sở hữu) |
| **AIE** (chủ phần này) | Thiết kế, xây dựng ai-service | Chất lượng agent, chi phí, tiến độ 8 tuần |
| **FSD** | Sở hữu interview-service và job-service | Contract ổn định, migration `interview_db`, relay SSE |
| **DE** | Hạ tầng và pipeline dữ liệu | Dữ liệu `knowledge_chunks`, đồng sở hữu topic catalog, APISIX, CI |
| **Giảng viên và hội đồng đồ án** | Đánh giá | Demo chạy được, số liệu đánh giá, đối chiếu tuân thủ pháp lý dữ liệu cá nhân |

## 6. Yêu cầu nghiệp vụ (BR)

Ưu tiên theo MoSCoW. Cột "FR" trỏ sang [tài liệu FR](02-functional-requirements.md).

| ID | Yêu cầu nghiệp vụ | Ưu tiên | Mục tiêu | FR chính |
|---|---|---|---|---|
| BR-01 | Hệ thống cho phép ứng viên chọn **vị trí** và **level** rồi thực hiện một buổi phỏng vấn kỹ thuật hội thoại | Must | BO-1 | FR-AI-001..003, 037, 039 |
| BR-02 | Câu hỏi phải **bám vào CV** của ứng viên khi có CV hợp lệ; không có CV vẫn phỏng vấn được | Must | BO-1 | FR-AI-010..015, 020 |
| BR-03 | Mỗi buổi gồm các giai đoạn cố định (giới thiệu và dự án, kiến thức chuyên môn, tình huống, kết thúc) với số chủ đề phù hợp level | Must | BO-1 | FR-AI-003, 020, 036 |
| BR-04 | Hệ thống **thích ứng** độ khó và hành động hỏi dựa trên chất lượng câu trả lời, trong giới hạn cứng về số lượt và thời gian | Must | BO-2 | FR-AI-033..036 |
| BR-05 | Mỗi câu trả lời được chấm theo **4 tiêu chí** so với chuẩn level; điểm có căn cứ trích dẫn từ câu trả lời | Must | BO-3 | FR-AI-030..032 |
| BR-06 | **Điểm tổng hợp do code tính**, không do LLM tự cộng; nhận xét văn bản không được sửa điểm | Must | BO-3 | FR-AI-050..052 |
| BR-07 | Ứng viên **không thấy điểm hay đáp án giữa buổi**; chỉ nhận báo cáo sau khi kết thúc | Must | BO-3 | FR-AI-037, 039 |
| BR-08 | Báo cáo cuối buổi gồm điểm, điểm mạnh, cần cải thiện, lộ trình học có dẫn chứng, điểm và nhận xét từng câu | Must | BO-4 | FR-AI-050..055 |
| BR-09 | Hệ thống **chống thao túng điểm**: chỉ dẫn nhúng trong CV hoặc trong câu trả lời không làm tăng điểm | Must | BO-5 | FR-AI-012, 030..032 |
| BR-10 | Thông tin cá nhân trong CV được **che trước khi gửi LLM** bên thứ ba; transcript và CV không bao giờ vào kho dữ liệu RAG | Must | BO-5 | FR-AI-011, 060 |
| BR-11 | Buổi phỏng vấn **không chết** khi LLM chậm hoặc lỗi: có retry giới hạn và phương án thay thế | Must | BO-1 | FR-AI-070..073 |
| BR-12 | Câu hỏi và nhận xét dựa trên **kiến thức tham chiếu** (Q&A mẫu, tài liệu) để giảm chấm sai và bịa | Should | BO-3 | FR-AI-060..064 |
| BR-13 | Chi phí và độ trễ của mỗi phiên được **đo và lưu** để kiểm soát | Should | BO-6 | FR-AI-080 |
| BR-14 | Chất lượng agent được **đo lặp lại được** bằng golden set và ứng viên giả lập, làm bằng chứng cho báo cáo đồ án | Must | BO-3, BO-7 | FR-AI-082 |
| BR-15 | Thêm **vị trí phỏng vấn mới** chỉ cần bổ sung dữ liệu catalog, không sửa code điều phối | Should | BO-8 | FR-AI-002 |
| BR-16 | Có **môi trường mock** để FSD và FE tích hợp độc lập trước khi AI thật sẵn sàng | Must | BO-7 | FR-AI-083, 090 |

## 7. Quy tắc nghiệp vụ

| ID | Quy tắc | Nguồn |
|---|---|---|
| BRU-01 | **Level là nguồn sự thật.** CV chỉ là lời tự khai: ứng viên chọn Junior mà CV ghi 6 năm thì vẫn phỏng vấn theo chuẩn Junior | design 01 §2.1 |
| BRU-02 | Điểm là band tương đối với chuẩn level: cùng câu trả lời, ứng viên Senior nhận band thấp hơn Junior | design 05 §6.2 |
| BRU-03 | Mỗi topic có giới hạn follow-up (2 hoặc 3 theo level), tối đa 1 gợi ý, tối đa 1 lần hỏi lại; tổng tối đa 24 lượt mỗi phiên | design 03 §4.3 |
| BRU-04 | Hết giờ thì sang kết thúc; quá hạn cứng (thời lượng + 3 phút) thì kết thúc ngay | design 03 §4.4 |
| BRU-05 | Lượt hỏi lại (clarify), lượt lỗi chấm (degraded) và lượt kết thúc không tính điểm | design 05 §6.3 |
| BRU-06 | Trọng số giai đoạn theo level: Senior nặng phần tình huống, Fresher nặng kiến thức nền | design 05 §6.3 |
| BRU-07 | Kết luận so với chuẩn level: ≥ 8.5 vượt kỳ vọng, 7.0 đến 8.4 đạt, 5.0 đến 6.9 gần đạt, dưới 5.0 chưa đạt. *(giả định, chỉnh sau khi chạy ứng viên giả lập)* | design 05 §6.3 |
| BRU-08 | Báo cáo hiển thị mức tin cậy; mức thấp phải có cảnh báo; luôn kèm lời nhắc điểm do AI chấm, mang tính tham khảo | design 05 §6.4, §6.5 |
| BRU-09 | Dùng CV nộp để ứng tuyển cho luyện phỏng vấn là **mục đích khác**, cần ứng viên đồng ý riêng | design 01 §2.2, 10 §11 |
| BRU-10 | Employer **không** xem phiên luyện tập của ứng viên trong MVP | design README §1.4 |
| BRU-11 | Quota mặc định 5 phiên mỗi ngày mỗi ứng viên *(đề xuất)* | design 10 |
| BRU-12 | Câu trả lời chỉ gồm cụm kiểu "không biết", "chưa học" (tối đa 6 từ) được xem là không biết và không cần Evaluator; có nội dung khác thì vẫn chấm | design 03 §4.5 |

## 8. Tiêu chí thành công

Ngưỡng lấy từ [design doc 10](../09-agent-quality-evaluation.md); toàn bộ là **(đề xuất)**, chỉnh sau lần chạy đầu. Đo bằng ba tầng test: unit (CI), golden set Evaluator, ứng viên giả lập end-to-end.

| Nhóm | Chỉ số | Ngưỡng |
|---|---|---|
| Độ chính xác chấm | Khớp người chấm ±1 band | ≥ 90% (mốc tuần 2: ≥ 80%) |
| | MAE band | ≤ 0.6 |
| | Độ lệch khoan dung (LLM trừ người) | Trong [−0.3, +0.3] |
| | Nhất quán qua 3 lần chạy (độ lệch chuẩn band) | ≤ 0.3 |
| | Bắt manipulation | 100% |
| Phân biệt | Điểm giỏi > trung bình > yếu trong cùng level, track | ≥ 7/8 tổ hợp |
| | Khoảng cách điểm giỏi trừ yếu | ≥ 3.0 |
| Thích ứng | Quỹ đạo độ khó đúng chiều | ≥ 80% phiên |
| Báo cáo | Recall lỗ hổng trong `improvements` | ≥ 70% |
| | Điểm mạnh sai | 0 |
| Độ bền | Lỗi format sau repair; tỉ lệ fallback | < 1%; < 2% |
| Vận hành | Thời gian tới token đầu tiên P50; P95 | ≤ 3.5 s; ≤ 6 s *(giả định)* |
| | Chi phí phiên chuẩn | ≈ $0.015, cảnh báo > $0.10 *(giả định)* |

Ghi chú: mốc "khớp ±1 band" có hai giá trị trong tài liệu gốc (80% ở lộ trình tuần 2, 90% ở cổng chất lượng tầng 2). BRD dùng 80% là **mốc trung gian**, 90% là **cổng cuối**.

## 9. Giả định và ràng buộc

| # | Loại | Nội dung |
|---|---|---|
| A-1 | Giả định | Dùng API OpenAI-compatible qua OpenRouter, model mặc định `gpt-4o-mini`, embedding `text-embedding-3-small` (1536 chiều) |
| A-2 | Giả định | Giá token là giả định; cần kiểm tra trang giá OpenRouter khi triển khai |
| A-3 | Giả định | Phiên chuẩn 30 phút, khoảng 15 lượt, khoảng 72k token vào và 7.5k token ra |
| A-4 | Giả định | Chất lượng `text-embedding-3-small` với tiếng Việt xen thuật ngữ Anh **chưa được đo**; đo bằng golden set RAG ở Sprint 1 |
| A-5 | Giả định | Quy mô demo vài chục người dùng, khoảng 20 phiên đồng thời |
| C-1 | Ràng buộc thời gian | 8 tuần từ 12/10 đến 06/12/2026, feature freeze 06/12; Sprint 5 (07/12 đến 21/12) dành cho polish, test tích hợp, báo cáo |
| C-2 | Ràng buộc nhân lực | 1 AIE chính; golden set cần thêm 1 người gán nhãn độc lập |
| C-3 | Ràng buộc kỹ thuật | Constitution: ai-service stateless; `interview-service` sở hữu dữ liệu phiên; REST/HTTP giữa NestJS và ai-service; không agent framework; file code dưới 200 dòng |
| C-4 | Ràng buộc chất lượng | CI chạy lint, type check, test; không mock giả để qua CI; không commit secret |
| C-5 | Ràng buộc quy trình | GitHub Flow, PR vào `main` cần CI xanh và ≥ 1 approve |
| C-6 | Ràng buộc pháp lý | Dữ liệu CV gửi tới LLM provider ở nước ngoài; cần consent và đối chiếu quy định bảo vệ dữ liệu cá nhân |

## 10. Phụ thuộc

| Phụ thuộc | Bên | Cần khi | Ghi chú |
|---|---|---|---|
| Pattern TCP `application.getCvFile` và presigned URL | FSD (job-service) | Tuần 5 | Chưa tồn tại; ngoài ra phỏng vấn không CV |
| Migration `interview_db` (cột mới `plan`, `candidate_state`, `cv_profile`, `action`, `evaluation`...) | FSD | Tuần 5 | Cần FSD xác nhận |
| Relay SSE trong interview-service, `AiInterviewClient` mới | FSD | Tuần 4 đến 5 | Contract cần FSD duyệt |
| `knowledge_chunks` có dữ liệu Q&A Java và Node (kèm `topic_id`, `key_points`) | DE | Tuần 2 | Không có thì Evaluator chạy không RAG |
| `ai_db`, extension `vector`, DDL `knowledge_chunks` ghép vào init script | DE (T016) | Tuần 1 đến 2 | |
| Cấu hình APISIX cho SSE, route `/ai/*` | DE | Tuần 4 | Chưa kiểm chứng buffering |
| Topic catalog review, `resources` (link tài liệu học) | DE | Tuần 1 đến 2 | Đồng sở hữu |
| CI job Python | DE (T032) | Sớm | |
| Người gán nhãn golden set độc lập | Thành viên khác | Tuần 2, 7 | Khoảng 2 đến 3 giờ mỗi lần |
| Phê duyệt ADR-008 và amendment constitution IV, V | Cả team | Tuần 1 | Constitution đang ở trạng thái Proposed |

## 11. Rủi ro chính

Danh sách đầy đủ ở [design doc 11](../10-risks-and-8-week-roadmap.md).

| # | Rủi ro | Tác động | Giảm thiểu |
|---|---|---|---|
| R-1 | LLM **chấm dễ dãi** hoặc bịa căn cứ | Cao | Rubric có mốc, luật khắt khe, hậu kiểm bằng code, golden set có nhãn người |
| R-2 | Đáp án mẫu hoặc `key_points` **sai** làm sai điểm | Cao | Người thứ hai review; catalog có `key_concepts` đã duyệt |
| R-3 | **Độ trễ** vượt mục tiêu vì Evaluator và Interviewer nối tiếp. Số đo thật: một lần chat 150 đến 200 token ra mất khoảng 4 đến 5 giây qua OpenRouter | Cao | Output gọn, model nhỏ, đo từ tuần 4, phương án dự phòng |
| R-4 | **Prompt injection** qua CV và câu trả lời | Cao | Cô lập CV thô chỉ ở CV Parser, khối untrusted, hậu kiểm code, bộ test adversarial |
| R-5 | **Lộ dữ liệu cá nhân** (CV tới bên thứ ba, log) | Cao | Redact trước LLM, consent riêng, không log nội dung, chọn provider không lưu dữ liệu nếu có |
| R-6 | **Trễ tiến độ** với 1 AIE | TB | Thứ tự cắt phạm vi: RAG grounding, track Node, phase scenario đơn giản, streaming, gắn CV, tầng test 3 rút gọn |
| R-7 | **Lệch contract** với FSD | TB | Chốt contract tuần 4 bằng PR, mock client theo contract mới |
| R-8 | Streaming bị buffer qua APISIX hoặc relay | TB | Spike tuần 4; dự phòng trả JSON và UI hiển thị "đang gõ" |

## 12. Câu hỏi mở

1. Team có duyệt bốn vị trí (Java, Python, Node.js, AI Engineer) hay giữ MVP Java và Node.js?
2. Ai viết và duyệt ADR-008, amendment constitution IV (nội dung contract) và V (transcript, CV không vào `knowledge_chunks`)?
3. FSD xác nhận các cột mới của `interview_db` và pattern `application.getCvFile`?
4. Bucket CV ở job-service là private (cần presigned) hay public (`cvUrl` hiện ghi là URL MinIO)?
5. Streaming SSE qua APISIX và relay interview-service có buffer không? (kiểm chứng tuần 4)
6. Tài khoản OpenRouter có bật được chế độ không lưu dữ liệu (zero data retention) không?
7. Quota phiên mỗi ngày: giữ 5 hay đổi?
8. Quy định bảo vệ dữ liệu cá nhân hiện hành: nhóm cần tự đối chiếu văn bản (Nghị định 13/2023/NĐ-CP và luật mới có hiệu lực từ 01/01/2026 theo design doc, chưa được kiểm chứng ở đây).

## 13. Truy vết mục tiêu sang yêu cầu

| Mục tiêu | Yêu cầu nghiệp vụ |
|---|---|
| BO-1 | BR-01, 02, 03, 11 |
| BO-2 | BR-04 |
| BO-3 | BR-05, 06, 07, 12, 14 |
| BO-4 | BR-08 |
| BO-5 | BR-09, 10 |
| BO-6 | BR-13 |
| BO-7 | BR-14, 16 |
| BO-8 | BR-15 |
