"""match-eval (spec 017 US3, contracts/pipeline-cli-match.md): danh gia chat luong, do tre va chi phi cua endpoint goi y.

Thu tu: nap bo du lieu (loi -> ma 1) -> cau hinh (loi -> ma 2) -> moi CV mot lan goi voi job_ids = pool, page_size 50
(degraded / mock -> ma 4, dung, khong ghi gi) -> so tap cap qua loc voi tap co nhan (lech -> ma 1, chua do tre) -> cac vong
do tre co va khong co job_ids -> ghi JSON tho + bang markdown. Chi ghi file khi ca lan chay deu la che do that.
Ma thoat: 0 xong; 1 thieu / thua nhan hoac du lieu hong; 2 khong goi duoc ai-service; 4 co phan hoi degraded hoac mock.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from .match_eval_client import AiServiceError, MatchClient, MatchReply, build_request, require_complete_page
from .match_eval_data import (EvalData, EvalDataError, compare_pair_sets, language_groups, load_eval_data, load_pool_jds,
                              require_pair_sets_equal)
from .match_eval_report import render_markdown
from .match_eval_summary import add_latency_sample, build_summary, embedding_tokens, find_index_report, new_latency_samples
from .settings import (JD_NORMALIZED_PATH, MATCH_EVAL_RESULTS_PATH, MATCH_EVAL_RUN_DIR, MATCH_EVAL_SEEDS_DIR, PROCESSED_DIR,
                       ConfigError, require_match_eval_settings)

EXIT_OK, EXIT_INPUT_ERROR, EXIT_SERVICE, EXIT_UNUSABLE = 0, 1, 2, 4
SEEDS_DIR, RUN_DIR = MATCH_EVAL_SEEDS_DIR, MATCH_EVAL_RUN_DIR  # test tro sang tmp_path
POOL_PAGE_SIZE, FULL_INDEX_PAGE_SIZE = 50, 10  # co job_ids: lay het pool; khong job_ids: trang dau nhu dung that


class UnusableRunError(RuntimeError):
    """Phan hoi degraded hoac mock: so do tren vector gia / diem thieu cosine vo nghia (FR-021) -> ma 4."""


def check_real_run(cv_id: str, body: Dict) -> None:
    meta = body["metadata"]
    if meta.get("mock"):
        raise UnusableRunError(f"{cv_id}: ai-service dang o che do mock (MATCH_MOCK=true); can che do that voi chi muc ai_db")
    if meta.get("degraded"):
        raise UnusableRunError(f"{cv_id}: phan hoi degraded ({meta.get('degraded_reason')}); kiem tra khoa embedding / ket noi roi chay lai")


def _fmt(value) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def _call(client, cv: Dict, data: EvalData, pool_only: bool) -> MatchReply:
    request = build_request(cv, data.as_of, data.jd_ids if pool_only else None, POOL_PAGE_SIZE if pool_only else FULL_INDEX_PAGE_SIZE)
    reply = client.match(request)
    check_real_run(cv["cv_id"], reply.body)
    return reply


def _measure_latency(client, data: EvalData, rounds: int, token_counts: List[int]) -> Dict:
    samples = new_latency_samples()
    for _ in range(rounds):
        for cv in data.cvs:
            for variant, pool_only in (("with_job_ids", True), ("without_job_ids", False)):
                reply = _call(client, cv, data, pool_only)
                add_latency_sample(samples, variant, reply)
                token_counts.append(embedding_tokens(reply.body))
    return samples


def _write_outputs(summary: Dict, out: Path) -> Tuple[Path, Path]:
    now = datetime.now(timezone.utc)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    raw = RUN_DIR / f"run-{now.strftime('%Y%m%dT%H%M%S%fZ')}.json"  # micro giay: hai lan chay lien tiep khong ghi de nhau
    raw.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_markdown(summary, raw.name), encoding="utf-8")
    return raw, out


def run_match_eval(args: argparse.Namespace) -> int:
    if args.rounds < 1:
        print("loi: --rounds phai >= 1", file=sys.stderr)
        return EXIT_INPUT_ERROR
    try:
        data = load_eval_data(SEEDS_DIR)
        jds = load_pool_jds(JD_NORMALIZED_PATH, data.jd_ids)
        groups = language_groups(jds)
    except EvalDataError as exc:
        print(f"loi: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    try:
        settings = require_match_eval_settings()
    except ConfigError as exc:
        print(f"loi cau hinh: {exc}", file=sys.stderr)
        return EXIT_SERVICE
    client = MatchClient(settings)
    token_counts: List[int] = []
    bodies: Dict[str, Dict] = {}
    try:
        for cv in data.cvs:
            reply = _call(client, cv, data, pool_only=True)
            require_complete_page(cv["cv_id"], reply.body)
            bodies[cv["cv_id"]] = reply.body
            token_counts.append(embedding_tokens(reply.body))
        check = compare_pair_sets({cv: [i["job_id"] for i in b["items"]] for cv, b in bodies.items()}, data.labels)
        try:
            require_pair_sets_equal(check)
        except EvalDataError as exc:  # chua do tre: nhan chua du thi khong phi cuoc goi
            print(f"loi: {exc}", file=sys.stderr)
            return EXIT_INPUT_ERROR
        samples = _measure_latency(client, data, args.rounds, token_counts)
    except UnusableRunError as exc:
        print(f"loi: {exc}. Dung, khong ghi bang.", file=sys.stderr)
        return EXIT_UNUSABLE
    except AiServiceError as exc:
        print(f"loi ai-service: {exc}", file=sys.stderr)
        return EXIT_SERVICE
    summary = build_summary(data, jds, groups, bodies, samples, token_counts, settings,
                            find_index_report(PROCESSED_DIR), args.rounds, datetime.now(timezone.utc).isoformat(timespec="seconds"))
    raw, out = _write_outputs(summary, Path(args.out))
    for method, s in summary["quality"].items():
        print(f"{method:<12} P@5 {_fmt(s['p_at_5'])}  nDCG@5 {_fmt(s['ndcg_at_5'])}  ({s['n_cv']} CV)")
    print(f"ghi {raw}")
    print(f"ghi {out}")
    return EXIT_OK


def add_parser(sub) -> None:
    parser = sub.add_parser("match-eval", help="danh gia chat luong / do tre / chi phi cua endpoint goi y viec lam (spec 017); can ai-service che do that")
    parser.add_argument("--rounds", type=int, default=4, metavar="N", help="so vong do tre, moi vong goi moi CV co va khong co job_ids (mac dinh 4)")
    parser.add_argument("--out", default=str(MATCH_EVAL_RESULTS_PATH), metavar="FILE", help="bang markdown ket qua (mac dinh specs/017-cv-jd-matching/eval-results.md)")
