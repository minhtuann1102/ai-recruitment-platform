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

## Mặc định của kế hoạch, chờ owner xác nhận
- D7 JD vào Planner (không vào RAG); D8 voice tùy chọn A (theo `main`, DE sở hữu, TTS + STT bấm-để-nói); D9 phiên riêng tư; D10 6 track; D11 DE sở hữu đường ghi RAG, AIE đường đọc; D12 thời lượng 15–20 phút, mặc định 20, turn cap 16.

## Quy ước kỹ thuật đã chốt
- LLM qua API OpenAI-compatible (OpenRouter), model mặc định `gpt-4o-mini`; embedding `text-embedding-3-small` 1536 chiều.
- Điểm do code tổng hợp; Evaluator chấm mỗi lượt; ứng viên không thấy điểm giữa phiên (ADR-008).
- Biên độ độ khó theo `docs/ai-service/01` §2.1 (Fresher 1–3, Junior 1–4, Middle 2–4, Senior 2–5); có test đối chiếu.
