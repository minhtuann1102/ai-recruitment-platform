# Tổng hợp: OpenAI vs sentence-transformers (RAG + matching), 2026-11-27

Chi tiết: [rag-embedding-results.md](rag-embedding-results.md), [matching-embedding-results.md](matching-embedding-results.md).
Luật quyết định (ghi trước khi chạy): một model chỉ "hơn" hoặc "kém" khi khoảng tin cậy 95% bootstrap của hiệu số không
chứa 0. Nếu không, coi là ngang và quyết theo vận hành.

## 1. RAG (golden của AIE, 8.356 chunk interview_qa, recall@5)

Chỉ số chính: truy vấn gốc, chỉ tìm vector. Mọi model đi cùng một đường tìm, đã kiểm khớp 61/61 với DB.

| Model | main (24) | holdout (32) | Kết luận holdout (cả 2 bản golden) |
|---|---|---|---|
| OpenAI 3-small (đang dùng) | 0,833 | 0,562 | mốc |
| OpenAI 3-large | 1,000 | 0,906 | **hơn** |
| MiniLM (tên trong đề cương) | 0,750 | 0,562 | ngang |
| multilingual-e5-base | 1,000 | 0,844 | **hơn** |
| bge-m3 | 1,000 | 0,875 | **hơn** |

- Ở bộ main, kết luận của e5 và bge-m3 đổi thành "ngang" khi dùng golden bản arp-golden 3c7dae9. Kết quả trên holdout
  thì vững với cả hai bản golden.
- Có thêm bước LLM viết lại truy vấn (như production đang làm), chênh lệch gần như biến mất: mọi model ngang 3-small.
- Đường production thật (hybrid BM25 + vector + viết lại) **chưa đo** trong thí nghiệm này.

## 2. Matching (dev 017: 264 cặp, 24 CV, nhãn LLM), nDCG@5 chỉ theo cosine

| Model | nDCG@5 | Kết luận |
|---|---|---|
| 3-small | 0,842 | mốc |
| 3-large | 0,888 | ngang |
| MiniLM | 0,851 | ngang |
| e5 | 0,772 | **kém** |
| bge-m3 | 0,827 | ngang |

- Bước tái lập 017 khớp, trừ một chỗ đảo thứ tự top-5 do API trả vector lệch nhẹ (đã chấp nhận, có ghi lý do).
- Kết quả chính thức của matching chờ bộ test 019.

## 3. Vận hành (CPU 4 luồng, máy dev đang bận nên số chỉ để tham khảo)

| Model | RAM | Truy vấn RAG p50 | Embed cả kho | Bị cắt |
|---|---|---|---|---|
| MiniLM | ~1,3 GB | 17 ms | 3 phút | 33% chunk (128 token) |
| e5 | ~2,0 GB | 43 ms | 15 phút | 8% |
| bge-m3 | ~2,1 GB (embed kho 2,8 GB) | 163 ms | 52 phút | 0% |
| OpenAI | không chạy model tại chỗ | 280–290 ms (qua mạng) | 31 s, $0,21 (large) | 0% |

## 4. Đọc kết quả (owner quyết)

- **MiniLM, đúng tên trong đề cương, không hơn 3-small ở bất kỳ phép đo nào.** Đây là lý do có số liệu cho việc
  không dùng nó.
- e5 và bge-m3 tốt hơn 3-small ở RAG khi không viết lại truy vấn, nhưng ngang khi có bước viết lại như production. e5
  lại kém ở matching. bge-m3 cần khoảng 2 GB RAM thường trực trên VM 16 GB dùng chung.
- 3-large tốt hơn ở RAG khi không viết lại, ngang ở matching. Đổi sang 3-large tốn khoảng $0,21 và phải index lại cùng
  AIE (đúng phần 2 đang hoãn của ADR-010).
- Lý do giữ OpenAI mà số liệu đỡ được: với đường truy vấn đang chạy (có viết lại), không model sentence-transformers
  nào hơn 3-small; các model hơn ở chế độ không viết lại cần thêm khoảng 2 GB RAM và chạy CPU trên VM. **Không** dùng
  lý do "schema 1536".

## Việc tiếp

1. Chọn bản golden chính: bản trong repo hay arp-golden 3c7dae9 (DE đã duyệt).
2. Đo lại độ trễ khi máy rảnh, giới hạn 4 luồng.
3. Nếu muốn kết luận cho production: đo thêm đường hybrid + viết lại.
4. Viết ADR-012 sau khi owner chốt; matching chốt ở 019.
