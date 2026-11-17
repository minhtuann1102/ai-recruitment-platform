"""T033: coverage-textbook — dem doan theo nguon / track / tinh huong, gaps, kiem tra tu khoa, --db (vector gia), --strict."""
import json

import yaml
from textbook_review_fixtures import SOURCE, make_record, textbook_env, write_processed  # noqa: F401

from pipeline.__main__ import main
from pipeline.settings import ConfigError
from pipeline.textbook_coverage_vector_check import vector_hits

BE, FE = "scn.be.orders", "scn.fe.dashboard"
BE_TERMS = "order API transactions row locking unique constraints design"  # trung query_en cua fixture
FE_QUERY = "render dashboard widgets from client state with memoization and virtualized lists"
FE_TERMS = "render dashboard widgets client state memoization virtualized lists"


def be_record(n, **kw):
    return make_record(n, content=f"Locking > Orders {n}\n\n{BE_TERMS} number{n}", **kw)


def fe_record(n):
    return make_record(100 + n, content=f"State > Dashboard {n}\n\n{FE_TERMS} item{n}", scenarios=(FE,),
                       category="Frontend", tracks=("fe_track",))


def add_fe_query(env):
    queries = yaml.safe_load((env.sources / "scenario-queries.yaml").read_text(encoding="utf-8"))
    queries[FE] = {"query_en": FE_QUERY, "terms": ["state", "memo", "list"]}
    (env.sources / "scenario-queries.yaml").write_text(yaml.safe_dump(queries), encoding="utf-8")


def run_coverage(env, *extra):
    code = main(["coverage-textbook", *extra])
    report_path = env.processed / "coverage-report.json"
    return code, json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else None


def test_counts_chunks_per_source_track_and_scenario(textbook_env, capsys):
    write_processed(textbook_env, [be_record(1), be_record(2), be_record(3), make_record(9, scenarios=(), content="Docs > Intro\n\nunrelated words")])
    code, report = run_coverage(textbook_env)
    assert code == 0
    assert report["scenarios"][BE]["chunks"] == 3 and report["scenarios"][FE]["chunks"] == 0
    assert report["tracks"]["be_track"] == {"official_sources": 1, "chunks": 4}
    assert report["tracks"]["fe_track"]["chunks"] == 0
    source = next(s for s in report["sources"] if s["source_id"] == SOURCE)
    assert source["chunks"] == 4 and source["license"] == "MIT" and source["license_class"] == "open"
    assert report["totals"]["chunks"] == 4 and report["totals"]["ratio_ge1"] == 0.5 and report["totals"]["ratio_ge3"] == 0.5
    assert "scn.be.orders" in capsys.readouterr().out


def test_zero_and_under_three_chunk_scenarios_land_in_gaps(textbook_env):
    write_processed(textbook_env, [be_record(1), be_record(2)])
    _, report = run_coverage(textbook_env)
    assert report["gaps"]["zero_chunks"] == [FE]
    assert report["gaps"]["under_3_chunks"] == [BE]
    assert "vector_miss" not in report["gaps"] and "vector_hit" not in report["scenarios"][BE]


def test_keyword_hit_gives_rank_and_retrieval_miss_goes_to_gaps(textbook_env):
    hit_first = be_record(1)
    write_processed(textbook_env, [hit_first, be_record(2), be_record(3)])
    _, report = run_coverage(textbook_env)
    assert report["scenarios"][BE]["keyword_hit"] and report["scenarios"][BE]["first_hit_rank"] in (1, 2, 3)

    # 3 doan khong gan ma tinh huong nhung khop truy van hon -> doan mang ma khong nam trong top 3
    carrying = [make_record(n, scenarios=(BE,), content=f"Notes > Misc {n}\n\ngardening tomatoes watering schedule {n}") for n in range(3)]
    others = [make_record(10 + n, scenarios=(), content=f"Locking > Other {n}\n\n{BE_TERMS} filler{n}") for n in range(3)]
    write_processed(textbook_env, carrying + others)
    _, report = run_coverage(textbook_env)
    assert not report["scenarios"][BE]["keyword_hit"] and report["scenarios"][BE]["first_hit_rank"] is None
    assert BE in report["gaps"]["retrieval_miss"]


def test_keyword_check_only_looks_at_track_main_category_and_system_design(textbook_env):
    wrong = [be_record(n, category="Frontend") for n in range(3)]
    write_processed(textbook_env, wrong)
    _, report = run_coverage(textbook_env)
    assert not report["scenarios"][BE]["keyword_hit"] and BE in report["gaps"]["retrieval_miss"]
    write_processed(textbook_env, [be_record(n, category="System Design") for n in range(3)])
    _, report = run_coverage(textbook_env)
    assert report["scenarios"][BE]["keyword_hit"]


def test_strict_exits_one_with_gaps_and_zero_when_sc001_and_sc004_hold(textbook_env, capsys):
    write_processed(textbook_env, [be_record(n) for n in range(3)])
    assert main(["coverage-textbook"]) == 0  # khong strict: luon 0
    assert run_coverage(textbook_env, "--strict")[0] == 1
    assert "SC-001" in capsys.readouterr().err
    add_fe_query(textbook_env)
    write_processed(textbook_env, [be_record(n) for n in range(3)] + [fe_record(n) for n in range(3)])
    code, report = run_coverage(textbook_env, "--strict")
    assert code == 0 and report["totals"]["sc001"] and report["totals"]["sc004"]
    assert report["gaps"] == {"zero_chunks": [], "under_3_chunks": [], "retrieval_miss": []}


def test_no_processed_files_reports_everything_as_gap_and_strict_fails(textbook_env):
    code, report = run_coverage(textbook_env)
    assert code == 0 and report["totals"]["chunks"] == 0 and set(report["gaps"]["zero_chunks"]) == {BE, FE}
    assert run_coverage(textbook_env, "--strict")[0] == 1


def test_db_flag_adds_vector_hit_and_vector_miss_and_counts_for_strict(textbook_env, monkeypatch):
    add_fe_query(textbook_env)
    write_processed(textbook_env, [be_record(n) for n in range(3)] + [fe_record(n) for n in range(3)])
    seen = {}

    def fake_vector_check(items):
        seen["items"] = items
        return {BE: True, FE: False}

    monkeypatch.setattr("pipeline.textbook_coverage_command.run_vector_check", fake_vector_check)
    code, report = run_coverage(textbook_env, "--db")
    assert code == 0 and report["scenarios"][BE]["vector_hit"] and not report["scenarios"][FE]["vector_hit"]
    assert report["gaps"]["vector_miss"] == [FE] and report["totals"]["vector_hit_ratio"] == 0.5
    assert {scn: cats for scn, _, cats in seen["items"]} == {BE: ["Backend", "System Design"], FE: ["Frontend", "System Design"]}
    assert run_coverage(textbook_env, "--db", "--strict")[0] == 1  # vector 50% < 80% -> khong dat SC-004


def test_db_flag_config_error_exits_two_and_writes_no_report(textbook_env, monkeypatch, capsys):
    def boom(items):
        raise ConfigError("thieu AI_DB_URL")

    monkeypatch.setattr("pipeline.textbook_coverage_command.run_vector_check", boom)
    code, report = run_coverage(textbook_env, "--db")
    assert code == 2 and report is None
    assert "AI_DB_URL" in capsys.readouterr().err


class FakeCursor:
    def __init__(self, rows_by_vector):
        self.rows_by_vector, self.calls, self._rows = rows_by_vector, [], []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params):
        self.calls.append((sql, params))
        self._rows = self.rows_by_vector[params[3]]

    def fetchall(self):
        return self._rows


class FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor


def test_vector_hits_query_textbook_rows_in_two_categories_and_match_scenario_code():
    cursor = FakeCursor({"[1.0,0.0]": [([BE],), (["scn.other"],)], "[0.0,1.0]": [(None,), ("[]",)]})
    items = [(BE, "q1", ["Backend", "System Design"]), (FE, "q2", ["Frontend", "System Design"])]
    hits = vector_hits(FakeConn(cursor), items, [[1.0, 0.0], [0.0, 1.0]], "model-x")
    assert hits == {BE: True, FE: False}
    sql, params = cursor.calls[0]
    assert "category = ANY(%s)" in sql and "source_type = %s" in sql
    assert params == ["textbook", "model-x", ["Backend", "System Design"], "[1.0,0.0]", 3]
