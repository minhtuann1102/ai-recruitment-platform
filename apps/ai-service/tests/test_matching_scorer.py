"""017 US2 T013: ham thuan cua scorer: loc cung, thanh phan diem (data-model muc 4), degraded, thu tu va tran."""
from datetime import date

import numpy as np
import pytest

from app.matching.levels_tracks import level_rank
from app.matching.scorer import (IndexedJob, cosine_scores, effective_weights, level_fit, passes_hard_filter,
                                 rank_jobs, skill_overlap)
from app.matching.settings import MatchWeights

AS_OF = date(2026, 11, 21)
W = MatchWeights(0.6, 0.3, 0.1)


def job(job_id, *, group="backend", level="Mid", deadline=date(2030, 1, 1), skills=("java",), title="T"):
    return IndexedJob(job_id=job_id, title=title, group=group, level=level, level_rank=level_rank(level),
                      deadline=deadline, skills=frozenset(skills))


def hard(j, *, group="backend", as_of=AS_OF, candidate_rank=2, gap=1):
    return passes_hard_filter(j, group=group, as_of=as_of, candidate_rank=candidate_rank, max_level_gap=gap)


def rank(jobs, matrix=None, cv_vector=None, cv_skills=(), **kw):
    args = dict(group="backend", as_of=AS_OF, candidate_rank=2, weights=W, max_level_gap=1, max_results=50)
    args.update(kw)
    matrix = np.eye(len(jobs), 4) if matrix is None else matrix
    return rank_jobs(jobs, matrix, cv_vector, cv_skills, **args)


# --- loc cung ---------------------------------------------------------------------------------------------------

def test_hard_filter_same_group_only():
    assert hard(job("a")) and not hard(job("a", group="frontend"))


def test_hard_filter_deadline_is_inclusive_and_null_deadline_passes():
    assert hard(job("a", deadline=AS_OF))  # deadline >= as_of
    assert not hard(job("a", deadline=date(2026, 11, 20)))
    assert hard(job("a", deadline=None))  # khong co han = khong biet het han: khong loc


@pytest.mark.parametrize("jd_level,passes", [("Intern", False), ("Junior", True), ("Mid", True), ("Senior", True),
                                             ("Lead", False)])
def test_hard_filter_level_gap_at_most_one_for_middle_candidate(jd_level, passes):
    assert hard(job("a", level=jd_level), candidate_rank=2) is passes


def test_hard_filter_gap_is_configurable():
    assert not hard(job("a", level="Senior"), candidate_rank=2, gap=0)
    assert hard(job("a", level="Lead"), candidate_rank=2, gap=2)


def test_hard_filter_jd_without_level_or_candidate_without_level_is_not_filtered():
    assert hard(job("a", level=None), candidate_rank=3)
    assert hard(job("a", level="Manager"), candidate_rank=None)


def test_rank_jobs_drops_filtered_and_restricts_to_job_ids():
    jobs = [job("a"), job("b", group="devops"), job("c", deadline=date(2020, 1, 1)), job("d", level="Lead"),
            job("e"), job("f")]
    assert [s.job.job_id for s in rank(jobs)] == ["a", "e", "f"]
    assert [s.job.job_id for s in rank(jobs, job_ids=["f", "a", "b", "zzz"])] == ["a", "f"]  # b khong qua loc, zzz la


def test_no_job_passes_gives_empty_list():
    assert rank([job("a", group="devops")]) == []
    assert rank([]) == []


# --- thanh phan diem -------------------------------------------------------------------------------------------

def test_cosine_is_clamped_to_zero_one_and_cv_vector_is_normalized_inside():
    matrix = np.array([[1.0, 0, 0, 0], [0.6, 0.8, 0, 0], [-1.0, 0, 0, 0], [0, 1.0, 0, 0]])
    got = cosine_scores(np.array([5.0, 0, 0, 0]), matrix)  # cv chua chuan hoa
    assert got == pytest.approx([1.0, 0.6, 0.0, 0.0])  # am -> 0
    assert (got >= 0).all() and (got <= 1).all()


def test_cosine_zero_vector_gives_zeros_not_nan():
    assert cosine_scores(np.zeros(4), np.eye(3, 4)).tolist() == [0.0, 0.0, 0.0]


def test_skill_overlap_ratio_matched_and_missing_in_slug_order():
    value, matched, missing = skill_overlap({"java", "spring-boot", "kafka", "redis"}, {"java", "spring-boot", "go"})
    assert value == 0.5 and matched == ["java", "spring-boot"] and missing == ["kafka", "redis"]


def test_skill_overlap_empty_jd_is_zero():
    assert skill_overlap(frozenset(), {"java"}) == (0.0, [], [])
    assert skill_overlap({"java"}, set()) == (0.0, [], ["java"])


@pytest.mark.parametrize("jd,cand,expected", [(2, 2, 1.0), (1, 2, 0.5), (3, 2, 0.5), (0, 2, 0.0), (4, 2, 0.0),
                                              (None, 2, 0.5), (2, None, 0.5), (None, None, 0.5)])
def test_level_fit(jd, cand, expected):
    assert level_fit(jd, cand) == expected


def test_score_follows_formula_with_display_names_and_notes():
    jobs = [job("a", skills=("java", "spring-boot", "kafka"), level="Mid")]
    cv = np.array([1.0, 0, 0, 0])
    [s] = rank(jobs, matrix=np.array([[0.6, 0.8, 0, 0]]), cv_vector=cv, cv_skills={"java", "spring-boot"})
    assert s.cosine == pytest.approx(0.6) and s.skill_match == pytest.approx(2 / 3, abs=1e-4) and s.level_fit == 1.0
    assert s.score == pytest.approx(0.6 * 0.6 + 0.3 * (2 / 3) + 0.1 * 1.0, abs=1e-4)
    assert s.matched_skills == ("Java", "Spring Boot") and s.missing_skills == ("Kafka",)  # ten hien thi, theo slug
    assert s.notes == ()


def test_jd_without_skills_scores_zero_skill_match_with_note():
    [s] = rank([job("a", skills=())], cv_vector=np.array([1.0, 0, 0, 0]), cv_skills={"java"})
    assert s.skill_match == 0.0 and s.notes == ("jd_no_skills",) and s.matched_skills == s.missing_skills == ()


def test_jd_without_level_gets_half_level_fit_and_note_but_unknown_candidate_level_gets_no_note():
    [s] = rank([job("a", level=None)], cv_vector=np.array([1.0, 0, 0, 0]))
    assert s.level_fit == 0.5 and "jd_no_level" in s.notes
    [s] = rank([job("a", level="Mid")], cv_vector=np.array([1.0, 0, 0, 0]), candidate_rank=None)
    assert s.level_fit == 0.5 and s.notes == ()


# --- degraded ---------------------------------------------------------------------------------------------------

def test_effective_weights_renormalize_when_degraded():
    assert effective_weights(W, degraded=False) == W
    got = effective_weights(W, degraded=True)
    assert (got.cosine, got.skill_match, got.level_fit) == (0.0, pytest.approx(0.75), pytest.approx(0.25))
    assert effective_weights(MatchWeights(0.5, 0.5, 0.0), degraded=True).skill_match == 1.0


def test_degraded_has_no_cosine_and_uses_w2_w3_only():
    jobs = [job("a", skills=("java", "kafka"))]
    [s] = rank(jobs, cv_vector=None, cv_skills={"java"})
    assert s.cosine is None
    assert s.score == pytest.approx(0.75 * 0.5 + 0.25 * 1.0, abs=1e-4)


def test_degraded_with_zero_w2_w3_scores_zero_without_nan_and_orders_by_job_id():
    got = rank([job("b"), job("a")], cv_vector=None, cv_skills={"java"}, weights=MatchWeights(1.0, 0.0, 0.0))
    assert [s.job.job_id for s in got] == ["a", "b"] and [s.score for s in got] == [0.0, 0.0]


# --- thu tu va tran --------------------------------------------------------------------------------------------

def test_order_is_score_desc_then_job_id_asc():
    jobs = [job("c", skills=("java",)), job("a", skills=("java",)), job("b", skills=("java",)),
            job("d", skills=("java", "kafka"))]
    got = rank(jobs, cv_vector=None, cv_skills={"java"})
    assert [s.job.job_id for s in got] == ["a", "b", "c", "d"]  # d chi khop 1/2 nen thap nhat; a b c hoa -> job_id


def test_ties_use_the_rounded_score_so_displayed_order_is_consistent():
    # hai cosine khac 1e-10 (b nhinh hon): sau lam tron 4 chu so hai diem bang nhau -> thu tu theo job_id, khong theo
    # nhieu so thuc (hang ma tran dua thang vao tich vo huong nen khong can chuan hoa o day)
    matrix = np.array([[0.5, 0, 0, 0], [0.5000000001, 0, 0, 0]])
    got = rank([job("a"), job("b")], matrix=matrix, cv_vector=np.array([1.0, 0, 0, 0]))
    assert got[0].score == got[1].score and [s.job.job_id for s in got] == ["a", "b"]


def test_better_cosine_ranks_first_and_ranking_is_stable_across_runs():
    jobs = [job("a"), job("b"), job("c")]
    matrix = np.array([[0.0, 1.0, 0, 0], [1.0, 0.0, 0, 0], [0.6, 0.8, 0, 0]])
    cv = np.array([1.0, 0, 0, 0])
    first = rank(jobs, matrix=matrix, cv_vector=cv)
    assert [s.job.job_id for s in first] == ["b", "c", "a"]
    assert rank(jobs, matrix=matrix, cv_vector=cv) == first


def test_results_capped_at_max_results_keeping_the_best():
    jobs = [job(f"j{i}") for i in range(5)]
    matrix = np.array([[i / 10, 1 - i / 10, 0, 0] for i in range(5)])  # j4 giong cv nhat... theo cosine voi [1,0,0,0]
    got = rank(jobs, matrix=matrix, cv_vector=np.array([1.0, 0, 0, 0]), max_results=2)
    assert len(got) == 2 and [s.job.job_id for s in got] == ["j4", "j3"]
