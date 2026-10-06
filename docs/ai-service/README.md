# AI Service — Design Doc: Phỏng vấn kỹ thuật agentic

> **Trạng thái:** Draft, chờ team review · **Ngày:** 2026-10-06 · **Owner đề xuất:** AIE · **Reviewer:** FSD, DE
>
> **Phạm vi tài liệu:** thiết kế `apps/ai-service` (Python FastAPI) và phần liên quan trong `interview-service`
> (NestJS) cho tính năng luyện phỏng vấn kỹ thuật bằng AI. Đây là feature `006-ai-interview-agents` +
> `011-agentic-interview-hardening` trong [specs/README.md](../../specs/README.md).

## Mục lục

| # | Nội dung | File |
|---|---|---|
| 1 | Tổng quan & phạm vi, giả định, quan hệ với ADR-007 | README.md (file này) |
| 2 | Input schema & xử lý CV (validate, parse, chống prompt injection) | [01-input-schema-and-cv-processing.md](01-input-schema-and-cv-processing.md) |
| 3 | Kiến trúc multi-agent: sơ đồ, trách nhiệm, I/O schema, cấu trúc prompt | [02-multi-agent-architecture-and-prompts.md](02-multi-agent-architecture-and-prompts.md) |
| 4 | Orchestrator: state machine, điều kiện chuyển, lỗi & retry | [03-orchestrator-state-machine.md](03-orchestrator-state-machine.md) |
| 5 | Vòng lặp adapt & candidate state | [04-adaptive-loop-and-candidate-state.md](04-adaptive-loop-and-candidate-state.md) |
| 6 | Rubric & báo cáo cuối buổi | [05-rubric-and-final-report.md](05-rubric-and-final-report.md) |
| 7 | API contract (public + internal, streaming) | [06-api-contract.md](06-api-contract.md) |
| 8 | Lưu trữ dữ liệu | [07-data-storage.md](07-data-storage.md) |
| 9 | Latency & chi phí, chọn model | [08-latency-and-cost.md](08-latency-and-cost.md) |
| 10 | Đánh giá chất lượng agent | [09-agent-quality-evaluation.md](09-agent-quality-evaluation.md) |
| 11–12 | Rủi ro, lộ trình 8 tuần | [10-risks-and-8-week-roadmap.md](10-risks-and-8-week-roadmap.md) |

## Tóm tắt nhanh

- **5 agent theo vai trò** (CV Parser, Planner, Evaluator, Interviewer, Reporter), **điều phối bằng code**
  (state machine thuần Python). Agent không gọi nhau, không tự quyết luồng; chỉ orchestrator gọi agent.
- **Mỗi lượt:** Evaluator chấm câu trả lời (JSON, không stream) → **policy viết bằng code** chọn hành động
  (đào sâu / gợi ý / hỏi lại / đổi độ khó / chuyển chủ đề) → Interviewer **chỉ diễn đạt** câu hỏi theo hành
  động đã chọn, stream từng token về client.
- **ai-service stateless** (ADR-004, constitution IV): interview-service lưu session, transcript, candidate
  state, report và gửi state kèm mỗi request.
- **Buổi mặc định:** ~30 phút, 5–6 chủ đề, 4 phase: giới thiệu & dự án (từ CV) → kiến thức chuyên môn →
  tình huống / system design theo level → kết thúc.
- **Điểm số do code tổng hợp** từ kết quả Evaluator; Reporter chỉ viết phần nhận xét, phải trích lượt làm
  bằng chứng.
- **Ước tính:** ~72k input + ~7.5k output token/phiên ≈ **$0.015/phiên** (giá giả định, xem §9). Thời gian
  tới token đầu tiên mục tiêu P50 ≤ 3.5 s, P95 ≤ 6 s.

## Giả định đã chọn

Repo đã chốt stack và LLM provider nên tài liệu không đặt câu hỏi lại, chỉ ghi rõ nguồn. Điểm nào nhóm muốn
đổi, sửa ở bảng này trước.

| # | Hạng mục | Giả định | Nguồn |
|---|---|---|---|
| A1 | LLM provider | API **OpenAI-compatible**, cấu hình qua `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`; mặc định OpenRouter | Constitution IV; `apps/ai-service/app/config.py` (nhánh `feat/aie`) |
| A2 | Model mặc định | `gpt-4o-mini` cho mọi agent; **override riêng từng agent bằng env** (§9) | Constitution IV, [rag-design.md](../architecture/rag-design.md) ¹ |
| A3 | Embedding / RAG | `text-embedding-3-small` (1536 dims), pgvector `knowledge_chunks`; chỉ dùng `interview_qa` + `textbook`, **không dùng JD** | rag-design.md ¹; yêu cầu "không dùng JD" |
| A4 | ai-service | Python FastAPI, Pydantic v2, `openai` SDK. **Không dùng LangGraph/agent framework**: state machine tự viết | Constitution VII (KISS) |
| A5 | Quyền sở hữu dữ liệu | interview-service sở hữu toàn bộ dữ liệu phỏng vấn; ai-service không lưu phiên | ADR-004, constitution IV |
| A6 | Transport | REST giữa interview-service ↔ ai-service; streaming bằng **SSE** | ADR-003 |
| A7 | Ngôn ngữ | Phỏng vấn tiếng Việt, giữ thuật ngữ tiếng Anh | rag-design.md §9 ¹ |
| A8 | Kênh | Chat văn bản. Voice ngoài phạm vi | Thời gian 2 tháng |
| A9 | Track MVP | `java_backend`, `nodejs_backend`. Thêm track = thêm 1 file topic catalog | Đề bài |
| A10 | CV | **Dùng lại CV đã nộp ở job-service** (PDF / DOCX); interview-service không nhận upload, không lưu bản sao file | Quyết định của team 2026-10-06 (§2, §8) |

¹ `rag-design.md`, `adr-007-multi-agent-interview.md` và bản mới của `ai-integration.md` hiện **chỉ có trên
nhánh `origin/feat/aie`**, link sẽ chạy khi nhánh đó merge vào `main`.

---

## 1. Tổng quan & phạm vi

### 1.1 Mục tiêu

Mô phỏng một buổi phỏng vấn kỹ thuật **gần thực tế nhất** cho ứng viên IT:

1. Câu hỏi bám vào **CV thật** của ứng viên (dự án, công nghệ đã dùng), không phải bộ câu hỏi cố định.
2. Agent **adapt sau mỗi câu trả lời**: trả lời tốt thì hỏi sâu hơn hoặc khó hơn; trả lời yếu thì gợi ý,
   hạ độ khó hoặc chuyển chủ đề, giống cách người phỏng vấn thật làm.
3. Chấm điểm **khắt khe, có căn cứ**, theo chuẩn của level đã chọn.
4. Cuối buổi có **báo cáo feedback** đủ cụ thể để ứng viên biết học gì tiếp.

Đồng thời phải **làm xong trong 2 tháng** (8 tuần, §12) bởi 1 AIE chính, nên mọi lựa chọn ưu tiên đơn giản,
test được, ít thành phần.

### 1.2 Nguyên tắc thiết kế

| Nguyên tắc | Cụ thể hóa |
|---|---|
| Code điều phối, LLM làm việc hẹp | Mọi quyết định luồng (chuyển phase, giới hạn follow-up, đổi độ khó) là code deterministic, unit test được. LLM chỉ: trích xuất, lập kế hoạch, chấm, diễn đạt, tóm tắt. |
| Tách người chấm khỏi người hỏi | Evaluator không nói chuyện với ứng viên, không biết câu hỏi tiếp; Interviewer không chấm. Giảm thiên vị "đã hỏi thì muốn khen". |
| Output có cấu trúc | Mọi agent trừ Interviewer trả JSON theo Pydantic schema; dùng structured outputs khi provider hỗ trợ. |
| Dữ liệu ứng viên là không tin cậy | CV và câu trả lời đều có thể chứa prompt injection; chỉ CV Parser thấy CV thô. |
| Stateless AI | ai-service nhận state, trả state mới; restart / scale / swap model không mất dữ liệu. |
| Điểm do code tính | LLM cho band từng tiêu chí từng lượt; tổng hợp, trọng số, kết luận do code. |

### 1.3 In-scope

- Input: track (Java BE, NodeJS BE), level (Fresher / Junior / Middle / Senior), CV đã nộp ở job-service (PDF / DOCX), thời
  lượng (mặc định 30 phút).
- 5 agent: CV Parser, Planner, Evaluator, Interviewer, Reporter.
- Orchestrator state machine 4 phase, policy adapt, giới hạn follow-up / gợi ý / thời gian.
- Rubric 4 tiêu chí theo level, báo cáo cuối buổi (điểm từng phần, điểm mạnh, cần cải thiện, gợi ý học).
- Streaming câu hỏi (SSE) từ ai-service → interview-service → APISIX → client.
- Xử lý lỗi LLM: retry giới hạn, repair JSON, fallback để buổi phỏng vấn không chết.
- Chống prompt injection từ CV và câu trả lời; redact PII trước khi gửi LLM.
- Bộ đánh giá chất lượng: golden set cho Evaluator, ứng viên giả lập (giỏi / trung bình / yếu) chạy end-to-end.
- Log token, latency, chi phí theo phiên.

### 1.4 Out-of-scope

| Hạng mục | Lý do / hướng sau này |
|---|---|
| Job Description làm input | Đề bài yêu cầu không dùng JD |
| Voice (STT/TTS), video, nhận diện cảm xúc | Không kịp 2 tháng |
| Live coding / chạy code ứng viên | Cần sandbox; scenario phase chỉ hỏi đáp bằng lời |
| OCR CV dạng ảnh scan | Báo lỗi "CV không đọc được", gợi ý chọn CV khác hoặc phỏng vấn không CV |
| Track ngoài Backend (Frontend, DevOps, Data...) | Kiến trúc hỗ trợ, chỉ cần thêm topic catalog; không làm trong 8 tuần |
| Employer xem kết quả luyện tập của ứng viên | Cần cơ chế consent riêng; phiên luyện tập mặc định riêng tư |
| Chống gian lận (copy-paste, tra cứu) | Stretch S5-8 trong sprint plan |
| Fine-tune model, agent tự học từ dữ liệu | Không đủ dữ liệu và thời gian |
| Tiếp tục phiên trên nhiều thiết bị cùng lúc | Một phiên một client; refresh trang thì resume được (§7) |
| Agent framework (LangGraph, CrewAI, AutoGen...) | State machine tự viết đủ dùng, dễ test hơn |

### 1.5 Thuật ngữ

| Thuật ngữ | Nghĩa trong tài liệu này |
|---|---|
| **track** | Mảng phỏng vấn ứng viên chọn (đề bài gọi là "chủ đề"): `java_backend`, `nodejs_backend` |
| **topic** | Chủ đề con trong interview plan, ví dụ "Spring `@Transactional`", "Dự án order service". Một buổi có 5–6 topic |
| **phase** | Giai đoạn buổi phỏng vấn: `intro`, `technical`, `scenario`, `wrap_up` |
| **turn** | Một lượt: 1 câu hỏi của Interviewer + 1 câu trả lời của ứng viên |
| **action** | Hành động orchestrator chọn cho lượt tiếp: `ask_main`, `follow_up`, `hint`, `clarify`, `wrap_up`, `end` |
| **band** | Điểm Evaluator cho 1 tiêu chí ở 1 lượt, số nguyên 0–4, quy đổi 0–10 khi lưu |
| **difficulty** | Độ khó nội bộ 1–5, map sang `easy/medium/hard` của schema hiện có |
| **candidate state** | JSON trạng thái ứng viên trong phiên: phase, topic, độ khó, điểm mạnh, lỗ hổng, bộ đếm (§5) |
| **topic catalog** | File YAML theo track, liệt kê topic, level phù hợp, key concepts, tài liệu học (do team curate) |

---

## Quan hệ với ADR-007 và tài liệu hiện có

ADR-007 (nhánh `feat/aie`, 2026-10-03) mô tả kiến trúc 3 agent khác với kiến trúc đã chốt trong tài liệu này.
Tài liệu này **đi theo kiến trúc đã chốt** và ghi rõ các điểm thay đổi:

| Hạng mục | ADR-007 | Tài liệu này | Hệ quả |
|---|---|---|---|
| Evaluator | 1 lần cuối phiên, chấm cả transcript | **Mỗi lượt**, chấm câu vừa trả lời | Adapt dựa trên điểm thật, không cần `answer_signal`; thêm ~1 LLM call/lượt vào đường latency |
| Planner | Mỗi lượt, chọn `deepen/switch/keep` | **1 lần đầu buổi**, sinh interview plan | Quyết định từng lượt chuyển sang policy viết bằng code |
| CV Parser, Reporter | Không có | Mới | Thêm endpoint parse CV; Reporter thay phần tổng kết của Evaluator |
| Ngoại lệ "chấm mọi câu" | — | Câu trả lời **chỉ gồm** cụm "không biết" / "em chưa học" / "pass" (≤ 6 từ) được code gán `dont_know`, **bỏ qua Evaluator**; có nội dung khác thì vẫn chấm (§4.5) | Lượt đó ~1 s thay vì ~3.6 s; nhóm có thể tắt bằng cờ nếu muốn Evaluator chấm tuyệt đối mọi câu |
| Tool calling (`retrieve_*`) | Agent tự gọi tool | Orchestrator lấy RAG trước rồi đưa vào prompt | Ít vòng LLM hơn, latency thấp hơn, dễ test |
| RAG `job_description` | Planner dùng `retrieve_topics` trên JD (rag-design.md §4) | **Không dùng JD**; Planner chọn topic từ topic catalog, RAG chỉ lấy `interview_qa` + `textbook` | Owner rag-design cần cập nhật mục 4; dữ liệu JD vẫn phục vụ job-service nếu cần |
| Contract ai-service | `start / next-turn / finalize` | Giữ 3 tên này + thêm `cv/parse`; **đổi nội dung** request/response, `next-turn` stream SSE | Đổi `AiInterviewClient` phía NestJS |
| `agent_decision` | `deepen / switch_topic / keep_difficulty` | Thêm cột `action` (6 giá trị), giữ `agent_decision` bằng bảng map (§5) | Migration `interview_db` |
| Ứng viên thấy điểm giữa phiên | Không | Không (giữ nguyên) | — |

## Quyết định của team

| Ngày | Quyết định | Ảnh hưởng |
|---|---|---|
| 2026-10-06 | **Đánh giá sau từng câu trả lời** rồi adapt câu hỏi tiếp theo (kiến trúc trong tài liệu này) | Cần ADR-008 thay ADR-007 |
| 2026-10-06 | Index JD vào `ai_db` (S2-DE-3) **không cắt, chuyển thành Stretch**: còn thời gian thì embed | §8.7 |
| 2026-10-06 | `knowledge_chunks` thêm **cột** `topic_id` (thay vì để trong `metadata`) | §8.7, cập nhật rag-design §3 |
| 2026-10-06 | Topic catalog **AIE + DE đồng sở hữu** | §8.1, §8.7 |
| 2026-10-06 | **Dùng lại CV đã nộp ở job-service**, không upload / lưu riêng cho phỏng vấn | §2.3, §7.2–7.3, §8 |

**Việc cần làm khi tài liệu được duyệt** (không làm trong tài liệu này):

1. Viết **ADR-008** "Evaluator mỗi lượt + Planner một lần + orchestrator bằng code", supersede ADR-007.
2. Amendment **constitution IV** nếu đổi nội dung contract (tên endpoint giữ nguyên).
3. Cập nhật `docs/architecture/ai-integration.md`, `data-model.md`, `api-contracts.md` (thêm TCP pattern
   `application.getCvFile`), `sprint-plan.md` (S2-AIE-1 "agent decision logic" thành policy code; S4-AIE-5
   streaming từ Stretch thành Bắt buộc; S2-DE-3 thành Stretch).
4. Cập nhật `data-pipeline.md` (Q&A có `topic_id` + `key_points`, nguồn textbook Java/Spring) và `rag-design.md`
   §3–4 (cột `topic_id`, bỏ `retrieve_topics` trên JD).
5. Amendment **constitution V**: transcript / CV không bao giờ vào `knowledge_chunks` hay dataset pipeline.

## Câu hỏi chưa giải quyết

1. Ai viết ADR-008, và AIE (tác giả ADR-007) review nội dung.
2. Thêm cột `action`, `phase`, `topic_id`, `evaluation`, `cv_application_id`, `cv_file_ref`... vào `interview_db` (§8): FSD (owner interview-service) xác nhận.
3. FSD xác nhận job-service làm pattern `application.getCvFile` + presigned URL (§7.3), và bucket CV đang private (cần presigned) hay public (`cvUrl` hiện ghi là "MinIO URL").
4. Streaming SSE qua APISIX: cần kiểm chứng proxy buffering và timeout (§7.5) trong tuần 4.
5. Quota phiên/ngày cho mỗi ứng viên (đề xuất 5) và tài khoản OpenRouter có bật zero-data-retention được không.
