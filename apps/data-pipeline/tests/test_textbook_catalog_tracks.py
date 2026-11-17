"""pipeline/textbook_catalog_tracks tren catalog that cua ai-service va catalog nho cho truong hop hoa."""
import pytest

from pipeline import settings
from pipeline.textbook_catalog_tracks import load_tracks
from pipeline.topic_catalog_reader import CatalogError


@pytest.fixture(scope="module")
def real_tracks():
    return load_tracks([settings.catalog_dir()])


def test_main_category_of_each_real_track(real_tracks):
    assert {t: real_tracks[t].main_category for t in real_tracks} == {
        "java_backend": "Backend",
        "nodejs_backend": "Backend",
        "python_backend": "Backend",
        "frontend_react": "Frontend",
        "devops_engineer": "DevOps",
        "ai_engineer": "AI",
    }


def test_real_catalog_has_28_scenarios_and_flash_sale_is_java(real_tracks):
    all_scenarios = [s for t in real_tracks.values() for s in t.scenario_ids]
    assert len(all_scenarios) == 28 and len(set(all_scenarios)) == 28
    assert "scn.java.flash-sale-inventory" in real_tracks["java_backend"].scenario_ids


def test_topic_categories_map_topic_id_to_category(real_tracks):
    assert real_tracks["java_backend"].topic_categories["java.data.sql-index-tuning"] == "Database"
    assert real_tracks["java_backend"].topic_categories["java.spring.transaction"] == "Backend"


def test_tie_takes_category_that_appears_first(fixtures_dir):
    tracks = load_tracks([fixtures_dir / "textbook" / "catalog_tie"])  # 2 Database + 2 Backend, Database dung truoc
    assert tracks["tie_track"].main_category == "Database"
    assert tracks["tie_track"].scenario_ids == ["scn.tie.one"]


def test_missing_track_field_and_empty_dir_are_catalog_errors(tmp_path):
    with pytest.raises(CatalogError, match="khong co file"):
        load_tracks([tmp_path])
    (tmp_path / "bad.yaml").write_text("topics:\n  - {id: x.y, category: Backend}\n", encoding="utf-8")
    with pytest.raises(CatalogError, match="track"):
        load_tracks([tmp_path])


def test_duplicate_track_and_topic_without_category_are_errors(tmp_path, fixtures_dir):
    src = (fixtures_dir / "textbook" / "catalog_tie" / "tie_track.yaml").read_text(encoding="utf-8")
    (tmp_path / "a.yaml").write_text(src, encoding="utf-8")
    (tmp_path / "b.yaml").write_text(src, encoding="utf-8")
    with pytest.raises(CatalogError, match="trung"):
        load_tracks([tmp_path])
    (tmp_path / "b.yaml").unlink()
    (tmp_path / "a.yaml").write_text("track: t\ntopics:\n  - {id: t.a}\n", encoding="utf-8")
    with pytest.raises(CatalogError, match="thieu id hoac category"):
        load_tracks([tmp_path])
