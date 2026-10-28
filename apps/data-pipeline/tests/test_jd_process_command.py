"""Lenh process-jd (spec 009 T028, contracts/pipeline-cli-jd.md): raw JSONL tu soan trong tmp_path, offline."""
import argparse
import json

import pytest

from pipeline import jd_process_command
from pipeline.__main__ import HANDLERS, build_parser
from pipeline.settings import SKILL_DICTIONARY_PATH

REPORT_KEYS = {
    "records_in", "rejected", "jd_out", "dedup_ratio", "chunks_out", "with_skill_ratio", "crawl_vs_synthetic",
    "distribution", "unknown_skills", "pii_remaining", "cells",
}


@pytest.fixture()
def paths(tmp_path, monkeypatch):
    raw_dir, processed = tmp_path / "raw" / "jd", tmp_path / "processed"
    monkeypatch.setattr(jd_process_command, "JD_RAW_DIR", raw_dir)
    monkeypatch.setattr(jd_process_command, "PROCESSED_DIR", processed)
    monkeypatch.setattr(jd_process_command, "JD_NORMALIZED_PATH", processed / "jd_normalized.jsonl")
    monkeypatch.setattr(jd_process_command, "JD_CHUNKS_PATH", processed / "jd_chunks.jsonl")
    monkeypatch.setattr(jd_process_command, "SKILL_DICTIONARY_PATH", SKILL_DICTIONARY_PATH)
    return raw_dir, processed


def _write(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")


@pytest.fixture()
def raw_files(paths, make_raw_jd):
    raw_dir, _ = paths
    contact = make_raw_jd("1002", title="Senior Java Developer", skills_raw=["Java", "Spring Boot"], description_text=(
        "Mô tả công việc\n- Xây dựng dịch vụ Java Spring Boot cho ngân hàng số Biển Xanh, xử lý giao dịch thời gian thực.\n"
        "Liên hệ: Anh Tuấn - 0987 654 321 - tuyendung@bienxanh-gia.vn\n"
        "Yêu cầu\n- 5 năm kinh nghiệm Java, Kafka, Microservices, hiểu Kubernetes.\n- Tiếng Anh đọc hiểu tài liệu."),
        location_raw=["Hà Nội"], experience_raw="60 months")
    _write(raw_dir / "itviec" / "20261027T030000Z.jsonl", [make_raw_jd("1001"), contact])
    _write(raw_dir / "careerlink" / "20261027T040000Z.jsonl", [
        make_raw_jd("C9", source="careerlink", skills_raw=..., salary_raw=None),  # trung noi dung itviec:1001
        make_raw_jd("C10", source="careerlink", title="Nhân viên kế toán tổng hợp", skills_raw=...,
                    description_text="Hạch toán sổ sách, lập báo cáo thuế cho cửa hàng thời trang Hoa Cúc. " * 4),
    ])
    _write(raw_dir / "synthetic" / "20261027T050000Z.jsonl", [make_raw_jd(
        "syn-frontend-Junior-Đà Nẵng-1", source="synthetic", url=None, synthetic=True, title="Junior React Developer",
        company="Công ty Hư cấu Mây Trắng", skills_raw=["React", "TypeScript"], location_raw=["Đà Nẵng"],
        experience_raw=None, description_text=(
            "Mô tả công việc\n- Xây dựng giao diện quản lý kho bằng React, TypeScript và Tailwind CSS.\n"
            "Yêu cầu\n- Hiểu HTML, CSS, gọi RESTful API; biết Redux là lợi thế.\n"
            "Quyền lợi\n- Lương tháng 13, làm việc thứ 2 đến thứ 6, đào tạo nội bộ hằng quý."))])
    return raw_dir


def _run():
    return jd_process_command.run_process_jd(argparse.Namespace(command="process-jd"))


def _latest_report(processed):
    return json.loads(sorted(processed.glob("jd-report-*.json"))[-1].read_text(encoding="utf-8"))


def test_process_counts_report_and_scrubs_pii(raw_files, paths, capsys):
    _, processed = paths
    assert _run() == 0
    report = _latest_report(processed)
    assert REPORT_KEYS <= set(report)
    assert report["records_in"] == {
        "crawl": 4, "synthetic": 1, "by_source": {"careerlink": 2, "itviec": 2, "synthetic": 1},
    }
    assert report["rejected"] == {"not_it": 1, "missing_field": 0, "duplicate": 1}
    assert report["rejected_by_source"] == {"careerlink": {"duplicate": 1, "not_it": 1}}
    assert report["jd_out"] == 3 and report["dedup_ratio"] == 0.25
    assert report["pii_remaining"] == 0 and report["with_skill_ratio"] == 1.0
    assert report["crawl_vs_synthetic"] == {"crawl": 2, "synthetic": 1, "synthetic_ratio": 0.3333}
    assert report["distribution"]["city"] == {"Hà Nội": 1, "Hồ Chí Minh": 1, "Đà Nẵng": 1}
    assert report["cells"] == [
        {"group": "backend", "level": "Mid", "city": "Hồ Chí Minh", "crawled": 1, "synthetic": 0},
        {"group": "backend", "level": "Senior", "city": "Hà Nội", "crawled": 1, "synthetic": 0},
        {"group": "frontend", "level": "Junior", "city": "Đà Nẵng", "crawled": 0, "synthetic": 1},
    ]
    normalized = (processed / "jd_normalized.jsonl").read_text(encoding="utf-8")
    assert [json.loads(line)["jd_id"] for line in normalized.splitlines()] == [
        "itviec:1001", "itviec:1002", "synthetic:syn-frontend-Junior-Đà Nẵng-1",
    ]
    assert "0987" not in normalized and "bienxanh-gia.vn" not in normalized and "Anh Tuấn" not in normalized
    chunks = (processed / "jd_chunks.jsonl").read_text(encoding="utf-8").splitlines()
    assert report["chunks_out"] == len(chunks) > 0
    assert "pii_remaining       0" in capsys.readouterr().out


def test_rerun_gives_byte_identical_output(raw_files, paths):
    _, processed = paths
    assert _run() == 0
    first = [(processed / n).read_bytes() for n in ("jd_normalized.jsonl", "jd_chunks.jsonl")]
    assert _run() == 0
    assert [(processed / n).read_bytes() for n in ("jd_normalized.jsonl", "jd_chunks.jsonl")] == first
    assert b"\r\n" not in first[0]


def test_no_raw_exits_1(paths):
    assert _run() == 1


def test_broken_json_line_exits_1(paths, capsys):
    raw_dir, _ = paths
    (raw_dir / "itviec").mkdir(parents=True)
    (raw_dir / "itviec" / "bad.jsonl").write_text('{"source": "itviec"\n', encoding="utf-8")
    assert _run() == 1
    assert "bad.jsonl:1" in capsys.readouterr().err


def test_broken_dictionary_exits_1(raw_files, tmp_path, monkeypatch):
    bad = tmp_path / "skills.yaml"
    bad.write_text("- {slug: java, name: Java, category: Backend, group: backend, aliases: [js]}\n"
                   "- {slug: javascript, name: JavaScript, category: Frontend, group: frontend, aliases: [js]}\n",
                   encoding="utf-8")
    monkeypatch.setattr(jd_process_command, "SKILL_DICTIONARY_PATH", bad)
    assert _run() == 1


def test_remaining_pii_exits_1_and_writes_no_jd_output(raw_files, paths, monkeypatch):
    _, processed = paths
    monkeypatch.setattr(jd_process_command, "count_output_pii", lambda records, chunks: 2)
    assert _run() == 1
    assert not (processed / "jd_normalized.jsonl").exists()
    assert _latest_report(processed)["pii_remaining"] == 2


def test_cli_registers_process_jd():
    assert build_parser().parse_args(["process-jd"]).command == "process-jd"
    assert HANDLERS["process-jd"] is jd_process_command.run_process_jd
