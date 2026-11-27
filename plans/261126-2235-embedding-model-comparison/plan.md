# Plan: so sánh embedding OpenAI vs sentence-transformers (RAG + matching)

Created 2026-11-26. Owner DE. Branch `docs/cv-jd-matching-comparison-spec` (no commit until owner asks).

**Why**: đề cương ghi "sentence-transformers đa ngôn ngữ", thực tế dùng `openai/text-embedding-3-small` (RAG + 017).
Repo chưa có số đo nào so hai loại (rag-design §1: chất lượng tiếng Việt "chưa đo"; ADR-010 chỉ so small vs large).
Mục tiêu: đo trước, quyết sau. Lý do trong đồ án phải dựa trên số liệu, không viết lý do sẵn.

## Models (pin HF revision trong kết quả)

| id | Model | Dim | Ghi chú |
|---|---|---|---|
| oa-small | `text-embedding-3-small` | 1536 | hiện tại; RAG dùng vector đã lưu trong ai_db (đọc) |
| oa-large | `text-embedding-3-large` @1536 | 1536 | tùy chọn, ~$0.21, trả lời "sao không dùng large" |
| st-minilm | `paraphrase-multilingual-MiniLM-L12-v2` | 384 | đúng chữ trong đề cương; max_seq 128 |
| st-e5 | `intfloat/multilingual-e5-base` | 768 | prefix `query: ` / `passage: ` |
| st-bge | `BAAI/bge-m3` (dense) | 1024 | mạnh nhất cho tiếng Việt, chậm trên CPU → chạy nền |

## Luật quyết định (ghi trước khi chạy, chép vào ADR-012 nháp)

- Một model chỉ "thắng" về chất lượng nếu khoảng tin cậy 95% bootstrap của hiệu số **không chứa 0**
  (RAG: bootstrap theo truy vấn; matching: theo CV). Không thì coi như ngang, quyết theo vận hành.
- Vận hành đo như VM thật: `e2-standard-4` = 4 vCPU / 16 GB, không GPU → torch 4 thread.
- Không dùng "schema cố định 1536" làm lý do (đệm 0 giữ nguyên cosine). Chi phí đổi thật = index lại RAG + matching
  cùng AIE.
- Kết quả 264 cặp 017 là bằng chứng dev; matching chốt trên bộ test 019 sau khi khóa.

## Phase 1 — RAG (ai-service evals, file mới, không sửa file của AIE)

`apps/ai-service/evals/embedding_model_experiment.py` (+ module phụ nếu >200 dòng),
`apps/ai-service/evals/requirements-embedding-experiment.txt` (sentence-transformers, torch CPU; không vào runtime).

1. Đọc corpus đúng phạm vi golden (`corpus` trong rag_golden.json) từ ai_db (aie_reader, chỉ đọc): id, content,
   content_hash, metadata, **và vector 3-small đã lưu**. Cache ở scratch / thư mục gitignored (nội dung crawl không
   commit).
2. Kiểm tra trước: bao nhiêu id `relevant` của golden (main + holdout) không còn trong corpus → báo cáo, nếu >0 thì
   ghi rõ trần recall.
3. Một đường tìm duy nhất cho mọi model: cosine trong bộ nhớ + `OVERFETCH` + `dedup` của `app.rag.retriever`, top-5.
4. Query: (a) **raw, vector-only = chỉ số chính**, nhóm vi + no_diacritics nổi bật; (b) raw+rewrite: sinh bản viết
   lại LLM **một lần**, lưu file, mọi model dùng cùng chuỗi.
5. Chỉ số: recall@5 theo nhóm (dùng `rag_metrics.recall_by_group`), MRR; bootstrap CI hiệu số so với oa-small.
6. Vận hành: thời gian embed corpus, p50/p95 embed 1 truy vấn (4 thread), RSS, load time, tỉ lệ chunk bị cắt do
   max_seq_length.
7. Golden: chạy bản main (ghi SHA file) và bản arp-golden 3c7dae9 nếu đọc được; báo cả hai.

## Phase 2 — Matching (data-pipeline, offline, không qua endpoint)

`apps/data-pipeline/pipeline/match_embedding_experiment.py` (+ phụ). Dùng lại `jd_match_text.build_match_text`,
`app/matching/cv_text.build_cv_text` (hoặc bản sao tất định nếu import chéo không được), `scorer.py` và
`match_eval_metrics`.

1. **Cổng tái lập**: harness offline với vector OpenAI (3-small) phải ra lại nDCG@5 0,883 / P@5 0,642 trên 264 cặp
   (cùng bộ lọc như endpoint, as_of 2026-11-01). Không khớp → dừng, tìm nguyên nhân trước khi đổi model.
2. Đổi model: chỉ số chính = **cosine-only** xếp hạng theo CV (không phụ thuộc thang điểm); phụ = điểm đầy đủ với
   trọng số cũ 0,6/0,3/0,1, gắn cờ "trọng số chỉnh cho thang cosine của 3-small".
3. Báo cáo tách JD vi / en (như eval-analysis 017), bootstrap theo CV.

## Phase 3 — Tài liệu

- `docs/architecture/adr/adr-012-embedding-model-openai-vs-sentence-transformers.md`: bối cảnh (lệch đề cương), luật
  quyết định, bảng số, quyết định (owner chốt), hệ quả.
- `rag-design.md` §1 trỏ ADR-012; spec 019 FR-020 thêm hệ "embedding ST + bộ chấm 017".
- Báo cáo số thô: `plans/261126-2235-embedding-model-comparison/reports/`.

## Thứ tự / phân việc

Phase 1 và 2 độc lập (khác app, khác file) → 2 worker sonnet song song. Phase 3 sau khi có số. Review opus cuối.

## Rủi ro

- Golden 24 + 32 truy vấn: chỉ phát hiện chênh lớn. Nói rõ trong ADR.
- HF download qua TLS interception → inject truststore ở entry point; pip cần `--use-feature=truststore`, sandbox off.
- bge-m3 trên CPU chậm (ước lượng 30–90 phút cho ~9k chunk) → chạy nền, cache theo (model revision, content_hash).

## Câu hỏi mở

- Golden bản nào là chính (main hay 3c7dae9)? Mặc định: main, báo thêm 3c7dae9.
- Chạy oa-large không (~$0.21)? Mặc định: có.
