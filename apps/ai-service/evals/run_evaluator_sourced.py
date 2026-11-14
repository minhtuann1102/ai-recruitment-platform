"""Golden co tai lieu (Phase 05, buoc 5): Evaluator v4+ co gan dung `support` khi tai lieu ung ho, noi nguoc, hay khong
lien quan den cau tra loi? 47 mau tu viet (evals/evaluator_golden_sourced.jsonl): 25 `supported`, 10 `contradicted`
(4 qua dap an chuan R, 6 chi qua snippet S), 12 `no_source` (tai lieu cung chu de nhung khong noi y do; 3 mau co R).
Nhom `short` (32 mau, g1-g32): tai lieu ngan, doc ~250 ky tu nen lo loi qua chat, recall o day lac quan.
Nhom `long_s` (15 mau, g33-g47): luot khong co R, 2-5 tai lieu ~900 ky tu nhieu y, cau can cu nam giua chunk, tra loi co
y phu va `topic_turns`; moi so sanh recall tai lieu phai doc nhom nay. Tai lieu van tu viet theo hinh dang chunk that:
chunk that chua chot giay phep, repo public, khong commit (xem support_set.py). So sanh `long_s` dung >= 5 lan chay.
Nhan la y do cua nguoi viet mau, khong phai nhan nguoi cham doc lap.

Nhan quan sat cua mot lan chay lay tu output LLM truoc hau kiem (`evaluate_with_raw`), vi postcheck bo y
`contradicted` khoi `covered`: co y contradicted voi id hop le -> `contradicted`; con lai co y supported -> `supported`;
khong thi `no_source`. `r_blocked` lay tu Evaluation sau hau kiem: R bi trich la bac bo va con misconception nen luat 4
da chan diem, do ca hai chieu vi bac nham cau dung con hai hon bo sot cau sai.
  cd apps/ai-service && python -m evals.run_evaluator_sourced --runs 3 [--prompt v5] [--lookup] [--out report.json]
--lookup: mau khong co R duoc tra cuu them (nhu EVALUATOR_TOOLS=true); id sai (`invalid_source_ids`) khong duoc tang.
"""
import argparse
import asyncio
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from app.agents.evaluator import EvaluationInput, LlmEvaluator, TopicTurn
from app.evaluator_source_checks import REFERENCE_ID, source_blocks
from app.llm.gateway import get_gateway
from app.llm.usage import UsageCollector
from app.models_interview import Evaluation, PlanTopic, SourceRef
from evals.label_sheet import load_golden
from evals.policy_context_support import apply_policy_context
from evals.lookup_support import attach_lookup, load_lookup_retriever, lookup_fields, lookup_summary
from evals.run_evaluator import REPORTS

GOLDEN = Path(__file__).with_name("evaluator_golden_sourced.jsonl")
LABELS = ("supported", "contradicted", "no_source")
COHORTS = ("short", "long_s")


def to_input(s: dict) -> EvaluationInput:
    topic = PlanTopic(id=s["qid"], title=s["topic"]["title"], source="catalog", objective=s["topic"]["objective"],
                      key_points=s["topic"]["key_points"], start_difficulty=2, opening_hint="-", backup_question="-",
                      reference_snippets=list(s["documents"]))
    reference = s.get("reference_answer", "")
    return EvaluationInput(level=s["level"], phase=s["phase"], topic=topic, difficulty=2, turn_kind=s["turn_kind"],
                           turn_number=1, question=s["question"], answer=s["answer"],
                           topic_turns=[TopicTurn(q=t["q"], a=t["a"]) for t in s.get("topic_turns", [])],
                           reference_answer=reference,
                           reference_source=SourceRef(ref=s["id"], title=s["question"]) if reference else None)


def observed(points: List[dict], valid_ids: List[str]) -> str:
    """Nhan cua lan chay tu cac y covered tho; id khong co trong luot bo qua (nhu check_sources)."""
    labels = {p["support"] for p in points if any(i.strip().upper() in valid_ids for i in p.get("source_ids", []))}
    return "contradicted" if "contradicted" in labels else "supported" if "supported" in labels else "no_source"


def blocked_by_reference(ev: Evaluation) -> bool:
    return bool(ev.misconceptions) and any(c.id == REFERENCE_ID and c.support == "contradicted" for c in ev.sources)


async def run_all(samples: List[dict], runs: int, prompt: Optional[str], collector: UsageCollector,
                  concurrency: int = 4, lookup: bool = False, policy_context: str = "none") -> Dict[str, List[dict]]:
    evaluator, sem = LlmEvaluator(get_gateway(), prompt_version=prompt), asyncio.Semaphore(concurrency)
    retriever = await load_lookup_retriever() if lookup else None

    async def one(s: dict) -> dict:
        inp = apply_policy_context(to_input(s), policy_context)
        tool = attach_lookup(retriever, s, inp)
        async with sem:
            raw, ev = await evaluator.evaluate_with_raw(inp, collector)
        points = [c.model_dump() for c in raw.covered] if raw else []
        # id hop le gom ca chunk cong cu (S{n+1}..) khi vong lap da chot
        extended = tool.extend(inp) if tool is not None and tool.committed else inp
        valid = [i for i, _ in source_blocks([*extended.topic.reference_snippets, *extended.turn_snippets],
                                             s.get("reference_answer", ""))]
        return {"observed": observed(points, valid), "points": points, "degraded": ev.degraded,
                "invalid_ids": sum(i.strip().upper() not in valid for p in points for i in p.get("source_ids", [])),
                "r_blocked": blocked_by_reference(ev),
                "technical_accuracy": ev.scores.technical_accuracy, "misconceptions": len(ev.misconceptions),
                **lookup_fields(tool)}

    results: Dict[str, List[dict]] = {s["id"]: [] for s in samples}
    for r in range(runs):
        for s, out in zip(samples, await asyncio.gather(*(one(s) for s in samples))):
            results[s["id"]].append(out)
        print(f"lan chay {r + 1}/{runs} xong", file=sys.stderr)
    return results


def with_reference(samples: List[dict], results: Dict[str, List[dict]], correct: bool) -> List[dict]:
    """Cac lan chay khong degraded cua mau co R; correct: cau tra loi dung (ky vong khac `contradicted`)."""
    return [r for s in samples if s.get("reference_answer") and (s["expect"]["support"] != "contradicted") == correct
            for r in results[s["id"]] if not r["degraded"]]


def share(runs: List[dict], key: str) -> Optional[float]:
    return round(sum(bool(r[key]) for r in runs) / len(runs), 3) if runs else None


def label_stats(matrix: Counter) -> Dict[str, dict]:
    stats = {}
    for lab in LABELS:
        tp = matrix[(lab, lab)]
        pred = sum(v for (_, o), v in matrix.items() if o == lab)
        truth = sum(v for (e, _), v in matrix.items() if e == lab)
        stats[lab] = {"precision": round(tp / pred, 3) if pred else None,
                      "recall": round(tp / truth, 3) if truth else None, "n": truth}
    return stats


def summarize(samples: List[dict], results: Dict[str, List[dict]]) -> dict:
    """Precision / recall tung nhan tren moi (mau, lan chay) khong degraded; `contradicted` tach theo R / chi S."""
    pairs = [(s["expect"]["support"], r["observed"], s) for s in samples for r in results[s["id"]] if not r["degraded"]]
    matrix = Counter((e, o) for e, o, _ in pairs)
    contra = [(o, s) for e, o, s in pairs if e == "contradicted"]
    by_doc = {"R": [o == "contradicted" for o, s in contra if s.get("reference_answer")],
              "S": [o == "contradicted" for o, s in contra if not s.get("reference_answer")]}
    runs_contra = [r for s in samples if s["expect"]["support"] == "contradicted" for r in results[s["id"]]
                   if not r["degraded"]]
    right, wrong = with_reference(samples, results, True), with_reference(samples, results, False)
    return {"samples": len(samples), "runs": max((len(v) for v in results.values()), default=0),
            "degraded_runs_excluded": sum(r["degraded"] for v in results.values() for r in v),
            "confusion_expected_observed": {f"{e}->{o}": n for (e, o), n in sorted(matrix.items())},
            "per_label": label_stats(matrix),
            "per_label_by_cohort": {c: label_stats(Counter((e, o) for e, o, s in pairs
                                                           if s.get("cohort", "short") == c)) for c in COHORTS},
            "contradicted_recall_by_doc": {k: round(sum(v) / len(v), 3) if v else None for k, v in by_doc.items()},
            # cau tra loi sai: diem technical_accuracy va misconception co phan anh khong (postcheck chi chan khi R bac bo)
            "wrong_answer_technical_accuracy_mean": round(sum(r["technical_accuracy"] for r in runs_contra)
                                                          / len(runs_contra), 2) if runs_contra else None,
            "wrong_answer_with_misconception": round(sum(r["misconceptions"] > 0 for r in runs_contra)
                                                     / len(runs_contra), 3) if runs_contra else None,
            "r_blocked_wrong_answers": share(wrong, "r_blocked"),
            "r_blocked_correct_answers": share(right, "r_blocked"),
            "correct_with_r_technical_accuracy_mean": round(sum(r["technical_accuracy"] for r in right) / len(right), 2)
            if right else None,
            "correct_with_r_with_misconception": share(right, "misconceptions"),
            "invalid_source_ids": sum(r["invalid_ids"] for v in results.values() for r in v),
            "by_sample": {sid: Counter(r["observed"] for r in v) for sid, v in results.items()}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--prompt", default=None, help="vd v5; mac dinh v8 (ban ghim)")
    parser.add_argument("--lookup", action="store_true", help="bat Evaluator tra cuu kho (can RAG + AI_DB_URL)")
    parser.add_argument("--policy-context", choices=["none", "default"], default="none",
                        help="default: them policy_context trung tinh vao dau vao (chi prompt v9 render), de gate v9 vs v8")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    samples, collector = load_golden(GOLDEN), UsageCollector()
    results = asyncio.run(run_all(samples, args.runs, args.prompt, collector, lookup=args.lookup, policy_context=args.policy_context))
    summary = {**summarize(samples, results), "usage": collector.to_metadata()["usage"]}
    if args.lookup:
        summary["lookup"] = lookup_summary([r for runs in results.values() for r in runs])
    print(json.dumps({k: v for k, v in summary.items() if k != "by_sample"}, ensure_ascii=False, indent=1))
    out = args.out or REPORTS / f"eval-evaluator-sourced-{datetime.now():%y%m%d-%H%M}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=1), "utf-8")
    print(f"Da ghi {out}")


if __name__ == "__main__":
    main()
