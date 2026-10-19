import shutil

import pytest

from pipeline.settings import canonical_embedding_model
from pipeline.topic_catalog_reader import CatalogError, load_topic_categories


def test_reads_topics_and_skips_scenarios(sample_catalog_dir):
    topics = load_topic_categories([sample_catalog_dir])
    assert topics == {"smp.core.event-loop": "Backend", "smp.data.sql-index": "Database"}
    assert "scn.smp.cache-stampede" not in topics


def test_duplicate_topic_id_across_dirs_is_error(sample_catalog_dir, tmp_path):
    shutil.copy(sample_catalog_dir / "sample_track.yaml", tmp_path / "copy.yaml")
    with pytest.raises(CatalogError, match="trung"):
        load_topic_categories([sample_catalog_dir, tmp_path])


def test_empty_dir_is_error(tmp_path):
    with pytest.raises(CatalogError):
        load_topic_categories([tmp_path])


@pytest.mark.parametrize(
    "name", ["openai/text-embedding-3-small", "text-embedding-3-small", " openai/text-embedding-3-small "]
)
def test_canonical_embedding_model_strips_provider_prefix(name):
    assert canonical_embedding_model(name) == "text-embedding-3-small"


def test_hard_topic_ids_keep_middle_and_senior_topics():
    from pipeline.topic_catalog_reader import hard_topic_ids

    catalog = [
        {"id": "a", "levels": "fresher, junior"},
        {"id": "b", "levels": "junior, middle"},
        {"id": "c", "levels": "senior"},
    ]
    assert hard_topic_ids(catalog) == {"b", "c"}


def test_load_topics_carries_levels(sample_catalog_dir):
    from pipeline.topic_catalog_reader import load_topics

    assert {t["id"]: t["levels"] for t in load_topics([sample_catalog_dir])} == {
        "smp.core.event-loop": "junior, middle",
        "smp.data.sql-index": "middle",
    }
