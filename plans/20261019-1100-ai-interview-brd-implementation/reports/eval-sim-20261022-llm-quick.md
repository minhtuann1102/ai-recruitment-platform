# Số đo đầu tiên với LLM thật (harness tầng 3, ma trận quick), 2026-10-22

Lệnh (owner chạy, khóa OpenRouter, `gpt-4o-mini` cho mọi agent kể cả Simulator):
`AGENT_EVALUATOR_MODE=llm AGENT_INTERVIEWER_MODE=llm AGENT_PLANNER_MODE=llm AGENT_REPORTER_MODE=llm python -m evals.simulate --matrix quick --simulator llm`
(in-process, phiên 20 phút, RAG tắt, CV Parser/JD Parser không dùng). Kết quả thô: `plans/reports/eval-sim-261022-2309.json` (không commit, chứa transcript tổng hợp).

**Cỡ mẫu nhỏ: 9 phiên, 94 lượt next-turn.** Số đo độ trễ và chi phí đủ để thấy xu hướng; chỉ số chất lượng (phân biệt, verdict) **chưa đủ để kết luận** (chỉ 1 nhóm level × track đủ 3 mức; Simulator và Evaluator cùng model).

## Độ trễ (đã đo)

| Chỉ số | P50 | P95 | Mục tiêu (NFR) |
|---|---|---|---|
| Một lượt `next-turn` tới token đầu (phía client, in-process nên ≈ cả lượt) | **6.0 s** | **9.7 s** | PERF01: P50 ≤ 3.5 s, P95 ≤ 6 s → **không đạt** |
| Evaluator (một lần gọi) | 4.8 s | 7.5 s | — |
| Interviewer (cả stream) | 2.0 s | 4.0 s | — |
| Planner (cả repair) | 13.0 s | 17.0 s | Hạn 22 s; **2/9 phiên quá hạn → plan dự phòng** |
| Reporter | 16.5 s | 30.0 s | Timeout 60 s, đạt |

Nhận xét: R-3 của BRD được xác nhận bằng số đo. Evaluator chạy trước Interviewer chiếm ~70% thời gian một lượt.

## Chi phí (đã đo token, giá giả định)

| Chỉ số | Giá trị |
|---|---|
| Số lượt trung bình mỗi phiên | 10.4 |
| Token trung bình mỗi phiên (vào / ra) | Evaluator 21.6k / 1.3k · Interviewer 9.3k / 0.4k · Reporter 2.5k / 1.0k · Planner 1.8k / 0.6k |
| Chi phí mỗi phiên | **trung bình $0.0073, tối đa $0.0098** (giá giả định gpt-4o-mini $0.15 / $0.60 mỗi 1M token) |
| Phiên vượt ngưỡng cảnh báo $0.10 | 0 |

Thấp hơn ước tính cũ (COST01 ≈ $0.01–0.015) vì phiên ngắn hơn và không có CV Parser, RAG. Chưa tính STT, TTS.

## Độ bền và hành vi

| Chỉ số | Kết quả | Mục tiêu |
|---|---|---|
| Phiên hoàn tất | 9/9 | — |
| Tỉ lệ call có fallback | **2.7%** (2 Planner quá hạn, 1 Interviewer quá 5 s chờ token đầu) | REL04 < 2% → **không đạt** |
| Câu hỏi lặp | 0% | < 5% |
| Vượt turn cap / follow-up, đủ 4 phase | 0 / 0 / 100% | 0 / 0 / 100% |
| Recall lỗ hổng (7 topic không biết được hỏi) | 100% | ≥ 70% |
| Điểm mạnh sai (trong `strengths`) | 0 | 0 |
| Injection không tăng điểm | 1/1 (0.0) | 100% |
| Junior Java: giỏi > TB > yếu | 6.2 > 4.6 > 1.5 (khoảng cách 4.7) | ≥ 3.0 |
| Verdict đúng (giỏi meets/exceeds, yếu below) | 33% (3 persona giỏi đều `near`: 6.2, 5.5, 5.2) | ≥ 80% |

## Phát hiện và đề xuất

1. **Độ trễ một lượt gấp ~1.7 lần mục tiêu.** Đề xuất theo thứ tự rẻ trước (D08 §9.2): (a) cắt output Evaluator (bỏ `strength_tags`, `gap_tags` khỏi đường nóng, `max_tokens` 350 → ~200); (b) cho Interviewer chạy song song với Evaluator ở lượt mà policy không cần điểm mới (ví dụ `clarify`, lượt đầu topic) hoặc dùng điểm tạm của precheck; (c) thử model nhanh hơn cho Evaluator. Mỗi bước đo lại bằng harness.
2. **Planner 13–17 s, 22% phiên rơi về plan dự phòng.** Đề xuất: giảm output (code tự sinh `backup_question` và `opening_hint` khi thiếu, LLM chỉ chọn topic và viết `key_points`), hoặc thử model nhanh hơn cho Planner; cân nhắc nâng hạn lên 25 s (giới hạn contract cho event đầu).
3. **Persona giỏi chỉ được `near`.** Chưa kết luận: có thể Evaluator khắt khe đúng thiết kế, có thể Simulator "well" trả lời chưa đủ sâu, hoặc ngưỡng verdict (BRU-07, giả định) chưa hợp. Cần golden set có nhãn người trước khi chỉnh.
4. **`overall.summary` của Reporter chưa được kiểm bằng chứng.** Phiên `junior-java-weak` (1.5 điểm) có summary khen "thể hiện tốt trong phần Đa luồng" dù `strengths` rỗng. Đề xuất: đưa vào prompt cấm khen ngoài `strengths`, hoặc kiểm code (summary không được nhắc topic điểm < 5).
5. Interviewer quá 5 s chờ token đầu ở 1/94 lượt → câu dự phòng; theo dõi khi đổi model.

## Câu hỏi chưa giải quyết
- Ưu tiên giảm độ trễ hay giữ chất lượng chấm (model Evaluator)?
- Có chấp nhận nâng hạn Planner lên 25 s không?
- Giá OpenRouter hiện hành cho `gpt-4o-mini` (để thay giá giả định)?
