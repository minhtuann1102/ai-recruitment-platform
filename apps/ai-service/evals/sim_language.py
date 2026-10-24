"""Chi so ngon ngu tu cac phien gia lap: ti le van ban AI viet sai ngon ngu (cau tieng Anh tron cau / khong dau).

Do 3 nhom: cau hoi Interviewer, cac truong chu cua bao cao (ung vien doc) va y cua Evaluator (noi bo, nhung di vao
focus cau hoi va nhan xet). Chay lai tren file phien da luu, khong goi mang:
  python -m evals.sim_language plans/reports/eval-sim-*.json
"""
import json
import sys
from typing import Dict, Iterable, List

from app.language_check import english_sentences


def report_texts(report: Dict) -> List[str]:
    """Moi truong chu trong bao cao ung vien doc (diem va enum khong tinh)."""
    texts = [report.get("overall", {}).get("summary", "")]
    texts += [s["point"] for s in report.get("strengths", [])]
    texts += [x for i in report.get("improvements", []) for x in (i["point"], i.get("why", ""))]
    texts += [x for p in report.get("study_plan", []) for x in [p["topic"], *p.get("actions", [])]]
    texts += [t.get("comment", "") for t in report.get("topics", []) + report.get("turns", [])]
    return [t for t in texts if t]


def evaluator_points(turns: Iterable[Dict]) -> List[str]:
    return [p for t in turns if t.get("evaluation") for k in ("covered_points", "missing_points", "misconceptions")
            for p in t["evaluation"].get(k, [])]


def _group(texts: List[str], examples: List[str]) -> Dict:
    bad = [t for t in texts if english_sentences(t)]
    examples += [english_sentences(t)[0][:160] for t in bad[:2]]
    return {"total": len(texts), "wrong": len(bad), "rate": round(len(bad) / len(texts), 3) if texts else None}


def language(sessions: Dict[str, Dict]) -> Dict:
    questions, report, points, examples = [], [], [], {"questions": [], "report": [], "evaluator_points": []}
    per_session = {}
    for pid, s in sessions.items():
        q, r = [t["question"] for t in s["turns"]], report_texts(s["report"] or {})
        questions += q
        report += r
        points += evaluator_points(s["turns"])
        per_session[pid] = any(english_sentences(t) for t in q + r)
    out = {"questions": _group(questions, examples["questions"]), "report": _group(report, examples["report"]),
           "evaluator_points": _group(points, examples["evaluator_points"]),
           "sessions_with_wrong_language": sum(per_session.values()), "examples": examples}
    return out


def main() -> None:
    for path in sys.argv[1:]:
        data = json.load(open(path, encoding="utf-8"))
        print(path, json.dumps(language(data["sessions"]), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
