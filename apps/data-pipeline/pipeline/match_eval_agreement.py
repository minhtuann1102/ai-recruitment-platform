"""Do dong thuan nhan danh gia goi y CV-JD (spec 017 US3, research R9): DE gan mu mot phan so cap, so voi nhan cuoi.

Kappa Cohen co trong so bac hai cho nhan thu tu 0/1/2, kem ty le trung tuyet doi va lech toi da mot muc.
Chay (trong apps/data-pipeline):
    python -m pipeline.match_eval_agreement data/seeds/match_eval/de_blind_labels.json data/seeds/match_eval/labels.json
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

LEVELS = 3  # nhan 0 / 1 / 2

Labels = Dict[str, Dict[str, int]]


def weighted_kappa(a: Sequence[int], b: Sequence[int], k: int = LEVELS) -> float:
    """Kappa trong so bac hai; tra nan khi khong tinh duoc (mot ben chi co mot nhan)."""
    if len(a) != len(b) or not a:
        raise ValueError("hai day nhan phai cung do dai va khac rong")
    n = len(a)
    obs = [[0] * k for _ in range(k)]
    for x, y in zip(a, b):
        obs[x][y] += 1
    rows = [sum(r) for r in obs]
    cols = [sum(obs[i][j] for i in range(k)) for j in range(k)]
    weight = [[(i - j) ** 2 / (k - 1) ** 2 for j in range(k)] for i in range(k)]
    observed = sum(weight[i][j] * obs[i][j] for i in range(k) for j in range(k))
    expected = sum(weight[i][j] * rows[i] * cols[j] / n for i in range(k) for j in range(k))
    return 1 - observed / expected if expected else float("nan")


def paired(sample: Labels, reference: Labels) -> Tuple[List[int], List[int]]:
    """Ghep nhan theo (cv_id, jd_id) cua mau; cap thieu trong reference la loi."""
    missing = [(c, j) for c in sample for j in sample[c] if j not in reference.get(c, {})]
    if missing:
        raise ValueError(f"reference thieu {len(missing)} cap, vd {missing[:3]}")
    pairs = sorted((c, j) for c in sample for j in sample[c])
    return [sample[c][j] for c, j in pairs], [reference[c][j] for c, j in pairs]


def agreement(sample: Labels, reference: Labels) -> Dict[str, float]:
    a, b = paired(sample, reference)
    n = len(a)
    return {"n": n, "weighted_kappa": round(weighted_kappa(a, b), 3),
            "exact": round(sum(x == y for x, y in zip(a, b)) / n, 4),
            "within_one": round(sum(abs(x - y) <= 1 for x, y in zip(a, b)) / n, 4)}


def _load(path: str) -> Labels:
    return json.loads(Path(path).read_text(encoding="utf-8"))["labels"]


def main(argv: Sequence[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 1
    print(json.dumps(agreement(_load(argv[0]), _load(argv[1]))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
