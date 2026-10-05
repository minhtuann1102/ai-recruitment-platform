# Contract: CI Pipeline

File: `.github/workflows/ci.yml`. Trigger: `pull_request` (mọi nhánh), `push` vào `main`, `develop`.
`concurrency: ci-${{ github.ref }}`, `cancel-in-progress: true`. Không dùng secret.

| Job | Bước | Lệnh | Thất bại khi |
|---|---|---|---|
| `node` | install | `pnpm install --frozen-lockfile` | lockfile lệch `package.json` |
| `node` | lint | `pnpm lint` | oxlint báo lỗi |
| `node` | types | `pnpm check-types` | lỗi TypeScript |
| `node` | test | `pnpm test` | test fail |
| `python` (matrix `ai-service`, `data-pipeline`) | guard | bỏ qua nếu `apps/<app>/requirements.txt` không tồn tại | — |
| `python` | install | `pip install -r requirements.txt` (+ `requirements-dev.txt` nếu có) | dependency lỗi |
| `python` | test | `pytest` trong `apps/<app>` | test fail |

Runtime: Node 22 (`actions/setup-node`, cache pnpm), pnpm theo `packageManager`, Python 3.11.
Mục tiêu: tổng thời gian ≤ 10 phút (SC-004). Branch protection (bắt buộc CI xanh) do người có quyền admin repo
bật sau khi workflow chạy ổn.
