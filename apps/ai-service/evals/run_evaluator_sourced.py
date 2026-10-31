"""Golden co tai lieu (Phase 05, buoc 5): Evaluator v4+ co gan dung `support` khi tai lieu ung ho, noi nguoc, hay khong
lien quan den cau tra loi? 20 mau tu viet (evals/evaluator_golden_sourced.jsonl): 10 `supported`, 6 `contradicted`
(3 qua dap an chuan R, 3 chi qua snippet S), 4 `no_source` (tai lieu cung chu de nhung khong noi y do). Nhan la y do
cua nguoi viet mau, khong phai nhan nguoi cham doc lap.

Nhan quan sat cua mot lan chay lay tu output LLM truoc hau kiem (`evaluate_with_raw`), vi postcheck bo y
`contradicted` khoi `covered`: co y contradicted voi id hop le -> `contradicted`; con lai co y supported -> `supported`;
khong thi `no_source`.
  cd apps/ai-service && python -m evals.run_evaluator_sourced --runs 3 [--prompt v5] [--out report.json]
"""
import argparse
import asyncio
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from app.agents.evaluator import EvaluationInput, LlmEvaluator
from app.evaluator_source_checks import REFERENCE_ID, source_blocks
from app.llm.gateway import get_gateway
from app.llm.usage import UsageCollector
from app.models_interview import PlanTopic
from evals.label_sheet import load_golden
from evals.run_evaluator import REPORTS

GOLDEN = Path(__file__).with_name("evaluator_golden_sourced.jsonl")
LABELS = ("supported", "contradicted", "no_source")


def to_input(s: dict) -> EvaluationInput:
    topic = PlanTopic(id=s["qid"], title=s["topic"]["title"], source="catalog", objective=s["topic"]["objective"],
                      key_points=s["topic"]["key_points"], start_difficulty=2, opening_hint="-", backup_question="-",
                      reference_snippets=list(s["documents"]))
    return EvaluationInput(level=s["level"], phase=s["phase"], topic=topic, difficulty=2, turn_kind=s["turn_kind"],
                           turn_number=1, question=s["question"], answer=s["answer"],
                           reference_answer=s.get("reference_answer", ""))


def observed(points: List[dict], valid_ids: List[str]) -> str:
    """Nhan cua lan chay tu cac y covered tho; id khong co trong luot bo qua (nhu check_sources)."""
    labels = {p["support"] for p in points if any(i.strip().upper() in valid_ids for i in p.get("source_ids", []))}
    return "contradicted" if "contradicted" in labels else "supported" if "supported" in labels else "no_source"


async def run_all(samples: List[dict], runs: int, prompt: Optional[str], collector: UsageCollector,
                  concurrency: int = 4) -> Dict[str, List[dict]]:
    evaluator, sem = LlmEvaluator(get_gateway(), prompt_version=prompt), asyncio.Semaphore(concurrency)

    async def one(s: dict) -> dict:
        async with sem:
            raw, ev = await evaluator.evaluate_with_raw(to_input(s), collector)
        points = [c.model_dump() for c in raw.covered] if raw else []
        valid = [i for i, _ in source_blocks(s["documents"], s.get("reference_answer", ""))]
        return {"observed": observed(points, valid), "points": points, "degraded": ev.degraded,
                "invalid_ids": sum(i.strip().upper() not in valid for p in points for i in p.get("source_ids", [])),
                "technical_accuracy": ev.scores.technical_accuracy, "misconceptions": len(ev.misconceptions)}

    results: Dict[str, List[dict]] = {s["id"]: [] for s in samples}
    for r in range(runs):
        for s, out in zip(samples, await asyncio.gather(*(one(s) for s in samples))):
            results[s["id"]].append(out)
        print(f"lan chay {r + 1}/{runs} xong", file=sys.stderr)
    return results


def summarize(samples: List[dict], results: Dict[str, List[dict]]) -> dict:
    """Precision / recall tung nhan tren moi (mau, lan chay) khong degraded; `contradicted` tach theo R / chi S."""
    pairs = [(s["expect"]["support"], r["observed"], s) for s in samples for r in results[s["id"]] if not r["degraded"]]
    matrix = Counter((e, o) for e, o, _ in pairs)
    per_label = {}
    for lab in LABELS:
        tp = matrix[(lab, lab)]
        pred, truth = sum(v for (_, o), v in matrix.items() if o == lab), sum(v for (e, _), v in matrix.items() if e == lab)
        per_label[lab] = {"precision": round(tp / pred, 3) if pred else None, "recall": round(tp / truth, 3) if truth else None,
                          "n": truth}
    contra = [(o, s) for e, o, s in pairs if e == "contradicted"]
    by_doc = {"R": [o == "contradicted" for o, s in contra if s.get("reference_answer")],
              "S": [o == "contradicted" for o, s in contra if not s.get("reference_answer")]}
    runs_contra = [r for s in samples if s["expect"]["support"] == "contradicted" for r in results[s["id"]]
                   if not r["degraded"]]
    return {"samples": len(samples), "runs": max((len(v) for v in results.values()), default=0),
            "degraded_runs_excluded": sum(r["degraded"] for v in results.values() for r in v),
            "confusion_expected_observed": {f"{e}->{o}": n for (e, o), n in sorted(matrix.items())},
            "per_label": per_label,
            "contradicted_recall_by_doc": {k: round(sum(v) / len(v), 3) if v else None for k, v in by_doc.items()},
            # cau tra loi sai: diem technical_accuracy va misconception co phan anh khong (postcheck chi chan khi R bac bo)
            "wrong_answer_technical_accuracy_mean": round(sum(r["technical_accuracy"] for r in runs_contra)
                                                          / len(runs_contra), 2) if runs_contra else None,
            "wrong_answer_with_misconception": round(sum(r["misconceptions"] > 0 for r in runs_contra)
                                                     / len(runs_contra), 3) if runs_contra else None,
            "invalid_source_ids": sum(r["invalid_ids"] for v in results.values() for r in v),
            "by_sample": {sid: Counter(r["observed"] for r in v) for sid, v in results.items()}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--prompt", default=None, help="vd v5; mac dinh ban moi nhat")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    samples, collector = load_golden(GOLDEN), UsageCollector()
    results = asyncio.run(run_all(samples, args.runs, args.prompt, collector))
    summary = {**summarize(samples, results), "usage": collector.to_metadata()["usage"]}
    print(json.dumps({k: v for k, v in summary.items() if k != "by_sample"}, ensure_ascii=False, indent=1))
    out = args.out or REPORTS / f"eval-evaluator-sourced-{datetime.now():%y%m%d-%H%M}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=1), "utf-8")
    print(f"Da ghi {out}")


if __name__ == "__main__":
    main()
