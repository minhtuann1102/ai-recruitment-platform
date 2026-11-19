# Plan: DevOps + Monitoring + Eval (S4, DE)

Ngày: 2026-11-17 · Owner: DE (minhtuann1102) · Sprint 4: 23/11 → 07/12, Sprint 5 (E2E, báo cáo): 07/12 → 21/12

Nguồn sprint: `docs/sprint-plan.md` S4-DE-2 (seed, bắt buộc), S4-DE-3 (deploy staging, bắt buộc), S4-DE-4 (monitoring,
Stretch). Phần deploy + monitoring sẽ thành spec Spec Kit **014-staging-deploy-monitoring** (theo `specs/README.md`);
file này chốt phạm vi trước khi viết spec. Eval AI do AIE sở hữu (đã đồng ý chọn mẫu + ngưỡng cho 3.2); DE làm phần
dữ liệu + CI.

## Quyết định (DE, 2026-11-17)

- Hạ tầng: **Vercel** (web frontend, spec 013) + **GCP** (backend). Cảnh báo qua **email**. Ngân sách: không giới hạn
  (vẫn tránh lãng phí). Không có tính năng match job ↔ ứng viên → không cần eval riêng.
- **Đề xuất backend: một VM Compute Engine chạy Docker Compose** (giống máy dev), không tách Cloud Run ngay:
  - Lý do: còn 2 tuần; compose hiện có APISIX + etcd, Redis, MinIO, Postgres — chuyển sang Cloud Run phải đổi gateway,
    thay MinIO bằng GCS, Redis bằng Memorystore, Postgres bằng Cloud SQL: nhiều việc, rủi ro trễ.
  - ai-service dùng SSE dài: VM không bị giới hạn timeout request.
  - Sau demo, nếu cần co giãn: tách ai-service sang Cloud Run trước (stateless), giữ phần còn lại.
- **Monitoring dùng dịch vụ GCP** thay vì tự dựng Prometheus / Grafana / Uptime Kuma: Ops Agent trên VM (CPU, RAM,
  đĩa, log container, scrape `/metrics` Prometheus của ai-service + APISIX) → Cloud Monitoring (dashboard, alert email)
  + Cloud Logging; Uptime checks có sẵn. Ít container hơn, cảnh báo email có sẵn.

## Hiện trạng (đã kiểm trong repo)

- `docker-compose.yml`: db (Postgres), minio, redis, redisinsight, ai-service, etcd, apisix (+ homepage, adc); kafka đang tắt.
  Kho RAG `ai_db` ở Supabase (ngoài compose).
- Chỉ `apps/ai-service` có Dockerfile; auth / user / notification (NestJS) chưa có.
- CI: `.github/workflows/ci.yml` có job `node`, `python` (lint + test). Chưa có build image, deploy, eval.
- ai-service đã có `/metrics` Prometheus (`app/metrics.py`: request, duration, TTFT, agent calls/fallback, tokens,
  tool calls, RAG, kết quả chấm), Langfuse trace, `/api/health`.
- Endpoint AI: `/api/cv/parse`, `/api/jd/parse`, `/api/start`, `/api/next-turn`, `/api/finalize`, `/api/stt/phrases`.
- Eval AI đã có trong `apps/ai-service/evals/` (Evaluator golden + holdout + STT, judge Interviewer, RAG golden,
  CV samples có injection, persona simulate, cost/latency) và ~18 báo cáo `plans/reports/eval-*`.

## Phase 1 — Deploy staging (bắt buộc, S4-DE-3) · 23/11 → 30/11

| # | Việc | Xong khi |
|---|---|---|
| 1.1 | Dockerfile cho auth / user / notification (multi-stage, non-root) | `docker compose build` xanh |
| 1.2 | `docker-compose.staging.yml`: bỏ redisinsight; healthcheck mọi service; `restart: unless-stopped`; log driver json-file xoay vòng (`max-size: 10m`, `max-file: 3`) | `compose up` trên máy sạch, mọi health xanh |
| 1.3 | GCP: project, VM Compute Engine (e2-standard-4, 4 vCPU / 16 GB, đĩa SSD 100 GB, Ubuntu LTS), IP tĩnh, firewall chỉ mở 80/443 (+ SSH qua IAP) | SSH được, Docker chạy |
| 1.4 | Domain: mua trên **Vercel Domains** (DNS do Vercel quản, `app.<domain>` tự gắn vào project Vercel); thêm bản ghi `A api` → IP tĩnh VM trong Vercel DNS. Caddy trên VM tự lấy Let's Encrypt cho `api.<domain>`, đứng trước APISIX | `https://api.<domain>/api/health` xanh |
| 1.5 | Vercel: deploy web frontend (013), env `NEXT_PUBLIC_API_URL=https://api.<domain>`; CORS ở APISIX cho `app.<domain>` + `*-<team>.vercel.app` (preview) | Frontend gọi được API |
| 1.6 | Secrets: Secret Manager (hoặc `.env.staging` chỉ trên VM), mẫu `.env.staging.example` trong repo; Vercel env cho frontend | Không secret nào trong git |
| 1.7 | CI build + push image lên **Artifact Registry** khi merge `main` (Workload Identity Federation, không key JSON); deploy bằng script (`pull` + `up -d`) qua SSH / IAP | Merge → image mới → deploy 1 lệnh |
| 1.8 | Backup Postgres: cron `pg_dump` hằng ngày → bucket GCS (giữ 7 bản, lifecycle rule) + snapshot đĩa VM hằng ngày | Có bản backup + thử restore 1 lần |
| 1.9 | Seed staging (S4-DE-2): seed JD / company / candidate khi migration FSD (004, 007) sẵn sàng | Số bản ghi đạt sprint plan |

## Phase 2 — Monitoring (tối thiểu bắt buộc cùng deploy) · 28/11 → 03/12

| # | Việc | Công cụ |
|---|---|---|
| 2.1 | Uptime checks: `https://api.<domain>/api/health`, trang Vercel; cảnh báo hạn chứng chỉ | Cloud Monitoring Uptime |
| 2.2 | Ops Agent trên VM: CPU, RAM, **đĩa**, log container → Cloud Logging | Ops Agent |
| 2.3 | Ops Agent scrape Prometheus: ai-service `/metrics`, APISIX plugin `prometheus` (rate, 5xx, p95 theo route) | Ops Agent prometheus receiver |
| 2.4 | Dashboard AI: TTFT p95 theo `source`, fallback rate theo agent, lỗi theo mã, token/ngày theo agent, RAG lỗi / rỗng / độ trễ, phân bố kết quả chấm | Cloud Monitoring dashboard |
| 2.5 | Cảnh báo email (≤ 8): site down > 2 phút; 5xx > 5% / 5 phút; TTFT p95 > mốc `eval-261109-1648-ttft-breakdown`; fallback > 20%; đĩa > 80%; container restart lặp (log-based metric); token/ngày bất thường (gấp 3 trung bình 7 ngày — phát hiện vòng lặp, không phải ngân sách); backup > 24h hoặc cert < 14 ngày | Alerting policy → email |
| 2.6 | Frontend: Vercel Analytics + Speed Insights | Vercel |

Stretch (S4-DE-4): metric Postgres / Redis (Ops Agent có receiver), job số bản ghi `knowledge_chunks` theo
`source_type` + phễu phiên phỏng vấn (bắt đầu / hoàn thành), Error Reporting cho exception.

Không làm: label `session_id` / user / nội dung trong metrics (nổ cardinality + PII); tự dựng ELK / Grafana; Kafka chỉ
để đọc log.

## Phase 3 — Eval · 18/11 → 05/12

| # | Việc | Owner | Hạn |
|---|---|---|---|
| 3.1 | **Textbook trước/sau** (012 SC-007): đo nền cờ tắt → bật `RAG_TEXTBOOK_ENABLED` → đo lại tỉ lệ ý có căn cứ phase scenario + độ trễ | AIE đo, DE cấp dữ liệu | 23/11 |
| 3.2 | **Eval hồi quy trong CI**: tập mẫu Evaluator + truy vấn RAG golden do AIE chọn, chạy khi PR đổi `apps/ai-service/app/{agents,prompts,llm,rag}/**` + nightly trên `main`; tụt quá ngưỡng AIE đặt → đỏ; key LLM qua GitHub secret | DE (workflow) + AIE (mẫu, ngưỡng) | 30/11 |
| 3.3 | **Reporter / study_plan** (016): báo cáo có bắt đúng lỗ hổng cài sẵn của persona không; study_plan trỏ đúng topic / tài liệu | DE | 05/12 |
| 3.4 | Eval dữ liệu (offline): textbook coverage + cổng mồi (có), JD dedup / PII còn sót / tỉ lệ seedable (đặt ngưỡng), số bản ghi sau index không sụt | DE | 30/11 |
| 3.5 | Tải: 5–10 phiên đồng thời trên staging; TTFT, lỗi, RAM so với mốc | DE | sau Phase 2 |
| 3.6 | Đề xuất cho AIE: Planner (phủ topic, lặp câu), CV / JD parser golden (đã có 10 CV mẫu), injection trong câu trả lời ứng viên, công bằng VN / EN / trộn và gõ / STT | AIE | tùy AIE |

## Thứ tự và phụ thuộc

1. 012 dữ liệu 5 track (đang chạy nền) → index sau khi merge → 3.1 có đủ dữ liệu.
2. 1.3 (VM) + 1.4 (domain) mở khóa mọi việc deploy; Phase 2 sau khi staging chạy; 2.4–2.5 cần traffic thật.
3. 3.2 độc lập, làm song song Phase 1 (chỉ cần CI + secret).
4. 1.5 phụ thuộc web frontend (013, FSD); 1.9 phụ thuộc migration FSD — ngoài tay DE.

## Rủi ro

- Không có domain → không có HTTPS đúng nghĩa cho API (Vercel bắt HTTPS, gọi API http bị chặn mixed content) →
  cần domain hoặc subdomain sớm (mua hoặc dùng domain trường / nhóm).
- SSE qua Caddy / APISIX bị buffer → tắt buffering cho route `/api/start`, `/api/next-turn`; kiểm bằng uptime + tay.
- CORS giữa Vercel preview (URL đổi theo PR) và API → cho phép pattern `*.vercel.app` của project hoặc chỉ domain chính.
- Một VM = một điểm chết → snapshot đĩa hằng ngày + script dựng lại; chấp nhận cho staging.
- Eval CI tốn thời gian chạy → chỉ chạy khi đổi file liên quan + nightly, không chặn PR không liên quan.

## Câu hỏi còn mở

1. Tên domain mua trên Vercel (chốt 2026-11-17: backend GCP VM, FE + domain trên Vercel)?
2. GCP project + billing đã tạo chưa, ai có quyền Owner? Region (đề xuất `asia-southeast1`, Singapore)?
3. Web frontend (013) dùng Next.js để deploy Vercel trực tiếp không? (FSD sở hữu)

## Cập nhật 2026-11-19 (DE chốt)

- Xác nhận 1 VM Compute Engine + compose + Ops Agent / Cloud Monitoring (không Cloud Run).
- GCP project + billing đã có; region `asia-southeast1`. Domain chưa mua (Q1 còn mở; tạm dùng tên suy ra IP).
- Phase 1–2 thành spec [014](../../specs/014-staging-deploy-monitoring/spec.md): deploy service đang có trên `main`
  (ai-service, auth / user / notification, hạ tầng) + quy trình thêm service cho frontend / service FSD sau.
- 1.9 seed ra khỏi 014 (đi theo 009 US4). Phase 3 (eval) không thuộc 014.
