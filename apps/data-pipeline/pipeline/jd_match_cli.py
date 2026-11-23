"""Dang ky lenh goi y viec lam CV-JD vao CLI chinh (spec 017, contracts/pipeline-cli-match.md).

__main__ chi goi add_parsers(sub) va HANDLERS.update(HANDLERS cua file nay), giong textbook_cli. Hien co
index-jd-match; match-eval-sheet va match-eval them o PR-3 (US3).
"""
import argparse
from typing import Callable, Dict

from .jd_match_index_command import run_index_jd_match

Handler = Callable[[argparse.Namespace], int]

HANDLERS: Dict[str, Handler] = {
    "index-jd-match": run_index_jd_match,
}


def add_parsers(sub) -> None:
    """Them subparser vao `sub` (ket qua cua parser.add_subparsers)."""
    index = sub.add_parser("index-jd-match", help="embed JD chuan hoa va ghi vao knowledge_chunks de goi y viec lam (spec 017)")
    index.add_argument("--rebuild", action="store_true",
                       help="xoa dataset jd-match (chi source_type job_description) roi index lai; dung khi doi embedding model")
    index.add_argument("--limit", type=int, default=None, metavar="N",
                       help="chi N JD dau (chay thu); khong don ban ghi cu, khong dung chung voi --rebuild")
