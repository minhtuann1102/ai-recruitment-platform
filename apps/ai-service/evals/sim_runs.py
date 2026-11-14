"""Gop nhieu run (`simulate --runs N`): stdev gop giua persona + CI bootstrap + gap strong-weak (plan agentic muc 8).

Ham thuan, khong goi mang. Co `personas` thi chi persona loi (khong adversarial / skewed) tinh vao stdev gop va gap. `sessions_by_run`: moi phan tu la {persona_id: session} cua mot run (cung dinh dang
`run_all`). Stdev mot persona voi n = 3 (df = 2) khong du de so sanh; gop theo persona cho df ~ 2 x so persona:
  s_p = sqrt( sum_p sum_i (x_pi - mean_p)^2 / sum_p (n_p - 1) )
CI bootstrap lay mau PERSONA (khong lay mau run): do bat dinh giua persona la nguon nhieu chinh.
"""
import random
from collections import defaultdict
from statistics import mean
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from evals.personas import QUALITIES, Persona

Scores = Dict[str, List[float]]  # persona_id -> diem tong theo tung run (bo run hong / unscored)


def is_core(p: Optional[Persona]) -> bool:
    """Persona ma tran strong/average/weak, khong adversarial / skewed: diem cua chung moi dung de do nhieu."""
    return p is not None and not p.behaviors and p.quality in QUALITIES


def scores_by_persona(sessions_by_run: Sequence[Dict[str, Dict]],
                      personas: Optional[Dict[str, Persona]] = None) -> Scores:
    """`personas` co thi chi lay persona loi (adversarial co diem gan san, se keo stdev gop xuong)."""
    out: Scores = defaultdict(list)
    for sessions in sessions_by_run:
        for pid, s in sessions.items():
            if personas is not None and not is_core(personas.get(pid)):
                continue
            score = ((s.get("report") or {}).get("overall") or {}).get("score")
            if score is not None:
                out[pid].append(score)
    return dict(out)


def _pooled(groups: Sequence[Sequence[float]]) -> Optional[float]:
    """Cong thuc stdev gop; persona chi co 1 diem khong dong gop df. None neu khong co df nao."""
    df = sum(len(g) - 1 for g in groups if len(g) >= 2)
    if df <= 0:
        return None
    ss = sum(sum((x - mean(g)) ** 2 for x in g) for g in groups if len(g) >= 2)
    return (ss / df) ** 0.5


def pooled_stdev(sessions_by_run: Sequence[Dict[str, Dict]],
                 personas: Optional[Dict[str, Persona]] = None) -> Optional[float]:
    return _pooled(list(scores_by_persona(sessions_by_run, personas).values()))


def bootstrap_ci(items: Sequence, stat: Callable[[Sequence], Optional[float]], n_boot: int = 1000, seed: int = 0,
                 alpha: float = 0.05) -> Optional[Tuple[float, float]]:
    """CI phan vi bootstrap: lay mau `items` co hoan lai; bo lan mau ma stat = None. Seed co dinh de lap lai duoc."""
    if not items:
        return None
    rng = random.Random(seed)
    vals = sorted(v for v in (stat([rng.choice(items) for _ in items]) for _ in range(n_boot)) if v is not None)
    if not vals:
        return None
    lo, hi = vals[int(alpha / 2 * len(vals))], vals[min(len(vals) - 1, int((1 - alpha / 2) * len(vals)))]
    return round(lo, 3), round(hi, 3)


def _round(x: Optional[float]) -> Optional[float]:
    return None if x is None else round(x, 3)


def pooled_stdev_report(sessions_by_run: Sequence[Dict[str, Dict]],
                        personas: Optional[Dict[str, Persona]] = None) -> Dict:
    groups = list(scores_by_persona(sessions_by_run, personas).values())
    return {"value": _round(_pooled(groups)), "ci95": bootstrap_ci(groups, _pooled),
            "personas": sum(len(g) >= 2 for g in groups), "df": sum(len(g) - 1 for g in groups if len(g) >= 2)}


def strong_weak_gap(sessions_by_run: Sequence[Dict[str, Dict]], personas: Dict[str, Persona]) -> Dict:
    """Gap strong - weak theo nhom (level, track) (trung binh qua cac run), mean + CI bootstrap lay mau nhom."""
    scores = scores_by_persona(sessions_by_run)
    cells: Dict[tuple, Dict[str, float]] = {}
    for pid, vals in scores.items():
        p = personas.get(pid)
        if is_core(p) and p.quality in ("strong", "weak"):
            cells.setdefault((p.level, p.track), {})[p.quality] = mean(vals)
    gaps = [c["strong"] - c["weak"] for c in cells.values() if len(c) == 2]
    stat = lambda xs: mean(xs) if xs else None  # noqa: E731
    return {"mean": _round(stat(gaps)), "ci95": bootstrap_ci(gaps, stat), "groups": len(gaps)}


def summarize_runs(sessions_by_run: Sequence[Dict[str, Dict]], personas: Dict[str, Persona]) -> Dict:
    return {"runs": len(sessions_by_run), "pooled_stdev": pooled_stdev_report(sessions_by_run, personas),
            "strong_weak_gap": strong_weak_gap(sessions_by_run, personas)}
