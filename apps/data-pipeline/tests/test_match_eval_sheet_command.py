"""T031 (spec 017 US3): match-eval-sheet voi client ai-service gia. Bang soat KHONG co diem / thu hang cua he thong.

Moi thu tu nao cua response deu cho cung mot bang (JD xep ngau nhien theo seed co dinh, khong theo diem).
Du lieu: match_eval_command_fixtures (client gia nhet chuoi "LEAK-*" vao truong title / matched_skills de bat ro ri).
"""
import json
import re

from match_eval_command_fixtures import FILTERED, POOL, env  # noqa: F401  (fixture)
from pipeline.match_eval_client import AiServiceError

SHEET, TEMPLATE, PAIR_CHECK = "sheet-2026-11-01.md", "labels.template.json", "pair-set-check.json"


def read(env, name):
    return (env.sheet_dir / name).read_text(encoding="utf-8")


def jd_order(text, cv_id):
    """Thu tu cac jd_id trong muc cua mot CV (moi JD la mot tieu de ### <jd_id> — <title>)."""
    block = text.split(f"## CV {cv_id}")[1].split("\n## CV ")[0]
    return re.findall(r"^### (\S+) ", block, flags=re.M)


def test_sheet_lists_each_cv_with_its_filtered_jds_and_jd_details(env):
    assert env.run_sheet() == 0
    text = read(env, SHEET)
    assert "## CV cv-a" in text and "## CV cv-b" in text
    assert sorted(jd_order(text, "cv-a")) == sorted(FILTERED["cv-a"]) and sorted(jd_order(text, "cv-b")) == sorted(FILTERED["cv-b"])
    assert "Tiêu đề x:3" in text and "Mid" in text and "java, spring-boot" in text  # tieu de, level, ky nang lay tu jd_normalized
    assert "MOTA-x:3" in text and "YEUCAU-x:3" in text  # noi dung JD day du (research R9)
    assert "PHUCLOI" not in text  # quyen loi khong giup gan nhan
    assert "Ghi chú cv-a" in text and "Vai tro cv-a" in text  # thong tin CV


def test_sheet_has_no_system_score_rank_or_scorer_output(env):
    assert env.run_sheet() == 0
    text = read(env, SHEET)
    assert "LEAK" not in text  # title / matched_skills / missing_skills cua response khong duoc vao bang
    lowered = text.lower()
    for word in ("score", "cosine", "skill_match", "level_fit", "rank", "hạng", "matched", "missing"):
        assert word not in lowered, word
    assert not re.search(r"\b0\.\d{2,}\b", text)  # khong co con so diem nao cua response (0.209, 0.9 ...)
    assert not re.search(r"^### \d+[.)]", text, flags=re.M)  # tieu de khong danh so (tranh doc nham la thu hang)


def test_sheet_is_identical_whatever_order_the_service_answers(env):
    assert env.run_sheet() == 0
    first = read(env, SHEET)
    env.client.reverse = True
    assert env.run_sheet() == 0
    assert read(env, SHEET) == first
    env.client.filtered = {k: list(reversed(v)) for k, v in FILTERED.items()}
    assert env.run_sheet() == 0
    assert read(env, SHEET) == first


def test_template_has_every_filtered_pair_unlabeled(env):
    assert env.run_sheet() == 0
    template = json.loads(read(env, TEMPLATE))
    assert {cv: sorted(pairs) for cv, pairs in template["labels"].items()} == {cv: sorted(ids) for cv, ids in FILTERED.items()}
    assert all(v is None for pairs in template["labels"].values() for v in pairs.values())
    assert "score" not in json.dumps(template)


def test_pair_set_comparison_equal_when_labels_match_endpoint(env, capsys):
    assert env.run_sheet() == 0
    check = json.loads(read(env, PAIR_CHECK))
    assert check["equal"] is True and check["filtered_pairs"] == 11 and check["labeled_pairs"] == 11
    assert check["missing"] == [] and check["extra"] == []
    assert "equal" in capsys.readouterr().out.lower()


def test_pair_set_comparison_lists_missing_and_extra_and_still_exits_0(env, capsys):
    labels = json.loads((env.seeds / "labels.json").read_text(encoding="utf-8"))
    del labels["labels"]["cv-a"]["x:3"]  # qua loc nhung chua co nhan
    labels["labels"]["cv-b"]["x:6"] = 0  # co nhan nhung khong qua loc
    env.write_seed("labels.json", labels)
    assert env.run_sheet() == 0
    check = json.loads(read(env, PAIR_CHECK))
    assert check["equal"] is False and check["missing"] == [["cv-a", "x:3"]] and check["extra"] == [["cv-b", "x:6"]]
    out = capsys.readouterr().out
    assert "missing 1" in out and "extra 1" in out


def test_sheet_works_before_labels_exist(env):
    (env.seeds / "labels.json").unlink()
    assert env.run_sheet() == 0
    check = json.loads(read(env, PAIR_CHECK))
    assert check["equal"] is None and "labels.json" in check["note"]


def test_cv_without_any_filtered_jd_exits_1(env, capsys):
    env.client.filtered = {"cv-a": POOL[:], "cv-b": []}
    assert env.run_sheet() == 1
    assert "cv-b" in capsys.readouterr().err and not (env.sheet_dir / SHEET).exists()


def test_mock_service_gets_a_hint_and_exit_1(env, capsys):
    env.client.filtered = {"cv-a": [], "cv-b": []}  # che do mock: chi muc mau, job_ids that khong khop
    env.client.mock = True
    assert env.run_sheet() == 1
    assert "mock" in capsys.readouterr().err.lower()


def test_unreachable_service_exits_2(env):
    env.client.fail = AiServiceError("khong ket noi duoc")
    assert env.run_sheet() == 2 and not env.sheet_dir.exists()


def test_missing_input_files_exit_1(env):
    (env.seeds / "pool.json").unlink()
    assert env.run_sheet() == 1 and env.client.calls == []


def test_sheet_requests_use_pool_as_job_ids_and_max_page(env):
    assert env.run_sheet() == 0
    assert [c["job_ids"] for c in env.client.calls] == [POOL, POOL] and {c["page_size"] for c in env.client.calls} == {50}
