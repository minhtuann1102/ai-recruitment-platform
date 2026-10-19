"""Kiem tra topic catalog theo track: schema, id duy nhat, du topic cho moi level."""
import pytest

from app.catalog.loader import CatalogError, list_tracks, load_catalog

LEVELS = ["fresher", "junior", "middle", "senior"]
MIN_TOPICS_PER_LEVEL = 5  # phase technical ~4 topic + du de Planner co lua chon


def test_expected_tracks_present():
    assert {"java_backend", "python_backend", "nodejs_backend", "ai_engineer"} <= set(list_tracks())


@pytest.mark.parametrize("track", list_tracks())
def test_track_is_valid_and_covers_every_level(track):
    catalog = load_catalog(track)
    assert catalog.track == track
    for level in LEVELS:
        assert len(catalog.topics_for(level)) >= MIN_TOPICS_PER_LEVEL, f"{track}/{level} thieu topic"
        assert catalog.scenarios_for(level), f"{track}/{level} thieu scenario"


@pytest.mark.parametrize("track", list_tracks())
def test_every_topic_has_distinct_concepts(track):
    for topic in load_catalog(track).topics:
        concepts = [c.lower() for c in topic.key_concepts]
        assert len(set(concepts)) == len(concepts), topic.id


def test_unknown_track_raises():
    with pytest.raises(CatalogError):
        load_catalog("cobol_backend")
