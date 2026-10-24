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

- [ ] No [NEEDS CLARIFICATION] markers remain — 2026-10-24: NC-2, NC-3 đã chốt (Clarifications); còn NC-1 schema
  `job_db` (chờ FSD), chỉ chặn US4, cố ý để lại
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
- [ ] Feature meets measurable outcomes defined in Success Criteria — SC-005 phụ thuộc NC-1; SC-004 là Stretch (US3)
- [x] No implementation details leak into specification

## Notes

- Tên `ai_db`, `knowledge_chunks`, `job_db`, `job_postings`, `source_type = job_description` là tên contract dữ liệu đã
  chốt trong constitution / rag-design / data-model, giữ để truy vết (cùng cách làm spec 005). Thư viện crawl, cách
  render, vị trí code để ở plan.
- Mục "Kiểm tra nguồn crawl" ghi kết quả robots.txt/ToS ngày 2026-10-23 (itviec: robots cho phép, không cần JS, ToS
  2.2 hạn chế sao chép; topcv: robots cho phép trang job nhưng Cloudflare 403 mọi trang, ToS không đọc được). Plan
  MUST kiểm tra lại trước lần crawl thật.
- 2026-10-24: NC-2, NC-3 chốt bởi DE (spec Clarifications); kiểm nguồn bổ sung từ IP cá nhân; plan chạy với NC-1 còn
  mở vì chỉ ảnh hưởng US4.
