"""Lint review results against the rubric and build the Vietnamese review report.

Inputs: the batch from prepare_review_batch.py and a JSON array of result objects (references/review-rubric.md).
Outputs: a markdown report, and optionally a suggestions JSON {qa_id: result} for the review page.
Planted test pairs listed in --canary-key ({qa_id: "planted error"} or {qa_id: {"error", "keywords"}}) are scored
separately and left out of the pair tables and suggestions. --quote-check takes the output of verify_quotes.py.

Usage:
  python build_review_report.py --batch batch.json --results results.json --out report.md \
    [--suggestions suggestions.json] [--canary-key canaries-key.json] [--quote-check quote-check.json]
"""
import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from review_triage import canary_caught, canary_error, load_quote_check, quote_problems, triage

VERDICTS = {"ok": "Đạt", "fix": "Cần sửa", "drop": "Bỏ"}
TRIAGE = {"must_read": "Phải đọc", "format_only": "Chỉ hình thức", "accept": "Có thể chấp nhận"}
CONFIDENCE = {"high", "medium", "low"}
CLAIM_STATUS = {"supported", "contradicted", "outdated", "unverified"}
SEVERITY_ORDER = {"critical": 0, "major": 1, "minor": 2}
REQUIRED = ("qa_id", "verdict", "confidence", "summary_vi", "claims", "issues", "difficulty", "interview_fit",
            "junior_guide")


def lint(result):
    """Rubric violations in one result; an empty list means the result can be trusted as written."""
    problems = [f"thiếu trường `{f}`" for f in REQUIRED if f not in result]
    verdict, claims, issues = result.get("verdict"), result.get("claims") or [], result.get("issues") or []
    if verdict not in VERDICTS:
        problems.append(f"verdict không hợp lệ: {verdict!r}")
    if result.get("confidence") not in CONFIDENCE:
        problems.append(f"confidence không hợp lệ: {result.get('confidence')!r}")
    for i, claim in enumerate(claims, 1):
        status = claim.get("status")
        if status not in CLAIM_STATUS:
            problems.append(f"claim {i}: status không hợp lệ {status!r}")
        elif status != "unverified" and not (claim.get("quote", "").strip() and claim.get("source_url", "").strip()):
            problems.append(f"claim {i}: `{status}` nhưng thiếu quote hoặc source_url")
    if verdict == "ok":
        if not any(c.get("status") == "supported" and c.get("quote", "").strip() for c in claims):
            problems.append("`ok` nhưng không có claim nào được trích dẫn nguồn")
        bad = [c for c in claims if c.get("status") != "supported"]
        if bad:
            problems.append(f"`ok` nhưng {len(bad)} claim không ở trạng thái supported")
        if any(i.get("severity") in ("critical", "major") for i in issues):
            problems.append("`ok` nhưng có issue critical/major")
    if verdict in ("fix", "drop") and not issues:
        problems.append(f"`{verdict}` nhưng không có issue nào")
    if verdict == "fix" and not (result.get("proposed_fix") or {}).get("answer_change", "").strip() \
            and not (result.get("proposed_fix") or {}).get("question", "").strip():
        problems.append("`fix` nhưng thiếu proposed_fix")
    return problems


def main_issue(result):
    issues = sorted(result.get("issues") or [], key=lambda i: SEVERITY_ORDER.get(i.get("severity"), 9))
    return f"[{issues[0].get('severity')}] {issues[0].get('detail', '')}" if issues else "—"


def cell(text, limit=140):
    text = " ".join(str(text).split()).replace("|", "\\|")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def pair_section(pair, result, quote_check):
    c = pair["checks"]
    bad_quotes = set(quote_problems(result, quote_check))
    lines = [f"### {pair['qa_id']} · {VERDICTS.get(result.get('verdict'), '?')} · tin cậy {result.get('confidence')} · "
             f"{TRIAGE[triage(result, quote_check)]}",
             "", f"**Topic:** {(pair.get('topic') or {}).get('title', '?')} (`{pair['topic_id']}`) · "
             f"~{c['chunk_tokens_est']} token · hard của topic: {c['topic_hard_total']}"
             + (f" · golden: {', '.join(c['golden_labels'])}" if c["golden_labels"] else ""), "",
             f"**Câu hỏi:** {pair['question']}", "", f"**Kết luận:** {result.get('summary_vi', '')}", ""]
    if result.get("issues"):
        lines += ["| Mức | Loại | Vấn đề | Cách sửa |", "|---|---|---|---|"]
        lines += [f"| {i.get('severity')} | {i.get('type')} | {cell(i.get('detail', ''), 300)} | {cell(i.get('fix', ''), 300)} |"
                  for i in sorted(result["issues"], key=lambda i: SEVERITY_ORDER.get(i.get("severity"), 9))]
        lines.append("")
    lines.append("**Kiểm chứng:**")
    for index, claim in enumerate(result.get("claims") or []):
        warn = " **(quote không có nguyên văn trên trang nguồn)**" if index in bad_quotes else ""
        lines.append(f"- `{claim.get('status')}` {claim.get('claim', '')}{warn}")
        if claim.get("quote"):
            lines.append(f"  > {cell(claim['quote'], 320)}  ")
            lines.append(f"  > — {claim.get('source_url', '')}")
        if claim.get("note"):
            lines.append(f"  _{claim['note']}_")
    d, f, g = result.get("difficulty") or {}, result.get("interview_fit") or {}, result.get("junior_guide") or {}
    lines += ["", f"**Độ khó:** {'hard thật' if d.get('is_hard') else 'chưa đủ hard'} · hợp level "
              f"{', '.join(d.get('levels', []))} — {d.get('note', '')}",
              f"**Dùng trong phỏng vấn:** ~{f.get('minutes', '?')} phút, {f.get('sub_questions', '?')} ý hỏi, "
              f"{'chấm được' if f.get('gradeable') else 'khó chấm'} — {f.get('note', '')}", "",
              "**Hướng dẫn cho người duyệt junior**", f"- Câu này kiểm tra: {g.get('tests', '')}",
              "- Ý bắt buộc: " + "; ".join(g.get("must_have", [])),
              "- Dấu hiệu trả lời sai: " + "; ".join(g.get("red_flags", [])),
              f"- Câu hỏi nối tiếp: {g.get('follow_up', '')}"]
    fix = result.get("proposed_fix") or {}
    if fix.get("question") or fix.get("answer_change"):
        lines += ["", "**Đề xuất sửa:**"]
        if fix.get("question"):
            lines.append(f"- Câu hỏi mới: {fix['question']}")
        if fix.get("answer_change"):
            lines.append(f"- Đáp án: {fix['answer_change']}")
    return lines + [""]


def build(batch, results, canaries, quote_check=None):
    quote_check = quote_check or {}
    by_id = {r.get("qa_id"): r for r in results}
    in_batch = {p["qa_id"] for p in batch["pairs"]}
    canaries = {k: v for k, v in canaries.items() if k in in_batch}
    pairs = [p for p in batch["pairs"] if p["qa_id"] not in canaries]
    missing = [p["qa_id"] for p in batch["pairs"] if p["qa_id"] not in by_id]
    lint_rows = [(qa_id, prob) for qa_id, r in by_id.items() for prob in lint(r)]
    reviewed = [p for p in pairs if p["qa_id"] in by_id]
    verdicts = Counter(by_id[p["qa_id"]].get("verdict") for p in reviewed)
    conf = Counter(by_id[p["qa_id"]].get("confidence") for p in reviewed)
    groups = Counter(triage(by_id[p["qa_id"]], quote_check) for p in reviewed)
    quote_counts = Counter(s for qa_id in (p["qa_id"] for p in reviewed)
                           for s in quote_check.get(qa_id, {}).values())

    out = [f"# Báo cáo duyệt cặp Q&A — {batch['selection']} ({datetime.now():%Y-%m-%d %H:%M})", "",
           "> Báo cáo do Claude tạo bằng skill `interview-qa-review`: **chỉ là gợi ý kèm bằng chứng**. Các cặp này "
           "cũng do Claude viết, nên người reviewer (cùng họ model) có thể chung điểm mù. Quyết định và `reviewed_by` "
           "thuộc về người duyệt.", "",
           f"**{len(reviewed)}/{len(pairs)} cặp đã duyệt** · Đạt {verdicts['ok']} · Cần sửa {verdicts['fix']} · "
           f"Bỏ {verdicts['drop']} · tin cậy cao {conf['high']} / vừa {conf['medium']} / thấp {conf['low']}", "",
           f"**Phân loại cho người duyệt:** Phải đọc {groups['must_read']} · Chỉ hình thức {groups['format_only']} "
           f"(câu hỏi quá rộng, quá dài: nội dung đúng) · Có thể chấp nhận {groups['accept']}", ""]
    if quote_check:
        out += [f"**Kiểm tra trích dẫn nguyên văn:** khớp {quote_counts['found']} · không khớp "
                f"{quote_counts['not_found']} · không kiểm được từ máy này {quote_counts['unreadable']}", ""]
    if canaries:
        out += ["## Cặp mồi (kiểm tra người reviewer)", "", "| qa_id | Lỗi cài sẵn | Gợi ý nhận được | Bắt được? |",
                "|---|---|---|---|"]
        for qa_id, spec in canaries.items():
            r = by_id.get(qa_id, {})
            out.append(f"| {qa_id} | {cell(canary_error(spec))} | {VERDICTS.get(r.get('verdict'), 'chưa có')}: "
                       f"{cell(main_issue(r) if r else '')} | {'có' if canary_caught(r, spec) else '**KHÔNG**'} |")
        out.append("")
    if missing or lint_rows:
        out += ["## Lint (phải sạch trước khi dùng báo cáo)", ""]
        out += [f"- {qa_id}: chưa có kết quả" for qa_id in missing]
        out += [f"- {qa_id}: {prob}" for qa_id, prob in lint_rows]
        out.append("")
    out += ["## Tổng hợp", "", "| qa_id | Topic | Gợi ý | Tin cậy | Nhóm | Vấn đề chính | Token | Golden |",
            "|---|---|---|---|---|---|---|---|"]
    for p in reviewed:
        r = by_id[p["qa_id"]]
        out.append(f"| {p['qa_id']} | {cell((p.get('topic') or {}).get('title', p['topic_id']), 40)} | "
                   f"{VERDICTS.get(r.get('verdict'), '?')} | {r.get('confidence')} | {TRIAGE[triage(r, quote_check)]} | "
                   f"{cell(main_issue(r))} | {p['checks']['chunk_tokens_est']} | {len(p['checks']['golden_labels']) or ''} |")
    risky = [p for p in reviewed if by_id[p["qa_id"]].get("verdict") != "ok" and
             (p["checks"]["drop_breaks_sc001"] or p["checks"]["golden_labels"])]
    over = [p["qa_id"] for p in reviewed if p["checks"]["over_plan_budget"]]
    out += ["", "## Ảnh hưởng nếu sửa hoặc bỏ", ""]
    out += [f"- {p['qa_id']}: " + ", ".join(filter(None, [
        "bỏ thì topic còn < 2 cặp hard (SC-001)" if p["checks"]["drop_breaks_sc001"] else "",
        f"là nhãn golden set {', '.join(p['checks']['golden_labels'])} (báo Thắng nếu đổi nội dung)"
        if p["checks"]["golden_labels"] else ""])) for p in risky] or ["- Không có cặp nào vừa bị gắn cờ vừa chạm SC-001 hay golden set."]
    out += [f"- {len(over)}/{len(reviewed)} cặp dài hơn 600 token: snippet của Planner sẽ bị cắt ({', '.join(over) or '—'})."]
    by_group = {g: [p["qa_id"] for p in reviewed if triage(by_id[p["qa_id"]], quote_check) == g] for g in TRIAGE}
    golden = [p["qa_id"] for p in reviewed if p["checks"]["golden_labels"]]
    out += ["", "## Việc cho người duyệt", "",
            f"- **Phải đọc** ({len(by_group['must_read'])}): {', '.join(by_group['must_read']) or '—'}. Sai kiến thức, "
            "lỗi thời, chưa kiểm chứng được, tin cậy thấp, hoặc trích dẫn không khớp nguyên văn. Đọc phần kiểm chứng; "
            "chỗ Claude bác bỏ chính nguồn mà cặp trích thì Claude cũng có thể sai.",
            f"- **Chỉ hình thức** ({len(by_group['format_only'])}): {', '.join(by_group['format_only']) or '—'}. "
            "Nội dung đúng; vấn đề là câu hỏi quá rộng hoặc quá dài. Sửa hay giữ là lựa chọn của bạn.",
            f"- **Có thể chấp nhận** ({len(by_group['accept'])}): {', '.join(by_group['accept']) or '—'}. Mọi ý đã có "
            "trích dẫn; chấp nhận dựa trên bằng chứng là quyết định của bạn.",
            f"- Có nhãn golden set ({len(golden)}): {', '.join(golden) or '—'}. Sửa câu hỏi thì giữ các thuật ngữ chính.",
            "", "## Chi tiết từng cặp", ""]
    for p in reviewed:
        out += pair_section(p, by_id[p["qa_id"]], quote_check)
    return "\n".join(out), {p["qa_id"]: by_id[p["qa_id"]] for p in reviewed}, lint_rows, missing


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--results", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--suggestions")
    parser.add_argument("--canary-key")
    parser.add_argument("--quote-check", help="output of verify_quotes.py")
    args = parser.parse_args()

    batch = json.loads(Path(args.batch).read_text(encoding="utf-8"))
    results = json.loads(Path(args.results).read_text(encoding="utf-8"))
    canaries = json.loads(Path(args.canary_key).read_text(encoding="utf-8")) if args.canary_key else {}
    report, suggestions, lint_rows, missing = build(batch, results, canaries, load_quote_check(args.quote_check))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(report + "\n", encoding="utf-8")
    if args.suggestions:
        Path(args.suggestions).write_text(json.dumps(suggestions, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"report -> {args.out}; {len(suggestions)} suggestions; lint problems: {len(lint_rows)}; missing: {len(missing)}")
    return 1 if lint_rows or missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
