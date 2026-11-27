"""Chan doan khi cong tai lap lech: so tung CV / tung cap voi lan chay 017 goc (data/processed/match_eval/run-*.json, gitignore).

File run goc luu thu hang day du moi CV (job_id, score, cosine, skill_match) nen biet duoc CV nao doi thu tu, lech cosine bao nhieu,
va so cong bo se ra sao neu chi nhung CV do dung thu hang goc. Khong sua ket qua cua cong: chi giai thich so lech.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from .match_eval_metrics import rank_items, quality_summary
from .settings import MATCH_EVAL_RUN_DIR

ORIGINAL_RUN_PATH = MATCH_EVAL_RUN_DIR / "run-20261123T044343309633Z.json"  # lan chay ghi trong eval-results.md
NEAR_TIE_GAP = 0.003  # chenh diem day du giua hang 5 va 6 nho hon nguong nay: cosine lech ~1e-3 co the doi top-5


def _original_items(rows: Sequence[Dict]) -> List[Dict]:
    return [{"job_id": r["job_id"], "score": r["score"],
             "components": {"cosine": r["cosine"], "skill_match": r["skill_match"], "level_fit": 0.0}} for r in rows]


def drift_vs_original_run(items: Dict[str, List[Dict]], labels: Dict[str, Dict[str, int]],
                          run_path: Path = ORIGINAL_RUN_PATH) -> Optional[Dict]:
    if not run_path.is_file():
        return None
    original = {cv: _original_items(rows) for cv, rows in json.loads(run_path.read_text(encoding="utf-8"))["rankings"].items()}
    cos_diff: Dict[str, float] = {}
    changed: List[Dict] = []
    near_ties: List[Dict] = []
    for cv_id, mine in items.items():
        old = {i["job_id"]: i for i in original[cv_id]}
        cos_diff[cv_id] = max(abs(old[i["job_id"]]["components"]["cosine"] - i["components"]["cosine"]) for i in mine)
        ranked, ranked_old = rank_items(mine, "full"), rank_items(original[cv_id], "full")
        if len(ranked) > 5:
            gap = ranked[4]["score"] - ranked[5]["score"]
            if gap < NEAR_TIE_GAP:
                near_ties.append({"cv_id": cv_id, "gap_rank5_rank6": round(gap, 4),
                                  "labels_rank5_rank6": [labels[cv_id][ranked[4]["job_id"]], labels[cv_id][ranked[5]["job_id"]]]})
        if [i["job_id"] for i in ranked] != [i["job_id"] for i in ranked_old]:
            pos = next(p for p, (a, b) in enumerate(zip(ranked, ranked_old)) if a["job_id"] != b["job_id"])
            changed.append({"cv_id": cv_id, "first_difference_rank": pos + 1,
                            "now": {"job_id": ranked[pos]["job_id"], "score": ranked[pos]["score"], "label": labels[cv_id][ranked[pos]["job_id"]]},
                            "original_run": {"job_id": ranked_old[pos]["job_id"], "score": ranked_old[pos]["score"],
                                             "label": labels[cv_id][ranked_old[pos]["job_id"]]}})
    patched = {cv: (original[cv] if cv in {c["cv_id"] for c in changed} else v) for cv, v in items.items()}
    overall = {m: quality_summary(patched, labels, m) for m in ("full", "skill_match", "cosine")}
    return {"run_file": run_path.name, "max_abs_cosine_diff_all_pairs": max(cos_diff.values()),
            "cvs_with_cosine_diff_over_1e-4": {c: round(d, 5) for c, d in sorted(cos_diff.items(), key=lambda kv: -kv[1]) if d > 1e-4},
            "cvs_with_different_full_order": changed, "near_ties_rank5_rank6": near_ties,
            "metrics_if_changed_cvs_use_original_ranking": {m: {"p_at_5": s["p_at_5"], "ndcg_at_5": s["ndcg_at_5"]} for m, s in overall.items()}}
