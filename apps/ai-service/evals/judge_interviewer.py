"""LLM-as-judge cho cau hoi Interviewer (Q5, context/quality-criteria.md): level_fit, natural 1-5, action_ok,
single_question, leaks. Chi dung lam so do sau khi hieu chinh voi nhan nguoi (evals/question_labels/): dong y
level_fit >= 0.7, natural lech <= 1 >= 0.8. Judge cung ho model voi agent nen co the thien vi.
  python -m evals.judge_interviewer                      # bo 60 cau (evals/question_golden.jsonl) + do dong y neu co nhan
  python -m evals.judge_interviewer --run ../../plans/reports/eval-sim-bank-after2.json   # moi cau trong mot lan chay
"""
import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Dict, List, Literal

from pydantic import BaseModel

from app.llm.gateway import get_gateway
from app.prompts.store import PromptStore
from evals.question_set import items_from_sessions, load, load_labels

PROMPTS = PromptStore(Path(__file__).with_name("prompts"))
REPORTS = Path(__file__).resolve().parents[3] / "plans" / "reports"
FIELDS = ("level", "phase", "action", "difficulty", "topic", "key_points", "prev_question", "prev_answer", "question")


class JudgeOutput(BaseModel):
    level_fit: Literal["too_easy", "ok", "too_hard"]
    natural: int
    action_ok: bool
    single_question: bool
    leaks: bool
    reason: str


async def judge_items(items: List[dict], gateway=None, concurrency: int = 6) -> Dict[str, dict]:
    gateway, prompt, sem = gateway or get_gateway(), PROMPTS.get("judge_interviewer"), asyncio.Semaphore(concurrency)

    async def one(item):
        msgs = [{"role": "system", "content": prompt.text},
                {"role": "user", "content": json.dumps({k: item.get(k) for k in FIELDS}, ensure_ascii=False)}]
        async with sem:
            out = (await gateway.complete("judge", msgs, JudgeOutput, prompt_version=prompt.version)).data
        return item["id"], {**out.model_dump(), "natural": min(5, max(1, out.natural))}

    return dict(await asyncio.gather(*(one(i) for i in items)))


def summarize(results: Dict[str, dict], items: List[dict]) -> Dict:
    def block(ids):
        rs = [results[i] for i in ids if i in results]
        if not rs:
            return None
        return {"n": len(rs), "level_fit": {k: round(sum(r["level_fit"] == k for r in rs) / len(rs), 3)
                                            for k in ("too_easy", "ok", "too_hard")},
                "natural_mean": round(mean(r["natural"] for r in rs), 2),
                "action_ok": round(sum(r["action_ok"] for r in rs) / len(rs), 3),
                "single_question": round(sum(r["single_question"] for r in rs) / len(rs), 3),
                "leaks": round(sum(r["leaks"] for r in rs) / len(rs), 3)}
    by = lambda key: {v: block([i["id"] for i in items if i[key] == v]) for v in sorted({i[key] for i in items})}  # noqa: E731
    return {"all": block([i["id"] for i in items]), "by_level": by("level"), "by_action": by("action"),
            "by_source": by("question_source")}


def agreement(a: Dict[str, dict], b: Dict[str, dict]) -> Dict:
    """Dong y giua hai bo nhan (judge-nguoi hoac nguoi-nguoi) tren cac id chung."""
    ids = sorted(set(a) & set(b))
    if not ids:
        return {"n": 0}
    rate = lambda f: round(sum(f(a[i], b[i]) for i in ids) / len(ids), 3)  # noqa: E731
    return {"n": len(ids), "level_fit": rate(lambda x, y: x["level_fit"] == y["level_fit"]),
            "natural_within_1": rate(lambda x, y: abs(x["natural"] - y["natural"]) <= 1),
            "action_ok": rate(lambda x, y: x["action_ok"] == y["action_ok"])}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, help="file phien gia lap; mac dinh: bo 60 cau evals/question_golden.jsonl")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    items = items_from_sessions(json.loads(args.run.read_text("utf-8"))["sessions"]) if args.run else load()
    results = asyncio.run(judge_items(items))
    report = {"source": str(args.run or "question_golden"), "summary": summarize(results, items)}
    if not args.run:
        labels = load_labels()
        report["agreement_judge_vs_rater"] = {r: agreement(results, lab) for r, lab in labels.items()}
        names = sorted(labels)
        if len(names) >= 2:
            report["agreement_rater_vs_rater"] = agreement(labels[names[0]], labels[names[1]])
    print(json.dumps(report, ensure_ascii=False, indent=1))
    out = args.out or REPORTS / f"judge-interviewer-{datetime.now():%y%m%d-%H%M}.json"
    out.write_text(json.dumps({**report, "results": results}, ensure_ascii=False, indent=1), "utf-8")
    print(f"Da ghi {out}")


if __name__ == "__main__":
    main()
