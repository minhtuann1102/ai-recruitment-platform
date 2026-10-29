"""Chay Evaluator LLM tren golden set va in chi so tang 2 (docs/ai-service/09 muc 10.2).

Can LLM_API_KEY (ton phi, khong chay trong CI). Nhan nguoi o evals/evaluator_labels/{rater_a,rater_b,final}.json;
chua co nhan thi chi in cac chi so khong can nhan (nhat quan, thu tu, bat manipulation, evidence hop le).
  cd apps/ai-service && python -m evals.run_evaluator --runs 3 [--prompt v1] [--limit 10] [--out report.json]
"""
import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from app.agents.evaluator import EvaluationInput, LlmEvaluator
from app.evaluation_checks import quote_in_answer
from app.llm.gateway import get_gateway
from app.llm.usage import UsageCollector
from app.models_interview import PlanTopic
from evals.evaluator_metrics import (CRITERIA, agreement, consensus, consistency, ordering, quadratic_kappa,
                                     rate)
from evals.label_sheet import LABELS_DIR, load_golden

REPORTS = Path(__file__).resolve().parents[3] / "plans" / "reports"


def to_input(s: dict) -> EvaluationInput:
    topic = PlanTopic(id=s["qid"], title=s["topic"]["title"], source="catalog", objective=s["topic"]["objective"],
                      key_points=s["topic"]["key_points"], start_difficulty=2, opening_hint="-", backup_question="-")
    return EvaluationInput(level=s["level"], phase=s["phase"], topic=topic, difficulty=2, turn_kind=s["turn_kind"],
                           turn_number=1, question=s["question"], answer=s["answer"])


async def run_all(samples: List[dict], runs: int, prompt: str, collector: UsageCollector,
                  concurrency: int = 4) -> Dict[str, List[dict]]:
    evaluator, sem = LlmEvaluator(get_gateway(), prompt_version=prompt), asyncio.Semaphore(concurrency)

    async def one(s: dict) -> dict:
        async with sem:
            raw, ev = await evaluator.evaluate_with_raw(to_input(s), collector)
        quotes = [c.quote for c in raw.covered] if raw else []
        source_ids = [i for c in (raw.covered if raw else []) for i in getattr(c, "source_ids", [])]
        return {**ev.scores.model_dump(), "answer_type": ev.answer_type, "turn_score_10": ev.turn_score_10,
                "degraded": ev.degraded, "llm": raw is not None, "quotes": len(quotes),
                "valid_quotes": sum(quote_in_answer(q, s["answer"]) for q in quotes),
                # golden khong co tai lieu: moi id deu la id la (v4 phai tra no_source, source_ids rong)
                "source_ids": len(source_ids)}

    results: Dict[str, List[dict]] = {s["id"]: [] for s in samples}
    for r in range(runs):
        outs = await asyncio.gather(*(one(s) for s in samples))
        for s, out in zip(samples, outs):
            results[s["id"]].append(out)
        print(f"lan chay {r + 1}/{runs} xong", file=sys.stderr)
    return results


def load_labels(directory: Path) -> Dict[str, Dict[str, dict]]:
    return {name: json.loads((directory / f"{name}.json").read_text(encoding="utf-8"))
            for name in ("rater_a", "rater_b", "final") if (directory / f"{name}.json").exists()}


def summarize(samples: List[dict], all_results: Dict[str, List[dict]], labels: Dict[str, Dict[str, dict]]) -> dict:
    """Chi so tren cac lan chay KHONG degraded (lan dung heuristic khong phan anh LLM). Nhan 1 nguoi khong dung
    de do; kappa LLM-nguoi va nguoi-nguoi tinh tren cung tap mau co du 2 nguoi cham, khong lam tron nhan."""
    results = {sid: [r for r in runs if not r["degraded"]] for sid, runs in all_results.items()}
    a, b, final = (labels.get(k, {}) for k in ("rater_a", "rater_b", "final"))
    statuses, pairs, type_hits = {}, [], []
    llm_k, rater_a, rater_b = [], [], []
    for s in samples:
        sid, runs = s["id"], results[s["id"]]
        human, status = consensus(a.get(sid), b.get(sid), final.get(sid))
        statuses[status] = statuses.get(status, 0) + 1
        if not runs:
            continue
        if a.get(sid) and b.get(sid):
            for c in CRITERIA:
                llm_k.append(runs[0][c])
                rater_a.append(a[sid][c])
                rater_b.append(b[sid][c])
        if human is None or status == "single":
            continue
        for run in runs:
            pairs.extend((run[c], human[c]) for c in CRITERIA)
        if human.get("answer_type"):
            type_hits.append(runs[0]["answer_type"] == human["answer_type"])
    kappas = [quadratic_kappa(llm_k, rater_a), quadratic_kappa(llm_k, rater_b)]
    mean_score = {sid: sum(r["turn_score_10"] for r in runs) / len(runs) for sid, runs in results.items() if runs}
    manip_runs = [results[s["id"]] for s in samples if s["expect"].get("answer_type") == "manipulation"]
    caught = [bool(runs) and all(r["answer_type"] == "manipulation" and r["turn_score_10"] == 0 for r in runs)
              for runs in manip_runs]
    llm_runs = {sid: runs for sid, runs in results.items() if runs and all(r["llm"] for r in runs)}
    quotes = sum(r["quotes"] for runs in results.values() for r in runs)
    valid = sum(r["valid_quotes"] for runs in results.values() for r in runs)
    return {
        "samples": len(samples), "runs": max((len(v) for v in all_results.values()), default=0),
        "degraded_runs_excluded": sum(r["degraded"] for runs in all_results.values() for r in runs),
        "label_status": statuses, "agreement": agreement(pairs),
        "kappa_llm_human": None if None in kappas else round(sum(kappas) / 2, 3),
        "kappa_human_human": quadratic_kappa(rater_a, rater_b),
        "answer_type_accuracy": rate(type_hits), "consistency_std": consistency(llm_runs),
        "ordering": ordering(mean_score, {s["id"]: (s["qid"], s["intended_tier"]) for s in samples}),
        "manipulation_caught": rate(caught),
        # mau injection ma regex precheck khong bat, phai do LLM tu nhan ra
        "manipulation_caught_by_llm": rate([ok for ok, runs in zip(caught, manip_runs) if runs and runs[0]["llm"]]),
        "evidence_valid": round(valid / quotes, 3) if quotes else None,
        "invented_source_ids": sum(r.get("source_ids", 0) for runs in results.values() for r in runs),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--prompt", default=None, help="vd v1; mac dinh ban moi nhat")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--labels-dir", type=Path, default=LABELS_DIR)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    samples = load_golden()[: args.limit]
    collector = UsageCollector()
    results = asyncio.run(run_all(samples, args.runs, args.prompt, collector))
    summary = summarize(samples, results, load_labels(args.labels_dir))
    summary["usage"] = collector.to_metadata()["usage"]
    for key, value in summary.items():
        print(f"{key:22s} {value}")
    out = args.out or REPORTS / f"eval-evaluator-{datetime.now():%y%m%d-%H%M}.json"
    out.parent.mkdir(parents=True, exist_ok=True)  # ghi ket qua truoc khi co the mat du lieu da tra phi
    out.write_text(json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"Da ghi {out}")


if __name__ == "__main__":
    main()
