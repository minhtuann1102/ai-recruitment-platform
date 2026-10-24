# Đánh giá dữ liệu DE trong ai_db (đo 2026-10-24)

Nguồn: `knowledge_chunks` trên Supabase (đọc bằng `aie_reader`), pipeline `apps/data-pipeline/`, seed `apps/data-pipeline/data/seeds/interview_qa/`. Số liệu đo trực tiếp bằng SQL; chất lượng nội dung ước lượng bằng LLM (gpt-4o-mini) chấm 150 cặp ngẫu nhiên, **không thay người duyệt**.

## Kho có gì

- 9.006 chunk = 4.503 cặp Q&A × 2 (`question`, `qa_pair`), toàn bộ `source_type = interview_qa`, `language = vi`. **Chưa có textbook, chưa có tình huống / system design.**
- 4.359 cặp crawl từ GitHub (`de_crawled_qa`): crawl tiếng Anh → LLM dịch sang tiếng Việt (giữ thuật ngữ Anh), LLM gán `topic_id` và độ khó (`pipeline/llm_enricher.py`). 144 cặp `hard` do DE viết tay (`de_interview_qa`, có `reviewed_by`).
- Cả 90 topic trong catalog đều có câu; trung vị 21 câu/topic, p90 ~110, tối đa 451.

| Track | easy | medium | hard | Tổng |
|---|---|---|---|---|
| frontend_react | 707 | 697 | 27 | 1.431 |
| devops_engineer | 794 | 502 | 20 | 1.316 |
| python_backend | 392 | 180 | 22 | 594 |
| java_backend | 241 | 215 | 34 | 490 |
| nodejs_backend | 159 | 182 | 29 | 370 |
| ai_engineer | 79 | 169 | 54 | 302 |

## Chất lượng (mẫu 150 cặp, LLM chấm)

| Khía cạnh | Kết quả |
|---|---|
| Đáp án | good 94%, thin 5%, wrong 0.7% |
| Đúng trọng tâm topic được gán | main 68%, related 7%, **off 25%** (vd "GROUP BY" gán vào topic index SQL; "đọc input console" vào HashMap; "Route 53" vào Linux) |
| Nhãn độ khó DE so với chấm lại | đồng ý **69%**; DE thiên về dễ (46/75 "easy" bị chấm lại là "medium") |
| Hợp để hỏi miệng | 85% (15% là câu đố, trắc nghiệm, yêu cầu viết code) |
| Câu đọc thành lời được (1 dòng, không code, ≤ 200 ký tự) | 4.293/4.503 (95%) |
| Câu trùng nguyên văn | 0 |

## Độ phủ theo level (topic có ≥ 3 câu đọc được ở mức độ khó của level)

| Level | Mức | Topic đủ / topic của level |
|---|---|---|
| Fresher | easy | 34/37 |
| Junior | easy | 50/63 |
| Middle | medium | 54/80 |
| Senior | hard | **6/58** (tính cả medium: 36/58) |

63/90 topic không có câu `hard` nào. 12 topic có < 3 câu, chủ yếu track AI (LLM, RAG, agent, MCP, guardrails, LLMOps) và `java.spring.transaction`, `py.async.celery-queues`.

## Việc duyệt và giấy phép

- `data/reviews/translation-review.csv`: 440 dòng mẫu để duyệt bản dịch, **0/440 đã có verdict**. Tức là bản dịch và nhãn của 4.359 cặp crawl **chưa có người kiểm**.
- Giấy phép theo từng cặp: `unknown` 2.147, **CC-BY-NC-ND-3.0 1.145**, MIT 886, CC-BY-4.0 292, CC-BY-SA-4.0 33. ND (No Derivatives) không cho phép bản dịch; `unknown` chưa rõ quyền dùng. Cần DE và owner quyết định trước khi demo hoặc công bố.

## Kết luận: đã đủ chưa

**Đủ để chạy giai đoạn 1** cho phần technical của Fresher, Junior và phần lớn Middle: câu hỏi và đáp án chuẩn có sẵn, đáp án nhìn chung đúng, đã tích hợp (PR #39).

**Chưa đủ để đạt kết quả tốt nhất:**
1. Gán topic lệch 25% → câu hỏi lạc chủ đề, đáp án chuẩn không khớp trọng tâm topic.
2. Nhãn độ khó lệch, thiếu câu `hard` → senior không được hỏi đúng mức; phân biệt ứng viên giảm.
3. Chưa có người duyệt bản dịch và nhãn → không thể gọi là "đã kiểm chứng" (trừ 144 câu hard tự viết).
4. Giấy phép: 73% chưa rõ hoặc không cho phép dịch.
5. Thiếu loại dữ liệu: tình huống / system design (phase scenario), textbook, follow-up theo chuỗi, JD thật (spec 009 còn Draft), CV mẫu ẩn danh.
6. Track AI mỏng (302 cặp, 12 topic < 3 câu).

Kế hoạch xử lý: `context/next-phase-plan.md`.
