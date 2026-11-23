"""T029 (spec 017 US3): metric danh gia goi y, so tinh tay. Offline, ham thuan.

P@5: lien quan = nhan >= 1, mau so = min(5, so phan tu) (tap con ngon ngu thuong < 5 JD).
nDCG@5: gain = nhan (tuyen tinh), ideal tinh tu moi nhan cua CV; ideal = 0 -> None (bo khoi trung binh).
"""
import math

import pytest

from pipeline.match_eval_metrics import (
    latency_summary, ndcg_at_k, percentile, precision_at_k, quality_summary, rank_items)


def item(job_id, score=0.0, cosine=0.0, skill_match=0.0):
    return {"job_id": job_id, "score": score, "components": {"cosine": cosine, "skill_match": skill_match, "level_fit": 1.0}}


# ---- P@5 ----
def test_precision_counts_label_one_and_two_as_relevant():
    assert precision_at_k([2, 0, 1, 0, 1]) == pytest.approx(3 / 5)
    assert precision_at_k([0, 0, 0, 0, 0]) == 0.0


def test_precision_only_looks_at_top_five():
    assert precision_at_k([0, 0, 0, 0, 0, 2, 2, 2]) == 0.0


def test_precision_short_list_divides_by_list_length():
    assert precision_at_k([2, 0, 1]) == pytest.approx(2 / 3)  # khong phat danh sach ngan, de tap con ngon ngu so sanh duoc
    assert precision_at_k([]) == 0.0


# ---- nDCG@5 ----
def test_ndcg_hand_computed_two_items():
    # DCG = 1/log2(2) + 2/log2(3) = 2.26186 ; ideal [2,1] = 2 + 1/log2(3) = 2.63093
    assert ndcg_at_k([1, 2]) == pytest.approx(2.2618595 / 2.6309298)


def test_ndcg_hand_computed_six_items_ideal_uses_all_labels():
    # xep [2,0,1,2,0,1]: DCG@5 = 2 + 0 + 1/2 + 2/log2(5) = 3.36135 ; ideal [2,2,1,1,0] = 4.19254
    assert ndcg_at_k([2, 0, 1, 2, 0, 1]) == pytest.approx(3.3613531 / 4.1925361)


def test_ndcg_uses_linear_gain_not_exponential():
    expected = (2 / math.log2(3)) / (2 / math.log2(2))  # [0, 2] so voi ideal [2, 0]
    assert ndcg_at_k([0, 2]) == pytest.approx(expected)  # gain 2^2-1 = 3 se ra ket qua khac


def test_ndcg_perfect_order_is_one_and_short_list_is_fine():
    assert ndcg_at_k([2, 1, 0]) == pytest.approx(1.0)
    assert ndcg_at_k([2]) == pytest.approx(1.0)


def test_ndcg_without_any_relevant_label_is_undefined():
    assert ndcg_at_k([0, 0, 0]) is None
    assert ndcg_at_k([]) is None


def test_ndcg_ideal_considers_relevant_item_below_rank_five():
    # nhan 2 o vi tri 6: DCG@5 = 0, ideal@5 = 2 -> 0 (khong None)
    assert ndcg_at_k([0, 0, 0, 0, 0, 2]) == 0.0


# ---- xep lai theo thanh phan ----
def test_rank_by_each_method_with_job_id_tie_break():
    items = [item("b", score=0.5, cosine=0.9, skill_match=0.1), item("a", score=0.5, cosine=0.2, skill_match=0.8),
             item("c", score=0.7, cosine=0.9, skill_match=0.8)]
    assert [i["job_id"] for i in rank_items(items, "full")] == ["c", "a", "b"]  # a, b hoa 0.5 -> job_id tang dan
    assert [i["job_id"] for i in rank_items(items, "cosine")] == ["b", "c", "a"]  # b, c hoa 0.9 -> b truoc c
    assert [i["job_id"] for i in rank_items(items, "skill_match")] == ["a", "c", "b"]  # a, c hoa 0.8 -> a truoc c


def test_rank_does_not_mutate_input_and_rejects_unknown_method():
    items = [item("b", score=0.1), item("a", score=0.9)]
    rank_items(items, "full")
    assert [i["job_id"] for i in items] == ["b", "a"]
    with pytest.raises(ValueError):
        rank_items(items, "level_fit")


# ---- tong hop theo CV ----
def _labels():
    return {"cv1": {"a": 2, "b": 0, "c": 1}, "cv2": {"a": 0, "b": 0}, "cv3": {"a": 1, "b": 2}}


def test_quality_summary_means_over_cvs_and_skips_cv_without_relevant_pair():
    items = {"cv1": [item("a", 0.9), item("b", 0.8), item("c", 0.7)],
             "cv2": [item("a", 0.9), item("b", 0.8)],  # khong co nhan >= 1: bo
             "cv3": [item("a", 0.9), item("b", 0.8)]}
    summary = quality_summary(items, _labels(), "full")
    assert summary["n_cv"] == 2 and summary["n_pairs"] == 5
    cv1_ndcg = (2 + 0 + 1 / 2) / (2 + 1 / math.log2(3))  # xep [2,0,1] so voi ideal [2,1,0]
    cv3_ndcg = ndcg_at_k([1, 2])
    assert summary["ndcg_at_5"] == pytest.approx((cv1_ndcg + cv3_ndcg) / 2)
    assert summary["p_at_5"] == pytest.approx((2 / 3 + 1.0) / 2)


def test_quality_summary_subset_keeps_ranking_order_and_reports_empty_as_none():
    items = {"cv1": [item("a", 0.9), item("b", 0.8), item("c", 0.7)]}
    only_c = quality_summary(items, _labels(), "full", keep=lambda jd_id: jd_id == "c")
    assert only_c["p_at_5"] == 1.0 and only_c["ndcg_at_5"] == 1.0 and only_c["n_pairs"] == 1
    none_left = quality_summary(items, _labels(), "full", keep=lambda jd_id: False)
    assert none_left == {"p_at_5": None, "ndcg_at_5": None, "n_cv": 0, "n_pairs": 0}


def test_quality_summary_ranks_each_method_from_its_own_component():
    items = {"cv1": [item("a", score=0.1, cosine=0.1, skill_match=0.9), item("b", score=0.9, cosine=0.9, skill_match=0.5),
                     item("c", score=0.5, cosine=0.5, skill_match=0.1)]}
    labels = {"cv1": {"a": 2, "b": 0, "c": 0}}
    assert quality_summary(items, labels, "skill_match")["ndcg_at_5"] == 1.0  # a len dau
    assert quality_summary(items, labels, "cosine")["ndcg_at_5"] < 1.0  # a xuong cuoi
    assert quality_summary(items, labels, "full") == quality_summary(items, labels, "cosine")


# ---- percentile ----
def test_percentile_nearest_rank_returns_an_observed_value():
    assert percentile([50, 15, 40, 35, 20], 50) == 35  # thu tu thu ceil(0.5*5) = 3 cua [15,20,35,40,50]
    assert percentile([50, 15, 40, 35, 20], 95) == 50
    values = list(range(1, 101))
    assert (percentile(values, 50), percentile(values, 95)) == (50, 95)


def test_percentile_edge_cases():
    assert percentile([7], 95) == 7
    assert percentile([3, 1], 0) == 1
    with pytest.raises(ValueError):
        percentile([], 50)


def test_latency_summary_has_count_p50_p95():
    assert latency_summary([10, 20, 30, 40]) == {"n": 4, "p50": 20, "p95": 40}
    assert latency_summary([]) == {"n": 0, "p50": None, "p95": None}
