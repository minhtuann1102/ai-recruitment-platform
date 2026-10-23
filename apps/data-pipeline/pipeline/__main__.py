"""CLI: python -m pipeline <lenh> (chay trong apps/data-pipeline/).

Lenh va ma thoat: specs/005-rag-knowledge-base-qa/contracts/pipeline-cli.md.
"""
import argparse
import sys
from typing import Callable, Dict, List, Optional

from .collect_command import run_collect
from .crawl_command import run_crawl
from .db_commands import run_index, run_search
from .enrich_command import run_enrich
from .offline_commands import run_process, run_validate
from .review_sample_command import run_review_sample
from .seed_review_command import run_approve_seed, run_review_seed

EXIT_OK = 0
EXIT_INPUT_ERROR = 1  # seed / catalog / golden set loi, hoac crawl thu 0 record
EXIT_PREFLIGHT_ERROR = 2  # thieu key, DB chua san sang, provider loi; lenh chua lam cung dung ma nay
EXIT_EMBED_ERRORS = 3  # index xong nhung con ban ghi embed loi

Handler = Callable[[argparse.Namespace], int]


def _not_implemented(args: argparse.Namespace) -> int:
    print(f"lenh '{args.command}' chua duoc hien thuc", file=sys.stderr)
    return EXIT_PREFLIGHT_ERROR


# Moi lenh dang ky handler khi story tuong ung duoc hien thuc (tasks.md)
HANDLERS: Dict[str, Handler] = {
    "validate": run_validate,
    "process": run_process,
    "collect": run_collect,
    "enrich": run_enrich,
    "review-sample": run_review_sample,
    "review-seed": run_review_seed,
    "approve-seed": run_approve_seed,
    "index": run_index,
    "search": run_search,
    "crawl": run_crawl,
}


def _add_catalog_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--extra-catalog",
        action="append",
        default=[],
        metavar="DIR",
        help="them thu muc YAML catalog (chi de soan truoc voi de xuat; nghiem thu khong dung)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m pipeline", description="Data pipeline RAG (spec 005)")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="kiem tra seed Q&A (US1)")
    validate.add_argument("--strict", action="store_true", help="nguong phan bo SC-001/SC-002 thanh loi")
    _add_catalog_option(validate)

    process = sub.add_parser("process", help="lam sach -> 2 ban ghi/cap -> dedup, offline (US2)")
    _add_catalog_option(process)

    index = sub.add_parser("index", help="embed ban ghi moi va ghi vao knowledge_chunks (US3)")
    _add_catalog_option(index)

    search = sub.add_parser("search", help="truy hoi chi doc de kiem chung (US3)")
    search.add_argument("query")
    search.add_argument("--k", type=int, default=5)
    search.add_argument("--category")
    search.add_argument("--difficulty", choices=["easy", "medium", "hard"])
    search.add_argument("--topic-id")
    search.add_argument("--chunk-type", choices=["question", "qa_pair"])

    evaluate = sub.add_parser("eval", help="recall@k tren golden set (US4)")
    evaluate.add_argument("--k", type=int, default=5)

    collect = sub.add_parser("collect", help="tai Q&A tu cac repo GitHub -> data/raw/collected_qa/")
    collect.add_argument("--only", action="append", default=[], metavar="SOURCE", help="chi tai nguon nay (lap lai duoc)")
    collect.add_argument("--delay", type=float, default=0.5, help="giay nghi toi thieu giua hai request")

    enrich = sub.add_parser("enrich", help="LLM dich sang tieng Viet + gan topic + do kho -> data/raw/enriched_qa/")
    _add_catalog_option(enrich)
    enrich.add_argument("--only", action="append", default=[], metavar="SOURCE", help="chi xu ly nguon nay")
    enrich.add_argument("--per-source", type=int, default=0, metavar="N", help="toi da N cap moi nguon (thu / mau review)")
    enrich.add_argument("--workers", type=int, default=8, help="so loi goi LLM song song")
    enrich.add_argument("--retry-rejected", action="store_true", help="thu lai cap da bi loai (vd sau khi catalog doi)")

    review = sub.add_parser("review-sample", help="lay mau cap da dich de duyet (ban goc canh ban dich)")
    review.add_argument("--per-source", type=int, default=10, metavar="N")
    review.add_argument("--seed", type=int, default=2026, help="seed ngau nhien (cung seed -> cung mau)")

    sub.add_parser("review-seed", help="xuat cap seed curated chua duyet ra data/processed/seed-review.txt")
    approve_seed = sub.add_parser("approve-seed", help="dien reviewed_by cho cac cap seed da doc")
    approve_seed.add_argument("--reviewer", required=True)
    approve_seed.add_argument("--ids", required=True, help="vd de-qa-1000..1021,de-qa-1050")

    crawl = sub.add_parser("crawl", help="crawler mau (US5)")
    crawl.add_argument("source", choices=["react-docs"])
    crawl.add_argument("--max-pages", type=int, default=60)
    crawl.add_argument("--delay", type=float, default=1.0, help="giay nghi toi thieu giua hai request")
    crawl.add_argument("--render", action="store_true", help="dung Playwright cho trang can JavaScript")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    # Console Windows mac dinh cp1252: in tieng Viet se loi neu khong ep UTF-8
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    return HANDLERS.get(args.command, _not_implemented)(args)


if __name__ == "__main__":
    sys.exit(main())
