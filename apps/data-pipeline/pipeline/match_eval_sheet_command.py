"""match-eval-sheet (spec 017 US3, contracts/pipeline-cli-match.md): bang soat de gan nhan CV x JD + so tap cap voi labels.json.

Moi CV goi endpoint voi job_ids = pool de lay DUNG tap JD qua loc cung (dung chung bo loc, khong chep logic). Bang soat chi
dung du lieu goc (cvs.json, jd_normalized.jsonl): KHONG co diem, thu hang, matched / missing hay bat ky truong nao cua scorer;
JD xep ngau nhien theo seed co dinh tren danh sach job_id da sap xep nen khong phu thuoc thu tu response. Kem labels.template.json
va pair-set-check.json (tap cap cua endpoint so voi khoa cua labels.json: equal / missing / extra, de dong T036).
Ma thoat: 0 xong (ke ca khi tap cap lech: chi in va ghi); 1 thieu file hoac CV khong co JD nao qua loc; 2 khong goi duoc ai-service.
"""
import argparse
import json
import random
import sys
from pathlib import Path
from typing import Dict, List

from .match_eval_client import AiServiceError, MatchClient, build_request, require_complete_page
from .match_eval_data import EvalData, EvalDataError, compare_pair_sets, load_eval_data, load_pool_jds
from .settings import JD_NORMALIZED_PATH, MATCH_EVAL_RUN_DIR, MATCH_EVAL_SEEDS_DIR, ConfigError, require_match_eval_settings

EXIT_OK, EXIT_INPUT_ERROR, EXIT_SERVICE = 0, 1, 2
SEEDS_DIR = MATCH_EVAL_SEEDS_DIR  # test tro sang tmp_path
SHEET_SEED = "match-eval-sheet"
PAGE_SIZE = 50
JD_SECTIONS = (("description", "Mô tả"), ("responsibilities", "Công việc"), ("requirements", "Yêu cầu"))  # khong lay quyen loi


def shuffled_ids(cv_id: str, jd_ids: List[str]) -> List[str]:
    """Thu tu co dinh cho tung CV: sap xep truoc roi tron bang seed chuoi (khong phu thuoc PYTHONHASHSEED)."""
    ordered = sorted(jd_ids)
    random.Random(f"{SHEET_SEED}:{cv_id}").shuffle(ordered)
    return ordered


def _cv_lines(cv: Dict) -> List[str]:
    profile = cv["cv_profile"]
    years = profile.get("total_years_experience")
    lines = [f"- Hồ sơ: {profile.get('headline')}",
             f"- Track: {cv['track']}; level: {cv['level']}" + (f"; kinh nghiệm: {years} năm" if years is not None else ""),
             f"- Ghi chú: {cv.get('note')}", "- Kỹ năng: " + ", ".join(str(s.get("name")) for s in profile.get("skills") or [])]
    for title, key, name in (("Kinh nghiệm", "experiences", "role"), ("Dự án", "projects", "name")):
        entries = profile.get(key) or []
        lines += [f"- {title}:"] if entries else []
        for e in entries:
            period = f" ({e.get('start')} – {e.get('end') or 'nay'})" if key == "experiences" else ""
            lines.append(f"  - {e.get(name)}{period}: {e.get('summary')} [công nghệ: {', '.join(e.get('tech') or [])}]")
    lines += [f"- Học vấn: {e.get('degree')} ({e.get('year')})" for e in profile.get("education") or []]
    return lines


def _jd_lines(jd: Dict) -> List[str]:
    lines = [f"### {jd['jd_id']} — {jd.get('title')}", "", f"- Cấp bậc: {jd.get('level') or 'không ghi'}; kỹ năng: {', '.join(jd.get('skills') or [])}",
             "- Nhãn (0 / 1 / 2): ", ""]
    sections = jd.get("sections") or {}
    for key, title in JD_SECTIONS:
        if str(sections.get(key) or "").strip():
            lines += [f"**{title}**", "", str(sections[key]).strip(), ""]
    return lines


def render_sheet(data: EvalData, filtered: Dict[str, List[str]], jds: Dict[str, Dict]) -> str:
    lines = ["# Bảng soát nhãn CV × JD (spec 017, US3)", "",
             f"As-of {data.as_of}. Gán nhãn 0 (không) / 1 (một phần) / 2 (phù hợp) theo `specs/017-cv-jd-matching/label-rubric.md`, "
             "trước khi xem kết quả của hệ thống. Bảng không có điểm; JD của mỗi CV xếp ngẫu nhiên theo seed cố định.", ""]
    for cv in data.cvs:
        lines += [f"## CV {cv['cv_id']}", "", *_cv_lines(cv), ""]
        for jd_id in shuffled_ids(cv["cv_id"], filtered[cv["cv_id"]]):
            lines += _jd_lines(jds[jd_id])
    return "\n".join(lines)


def _pair_check(data: EvalData, filtered: Dict[str, List[str]]) -> Dict:
    if data.labels is None:
        return {"equal": None, "filtered_pairs": sum(len(v) for v in filtered.values()),
                "note": "chua co labels.json: chua so duoc tap cap qua loc voi tap cap co nhan"}
    return compare_pair_sets(filtered, data.labels).to_dict()


def run_match_eval_sheet(args: argparse.Namespace) -> int:
    out_dir = Path(args.out)
    try:
        data = load_eval_data(SEEDS_DIR, require_labels=False)
        jds = load_pool_jds(JD_NORMALIZED_PATH, data.jd_ids)
    except EvalDataError as exc:
        print(f"loi: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    try:
        client = MatchClient(require_match_eval_settings())
        filtered: Dict[str, List[str]] = {}
        mock_seen = False
        for cv in data.cvs:
            body = client.match(build_request(cv, data.as_of, data.jd_ids, PAGE_SIZE)).body
            require_complete_page(cv["cv_id"], body)
            filtered[cv["cv_id"]] = [i["job_id"] for i in body["items"] if i["job_id"] in jds]
            mock_seen = mock_seen or bool(body["metadata"].get("mock"))
    except ConfigError as exc:
        print(f"loi cau hinh: {exc}", file=sys.stderr)
        return EXIT_SERVICE
    except AiServiceError as exc:
        print(f"loi ai-service: {exc}", file=sys.stderr)
        return EXIT_SERVICE
    empty = [cv_id for cv_id, ids in filtered.items() if not ids]
    if empty:
        hint = " ai-service dang o che do mock (chi muc mau): can che do that voi chi muc ai_db." if mock_seen else ""
        print(f"loi: CV khong co JD nao qua loc cung trong pool: {', '.join(empty)}.{hint}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    check = _pair_check(data, filtered)
    out_dir.mkdir(parents=True, exist_ok=True)
    sheet = out_dir / f"sheet-{data.as_of}.md"
    sheet.write_text(render_sheet(data, filtered, jds), encoding="utf-8")
    template = {"labeled_by": "", "labeled_at": "", "method": "", "labels": {cv: {jd: None for jd in sorted(ids)} for cv, ids in filtered.items()}}
    (out_dir / "labels.template.json").write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "pair-set-check.json").write_text(json.dumps(check, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ghi {sheet} ({sum(len(v) for v in filtered.values())} cap, {len(filtered)} CV)")
    if check["equal"] is None:
        print(f"pair set: {check['note']}")
    elif check["equal"]:
        print(f"pair set: equal ({check['filtered_pairs']} cap qua loc = {check['labeled_pairs']} cap co nhan)")
    else:
        print(f"pair set: NOT equal - missing {len(check['missing'])}, extra {len(check['extra'])} (xem pair-set-check.json)")
    return EXIT_OK


def add_parser(sub) -> None:
    parser = sub.add_parser("match-eval-sheet", help="bang soat markdown de gan nhan CV x JD (khong co diem) + so tap cap qua loc voi labels.json (spec 017)")
    parser.add_argument("--out", default=str(MATCH_EVAL_RUN_DIR), metavar="DIR", help="thu muc ghi sheet-*.md, labels.template.json, pair-set-check.json")
