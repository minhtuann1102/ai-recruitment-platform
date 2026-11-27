"""So sanh model embedding cho RAG (plans/261126-2235-embedding-model-comparison, Phase 1): oa-small (dang dung),
oa-large, st-minilm, st-e5, st-bge tren cac golden set da co, MOT duong tim trong bo nho cho moi model (cosine toan kho
-> k*OVERFETCH -> dedup -> top-5) nen chi so chi do model. Kho + vector 3-small doc tu ai_db (chi doc), cache o
evals/.cache/ (gitignore, khong commit noi dung crawl).

Giai doan (moi lenh la mot tien trinh; chay tu apps/ai-service):
  python -m evals.embedding_model_experiment load-corpus
  python -m evals.embedding_model_experiment rewrites
  python -m evals.embedding_model_experiment embed --model {oa-large|st-minilm|st-e5|st-bge} [--max-usd 1]
  python -m evals.embedding_model_experiment queries --model {oa-small|oa-large|st-minilm|st-e5|st-bge}
  python -m evals.embedding_model_experiment parity
  python -m evals.embedding_model_experiment evaluate --out-json R.json --out-md R.md
Thu tu: load-corpus -> rewrites -> (embed, queries) tung model -> parity -> evaluate. Cai deps:
requirements-embedding-experiment.txt (may co TLS interception: truststore, nap duoi day truoc moi import mang).
"""
import truststore

truststore.inject_into_ssl()

import argparse  # noqa: E402
import asyncio  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

from evals.embedding_experiment_models import SPECS, disable_tracing  # noqa: E402

disable_tracing()
if sys.platform == "win32":  # psycopg async can SelectorEventLoop
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

EVALS = Path(__file__).parent
ALT_GOLDEN = Path("C:/Users/NITRO/arp-golden/apps/ai-service/evals")  # worktree chore/rag-golden-de-review @ 3c7dae9


def golden_versions(alt: Path):
    from evals.embedding_experiment_corpus import load_golden_versions
    return load_golden_versions({"repo": EVALS, "arp-golden-3c7dae9": alt})


def cmd_load_corpus(_args) -> None:
    from evals.embedding_experiment_cache import write_json
    from evals.embedding_experiment_corpus import fetch_corpus, persist_corpus
    from evals.embedding_experiment_embed import store_for
    rows, vecs, total = fetch_corpus()
    assert len(rows) == total == len(vecs) and vecs.shape[1] == SPECS["oa-small"].dims, (len(rows), total, vecs.shape)
    fingerprint = persist_corpus(rows)
    store = store_for(SPECS["oa-small"])
    store.hashes, store.vecs = [], None  # ghi de: kho vua doc lai tu DB
    store.add([r["content_hash"] for r in rows], vecs)
    store.meta = {"source": "ai_db.knowledge_chunks.embedding (vector da luu)", "n": len(rows)}
    store.save()
    write_json("corpus-meta.json", {"n_chunks": len(rows), "fingerprint_md5": fingerprint,
                                    "n_qa_ids": len({r["qa_id"] for r in rows}),
                                    "n_by_chunk_type": {t: sum(1 for r in rows if r["chunk_type"] == t)
                                                        for t in {r["chunk_type"] for r in rows}}})
    print(f"corpus {len(rows)} chunk, fingerprint {fingerprint}")


def cmd_rewrites(args) -> None:
    from evals.embedding_experiment_queries import rewrite_queries
    print(json.dumps(rewrite_queries(golden_versions(args.alt_golden)), ensure_ascii=False))


def cmd_embed(args) -> None:
    from evals.embedding_experiment_embed import embed_openai, embed_st
    spec = SPECS[args.model]
    if spec.id == "oa-small":
        raise SystemExit("oa-small dung vector da luu (load-corpus), khong embed lai kho")
    embed_st(spec) if spec.kind == "st" else embed_openai(spec, args.max_usd)


def cmd_queries(args) -> None:
    from evals.embedding_experiment_queries import embed_queries
    embed_queries(args.model, golden_versions(args.alt_golden))


def cmd_parity(args) -> None:
    from evals.embedding_experiment_parity import run_parity
    print(json.dumps(run_parity(golden_versions(args.alt_golden)), ensure_ascii=False, indent=1)[:3000])


def cmd_evaluate(args) -> None:
    from evals.embedding_experiment_evaluate import evaluate
    from evals.embedding_experiment_report import render_markdown
    results = evaluate(golden_versions(args.alt_golden), args.alt_golden)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    args.out_md.write_text(render_markdown(results), encoding="utf-8")
    print(f"da ghi {args.out_json} va {args.out_md}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--alt-golden", type=Path, default=ALT_GOLDEN, help="thu muc evals cua ban golden thu hai")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, fn in (("load-corpus", cmd_load_corpus), ("rewrites", cmd_rewrites), ("parity", cmd_parity)):
        sub.add_parser(name).set_defaults(fn=fn)
    for name, fn in (("embed", cmd_embed), ("queries", cmd_queries)):
        p = sub.add_parser(name)
        p.add_argument("--model", required=True, choices=sorted(SPECS))
        p.add_argument("--max-usd", type=float, default=1.0)
        p.set_defaults(fn=fn)
    p = sub.add_parser("evaluate")
    p.add_argument("--out-json", type=Path, required=True)
    p.add_argument("--out-md", type=Path, required=True)
    p.set_defaults(fn=cmd_evaluate)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
