"""Chi so tang 2 cho Evaluator (docs/ai-service/09 muc 10.2, NFR-AI-QUAL01..08). Ham thuan, khong goi mang.

Nhan nguoi: moi nguoi gan nhan mot file {sample_id: {bands..., answer_type}}. Nhan chot = nhan sau hop (final)
neu co; khong thi trung binh hai nguoi khi moi tieu chi lech <= 1; lech >= 2 ma chua hop thi loai khoi phep do.
"""
import statistics
from typing import Dict, List, Optional, Sequence, Tuple

CRITERIA = ("technical_accuracy", "completeness", "extensibility", "relevance")
TIER_ORDER = ("strong", "medium", "weak")


def consensus(a: Optional[dict], b: Optional[dict], final: Optional[dict] = None) -> Tuple[Optional[dict], str]:
    """-> (nhan dung de do, trang thai: final | agreed | single | needs_adjudication | unlabeled)."""
    if final:
        return final, "final"
    if a and b:
        if any(abs(a[c] - b[c]) >= 2 for c in CRITERIA):
            return None, "needs_adjudication"
        merged = {c: (a[c] + b[c]) / 2 for c in CRITERIA}
        merged["answer_type"] = a["answer_type"] if a["answer_type"] == b["answer_type"] else None
        return merged, "agreed"
    if a or b:  # mot nguoi: van do duoc nhung bao cao rieng, khong du chuan 2 nguoi cua design
        return dict(a or b), "single"
    return None, "unlabeled"


def agreement(pairs: Sequence[Tuple[float, float]]) -> Dict[str, Optional[float]]:
    """pairs = [(band LLM, band nguoi)] tren moi (mau x tieu chi) -> khop +-1, MAE, do lech khoan dung."""
    if not pairs:
        return {"n": 0, "within1": None, "mae": None, "leniency_bias": None}
    diffs = [llm - human for llm, human in pairs]
    return {"n": len(pairs), "within1": round(sum(abs(d) <= 1 for d in diffs) / len(diffs), 3),
            "mae": round(sum(abs(d) for d in diffs) / len(diffs), 3),
            "leniency_bias": round(sum(diffs) / len(diffs), 3)}


def quadratic_kappa(a: Sequence[int], b: Sequence[int], k: int = 5) -> Optional[float]:
    """Cohen's kappa co trong so bac hai cho thang 0..k-1 (so sanh LLM-nguoi voi nguoi-nguoi)."""
    if len(a) != len(b) or not a:
        return None
    n = len(a)
    observed = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b):
        observed[x][y] += 1
    hist_a = [sum(row) for row in observed]
    hist_b = [sum(observed[i][j] for i in range(k)) for j in range(k)]
    num = den = 0.0
    for i in range(k):
        for j in range(k):
            w = (i - j) ** 2 / (k - 1) ** 2
            num += w * observed[i][j] / n
            den += w * hist_a[i] * hist_b[j] / (n * n)
    return None if den == 0 else round(1 - num / den, 3)


def consistency(runs_by_sample: Dict[str, List[dict]]) -> Optional[float]:
    """Trung binh do lech chuan band qua cac lan chay (moi mau x tieu chi); can >= 2 lan chay."""
    stds = [statistics.pstdev([r[c] for r in runs]) for runs in runs_by_sample.values() if len(runs) >= 2
            for c in CRITERIA]
    return round(sum(stds) / len(stds), 3) if stds else None


def ordering(mean_score: Dict[str, float], tiers: Dict[str, Tuple[str, str]]) -> Optional[float]:
    """% cau hoi co diem strong > medium > weak. tiers = {sample_id: (qid, tier)}, mean_score = {sample_id: diem}."""
    by_q: Dict[str, Dict[str, float]] = {}
    for sid, (qid, tier) in tiers.items():
        if tier in TIER_ORDER and sid in mean_score:
            by_q.setdefault(qid, {})[tier] = mean_score[sid]
    full = [q for q in by_q.values() if len(q) == 3]
    if not full:
        return None
    ok = sum(q["strong"] > q["medium"] > q["weak"] for q in full)
    return round(ok / len(full), 3)


def rate(hits: Sequence[bool]) -> Optional[float]:
    return round(sum(hits) / len(hits), 3) if hits else None
