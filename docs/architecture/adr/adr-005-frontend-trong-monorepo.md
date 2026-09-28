# ADR-005: Frontend đặt trong monorepo (apps/web)

**Ngày:** 2026-09-28  
**Trạng thái:** Accepted

## Bối cảnh

Frontend (React/Next.js) có thể nằm trong monorepo hiện tại hoặc tách repo riêng.

## Quyết định

Frontend đặt tại **`apps/web`** trong monorepo, dùng Next.js.

## So sánh

| Tiêu chí | Monorepo (apps/web) | Repo riêng |
|---|---|---|
| Shared tooling | ESLint, Prettier, Husky dùng chung | Phải cấu hình lại |
| Full-stack PR | Một PR cho cả FE + BE | Cần 2 PR, đồng bộ khó |
| Turborepo cache | FE được cache chung pipeline | Không có |
| CI/CD | Một pipeline, Turborepo chỉ build what changed | Pipeline riêng |
| Team friction | Thấp — 3 người cùng repo | Cao — switch context giữa repo |
| Repo size | Lớn hơn, nhưng Turborepo handle tốt | Nhỏ hơn từng repo |

## Lý do

Với team 3 người làm đồ án tốt nghiệp:
- **Một repo, một branch, một PR** giảm friction tối đa
- Turborepo đã có sẵn, chỉ cần thêm `apps/web` vào workspace
- Shared types/enums từ `libs/common` dễ dàng import
- CI chỉ cần một pipeline

## Hệ quả

- Thêm `apps/web` vào `pnpm-workspace.yaml`
- Next.js project với TypeScript, Tailwind CSS
- Có thể share types từ `libs/common` (DTO, enums)
- APISIX route `/` tới apps/web (hoặc proxy riêng cho dev)
