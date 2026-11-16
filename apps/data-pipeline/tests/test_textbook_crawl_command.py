"""T013: crawl-textbook qua main() voi fetcher gia (monkeypatch make_fetchers): ghi file, 0 trang -> 1, chan -> 4."""
import json

import pytest

from pipeline import textbook_crawl_command
from pipeline.__main__ import main
from textbook_command_fixtures import LOCKING, SOURCE_ID, textbook_env  # noqa: F401  (fixture)

HTML = (
    '<html><body><div id="content"><h1>Locking</h1><p>Intro paragraph.</p><h2>Row locks</h2>'
    "<p>A row level lock stops two concurrent transactions from updating the same order at once.</p>"
    "</div></body></html>"
)


@pytest.fixture()
def fake_fetchers(monkeypatch):
    """fake_fetchers(table, blocked=False): fetch_html tra theo {url: html}, URL khac -> None; ghi lai cac URL da goi."""

    def install(table, blocked=False):
        calls = []

        def fetch_html(url):
            calls.append(url)
            return table.get(url)

        monkeypatch.setattr(textbook_crawl_command, "make_fetchers",
                            lambda source, delay, render, count: (fetch_html, None, lambda: blocked, lambda: None))
        return calls

    return install


def _raw_files(env):
    return list((env.raw_dir / SOURCE_ID).glob("*.jsonl")) if (env.raw_dir / SOURCE_ID).exists() else []


def test_crawl_writes_one_jsonl_line_per_fetched_page_and_counts_skips(textbook_env, fake_fetchers, capsys):
    calls = fake_fetchers({LOCKING: HTML})
    assert main(["crawl-textbook", "--source", SOURCE_ID]) == 0
    files = _raw_files(textbook_env)
    assert len(files) == 1 and files[0].name.endswith("Z.jsonl") and ":" not in files[0].name
    rows = [json.loads(line) for line in files[0].read_text(encoding="utf-8").splitlines()]
    assert [r["url"] for r in rows] == [LOCKING] and rows[0]["source_id"] == SOURCE_ID
    assert ["Row locks"] in [s["heading_path"] for s in rows[0]["sections"]]
    assert len(calls) == 3  # 3 URL status use trong manifest, moi URL mot lan
    out = capsys.readouterr().out
    assert "3 trang trong manifest, 1 tai duoc, 2 bo" in out and "fetch_failed: 2" in out


def test_zero_pages_exits_one_and_writes_no_file(textbook_env, fake_fetchers, capsys):
    fake_fetchers({})
    assert main(["crawl-textbook", "--source", SOURCE_ID]) == 1
    assert _raw_files(textbook_env) == []
    assert "khong tai duoc trang nao" in capsys.readouterr().err


def test_blocked_host_exits_four_before_zero_page_check_and_writes_no_file(textbook_env, fake_fetchers):
    fake_fetchers({LOCKING: HTML}, blocked=True)
    assert main(["crawl-textbook", "--source", SOURCE_ID]) == 4
    assert _raw_files(textbook_env) == []


def test_unknown_source_and_broken_manifest_exit_one_without_fetching(textbook_env, fake_fetchers):
    calls = fake_fetchers({LOCKING: HTML})
    assert main(["crawl-textbook", "--source", "nope"]) == 1
    (textbook_env.sources_dir / "scenario-queries.yaml").write_text("scn.unknown: {}\n", encoding="utf-8")
    assert main(["crawl-textbook", "--source", SOURCE_ID]) == 1
    assert calls == []
