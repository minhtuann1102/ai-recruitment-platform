# Data Model: 019 GĐ1

Tất cả là file JSON / JSONL. Seed (commit được): `apps/data-pipeline/data/seeds/match_test/`. Processed (gitignored):
`apps/data-pipeline/data/processed/match_test/`.

## 1. `pairs.json` (seed)

```json
{"version": 1, "seed": "match-test-v1", "created_at": "2026-11-27",
 "cvs": [{"cv_id": "cand-017", "track": "java_backend", "level": "junior"}],
 "pairs": [{"pair_id": "t001", "cv_id": "cand-017", "jd_id": "itviec:abc", "pair_type": "same|adjacent|far",
            "jd_language": "vi|en|mixed", "flags": ["no_requirements", "no_level", "no_skills"]}]}
```

Ràng buộc: 30 CV × 7 = 210 `pair_id` duy nhất (`t001`…`t210`, đánh số sau khi xáo theo seed); không `cv_id` nào thuộc
`match_eval/cvs.json`; không `jd_id` nào thuộc pool 017 hay trùng `content_hash` với pool; mỗi `jd_id` ≤ 3 lần (frontend
≤ 4). File không có văn bản JD.

## 2. `cvs_en.json` (seed)

`{"<cv_id>": CvProfile}`: bản tiếng Anh của 30 CV, cùng cấu trúc với `candidate_cvs.json[].cv_profile`. Kèm
`_meta`: `{"method": "LLM translation (Claude sonnet worker), terms kept", "date": ..., "spot_checked_by_de": [cv_id…]}`.

## 3. `inputs.jsonl` (processed, gitignored; băm ở manifest)

Mỗi dòng ứng với một `(pair_id, cv_lang)`, tổng 420 dòng:

```json
{"pair_id": "t001", "cv_lang": "vi|en", "cv_text_full": "...", "cv_profile": {},
 "jd_rater_text": "...", "jd_fsd": {"title": "", "description": "", "requirements": "", "responsibilities": "",
 "education": "", "experience": "Entry Level|Mid Level|Senior Level|Lead|Manager|", "skills": "a, b"},
 "jd_id": "itviec:abc", "sha256": {"cv": "...", "jd_rater": "...", "jd_fsd": "..."}}
```

Kiểm tra: `len(cv_text_full) ≤ 30000`, `len(jd_rater_text) ≤ 30000`, `CvProfile` hợp lệ, `jd_id` trong tập index.

## 4. `practice.json` (seed)

20 cặp lấy từ dev 017: `[{"practice_id": "p01", "cv_id", "jd_id", "dev_label"}]`. Nhãn dev chỉ hiện **sau** khi rater
nộp lô luyện tập.

## 5. Nhãn

- `labels_a.json`, `labels_b.json` (seed, xuất từ trang): `{"rater": "A|B", "rubric_version": "v1",
  "labels": {"t001": 0|1|2|"u"}, "exported_at": "..."}`.
- `adjudication.json` (processed): `[{"pair_id", "a", "b", "final", "decided_by": "both|DE", "note"}]` cho mọi cặp
  A ≠ B.
- `labels.json` (seed): `{"pair_id": {"a", "b", "final"}}`. `final = "u"` nghĩa là cặp bị loại khỏi chỉ số.

## 6. `manifest.json` (seed)

```json
{"locked_at": "...", "seed": "match-test-v1", "rubric_version": "v1",
 "sha256": {"pairs.json": "", "cvs_en.json": "", "inputs.jsonl": "", "labels.json": "", "label-rubric.md": ""},
 "agreement": {"weighted_kappa": 0.0, "exact": 0.0, "within_1": 0.0, "n": 0, "u_a": 0, "u_b": 0},
 "low_reliability": false, "excluded_u": 0,
 "label_distribution_same_group": {"0": 0, "1": 0, "2": 0}}
```

Trạng thái: `built` (có pairs + inputs) → `labeled` (có labels_a + labels_b) → `locked` (có manifest). Sau `locked`,
mọi thay đổi làm `match-test-verify` thất bại.
