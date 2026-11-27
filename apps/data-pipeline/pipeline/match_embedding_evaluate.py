"""Danh gia cua experiment embedding 017: ngu canh dung chung, cong tai lap (day du / khong can embedding) va cham tung model.

Moi model di qua CUNG mot duong: ma tran JD cua model (hang theo thu tu chi muc cua endpoint, da chuan hoa) + vector CV ->
endpoint_items (loc cung + diem day du, gia tri da kep va lam tron nhu endpoint) va xep hang cosine thuan (chi so chinh).
"""
from datetime import date
from typing import Dict

import numpy as np

from .match_embedding_ai_service import build_cv_inputs, endpoint_items, load_ai_service, pool_subset
from .match_embedding_gate import check_pool_texts, compare_published, load_index, quality_tables
from .match_embedding_gate_drift import drift_vs_original_run
from .match_embedding_models import PASSAGE, QUERY, ModelSpec
from .match_embedding_stats import (cosine_by_label_group, cosine_scale, mean_scores, normalize_rows, paired_bootstrap,
                                    per_cv_scores, raw_cosine_items, top_k_share, verdict)
from .match_eval_data import compare_pair_sets, language_groups, load_eval_data, load_pool_jds
from .settings import JD_NORMALIZED_PATH, MATCH_EVAL_SEEDS_DIR

BASE_ID = "oa-small"


class Context:
    """Du lieu dung chung cho moi model: bo dev, chi muc da luu trong ai_db, van ban CV / JD."""

    def __init__(self):
        self.data = load_eval_data(MATCH_EVAL_SEEDS_DIR)
        self.jds = load_pool_jds(JD_NORMALIZED_PATH, self.data.jd_ids)
        self.groups = language_groups(self.jds)
        self.ai = load_ai_service()
        self.cvs = build_cv_inputs(self.ai, self.data.cvs)
        self.as_of = date.fromisoformat(self.data.as_of)
        self.index = load_index(self.ai)
        self.jobs, self.rows = pool_subset(self.index.snapshot.jobs, self.data.jd_ids)  # thu tu chi muc cua endpoint
        self.jd_ids = [j.job_id for j in self.jobs]
        self.jd_texts = [self.index.content_by_id[j] for j in self.jd_ids]  # dung chuoi 3-small da embed (khong dung ban dung lai)
        self.items = [(QUERY, c.text) for c in self.cvs] + [(PASSAGE, t) for t in self.jd_texts]

    def split(self, vectors: np.ndarray):
        """(vector CV theo cv_id, ma tran JD da chuan hoa) tu ma tran vector theo thu tu `items`."""
        n = len(self.cvs)
        return {c.cv_id: vectors[i] for i, c in enumerate(self.cvs)}, normalize_rows(vectors[n:])

    def score(self, cv_vecs, matrix: np.ndarray) -> Dict:
        return endpoint_items(self.ai, self.jobs, matrix, self.cvs, cv_vecs, self.as_of, self.jd_ids)

    def settings(self) -> Dict:
        s = self.ai.settings
        return {"weights": vars(s.weights), "max_level_gap": s.max_level_gap, "max_results": s.max_results, "as_of": self.data.as_of}


def run_gate_without_embeddings(ctx: Context) -> Dict:
    """Phan cong khong can vector CV (khi khoa OpenAI bi tu choi): loc cung + skill_match xep hang khong dung embedding,
    nen so skill-only (0.847 / 0.625) kiem duoc metadata, bo loc, tap cap va luat hoa. KHONG thay cho cong tai lap day du."""
    items = ctx.score(None, ctx.index.snapshot.matrix[ctx.rows])
    tables = quality_tables(items, ctx.data.labels, ctx.groups, methods=("skill_match",))
    pair_check = compare_pair_sets({c: [i["job_id"] for i in v] for c, v in items.items()}, ctx.data.labels)
    return {"partial": True, "published": compare_published(tables, methods=("skill_match",)), "pair_check": pair_check.to_dict(),
            "index": ctx.index.info, "pool_text_check": check_pool_texts(ctx.index, ctx.jds, ctx.data.jd_ids), "settings": ctx.settings()}


def run_gate(ctx: Context, small: Dict) -> Dict:
    """oa-small: vector JD luu trong ai_db (nhu endpoint) + vector CV embed lai; so voi so da cong bo; kiem them vector JD embed lai."""
    cv_vecs, fresh = ctx.split(small["vectors"])
    stored = ctx.index.snapshot.matrix[ctx.rows]
    items = ctx.score(cv_vecs, stored)
    pair_check = compare_pair_sets({c: [i["job_id"] for i in v] for c, v in items.items()}, ctx.data.labels)
    cos_stored_vs_fresh = np.sum(stored * fresh, axis=1)
    full, skill, cosine = (per_cv_scores(items, ctx.data.labels, m) for m in ("full", "skill_match", "cosine"))
    ndcg = lambda d: {c: v[0] for c, v in d.items()}  # noqa: E731
    return {
        "published": compare_published(quality_tables(items, ctx.data.labels, ctx.groups)), "pair_check": pair_check.to_dict(),
        "index": ctx.index.info, "pool_text_check": check_pool_texts(ctx.index, ctx.jds, ctx.data.jd_ids),
        "jd_vector_fresh_vs_stored_cosine": {"min": float(cos_stored_vs_fresh.min()), "mean": float(cos_stored_vs_fresh.mean())},
        "with_fresh_jd_vectors": compare_published(quality_tables(ctx.score(cv_vecs, fresh), ctx.data.labels, ctx.groups)),
        "drift_vs_original_run": drift_vs_original_run(items, ctx.data.labels),
        "bootstrap_sanity": {  # so voi eval-analysis 017 muc 1: +0.036 [-0.010, +0.084] 12/6/6 va +0.041 12/10/2
            "full_vs_skill_match": paired_bootstrap(ndcg(skill), ndcg(full)),
            "full_vs_cosine": paired_bootstrap(ndcg(cosine), ndcg(full))},
        "settings": ctx.settings()}


def evaluate_model(ctx: Context, spec: ModelSpec, emb: Dict) -> Dict:
    labels, groups = ctx.data.labels, ctx.groups
    cv_vecs, matrix = ctx.split(emb["vectors"])
    full_items = ctx.score(cv_vecs, matrix)
    raw_items = {c: raw_cosine_items(cv_vecs[c], matrix, ctx.jd_ids, [i["job_id"] for i in v]) for c, v in full_items.items()}
    same, cross = (lambda j: groups[j] == "same"), (lambda j: groups[j] == "cross")
    per_cv = {"primary": per_cv_scores(raw_items, labels, "cosine"), "full": per_cv_scores(full_items, labels, "full")}
    relevant_vi = [groups[j] == "same" for v in labels.values() for j, y in v.items() if y >= 1]
    return {
        "model_id": spec.model_id, "name": spec.name, "dims": spec.dims, "revision": emb["revision"], "ops": emb["ops"],
        "primary_cosine_only": {"overall": mean_scores(per_cv["primary"]),
                                "same": mean_scores(per_cv_scores(raw_items, labels, "cosine", same)),
                                "cross": mean_scores(per_cv_scores(raw_items, labels, "cosine", cross))},
        "secondary_full_score": {"overall": mean_scores(per_cv["full"]),
                                 "same": mean_scores(per_cv_scores(full_items, labels, "full", same)),
                                 "cross": mean_scores(per_cv_scores(full_items, labels, "full", cross))},
        "endpoint_style_cosine_only": mean_scores(per_cv_scores(full_items, labels, "cosine")),
        "skill_only_baseline": mean_scores(per_cv_scores(full_items, labels, "skill_match")),
        "diagnostics": {"cosine_scale": cosine_scale(raw_items),
                        "cosine_by_label_group": cosine_by_label_group(raw_items, labels, groups.get),
                        "vi_share_top5_cosine_only": top_k_share(raw_items, same),
                        "vi_share_top5_full": top_k_share(full_items, same, "full"),
                        "vi_share_of_relevant_pairs": sum(relevant_vi) / len(relevant_vi)},
        "per_cv_ndcg": {k: {c: v[0] for c, v in d.items()} for k, d in per_cv.items()}}


def add_comparisons(results: Dict[str, Dict]) -> None:
    """Hieu so nDCG@5 theo CV (model - oa-small) + CI bootstrap + ket luan theo luat quyet dinh (chi so chinh va chi so phu)."""
    base = results[BASE_ID]["per_cv_ndcg"]
    for model_id, res in results.items():
        if model_id == BASE_ID:
            continue
        res["vs_oa_small"] = {}
        for key, name in (("primary", "primary_cosine_only"), ("full", "secondary_full_score")):
            ci = paired_bootstrap(base[key], res["per_cv_ndcg"][key])
            res["vs_oa_small"][name] = {**ci, "verdict": verdict(ci)}
