# Seed data (mock)

Dữ liệu mock cho RAG trong giai đoạn đầu, **do AIE tự soạn, `synthetic: true`**. DE sẽ bổ sung dữ liệu thật vào cùng bảng `knowledge_chunks` (xem `docs/architecture/rag-design.md`).

| File | source_type | Số lượng | Nguồn |
|---|---|---|---|
| `qa_seed.json` | `interview_qa` | 50 cặp (5 category, 3 độ khó) | Tự soạn từ kiến thức chung, tiếng Việt xen thuật ngữ Anh. **Cần người kiểm tra độ chính xác của đáp án** |
| `tech_notes_seed.json` | `textbook` | 19 ghi chú công nghệ | Tự soạn (`license: own-work`) |

Quy ước:
- Không dùng làm golden set. Golden set phải tách riêng và không trùng với các câu này.
- Khi có dữ liệu thật, lọc/xóa bằng `synthetic = true`.
- Không commit dữ liệu có giấy phép không rõ (ví dụ dataset Hugging Face không ghi license).
