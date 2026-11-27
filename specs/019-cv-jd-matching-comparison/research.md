# Research: 019 GĐ1 bộ test khóa

Mọi quyết định do DE (owner) chốt 2026-11-26. FSD chỉ gán nhãn.

## R1. Nguồn CV và JD

- **Decision**: lấy CV từ `data/seeds/candidates/candidate_cvs.json` (84 CV, T040). Đây là tệp khác với 24 CV của
  `match_eval/cvs.json`, và lệnh vẫn kiểm trùng theo ID và băm nội dung. JD là bản ghi `jd_normalized.jsonl` có
  `synthetic = false`, có trong tập đã index `jd-match` (bỏ những bản ghi run-report index đã loại: `no_group`,
  `duplicate_hash`), và không thuộc `match_eval/pool.json` hay trùng `content_hash` với pool.
- **Rationale**: JD thật đúng với miền dùng thật. CV tổng hợp là lựa chọn duy nhất không có PII; đây là hạn chế, ghi
  trong báo cáo.
- **Alternatives**: thêm JD tổng hợp cho track frontend (loại vì đó là văn bản LLM, lệch miền); dùng CV thật (không có).

## R2. Thiết kế lấy mẫu (FR-003, FR-004)

- **Decision**: 30 CV, mỗi track 5 CV. Mỗi track lấy 1 CV ở mỗi level (fresher / junior / middle / senior), CV thứ 5
  lấy ngẫu nhiên theo seed. Mỗi CV ghép 7 JD:
  - 5 JD cùng nhóm, trong đó ưu tiên ≥ 2 JD lệch ≥ 2 bậc level nếu có.
  - 1 JD nhóm lân cận.
  - 1 JD nhóm xa.

  Bảng nhóm dùng `TRACK_GROUPS` của 017. Nhóm lân cận: backend ↔ devops / mobile_fullstack, frontend ↔
  mobile_fullstack / backend, devops ↔ backend, ai_data ↔ backend. Mỗi JD xuất hiện tối đa 3 lần trong toàn bộ, để
  tránh một JD chi phối. Riêng nhóm frontend chỉ có 8 JD nên được phép tối đa 4 lần. Ngôn ngữ JD bốc theo tỉ lệ có sẵn
  của nhóm, và mỗi CV có ≥ 1 JD tiếng Anh nếu nhóm có.
- **Rationale**: cặp cùng nhóm là cặp khó và mang thông tin. Nhóm backend trộn Java / Python / Node nên tự nhiên có
  cặp "cùng nhóm nhưng khác ngôn ngữ chính", tức nhãn 0 theo rubric. Đây là hard negative thật, không cần dựng.
  Lấy 30 đơn vị CV cho bootstrap thay vì 24 như 017.
- **Alternatives**: 20 × 10 (ít CV, khoảng tin cậy rộng như 017); 40 × 5 (khó tính nDCG theo CV).

## R3. CV hai ngôn ngữ (FR-005)

- **Decision**: CV gốc là tiếng Việt. Worker (Claude sonnet, trong phiên làm việc) dịch 30 CV sang tiếng Anh **một
  lần**, giữ nguyên cấu trúc `CvProfile`, không dịch tên công nghệ, tên dự án hay chức danh tiếng Anh sẵn có. Kết quả
  lưu ở `cvs_en.json` (seed, commit được), có ghi cách dịch. DE kiểm 6 CV ngẫu nhiên (20%). Rater chỉ thấy bản tiếng
  Việt; nhãn áp cho cả hai bản.
- **Rationale**: không cần viết mã dịch hay gọi API lặp lại. Bản dịch cố định là một phần của bộ test, chạy lại không
  đổi. "Không dùng AI API ngoài" là ràng buộc cho model và lúc chạy, không cho bước chuẩn bị dữ liệu.
- **Alternatives**: dịch bằng mã gọi OpenAI (thừa vì chỉ chạy một lần); rater gán cả bản tiếng Anh (gấp đôi công).

## R4. Đầu vào cố định cho từng hệ (FR-006, FR-007)

- **Decision**:
  - **Văn bản CV đầy đủ** (cho rater, BiGRU, luật): headline; số năm kinh nghiệm; kỹ năng (tên); từng kinh nghiệm
    (role, thời gian, tech, summary); từng dự án (name, role, tech, summary, highlights); học vấn.
  - **017** dùng đúng `build_cv_text` + kỹ năng của nó từ cùng `CvProfile`. Mỗi hệ nhận dạng đầu vào gốc của mình,
    nhưng cùng một CV.
  - **JD cho BiGRU** (theo `server.analyze` / `classify_skills` / `seniority_evidence` của FSD):
    - `title` = title.
    - `description` = sections.summary + sections.description.
    - `requirements` = sections.requirements, hoặc rỗng nếu không có.
    - `responsibilities` = "".
    - `education` = "".
    - `experience` theo bảng: Intern / Junior → "Entry Level", Mid → "Mid Level", Senior → "Senior Level", Lead →
      "Lead", Manager → "Manager", không có → "".
    - `skills` = tên hiển thị của skill slug, nối bằng ", ".
    - Không lấy benefits.
  - **JD cho rater**: title + summary + description + requirements, cùng thứ tự phần như sheet 017, không có level
    hay nhóm.
  - **JD cho 017**: `jd_id`. Bộ chấm 017 dùng metadata và vector đã index.

  Mỗi dòng `inputs.jsonl` lưu cả ba dạng cùng băm. Bước kiểm tra chấp nhận gồm:
  - Mỗi phía ≤ 30.000 ký tự.
  - Văn bản CV parse lại được bằng `CvProfile`.
  - `jd_id` có trong tập index.
  - Dict JD có đủ 7 khóa.

  Cờ `no_requirements` / `no_level` / `no_skills` được ghi lại để phân tích sau.
- **Rationale**: khớp với mã FSD đang chạy (đã đọc `server.py` 2026-11-26). JD thiếu requirements khiến
  `classify_skills` trả "unspecified"; đó là hành vi thật của hệ FSD, nên ghi cờ chứ không sửa.
- **Alternatives**: gọi `/match` HTTP của FSD (cần file base64 và artifacts; bước kiểm tra không cần đến).

## R5. Rubric và nhãn (FR-009, FR-010)

- **Decision**: `label-rubric.md` v1 = rubric 017 (kể cả luật khác ngôn ngữ lập trình chính) + lựa chọn **"u" =
  không đủ thông tin**, dùng khi văn bản không đủ để xét cả ba tiêu chí, không dùng vì phân vân. Nhãn dương nhị phân =
  2; báo cáo phụ ≥ 1.
- **Rationale**: giữ tương thích với dev 017 (264 cặp), để ngưỡng và trọng số chỉnh trên dev dùng được cho test.

## R6. Trang gán mù 2 người (FR-012, FR-013)

- **Decision**: một artifact mới, dựng theo trang 017. Ô chọn rater (A / B) lưu ở trình duyệt; nhãn lưu theo khóa
  `labels/<rater>/<pair_id>`; thứ tự = hoán vị theo seed `<rater>`. Trang không hiển thị nhãn của rater khác (và không
  có nút xem). Lô luyện tập 20 cặp từ dev 017 (lấy theo nhãn: 7 / 7 / 6 cho 0 / 1 / 2), sau khi gán thì hiện nhãn dev
  để tự đối chiếu. Xuất JSON theo rater.
- **Rationale**: dùng lại thứ đã chạy ở 017. Lô luyện tập có phản hồi giúp FSD hiểu rubric mà DE không cần duyệt
  từng câu.
- **Alternatives**: Google Sheet (lộ thứ tự, dễ xem chéo).

## R7. Đồng thuận, phân xử, khóa (FR-014 → FR-018)

- **Decision**:
  - Weighted kappa quadratic dùng lại `match_eval_agreement.weighted_kappa`, chỉ tính trên các cặp cả hai đều gán
    0 / 1 / 2. Cặp "u" được đếm riêng.
  - Sàn 0,60. Dưới sàn thì ghi cờ `low_reliability`, không gán lại.
  - Danh sách cặp lệch xuất ra `adjudication.json`. Hai người bàn, DE quyết; ghi `decided_by` và `note`.
  - Khóa: SHA-256 của `pairs.json`, `inputs.jsonl`, `cvs_en.json`, `labels.json`, `label-rubric.md`. Thêm seed, ngày
    khóa, kappa, cờ vào `manifest.json`.
  - `match-test-verify` thoát 1 nếu bất kỳ băm nào lệch. Mã GĐ2 gọi lệnh này trước khi chấm.
- **Rationale**: khóa kiểm được bằng máy, không dựa vào lời hứa.

## R8. Kiểm phân bố trước khi khóa (SC-005)

- **Decision**: sau khi có nhãn cuối, nếu tập cùng nhóm có một mức < 15% thì được thêm cặp bằng `--extend-seed`, theo
  cùng luật R2, gán mù như cũ, **trước** khi khóa. Bước này chỉ dựa vào nhãn, không dựa vào điểm của hệ nào.

## R9. Nguyên tắc GĐ2 (để thiết kế GĐ1 không chặn GĐ2)

- Hệ: luật = skill-only của 017; BiGRU v1, v2 chấm đúng như FSD gửi, ngưỡng 0,5, hybrid 70/30 như README của FSD;
  embedding 017 cosine-only và full; sentence-transformers đã chọn ở dev (`plans/261126-2235-embedding-model-comparison/`).
- Chỉ số chính: theo CV, trên tập cùng nhóm (nDCG, độ chính xác xếp cặp). Paired bootstrap theo CV. Có bảng 2×2 ngôn
  ngữ, bảng phụ trên tập A = B và trên nhãn thô FSD (FR-015a).
