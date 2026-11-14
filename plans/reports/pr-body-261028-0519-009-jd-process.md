## Summary
Sprint 2 · `009-jd-crawling-seeding` · **US2 `process-jd` (T017–T028, S2-DE-2)**: raw JD → Normalized JD + chunk, kèm báo cáo phân bố. Code do phiên cloud viết (T017–T028); review 2026-10-27 chạy trên 515 JD crawl thật, các lỗi tìm ra đã sửa ở đây. Quyết định của DE ghi ở spec → Clarifications **Session 2026-10-28**.

## Thay đổi
- `data/seeds/skill_dictionary.yaml` + `pipeline/skill_dictionary.py`: 138 kỹ năng (bí danh, khớp trong văn bản theo ranh giới từ, nhóm).
- `pipeline/jd_normalizer.py` (cấp bậc, loại hình, ngôn ngữ), `jd_city.py` (thành phố), `jd_salary.py` (lương), `jd_sections.py` (section + chunk).
- `pipeline/jd_it_filter.py` (lọc IT), `jd_record_builder.py`, `jd_record_dedup.py`, `jd_process_report.py`, `jd_process_command.py` + lệnh `python -m pipeline process-jd`.
- Test: 5 file mới, toàn bộ suite data-pipeline **328 passed**.

## Sửa sau review (Clarifications 2026-10-28)
- **Cấp bậc**: dưới 12 tháng = fresher → `Junior`; `Intern` chỉ từ tiêu đề. itviec `experience_raw` chỉ là nhóm ("10 months"/"37 months"/"61 months") → bỏ qua, lấy số năm trong mô tả.
- **Lọc IT**: thêm IT / kỹ sư hệ thống / security / an ninh mạng / QA-QC / DBA; thẻ `skills_raw` cụ thể cũng tính; kỹ năng chung chung (cơ sở dữ liệu, network, cloud, QA/QC, IT support) không tự làm JD thành IT; loại sales / tư vấn / presale / giảng dạy / hành chính / phiên dịch / kiểm toán viên và **BA, PO, PM, Scrum Master** (để sau, raw vẫn giữ).
- **Thành phố**: dòng "Địa điểm:" trong mô tả + bảng quận → thành phố (careerviet chỉ ghi quận). Không crawl lại.
- **Nhóm**: kỹ năng trong tiêu đề quyết định ("Angular Developer" không còn bị xếp `devops`).
- **Section**: thêm tiêu đề careerlink ("Kinh nghiệm / Kỹ năng chi tiết"), careerviet ("Tiêu chuẩn tuyển dụng"), topdev ("Your skills & qualifications", "Benefits for you"); tiêu đề con giữ làm nội dung.
- **Danh mục**: tách bí danh gộp nhầm (vite, grafana, jest, rag, tableau, ...); "Khoa học máy tính" không còn khớp machine learning; "TS", "ai" chỉ nhận khi là thẻ. **Lương**: sửa tiền tệ sau đơn vị "k", bỏ VND < 1 triệu.

## Chạy trên raw thật (T029, 2026-10-28, chỉ ở máy DE)
| Chỉ số | Giá trị |
|---|---|
| records_in | 515 crawl (careerlink 37, careerviet 173, itviec 152, topdev 153) |
| rejected | not_it 174, missing_field 0, duplicate 0 |
| jd_out / chunks_out | 341 / 1053 |
| with_skill_ratio (SC-001 ≥ 0.9) | **0.9853** |
| pii_remaining | **0** |
| group | devops 137, backend 103, ai_data 77, mobile_fullstack 11, frontend 8, unknown 5 |
| level | Junior 98, Senior 87, Mid 81, Manager 24, Lead 11, Intern 3, unknown 37 |
| city | Hà Nội 184, Hồ Chí Minh 122, Đà Nẵng 8, khác 19, unknown 8 |
| cells (group, level, city) | 56 |
| có `requirements` / đủ điều kiện seed T041 | 215 / **186** |

Chạy lại 2 lần: file output giống hệt từng byte. Không file dữ liệu nào vào git (`data/processed` gitignore).

## Cần FSD xác nhận (T017)
`main` chưa có seed skills của FSD, nên danh sách slug + `category` (giá trị cột `job_db.skills.category`) dưới đây là đề xuất. Lệch slug sẽ thành hai kỹ năng ở US4 (seed). Category mới so với ví dụ ban đầu: AI/ML, Cloud, Data, Database, Testing, System Design.
- **AI/ML** (13): `artificial-intelligence`, `machine-learning`, `deep-learning`, `nlp`, `computer-vision`, `opencv`, `llm`, `generative-ai`, `rag`, `tensorflow`, `keras`, `pytorch`, `scikit-learn`
- **Backend** (30): `java`, `python`, `csharp`, `cpp`, `c`, `golang`, `php`, `ruby`, `rust`, `nodejs`, `nestjs`, `expressjs`, `spring-boot`, `hibernate`, `jpa`, `django`, `flask`, `fastapi`, `dotnet`, `laravel`, `ruby-on-rails`, `rest-api`, `graphql`, `rpa`, `cobol`, `servicenow`, `grpc`, `oop`, `kafka`, `rabbitmq`
- **Cloud** (4): `aws`, `azure`, `gcp`, `cloud-computing`
- **Data** (18): `scala`, `r`, `pandas`, `numpy`, `spark`, `hadoop`, `airflow`, `etl`, `data-engineering`, `data-governance`, `data-warehouse`, `bigquery`, `snowflake`, `redshift`, `power-bi`, `tableau`, `looker`, `data-analysis`
- **Database** (11): `sql`, `database`, `mysql`, `mariadb`, `postgresql`, `sql-server`, `oracle`, `mongodb`, `redis`, `elasticsearch`, `cassandra`
- **DevOps** (22): `bash`, `docker`, `kubernetes`, `linux`, `git`, `ci-cd`, `jenkins`, `github-actions`, `gitlab-ci`, `terraform`, `ansible`, `nginx`, `prometheus`, `grafana`, `networking`, `cisco`, `it-infrastructure`, `it-support`, `information-security`, `penetration-testing`, `devops`, `sre`
- **Frontend** (15): `javascript`, `typescript`, `html`, `css`, `react`, `vuejs`, `angular`, `nextjs`, `nuxtjs`, `redux`, `jquery`, `tailwindcss`, `sass`, `webpack`, `vite`
- **Fullstack** (1): `fullstack`
- **Mobile** (9): `kotlin`, `swift`, `dart`, `objective-c`, `android`, `ios`, `react-native`, `flutter`, `xamarin`
- **System Design** (3): `microservices`, `system-design`, `design-patterns`
- **Testing** (12): `software-testing`, `manual-testing`, `automation-testing`, `selenium`, `cypress`, `playwright`, `jmeter`, `performance-testing`, `unit-testing`, `junit`, `jest`, `pytest`

## Còn mở
- **T029**: DE đọc tay 10 JD ngẫu nhiên (không còn dòng liên hệ) rồi tick.
- **186 < 200 JD đủ điều kiện seed**: US5 (`jd-synthetic`, PR sau) phải bù; frontend (8) và mobile_fullstack (11) dưới sàn 20 của FR-022.
- 13 JD topdev chỉ có phần phúc lợi (crawler không lấy được vai trò / yêu cầu) → không đủ điều kiện seed, không ảnh hưởng `process-jd`.
- Cấp bậc trống 37 JD (tiêu đề không ghi cấp, mô tả không có số năm).
