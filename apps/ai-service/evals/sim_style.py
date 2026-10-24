"""Chi so van phong cau hoi Interviewer (context/quality-criteria.md): do bang code, khong goi mang, chay moi lan harness.

Nguong: khuon "Ban co the ... khong?" <= 40%; trung binh <= 25 tu; khong cau mo dau (3 tu dau) nao > 15%.
Chay lai tren file phien da luu: python -m evals.sim_style plans/reports/eval-sim-*.json
"""
import json
import re
import sys
from collections import Counter
from statistics import mean
from typing import Dict, List

from app.mock_evaluator import fold

TEMPLATE = re.compile(r"\bban co the\b.*\bkhong\b\s*\??\s*$")  # "Ban co the ... (duoc) khong?" o cuoi cau hoi
ECHO = re.compile(r"\bban (da|vua) (neu|noi|chia se|de cap|nhac)")
LIMITS = {"template_rate": 0.40, "mean_words": 25, "top_opener_share": 0.15}


def opener(question: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", fold(question))[:3])


def style(questions: List[str]) -> Dict:
    if not questions:
        return {"questions": 0}
    folded = [fold(q).strip() for q in questions]
    words = [len(q.split()) for q in questions]
    openers = Counter(opener(q) for q in questions)
    top, top_n = openers.most_common(1)[0]
    out = {"questions": len(questions),
           "template_rate": round(sum(bool(TEMPLATE.search(q)) for q in folded) / len(questions), 3),
           "echo_rate": round(sum(bool(ECHO.search(q)) for q in folded) / len(questions), 3),
           "mean_words": round(mean(words), 1), "p90_words": sorted(words)[int(0.9 * (len(words) - 1))],
           "top_opener": top, "top_opener_share": round(top_n / len(questions), 3)}
    out["within_limits"] = {k: out[k] <= v for k, v in LIMITS.items()}
    return out


def session_style(sessions: Dict[str, Dict]) -> Dict:
    return style([t["question"] for s in sessions.values() for t in s["turns"]])


def main() -> None:
    for path in sys.argv[1:]:
        print(path, json.dumps(session_style(json.load(open(path, encoding="utf-8"))["sessions"]),
                               ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
