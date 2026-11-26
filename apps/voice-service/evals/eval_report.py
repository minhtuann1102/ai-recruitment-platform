"""Bao cao markdown cua bo do voice (spec 015 T027/T028), ghi vao specs/015-voice-mode/eval-results.md.

Rieng tu: clip `free` la loi noi tu do cua nguoi that -> bao cao chi co chi so, ban ghi nam o evals/out/ (gitignore).
Clip `read` doc van ban golden nen chi ghi ty le loi, khong chep ban ghi.
"""
from typing import Dict, List

from .eval_stats import TERM_TARGET, TTS_FIRST_BYTE_TARGET_S, fmt, pct


def _passed(flag) -> str:
    return "–" if flag is None else ("đạt" if flag else "không đạt")


def _recognition(data: Dict) -> List[str]:
    lines = ["## SC-002: thuật ngữ và lỗi âm tiết (clip `read`)", "",
             "| Chế độ | Clip | Lỗi âm tiết gộp | TB từng clip | Trung vị | Thuật ngữ đúng | Tỷ lệ |",
             "|---|---|---|---|---|---|---|"]
    for key, label in (("kw", "có keywords (mọi clip)"), ("kw_pair", "có keywords (cặp)"),
                       ("nokw_pair", "không keywords (cặp)")):
        s = data["recognition"][key]
        lines.append(f"| {label} | {s['clips']} | {pct(s['ser_pooled'])} | {pct(s['ser_mean'])} | {pct(s['ser_median'])} | "
                     f"{s['terms_found']}/{s['terms_total']} | {pct(s['term_rate'])} |")
    rate = data["recognition"]["kw"]["term_rate"]
    lines += ["", f"Mục tiêu ≥ {TERM_TARGET:.0%} thuật ngữ đúng khi có keywords (dòng mọi clip): "
              f"**{_passed(None if rate is None else rate >= TERM_TARGET)}**. Hai dòng cặp chỉ gồm clip mà cả hai chế "
              "độ đều nhận được bản ghi, để so mức cải thiện của keywords.", ""]
    sent = ", ".join(f"{t} {n}" for t, n in sorted(data["keywords_sent"].items()))
    lines += [f"Keywords: gửi đủ danh sách của track như bên gọi thật ({sent} cụm); service cắt theo "
              "`VOICE_MAX_KEYWORDS` (mặc định 100), phần sau không tới nhà cung cấp. Thuật ngữ được chấm theo cả danh "
              "sách (không chỉ phần đã gửi).", ""]
    return lines


def _latency(data: Dict) -> List[str]:
    lines = ["## SC-001: thời gian nhận bản ghi", "",
             "Độ dài câu ước lượng bằng mốc cuối đoạn nói service trả về (không có ffprobe để đọc độ dài file); "
             "thời gian đo phía bên gọi, gồm cả mạng tới service. Chỉ tính lượt có keywords (bên gọi thật luôn gửi).",
             f"Lượt có keywords lỗi (không có độ dài): {data['kw_failures']}"
             + ("; có lượt lỗi nên không kết luận đạt / không đạt." if data["kw_failures"] else "."), "",
             "| Độ dài câu | Lượt | p50 (s) | p95 (s) | Ngưỡng p95 (s) | Kết quả |", "|---|---|---|---|---|---|"]
    for row in data["latency"]:
        lines.append(f"| {row['bucket']} | {row['n']} | {fmt(row['p50'])} | {fmt(row['p95'])} | "
                     f"{fmt(row['target'], 0)} | {_passed(row['passed'])} |")
    return lines + [""]


def _tts(data: Dict) -> List[str]:
    t = data["tts"]
    if t is None:
        return ["## SC-003: thời gian tới tiếng đầu (TTS)", "", "Không chạy (`--skip-tts`).", ""]
    passed = None if t["p95"] is None else t["p95"] <= TTS_FIRST_BYTE_TARGET_S
    return ["## SC-003: thời gian tới tiếng đầu (TTS)", "",
            f"{t['n']} câu hỏi golden ≤ 300 ký tự (1 lượt khởi động không tính), lỗi {t['errors']}.", "",
            "| p50 byte đầu (s) | p95 byte đầu (s) | p50 trọn câu (s) | Ngưỡng p95 (s) | Kết quả |", "|---|---|---|---|---|",
            f"| {fmt(t['p50'])} | {fmt(t['p95'])} | {fmt(t['total_p50'])} | {TTS_FIRST_BYTE_TARGET_S} | {_passed(passed)} |", ""]


def _free(data: Dict) -> List[str]:
    lines = ["## Chỉ số trình bày (clip `free`, chỉ số, không có bản ghi)", "",
             "| Clip | Người | Track | Có tiếng (s) | Âm tiết/phút | Quãng ngừng dài | Tỷ lệ từ đệm | Cảnh báo |",
             "|---|---|---|---|---|---|---|---|"]
    for r in data["free"]:
        m = r["metrics"] or {}
        lines.append(f"| {r['clip_id']} | {r['speaker']} | {r['track']} | {fmt(m.get('speech_time_s'), 1)} | "
                     f"{fmt(m.get('speech_rate_spm'), 0)} | {m.get('long_pause_count', '–')} | "
                     f"{fmt(m.get('filler_ratio'), 3)} | {', '.join(r['warnings']) or '–'} |")
    return lines + [""]


def _credit(data: Dict) -> List[str]:
    c, s = data["credit"], data["credit"]["session"]
    return ["## SC-007: credit", "",
            f"- Lượt đo này: ~{fmt(c['stt_seconds'] / 60, 1)} phút audio gửi STT (ước lượng theo mốc cuối đoạn nói, "
            f"cả hai chế độ) → ~{fmt(c['stt_credit'], 1)} credit STT; TTS, VAD và lượt lỗi (đã tới nhà cung cấp "
            "nhưng không có độ dài) chưa tính.",
            f"- Một phiên {s['session_min']} phút (giả định trong `evals/pricing.json`): STT ~{fmt(s['stt'], 1)} + "
            f"TTS ~{fmt(s['tts'], 1)} = **~{fmt(s['total'], 1)} credit**.", ""]


def _details(data: Dict) -> List[str]:
    lines = ["## Chi tiết clip `read`", "",
             "| Clip | Người | Track | Tier | Độ dài ~ (s) | Lỗi âm tiết (kw / không) | Thuật ngữ (kw / không) | "
             "Nhận bản ghi kw (s) |", "|---|---|---|---|---|---|---|---|"]
    for r in data["read_rows"]:
        lines.append(f"| {r['clip_id']} | {r['speaker']} | {r['track']} | {r['tier']} | {fmt(r['duration'], 1)} | "
                     f"{pct(r['ser_kw'])} / {pct(r['ser_nokw'])} | {r['terms_kw']} / {r['terms_nokw']} | "
                     f"{fmt(r['elapsed_kw'])} |")
    lines.append("")
    if data["errors"]:
        lines += ["## Lỗi", ""] + [f"- {clip} ({mode}): `{code}`" for clip, mode, code in data["errors"]] + [""]
    return lines


def build_report(data: Dict) -> str:
    missing = ", ".join(data["missing"]) or "không"
    head = ["# Kết quả bộ đo voice (spec 015 US4)", "",
            f"Chạy {data['date']}, model STT `{data['stt_model'] or '?'}`, lệnh `python -m evals.run_voice_eval`. "
            f"Clip có file: {data['clips_found']}/{data['clips_total']} (thiếu: {missing}); đã đo {data['clips_measured']} "
            f"clip; {data['speakers']} người ghi, mã ẩn danh.", "",
            "**Giới hạn:** clip `read` là đọc thành tiếng văn bản mẫu, không phải trả lời thật (ít ngập ngừng, đúng "
            "thuật ngữ hơn); số mẫu nhỏ nên p95 gần như giá trị lớn nhất. Thuật ngữ = token của bản chuẩn có trong danh "
            "sách của track (research R10): danh sách có cả token chung (`i`/`o` từ I/O, `test`, `key`, `set`, `model`) "
            "nên tỷ lệ hơi lạc quan; ngược lại cụm dính liền (`Promise.all` → `promiseall`) bị tính sai khi STT tách "
            "từ.", ""]
    sc004 = ["## SC-004: chênh điểm Evaluator", "",
             "Chờ AIE thêm tùy chọn đường dẫn cho `run_evaluator --stt` (T029). Mẫu đã xuất: "
             "`apps/voice-service/evals/out/stt_samples.jsonl` (bản STT có keywords của các clip `read`).", ""]
    return "\n".join(head + _recognition(data) + _latency(data) + _tts(data) + _free(data) + _credit(data)
                     + _details(data) + sc004)
