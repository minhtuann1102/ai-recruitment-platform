# Specification Quality Checklist: Textbook Ingestion & RAG Quality

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-11-14
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain — 5 câu hỏi cho AIE đều có mặc định, ghi ở mục "Câu hỏi cho AIE"
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [ ] Feature meets measurable outcomes defined in Success Criteria — chưa implement; SC-007 phụ thuộc AIE đo
- [x] No implementation details leak into specification

## Notes

- Tên `knowledge_chunks`, `source_type = 'textbook'`, `category`, `topic_id`, `difficulty`, `RAG_TEXTBOOK_ENABLED`,
  `scn.*` là tên contract dữ liệu / cấu hình đã có trong constitution, rag-design và code ai-service, giữ để truy vết
  (cùng cách làm spec 005, 009). Thư viện crawl, cấu trúc module, định dạng danh sách trang để ở plan.
- Mục "Bối cảnh" ghi kết quả đọc code ai-service ngày 2026-11-14 (bộ lọc scenario, category chính của track, ngân sách
  tài liệu theo lượt). Plan MUST đọc lại nếu AIE đổi các file đó.
- Ngưỡng ở SC-001 (80% tình huống ≥ 3 đoạn), SC-004 (80% tình huống tìm trúng trong ba kết quả đầu), SC-006 (≤ 3/50
  đoạn nhiễu) và SC-008 (300–1.500 đoạn) là mặc định DE đặt, chưa có số đo nền; chỉnh sau lô thử.
- Thu hẹp phạm vi S3-DE-1..3 so với sprint plan (10+ nguồn, ~5.000 chunk) do DE chốt 2026-11-14; cần AIE và FSD xác
  nhận khi review spec. Đề cương nộp GVHD không ghi số lượng.
- Giấy phép từng nguồn chưa kiểm ở bước spec (FR-004, FR-005): là việc đầu tiên của plan.
