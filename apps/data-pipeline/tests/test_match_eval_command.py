"""T031 (spec 017 US3): match-eval voi client ai-service gia. Hoan toan offline; moi duong dan tro ra tmp_path.

Du lieu va ky vong tinh tay: match_eval_command_fixtures (cv-a 6 JD, cv-b 5 JD; full = xep ly tuong nen nDCG@5 = 1,
skill_match xep nguoc thu tu job_id, cosine xep theo thu tu job_id).
"""
import json
import math
from pathlib import Path

import pytest

from match_eval_command_fixtures import env  # noqa: F401  (fixture)
from pipeline import match_eval_command
from pipeline.__main__ import build_parser
from pipeline.match_eval_client import AiServiceError
from pipeline.settings import ConfigError

SECTIONS = ["## 1. Bộ dữ liệu", "## 2. Chất lượng gợi ý", "## 3. Theo ngôn ngữ", "## 4. Độ trễ", "## 5. Chi phí embedding", "## 6. Hạn chế"]


def d(labels):
    return sum(g / math.log2(i + 2) for i, g in enumerate(labels[:5]))


def test_happy_path_writes_markdown_with_every_section_and_raw_json(env, capsys):
    assert env.run_eval("--rounds", "2") == 0
    text = env.out.read_text(encoding="utf-8")
    positions = [text.index(section) for section in SECTIONS]
    assert positions == sorted(positions)
    for needle in ("2 CV", "6 JD", "(1 tổng hợp", "11 cặp", "2026-11-01", "text-embedding-3-small", "P@5", "nDCG@5", "p50", "p95", "SC-001",
                   "SC-002", "trùng đúng tập đã gán nhãn"):
        assert needle in text
    assert "SC-004" in text.split("## 6.")[1] and "do test của ai-service" not in text  # khong tuyen bo dieu lenh khong kiem
    raw = env.run_json()
    assert {"dataset", "quality", "language_split", "latency", "cost"} <= set(raw)
    assert capsys.readouterr().out.encode("ascii")  # stdout ASCII: console Windows (cp1252) khong vo


def test_quality_per_method_matches_hand_computation(env):
    assert env.run_eval("--rounds", "1") == 0
    quality = env.run_json()["quality"]
    assert quality["full"]["ndcg_at_5"] == pytest.approx(1.0) and quality["full"]["p_at_5"] == pytest.approx(0.5)
    assert quality["skill_match"]["p_at_5"] == pytest.approx(0.4)  # moi CV 2/5
    assert quality["cosine"]["p_at_5"] == pytest.approx(0.5)  # cv-a 3/5, cv-b 2/5
    cv_a = d([2, 0, 1, 0, 2, 0]) / d([2, 2, 1, 0, 0])
    cv_b = d([0, 1, 0, 2, 0]) / d([2, 1, 0, 0, 0])
    assert quality["cosine"]["ndcg_at_5"] == pytest.approx((cv_a + cv_b) / 2)
    assert quality["skill_match"]["ndcg_at_5"] < quality["cosine"]["ndcg_at_5"] < quality["full"]["ndcg_at_5"]
    verdict = env.out.read_text(encoding="utf-8").split("SC-001")[1].split("\n")[0]  # full nDCG@5 > skill_match
    assert "đạt" in verdict and "không đạt" not in verdict


def test_language_split_by_jd_language_over_each_cvs_subset(env):
    assert env.run_eval("--rounds", "1") == 0
    split = env.run_json()["language_split"]
    same, cross = split["same"]["full"], split["cross"]["full"]  # same = JD vi (x:1 x:2 x:6), cross = en / mixed (x:3 x:4 x:5)
    assert same["p_at_5"] == pytest.approx((1 / 3 + 1 / 2) / 2)  # tap con < 5 JD: mau so = so JD
    assert (same["n_cv"], same["n_pairs"]) == (2, 5)
    assert cross["p_at_5"] == pytest.approx((2 / 3 + 1 / 3) / 2) and (cross["n_cv"], cross["n_pairs"]) == (2, 6)
    text = env.out.read_text(encoding="utf-8")
    assert "cùng ngôn ngữ (JD vi)" in text and "khác ngôn ngữ (JD en/mixed)" in text and "theo từng CV" in text


def test_dataset_section_prints_labeling_method_agreement_and_llm_limitation(env):
    assert env.run_eval("--rounds", "1") == 0
    text = env.out.read_text(encoding="utf-8")
    for needle in ("llm+de-blind-20 (final = llm)", "llm:test (all pairs)", "0.718", "0.659", "48", "nhãn cuối là nhãn LLM"):
        assert needle in text, needle


def test_requests_use_pool_page_50_and_latency_rounds_run_with_and_without_job_ids(env):
    assert env.run_eval("--rounds", "2") == 0
    calls = env.client.calls
    assert len(calls) == 2 + 2 * 2 * 2  # qua trinh chat luong 1 cuoc / CV, roi rounds x CV x {co, khong job_ids}
    first = calls[0]
    assert first["job_ids"] == ["x:1", "x:2", "x:3", "x:4", "x:5", "x:6"] and first["page_size"] == 50
    assert (first["track"], first["level"], first["as_of"], first["page"]) == ("java_backend", "junior", "2026-11-01", 1)
    assert sum("job_ids" in c for c in calls[2:]) == 4 and sum("job_ids" not in c for c in calls[2:]) == 4
    latency = env.run_json()["latency"]
    for variant in ("with_job_ids", "without_job_ids"):
        assert latency[variant]["server_score_ms"]["n"] == 4 and latency[variant]["client_ms"]["n"] == 4
        assert latency[variant]["client_ms"]["p95"] >= latency[variant]["client_ms"]["p50"] > 100


def test_two_runs_give_the_same_quality_numbers(env, tmp_path):
    assert env.run_eval("--rounds", "1") == 0
    assert env.run_eval("--rounds", "1") == 0
    first, second = (json.loads(p.read_text(encoding="utf-8")) for p in sorted(env.runs.glob("run-*.json")))
    assert first["quality"] == second["quality"] and first["language_split"] == second["language_split"]


# ---- chi phi ----
def test_cost_uses_newest_index_report_with_tokens_and_ignores_other_reports(env):
    env.write_index_report("run-report-index-jd-match-20261121T000000Z.json", tokens=7200)
    env.write_index_report("run-report-index-jd-match-20261122T000000Z.json", tokens=0, embedded=0)  # chay lai: 0 token
    env.write_index_report("run-report-index-20261123T000000Z.json", tokens=999999)  # bao cao index Q&A, khong phai JD
    assert env.run_eval("--rounds", "1") == 0
    cost = env.run_json()["cost"]
    assert cost["index"]["embedding_tokens"] == 7200 and cost["index"]["source"] == "run-report-index-jd-match-20261121T000000Z.json"
    assert cost["index"]["usd"] == pytest.approx(7200 * 0.02 / 1_000_000)
    assert cost["request"]["mean_embedding_tokens"] == 200 and cost["request"]["usd"] == pytest.approx(200 * 0.02 / 1_000_000)
    assert "7200" in env.out.read_text(encoding="utf-8").split("## 5.")[1]


def test_cost_prefers_the_newest_full_index_run_over_a_newer_partial_one(env):
    env.write_index_report("run-report-index-jd-match-20261121T000000Z.json", tokens=7200)  # index day du: embed 36 / 36
    env.write_index_report("run-report-index-jd-match-20261122T000000Z.json", tokens=100, embedded=2)  # chay tang dan: chi 2 JD moi
    assert env.run_eval("--rounds", "1") == 0
    index = env.run_json()["cost"]["index"]
    assert index["embedding_tokens"] == 7200 and index["complete"] is True
    assert "không phải chi phí index đầy đủ" not in env.out.read_text(encoding="utf-8")


@pytest.mark.parametrize("embedded, cleanup", [(2, "done"), (36, "skipped (--limit)"), (30, "skipped (embed_errors > 0)")])
def test_cost_flags_index_runs_that_were_not_a_full_index(env, embedded, cleanup):
    env.write_index_report("run-report-index-jd-match-20261121T000000Z.json", tokens=100, embedded=embedded, cleanup=cleanup)
    assert env.run_eval("--rounds", "1") == 0
    assert env.run_json()["cost"]["index"]["complete"] is False
    section = env.out.read_text(encoding="utf-8").split("## 5.")[1]
    assert "không phải chi phí index đầy đủ" in section and f"embed {embedded} / 36 bản ghi" in section


def test_cost_with_only_a_rerun_report_says_nothing_was_embedded(env):
    env.write_index_report("run-report-index-jd-match-20261121T000000Z.json", tokens=0, embedded=0)
    assert env.run_eval("--rounds", "1") == 0
    assert "không embed bản ghi nào" in env.out.read_text(encoding="utf-8").split("## 5.")[1]


def test_missing_index_report_is_reported_not_fatal(env):
    assert env.run_eval("--rounds", "1") == 0
    assert env.run_json()["cost"]["index"]["embedding_tokens"] is None
    assert "chưa có run report index-jd-match" in env.out.read_text(encoding="utf-8")


# ---- ma thoat 4: degraded / mock ----
@pytest.mark.parametrize("breaker, expected_calls", [("degraded_first", 1), ("degraded_latency", 3), ("mock", 1)])
def test_degraded_or_mock_response_stops_with_code_4_and_writes_nothing(env, capsys, breaker, expected_calls):
    if breaker == "mock":
        env.client.mock = True
    else:
        env.client.degraded_from = 1 if breaker == "degraded_first" else 3  # cuoc 3 la cuoc dau tien cua vong do tre
    assert env.run_eval("--rounds", "2") == 4
    assert not env.out.exists() and list(env.runs.glob("run-*.json")) == []
    assert len(env.client.calls) == expected_calls  # dung ngay, khong goi them
    err = capsys.readouterr().err.lower()
    assert ("mock" if breaker == "mock" else "degraded") in err and "cv-" in err


# ---- ma thoat 1: nhan ----
def test_missing_label_for_filtered_pair_exits_1_listing_pairs_before_latency_rounds(env, capsys):
    labels = json.loads((env.seeds / "labels.json").read_text(encoding="utf-8"))
    del labels["labels"]["cv-a"]["x:3"]
    env.write_seed("labels.json", labels)
    assert env.run_eval("--rounds", "3") == 1
    err = capsys.readouterr().err
    assert "thieu nhan" in err and "cv-a / x:3" in err
    assert len(env.client.calls) == 2  # chi qua trinh chat luong, chua do tre
    assert not env.out.exists() and list(env.runs.glob("run-*.json")) == []


def test_extra_label_outside_filtered_set_exits_1_listing_pairs(env, capsys):
    labels = json.loads((env.seeds / "labels.json").read_text(encoding="utf-8"))
    labels["labels"]["cv-b"]["x:6"] = 1  # x:6 khong qua loc voi cv-b
    env.write_seed("labels.json", labels)
    assert env.run_eval("--rounds", "1") == 1
    assert "nhan thua" in capsys.readouterr().err and not env.out.exists()


def test_invalid_labels_exit_1_without_calling_the_service(env):
    labels = json.loads((env.seeds / "labels.json").read_text(encoding="utf-8"))
    labels["labels"]["cv-a"]["x:1"] = 3
    env.write_seed("labels.json", labels)
    assert env.run_eval() == 1 and env.client.calls == []


def test_missing_cvs_file_exits_1(env):
    (env.seeds / "cvs.json").unlink()
    assert env.run_eval() == 1 and env.client.calls == []


def test_missing_jd_normalized_or_pool_jd_exits_1_pointing_to_process_jd(env, capsys):
    env.write_jd(*[json.loads(line) for line in env.jd_path.read_text(encoding="utf-8").splitlines()][:5])  # thieu x:6
    assert env.run_eval() == 1 and "x:6" in capsys.readouterr().err
    env.jd_path.unlink()
    assert env.run_eval() == 1 and "process-jd" in capsys.readouterr().err
    assert env.client.calls == []


def test_default_paths_are_repo_specs_file_and_pipeline_run_dir():
    parser = build_parser()
    out = parser.parse_args(["match-eval"]).out.replace("\\", "/")
    assert Path(out).is_absolute() and out.endswith("/specs/017-cv-jd-matching/eval-results.md") and "apps/data-pipeline" not in out
    assert parser.parse_args(["match-eval"]).rounds == 4
    sheet_out = parser.parse_args(["match-eval-sheet"]).out.replace("\\", "/")
    assert sheet_out.endswith("apps/data-pipeline/data/processed/match_eval")  # ngoai git, khong de lan voi nhan trung gian


def test_rounds_must_be_at_least_one(env):
    assert env.run_eval("--rounds", "0") == 1 and env.client.calls == []


# ---- ma thoat 2: ai-service ----
def test_unreachable_service_exits_2_and_writes_nothing(env, capsys):
    env.client.fail = AiServiceError("khong ket noi duoc http://fake")
    assert env.run_eval() == 2
    assert "http://fake" in capsys.readouterr().err and not env.out.exists()


def test_truncated_result_exits_2_not_misleading_extra_labels(env):
    env.client.total_override = 99  # total > so item tra ve
    assert env.run_eval() == 2


def test_config_error_exits_2(env, monkeypatch):
    def boom():
        raise ConfigError("EMBEDDING_PRICE_PER_1M khong hop le")

    monkeypatch.setattr(match_eval_command, "require_match_eval_settings", boom)
    assert env.run_eval() == 2
