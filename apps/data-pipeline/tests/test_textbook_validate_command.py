"""validate-textbook va viec dang ky 7 lenh textbook vao CLI (T009): ma thoat, bang in, lenh chua lam tra 2."""
import shutil

import pytest
import yaml

from pipeline import settings
from pipeline.__main__ import main


@pytest.fixture()
def sources_dir(tmp_path, monkeypatch, fixtures_dir):
    """Thu muc manifest rong trong tmp_path, catalog nho cua fixture (be_track 1 tinh huong, fe_track 1 tinh huong)."""
    directory = tmp_path / "textbook_sources"
    directory.mkdir()
    monkeypatch.setattr(settings, "TEXTBOOK_SOURCES_DIR", directory)
    monkeypatch.setattr(settings, "catalog_dir", lambda: fixtures_dir / "textbook" / "catalog_manifest")
    return directory


def copy_valid(fixtures_dir, directory):
    for name in ("valid-source.yaml", "scenario-queries.yaml"):
        shutil.copy(fixtures_dir / "textbook" / "sources" / name, directory / name)


def test_empty_manifest_dir_says_no_sources_and_exits_zero(sources_dir, capsys):
    assert main(["validate-textbook"]) == 0
    out = capsys.readouterr().out
    assert "chua co nguon" in out and "0 loi" in out
    assert main(["validate-textbook", "--strict"]) == 0  # khong co nguon thi khong co canh bao


def test_valid_manifest_prints_three_tables_and_exits_zero(sources_dir, fixtures_dir, capsys):
    copy_valid(fixtures_dir, sources_dir)
    assert main(["validate-textbook", "--strict"]) == 0
    out = capsys.readouterr().out
    assert "track x nguon chinh thuc x trang" in out and "tinh huong x trang" in out and "nguon x giay phep" in out
    assert "scn.be.orders" in out and "be_track" in out and "MIT" in out and "open" in out
    assert "0 loi, 0 canh bao" in out


def test_warning_exits_zero_without_strict_and_one_with_strict(sources_dir, fixtures_dir, capsys):
    copy_valid(fixtures_dir, sources_dir)
    (sources_dir / "scenario-queries.yaml").write_text("{}\n", encoding="utf-8")  # thieu dong truy van -> canh bao
    assert main(["validate-textbook"]) == 0
    assert "[canh bao]" in capsys.readouterr().out
    assert main(["validate-textbook", "--strict"]) == 1


def test_error_exits_one_and_names_file(sources_dir, fixtures_dir, capsys):
    copy_valid(fixtures_dir, sources_dir)
    doc = yaml.safe_load((sources_dir / "valid-source.yaml").read_text(encoding="utf-8"))
    doc["pages"][0]["scenarios"] = []
    (sources_dir / "valid-source.yaml").write_text(yaml.safe_dump(doc), encoding="utf-8")
    assert main(["validate-textbook"]) == 1
    assert "[loi] valid-source.yaml https://docs.example.org/guide/locking.html" in capsys.readouterr().out


def test_unreadable_yaml_exits_one(sources_dir, capsys):
    (sources_dir / "broken.yaml").write_text("source_id: [unclosed\n", encoding="utf-8")
    assert main(["validate-textbook"]) == 1
    assert "broken.yaml" in capsys.readouterr().err


@pytest.mark.parametrize(
    "argv",
    [
        ["crawl-textbook", "--source", "postgresql"],
        ["process-textbook"],
        ["review-textbook-prepare", "--source", "postgresql", "--batch-size", "10", "--seed", "7"],
        ["review-textbook-score", "--source", "postgresql"],
        ["coverage-textbook", "--db", "--strict"],
        ["index-textbook", "--source", "postgresql"],
    ],
)
def test_commands_not_implemented_yet_exit_two_with_message(argv, capsys):
    assert main(argv) == 2
    assert f"lenh '{argv[0]}' chua duoc hien thuc" in capsys.readouterr().err


@pytest.mark.parametrize("command", ["crawl-textbook", "review-textbook-prepare", "review-textbook-score", "index-textbook"])
def test_source_option_is_required_for_single_source_commands(command):
    with pytest.raises(SystemExit):
        main([command])
