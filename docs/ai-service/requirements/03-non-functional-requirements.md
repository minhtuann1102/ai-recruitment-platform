# NFR — Non-Functional Requirements: AI Interview Service

| Mục | Giá trị |
|---|---|
| Phiên bản | 0.1 (Draft, chờ team review) |
| Ngày | 2026-10-12 |
| Owner | AIE |
| Tài liệu liên quan | [BRD](01-brd.md) · [FR](02-functional-requirements.md) · [Kiến trúc L2](../11-architecture-l2-containers.md) · [Latency và chi phí](../08-latency-and-cost.md) · [Đánh giá chất lượng](../09-agent-quality-evaluation.md) |

> **Lưu ý (2026-10-12): tài liệu này viết theo BRD v0.1 (phỏng vấn chat văn bản, 15 đến 45 phút). [BRD v0.2](requirements/01-brd.md) đã mở rộng phạm vi sang hội thoại giọng nói và video thời gian thực 15 đến 20 phút, giao diện web, cho phép agent framework, fine-tune và học từ dữ liệu; nhận diện cảm xúc hoãn lại. Tài liệu này CHƯA được cập nhật theo v0.2. Phần bị ảnh hưởng: NFR-AI-PERF01 đến 07 (độ trễ tính bằng token đầu văn bản, không có STT và TTS); NFR-AI-SCAL01 (20 phiên đồng thời); NFR-AI-COST01, 02 (chi phí chỉ LLM văn bản, 30 phút); NFR-AI-CMP04, 05 (SSE văn bản); NFR-AI-PRIV (chưa phủ âm thanh và hình ảnh); và thiếu NFR cho độ trễ hội thoại, chất lượng STT, độ ổn định media. Nên trả lời các câu hỏi mở ở BRD mục 12 trước khi sửa.**

## 1. Cách đọc

- **ID** dạng `NFR-AI-<nhóm><số>`: PERF hiệu năng, SCAL mở rộng, REL độ tin cậy, QUAL chất lượng AI, SEC bảo mật, PRIV quyền riêng tư, COST chi phí, MNT bảo trì, OBS quan sát, CMP tương thích, USE trải nghiệm.
- **Căn cứ** cho biết mức chắc chắn của con số:
  - **Ràng buộc**: được nêu trong constitution, ADR, sprint plan hoặc contract của design doc. Lưu ý: constitution đang ở trạng thái Proposed và design doc đang Draft, nên **chưa có ràng buộc nào được team phê duyệt chính thức**; nhãn này chỉ cho biết yêu cầu đã có căn cứ trong tài liệu, không phải đã được duyệt.
  - **Đề xuất**: ngưỡng do design doc đưa ra, chưa được team duyệt và chưa đo.
  - **Giả định**: con số ước tính (giá token, tốc độ sinh), phải đo lại bằng log thật.
  - **Đã đo**: có số đo thật trong repo này.
- **Kiểm chứng** dùng ba tầng test của [design doc 10](../09-agent-quality-evaluation.md): **T1** unit test trong CI (không LLM), **T2** golden set Evaluator (LLM thật, có nhãn người), **T3** ứng viên giả lập end-to-end. Ngoài ra **Rev** là review tài liệu hoặc code, **Spike** là kiểm chứng kỹ thuật một lần.
- Các yêu cầu chức năng ở [FR](02-functional-requirements.md).

## 2. Hiệu năng (PERF)

| ID | Yêu cầu | Chỉ tiêu | Căn cứ | Kiểm chứng | Nguồn |
|---|---|---|---|---|---|
| NFR-AI-PERF01 | Thời gian từ lúc ứng viên gửi câu trả lời tới **token đầu tiên** của câu hỏi tiếp theo (TTFT) | P50 ≤ 3.5 s; P95 ≤ 6 s | Giả định (ước tính ≈ 3.6 s) | T3 + log `latency_ms` trên staging | D08 §9.1 |
| NFR-AI-PERF02 | Câu hỏi **hoàn chỉnh** hiển thị xong | P95 ≤ 7 s | Giả định | T3 | D08 §9.1 |
| NFR-AI-PERF03 | Lượt `dont_know` (bỏ qua Evaluator) | ≈ 1 s | Giả định | T1 + T3 | D08 §9.1 |
| NFR-AI-PERF04 | `/api/start` (Planner, RAG, Interviewer): event đầu và tổng | Event đầu ≤ 25 s; timeout 40 s | Ràng buộc (timeout), giả định (15 đến 25 s) | T3 | D06 §7.4, D08 §9.1 |
| NFR-AI-PERF05 | `/api/next-turn`: event đầu và tổng | Event đầu ≤ 15 s; timeout 45 s | Ràng buộc | T3 | D06 §7.4 |
| NFR-AI-PERF06 | `/api/finalize` (Reporter) | Timeout 90 s; thường 15 đến 30 s | Ràng buộc (timeout), giả định | T3 | D06 §7.4, D08 §9.1 |
| NFR-AI-PERF07 | `/api/cv/parse` | Timeout 30 s; thường 5 đến 9 s | Ràng buộc, giả định | T3 | D06 §7.4, D08 §9.1 |
| NFR-AI-PERF08 | `/api/health` | ≤ 5 s | Ràng buộc | T1 | D06 §7.4 |
| NFR-AI-PERF09 | Ngân sách retry của Evaluator trong một lượt | ≤ 10 s tổng | Ràng buộc | T1 (fake LLM) | D03 §4.6 |

**Số đo thật hiện có** (smoke test S0-AIE-4, OpenRouter, model `openai/gpt-4o-mini`, 2026-10-05):

| Phép đo | Kết quả | Ý nghĩa |
|---|---|---|
| Một lần chat sinh 200 token (bị cắt do `max_tokens`) | 5.4 s | Output dài là biến số lớn nhất |
| Một lần chat sinh 152 token (hoàn chỉnh) | 4.1 s | |
| Embedding 2 đoạn ngắn | 0.7 s đến 1.5 s | RAG tìm kiếm thêm ≈ 0.7 s mỗi truy vấn nếu không cache |

Hai mẫu đo chưa đủ để kết luận, nhưng cho thấy **NFR-AI-PERF01 có rủi ro**: Evaluator (≈ 200 token ra) và Interviewer nối tiếp có thể vượt 3.5 s ngay ở P50. Cần đo sớm (tuần 4) và áp dụng các kỹ thuật ở D08 §9.2: output Evaluator gọn (`max_tokens = 350`), model nhỏ, RAG lấy trước một lần lúc plan, streaming.

## 3. Mở rộng và công suất (SCAL)

| ID | Yêu cầu | Chỉ tiêu | Căn cứ | Kiểm chứng | Nguồn |
|---|---|---|---|---|---|
| NFR-AI-SCAL01 | Hỗ trợ phiên **đồng thời** ở quy mô demo | ≈ 20 phiên, mỗi lượt giữ kết nối ≈ 5 s | Giả định | T3 (tải nhẹ) | D08 §9.5 |
| NFR-AI-SCAL02 | ai-service **stateless** để mở rộng ngang bằng cách thêm process, không cần sticky session | Hai instance cùng phục vụ một phiên không lỗi | Ràng buộc | Rev + T3 | CON IV |
| NFR-AI-SCAL03 | I/O bất đồng bộ, dùng chung một HTTP client có keep-alive tới LLM provider | Không tạo kết nối TLS mới mỗi lời gọi | Đề xuất | Rev | D08 §9.2 |
| NFR-AI-SCAL04 | Thêm **vị trí phỏng vấn** chỉ bằng thêm file catalog, không sửa code điều phối | 0 dòng code đổi; test catalog tự nhận | Đề xuất | T1 | D01, README A9 |

## 4. Độ tin cậy và chịu lỗi (REL)

| ID | Yêu cầu | Chỉ tiêu | Căn cứ | Kiểm chứng | Nguồn |
|---|---|---|---|---|---|
| NFR-AI-REL01 | **Không phiên nào chết** vì lỗi LLM: retry giới hạn rồi fallback theo từng agent | Mọi nhánh lỗi trong bảng xử lý lỗi có test; không còn lỗi 5xx do LLM làm dừng phiên | Ràng buộc | T1 (fake LLM) | CON IV, D03 §4.6 |
| NFR-AI-REL02 | Retry lỗi tạm thời | ≤ 2 lần, backoff 0.5 s rồi 1.5 s + jitter; không retry 400, 401, 403 | Ràng buộc | T1 | D03 §4.6 |
| NFR-AI-REL03 | Lỗi định dạng JSON sau repair | < 1% tổng số lời gọi | Đề xuất | T3 | D09 §10.2 |
| NFR-AI-REL04 | Tỉ lệ dùng fallback | < 2% | Đề xuất | T3 + log | D09 §10.2 |
| NFR-AI-REL05 | Khởi động lại hoặc mở rộng ai-service **không mất dữ liệu** phiên | 0 dữ liệu phiên trong ai-service | Ràng buộc | Rev | CON IV |
| NFR-AI-REL06 | Client ngắt kết nối giữa stream: interview-service vẫn đọc hết và lưu câu hỏi cùng state | Vào lại phiên thấy câu hỏi hiện tại | Ràng buộc (hành vi phía FSD) | T3 | D03 §4.6 |
| NFR-AI-REL07 | Gửi trùng câu trả lời không làm hỏi trùng | Trả lại câu hỏi đã lưu (FSD) | Ràng buộc | T1 (FSD) | D03 §4.6 |
| NFR-AI-REL08 | ai-service có health endpoint cho Compose và gateway | `GET /api/health` 200 | Ràng buộc | T1 | CON |
| NFR-AI-REL09 | Mọi giới hạn cứng của phiên được **bảo đảm bằng code**, không dựa vào LLM | 0 phiên vượt follow-up tối đa, turn cap 24, thời gian | Ràng buộc | T1 (biên) + T3 | D03 §4.3, D09 §10.2 |

## 5. Chất lượng AI (QUAL)

Các chỉ tiêu này là bằng chứng chính cho báo cáo đồ án. Toàn bộ là **đề xuất**, chỉnh sau lần chạy đầu của từng tầng.

| ID | Yêu cầu | Chỉ tiêu | Kiểm chứng |
|---|---|---|---|
| NFR-AI-QUAL01 | Evaluator **khớp người chấm** | ±1 band ≥ 90% (mốc trung gian tuần 2: ≥ 80%) | T2 |
| NFR-AI-QUAL02 | Sai số tuyệt đối trung bình | MAE band ≤ 0.6 | T2 |
| NFR-AI-QUAL03 | **Không chấm dễ dãi** | Độ lệch khoan dung (LLM trừ người) trong [−0.3, +0.3]; là điều kiện merge | T2 |
| NFR-AI-QUAL04 | Thứ tự đúng: giỏi > trung bình > yếu | ≥ 95% câu hỏi | T2 |
| NFR-AI-QUAL05 | **Nhất quán** khi chạy lặp | Độ lệch chuẩn band qua 3 lần ≤ 0.3 | T2 |
| NFR-AI-QUAL06 | Bắt `manipulation` | 100% mẫu injection có band 0 và `answer_type = manipulation` | T2 |
| NFR-AI-QUAL07 | **Evidence hợp lệ** (quote có trong câu trả lời) trước hậu kiểm | ≥ 95% | T2 |
| NFR-AI-QUAL08 | `answer_type` đúng so với nhãn | ≥ 90% | T2 |
| NFR-AI-QUAL09 | Phân biệt trình độ: điểm giỏi > trung bình > yếu; khoảng cách giỏi trừ yếu | ≥ 7/8 tổ hợp; ≥ 3.0 điểm | T3 |
| NFR-AI-QUAL10 | **Thích ứng** đúng chiều: độ dốc quỹ đạo độ khó giỏi > 0, yếu < 0 | ≥ 80% phiên | T3 |
| NFR-AI-QUAL11 | Không lặp câu hỏi (Jaccard ≥ 0.8 với câu đã hỏi) | < 5% lượt | T3 |
| NFR-AI-QUAL12 | **Báo cáo trung thực**: recall lỗ hổng trong `improvements`; điểm mạnh sai; `evidence_turns` tồn tại | ≥ 70%; 0; 100% | T3 + người kiểm 5 báo cáo mỗi lần |
| NFR-AI-QUAL13 | Chất lượng Interviewer (một câu hỏi/lượt, đúng action, không lộ đáp án hay điểm, tự nhiên) | Judge LLM trung bình ≥ 4.0/5; người đọc 5 transcript mỗi lần | T3 |
| NFR-AI-QUAL14 | Truy xuất RAG | recall@5 ≥ 0.8 trên golden set RAG (≥ 20 query, nhiều nhóm ngôn ngữ) | RAG eval |
| NFR-AI-QUAL15 | Injection **không làm tăng điểm** so với cùng persona không injection | Đúng 100% | T3 |

Lưu ý phương pháp:
- **Thiên lệch cùng họ model**: Simulator và Evaluator cùng họ có thể "hiểu ý nhau" nên golden set có nhãn người (T2) là thước đo chính cho độ chính xác chấm; T3 chủ yếu đo hành vi hệ thống (D09 §10.2).
- Đổi model hoặc prompt Evaluator: chạy lại T2; không merge nếu "khớp ±1" giảm quá 5 điểm phần trăm hoặc độ lệch khoan dung vượt ngưỡng.
- Golden set RAG phải tách khỏi dữ liệu đã index và gắn nhãn vào corpus của nhóm (rag-design §9).

## 6. Bảo mật (SEC)

| ID | Yêu cầu | Chỉ tiêu | Căn cứ | Kiểm chứng | Nguồn |
|---|---|---|---|---|---|
| NFR-AI-SEC01 | ai-service **không expose ra ngoài**: gateway chỉ cho `/ai/api/health`; các endpoint khác yêu cầu `X-Internal-Token` | Gọi trực tiếp không token → 401; route khác `health` không truy cập được qua APISIX | Ràng buộc | T1 + Rev cấu hình APISIX | D06 §7.1, D10 P5 |
| NFR-AI-SEC02 | **Cô lập CV thô**: chỉ CV Parser thấy CV; các agent sau chỉ nhận `cv_profile` đã qua schema | Evaluator không nhận `cv_profile` | Ràng buộc | Rev + T3 | D01 §2.4 |
| NFR-AI-SEC03 | **Chống prompt injection** nhiều lớp: khối `untrusted` cho CV, câu trả lời và chunk RAG; hậu kiểm bằng code; band bị ép 0 với `manipulation` | Bộ test adversarial pass 100%; CV chứa injection không làm lệch plan | Ràng buộc | T1 + T2 + T3 | D01 §2.4, D10 R7 |
| NFR-AI-SEC04 | **Validate mọi input** bằng Pydantic, kể cả từ service nội bộ; giới hạn kích thước và loại file theo magic bytes; chống zip bomb | Mã lỗi đúng theo bảng validate | Ràng buộc | T1 | D01 §2.2 |
| NFR-AI-SEC05 | **Không commit secret**; biến môi trường mới có trong `.env.example` | Không có key trong git; CI quét secret | Ràng buộc | Rev + CI | CON VI |
| NFR-AI-SEC06 | Khóa API LLM chỉ ở biến môi trường, không ghi log | Log không chứa khóa | Ràng buộc | Rev | CON VI |
| NFR-AI-SEC07 | Lỗi trả ra ngoài **không lộ chi tiết nội bộ** (stack trace, prompt, khóa) | Response lỗi chỉ có `{error, message, details}` | Đề xuất | T1 | D06 §7.4 |
| NFR-AI-SEC08 | Dependency ghim phiên bản trong `requirements.txt` | Tất cả dòng có `==` | Ràng buộc | Rev | CON |
| NFR-AI-SEC09 | Bảo vệ khỏi **lạm dụng chi phí** (gọi thẳng ai-service, tạo phiên liên tục) | Quota ngày mỗi ứng viên (đề xuất 5); chặn route `/ai/*` | Đề xuất | Rev + T1 (FSD) | D08 §9.4 |

## 7. Quyền riêng tư và tuân thủ (PRIV)

| ID | Yêu cầu | Chỉ tiêu | Căn cứ | Kiểm chứng | Nguồn |
|---|---|---|---|---|---|
| NFR-AI-PRIV01 | **Redact PII trước khi gửi LLM** (email, SĐT, URL, ngày sinh) | 0 PII trong text đưa vào LLM; test với nhiều định dạng SĐT | Ràng buộc | T1 | D01 §2.3 |
| NFR-AI-PRIV02 | `cv_profile` **không chứa** tên, liên hệ, tên công ty (chỉ `company_type`) | Schema không có các trường đó | Ràng buộc | T1 | D02 §3.3.1 |
| NFR-AI-PRIV03 | ai-service **không log nội dung** câu hỏi, câu trả lời, CV; cờ `LOG_LLM_IO` mặc định tắt; log chỉ có id và số đo | Rà log trong T3 | Ràng buộc | Rev + T3 | D07, D10 P3 |
| NFR-AI-PRIV04 | Transcript, câu trả lời, `cv_profile`, file CV **không bao giờ** vào `knowledge_chunks` hay dataset pipeline | 0 bản ghi chứa dữ liệu phiên | Ràng buộc (cần amendment constitution V) | Rev | D07 §8.7 |
| NFR-AI-PRIV05 | **Consent riêng** khi dùng CV đã nộp để luyện phỏng vấn (mục đích khác), ghi `cv_consent_at` (FSD) | Gắn CV bị từ chối nếu thiếu consent | Ràng buộc | T1 (FSD) | D01 §2.2, D10 P1 |
| NFR-AI-PRIV06 | Xóa dữ liệu theo yêu cầu: xóa phiên xóa luôn `cv_profile`, transcript và báo cáo; job dọn phiên bỏ dở sau 30 ngày (FSD) | `DELETE /sessions/:id` xóa cứng | Đề xuất | T1 (FSD) | D10 P6 |
| NFR-AI-PRIV07 | Chọn LLM provider **không lưu hoặc huấn luyện** trên dữ liệu (zero data retention) nếu có; tắt prompt logging ở tài khoản | Cấu hình tài khoản OpenRouter đã kiểm tra | Cần kiểm chứng | Spike | D10 P1 |
| NFR-AI-PRIV08 | **Tuân thủ pháp lý** về dữ liệu cá nhân (chuyển dữ liệu ra nước ngoài, quyền xóa, consent): nhóm tự đối chiếu văn bản hiện hành và ghi vào báo cáo | Có mục pháp lý trong báo cáo đồ án | Cần kiểm chứng | Rev | D10 P7 |

## 8. Chi phí (COST)

| ID | Yêu cầu | Chỉ tiêu | Căn cứ | Kiểm chứng | Nguồn |
|---|---|---|---|---|---|
| NFR-AI-COST01 | Chi phí LLM của một **phiên chuẩn** (30 phút, ≈ 15 lượt) | ≈ $0.015 (≈ 72k token vào, 7.5k token ra, giá `gpt-4o-mini` giả định) | Giả định | T3 + log usage | D08 §9.4 |
| NFR-AI-COST02 | Phiên dài nhất (24 lượt, thêm 20% retry) | ≈ $0.027 | Giả định | T3 | D08 §9.4 |
| NFR-AI-COST03 | **Cảnh báo** khi một phiên vượt ngưỡng | > $0.10/phiên | Ràng buộc | Log + Rev | sprint S3-AIE-5 |
| NFR-AI-COST04 | Mỗi lời gọi LLM ghi token vào/ra để tính chi phí | 100% lời gọi có `usage` | Ràng buộc | T1 | D08 §9.4 |
| NFR-AI-COST05 | Giá token phải **kiểm tra lại** trên trang giá nhà cung cấp tại thời điểm triển khai | Ghi ngày kiểm tra trong báo cáo | Giả định | Rev | D08 §9.4 |

## 9. Bảo trì và khả năng kiểm thử (MNT)

| ID | Yêu cầu | Chỉ tiêu | Căn cứ | Kiểm chứng | Nguồn |
|---|---|---|---|---|---|
| NFR-AI-MNT01 | Logic điều phối (transition, policy, tổng hợp điểm, hậu kiểm, trích xuất và redact CV) có **unit test không cần LLM** | Mọi dòng bảng luật policy có ≥ 1 test; test biên giới hạn; ≥ 90% nhánh orchestrator (mốc tuần 3) | Ràng buộc, đề xuất | T1 | CON VI, D09 §10.2 |
| NFR-AI-MNT02 | **CI** chạy lint, type check, test cho ai-service; PR đỏ không merge; không bỏ qua hay xóa test fail | Job Python trong CI | Ràng buộc | CI | CON VI |
| NFR-AI-MNT03 | **Không mock giả để qua CI**: fake LLM chỉ để kiểm logic điều phối, không khẳng định chất lượng chấm | Chất lượng đo bằng T2, T3 với model thật | Ràng buộc | Rev | CON VI, D09 §10.2 |
| NFR-AI-MNT04 | File code dưới 200 dòng, tách theo trách nhiệm | Không file nào ≥ 200 dòng (trừ file cấu hình, tài liệu) | Ràng buộc | Rev | CON VII |
| NFR-AI-MNT05 | **Prompt là file trong repo**, có phiên bản; phiên bản được ghi vào metadata mỗi lượt | `prompt_version` có trong `metadata` | Đề xuất | T1 | D07 §8.1 |
| NFR-AI-MNT06 | **Contract-first**: đổi contract thì cập nhật tài liệu trong cùng PR; có mock theo contract | Tài liệu và mock luôn khớp | Ràng buộc | Rev | CON III |
| NFR-AI-MNT07 | Cấu hình model, temperature, max_tokens, timeout **theo từng agent** bằng biến môi trường | Đổi model một agent không sửa code | Đề xuất | T1 | D08 §9.3 |
| NFR-AI-MNT08 | Quyết định kiến trúc ghi bằng ADR; đổi model embedding là thay đổi contract dữ liệu cần ADR hoặc amendment | Có ADR cho mỗi thay đổi | Ràng buộc | Rev | CON IV |

## 10. Quan sát và giám sát (OBS)

| ID | Yêu cầu | Chỉ tiêu | Căn cứ | Kiểm chứng | Nguồn |
|---|---|---|---|---|---|
| NFR-AI-OBS01 | Mỗi response `done` có `metadata`: token vào/ra từng agent, độ trễ (TTFT, tổng), phiên bản prompt, danh sách fallback | Đủ trường theo contract | Ràng buộc | T1 | D06 §7.4 |
| NFR-AI-OBS02 | Log có cấu trúc kèm `session_id`, `turn_number`, agent; **không** có nội dung | Rà log | Ràng buộc | Rev | D07 |
| NFR-AI-OBS03 | Theo dõi được TTFT P50 và P95, tỉ lệ fallback, lỗi format, chi phí mỗi phiên | Bảng tổng hợp từ `ai_meta` sau mỗi lần chạy T3 | Đề xuất | T3 | D09 §10.2 |
| NFR-AI-OBS04 | Log similarity score và id chunk của mỗi lần truy xuất RAG để chọn ngưỡng dựa trên dữ liệu | Có trong log debug | Đề xuất | Rev | rag-design §4 |

## 11. Tương thích và triển khai (CMP)

| ID | Yêu cầu | Chỉ tiêu | Căn cứ | Kiểm chứng | Nguồn |
|---|---|---|---|---|---|
| NFR-AI-CMP01 | Gọi LLM qua **API OpenAI-compatible** cấu hình bằng biến môi trường; đổi nhà cung cấp không đổi code | Chạy được với OpenRouter, và với OpenAI trực tiếp khi đổi `LLM_BASE_URL` | Ràng buộc | Smoke test | CON IV |
| NFR-AI-CMP02 | Chạy bằng Docker; `docker compose up -d` trên máy sạch (sau khi sao chép `.env.example`) dựng được ai-service healthy | Container healthy | Ràng buộc | Spike | CON |
| NFR-AI-CMP03 | **Phiên bản Python thống nhất.** CI dự kiến dùng 3.11, Docker image dùng 3.12; mã hiện tương thích cả hai và chạy được trên 3.9 | Chốt một phiên bản trong CI và Dockerfile | Cần quyết định | CI | specs/001 T032 |
| NFR-AI-CMP04 | SSE đi được qua **hai hop proxy** (relay interview-service, APISIX) không bị gom buffer | `curl -N` qua cổng 9080 thấy token hiện dần | Cần kiểm chứng | Spike (tuần 4) | D06 §7.5 |
| NFR-AI-CMP05 | Client SSE dùng `fetch` stream (không `EventSource`, vì cần header `Authorization` và POST) | Đã ghi trong contract | Ràng buộc | Rev | D06 §7.5 |
| NFR-AI-CMP06 | Embedding cố định 1536 chiều khớp schema pgvector; đổi model là đổi contract dữ liệu | `embedding_dimensions = 1536` | Ràng buộc | T1 + smoke test | CON IV |

## 12. Trải nghiệm đầu ra (USE)

| ID | Yêu cầu | Chỉ tiêu | Căn cứ | Kiểm chứng | Nguồn |
|---|---|---|---|---|---|
| NFR-AI-USE01 | Câu hỏi **tiếng Việt tự nhiên**, giữ thuật ngữ tiếng Anh, ≤ 80 từ, một câu hỏi mỗi lượt | Judge LLM và người đọc transcript | Đề xuất | T3 | D02 §3.3.4 |
| NFR-AI-USE02 | Hỗ trợ trả lời **không dấu** hoặc viết tắt mà không làm hỏng việc chấm | Có mẫu không dấu trong golden set | Đề xuất | T2 | rag-design §9 |
| NFR-AI-USE03 | Báo cáo kèm **lời nhắc** điểm do AI chấm mang tính tham khảo và hiển thị mức tin cậy | Có `meta.disclaimer` và `confidence` | Ràng buộc | T1 | D05 §6.5 |
| NFR-AI-USE04 | Lượt nhận câu trả lời ngắn ("Em không biết") phải được chấp nhận, không báo lỗi độ dài tối thiểu | `answer` chấp nhận từ 1 ký tự | Ràng buộc | T1 | D06 §7.2 |

## 13. Tóm tắt theo căn cứ và hiện trạng

Số lượng NFR theo nhóm (đếm bằng script):

| Nhóm | Số NFR |
|---|---|
| Hiệu năng (PERF) | 9 |
| Mở rộng (SCAL) | 4 |
| Độ tin cậy (REL) | 9 |
| Chất lượng AI (QUAL) | 15 |
| Bảo mật (SEC) | 9 |
| Quyền riêng tư (PRIV) | 8 |
| Chi phí (COST) | 5 |
| Bảo trì (MNT) | 8 |
| Quan sát (OBS) | 4 |
| Tương thích (CMP) | 6 |
| Trải nghiệm (USE) | 4 |
| **Tổng** | **81** |

| Căn cứ | Số NFR |
|---|---|
| Ràng buộc | 42 |
| Đề xuất | 28 |
| Giả định | 7 |
| Cần kiểm chứng | 3 |
| Cần quyết định | 1 |

Nhóm QUAL được tính là "Đề xuất" (bảng không có cột căn cứ riêng). Không có NFR nào ở mức "Đã đo": repo mới chỉ có hai lần chạy smoke test, đủ để cảnh báo rủi ro độ trễ (mục 2) chứ chưa đủ để xác nhận chỉ tiêu.

## 14. Điều chưa kiểm chứng

| # | Điều chưa biết | Ảnh hưởng | Cách kiểm chứng |
|---|---|---|---|
| 1 | Độ trễ thật của chuỗi Evaluator rồi Interviewer qua OpenRouter | NFR-AI-PERF01, 02 | Đo từ tuần 4; có phương án dự phòng ở D08 §9.2 |
| 2 | Giá token hiện hành | NFR-AI-COST01..03 | Kiểm tra trang giá tại thời điểm triển khai |
| 3 | Chất lượng embedding với tiếng Việt xen thuật ngữ Anh | NFR-AI-QUAL14 | Golden set RAG; thử model khác nếu recall thấp |
| 4 | Prompt caching qua OpenRouter có hoạt động không | PERF01, COST01 | Đo `cached_tokens` trong usage |
| 5 | SSE có bị buffer qua APISIX không | NFR-AI-CMP04 | Spike tuần 4 |
| 6 | OpenRouter có zero data retention không | NFR-AI-PRIV07 | Kiểm tra cấu hình tài khoản |
| 7 | Ngưỡng weak, strong, verdict | QUAL09, QUAL10 | Chạy ứng viên giả lập rồi chỉnh |
| 8 | Quy định pháp lý bảo vệ dữ liệu cá nhân hiện hành | NFR-AI-PRIV08 | Nhóm tự đối chiếu văn bản |

## 15. Truy vết BR sang NFR

| BR | NFR |
|---|---|
| BR-01..03 | USE01, PERF01..07 |
| BR-04 | REL09, QUAL10 |
| BR-05 | QUAL01..08 |
| BR-06 | QUAL03, QUAL12, MNT03 |
| BR-07 | USE03, SEC07 |
| BR-08 | QUAL12, PERF06, USE03 |
| BR-09 | SEC02, SEC03, QUAL06, QUAL15 |
| BR-10 | PRIV01..04, SEC02 |
| BR-11 | REL01..04, REL06 |
| BR-12 | QUAL14, PRIV04 |
| BR-13 | COST01..05, OBS01..03 |
| BR-14 | MNT01..03, QUAL01..15 |
| BR-15 | SCAL04 |
| BR-16 | MNT06, CMP04 |
