# ADR-008: Evaluator mỗi lượt, Planner một lần, orchestrator bằng code

**Ngày:** 2026-10-08  
**Trạng thái:** Accepted (AIE). Contract chi tiết còn chờ FSD và DE review  
**Thay thế:** [ADR-007](adr-007-multi-agent-interview.md)  
**Thiết kế chi tiết:** [docs/ai-service/](../../ai-service/README.md)

## Bối cảnh

ADR-007 chia ai-service thành 3 agent (Planner mỗi lượt, Interviewer, Evaluator chấm cả phiên một lần cuối). Hạn chế:
- Giữa phiên không có điểm thật, Planner phải dựa vào `answer_signal` sơ bộ.
- Câu hỏi tiếp theo không thích ứng được với chất lượng câu trả lời vừa rồi một cách có căn cứ.
- Chưa có CV làm đầu vào, chưa có rubric theo level, chưa có kiểm chứng chống chấm dễ dãi.

## Quyết định

Dùng **5 agent theo vai trò, điều phối bằng code** (state machine thuần Python, không dùng agent framework):

| Agent | Chạy khi | Việc |
|---|---|---|
| CV Parser | Khi gắn CV | Trích xuất `cv_profile` từ CV đã redact |
| Planner | Một lần, đầu buổi | Chọn 5–6 topic từ **topic catalog**, key points, độ khó khởi đầu |
| Evaluator | **Sau mỗi câu trả lời** | Chấm 4 tiêu chí theo rubric + level; nêu ý có / thiếu / sai kèm trích dẫn |
| Interviewer | Mỗi lượt | Chỉ diễn đạt một câu hỏi theo action đã chọn, stream SSE |
| Reporter | Một lần, cuối buổi | Viết nhận xét; không tính điểm |

Các quyết định đi kèm:
- **Policy viết bằng code** chọn action mỗi lượt (đào sâu, gợi ý, hỏi lại, đổi độ khó, chuyển chủ đề, kết thúc). LLM không quyết luồng.
- **Điểm do code tổng hợp** từ kết quả Evaluator; Reporter chỉ viết lời, phải dẫn `evidence_turns`.
- **Không tool calling**: orchestrator lấy RAG và catalog trước rồi đưa vào prompt.
- **RAG chỉ dùng `interview_qa` và `textbook`**, không dùng JD. Chủ đề theo vị trí nằm trong topic catalog (`apps/ai-service/app/catalog/`).
- **Dùng lại CV đã nộp ở job-service**, không lưu bản sao.
- **ai-service vẫn stateless** (ADR-004): interview-service lưu plan và candidate state, gửi lại mỗi request.
- Tên endpoint giữ `start` / `next-turn` / `finalize`, thêm `cv/parse`. `start` và `next-turn` stream **SSE**.
- Ứng viên **không thấy điểm giữa phiên** (giữ nguyên).

## Lý do

- Adapt dựa trên điểm thật, có căn cứ, thay vì tín hiệu ước lượng.
- Mọi quyết định luồng là code xác định, unit test được; LLM làm việc hẹp (trích xuất, chấm, diễn đạt, tóm tắt).
- Tách người chấm khỏi người hỏi, giảm thiên vị "đã hỏi thì muốn khen".
- Đơn giản hơn agent tự gọi tool: ít vòng LLM, dễ đo, dễ debug.

## Đánh đổi

- **Latency mỗi lượt cao hơn:** Evaluator và Interviewer nối tiếp. Ước tính thời gian tới token đầu tiên khoảng 3,6 giây (P50 ≤ 3,5 s, P95 ≤ 6 s là mục tiêu). Đây là **giả định chưa đo**; số đo thật trên OpenRouter cho một lần chat dài vài trăm token là khoảng 4–5 giây, nên cần đo sớm.
- Chi phí ước tính khoảng $0,015 mỗi phiên, cũng là giả định cần kiểm chứng bằng log thật.
- Chỉ tiêu "P95 < 3 s" của S4-AIE-4 đổi thành chỉ tiêu TTFT.
- Phức tạp hơn ADR-007: 5 prompt, golden set cho Evaluator, harness ứng viên giả lập.
- Rủi ro riêng: chấm dễ dãi, đáp án mẫu sai làm sai điểm, streaming qua APISIX bị buffer (chưa kiểm chứng).

## Hệ quả

- Đổi `AiInterviewClient` phía NestJS (`parseCv`, `start`, `nextTurn`, `finalize`).
- Migration `interview_db`: thêm `action`, `phase`, `topic_id`, `evaluation`... (FSD xác nhận).
- `knowledge_chunks` thêm cột `topic_id`.
- Mock ai-service (`apps/ai-service/app/`) hiện theo contract cũ của ADR-007, cần cập nhật sang contract mới.
- Sprint plan: S2-AIE-1 thành policy code, S4-AIE-5 (streaming) từ Stretch thành Bắt buộc.
- Cần amendment constitution IV (nội dung contract đổi) và V (transcript, CV không vào `knowledge_chunks`).
