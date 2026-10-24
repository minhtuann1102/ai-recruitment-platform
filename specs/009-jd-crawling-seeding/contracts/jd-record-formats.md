# Contract: định dạng file JD

Mọi file dưới `data/raw/` và `data/processed/` nằm ngoài git (FR-007). File duy nhất được commit:
`data/seeds/skill_dictionary.yaml`. JSON Lines UTF-8, một object mỗi dòng, `ensure_ascii=False`.

## Raw JD (`data/raw/jd/<nguồn>/<ts>.jsonl`, `data/raw/jd/synthetic/<ts>.jsonl`)

```json
{
  "source": "careerviet",
  "source_job_id": "35C1A2B3",
  "url": "https://careerviet.vn/vi/tim-viec-lam/....35C1A2B3.html",
  "crawled_at": "2026-10-27T03:00:00Z",
  "title": "Backend Developer (NodeJS)",
  "company": "Công ty ABC",
  "skills_raw": ["NodeJS", "PostgreSQL"],
  "description_text": "Mô tả công việc\n...\nYêu cầu\n...",
  "location_raw": ["Hồ Chí Minh"],
  "experience_raw": "36 months",
  "employment_type_raw": ["FULL_TIME"],
  "salary_raw": {"currency": "VND", "min": 20000000, "max": 30000000, "text": null},
  "date_posted": "2026-10-20",
  "valid_through": "2026-11-20",
  "synthetic": false
}
```

- Bắt buộc: `source`, `source_job_id`, `url` (synthetic: `null`), `crawled_at`, `title`, `company`, `description_text`.
- `description_text`: HTML đã đổi sang text, giữ xuống dòng ở tiêu đề section để tách section; PII đã xóa.
- Synthetic thêm `"cell": {"group": "ai_data", "level": "Lead", "city": "Đà Nẵng"}`, `"synthetic": true`,
  `"source": "synthetic"`.
- Ví dụ trên là dữ liệu bịa để minh họa định dạng.

## Normalized JD (`data/processed/jd_normalized.jsonl`)

```json
{
  "jd_id": "careerviet:35C1A2B3",
  "title": "Backend Developer (NodeJS)",
  "company": "Công ty ABC",
  "skills": ["nodejs", "postgresql"],
  "skills_unknown": [],
  "group": "backend",
  "level": "Mid",
  "work_type": "onsite",
  "city": "Hồ Chí Minh",
  "salary_min": 20000000, "salary_max": 30000000, "salary_currency": "VND",
  "date_posted": "2026-10-20", "deadline": "2026-11-20",
  "sections": {"summary": "...", "description": "...", "requirements": "...", "benefits": "..."},
  "language": "vi",
  "content_hash": "sha256:...",
  "synthetic": false,
  "source_url": "https://careerviet.vn/..."
}
```

## JD Chunk (`data/processed/jd_chunks.jsonl`)

`{"jd_id", "section", "content", "content_hash", "skills", "company", "language", "source_url"}`. Section dài hơn giới
hạn ký tự của 005 chia nhỏ, không cắt mất nội dung. Chỉ index khi làm US3 (Stretch).

## Skill Dictionary (`data/seeds/skill_dictionary.yaml`)

```yaml
- slug: nodejs
  name: Node.js
  category: Backend        # giá trị cột job_db.skills.category
  group: backend           # backend | frontend | mobile_fullstack | devops | ai_data
  aliases: [node, node.js, nodejs, node js]
```

Luật: `slug` duy nhất, chữ thường; bí danh so khớp không phân biệt hoa thường, không trùng giữa hai kỹ năng; test kiểm
cả hai luật.
