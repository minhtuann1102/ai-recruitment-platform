"""017 US2 T011: bang bac level va anh xa track -> nhom (spec Assumptions, data-model muc 3)."""
import pytest

from app.catalog.loader import list_tracks
from app.matching.levels_tracks import TRACK_GROUPS, candidate_level_rank, group_for_track, level_rank, rank_from_years


@pytest.mark.parametrize("label,rank", [
    ("Intern", 0), ("Junior", 1), ("fresher", 1), ("junior", 1), ("Mid", 2), ("middle", 2),
    ("Senior", 3), ("senior", 3), ("Lead", 4), ("Manager", 5),
])
def test_level_rank_table(label, rank):
    assert level_rank(label) == rank


def test_level_rank_is_case_and_space_insensitive_and_none_means_no_level():
    assert level_rank("  MID ") == 2 and level_rank("Fresher") == 1
    assert level_rank(None) is None and level_rank("") is None
    assert level_rank("principal") is None  # nhan la -> coi nhu khong co level, khong loc


def test_six_tracks_map_to_four_groups_and_cover_the_catalog():
    assert TRACK_GROUPS == {
        "java_backend": "backend", "nodejs_backend": "backend", "python_backend": "backend",
        "frontend_react": "frontend", "devops_engineer": "devops", "ai_engineer": "ai_data",
    }
    assert set(TRACK_GROUPS) == set(list_tracks())  # them track moi o catalog thi phai them o day


def test_group_for_track_unknown_is_none():
    assert group_for_track("java_backend") == "backend"
    assert group_for_track("mobile_fullstack") is None and group_for_track("../x") is None


@pytest.mark.parametrize("years,rank", [(0, 1), (0.5, 1), (2.9, 1), (3, 2), (4.9, 2), (5, 3), (12, 3)])
def test_rank_from_years_thresholds_follow_009(years, rank):
    assert rank_from_years(years) == rank


def test_rank_from_years_none_means_no_level():
    assert rank_from_years(None) is None


def test_candidate_rank_prefers_request_level_then_years_then_none():
    assert candidate_level_rank("senior", 1.0) == 3  # level muc tieu thang so nam
    assert candidate_level_rank(None, 4.0) == 2
    assert candidate_level_rank(None, None) is None
