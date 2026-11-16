"""Dang ky 7 lenh textbook vao CLI chinh (spec 012, contracts/pipeline-cli-textbook.md).

__main__ chi goi add_parsers(sub) va HANDLERS.update(HANDLERS cua file nay). Lenh chua hien thuc tro toi
_not_implemented (ma thoat 2, giong lenh chua lam o __main__); moi task hien thuc xong thay mot dong trong HANDLERS.
"""
import argparse
import sys
from typing import Callable, Dict

from .textbook_validate_command import run_validate_textbook

EXIT_PREFLIGHT_ERROR = 2  # ma chung cua pipeline: lenh chua lam / thieu cau hinh

Handler = Callable[[argparse.Namespace], int]


def _not_implemented(args: argparse.Namespace) -> int:
    print(f"lenh '{args.command}' chua duoc hien thuc (spec 012, xem tasks.md)", file=sys.stderr)
    return EXIT_PREFLIGHT_ERROR


HANDLERS: Dict[str, Handler] = {
    "validate-textbook": run_validate_textbook,
    "crawl-textbook": _not_implemented,
    "process-textbook": _not_implemented,
    "review-textbook-prepare": _not_implemented,
    "review-textbook-score": _not_implemented,
    "coverage-textbook": _not_implemented,
    "index-textbook": _not_implemented,
}


def _add_source_option(parser: argparse.ArgumentParser, required: bool) -> None:
    parser.add_argument(
        "--source", action="append", default=[], required=required, metavar="S",
        help="source_id, lap lai duoc" + ("" if required else "; bo trong = moi nguon status use"),
    )


def add_parsers(sub) -> None:
    """Them 7 subparser vao `sub` (ket qua cua parser.add_subparsers)."""
    validate = sub.add_parser("validate-textbook", help="kiem manifest nguon textbook, offline (spec 012)")
    validate.add_argument("--strict", action="store_true", help="canh bao thanh loi")

    crawl = sub.add_parser("crawl-textbook", help="tai cac trang status use cua mot nguon -> data/raw/textbook/")
    _add_source_option(crawl, required=True)
    crawl.add_argument("--delay", type=float, default=1.0, help="giay nghi toi thieu giua hai request")
    crawl.add_argument("--render", action="store_true", help="dung Playwright cho trang can JavaScript")

    process = sub.add_parser("process-textbook", help="trang tho -> doan da loc nhieu + dedup, offline")
    _add_source_option(process, required=False)

    prepare = sub.add_parser("review-textbook-prepare", help="chia doan chua soat thanh lo kem doan moi (canary)")
    _add_source_option(prepare, required=True)
    prepare.add_argument("--batch-size", type=int, default=25, help="so doan that moi lo")
    prepare.add_argument("--seed", type=int, default=2026, help="seed xao vi tri doan moi (cung seed -> cung lo)")

    score = sub.add_parser("review-textbook-score", help="cham ket luan cua worker, ghi decisions")
    _add_source_option(score, required=True)

    coverage = sub.add_parser("coverage-textbook", help="bao cao do phu theo tinh huong va kiem tra truy hoi")
    coverage.add_argument("--db", action="store_true", help="them kiem tra vector tren kho that (can .env)")
    coverage.add_argument("--strict", action="store_true", help="thoat 1 khi khong dat SC-001 hoac SC-004")

    index = sub.add_parser("index-textbook", help="embed va ghi doan textbook vao knowledge_chunks")
    _add_source_option(index, required=True)
