# BRD — Business Requirements Document: AI Interview Service

| Mục | Giá trị |
|---|---|
| Phiên bản | 0.5 (Draft, chờ team review) |
| Ngày | 2026-10-19 |
| Owner | AIE |
| Reviewer | FSD, DE |
| Phạm vi | Phần AIE: `apps/ai-service` và phần tích hợp liên quan trong `interview-service` và giao diện web cho tính năng phỏng vấn kỹ thuật trực tiếp bằng AI |
| Tài liệu liên quan | [FR](02-functional-requirements.md) · [NFR](03-non-functional-requirements.md) · [Kiến trúc L2](../11-architecture-l2-containers.md) · [Design doc](../README.md) · [ADR-008](../../architecture/adr/adr-008-evaluator-per-turn-orchestrator.md) |

> **Quy ước nguồn.** Yêu cầu bám các tài liệu đã có trong repo (design doc `docs/ai-service`, constitution, sprint plan) và các quyết định phạm vi ở mục "Lịch sử thay đổi". Chỗ nào là con số giả định hoặc đề xuất chưa được team xác nhận thì ghi rõ **(giả định)** hoặc **(đề xuất)**. Các con số đó chưa được đo bằng dữ liệu thật.

## 0. Lịch sử thay đổi

| Phiên bản | Ngày | Thay đổi |
|---|---|---|
| 0.1 | 2026-10-12 | Bản đầu, dựa trên design doc phỏng vấn dạng chat văn bản, 15 đến 45 phút |
| 0.2 | 2026-10-12 | Đổi phạm vi theo yêu cầu của owner (chưa được FSD và DE xác nhận):** (1) phỏng vấn kỹ thuật là **hội thoại trực tiếp giống cuộc họp trực tuyến (kiểu Google Meet), đảm bảo real-time, thời lượng 15 đến 20 phút**; (2) **voice và video đưa vào phạm vi**, **nhận diện cảm xúc hoãn sang giai đoạn sau**; (3) **cho phép dùng agent framework, fine-tune model, agent tự học từ dữ liệu, và thêm giao diện web vào phạm vi** |
| 0.3 | 2026-10-12 | **Chốt các câu hỏi mở theo trả lời của owner:** phân kỳ theo đề xuất (giai đoạn 1 là **chat**, voice gắn sau nếu ổn); yêu cầu **đồng ý trước** khi dùng giọng nói và hình ảnh; độ trễ **cải thiện dần**; giao diện kiểu cuộc họp, **video ứng viên chỉ hiển thị**, **AI là ảnh**; dùng **hạ tầng voice-agent có sẵn**; thêm mục gợi ý xử lý mâu thuẫn với constitution |
| 0.4 | 2026-10-19 | **Đồng bộ với `main`:** quyết định của team ngày 15/10 (voice là Stretch do DE sở hữu theo kiểu TTS + STT bấm-để-nói, JD là đầu vào của Planner, phiên luyện tập riêng tư, DE sở hữu đường ghi RAG), 6 track theo đề xuất của DE, và các mặc định Q1–Q6 của [kế hoạch triển khai](../../../plans/20261019-1100-ai-interview-brd-implementation/plan.md). **Các mặc định này chờ owner xác nhận** |
| **0.5** | 2026-10-19 | **Owner xác nhận:** diễn giải A-6 (video ứng viên chỉ hiển thị = ứng viên tự thấy mình như khung tự xem, không gửi lên server, không lưu) và **chấp nhận đề xuất xử lý mâu thuẫn với constitution** (mục 0.3). D7–D12 vẫn là mặc định chờ xác nhận |

### 0.1 Tác động của thay đổi v0.2 tới tài liệu và quyết định hiện có

Thay đổi này **mâu thuẫn** với nhiều chỗ trong repo. BRD chỉ ghi nhận; sửa từng tài liệu cần team quyết định trước (xem mục 12).

| Tài liệu hoặc quyết định | Nội dung hiện tại | Mâu thuẫn |
|---|---|---|
| Design doc README, giả định A8 và mục 1.4 | Kênh chat văn bản; voice, video ngoài phạm vi; không agent framework; không fine-tune; không giao diện web | Đổi hoàn toàn |
| Design doc 04 (phase), 05, 08 | Phiên 15 đến 45 phút (mặc định 30), 5 đến 6 topic, ≈ 15 lượt, 24 lượt tối đa | Thời lượng mới 15 đến 20 phút: phải tính lại số topic, số lượt, chi phí |
| Design doc 06 và 08 | Giao tiếp REST và SSE văn bản; độ trễ tới token đầu ≈ 3.6 s (giả định) | Hội thoại giọng nói real-time cần đường truyền âm thanh thời gian thực và độ trễ thấp hơn nhiều; chưa tính STT và TTS |
| Constitution II, III, IV | NestJS ↔ ai-service dùng REST/HTTP (ADR-003); ai-service stateless | Luồng media real-time thường cần kết nối bền, có trạng thái. Cần ADR và amendment |
| Constitution VII và ADR-008 | "Không agent framework", state machine tự viết | Nay được phép dùng framework. Cần amendment và cập nhật ADR-008 |
| Constitution V và NFR-AI-PRIV04 | Transcript, CV không bao giờ vào `knowledge_chunks` hay dữ liệu pipeline | "Agent tự học từ dữ liệu" và fine-tune cần dữ liệu phiên. Phải có consent, ẩn danh và sửa quy tắc |
| Sprint plan, lộ trình 8 tuần | 8 tuần từ 12/10 đến 06/12, 1 AIE, giao diện web thuộc FSD | Phạm vi tăng đáng kể, thời gian không đổi (xem R-6) |
| FR, NFR, kiến trúc L2 (bản v0.1) | Viết cho chat văn bản 15 đến 45 phút | Cần viết lại các phần liên quan (xem banner ở đầu từng tài liệu) |

### 0.2 Quyết định đã chốt (v0.3, v0.4)

| # | Chủ đề | Quyết định | Câu hỏi mở liên quan |
|---|---|---|---|
| D1 | Phân kỳ và rủi ro tiến độ (R-6) | Theo đề xuất ở mục 4.3 | 17 (đã trả lời) |
| D2 | Giai đoạn đầu | **Chat văn bản trước** trong giao diện kiểu cuộc họp; nếu ổn mới gắn thêm voice | 11, 16, 17 (đã trả lời) |
| D3 | Giọng nói và hình ảnh | **Phải xin ứng viên đồng ý trước** khi bật | 19 (một phần) |
| D4 | Độ trễ | Cho phép **cải thiện dần**, không là điều kiện chặn giai đoạn đầu | 9 (một phần) |
| D5 | "Giống Google Meet" | Giống ở **giao diện họp**. Video ứng viên **chỉ hiển thị**. **AI là ảnh** (không avatar động). Diễn giải A-6 **đã xác nhận 19/10** | 10 (đã trả lời) |
| D6 | Hạ tầng real-time | **Dùng hạ tầng voice-agent có sẵn**, không tự xây | 13 (một phần: chưa chọn cụ thể) |
| D7 *(v0.4)* | JD | **JD của job trong application là đầu vào của Planner** (`jd_profile`), **không vào RAG**; báo cáo có khối `requirements`. Thay mục "ngoài phạm vi" của v0.3 | 17 (mới) |
| D8 *(v0.4)* | Voice | **Tùy chọn A theo `main`:** Stretch S4 do DE sở hữu: TTS đọc `done.question`, STT bấm-để-nói gửi transcript qua `/answer`, lưu bản STT gốc và bản sửa, **không lưu audio**, ai-service không đổi. Tùy chọn B (voice-gateway realtime, D6) **ra khỏi kế hoạch mặc định** | 13, 20 |
| D9 *(v0.4)* | Riêng tư | Phiên luyện tập **riêng tư**, Employer không xem (khớp BRU-10) | — |
| D10 *(v0.4)* | Track | **6 track** (thêm `frontend_react`, `devops_engineer`, 14 topic AI): 90 topic, đã triển khai ở nhánh `thang/catalog-6-tracks` (xếp chồng trên nhánh tài liệu) | 1 |
| D11 *(v0.4)* | RAG | **DE sở hữu đường ghi** (load, chunk, embed, upsert), **AIE sở hữu đường đọc** | — |
| D12 *(v0.4)* | Thời lượng | 15 đến 20 phút, mặc định 20, turn cap 16 *(đề xuất, chờ team)* | 12 |

*D7–D12 là mặc định của kế hoạch triển khai, bám quyết định đã nằm trên `main`; chờ owner xác nhận.*

*Diễn giải A-6 **đã được owner xác nhận (2026-10-19)**:* "video ứng viên chỉ hiển thị" nghĩa là **ứng viên thấy chính mình** như khung tự xem trong một cuộc họp; video **không gửi lên server và không lưu**.

### 0.3 Đề xuất xử lý mâu thuẫn với constitution

Phần 0.1 liệt kê các mâu thuẫn. Với quyết định D2 và D6, **phần lớn mâu thuẫn tránh được** nếu tách lớp giọng nói thành một container riêng. Các đề xuất dưới đây **đã được owner chấp nhận (2026-10-19)**; chúng sẽ được gộp vào PR ratify constitution (bản nháp ở `plans/20261019-1100-ai-interview-brd-implementation/reports/constitution-amendment-draft.md`), team duyệt khi ratify.

| Nguyên tắc | Mâu thuẫn | Gợi ý | Lý do |
|---|---|---|---|
| **II, III** (transport) và **IV** (ai-service stateless, REST) | Hội thoại real-time cần kết nối bền | **Giữ ai-service stateless, chỉ REST và SSE.** Thêm một container **voice-gateway** (chạy hạ tầng voice-agent) nằm giữa trình duyệt và interview-service: nhận âm thanh, nhận dạng thành chữ, gọi **đúng contract hiện có**, đọc câu hỏi trả về bằng TTS. Kết nối bền chỉ nằm ở voice-gateway. Amendment II chỉ cần thêm một dòng cho kênh media giữa trình duyệt và voice-gateway, kèm ADR chọn hạ tầng | Không phải sửa ai-service, interview-service và ADR-003, ADR-004; chat và voice dùng chung một đường xử lý nên dễ đo và dễ test |
| **VII** (không agent framework) | Nay được phép dùng framework | Sửa thành: *framework được phép khi có ADR nêu lý do và đã thử spike*. **Khuyến nghị:** dùng framework cho **lớp giọng nói và media**; giữ **orchestrator, policy, tổng hợp điểm là code của nhóm**, vì đó là phần có unit test và là bằng chứng của đồ án | Framework thay chỗ phần khó (VAD, STT, TTS, truyền âm thanh), không thay phần logic cần kiểm chứng được |
| **V** (không dữ liệu phiên vào kho tri thức) | "Học từ dữ liệu" và fine-tune cần dữ liệu phiên | **Giữ nguyên quy tắc cho `knowledge_chunks`.** Thêm đường riêng: dữ liệu huấn luyện chỉ lấy từ phiên có cờ `learning_consent_at`, đã ẩn danh, lưu **ngoài** `knowledge_chunks`, tách khỏi golden set. **Không làm trong giai đoạn 1 và 2**; chỉ thêm sớm cột cờ consent (nullable) để sau này không phải migration | Giữ lời hứa riêng tư mặc định, mở cửa có kiểm soát khi cần |
| **ADR-008** | Ghi "không agent framework", mẫu 30 phút | Giữ ADR-008 cho phần orchestrator; sửa dòng framework và thời lượng; viết **ADR-009** cho voice-gateway và phân kỳ | Một ADR cho một quyết định |
| **Quy trình** | Constitution đang ở trạng thái Proposed, chưa ratify | **Gộp các sửa đổi trên vào chính PR ratify constitution** thay vì amend sau khi ratify (amend cần 2/3 thành viên, gồm owner workstream bị ảnh hưởng) | Rẻ hơn nhiều so với amend về sau |

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
| P6 *(mới)* | Phỏng vấn thật diễn ra **bằng lời nói, trực tiếp, dưới áp lực thời gian**. Luyện bằng gõ chữ không rèn được kỹ năng diễn đạt bằng lời | Quen trả lời bằng văn bản nhưng lúng túng khi phải nói |

## 3. Mục tiêu kinh doanh

| ID | Mục tiêu | Giải quyết | Thước đo thành công |
|---|---|---|---|
| BO-1 | Mô phỏng một buổi phỏng vấn kỹ thuật **gần thực tế**: hội thoại trực tiếp, bám vào CV thật của ứng viên | P1, P3, P6 | Câu hỏi intro bám dự án trong CV khi có CV; judge LLM chấm độ tự nhiên ≥ 4.0/5 (đề xuất) |
| BO-2 | Hệ thống **thích ứng** sau mỗi câu trả lời (hỏi sâu, gợi ý, hạ hoặc tăng độ khó, đổi chủ đề) | P2 | Quỹ đạo độ khó đúng chiều ở ≥ 80% phiên giả lập (đề xuất) |
| BO-3 | Chấm điểm **khắt khe, có căn cứ, nhất quán** theo chuẩn của level | P4 | Khớp người chấm ±1 band ≥ 90%, độ lệch khoan dung trong [−0.3, +0.3] (đề xuất) |
| BO-4 | Báo cáo cuối buổi đủ cụ thể để ứng viên biết **học gì tiếp** | P1 | Recall lỗ hổng ≥ 70%, không có điểm mạnh sai (đề xuất) |
| BO-5 | **Bảo vệ** dữ liệu cá nhân (CV, **giọng nói, hình ảnh**) và chống thao túng điểm | P5 | 0 PII trong log và đầu vào LLM; injection không làm tăng điểm (100% bộ test adversarial); có consent trước khi bật micro hoặc camera |
| BO-6 | Vận hành với **chi phí thấp** trong khả năng của đồ án | Ràng buộc | Cảnh báo khi một phiên vượt ngưỡng chi phí. **Ước tính cũ ≈ $0.015/phiên chỉ tính LLM văn bản, 30 phút; cần tính lại** khi có STT, TTS và thời lượng 15 đến 20 phút |
| BO-7 | **Demo chạy được end-to-end** trước hạn đồ án, đủ số liệu để đưa vào báo cáo | Ràng buộc | Feature freeze 06/12/2026, demo trên staging; bảng chỉ số đánh giá đưa vào báo cáo. **Có rủi ro cao với phạm vi mới (R-6)** |
| BO-8 | Mở rộng thêm **vị trí phỏng vấn mới** mà không đổi kiến trúc | Tương lai | Thêm vị trí = thêm một file catalog, test tự nhận |
| BO-9 *(mới)* | Trải nghiệm **hội thoại thời gian thực** như cuộc họp video: ứng viên nói, AI nghe và đáp lại bằng giọng nói với độ trễ đủ tự nhiên | P6 | Độ trễ phản hồi và độ ổn định phiên (mục 8); ngưỡng cần chốt |
| BO-10 *(mới)* | Cải thiện chất lượng agent bằng **dữ liệu có kiểm soát** (fine-tune, học từ dữ liệu) | P4 | Đo trên golden set: không làm giảm chất lượng; mức cải thiện cần xác định. Ưu tiên thấp (Could) |
| BO-11 *(mới v0.4)* | **Luyện tập theo job cụ thể:** Planner dùng JD của job mà ứng viên chọn; báo cáo cho biết đã đánh giá bao nhiêu yêu cầu của job | P1 | Báo cáo hiển thị "đã đánh giá X/Y yêu cầu", không kết luận tuyển hay không tuyển |

## 4. Phạm vi

### 4.1 Trong phạm vi

- Phỏng vấn kỹ thuật **trực tiếp trong giao diện giống cuộc họp trực tuyến (kiểu Google Meet)**, ngôn ngữ tiếng Việt giữ thuật ngữ tiếng Anh, **thời lượng 15 đến 20 phút**. **Giai đoạn 1: chat văn bản** trong giao diện họp. **Giai đoạn 2 (nếu giai đoạn 1 ổn): hội thoại giọng nói** (ứng viên nói, AI đáp lại bằng giọng nói).
- **Voice (Stretch, giai đoạn 2; theo `main` là tùy chọn A, DE sở hữu)**: TTS đọc câu hỏi, STT bấm-để-nói gửi transcript qua `/answer`; lưu bản STT gốc và bản sửa, không lưu audio. Chỉ bật sau khi ứng viên đồng ý. Hội thoại realtime (tùy chọn B) không nằm trong kế hoạch mặc định.
- **Hình ảnh trong phòng họp**: khung **AI là ảnh tĩnh**; khung **video ứng viên chỉ hiển thị** (ứng viên thấy chính mình), không gửi lên server, không lưu. Chỉ bật camera sau khi ứng viên đồng ý.
- **Giao diện web** (`apps/web`) cho toàn bộ luồng: chọn vị trí và level, gắn CV và consent, phòng phỏng vấn kiểu cuộc họp, trang báo cáo. Người thực hiện cần xác nhận (câu hỏi mở 16).
- Agent framework: **không cần cho chat**; chỉ cân nhắc cho lớp giọng nói nếu chọn tùy chọn B, qua ADR (mục 0.3). Orchestrator là code của nhóm.
- **Fine-tune và agent tự học từ dữ liệu: hoãn**, không nằm trong kế hoạch 8 tuần (giai đoạn 3). Chỉ chuẩn bị tiền đề (cờ consent), điều kiện ở BRU-16.
- Vị trí (track) theo topic catalog: **6 track** `java_backend`, `python_backend`, `nodejs_backend`, `ai_engineer`, `frontend_react`, `devops_engineer` (90 topic, theo đề xuất của DE trong spec 005; đã triển khai ở nhánh `thang/catalog-6-tracks`). *Design doc gốc ghi MVP là Java và Node.js.*
- Level: Fresher, Junior, Middle, Senior.
- Dùng lại **CV đã nộp ở job-service** (PDF hoặc DOCX), khuyến nghị nhưng không bắt buộc.
- Sáu vai trò agent: CV Parser, **JD Parser**, Planner, Evaluator, Interviewer, Reporter.
- **Luyện tập theo job cụ thể:** JD của job trong application mà ứng viên chọn là đầu vào của Planner (không vào RAG); báo cáo có khối `requirements`.
- Báo cáo cuối buổi: điểm theo phần và theo tiêu chí, điểm mạnh, cần cải thiện, lộ trình học, điểm và nhận xét từng câu.
- Knowledge base RAG gồm `interview_qa` và `textbook`.
- Chống prompt injection từ CV, câu trả lời (kể cả lời nói qua STT) và nội dung RAG; redact PII trước khi gửi LLM.
- Xử lý lỗi (LLM, STT, TTS, kết nối media) bằng retry giới hạn và fallback.
- Bộ đánh giá chất lượng: golden set cho Evaluator, ứng viên giả lập chạy end-to-end.
- Ghi nhận token, độ trễ và chi phí theo phiên.

*Đã chốt:* chat văn bản là giai đoạn đầu, và nên được giữ làm phương án dự phòng khi voice không dùng được (câu hỏi mở 11).

### 4.2 Ngoài phạm vi (hiện tại)

| Hạng mục | Lý do hoặc hướng sau này |
|---|---|
| **Nhận diện cảm xúc** (từ khuôn mặt, giọng điệu) | **Hoãn sang giai đoạn sau** theo quyết định của owner. Trong lúc này, cảm xúc **không được dùng** để chấm điểm hay nhận xét (BRU-15) |
| Hội thoại giọng nói realtime (STT streaming, ngắt lời, voice-gateway) | `main` loại khỏi phạm vi (TTFT ≈ 3.6 s, turn-taking phải thiết kế lại); chỉ làm nếu owner xác nhận tùy chọn B |
| Chấm cách nói (tốc độ, ngập ngừng, tự tin) | Tín hiệu yếu, nguy cơ thiên vị theo giọng vùng miền và người nói không phải tiếng mẹ đẻ |
| Embed JD vào RAG (truy hồi theo JD) | JD chỉ vào Planner dạng `jd_profile`; index JD vào `ai_db` (S2-DE-3) là Stretch của DE, không agent nào dùng |
| Live coding, chạy code ứng viên | Cần sandbox |
| OCR CV dạng ảnh scan | Báo lỗi `cv_unreadable`, cho phép phỏng vấn không CV |
| Vị trí ngoài các track trên (Frontend, DevOps, Data, QA, Mobile) | Kiến trúc hỗ trợ, thêm bằng catalog, không làm trong 8 tuần |
| Employer xem hoặc nhận kết quả luyện tập của ứng viên | Quyết định 15/10: phiên luyện tập luôn riêng tư. Muốn chia sẻ cần consent từng nhà tuyển dụng, chống gian lận, đánh giá công bằng; để hướng phát triển |
| Chống gian lận (copy-paste, tra cứu) | Stretch S5-8 |
| Phỏng vấn nhiều người cùng lúc (nhiều ứng viên trong một phòng) | Không có yêu cầu |
| Tiếp tục phiên trên nhiều thiết bị cùng lúc | Một phiên một client |

### 4.3 Phân kỳ (đã chốt theo đề xuất của AIE, kèm quyết định D2)

Phạm vi mới lớn hơn nhiều so với khả năng của 8 tuần và 1 AIE (R-6). Team chọn chia giai đoạn và cắt từ dưới lên.

| Giai đoạn | Nội dung | Ưu tiên | Lý do |
|---|---|---|---|
| **1. Chat trong phòng họp** | Phỏng vấn **chat văn bản** 15 đến 20 phút trong giao diện kiểu cuộc họp (khung AI là ảnh, khung video ứng viên chỉ hiển thị, khung hội thoại, đồng hồ, trạng thái AI); báo cáo cuối buổi; consent trước khi bật camera | Must | Tái dùng orchestrator, Evaluator, policy, Reporter đã thiết kế và mock đã có; đủ để chứng minh giá trị |
| **2. Voice (Stretch)** | **Tùy chọn A (mặc định, theo `main`):** TTS đọc câu hỏi, STT bấm-để-nói; DE sở hữu (feature 015, S4-DE-5); ai-service không đổi. Tùy chọn B (voice-gateway realtime) chỉ khi owner xác nhận, cần ADR-009 | Could (chỉ khi qua gate 22/11) | Phần khó nhất; làm sau khi lõi chạy; gate ở plan Phase 08 |
| **3. Học từ dữ liệu** | Fine-tune hoặc cơ chế học có kiểm soát | Won't trong 8 tuần (hoãn) | Cần dữ liệu có consent và golden set để đo; hiện chưa có cả hai |
| **Hoãn** | Nhận diện cảm xúc | Won't (lúc này) | Theo quyết định của owner |

Độ trễ hội thoại được **cải thiện dần** (D4): giai đoạn 1 không cần đạt chỉ tiêu real-time của voice.

## 5. Các bên liên quan

| Bên | Vai trò | Quan tâm chính |
|---|---|---|
| **Candidate** | Người dùng chính | Phỏng vấn tự nhiên như nói chuyện thật, phản hồi hữu ích và công bằng, dữ liệu CV, giọng nói và hình ảnh được bảo vệ |
| **Employer** | Người dùng nền tảng | Không dùng phiên luyện tập trong MVP; có thể xem kết quả khi có consent (tương lai) |
| **Admin** | Quản trị | Quản lý danh mục và bộ câu hỏi (topic catalog và Q&A hiện là file trong repo, do AIE và DE sở hữu) |
| **AIE** (chủ phần này) | Thiết kế, xây dựng ai-service và pipeline giọng nói | Chất lượng agent, độ trễ real-time, chi phí, tiến độ |
| **FSD** | Sở hữu interview-service, job-service, và (đề xuất) giao diện web | Contract ổn định, migration `interview_db`, kênh real-time, giao diện phòng phỏng vấn |
| **DE** | Hạ tầng và pipeline dữ liệu | Dữ liệu `knowledge_chunks`, APISIX, hạ tầng media real-time nếu cần, CI |
| **Giảng viên và hội đồng đồ án** | Đánh giá | Demo chạy được, số liệu đánh giá, đối chiếu tuân thủ pháp lý dữ liệu cá nhân |

## 6. Yêu cầu nghiệp vụ (BR)

Ưu tiên theo MoSCoW. Cột "FR" trỏ sang [tài liệu FR](02-functional-requirements.md); **BR-17 trở đi chưa có FR** (xem mục 12). BR in nghiêng là đã đổi so với v0.1.

| ID | Yêu cầu nghiệp vụ | Ưu tiên | Mục tiêu | FR chính |
|---|---|---|---|---|
| BR-01 | *Hệ thống cho phép ứng viên chọn **vị trí** và **level** rồi thực hiện một buổi phỏng vấn kỹ thuật dưới dạng **hội thoại trực tiếp thời gian thực*** | Must | BO-1, BO-9 | FR-AI-001..003, 037, 039 (cần viết lại cho voice) |
| BR-02 | Câu hỏi phải **bám vào CV** của ứng viên khi có CV hợp lệ; không có CV vẫn phỏng vấn được | Must | BO-1 | FR-AI-010..015, 020 |
| BR-03 | *Mỗi buổi gồm các giai đoạn cố định (giới thiệu và dự án, kiến thức chuyên môn, tình huống, kết thúc) với số chủ đề phù hợp level **và thời lượng 15 đến 20 phút*** | Must | BO-1 | FR-AI-003, 020, 036 (cần tính lại số topic) |
| BR-04 | Hệ thống **thích ứng** độ khó và hành động hỏi dựa trên chất lượng câu trả lời, trong giới hạn cứng về số lượt và thời gian | Must | BO-2 | FR-AI-033..036 |
| BR-05 | Mỗi câu trả lời được chấm theo **4 tiêu chí** so với chuẩn level; điểm có căn cứ trích dẫn từ câu trả lời (*bản ghi chép lời nói*) | Must | BO-3 | FR-AI-030..032 |
| BR-06 | **Điểm tổng hợp do code tính**, không do LLM tự cộng; nhận xét văn bản không được sửa điểm | Must | BO-3 | FR-AI-050..052 |
| BR-07 | Ứng viên **không thấy điểm hay đáp án giữa buổi**; chỉ nhận báo cáo sau khi kết thúc | Must | BO-3 | FR-AI-037, 039 |
| BR-08 | Báo cáo cuối buổi gồm điểm, điểm mạnh, cần cải thiện, lộ trình học có dẫn chứng, điểm và nhận xét từng câu | Must | BO-4 | FR-AI-050..055 |
| BR-09 | Hệ thống **chống thao túng điểm**: chỉ dẫn nhúng trong CV hoặc trong câu trả lời (*kể cả lời nói*) không làm tăng điểm | Must | BO-5 | FR-AI-012, 030..032 |
| BR-10 | Thông tin cá nhân trong CV được **che trước khi gửi LLM** bên thứ ba; transcript và CV không bao giờ vào kho dữ liệu RAG (*trừ khi có quy tắc khác cho mục học từ dữ liệu, xem BRU-16*) | Must | BO-5 | FR-AI-011, 060 |
| BR-11 | *Buổi phỏng vấn **không chết** khi LLM chậm hoặc lỗi, **hoặc khi STT, TTS, kết nối media lỗi**: có retry giới hạn và phương án thay thế* | Must | BO-1, BO-9 | FR-AI-070..073 (chưa phủ STT, TTS) |
| BR-12 | Câu hỏi và nhận xét dựa trên **kiến thức tham chiếu** (Q&A mẫu, tài liệu) để giảm chấm sai và bịa | Should | BO-3 | FR-AI-060..064 |
| BR-13 | *Chi phí và độ trễ của mỗi phiên (**gồm STT, TTS, media**) được **đo và lưu** để kiểm soát* | Should | BO-6 | FR-AI-080 |
| BR-14 | Chất lượng agent được **đo lặp lại được** bằng golden set và ứng viên giả lập, làm bằng chứng cho báo cáo đồ án | Must | BO-3, BO-7 | FR-AI-082 |
| BR-15 | Thêm **vị trí phỏng vấn mới** chỉ cần bổ sung dữ liệu catalog, không sửa code điều phối | Should | BO-8 | FR-AI-002 |
| BR-16 | Có **môi trường mock** để FSD và FE tích hợp độc lập trước khi AI thật sẵn sàng | Must | BO-7 | FR-AI-083, 090 |
| **BR-17** | **Hội thoại giọng nói hai chiều thời gian thực:** ứng viên nói, hệ thống nhận dạng (tiếng Việt xen thuật ngữ Anh), AI đáp lại bằng giọng nói, với độ trễ đủ tự nhiên (cải thiện dần). Dùng hạ tầng voice-agent có sẵn. Chat là dự phòng | Could (tùy chọn B; kế hoạch mặc định theo tùy chọn A, xem BR-24) | BO-1, BO-9 | Chưa có |
| **BR-24** *(v0.4)* | **Voice kiểu bấm-để-nói (tùy chọn A, theo `main`):** TTS đọc câu hỏi; STT bấm-để-nói, ứng viên sửa được transcript trước khi gửi; lưu bản STT gốc và bản sửa; không lưu audio | Could (Stretch S4, DE sở hữu) | BO-9 | FR-AI-125, 128, 129 (phần AIE) |
| **BR-18** | **Phòng phỏng vấn giao diện kiểu cuộc họp:** khung AI là ảnh tĩnh, khung **video ứng viên chỉ hiển thị** (ứng viên thấy chính mình, không gửi đi, không lưu), khung hội thoại, trạng thái AI, đồng hồ thời gian | Must (giai đoạn 1; video tự xem là Should) | BO-9 | Chưa có |
| **BR-19** | **Thời lượng 15 đến 20 phút**, kết thúc đúng giờ; thời lượng mặc định cần chốt | Must | BO-1, BO-9 | Chưa có (sửa FR-AI-003, 035, 036) |
| **BR-20** | **Giao diện web** cho toàn bộ luồng: chọn vị trí và level, gắn CV và consent, kiểm tra camera (và micro ở giai đoạn 2), phòng phỏng vấn, trang báo cáo | Must (giai đoạn 1) | BO-7, BO-9 | Chưa có (thuộc FSD, đề xuất) |
| **BR-21** | **Cải thiện chất lượng bằng dữ liệu có kiểm soát:** fine-tune model hoặc cơ chế agent học từ dữ liệu, chỉ dùng dữ liệu có consent, ẩn danh, tách khỏi golden set; mọi thay đổi phải được đo và không làm giảm chất lượng | Won't trong 8 tuần (hoãn) | BO-10 | Chưa có |
| **BR-22** | **Bảo vệ dữ liệu âm thanh và hình ảnh:** **xin ứng viên đồng ý trước** khi bật camera (giai đoạn 1) hoặc micro (giai đoạn 2); nói rõ có ghi lại hay không; chỉ gửi tới bên thứ ba đã khai báo (STT, TTS, LLM); ứng viên từ chối vẫn phỏng vấn được bằng chat | Must | BO-5 | Chưa có |
| **BR-23** *(v0.4)* | **Luyện tập theo job cụ thể:** từ application ứng viên chọn, hệ thống lấy JD, trích yêu cầu (`jd_profile`) cho Planner; báo cáo có khối `requirements` mỗi yêu cầu `assessed`, `not_assessed` hoặc `out_of_catalog`; "chưa hỏi" không bị coi là "yếu"; không kết luận tuyển hay không tuyển | Must | BO-11 | FR-AI-016, 017, 023, 056 |

## 7. Quy tắc nghiệp vụ

| ID | Quy tắc | Nguồn |
|---|---|---|
| BRU-01 | **Level là nguồn sự thật.** CV chỉ là lời tự khai: ứng viên chọn Junior mà CV ghi 6 năm thì vẫn phỏng vấn theo chuẩn Junior | design 01 §2.1 |
| BRU-02 | Điểm là band tương đối với chuẩn level: cùng câu trả lời, ứng viên Senior nhận band thấp hơn Junior | design 05 §6.2 |
| BRU-03 | Mỗi topic có giới hạn follow-up (2 hoặc 3 theo level), tối đa 1 gợi ý, tối đa 1 lần hỏi lại. **Tổng tối đa 24 lượt mỗi phiên là con số cho phiên 30 phút; cần tính lại cho 15 đến 20 phút** | design 03 §4.3 |
| BRU-04 | Hết giờ thì sang kết thúc; quá hạn cứng (thời lượng + 3 phút) thì kết thúc ngay | design 03 §4.4 |
| BRU-05 | Lượt hỏi lại (clarify), lượt lỗi chấm (degraded) và lượt kết thúc không tính điểm | design 05 §6.3 |
| BRU-06 | Trọng số giai đoạn theo level: Senior nặng phần tình huống, Fresher nặng kiến thức nền | design 05 §6.3 |
| BRU-07 | Kết luận so với chuẩn level: ≥ 8.5 vượt kỳ vọng, 7.0 đến 8.4 đạt, 5.0 đến 6.9 gần đạt, dưới 5.0 chưa đạt. *(giả định, chỉnh sau khi chạy ứng viên giả lập)* | design 05 §6.3 |
| BRU-08 | Báo cáo hiển thị mức tin cậy; mức thấp phải có cảnh báo; luôn kèm lời nhắc điểm do AI chấm, mang tính tham khảo. **Với voice, mức tin cậy phải xét thêm chất lượng nhận dạng giọng nói** *(đề xuất)* | design 05 §6.4, §6.5 |
| BRU-09 | Dùng CV nộp để ứng tuyển cho luyện phỏng vấn là **mục đích khác**, cần ứng viên đồng ý riêng | design 01 §2.2, 10 §11 |
| BRU-10 | Employer **không** xem phiên luyện tập của ứng viên trong MVP | design README A12, quyết định 15/10 |
| BRU-11 | Quota mặc định 5 phiên mỗi ngày mỗi ứng viên *(đề xuất)* | design 10 |
| BRU-12 | Câu trả lời chỉ gồm cụm kiểu "không biết", "chưa học" (tối đa 6 từ) được xem là không biết và không cần Evaluator; có nội dung khác thì vẫn chấm | design 03 §4.5 |
| **BRU-13** | Thời lượng phiên nằm trong khoảng **15 đến 20 phút**. Giá trị mặc định chưa chốt | Yêu cầu v0.2 |
| **BRU-14** | **Phải có sự đồng ý của ứng viên trước khi bật giọng nói hoặc hình ảnh** (consent riêng cho camera, và cho micro ở giai đoạn 2). Từ chối hoặc tắt vẫn phỏng vấn được bằng chat | Quyết định D3, BR-22 |
| **BRU-15** | **Không dùng cảm xúc, biểu cảm khuôn mặt hay giọng điệu** để chấm điểm hay viết nhận xét trong giai đoạn này (nhận diện cảm xúc đã hoãn) | Yêu cầu v0.2 |
| **BRU-16** | Dữ liệu dùng để **fine-tune hoặc để agent học** phải: có consent riêng, đã ẩn danh, **tách khỏi golden set**, và nếu lấy từ transcript hay CV thì phải sửa quy tắc "không vào `knowledge_chunks`" bằng amendment có chủ đích | Yêu cầu v0.2, constitution V |
| **BRU-17** | **Video ứng viên chỉ hiển thị cục bộ**, không gửi lên server, không lưu (diễn giải A-6). Âm thanh (giai đoạn 2) chỉ gửi tới nhà cung cấp STT đã khai báo và **không ghi lại** trừ khi ứng viên đồng ý rõ ràng và có thời hạn lưu *(đề xuất)* | Quyết định D5, BR-22 |
| **BRU-18** *(v0.4)* | **JD là dữ liệu không tin cậy** như CV: đi qua parser riêng, quét injection, chỉ agent sau nhận `jd_profile` đã qua schema; redact thông tin liên hệ trước khi gửi LLM | A11 |
| **BRU-19** *(v0.4)* | Trong báo cáo theo JD, yêu cầu **chưa được hỏi** hiển thị `not_assessed`, **không** bị coi là yếu | A11, S3-AIE-6 |
| **BRU-20** *(v0.4)* | Cho **sửa transcript STT tự do** (chỉ vì phiên riêng tư); lưu cả bản gốc và bản sửa; tỉ lệ từ bị sửa là số đo độ chính xác STT; không lưu audio | quyết định 15/10 |

## 8. Tiêu chí thành công

Ngưỡng chất lượng lấy từ [design doc 10](../09-agent-quality-evaluation.md); toàn bộ là **(đề xuất)**, chỉnh sau lần chạy đầu. Đo bằng ba tầng test: unit (CI), golden set Evaluator, ứng viên giả lập end-to-end.

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
| **Hội thoại real-time** *(mới; chỉ áp dụng nếu chọn tùy chọn B; cải thiện dần, không chặn giai đoạn 1)* | Độ trễ phản hồi: từ lúc ứng viên dứt lời tới lúc AI bắt đầu nói | **Chưa chốt.** Đề xuất P50 ≤ 2 s, P95 ≤ 4 s *(đề xuất, chưa đo)*. Lưu ý: ước tính đường nóng chỉ văn bản đã là ≈ 3.6 s tới token đầu, chưa gồm STT và TTS, nên mục tiêu này đòi hỏi đổi thiết kế (xem R-3) |
| | Chất lượng nhận dạng giọng nói tiếng Việt xen thuật ngữ Anh | **Cần đo thử các nhà cung cấp** rồi mới đặt ngưỡng; hiện chưa có số liệu |
| | Phiên hoàn thành trọn thời lượng không đứt kết nối | ≥ 90% *(đề xuất)* |
| | Phiên kết thúc trong thời lượng + 3 phút | 100% (giới hạn cứng bằng code) |
| Vận hành | Chi phí mỗi phiên | **Cần tính lại**: ước tính cũ ≈ $0.015 chỉ cho LLM văn bản 30 phút; chưa gồm STT, TTS, media; cảnh báo > $0.10/phiên |

Ghi chú: mốc "khớp ±1 band" có hai giá trị trong tài liệu gốc (80% ở lộ trình tuần 2, 90% ở cổng chất lượng tầng 2). BRD dùng 80% là **mốc trung gian**, 90% là **cổng cuối**. Chỉ tiêu "thời gian tới token đầu tiên P50 ≤ 3.5 s, P95 ≤ 6 s" của v0.1 **không còn đủ** cho hội thoại giọng nói và sẽ được thay bằng chỉ tiêu độ trễ phản hồi ở trên khi chốt.

## 9. Giả định và ràng buộc

| # | Loại | Nội dung |
|---|---|---|
| A-1 | Giả định | Dùng API OpenAI-compatible qua OpenRouter, model mặc định `gpt-4o-mini`, embedding `text-embedding-3-small` (1536 chiều) |
| A-2 | Giả định | Giá token là giả định; cần kiểm tra trang giá OpenRouter khi triển khai |
| A-3 | Giả định | **Đã lỗi thời.** Phiên chuẩn 30 phút, khoảng 15 lượt, 72k token vào, 7.5k token ra. Cần tính lại cho 15 đến 20 phút và chi phí STT, TTS |
| A-4 | Giả định | Chất lượng `text-embedding-3-small` với tiếng Việt xen thuật ngữ Anh **chưa được đo**; đo bằng golden set RAG ở Sprint 1 |
| A-5 | Giả định | Quy mô demo vài chục người dùng, khoảng 20 phiên đồng thời. **Phiên real-time tốn tài nguyên hơn chat, con số này cần kiểm tra lại** |
| A-6 *(mới)* | Giả định **đã xác nhận (owner, 19/10)** | "Video ứng viên chỉ hiển thị" nghĩa là ứng viên **thấy chính mình** trong khung tự xem; video không rời khỏi trình duyệt. AI là ảnh tĩnh. Nhận diện cảm xúc đã hoãn nên không phân tích video |
| A-7 *(mới)* | Giả định | Hạ tầng voice-agent có sẵn kèm nhà cung cấp STT và TTS hỗ trợ tiếng Việt xen thuật ngữ tiếng Anh đủ dùng. **Chưa khảo sát, chưa có số liệu** (chỉ liên quan giai đoạn 2) |
| A-8 *(mới)* | Giả định | Trình duyệt của ứng viên cho phép truy cập micro và camera, và mạng đủ ổn định cho hội thoại real-time |
| C-1 | Ràng buộc thời gian | 8 tuần từ 12/10 đến 06/12/2026, feature freeze 06/12; Sprint 5 (07/12 đến 21/12) dành cho polish, test tích hợp, báo cáo. **Không đổi dù phạm vi tăng (R-6)** |
| C-2 | Ràng buộc nhân lực | 1 AIE chính; golden set cần thêm 1 người gán nhãn độc lập. Giao diện web phòng phỏng vấn cần FSD |
| C-3 | Ràng buộc kỹ thuật | Constitution: `interview-service` sở hữu dữ liệu phiên; file code dưới 200 dòng. ~~Không agent framework~~ **(nay được phép)**. ~~REST/HTTP giữa NestJS và ai-service; ai-service stateless~~ **(cần xem lại vì hội thoại real-time có thể cần kết nối bền, phải có ADR và amendment)** |
| C-4 | Ràng buộc chất lượng | CI chạy lint, type check, test; không mock giả để qua CI; không commit secret |
| C-5 | Ràng buộc quy trình | GitHub Flow, PR vào `main` cần CI xanh và ≥ 1 approve |
| C-6 | Ràng buộc pháp lý | Dữ liệu CV, **giọng nói và hình ảnh** gửi tới nhà cung cấp ở nước ngoài; cần consent và đối chiếu quy định bảo vệ dữ liệu cá nhân (xem R-9) |

## 10. Phụ thuộc

| Phụ thuộc | Bên | Cần khi | Ghi chú |
|---|---|---|---|
| Pattern TCP `application.getCvFile` và presigned URL | FSD (job-service) | Tuần 5 | Chưa tồn tại; ngoài ra phỏng vấn không CV |
| Pattern TCP `application.getJobDescription` (S2-FSD-11, đề xuất, chờ FSD xác nhận) và S3-FSD-8 (gắn CV + JD vào phiên) | FSD (job-service, interview-service) | Tuần 4 đến 5 | Mới; ngoài ra luyện tập theo track + level |
| Migration `interview_db` (cột mới `plan`, `candidate_state`, `cv_profile`, `action`, `evaluation`...) | FSD | Tuần 5 | Cần FSD xác nhận |
| Kênh truyền thời gian thực giữa trình duyệt, interview-service và ai-service (thay cho relay SSE văn bản) | FSD + AIE + DE | **Cần quyết định kiến trúc trước** | Mới; xem câu hỏi mở 13 |
| Giao diện web: phòng phỏng vấn, kiểm tra micro và camera, trang báo cáo | FSD | Sớm | Mới; lượng việc lớn |
| Nhà cung cấp STT, TTS (và hạ tầng media nếu cần) | AIE + DE | Sớm | Mới; chưa khảo sát |
| `knowledge_chunks` có dữ liệu Q&A Java và Node (kèm `topic_id`, `key_points`) | DE | Tuần 2 | Không có thì Evaluator chạy không RAG |
| `ai_db`, extension `vector`, DDL `knowledge_chunks` ghép vào init script | DE (T016) | Tuần 1 đến 2 | |
| Cấu hình APISIX cho luồng real-time, route `/ai/*` | DE | Tuần 4 | Chưa kiểm chứng |
| Topic catalog review, `resources` (link tài liệu học) | DE | Tuần 1 đến 2 | Đồng sở hữu |
| CI job Python | DE (T032) | Sớm | |
| Dữ liệu có consent cho fine-tune hoặc học | Cả team | Trước giai đoạn 3 | Mới; chưa có nguồn |
| Người gán nhãn golden set độc lập | Thành viên khác | Tuần 2, 7 | Khoảng 2 đến 3 giờ mỗi lần |
| Phê duyệt ADR-008 (cập nhật), ADR mới cho kênh real-time và amendment constitution II, IV, V, VII | Cả team | Tuần 1 | Constitution đang ở trạng thái Proposed |

## 11. Rủi ro chính

Danh sách rủi ro của thiết kế văn bản ở [design doc 11](../10-risks-and-8-week-roadmap.md). Bảng dưới gồm rủi ro cũ đã cập nhật và rủi ro mới do thay đổi phạm vi.

| # | Rủi ro | Tác động | Giảm thiểu |
|---|---|---|---|
| R-1 | LLM **chấm dễ dãi** hoặc bịa căn cứ | Cao | Rubric có mốc, luật khắt khe, hậu kiểm bằng code, golden set có nhãn người |
| R-2 | Đáp án mẫu hoặc `key_points` **sai** làm sai điểm | Cao | Người thứ hai review; catalog có `key_concepts` đã duyệt |
| R-3 | **Độ trễ vượt khả năng (rõ nhất ở giai đoạn 2).** Số đo thật: một lần chat 150 đến 200 token ra mất khoảng 4 đến 5 giây qua OpenRouter. Thiết kế hiện tại chạy Evaluator rồi Interviewer **nối tiếp** (ước tính ≈ 3.6 s tới token đầu), chưa tính STT và TTS. Mục tiêu real-time đòi hỏi đổi thiết kế đường nóng | Cao (đã chấp nhận cải thiện dần) | Chạy Evaluator song song hoặc sau khi AI đã bắt đầu nói; stream STT, LLM, TTS theo từng đoạn; model nhanh hơn; rút ngắn output; đo từ tuần đầu, không đợi tuần 4 |
| R-4 | **Prompt injection** qua CV và câu trả lời (kể cả lời nói được chuyển thành chữ) | Cao | Cô lập CV thô chỉ ở CV Parser, khối untrusted, hậu kiểm code, bộ test adversarial |
| R-5 | **Lộ dữ liệu cá nhân** (CV tới bên thứ ba, log) | Cao | Redact trước LLM, consent riêng, không log nội dung, chọn provider không lưu dữ liệu nếu có |
| R-6 | **Trễ tiến độ do phạm vi tăng mạnh.** Voice, giao diện web, fine-tune và học từ dữ liệu được thêm vào nhưng vẫn 8 tuần, 1 AIE, hạn 06/12 | **Cao** (giảm từ rất cao nhờ phân kỳ đã chốt) | **Đã chọn phân kỳ ở mục 4.3**: chat trước, voice nếu ổn; cắt từ dưới lên (học từ dữ liệu, rồi voice); dùng hạ tầng voice-agent có sẵn |
| R-7 | **Lệch contract** với FSD, nặng hơn vì thêm kênh real-time và giao diện | Cao | Chốt kiến trúc và contract sớm bằng PR; mock theo contract mới |
| R-8 | Luồng real-time bị gián đoạn qua gateway hoặc relay (buffer, timeout, NAT/firewall) | Cao | Kiểm chứng sớm bằng spike; phương án dự phòng chat văn bản (nếu giữ) |
| R-9 *(mới)* | **Dữ liệu giọng nói và hình ảnh** thường được xem là dữ liệu nhạy cảm theo nhiều quy định; gửi tới STT, TTS, LLM bên thứ ba | Cao | Consent riêng, không ghi nếu chưa đồng ý, nêu rõ nơi xử lý và thời hạn lưu, chọn nhà cung cấp không lưu dữ liệu nếu có; nhóm đối chiếu văn bản pháp lý hiện hành (chưa kiểm chứng ở đây) |
| R-10 *(mới)* | **Chất lượng STT** với tiếng Việt xen thuật ngữ Anh và giọng vùng miền: nhận sai làm sai điểm, ứng viên bị chấm oan | Cao | Đo thử nhiều nhà cung cấp trước khi chọn; cho Evaluator biết độ tin cậy của bản ghi; hiển thị lại câu đã nghe để ứng viên xác nhận (đề xuất) |
| R-11 *(mới)* | **Chi phí** STT, TTS, media chưa có ước tính | TB | Đo sớm; quota phiên; cảnh báo ngưỡng |
| R-12 *(mới)* | **Fine-tune không có dữ liệu và không có cách đo.** Dự án chưa có dữ liệu phỏng vấn có nhãn đủ lớn; fine-tune có thể làm chất lượng giảm mà không biết | TB | Chỉ làm sau khi có golden set và dữ liệu có consent; so sánh trước và sau trên cùng bộ đo |
| R-13 *(mới)* | **Agent tự học** làm lệch hành vi, nhiễm dữ liệu độc hại hoặc thao túng (ứng viên cố dạy hệ thống chấm dễ) | Cao | Không tự cập nhật trực tiếp; mọi thay đổi qua duyệt và đo trên golden set; tách dữ liệu học khỏi dữ liệu đánh giá |
| R-14 *(mới)* | **Khác biệt thiết bị và mạng** của ứng viên (micro, tiếng ồn, băng thông) làm hỏng phiên | TB | Kiểm tra micro và camera trước phiên; cho phép tiếp tục sau khi đứt kết nối; ghi lại trạng thái phiên |
| R-15 *(mới v0.4)* | **JD map sai sang catalog** hoặc JD chứa chỉ dẫn độc hại | TB | `out_of_catalog` thay vì ép; JD đi qua parser như CV (khối untrusted, quét injection) |
| R-16 *(mới v0.4)* | **Phụ thuộc nhiều vào FSD và DE** (interview-service, TCP lấy CV và JD, giao diện, đường ghi RAG, voice): chậm một bên làm trễ tích hợp | Cao | Harness và simulator gọi thẳng ai-service; mock đúng contract; mốc cắt giảm trong plan |

## 12. Câu hỏi mở

Câu 1 đến 8 giữ từ v0.1. Câu 9 đến 19 phát sinh từ thay đổi phạm vi v0.2. Cột trạng thái cập nhật theo trả lời của owner (v0.3).

| # | Câu hỏi | Trạng thái |
|---|---|---|
| 1 | Team có duyệt 6 track (thêm `frontend_react`, `devops_engineer`, topic AI) hay giữ 4? | **Mặc định: duyệt** (đề xuất DE, spec 005); chờ owner xác nhận |
| 2 | Ai viết và duyệt ADR (cập nhật ADR-008, ADR-009 mới) và các sửa đổi constitution? Gợi ý ở mục 0.3: gộp vào PR ratify | **Một phần**: hướng xử lý ở mục 0.3 đã được owner chấp nhận (19/10). Việc viết ADR và đưa vào PR ratify còn **mở** |
| 3 | FSD xác nhận các cột mới của `interview_db` và pattern `application.getCvFile`? | **Mở** |
| 4 | Bucket CV ở job-service là private (cần presigned) hay public (`cvUrl` hiện ghi là URL MinIO)? | **Mở** |
| 5 | Streaming SSE qua APISIX có bị buffer không? | **Mở** (vẫn cần cho giai đoạn 1, chat dùng SSE) |
| 6 | Tài khoản OpenRouter có bật được chế độ không lưu dữ liệu (zero data retention) không? | **Mở** |
| 7 | Quota phiên mỗi ngày: giữ 5 hay đổi? | **Mở** |
| 8 | Quy định bảo vệ dữ liệu cá nhân hiện hành: nhóm tự đối chiếu văn bản (design doc nhắc Nghị định 13/2023/NĐ-CP và luật mới có hiệu lực từ 01/01/2026, chưa được kiểm chứng ở đây) | **Mở** |
| 9 | "Real-time" cụ thể: độ trễ chấp nhận được, ứng viên có được ngắt lời AI (barge-in) không? | **Một phần**: độ trễ cải thiện dần (D4). Barge-in còn mở, chỉ liên quan giai đoạn 2 |
| 10 | "Giống Google Meet" nghĩa là gì, video ứng viên dùng để làm gì? | **Đã trả lời (D5)**: giống giao diện họp; video ứng viên chỉ hiển thị; AI là ảnh. *Diễn giải "chỉ hiển thị cho chính ứng viên, không gửi đi" đã xác nhận 19/10 (A-6)* |
| 11 | Có giữ chat văn bản làm dự phòng không? | **Đã trả lời (D2)**: chat là giai đoạn đầu; giữ làm dự phòng khi thêm voice |
| 12 | Thời lượng mặc định trong 15 đến 20 phút và số topic mỗi phiên? | **Mở.** Đề xuất ở FR-AI-003: 20 phút ≈ 5 topic, 15 phút ≈ 4 topic (xem FR) |
| 13 | Kênh real-time, hạ tầng và nhà cung cấp STT, TTS? | **Một phần (D6, D8)**: dùng hạ tầng có sẵn; theo `main` voice là tùy chọn A do DE sở hữu. Chọn cụ thể và khảo sát chất lượng tiếng Việt xen thuật ngữ Anh còn **mở** (giai đoạn 2) |
| 14 | Fine-tune cái gì, dữ liệu từ đâu, ai gán nhãn? | **Hoãn** (ngoài kế hoạch 8 tuần) |
| 15 | "Agent tự học từ dữ liệu" là học gì, từ dữ liệu nào, ai duyệt? | **Hoãn** (ngoài kế hoạch 8 tuần) |
| 16 | Ai làm giao diện web phòng phỏng vấn và trang báo cáo? | **Một phần**: giai đoạn 1 là chat trong giao diện họp. Người thực hiện (FSD?) còn **mở** |
| 17 | Giữ 8 tuần và feature freeze 06/12 hay dời? | **Đã trả lời (D1)**: giữ khung, áp dụng phân kỳ mục 4.3 |
| 18 | Nhận diện cảm xúc "để sau": giai đoạn nào, điều kiện nào? | **Mở** (hoãn; trong lúc này không phân tích video, BRU-15) |
| 19 | Pháp lý về giọng nói và hình ảnh khuôn mặt (thường là dữ liệu nhạy cảm) | **Một phần**: đã chốt phải có sự đồng ý trước (D3). Đối chiếu văn bản pháp lý hiện hành còn **mở** |
| 20 | Voice: tùy chọn A (theo `main`, bấm-để-nói) hay B (realtime, BRD v0.3)? | **Mặc định A**, chờ owner xác nhận |
| 21 | Xác nhận JD là đầu vào của Planner (S2-AIE-6, S3-AIE-6) thay mục "ngoài phạm vi" của v0.3 | **Mặc định xác nhận** (AIE đã đồng ý 15/10) |
| 22 | FSD xác nhận S2-FSD-11 (TCP lấy JD) và S3-FSD-8 (gắn CV + JD vào phiên) | **Mở** |

## 13. Truy vết mục tiêu sang yêu cầu

| Mục tiêu | Yêu cầu nghiệp vụ |
|---|---|
| BO-1 | BR-01, 02, 03, 11, 17, 19 |
| BO-2 | BR-04 |
| BO-3 | BR-05, 06, 07, 12, 14 |
| BO-4 | BR-08 |
| BO-5 | BR-09, 10, 22 |
| BO-6 | BR-13 |
| BO-7 | BR-14, 16, 20 |
| BO-8 | BR-15 |
| BO-9 | BR-01, 11, 17, 18, 19, 20, 24 |
| BO-10 | BR-21 |
| BO-11 | BR-23 |

## 14. Việc cần làm tiếp

1. Owner xác nhận các mặc định D7–D12 (đặc biệt D8 voice và D12 thời lượng); team duyệt BRD v0.5. (A-6 và hướng xử lý constitution đã xác nhận 19/10.)
2. Mở PR tài liệu (nhánh `thang/brd-v04-reconcile`), nhờ FSD và DE review; gộp sửa đổi constitution vào PR ratify (bản nháp ở `plans/20261019-1100-ai-interview-brd-implementation/reports/`).
3. Triển khai theo [kế hoạch](../../../plans/20261019-1100-ai-interview-brd-implementation/plan.md); mỗi tính năng một nhánh `thang/<tính-năng>`; xong một việc thì commit, push và mở PR vào `main`; mỗi PR đồng bộ BRD, FR, NFR, L2 và chạy `apps/ai-service/scripts/check_docs.py`.
