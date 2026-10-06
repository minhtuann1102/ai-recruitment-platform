# 6. Rubric & báo cáo cuối buổi

> Thuộc bộ [AI Service design doc](README.md). Liên quan: §3.3.3 (Evaluator), §5.3 (điểm lượt), §8 (lưu report).

## 6.1 Bốn tiêu chí và thang band

Giữ nguyên 4 key của `interview_turns.scores` hiện có để không đổi schema. Evaluator chấm **band nguyên 0–4**
(thang thô có mốc rõ giúp LLM chấm ổn định hơn thang 0–10); code quy đổi `× 2.5` sang 0–10 khi lưu và hiển thị.

| Band | `technical_accuracy` — Độ chính xác | `completeness` — Độ đầy đủ (so với key points) | `extensibility` — Chiều sâu & mở rộng | `relevance` — Đúng trọng tâm & mạch lạc |
|---|---|---|---|---|
| **0** | Sai hoàn toàn / không trả lời | Không có ý nào | Chỉ nêu thuật ngữ, không giải thích | Lạc đề |
| **1** | Có ý đúng nhưng kèm lỗi sai nghiêm trọng | Dưới 1/3 key points | Giải thích bề mặt, học thuộc | Phần lớn không liên quan hoặc rất rối |
| **2** | Đúng cơ bản, vài chỗ thiếu chính xác nhỏ | Khoảng một nửa | Giải thích được cơ chế **hoặc** có ví dụ thực tế | Đúng hướng nhưng lan man |
| **3** | Chính xác, không sai đáng kể | Phần lớn (≥ 2/3) | Nêu trade-off / so sánh lựa chọn / kinh nghiệm thực tế cụ thể | Đúng trọng tâm, có cấu trúc |
| **4** | Chính xác và tinh tế (điều kiện, ngoại lệ, khác biệt phiên bản) | Đủ key points và thêm ý đúng liên quan | Internals, edge case, ảnh hưởng khi scale, liên hệ toàn hệ thống | Súc tích, cấu trúc rõ, như trình bày cho đồng nghiệp |

## 6.2 Kỳ vọng theo level

**Band là tương đối với chuẩn level.** Bảng dưới mô tả "đạt chuẩn" (≈ band 3) ở mỗi level; Evaluator nhận bảng
này trong phần tĩnh của prompt. Hệ quả: cùng một câu trả lời, ứng viên Senior nhận band thấp hơn Junior.

| Khía cạnh | Fresher | Junior | Middle | Senior |
|---|---|---|---|---|
| Kiến thức | Định nghĩa đúng, ví dụ đơn giản, nền tảng CS (OOP, cấu trúc dữ liệu, HTTP, SQL cơ bản) | Dùng đúng trong dự án, biết lỗi thường gặp và cách sửa | Giải thích cơ chế bên dưới, so sánh lựa chọn, chọn có lý do | Internals, giới hạn, ảnh hưởng vận hành; chọn giải pháp theo bối cảnh tổ chức |
| Dự án (phase intro) | Mô tả rõ đồ án / bài tập lớn, phần mình làm | Phần việc của mình, công nghệ dùng và lý do cơ bản | Quyết định kỹ thuật mình đưa ra, sự cố đã xử lý, kết quả đo được | Ownership, trade-off kiến trúc, dẫn dắt người khác, bài học |
| Tình huống (phase scenario) | Có quy trình debug hợp lý từng bước | Thiết kế API + schema chạy được, xử lý validate / lỗi | Xử lý concurrency / cache / consistency, nêu trade-off | Scale, failure modes, observability, ước lượng tải, lộ trình triển khai |
| Giao tiếp | Trả lời đúng câu hỏi | Mạch lạc, có ví dụ | Có cấu trúc, chủ động nêu giả định | Dẫn dắt thảo luận, hỏi lại để làm rõ yêu cầu |

### Luật "khắt khe" (áp dụng bằng prompt **và** bằng code)

| Luật | Prompt | Code hậu kiểm |
|---|---|---|
| Chỉ công nhận ý nói rõ, mỗi ý có quote | ✔ | Xóa covered point có quote không khớp câu trả lời |
| `completeness` không vượt tỉ lệ key point có bằng chứng | ✔ | `completeness ≤ ceil(4 × verified_covered / số key_points)` |
| Có misconception nghiêm trọng → `technical_accuracy ≤ 1` | ✔ | `misconceptions` không rỗng → kẹp `≤ 1` |
| Chỉ nêu thuật ngữ → `completeness`, `extensibility ≤ 1` | ✔ | — (phụ thuộc phán đoán) |
| Lượt sau gợi ý (`turn_kind = hint`) → mọi band ≤ 3 | ✔ | Kẹp `≤ 3` |
| `dont_know` / `manipulation` → mọi band = 0 | ✔ | Ép về 0 |
| Dài ≠ tốt | ✔ | Test case "lan man" trong golden set (§10) |

## 6.3 Tổng hợp điểm (code, không phải LLM)

```text
turn_score_10      = turn_score (§5.3, thang band) × 2.5
criterion_10       = band × 2.5
topic_score        = trung bình turn_score_10 của các lượt được chấm trong topic
phase_score        = trung bình topic_score của các topic trong phase
overall            = Σ w_phase × phase_score       (chuẩn hóa lại trọng số nếu thiếu phase)
criteria_averages  = trung bình criterion_10 theo từng tiêu chí, trên mọi lượt được chấm
```

Lượt **không** tính điểm: wrap-up, lượt `degraded`, lượt `asks_clarification` (đã được hỏi lại; lượt trả lời
sau clarify mới được chấm).

**Trọng số phase theo level** (Senior nặng phần thiết kế, Fresher nặng kiến thức nền):

| Phase | Fresher | Junior | Middle | Senior |
|---|---|---|---|---|
| intro | 0.15 | 0.15 | 0.20 | 0.20 |
| technical | 0.60 | 0.55 | 0.45 | 0.35 |
| scenario | 0.25 | 0.30 | 0.35 | 0.45 |

**Kết luận (verdict)** so với chuẩn level đã chọn:

| `overall` | `verdict` | Hiển thị |
|---|---|---|
| ≥ 8.5 | `exceeds` | Vượt kỳ vọng level |
| 7.0 – 8.4 | `meets` | Đạt kỳ vọng level |
| 5.0 – 6.9 | `near` | Gần đạt |
| < 5.0 | `below` | Chưa đạt |

**Độ tin cậy (`confidence`):** `low` nếu < 6 lượt được chấm, hoặc > 20% lượt degraded, hoặc thiếu nguyên một
phase (kết thúc sớm); `medium` nếu 6–9 lượt; `high` nếu ≥ 10 lượt. Report `low` hiển thị cảnh báo rõ.

Ngưỡng verdict và trọng số là **giả định ban đầu**, chỉnh sau khi chạy ứng viên giả lập (§10).

## 6.4 Cấu trúc báo cáo

Report = **phần điểm** (code tính, §6.3) + **phần nhận xét** (Reporter, §3.3.5), ghép trong `/api/finalize`.
Lưu ở `interview_results.report` (JSONB, §8); các cột cũ (`overall_score`, `criteria_averages`, `strengths`,
`improvements`, `ai_summary`) được điền từ report để tương thích.

```jsonc
{
  "schema_version": 1,
  "status": "complete",                         // complete | partial (Reporter lỗi, chỉ có điểm)
  "session": {
    "track": "java_backend", "level": "junior", "duration_s": 1790,
    "end_reason": "plan_complete", "evaluated_turns": 14, "confidence": "high"
  },
  "overall": {
    "score": 5.7, "verdict": "near",
    "summary": "Nền tảng REST và SQL tốt; cơ chế transaction của Spring còn hời hợt, cần ôn trước khi phỏng vấn Junior thật."
  },
  "sections": [                                  // điểm từng phần (phase)
    { "phase": "intro",     "score": 7.0, "weight": 0.15 },
    { "phase": "technical", "score": 5.2, "weight": 0.55 },
    { "phase": "scenario",  "score": 6.0, "weight": 0.30 }
  ],
  "criteria": { "technical_accuracy": 5.5, "completeness": 5.0, "extensibility": 4.5, "relevance": 8.0 },
  "topics": [
    {
      "topic_id": "t2", "title": "Spring @Transactional", "phase": "technical",
      "score": 5.3, "hint_used": true,
      "difficulty_path": [3, 3, 2],
      "comment": "Biết rollback cơ bản nhưng hiểu sai rollback với checked exception; sửa được sau gợi ý."
    }
  ],
  "strengths": [
    { "point": "Thiết kế REST API rõ ràng, đặt tên resource hợp lý", "evidence_turns": [2, 3] }
  ],
  "improvements": [
    { "point": "Rollback rules của Spring", "why": "Lượt 5 cho rằng mọi exception đều rollback", "evidence_turns": [5, 6] }
  ],
  "study_plan": [
    {
      "topic": "Spring transaction: rollback rules, propagation, proxy",
      "priority": "high",
      "actions": ["Đọc mục Rollback rules và Proxy mode", "Viết demo checked vs unchecked exception"],
      "resources": [{ "title": "Spring Framework Docs — Transaction Management", "url": "https://docs.spring.io/..." }]
    }
  ],
  "turns": [                                     // điểm + nhận xét từng câu
    {
      "turn_number": 5, "topic_id": "t2", "turn_kind": "follow_up",
      "question": "Nếu method ném checked exception thì có rollback không?",
      "scores": { "technical_accuracy": 2.5, "completeness": 2.5, "extensibility": 0.0, "relevance": 7.5 },
      "comment": "Sai: mặc định Spring chỉ rollback với RuntimeException và Error."
    }
  ],
  "meta": {
    "difficulty_trajectory": [2, 2, 3, 3, 3, 2, 2, 3],
    "degraded_turns": [], "prompt_versions": { "evaluator": "v3", "reporter": "v2" },
    "disclaimer": "Điểm do AI chấm, mang tính tham khảo cho việc luyện tập."
  }
}
```

`url` trong `resources` do **code tra từ topic catalog** theo `resource_ids` Reporter chọn; Reporter không bao
giờ tự viết URL (chống link bịa).

## 6.5 Quy tắc hiển thị

- **Trong phiên:** ứng viên chỉ thấy câu hỏi, tiến độ (phase, topic x/y, thời gian còn lại). Không thấy điểm hay
  nhận xét (giống phỏng vấn thật, và tránh ứng viên "chơi theo điểm").
- **Sau phiên:** thấy toàn bộ report: tổng điểm + verdict, điểm từng phần, 4 tiêu chí, từng topic, từng câu kèm
  nhận xét, điểm mạnh, cần cải thiện, lộ trình học.
- Luôn hiển thị `disclaimer` và mức `confidence`.
- Report `partial` hiển thị điểm + thông báo "nhận xét chi tiết đang lỗi, bấm để tạo lại".
