## Summary
Sprint 2 · `005-rag-knowledge-base-qa` · **T041**: DE duyệt nhãn golden set RAG của AIE (`evals/rag_golden.json`, 24 query) và bộ held-out (`evals/rag_golden_holdout.json`, 32 query). Nhãn trỏ vào `qa_id` của DE nên AIE đã nhờ DE duyệt (2026-10-24).

@thangp97 nhờ Thắng xác nhận **query g21 mới** (mục dưới); nếu đồng ý thì điền `"approved_by"` cho g21.

## Thay đổi
- **24 query chính**: 24/24 `qa_id` có trong kho, `category` khớp `filters` 8/8; 22 query giữ nguyên.
  - **g02** thêm `de-qa-1016`: query "Lỗi tràn bộ nhớ heap sau vài ngày chạy, cách tìm nguyên nhân rò rỉ" không nói ngôn ngữ; 1016 (Node.js OOMKill vài ngày, điều tra khi `heapUsed` tăng) trả lời đầy đủ như 1104 (Java).
  - **g21** viết lại query: câu cũ `event loop bi chan lam latency p99 tang du cpu thap` mâu thuẫn chính đáp án của nhãn 1000 ("libuv threadpool bị bão hòa chứ không phải event loop bị block"); 1017 (event loop bị chặn) lại có một core CPU 100% nên cũng không khớp. Báo cáo eval 10-24 của AIE cũng ghi g21 trượt vì "top-3 là cặp Node.js performance gần nghĩa nhưng không phải nhãn".
    - Câu mới: `dich vu node gan nhu khong ton cpu ma cac yeu cau bam mat khau va mo tep van phai xep hang cho`, trùng 17% từ với câu hỏi 1000 (câu cũ 45%).
    - DE đã cân nhắc và bỏ câu `nodejs p99 latency tang vot du cpu thap, doc file va goi crypto deu cham` vì trùng 80%, lộ đáp án.
    - Query do DE viết sau khi biết đáp án nên **g21 chưa có `approved_by`**.
- **32 query held-out**: 32/32 đúng, không sửa nhãn.
- `approved_by: "minhtuann1102"` cho 55/56 query (trừ g21); `status` hai file ghi ngày duyệt và thay đổi.
- Docs: `rag-design.md` §5, FR-AI-061, NFR-AI-QUAL14 bỏ "chờ DE duyệt"; 005 `tasks.md` T041 ghi tiến độ (chưa tick).
- Báo cáo duyệt kèm bằng chứng từng query: `plans/reports/golden-review-261028-1508-rag-golden-24-queries.md`.
- Phần lớn diff hai file JSON là do hook `lint-staged` chạy `prettier --write` cho `*.json` (một query / dòng → nhiều dòng; held-out thụt 1 → 2). Nội dung đổi: g02, g21, `status`, `approved_by`.

## Cách duyệt
Script tạm đọc 144 cặp curated + 4.359 cặp crawl (= 9.006 record trên Supabase). Mỗi query kiểm:
1. nhãn có thật;
2. cặp được gán có trả lời trọn query không;
3. có cặp curated nào khác trả lời đầy đủ như vậy mà chưa gán không. Ứng viên lấy theo xếp hạng BM25 rồi đọc tay. Test chỉ cho nhãn `de-qa-*`, nên cặp crawl không xét;
4. nhóm, `filters` và độ trùng chữ với câu hỏi gốc.

## Recall
- Trước sửa (AIE đo 2026-10-24, không mở rộng truy vấn): 0,875; trượt g04, g05, g21. g04, g05 là lỗi truy hồi tiếng Việt thuần: nhãn đúng, không cặp curated nào khác trả lời trọn query.
- **Sau sửa: chưa đo.** DE sẽ chạy `evals.run_rag` (chính + held-out, có và không có `--no-expand`) rồi dán bảng, bỏ draft.

## Test
- `apps/ai-service`: `pytest` **411 passed, 5 skipped** (gồm `test_rag_golden_and_metrics.py`).

## Còn mở
- Thắng đồng ý câu g21 mới không? Nếu muốn giữ ý "event loop bị chặn" thì cần viết một query riêng nhắm 1017.
- Ghi chú độ khó:
  - g22, g24 (nhóm không dấu) và h29, h30 (held-out) gần như chép câu hỏi gốc, nên recall của các nhóm này hơi lạc quan.
  - Nhóm `vi_to_en` vẫn trống (chưa có textbook, 012 ở S3), nên FR-020 "phủ 5 nhóm" chưa đạt.
- Kho Supabase index bằng model embedding nào (3-small hay 3-large theo ADR-010)? Lúc đo, `EMBEDDING_MODEL` phải trùng model đó.
