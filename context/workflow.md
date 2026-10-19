# Quy trình làm việc (bắt buộc)

Owner: Thắng (vai trò AIE). Hiệu lực từ 2026-10-19.

## 1. Một tính năng, một nhánh

- Tên nhánh: **`thang/<tính-năng>`** (username/feature), chữ thường, gạch ngang. Ví dụ `thang/llm-foundation`.
- Mỗi nhánh tách từ `main` (hoặc từ nhánh phụ thuộc, ghi rõ trong PR "xếp chồng trên ..."). Một nhánh một PR.
- Không push thẳng vào `main`. Không gộp nhiều tính năng độc lập vào một nhánh.

## 2. Xong một việc thì: commit, push, mở PR vào `main`

Owner đã cho phép thường trực. Mỗi lần hoàn thành một việc (một tính năng hoặc một phần có thể review độc lập):

1. Chạy test và `python apps/ai-service/scripts/check_docs.py` (xem `environment.md`).
2. `git commit` theo Conventional Commits bằng tiếng Anh, **không có dòng ghi công AI**.
3. `git push -u origin thang/<tính-năng>`.
4. Mở PR vào `main`. Dùng `gh pr create --base main --head <nhánh>` (xem `environment.md`); nếu `gh` chưa đăng nhập thì dùng link `https://github.com/minhtuann1102/ai-recruitment-platform/pull/new/<nhánh>` và dán nội dung theo mẫu dưới.
5. Cập nhật `context/project-state.md` (trong PR kế tiếp hoặc cùng PR nếu liên quan).

## 3. Mỗi thay đổi phải đồng bộ tài liệu cùng PR

BRD, FR, NFR, kiến trúc L2 (`docs/ai-service/`), tài liệu thiết kế liên quan (`docs/architecture/`, ADR) và kế hoạch (`plans/`). Chạy `check_docs.py` trước khi commit. Đổi yêu cầu thì tăng phiên bản BRD và sửa banner ở FR, NFR, L2 (checker bắt lệch).

## 4. Mỗi phase có Bàn giao và Cách test

Xem các file `plans/<ngày>-ai-interview-brd-implementation/phase-*.md`. Mô tả PR phải ghi kết quả các bước test.

## 5. Mẫu mô tả PR

```
## Nội dung
(một đoạn)
## Kiểm thử
- lệnh đã chạy và kết quả
## Tài liệu đã cập nhật
- BRD / FR / NFR / L2 / thiết kế nào
## Phụ thuộc và rủi ro
- xếp chồng trên PR nào, điều chưa kiểm chứng
```

## 6. Điều không được làm

- Không commit `.env`, khóa API, dữ liệu cá nhân thật.
- Không bỏ qua hay xóa test đỏ, không mock giả để qua CI.
- File code mới nên dưới 200 dòng (Python dùng snake_case theo PEP 8).
- Không tự suy ra nhãn hay số đo: số liệu trong tài liệu phải ghi rõ là đã đo, giả định hay đề xuất.
