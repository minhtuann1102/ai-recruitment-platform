"""Fixture chung cho test match-eval / match-eval-sheet (spec 017 US3): bo du lieu nho o tmp_path + client gia.

Bo du lieu: 2 CV (cv-a qua loc 6 JD, cv-b qua loc 5 JD: x:6 bi loc), pool 6 JD, nhan da tinh tay (xem test).
Test import `env` voi `# noqa: F401  (fixture)`, giong jd_match_command_fixtures.
"""
import json

import pytest

from match_eval_fakes import FakeMatchClient
from pipeline import match_eval_command as eval_command
from pipeline import match_eval_sheet_command as sheet_command
from pipeline.__main__ import main
from pipeline.settings import MatchEvalSettings

POOL = ["x:1", "x:2", "x:3", "x:4", "x:5", "x:6"]
FILTERED = {"cv-a": POOL[:], "cv-b": POOL[:5]}
LABELS = {"cv-a": {"x:1": 2, "x:2": 0, "x:3": 1, "x:4": 0, "x:5": 2, "x:6": 0},
          "cv-b": {"x:1": 0, "x:2": 1, "x:3": 0, "x:4": 2, "x:5": 0}}
LANGUAGES = {"x:1": "vi", "x:2": "vi", "x:3": "en", "x:4": "en", "x:5": "mixed", "x:6": "vi"}
LABEL_META = {"labeled_by": "llm:test (all pairs)", "labeled_at": "2026-11-22", "method": "llm+de-blind-20 (final = llm)",
              "rubric": "label-rubric.md", "pair_set": "replica", "final_source": {"llm": 11},
              "agreement": {"n_blind": 48, "weighted_kappa_quadratic": 0.718, "weighted_kappa_before_rubric_fix": 0.659}}


def make_cv(cv_id: str, level: str = "junior") -> dict:
    profile = {"schema_version": 1, "headline": cv_id, "skills": [{"name": "Java", "category": "language", "evidence": "work"}],
               "experiences": [{"role": f"Vai tro {cv_id}", "company_type": "outsource", "start": "2025-01", "end": None,
                                "tech": ["Java"], "summary": f"Mo ta kinh nghiem {cv_id}"}], "projects": []}
    return {"cv_id": cv_id, "track": "java_backend", "level": level, "note": f"Ghi chú {cv_id}", "cv_profile": profile}


def make_jd(jd_id: str) -> dict:
    return {"jd_id": jd_id, "title": f"Tiêu đề {jd_id}", "level": "Mid", "skills": ["java", "spring-boot"], "group": "backend",
            "language": LANGUAGES[jd_id], "deadline": "2026-12-01", "company": "Cong ty Test", "synthetic": jd_id == "x:6",
            "sections": {"description": f"MOTA-{jd_id}", "requirements": f"YEUCAU-{jd_id}", "benefits": f"PHUCLOI-{jd_id}"}}


class Env:
    """Ghi file dau vao vao tmp_path, gan client gia, tro cac duong dan ra tmp_path (khong cham data that)."""

    def __init__(self, tmp_path):
        self.seeds, self.jd_path = tmp_path / "seeds", tmp_path / "jd_normalized.jsonl"
        self.processed, self.runs = tmp_path / "processed", tmp_path / "processed" / "match_eval"
        self.out, self.sheet_dir = tmp_path / "eval-results.md", tmp_path / "sheets"
        self.seeds.mkdir()
        self.processed.mkdir()
        self.client = FakeMatchClient(FILTERED, LABELS)
        self.write_seed("cvs.json", [make_cv("cv-a"), make_cv("cv-b", "senior")])
        self.write_seed("pool.json", {"as_of": "2026-11-01", "jd_ids": POOL})
        self.write_seed("labels.json", {**LABEL_META, "labels": LABELS})
        self.write_jd(*[make_jd(j) for j in POOL])

    def write_seed(self, name, data):
        (self.seeds / name).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def write_jd(self, *jds):
        self.jd_path.write_text("".join(json.dumps(j, ensure_ascii=False) + "\n" for j in jds), encoding="utf-8")

    def write_index_report(self, name, tokens, embedded=36, records=36, cleanup="done"):
        """Run report index-jd-match: ban day du = embedded == chunks_out va cleanup 'done' (khong phai --limit / loi embed)."""
        report = {"command": "index-jd-match", "chunks_out": records,
                  "index": {"embedding_tokens": tokens, "embedded": embedded, "cleanup": cleanup}}
        (self.processed / name).write_text(json.dumps(report), encoding="utf-8")

    def run_eval(self, *flags):
        return main(["match-eval", "--out", str(self.out), *flags])

    def run_sheet(self, *flags):
        return main(["match-eval-sheet", "--out", str(self.sheet_dir), *flags])

    def run_json(self):
        paths = sorted(self.runs.glob("run-*.json"))
        assert len(paths) == 1, paths
        return json.loads(paths[0].read_text(encoding="utf-8"))


@pytest.fixture()
def env(tmp_path, monkeypatch):
    e = Env(tmp_path)
    settings = MatchEvalSettings(base_url="http://fake", token="tok", embedding_price_per_1m=0.02)
    for module in (eval_command, sheet_command):
        monkeypatch.setattr(module, "SEEDS_DIR", e.seeds)
        monkeypatch.setattr(module, "JD_NORMALIZED_PATH", e.jd_path)
        monkeypatch.setattr(module, "require_match_eval_settings", lambda: settings)
        monkeypatch.setattr(module, "MatchClient", lambda s: e.client)
    monkeypatch.setattr(eval_command, "PROCESSED_DIR", e.processed)
    monkeypatch.setattr(eval_command, "RUN_DIR", e.runs)
    return e
