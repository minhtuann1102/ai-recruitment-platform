"""Planner dung duoc ke hoach hop le cho moi track, level va thoi luong (smoke)."""
import pytest

from app.catalog.loader import list_tracks
from app.mock_planner import build_plan

LEVELS = ["fresher", "junior", "middle", "senior"]


@pytest.mark.parametrize("track", list_tracks())
@pytest.mark.parametrize("level", LEVELS)
@pytest.mark.parametrize("duration", [15, 20, 30, 45])
def test_build_plan_for_every_track_level_and_duration(track, level, duration):
    plan = build_plan(track, level, duration, None)
    assert [p.phase for p in plan.phases] == ["intro", "technical", "scenario"]
    topics = [t for p in plan.phases for t in p.topics]
    assert len({t.id for t in topics}) == len(topics)
    assert all(len(t.key_points) >= 3 and t.backup_question for t in topics)
