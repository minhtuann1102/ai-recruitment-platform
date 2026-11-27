"""Thong ke thuan cua experiment embedding 017 (Phase 2): xep hang cosine thuan, metric theo CV, bootstrap, chan doan ngon ngu.

Khong I/O, khong import ai-service / torch / openai: test duoc voi vector gia. Tai su dung ndcg / P@5 / rank_items cua
match_eval_metrics (cung quy uoc voi eval-results 017: CV khong co JD lien quan trong tap dang xet bi bo).
"""
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .match_eval_metrics import K, ndcg_at_k, precision_at_k, rank_items

N_BOOTSTRAP = 10_000
BOOTSTRAP_SEED = 20261126
CI_PERCENT = (2.5, 97.5)
EPS = 1e-9  # chenh nho hon EPS coi la 0 (nhieu dau phay dong, khong phai khac biet that)


def normalize_rows(matrix: np.ndarray) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=np.float64)
    norms = np.linalg.norm(matrix, axis=-1, keepdims=True)
    return matrix / np.where(norms > 0, norms, 1.0)


def raw_cosine_items(cv_vector: np.ndarray, matrix: np.ndarray, job_ids: Sequence[str],
                     allowed: Sequence[str]) -> List[Dict]:
    """Cosine THUAN (khong kep 0, khong lam tron) cua CV voi cac JD `allowed` (qua loc cung); dung dang item cua
    match_eval_metrics de rank_items(method='cosine') xep: giam dan, hoa thi job_id tang dan. Khong phu thuoc thang diem."""
    cos = normalize_rows(matrix) @ normalize_rows(np.asarray(cv_vector)[None, :])[0]
    wanted = set(allowed)
    return [{"job_id": j, "score": float(c), "components": {"cosine": float(c), "skill_match": 0.0, "level_fit": 0.0}}
            for j, c in zip(job_ids, cos) if j in wanted]


def per_cv_scores(items_by_cv: Dict[str, Sequence[Dict]], labels: Dict[str, Dict[str, int]], method: str,
                  keep: Optional[Callable[[str], bool]] = None) -> Dict[str, Tuple[float, float]]:
    """{cv_id: (nDCG@5, P@5)}; CV khong co JD lien quan trong tap (ideal = 0) bi bo, giong quality_summary."""
    out: Dict[str, Tuple[float, float]] = {}
    for cv_id, items in items_by_cv.items():
        ranked = [labels[cv_id][i["job_id"]] for i in rank_items(items, method) if keep is None or keep(i["job_id"])]
        ndcg = ndcg_at_k(ranked)
        if ndcg is not None:
            out[cv_id] = (ndcg, precision_at_k(ranked))
    return out


def mean_scores(per_cv: Dict[str, Tuple[float, float]]) -> Dict:
    n = len(per_cv)
    return {"ndcg_at_5": sum(v[0] for v in per_cv.values()) / n if n else None,
            "p_at_5": sum(v[1] for v in per_cv.values()) / n if n else None, "n_cv": n}


def paired_bootstrap(base: Dict[str, float], other: Dict[str, float], n_boot: int = N_BOOTSTRAP,
                     seed: int = BOOTSTRAP_SEED) -> Dict:
    """Bootstrap ghep theo CV cua (other - base): boc lai n CV co hoan lai n_boot lan, CI 95% bang percentile 2.5 / 97.5.

    `excludes_zero` chi dung khi CI nam han mot phia cua 0 (qua EPS): CI chua 0 -> coi la ngang (luat quyet dinh cua plan).
    """
    cvs = sorted(set(base) & set(other))
    if not cvs:
        raise ValueError("khong co CV chung de so sanh")
    diffs = np.array([other[c] - base[c] for c in cvs], dtype=np.float64)
    idx = np.random.default_rng(seed).integers(0, len(cvs), size=(n_boot, len(cvs)))
    lo, hi = (float(x) for x in np.percentile(diffs[idx].mean(axis=1), CI_PERCENT))
    return {"n_cv": len(cvs), "mean_diff": float(diffs.mean()), "ci_lo": lo, "ci_hi": hi,
            "wins": int((diffs > EPS).sum()), "losses": int((diffs < -EPS).sum()), "ties": int((np.abs(diffs) <= EPS).sum()),
            "excludes_zero": bool(lo > EPS or hi < -EPS)}


def verdict(ci: Dict) -> str:
    """'better' / 'worse' neu CI khong chua 0, nguoc lai 'equal' (khong phan biet duoc)."""
    if not ci["excludes_zero"]:
        return "equal"
    return "better" if ci["ci_lo"] > 0 else "worse"


def top_k_share(items_by_cv: Dict[str, Sequence[Dict]], in_group: Callable[[str], bool], method: str = "cosine",
                k: int = K) -> Optional[float]:
    """Ty le JD thuoc nhom (vd JD tieng Viet) trong top-k cua moi CV, gop moi CV (cung cach eval-analysis 017 muc 2)."""
    hits = total = 0
    for items in items_by_cv.values():
        top = [i["job_id"] for i in rank_items(items, method)[:k]]
        hits += sum(1 for j in top if in_group(j))
        total += len(top)
    return hits / total if total else None


def cosine_by_label_group(items_by_cv: Dict[str, Sequence[Dict]], labels: Dict[str, Dict[str, int]],
                          group_of: Callable[[str], str]) -> Dict[str, Dict[str, Optional[float]]]:
    """Cosine trung binh theo (nhan 0/1/2, nhom ngon ngu JD): cung nhan ma JD khac ngon ngu lech cosine = thien vi ngon ngu."""
    buckets: Dict[Tuple[int, str], List[float]] = {}
    for cv_id, items in items_by_cv.items():
        for item in items:
            buckets.setdefault((labels[cv_id][item["job_id"]], group_of(item["job_id"])), []).append(item["components"]["cosine"])
    groups = sorted({g for _, g in buckets})
    return {str(label): {g: (float(np.mean(buckets[(label, g)])) if (label, g) in buckets else None) for g in groups}
            for label in (0, 1, 2)}


def cosine_scale(items_by_cv: Dict[str, Sequence[Dict]]) -> Dict:
    """Thang cosine thuan tren cac cap qua loc: trung binh / do lech / min / max, so cap am (bi kep 0 trong scorer) va so
    cap hoa sau khi lam tron 4 chu so (scorer lam tron + xep hoa theo job_id)."""
    values = [i["components"]["cosine"] for items in items_by_cv.values() for i in items]
    ties = 0
    for items in items_by_cv.values():
        rounded = [round(i["components"]["cosine"], 4) for i in items]
        ties += len(rounded) - len(set(rounded))
    arr = np.array(values)
    return {"n_pairs": len(values), "mean": float(arr.mean()), "std": float(arr.std()), "min": float(arr.min()),
            "max": float(arr.max()), "n_negative": int((arr < 0).sum()), "n_rounded_ties": ties}
