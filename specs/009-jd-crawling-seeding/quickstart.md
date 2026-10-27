# Quickstart: kiểm chứng JD Crawling & Seeding

Checklist nghiệm thu theo story và kịch bản demo Sprint 2. Bash (Git Bash trên Windows), chạy trong
`apps/data-pipeline/`. Lệnh và mã thoát: [contracts/pipeline-cli-jd.md](contracts/pipeline-cli-jd.md); định dạng file:
[contracts/jd-record-formats.md](contracts/jd-record-formats.md).

## 0. Chuẩn bị

Như [005 quickstart §0](../005-rag-knowledge-base-qa/quickstart.md) (venv, `requirements-dev.txt`, `.env`). §1–§2 không
cần DB và key; §4 cần `LLM_API_KEY`; §5 cần `job_db` đã chạy migration của job-service (007).

## 1. Crawl thử nhỏ (US1, SC-002) — không DB, không key

```bash
python -m pipeline crawl-jd --source careerviet --max-pages 2 --max-jobs 10
```

Kỳ vọng: thoát 0; log có `robots checked: https://careerviet.vn/robots.txt [200]`; mỗi request cách nhau ≥ 2 giây;
`data/raw/jd/careerviet/<ts>.jsonl` có ≤ 10 record đủ trường bắt buộc. Chạy lại cùng lệnh → không record trùng: id đã
có bị bỏ qua, không request lại trang chi tiết (`id đã có, bỏ qua` tăng). `--max-jobs` tính trên JD **mới**, nên lần
chạy lại vẫn lấy tiếp tối đa 10 JD chưa có; `record mới: 0` chỉ khi các trang trong `--max-pages` đã crawl hết.

Kiểm luật crawler: `pytest tests -k "jd_page_parser or polite_fetcher"` (fixture HTML tự soạn: `JobPosting` trong mảng /
`@graph`, JSON lỗi, robots 2 nhóm `*`, 3 lần 403 liên tiếp → dừng nguồn).

## 2. Crawl đầy đủ (US1, SC-001)

```bash
python -m pipeline crawl-jd            # 4 nguồn, mặc định --delay 2
```

Kỳ vọng: mỗi nguồn kết thúc `ok` hoặc `blocked` (thoát 4, không thử né); tổng hợp số record theo nguồn. Thời gian dài
do giới hạn tốc độ (không tính vào SC-006).

## 3. Xử lý offline (US2, SC-001, SC-003)

```bash
python -m pipeline process-jd
grep -cE "[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}" data/processed/jd_normalized.jsonl   # email: kỳ vọng 0
grep -ciE "linkedin\.com/in/|facebook\.com/|fb\.com/|zalo\.me/|t\.me/" data/processed/jd_normalized.jsonl   # kỳ vọng 0
```

Kiểm tay thêm: đọc 10 JD ngẫu nhiên, không còn dòng "Liên hệ / Contact / Anh, Chị + tên" kèm số hay email.

Kỳ vọng: thoát 0; báo cáo in `pii_remaining 0`, `with_skill_ratio ≥ 0.9`, bị loại theo lý do (`not_it`, …), phân bố
group / level / city, top kỹ năng ngoài danh mục. Chạy lại → output giống hệt (deterministic).
Kiểm luật: `pytest tests -k "skill_dictionary or jd_normalizer or jd_sections or jd_record"`.

## 4. Bù synthetic (US5, SC-008) — cần key

```bash
python -m pipeline synth-jd --dry-run            # chỉ in ô thiếu, không gọi LLM
python -m pipeline synth-jd --limit 10           # thử nhỏ, đọc kỹ 10 JD
python -m pipeline synth-jd && python -m pipeline process-jd
```

Kỳ vọng: chỉ sinh cho ô thiếu; mọi JD synthetic có `synthetic: true`, công ty hư cấu (không trùng công ty crawl), 0
PII / URL; sau `process-jd` lần 2: ≥ 500 JD hợp lệ, in tỉ lệ crawl / synthetic. Chạy lại `synth-jd` khi không còn ô thiếu
→ 0 lời gọi LLM.
Kiểm luật: `pytest tests -k "jd_gap or jd_synthetic"` (client LLM giả trả JSON lỗi / có email / kỹ năng lạ → bị loại).

## 5. Seed `job_db` (US4, SC-005) — cần migration `company_profiles` (004) + job-service (007)

```bash
python -m pipeline seed-jobs --count 200
python -m pipeline seed-jobs --count 200        # lần 2: 0 posting mới
```

Kỳ vọng: preflight báo đủ bảng/cột (thiếu → thoát 2, không ghi); ≥ 200 posting, phủ ≥ 5 nhóm / ≥ 3 cấp / ≥ 3 thành phố,
JD crawl được chọn trước; tìm kiếm của 007 trả kết quả cho "NodeJS", "React", "DevOps", "Senior", "Hà Nội".
Mỗi công ty có một Employer seed (email miền `seed.ai-recruit.test`), không đăng nhập được. `seed-jobs --clean`
chỉ xóa dữ liệu của Employer seed.

## 6. Không commit nội dung crawl (SC-003)

```bash
git status --porcelain apps/data-pipeline/data/raw apps/data-pipeline/data/processed   # kỳ vọng rỗng
```

## Demo Sprint 2

§3 báo cáo phân bố trên dữ liệu thật → §4 tỉ lệ crawl / synthetic → (khi có migration 004, 007) §5 danh sách job trên job-service.
