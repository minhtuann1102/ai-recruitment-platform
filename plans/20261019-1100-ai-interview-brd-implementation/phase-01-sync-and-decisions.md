# Phase 01. Đồng bộ main và chốt quyết định

## Context Links
- [plan.md](plan.md) · [BRD §0.1–0.3, §12](../../docs/ai-service/requirements/01-brd.md) · commit `35a3cc2` trên `main` (quyết định 15/10) · [spec 005](../../specs/005-rag-knowledge-base-qa/spec.md)

## Overview
- **Priority:** P1 (chặn các phase còn lại) · **Status:** chưa bắt đầu · **Tuần:** W2 (19–25/10)
- Đưa nhánh làm việc về trạng thái khớp `main`, đóng các điểm lệch giữa BRD v0.3 và quyết định đã nằm trên `main`, mở PR tài liệu để FSD và DE review sớm.

## Key Insights
- `apps/ai-service` trên nhánh hiện tại **giống hệt** `main`; 4 commit chưa lên là tài liệu (BRD, FR, NFR, L2). `git merge-tree` báo merge sạch.
- `main` đã có quyết định 15/10 mà BRD chưa phản ánh: voice là Stretch do DE sở hữu, JD vào Planner, phiên riêng tư, DE sở hữu đường ghi RAG, 6 track.
- Constitution còn Proposed: gộp sửa đổi vào PR ratify rẻ hơn amend sau.

## Requirements
- Chốt Q1–Q6 trong plan.md. Cập nhật BRD lên v0.4, FR/NFR/L2 cho khớp.
- Thêm FR mới cho JD: **FR-AI-016** JD Parser, **FR-AI-017** `jd_profile` trong request `/api/start`, **FR-AI-023** Planner dùng `jd_profile`, **FR-AI-056** khối `requirements` trong report. Sửa FR-AI-062 (DE sở hữu đường ghi), nhóm L theo tùy chọn voice đã chọn.

## Architecture
Không đổi kiến trúc. Chỉ quyết định cách tách voice (A: lớp kênh ngoài ai-service; B: voice-gateway) và nơi đặt JD parse (endpoint `/api/jd/parse`, kết quả đi vào `/api/start`).

## Related Code Files
- **Sửa:** `apps/ai-service/app/catalog/models.py` (thêm category `Frontend`), 3 file YAML catalog + thêm `frontend_react.yaml`, `devops_engineer.yaml` từ `specs/005-.../contracts/topic-catalog-proposal/`; `tests/test_topic_catalog.py` (danh sách track).
- **Sửa docs:** BRD, FR, NFR, L2 (`docs/ai-service/requirements/`, `11-architecture-l2-containers.md`), `docs/ai-service/README.md`, ADR-008, `specs/README.md` (cột trạng thái 006, 011 trỏ về plan này).
- **Tạo:** ADR-009 chỉ khi chọn voice tùy chọn B.

## Implementation Steps
1. `git merge origin/main`, chạy `python -m pytest -q`, đẩy lên remote.
2. Chạy test trên **Python 3.11** (CI dùng 3.11): container `python:3.11-slim` hoặc xem kết quả CI. Sửa nếu đỏ.
3. Nhận đề xuất catalog của DE: thêm category `Frontend`, hợp nhất YAML, chạy `tests/test_topic_catalog.py` (mỗi level ≥ 5 topic, ≥ 1 scenario).
4. Viết BRD v0.4 + cập nhật FR/NFR/L2 theo Q1–Q6 đã chốt.
5. Mở PR tài liệu (1 PR) gồm BRD/FR/NFR/L2 + sửa README; nhờ FSD và DE review. Gửi riêng danh sách xác nhận cần từ FSD: contract, migration `interview_db`, `getCvFile`, `getJobDescription`.
6. Soạn đoạn sửa constitution (II một dòng cho kênh media nếu chọn B, V đường dữ liệu huấn luyện, VII framework có ADR) gộp vào PR ratify.
7. Cập nhật `specs/README.md` trạng thái 006, 011.

## Todo List
- [ ] Merge main, test 3.11 xanh
- [ ] Q1–Q6 có câu trả lời ghi lại (BRD §0.2)
- [ ] Catalog 6 track, test xanh
- [ ] BRD v0.4, FR/NFR/L2 đồng bộ
- [ ] PR tài liệu đã mở, FSD và DE đã nhận câu hỏi
- [ ] Sửa constitution đã đưa vào PR ratify

## Success Criteria
- `main` chứa BRD v0.4 và catalog 6 track; CI Python xanh; mọi quyết định Q1–Q6 có ghi nhận; FSD xác nhận bằng văn bản ít nhất contract và `getCvFile`.

## Risk Assessment
- FSD/DE chậm review → các phase 02–06 không phụ thuộc nên vẫn chạy; chỉ Phase 07 bị ảnh hưởng.
- Chọn voice B làm tăng phạm vi rất lớn → mặc định A, B chỉ khi có xác nhận bằng văn bản.

## Security Considerations
- PR tài liệu không chứa khóa API; không đưa `.env` vào git.

## Next Steps
Phase 02 và 03 chạy song song ngay sau bước 1–2.
