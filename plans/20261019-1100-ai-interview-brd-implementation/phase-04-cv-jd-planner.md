# Phase 04. CV Parser, JD Parser, Planner

## Context Links
- [plan.md](plan.md) · [design 01](../../docs/ai-service/01-input-schema-and-cv-processing.md) · [design 02 §3.3.1–3.3.2](../../docs/ai-service/02-multi-agent-architecture-and-prompts.md) · quyết định A11 (JD) trong [docs/ai-service/README.md](../../docs/ai-service/README.md) · FR-AI-003, 013–017, 020–023

## Overview
- **Priority:** P1 · **Status:** đang làm (2026-10-22): CV Parser LLM (`thang/cv-parser-llm`), JD Parser (`thang/jd-parser`), Planner LLM (`thang/planner-llm`) · **Tuần:** W3–W4
- Thay ba agent mock bằng LLM thật: CV Parser, **JD Parser (mới, S2-AIE-6)** và Planner; áp cấu hình thời lượng 15–20 phút.

## Key Insights
- Phần trích text, chuẩn hóa, redact PII, quét injection, tính số năm kinh nghiệm đã là code thật (`cv_text.py`, `mock_cv_parser.py`); chỉ bước trích xuất có cấu trúc cần LLM.
- JD là dữ liệu không tin cậy như CV, **không vào RAG** (A11). `jd_profile` map kỹ năng về `topic_id`; yêu cầu ngoài catalog đánh dấu `out_of_catalog`.
- Mock Planner hiện chia theo 30 phút; cần công thức mới.

## Requirements
- FR-AI-013 (CvProfile qua schema), 015 (không CV vẫn chạy), 016 JD Parser, 017 `jd_profile` vào `/api/start`, 020 Planner, 021 kiểm plan + repair + plan dự phòng, 022 `reference_snippets`, 023 Planner tăng trọng số theo `jd_profile`, 003 (công thức thời lượng).
- NFR: PERF04, PERF07, SEC02, SEC03, PRIV01, PRIV02, QUAL (10 CV mẫu, 3 CV injection).

## Architecture
```
/api/cv/parse  : bytes ─▶ cv_text (code) ─▶ CV Parser LLM ─▶ hậu kiểm (code) ─▶ CvProfile
/api/jd/parse  : text  ─▶ redact + injection scan ─▶ JD Parser LLM ─▶ jd_profile
/api/start     : track, level, duration, cv_profile?, jd_profile? ─▶ Planner LLM ─▶ validate ─▶ plan (+RAG snippets)
                                                        └─ lỗi ─▶ plan dự phòng (code, mock_planner)
```
Số topic technical = `max(2, round(gốc × thời lượng / 30))`; turn cap = 1.6 × số lượt dự kiến (đề xuất 16 cho 20 phút).

## Related Code Files
- **Tạo:** `app/agents/{cv_parser,jd_parser,planner}.py`, `app/prompts/{cv_parser,jd_parser,planner}.v1.md`, `app/models_jd.py`, `app/plan_validator.py`, `tests/test_plan_validator.py`, `tests/test_jd_parse.py`, `evals/cv_samples/` (CV tổng hợp, không PII thật).
- **Sửa:** `app/main.py` (route `/api/jd/parse`, `jd_profile` trong start), `app/models_interview.py`, `app/mock_planner.py` (công thức 15–20 phút, làm dự phòng), `docs/ai-service/06-api-contract.md`, `docs/architecture/api-contracts.md`.

## Implementation Steps
1. Contract trước: thêm `/api/jd/parse`, `jd_profile`, thời lượng 15–20 vào docs và mock, báo FSD (Phase 07 khóa).
2. CV Parser LLM: prompt `temperature 0`, schema CvProfile, không xuất tên/liên hệ/tên công ty; code ghi đè `total_years_experience`, `flags`.
3. JD Parser LLM: `must[]`, `nice[]`, ánh xạ `topic_id`, `out_of_catalog[]`; xóa trường chứa chỉ dẫn nghi ngờ, đặt cờ.
4. Planner LLM: nhận catalog đã lọc theo track + level (~15 topic), `cv_profile`, `jd_profile`; `plan_validator` (số topic đúng template, `catalog_ref`/`cv_ref` tồn tại, không trùng, độ khó trong khoảng, có `backup_question`); repair 1 lần; lỗi thì dùng plan dự phòng.
5. Sau plan hợp lệ gọi retriever lấy `reference_snippets` (Phase 03).
6. Kiểm với 10 CV mẫu (PDF, DOCX), 3 CV và 2 JD chứa injection.

## Todo List
- [x] Contract JD cập nhật (docs + mock): `/api/jd/parse`, `jd_profile` trong `/api/start`
- [x] CV Parser LLM + test (LLM giả); 10 CV mẫu + `evals/run_cv_samples.py` (parser quy tắc qua kiểm cứng; LLM thật chưa chạy)
- [x] JD Parser LLM + test injection (LLM giả; parser quy tắc làm mặc định và dự phòng; LLM thật chưa chạy)
- [ ] Planner LLM + validator + fallback + công thức 15–20
- [ ] 10 CV mẫu ra profile hợp lệ; 3 CV injection không lọt

## Success Criteria
- Plan hợp lệ 100% (kể cả khi LLM lỗi nhờ fallback); có CV liên quan thì topic intro `source = cv`; có `jd_profile` thì ≥ 1 topic technical ưu tiên theo JD; injection không đổi plan.

## Delivery (bàn giao)
- CV Parser LLM + prompt + tập CV mẫu
- JD Parser: `POST /api/jd/parse`, `jd_profile` trong `/api/start`
- Planner LLM + `plan_validator` + plan dự phòng + công thức 15–20 phút

## Cách test và nghiệm thu
1. `pytest` với FakeLlm: schema hợp lệ, hậu kiểm, injection bị loại
2. `python -m evals.run_cv_samples`: 10 CV (PDF, DOCX) ra profile hợp lệ; 3 CV injection không lọt chỉ dẫn
3. JD: 2 JD injection không đổi plan; yêu cầu ngoài catalog ra `out_of_catalog`
4. Planner: bảng test công thức (Junior 20 phút = 1 intro + 3 technical + 1 scenario; 15 phút = 2 technical); LLM trả plan sai → dùng plan dự phòng, test chứng minh

## Đồng bộ tài liệu (bắt buộc, cùng PR với thay đổi)
**Contract trước code**: `docs/ai-service/06-api-contract.md` và `docs/architecture/api-contracts.md` (JD endpoint, `jd_profile`, thời lượng). BRD (BR-23, A11), FR-AI-013/016/017/020–023/003, L2 (luồng JD, I16), ADR-008 (thêm JD Parser), NFR PERF07/SEC12/PRIV14.
Sau khi sửa: chạy `python apps/ai-service/scripts/check_docs.py` (link, ID, truy vết BR→FR→NFR, số lượng trong mục lục).

## Nhánh
3 nhánh độc lập: `thang/cv-parser-llm`, `thang/jd-parser`, `thang/planner-llm` (Planner sau cùng vì cần hai nhánh kia). Mỗi nhánh một PR; mô tả PR ghi lại kết quả các bước test ở trên.

## Risk Assessment
- Planner dài (≈ 15–25 s) → chạy một lần, hiển thị trạng thái chờ; mức tin cậy của JD map thấp → `out_of_catalog`, không ép.
- Phụ thuộc FSD `getJobDescription` (S2-FSD-11) → dùng JD dán tay trong harness.

## Security Considerations
- CV/JD thô chỉ qua parser; các agent sau chỉ nhận profile đã qua schema; redact PII trước LLM; không log nội dung.

## Next Steps
Phase 05 (Evaluator), Phase 06 (Interviewer đọc plan).
