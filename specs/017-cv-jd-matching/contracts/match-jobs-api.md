# Contract: `POST /api/match/jobs` (ai-service, nội bộ)

Endpoint nội bộ. Request phải có header `X-Internal-Token`, do middleware hiện có kiểm (`app/security.py`). JSON dùng
snake_case. Lỗi theo `{error, message, details}` ([`docs/ai-service/06`](../../../docs/ai-service/06-api-contract.md)).
Khi merge PR-2, contract này được chép vào `docs/ai-service/06` (constitution III).

## Request

```json
{
  "cv_profile": { "...": "CvProfile, kết quả /api/cv/parse" },
  "track": "java_backend",
  "level": "middle",
  "as_of": "2026-11-21",
  "job_ids": ["careerlink:2213041"],
  "page": 1,
  "page_size": 10
}
```

| Trường | Bắt buộc | Luật |
|---|---|---|
| `cv_profile` | có | Theo `CvProfile` (`app/models_cv.py`) |
| `track` | có | Một trong 6 track phỏng vấn; track lạ → 422 `unknown_track` |
| `level` | không | `fresher` \| `junior` \| `middle` \| `senior`; không có thì suy từ số năm |
| `as_of` | không | `YYYY-MM-DD`, mặc định ngày hiện tại (Asia/Ho_Chi_Minh) |
| `job_ids` | không | 1–200 mã; chỉ xét JD trong danh sách (dùng cho đánh giá, sau này cho GĐ2) |
| `page` | không | ≥ 1, mặc định 1 |
| `page_size` | không | 1–50, mặc định 10 |

## Response 200

```json
{
  "items": [
    {
      "job_id": "careerlink:2213041",
      "title": "Backend Developer (Java)",
      "group": "backend",
      "level": "Mid",
      "deadline": "2026-12-01",
      "score": 0.712,
      "components": { "cosine": 0.583, "skill_match": 0.857, "level_fit": 1.0 },
      "matched_skills": ["Java", "PostgreSQL", "Spring Boot"],
      "missing_skills": ["Kafka"],
      "notes": []
    }
  ],
  "page": 1,
  "page_size": 10,
  "total": 37,
  "metadata": {
    "as_of": "2026-11-21",
    "weights": { "cosine": 0.6, "skill_match": 0.3, "level_fit": 0.1 },
    "max_level_gap": 1,
    "candidate_level_rank": 2,
    "embedding_model": "text-embedding-3-small",
    "index_size": 360,
    "index_loaded_at": "2026-11-21T16:02:11Z",
    "cv_skill_count": 9,
    "unknown_skills_count": 2,
    "degraded": false,
    "degraded_reason": null,
    "mock": false,
    "usage": { "embedding_tokens": 212 },
    "timing_ms": { "embed": 180, "score": 4, "total": 190 }
  }
}
```

- Thứ tự: `score` giảm dần; hòa thì `job_id` tăng dần.
- `total` = min(số JD qua lọc cứng, `MATCH_MAX_RESULTS`). Trang vượt quá `total` thì trả `items: []`, không báo lỗi.
- `notes`: `jd_no_skills`, `jd_no_level`.
- `degraded_reason`: `embedding_unavailable` | `embedding_timeout` | `embedding_error`.
- Văn bản CV không bao giờ được ghi log, chỉ log số lượng và thời gian.

## Lỗi

| HTTP | `error` | Khi nào |
|---|---|---|
| 401 | `unauthorized` | Thiếu hoặc sai `X-Internal-Token` (middleware) |
| 422 | `invalid_request` | Sai schema: `page_size` > 50, `as_of` sai định dạng, `job_ids` > 200, level lạ (handler hiện có) |
| 422 | `unknown_track` | `track` không thuộc 6 track |
| 503 | `match_index_unavailable` | Chưa có snapshot và không đọc được ai_db |

Chỉ mục rỗng (chưa chạy `index-jd-match`): trả 200 với `items: []`, `total: 0`, `metadata.index_size: 0`.

## Cấu hình (env của ai-service, thêm vào `apps/ai-service/.env.example`)

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `MATCH_MOCK` | `false` | `true`: chỉ mục mẫu + embedding băm, không đọc ai_db, không gọi provider |
| `MATCH_WEIGHTS` | `0.6,0.3,0.1` | cosine, skill_match, level_fit; mỗi số ≥ 0, tổng bằng 1 (sai thì không khởi động được) |
| `MATCH_MAX_LEVEL_GAP` | `1` | Độ lệch bậc tối đa |
| `MATCH_MAX_RESULTS` | `50` | Trần của `total` |
| `MATCH_INDEX_REFRESH_S` | `300` | Tuổi tối đa của snapshot trước khi nạp nền |
| `MATCH_EMBED_TIMEOUT_S` | `5` | Quá hạn thì `degraded` |

Dùng lại các biến có sẵn: `AI_DB_URL`, `AI_DB_CONNECT_TIMEOUT_S`, `EMBEDDING_MODEL`, `LLM_*`.
