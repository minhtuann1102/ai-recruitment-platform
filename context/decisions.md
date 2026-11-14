# Quyết định

Nguồn chi tiết: `docs/ai-service/requirements/01-brd.md` §0.2 (D1–D12), §0.3.

## Owner đã xác nhận
- **A-6 (2026-10-19):** "video ứng viên chỉ hiển thị" = ứng viên thấy chính mình như khung tự xem; không gửi lên server, không lưu. AI là ảnh tĩnh.
- **Xử lý mâu thuẫn constitution (2026-10-19):** giữ ai-service stateless và REST/SSE; voice (nếu có) nằm ngoài ai-service; framework chỉ cho lớp giọng nói qua ADR, orchestrator/policy/tính điểm là code của nhóm; dữ liệu huấn luyện đi đường riêng, không vào `knowledge_chunks`; gộp sửa đổi vào PR ratify constitution.
- Phân kỳ: **chat trước**, voice sau nếu ổn (D1, D2). Phải xin ứng viên đồng ý trước khi bật camera/micro (D3). Độ trễ cải thiện dần (D4). Dùng hạ tầng voice-agent có sẵn (D6).

- **Độ trễ giai đoạn 1 (2026-10-22):** chấp nhận P50 ~5 s một lượt (đo: P50 5.0 s, P95 7.7 s sau Evaluator/Planner v2) theo D4 "cải thiện dần". Chưa làm Interviewer song song Evaluator; xem lại khi có golden set và trước gate voice.

- **Truy hồi tiếng Việt (2026-10-24, ADR-010):** giữ `text-embedding-3-small` + LLM viết lại truy vấn (held-out 32 câu tiếng Việt thuần 0.938) cho giai đoạn 1. Chưa đổi sang `3-large`, chưa nhờ DE index lại.

- **Ngân hàng câu hỏi từ kho (2026-10-24, PR #39):** giữ như hiện tại (`RAG_QUESTION_BANK` bật). Chưa chỉnh độ khó câu kho (vd hỏi cao hơn một bậc) cho đến khi golden set có người chấm.
- **Ngôn ngữ (2026-10-24, PR #38):** câu tiếng Việt, giữ thuật ngữ tiếng Anh; không đổi prompt, chặn bằng code ở đầu ra.
- **Hiệu chỉnh judge_support (2026-10-31):** số `supported` dùng judge v2 đã hiệu chỉnh với nhãn của Claude (Fable 5.1, `evals/support_labels/claude.json`), không chờ nhãn người; mọi báo cáo ghi rõ "hiệu chỉnh với LLM thứ hai, chưa với người". Nhãn người là tùy chọn nếu kịp trước 06/12.
- **Chấm ngôn ngữ (2026-10-31, Evaluator v5):** câu trả lời tiếng Anh hoặc không dấu chấm như tiếng Việt, theo nhãn người; không trừ điểm giao tiếp.
- **Phase A xong (2026-11-02):** đạt mốc 07/11 sớm, theo tiêu chí "có số đo thật". Nhãn người chỉ có 1 người chấm, chưa có kappa; Q2 vẫn mở nếu báo cáo cần kappa.
- **Tool calling trong gateway (2026-11-14, phase 02 plan agentic):** vòng lặp tự viết trên SDK `openai`, không framework (A4). Không làm chế độ tách; combo model + tools + JSON strict không hỗ trợ thì latch theo tiến trình và caller gọi một lần không tools như cũ. Lần gọi đầu cũng bị cắt theo ngân sách đồng hồ chung (H1). Chưa agent nào dùng; bước gọi LLM thật chờ khóa API.

## Mặc định của kế hoạch, chờ owner xác nhận
- D7 JD vào Planner (không vào RAG); D8 voice tùy chọn A (theo `main`, DE sở hữu, TTS + STT bấm-để-nói); D9 phiên riêng tư; D10 6 track; D11 DE sở hữu đường ghi RAG, AIE đường đọc; D12 thời lượng 15–20 phút, mặc định 20, turn cap 16.

## Quy ước kỹ thuật đã chốt
- LLM qua API OpenAI-compatible (OpenRouter), model mặc định `gpt-4o-mini`; embedding `text-embedding-3-small` 1536 chiều.
- Điểm do code tổng hợp; Evaluator chấm mỗi lượt; ứng viên không thấy điểm giữa phiên (ADR-008).
- RAG bật mặc định (PR #52): truy hồi kết hợp BM25 trong bộ nhớ, vector và tăng điểm `topic_id`, gộp bằng RRF; thiếu `AI_DB_URL` hay ai_db lỗi thì phiên chạy không có RAG.
- Biên độ độ khó theo `docs/ai-service/01` §2.1 (Fresher 1–3, Junior 1–4, Middle 2–4, Senior 2–5); có test đối chiếu.
- **Evaluator tự tra cứu (2026-11-14, phase 03 plan agentic):** `search_knowledge` do LLM chọn `query`, code cố định phạm vi và chỉ BM25 bộ nhớ; chunk nối cuối `turn_snippets` để id `S{n+1}..` đi qua hậu kiểm hiện có. Chunk tra cứu không có quyền phạt: chỉ misconception dựa hoàn toàn vào chúng mới không chặn `technical_accuracy`, còn lại như tắt cờ (H4). Vòng lặp + đường lùi chung một ngân sách 10 s (worst case ≈ 11,5 s trước `meta`). Mặc định tắt cho đến khi đo đạt mốc reply mục 8.
- **Policy lai (2026-11-14, phase 04 plan agentic):** `POLICY_MODE=rules` (mặc định) | `hybrid`, không có `shadow` (sim `hybrid` đã ghi hành động phản thực của luật). Cách A: Evaluator v9 đề xuất, không thêm lời gọi LLM. Code quyết bằng bảng hợp lệ theo `classify(ev)` sau ngân sách; loại nhạy cảm không giao LLM; `forced`, `low_performance_stop`, turn cap luôn ở trên. Đề xuất không hợp lệ thì lùi về `decide()`. Evaluator giữ ghim v8 khi cờ tắt.
- **Lập lại kế hoạch giữa buổi (2026-11-14, phase 05 plan agentic):** `REPLAN_ENABLED=false` (mặc định, cần `POLICY_MODE=hybrid`), `REPLAN_MAX_SWAPS=1` (trần 2). Planner dự phòng tối đa 2 topic `alt{n}` lưu trong `plan.replan`; Evaluator v10 (cố định cả phiên khi hybrid + cờ) đề xuất `swap`, code kiểm (chỉ technical `pending` sau topic hiện tại, không topic JD ưu tiên, không khi forced / hurry / `low_performance_stop`) rồi đổi tại chỗ; `effective_plan` gọi một lần ở mỗi entry point. **Cờ giữ tắt cho đến khi FSD xác nhận bằng văn bản** (lưu nguyên plan/state, `topic_id` `alt*`, danh sách topic, khóa mặc định mới); không đạt mốc đo thì giữ tắt và ghi lý do ở đây.
- **Ghi chú agent (2026-11-14, phase 07 plan agentic, tùy chọn):** `AGENT_NOTES_ENABLED=false` (mặc định, cần `POLICY_MODE=hybrid`). Evaluator v11 (= v10 + `new_note`, `note_updates`, cố định cả phiên) ghi tối đa 1 ghi chú/lượt, ≤ 8 ghi chú, ≤ 150 ký tự; code lọc injection + PII, lượt sensitive/injection không ghi. **Chỉ `to_verify` đang `open` được đưa lại vào Evaluator** (giảm neo điểm, audit H2); code không dùng ghi chú để tính điểm hay quyết định và Interviewer/Reporter không đọc, nhưng Evaluator v11 thấy ghi chú `to_verify` đang `open` khi chấm: rủi ro neo điểm chờ gate [BLOCKED-KEY]. Ghi chú dài hơn 150 ký tự bị bỏ (không cắt, tránh lọt một phần PII); đầy 8 thì bỏ ghi chú đã xong rồi ghi chú cũ nhất không phải `to_verify`. Prompt v8/v9/v10 không đổi khi cờ tắt (test ghim). Giữ tắt cho đến khi [BLOCKED-KEY] gate chấm điểm + đọc tay 20 phiên đạt (≥ 85%, 0 PII); không đạt thì ghi lý do ở đây.
