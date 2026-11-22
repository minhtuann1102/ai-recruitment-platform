# Data Model: Gợi ý việc làm theo độ tương đồng CV–JD (017, GĐ1)

Chỉ ghi phần mới. Bảng `knowledge_chunks`: [`docs/architecture/data-model.md`](../../docs/architecture/data-model.md)
§5. Bản ghi JD chuẩn hóa: [009 jd-record-formats](../009-jd-crawling-seeding/contracts/jd-record-formats.md).

## 1. Bản ghi JD trong chỉ mục (`ai_db.knowledge_chunks`, không đổi DDL)

| Cột | Giá trị |
|---|---|
| `content` | Văn bản đem embed (research R4) |
| `content_hash` | md5(lower(strip(content))), 32 ký tự |
| `embedding` / `embedding_model` | Vector 1536 chiều / tên model không có tiền tố provider (vd `text-embedding-3-small`) |
| `source_type` | `job_description` |
| `category`, `difficulty`, `topic_id` | NULL |
| `language` | `language` của JD 009 (`vi` / `en` / `mixed`, cắt còn 5 ký tự) |
| `metadata` | Xem bên dưới |

`metadata`:

```json
{
  "dataset": "jd-match",
  "chunk_type": "jd_match_summary",
  "jd_id": "careerlink:2213041",
  "title": "Backend Developer (Java)",
  "group": "backend",
  "level": "Mid",
  "deadline": "2026-12-01",
  "skills": ["java", "spring-boot", "postgresql"],
  "synthetic": false
}
```

Luật:
- Mỗi `jd_id` có tối đa một dòng.
- JD có `group = null` không được index (đếm `skipped_no_group`).
- Hai JD có văn bản trùng hash: giữ JD có hạn nộp muộn nhất (bằng nhau thì giữ JD đầu), đếm `skipped_duplicate_hash`.
- Mọi dòng của dataset dùng cùng một `embedding_model` (research R3).

## 2. Snapshot chỉ mục trong ai-service (bộ nhớ)

`JobIndexSnapshot`:
- `jobs`: danh sách `IndexedJob` (`job_id`, `title`, `group`, `level_rank` (int | None), `deadline` (date | None),
  `skills` (tập slug))
- `matrix`: ma trận numpy N × 1536, mỗi hàng đã chuẩn hóa L2
- `embedding_model`, `loaded_at`, `source` (`ai_db` | `mock`)

Vòng đời: chưa có → nạp lần đầu (một task nạp dùng chung; mỗi request chờ tối đa `AI_DB_CONNECT_TIMEOUT_S` + 5 s,
quá hạn hoặc lỗi → 503 `match_index_unavailable`; task vẫn chạy tiếp ở nền) → còn mới → cũ hơn `MATCH_INDEX_REFRESH_S`
(request dùng bản cũ, nạp nền) → thay bằng bản mới. Nạp nền lỗi thì giữ bản cũ và ghi log `match_index_refresh_failed`;
nạp nền ra rỗng trong khi bản cũ có JD thì cũng giữ bản cũ (log `match_index_refresh_empty`). Sau khi nạp lần đầu lỗi, 5 s
tiếp theo request khác nhận 503 ngay, không thử lại (tránh mỗi request chờ hết `connect_timeout`).

## 3. Bảng bậc level và ánh xạ track

Theo Assumptions của spec. Code đặt ở `app/matching/levels_tracks.py`; test so với bảng trong spec.

| Nguồn | Giá trị → bậc |
|---|---|
| JD (009) | Intern 0, Junior 1, Mid 2, Senior 3, Lead 4, Manager 5, null → không lọc |
| Phỏng vấn / request | fresher 1, junior 1, middle 2, senior 3 |
| Suy từ số năm | < 3 → 1, < 5 → 2, còn lại → 3; không có → không lọc |

## 4. Thành phần điểm

- `cosine` = max(0, cos(v_cv, v_jd)).
- `skill_match` = |S_jd ∩ S_cv| / |S_jd|; S_jd rỗng → 0, kèm note `jd_no_skills`.
- `level_fit` = 1 (cùng bậc) | 0,5 (lệch 1 bậc hoặc thiếu level) | 0.
- `score` = w1·cosine + w2·skill_match + w3·level_fit. Khi `degraded`: w2' = w2/(w2+w3), w3' = w3/(w2+w3), không có
  cosine.
- `matched_skills` = tên hiển thị của S_jd ∩ S_cv; `missing_skills` = tên hiển thị của S_jd \ S_cv, theo thứ tự slug.
- S_cv = slug của `skills[].name` ∪ `experiences[].tech` ∪ `projects[].tech`, sau khi chuẩn hóa (research R6).

## 5. Dữ liệu đánh giá (`apps/data-pipeline/data/seeds/match_eval/`, commit)

- `cvs.json`: `[{cv_id, track, level, note, cv_profile}]`. `cv_profile` theo `CvProfile` của ai-service, toàn bộ là dữ
  liệu tổng hợp.
- `pool.json`: `{as_of, jd_ids: [...]}`. Chỉ có mã JD, không chép nội dung crawl (FR-007 của 009).
- `labels.json`: `{labeled_by, labeled_at, method, rubric, pair_set, agreement, final_source, labels: {cv_id: {jd_id:
  0|1|2}}}`. `agreement` ghi kappa có trọng số giữa DE gán mù và LLM (trước và sau lần sửa rubric), `final_source` đếm
  số nhãn cuối lấy từ DE và từ LLM. Nhãn trung gian (DE mù, LLM từng lượt) nằm ngoài git ở
  `data/processed/match_eval/`.
- Bảng soát (`data/processed/match_eval/sheet-*.md`) và kết quả thô (`data/processed/match_eval/run-*.json`) nằm ngoài
  git. Bảng kết quả markdown cuối cùng được commit ở `specs/017-cv-jd-matching/eval-results.md`.
