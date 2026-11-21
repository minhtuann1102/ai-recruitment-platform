# Specification Quality Checklist: Gợi ý việc làm theo độ tương đồng CV–JD

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-11-21
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) — theo lệ repo (016, 014): chỉ trích file / bảng hiện có làm bằng chứng phụ thuộc, không chọn công nghệ mới
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain (FR-018, FR-025 chốt 2026-11-21)
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded (GĐ1 / GĐ2, Ngoài phạm vi)
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- FR-027 (nơi lưu vector CV cho nhóm open-to-work) để plan GĐ2 chốt.
- AIE cần đồng ý dùng `knowledge_chunks` (`source_type = job_description`) và module mới trong ai-service trước khi code.
