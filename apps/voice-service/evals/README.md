# Bộ đo voice (spec 015 US4)

Đo nhận dạng giọng nói, thuật ngữ, độ trễ, TTS và credit trên giọng thật, theo [research R10](../../../specs/015-voice-mode/research.md).
Kết quả ghi ở `specs/015-voice-mode/eval-results.md`.

| File | Commit? | Nội dung |
|---|---|---|
| `manifest.jsonl` | có | 30 clip: `{clip_id, golden_id?, speaker, kind, track}`. Sinh lại: `python -m evals.build_manifest` |
| `phrases/<track>.json` | có | danh sách thuật ngữ gửi làm `keywords` (= `GET /api/stt/phrases` của ai-service, ghi commit và ngày sinh) |
| `pricing.json` | có | đơn giá Blaze 2026-11-25 và giả định một phiên 20 phút |
| `audio/` | **không** | file ghi âm (gitignore) |
| `out/` | **không** | `stt_samples.jsonl` và bản ghi thô (gitignore) |

## Clip

- **`read` (r01–r24)**: đọc nguyên văn câu trả lời của một mẫu golden Evaluator. Văn bản đó là bản chuẩn để tính lỗi.
  4 track (java, nodejs, python, ai_engineer), mỗi track 6 mẫu, 2 mẫu cho mỗi mức strong / medium / weak. Mẫu weak
  khoảng 5 giây, mẫu strong 30–45 giây.
- **`free` (f01–f06)**: trả lời tự do 30–90 giây một câu hỏi của track. Không có bản chuẩn, chỉ dùng xem chỉ số trình bày.

Mỗi người ghi có mã ẩn danh: `s1`, `s2`. Không ghi tên thật vào manifest, file hay báo cáo. Ai giữ mã nào thì chỉ ghi
ngoài repo.

## Ghi âm

1. Người ghi điền và gửi lời đồng ý (mẫu bên dưới) cho owner trước khi ghi.
2. In phiếu đọc của mình:
   ```bash
   cd apps/voice-service
   python -m evals.build_manifest --sheet s1 > ../../../phieu-s1.md   # ngoài repo
   ```
3. Mỗi clip ghi một file, tên đúng `clip_id`: `evals/audio/r01.webm`. Định dạng nhận: webm, ogg, wav, mp3, m4a (ghi
   bằng trình duyệt ra webm/opus là được). Phòng yên tĩnh, micro máy tính hoặc tai nghe, nói tốc độ bình thường.
4. Bấm ghi, chờ khoảng 1 giây rồi mới đọc; đọc xong chờ khoảng 1 giây rồi dừng. Đọc sai thì ghi lại cả clip.
5. Không đổi file sau khi đo. Ghi lại thì chạy lại bộ đo.

### Mẫu xác nhận đồng ý

> Tôi, người ghi mã `s_`, đồng ý ghi âm giọng nói của mình để đo chất lượng nhận dạng giọng nói của đồ án AI Recruitment
> Platform. Tôi biết: file ghi âm được gửi tới voice-service và nhà cung cấp Blaze (xử lý tại Việt Nam, cam kết không lưu);
> file chỉ nằm trên máy của owner, không đưa lên git hay nơi công khai; báo cáo chỉ có số liệu và mã ẩn danh, không có
> tên tôi hay nội dung phần trả lời tự do; tôi có thể rút lại đồng ý và yêu cầu xóa file bất cứ lúc nào.
> Ngày: ____ Xác nhận (tin nhắn hoặc chữ ký): ____

## Chạy đo

Cần voice-service đang chạy với key Blaze thật (`apps/voice-service/.env`, xem [README của service](../README.md)).

```bash
cd apps/voice-service
uvicorn app.main:app --port 8020          # terminal khác
python -m evals.run_voice_eval --base-url http://localhost:8020 \
  --out ../../specs/015-voice-mode/eval-results.md
```

- Chạy với các clip đã có trong `audio/`, liệt kê clip còn thiếu trong báo cáo. Chưa có clip nào thì dừng và không ghi
  báo cáo (mã thoát 2). Service báo `provider` khác `blaze` thì dừng (mã thoát 1).
- Clip `read` gọi STT 2 lần (có / không keywords), clip `free` 1 lần; TTS đọc 20 câu hỏi golden. Đủ 30 clip tốn khoảng
  vài chục credit (xem phần credit của báo cáo). `--limit N` chỉ đo N clip đầu và N câu TTS; `--skip-tts` bỏ phần TTS.
- Token nội bộ lấy từ `VOICE_SERVICE_INTERNAL_TOKEN` (biến môi trường hoặc `.env` của service).
- Thuật ngữ lấy từ `phrases/`. Muốn lấy lại từ ai-service: xóa file của track rồi chạy với `--ai-base-url`.

## So điểm Evaluator (SC-004)

Bộ đo xuất `out/stt_samples.jsonl` cùng dạng `apps/ai-service/evals/evaluator_golden_stt.jsonl`
(`{id, stt_of, noise: ["real_stt"], answer}`). Công cụ `python -m evals.run_evaluator --stt` của AIE hiện chỉ đọc file
cố định; chờ AIE thêm tùy chọn đường dẫn (task T029).
