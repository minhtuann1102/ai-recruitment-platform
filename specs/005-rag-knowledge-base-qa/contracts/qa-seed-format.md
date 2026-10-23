# Contract: Q&A Seed và Golden Set

Lệnh `validate` (FR-005) kiểm mọi luật dưới đây; vi phạm mức **lỗi** → thoát mã 1, mức **cảnh báo** → chỉ in.
`process`/`index` dùng cùng luật mức cặp nhưng **loại cặp lỗi kèm lý do và chạy tiếp** (US2-1); câu hỏi trùng tuyệt
đối giữ cặp có `qa_id` nhỏ hơn.

## Seed: `apps/data-pipeline/data/seeds/interview_qa/*.json`

Mỗi file là một mảng JSON; loader gộp mọi file theo thứ tự tên. Mỗi phần tử:

| Trường | Kiểu | Bắt buộc | Luật |
|---|---|---|---|
| `qa_id` | string | có | `^de-qa-\d{4}$`; duy nhất toàn bộ seed; gán khi tạo, không đổi, không tái sử dụng |
| `topic_id` | string | có | id của một **topic** (không phải scenario) trong catalog lúc chạy (FR-002) |
| `question` | string | có | ≥ 10 ký tự sau làm sạch |
| `answer` | string | có | ≥ 30 ký tự sau làm sạch |
| `difficulty` | enum | có | `easy` (rubric 1–2) \| `medium` (3) \| `hard` (4–5) — FR-001 |
| `language` | enum | có | `vi` \| `en` (FR-004: đáp án tiếng Việt giữ thuật ngữ Anh; tiếng Anh phải gắn `en`) |
| `tags` | string[] | không | chữ thường, không trùng |
| `source` | string | có | URL nguồn khi **bất kỳ** phần chữ nào lấy từ ngoài; `"self"` khi tự soạn hoàn toàn |
| `license` | string | có | thuộc danh sách cho phép (research R6). Cặp ngoài: giấy phép của nguồn; cặp `self`: giấy phép của bộ seed (khai trong `NOTICE`) |
| `attribution` | string | khi `source ≠ "self"` | tác giả / dự án gốc, vd `"sudheerj/reactjs-interview-questions contributors"` |
| `synthetic` | bool | có | `true` khi đáp án tự soạn (kể cả câu hỏi lấy từ nguồn công khai); `false` chỉ khi cả hỏi lẫn đáp lấy/chuyển thể từ nguồn có giấy phép. Quota 50% chỉ đếm `false` |
| `reviewed_by` | string | có (mọi cặp) | người đã đọc đáp án; cặp dịch/chuyển thể phải được đối chiếu bản gốc. Chỉ điền sau khi đọc thật — bản nháp để trống nên `validate` thất bại cho tới khi duyệt. Ngoại lệ: cặp hard tự viết duyệt theo spec Clarification Session 2026-10-23 (đọc nhóm phải đọc + mẫu, phần còn lại chấp nhận theo báo cáo duyệt có bằng chứng) |

`category` **không** có trong seed: suy ra từ catalog theo `topic_id`.

### Luật kiểm tra

| Luật | Mức | Nguồn |
|---|---|---|
| Thiếu trường / sai kiểu / sai enum / sai pattern | lỗi | FR-001 |
| `topic_id` không thuộc catalog hoặc là id scenario | lỗi | FR-002 |
| `license` ngoài danh sách cho phép; `source ≠ "self"` mà không phải URL hoặc thiếu `attribution`; `synthetic=false` mà `source = "self"` | lỗi | FR-003, SC-002 |
| Thiếu `reviewed_by` (mọi cặp) | lỗi | FR-003 |
| Cặp `source = "self"` mà `license` ≠ giấy phép bộ seed (`CC-BY-4.0`, khai trong `NOTICE`) | lỗi | research R6 |
| Cặp `CC-BY-SA-*` khi bộ seed chưa chuyển sang `CC-BY-SA-4.0` (share-alike) | lỗi | research R6 |
| `qa_id` trùng | lỗi | Clarifications |
| Câu hỏi trùng tuyệt đối (sau làm sạch + lower) — báo cả hai `qa_id` | lỗi | US1-3 |
| Câu hỏi gần trùng (ratio ≥ 0.9 sau bỏ dấu, research R3) | cảnh báo | FR-005 |
| Email hoặc số điện thoại (regex) trong `question`/`answer` | lỗi | FR-005, SC-002 |
| Topic trong catalog có < 2 cặp | lỗi (`--strict`) / cảnh báo (mặc định) | SC-001 |
| < 200 cặp; topic có level `middle`/`senior` có < 2 cặp `hard` | lỗi (`--strict`) / cảnh báo (mặc định) | SC-001 (sửa 2026-10-19) |

Mặc định chỉ cảnh báo các ngưỡng phân bố để soạn dần được; nghiệm thu chạy `validate --strict`.

Báo cáo phân bố: số cặp theo topic / category / difficulty / language / license / nguồn (`self`, `owner/repo` GitHub hoặc tên miền), tỉ lệ công khai.

### Ví dụ

```json
{
  "qa_id": "de-qa-0001",
  "topic_id": "node.core.event-loop",
  "question": "Giải thích các pha của event loop trong Node.js?",
  "answer": "Event loop gồm các pha timers, pending callbacks, poll, check, close callbacks ...",
  "difficulty": "medium",
  "language": "vi",
  "tags": ["event-loop"],
  "source": "https://github.com/DevLoversTeam/nodejs-interview-questions",
  "license": "MIT",
  "attribution": "DevLoversTeam/nodejs-interview-questions contributors",
  "synthetic": false,
  "reviewed_by": "<người đã đọc và đối chiếu bản gốc>"
}
```

## Dữ liệu crawl: `apps/data-pipeline/data/raw/enriched_qa/*.json` (dataset `de_crawled_qa`, KHÔNG commit)

Sinh bởi `enrich` (quyết định 2026-10-19). Cùng các trường trên, khác ở: `qa_id` khớp `^cr-[a-z0-9-]+-[0-9a-f]{8}$`
(md5 của URL + câu hỏi gốc); `language = vi`; `source` là URL; `license` ghi nếu biết, còn lại `unknown` (không kiểm
danh sách); `synthetic = false`; không cần `reviewed_by` từng cặp (review theo mẫu); thêm `source_lang`,
`question_original`, `answer_original`, `truncated` để đối chiếu bản dịch. Luật topic, độ dài, PII, trùng như seed.

## Golden set: `apps/data-pipeline/data/seeds/golden_set.json`

Mảng JSON; mỗi phần tử:

| Trường | Kiểu | Bắt buộc | Luật |
|---|---|---|---|
| `query_id` | string | có | `^gq-\d{3}$`, duy nhất |
| `query` | string | có | MUST NOT trùng nguyên văn (sau làm sạch + lower) câu hỏi nào trong seed (US4-2) |
| `group` | enum | có | `vi` (a) \| `mixed` (b) \| `en` (c) \| `vi_to_en` (d) \| `no_diacritics` (e) |
| `expected_qa_ids` | string[] | có | ≥ 1 phần tử, mỗi `qa_id` có trong seed |
| `filters` | object | không | khóa như bộ lọc truy hồi ([knowledge-chunks-io.md](knowledge-chunks-io.md)) |
| `source` | string | có | nguồn truy vấn (`"handwritten"` hoặc URL dataset + giấy phép) |
| `approved_by` | string | không | AIE điền khi duyệt nhãn (FR-020); trống → báo cáo ghi "chưa duyệt" |

Ràng buộc tập: ≥ 20 truy vấn; mỗi nhóm (a)–(e) ≥ 1 truy vấn (lỗi nếu thiếu).
