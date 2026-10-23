# Specification Quality Checklist: JD Crawling & Seeding

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-23
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [ ] No [NEEDS CLARIFICATION] markers remain — còn 3 (NC-1 schema `job_db`, NC-2 S2-DE-3 Bắt buộc/Stretch, NC-3 500
  JD + nguồn hợp lệ); cố ý để lại vì phụ thuộc FSD/AIE/team
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
- [ ] Feature meets measurable outcomes defined in Success Criteria — SC-001, SC-004, SC-005 phụ thuộc kết luận NC-1..3
- [x] No implementation details leak into specification

## Notes

- Tên `ai_db`, `knowledge_chunks`, `job_db`, `job_postings`, `source_type = job_description` là tên contract dữ liệu đã
  chốt trong constitution / rag-design / data-model, giữ để truy vết (cùng cách làm spec 005). Thư viện crawl, cách
  render, vị trí code để ở plan.
- Mục "Kiểm tra nguồn crawl" ghi kết quả robots.txt/ToS ngày 2026-10-23 (itviec: robots cho phép, không cần JS, ToS
  2.2 hạn chế sao chép; topcv: robots cho phép trang job nhưng Cloudflare 403 mọi trang, ToS không đọc được). Plan
  MUST kiểm tra lại trước lần crawl thật.
- Trước `/speckit-plan`: chạy `/speckit-clarify` hoặc chốt NC-1 (FSD), NC-2 (AIE + DE), NC-3 (team) trong PR review,
  rồi chạy lại validation.
