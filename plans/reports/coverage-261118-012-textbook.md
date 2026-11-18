# Coverage 012 textbook — sau khi nạp 6 track (2026-11-18)

Spec 012 T057 / T058. Kho `ai_db` (Supabase), chạy từ `main` sau PR #100. Lệnh: `index-textbook` 18 nguồn (17 mới + postgresql soát lại), chạy lần hai, `coverage-textbook --db`. celery chưa nạp (crawl lại bị chặn 403/429), báo cáo không tính celery.

## Kho
| | Trước | Sau |
|---|---|---|
| `interview_qa` | 8.356 | 8.356 |
| `textbook` | 262 (lô thử java) → 152 sau khi xóa 110 đoạn postgresql cũ | 1.121 |

- Lần index thứ hai: 18/18 nguồn `inserted=0`, `embed_errors=0`.
- 110 đoạn postgresql cũ (tiêu đề còn ` #` do neo permalink) bị xóa theo đúng hash vì `index-textbook` không xóa hash cũ; postgresql nạp lại 139 đoạn.
- 22 dataset `de_textbook_*`; 0 đoạn thiếu `source_url` hoặc `license`.

## Nguồn × giấy phép × số đoạn
| Nguồn | Giấy phép | Lớp | Trang | Đoạn | Drop theo lý do |
|---|---|---|---|---|---|
| django | NOASSERTION | restricted | 4 | 40 | nav 1, not_self_contained 2, other 1 |
| docker | Apache-2.0 | open | 6 | 42 | not_self_contained 4 |
| fastapi | MIT | open | 5 | 36 | code_only 1, not_self_contained 6, off_topic 3, other 1 |
| hibernate-orm | NOASSERTION | restricted | 3 | 49 | code_only 2, not_self_contained 7, other 1 |
| huggingface-docs | Apache-2.0 | open | 12 | 86 | code_only 1, nav 2, not_self_contained 27, off_topic 5, other 8 |
| kubernetes | CC-BY-4.0 | open | 8 | 103 | code_only 7, nav 1, not_self_contained 9 |
| livekit-docs | LiveKit docs, all rights reserved | restricted | 5 | 37 | code_only 1, not_self_contained 2, other 1, reference_table 1 |
| mdn-web-docs | CC-BY-SA-2.5 | open | 8 | 61 | not_self_contained 5, other 2 |
| nannyml | Apache-2.0 | open | 3 | 36 | code_only 2, not_self_contained 3 |
| nestjs | MIT | open | 5 | 75 | not_self_contained 6, off_topic 1, reference_table 1 |
| nodejs | CC-BY-4.0 | open | 3 | 13 | not_self_contained 4, other 1 |
| owasp-llm-top10 | CC-BY-SA-4.0 | open | 7 | 53 | nav 10 |
| postgresql | PostgreSQL | open | 7 | 139 | nav 1, not_self_contained 20, off_topic 2, other 1 |
| prometheus | Apache-2.0 | open | 3 | 37 | not_self_contained 3 |
| react-dev | CC-BY-4.0 | open | 5 | 38 | not_self_contained 8, other 1 |
| redis | CC-BY-NC-SA-4.0 | restricted | 6 | 61 | nav 6, not_self_contained 1, off_topic 8 |
| scikit-learn | BSD-3-Clause | open | 5 | 35 | nav 3, not_self_contained 6, reference_table 1 |
| spring-boot | NOASSERTION | restricted | 1 | 31 | - |
| spring-framework | Spring docs notice | restricted | 5 | 50 | not_self_contained 4, other 1, reference_table 6 |
| sqlalchemy | MIT | open | 2 | 23 | nav 1, not_self_contained 3 |
| system-design-primer | CC-BY-4.0 | open | 3 | 22 | not_self_contained 1, reference_table 1 |
| web-dev | CC-BY-4.0 | open | 5 | 54 | not_self_contained 4, other 4 |
| spring-data-jpa | (excluded) | | 0 | 0 | |
| celery | CC-BY-SA-4.0 | open | 2 | chưa nạp | crawl lại bị chặn |

Giấy phép chỉ để phân loại (đồ án học thuật, không loại nguồn vì giấy phép).

## Track
| Track | Nguồn chính thức | Đoạn |
|---|---|---|
| java_backend | 4 | 267 |
| ai_engineer | 5 | 256 |
| devops_engineer | 3 | 182 |
| nodejs_backend | 3 | 158 |
| frontend_react | 1 | 153 |
| python_backend | 5 | 151 |

## Tình huống × số đoạn × truy hồi
Từ khóa: hạng BM25 của đoạn gắn tình huống trong top 3. Vector: top 3 tìm vector trên kho.

| Tình huống | Đoạn | Từ khóa | Vector |
|---|---|---|---|
| scn.ai.cv-job-matching | 35 | #1 | hit |
| scn.ai.docs-qa-rag | 32 | #1 | hit |
| scn.ai.model-drift-incident | 46 | #1 | hit |
| scn.ai.prompt-injection-defense | 47 | #1 | hit |
| scn.ai.support-agent-handoff | 36 | #3 | hit |
| scn.ai.llm-cost-reduction | 43 | #3 | hit |
| scn.ai.model-upgrade-rollout | 35 | #1 | hit |
| scn.ai.voice-interview-agent | 37 | #1 | hit |
| scn.devops.dockerize-web-app | 37 | #1 | hit |
| scn.devops.container-crashloop | 60 | #1 | hit |
| scn.devops.zero-downtime-deploy | 56 | #1 | hit |
| scn.devops.prod-latency-incident | 59 | #1 | hit |
| scn.fe.job-list-infinite-scroll | 34 | #1 | hit |
| scn.fe.multi-step-apply-form | 31 | #1 | hit |
| scn.fe.slow-page-lcp | 58 | #1 | hit |
| scn.fe.realtime-interview-ui | 40 | #1 | hit |
| scn.java.order-api-crud | 61 | #1 | hit |
| scn.java.flash-sale-inventory | 75 | #1 | hit |
| scn.java.payment-idempotency | 90 | #1 | **miss** |
| scn.java.slow-query-incident | 105 | #1 | hit |
| scn.node.file-upload-service | 49 | #1 | hit |
| scn.node.rate-limit-api | 20 | #1 | hit |
| scn.node.realtime-notifications | 46 | #1 | hit |
| scn.node.cache-stampede | 43 | #1 | hit |
| scn.py.report-export-timeout | 34 | #1 | hit |
| scn.py.webhook-ingest | 54 | **miss** | **miss** |
| scn.py.multi-tenant-api | 43 | #1 | hit |
| scn.py.csv-import-pipeline | 65 | **miss** | hit |

## Đối chiếu Success Criteria (T058)
| SC | Kết quả | Ghi chú |
|---|---|---|
| SC-001 | Đạt | 28/28 tình huống ≥ 1 đoạn; 100% ≥ 3 đoạn (ít nhất: `scn.node.rate-limit-api` 20) |
| SC-002 | Đạt | 6/6 track có nguồn chính thức (frontend_react: 1) |
| SC-003 | Đạt | 1.121/1.121 đoạn có URL và giấy phép; mọi dataset thuộc manifest (index chặn dataset lạ) |
| SC-004 | Đạt | Từ khóa 26/28 (93%), vector 26/28 (93%), ngưỡng 80% |
| SC-005 | Đạt | `interview_qa` 8.356 trước / sau; lần hai 0 bản ghi mới |
| SC-006 | Đạt, có lưu ý | 100% đoạn mồi bị drop ở 18 nguồn. Cùng nhóm ~6–8 đoạn mồi lặp ở mọi nguồn và worker nhận ra là nội dung lạ, nên cổng yếu hơn thiết kế |
| SC-007 | Chưa có | AIE chưa đo trước / sau (T049); T050 quyết theo độ phủ |
| SC-008 | Đạt | 1.121 đoạn, trong khoảng 300–1.500 |

## Gaps
- `scn.py.webhook-ingest` trượt cả từ khóa lẫn vector; `scn.py.csv-import-pipeline` trượt từ khóa. Nguồn python còn thiếu celery (task, retry); nạp celery xong đo lại trước khi thêm trang.
- `scn.java.payment-idempotency` trượt vector (lô thử 11-17 trúng): category Backend nay có thêm đoạn NestJS, FastAPI, Django nên đoạn Spring bị đẩy khỏi top 3. Từ khóa vẫn #1. Chấp nhận, ghi lại; xem lại nếu AIE đo thấy lượt scenario này thiếu căn cứ.

## Lệch / rủi ro
- Soát: 14 worker Sonnet, 2 song song, 3–5 lô / worker (spec: 1 lô / worker).
- 13 lệnh trim cắt cả khối code (`pip install`, sơ đồ mermaid, code vẽ biểu đồ); phần còn lại đã đọc lại.
- Sửa parser bỏ neo permalink (`a.headerlink`, `a.id_link`) làm đổi hash postgresql → soát lại 151 đoạn, xóa 110 đoạn cũ trong kho.

## Tin nhắn cho AIE (T048 / T056)
> Textbook 012 đã nạp đủ 6 track vào `ai_db`: 1.121 đoạn `source_type = 'textbook'`, 22 dataset `de_textbook_*`, category `Backend`, `Frontend`, `DevOps`, `AI`, `System Design`. `interview_qa` không đổi (8.356). Cần làm: khởi động lại ai-service để nạp lại kho từ khóa; nếu đo được thì đo nền với `RAG_TEXTBOOK_ENABLED` tắt → bật → khởi động lại → đo lại (quickstart §7). Gaps: `scn.py.webhook-ingest`, `scn.py.csv-import-pipeline` (chờ celery), `scn.java.payment-idempotency` trượt vector. Báo cáo: `plans/reports/coverage-261118-012-textbook.md`.

## Câu hỏi còn mở
- celery: crawl lại ngày 19/11; nếu vẫn chặn thì `excluded` hay giữ gap?
- AIE có đo SC-007 trước hạn Sprint không?
