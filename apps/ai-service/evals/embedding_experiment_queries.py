"""Giai doan truy van cua thi nghiem embedding: (1) viet lai LLM MOT lan, luu cache, moi model dung chung; (2) embed tung
truy van (raw + raw+rewrite) bang tung model, do p50/p95 tren cac truy van raw (batch 1, 4 thread, bo 3 lan khoi dong).
Truy van embed TUNG CAI MOT (khong batch) de vector khong phu thuoc padding va dung la thoi gian 1 truy van that.
"""
import asyncio
import datetime
import sys
import time
from typing import Dict, List

import psutil

from app.llm.gateway import build_client, get_gateway
from app.llm.settings import agent_settings, load_llm_settings
from app.llm.usage import UsageCollector
from app.prompts.store import PromptStore
from app.rag.query_rewrite import AGENT, QueryRewriter
from evals.embedding_experiment_cache import read_json, text_key, write_json
from evals.embedding_experiment_core import percentile_ms
from evals.embedding_experiment_models import (SPECS, THREADS, load_st, openai_model_name, peak_rss_mb,
                                               resolve_revision, st_encode)
from evals.retrieval_experiment import texts_for

WARMUP = ["warm up query one", "cau hoi khoi dong thu hai", "third warm up sentence for the encoder"]


def unique_queries(versions: Dict[str, Dict]) -> List[str]:
    """Cau truy van duy nhat cua moi ban golden (giu thu tu xuat hien)."""
    seen: Dict[str, None] = {}
    for v in versions.values():
        for golden in v["sets"].values():
            for q in golden["queries"]:
                seen.setdefault(q["query"], None)
    return list(seen)


async def _rewrite(queries: List[str], concurrency: int = 4) -> Dict:
    gw, sem, failed = get_gateway(), asyncio.Semaphore(concurrency), []
    rewriter = QueryRewriter(gw)
    out = read_json("rewrites.json", {"rewrites": {}, "usage": []})

    async def one(q: str) -> None:
        async with sem:
            col = UsageCollector()
            text = await rewriter.to_english(q, col)
            if not col.records:  # QueryRewriter nuot loi LLM va tra lai truy van goc: KHONG cache, de khong ghi ban sai
                failed.append(q)
                return
            out["rewrites"][q] = text
            out["usage"].append(col.to_metadata()["usage"])

    await asyncio.gather(*(one(q) for q in queries if q not in out["rewrites"]))
    if failed:
        raise SystemExit(f"Viet lai loi {len(failed)}/{len(queries)} truy van (kiem tra LLM_API_KEY); khong ghi cache")
    rewrites = out["rewrites"]
    out["meta"] = {"model": agent_settings(AGENT, gw.llm).model, "prompt_version": PromptStore().get(AGENT).version,
                   "date": datetime.date.today().isoformat(), "n": len(rewrites),
                   "billed_tokens": sum(u["query_rewriter"]["input_tokens"] + u["query_rewriter"]["output_tokens"]
                                        for u in out["usage"] if "query_rewriter" in u),
                   # rewrite == raw sau khi LLM tra loi thanh cong: texts_for dung tu dien (nhu Retriever)
                   "unchanged_after_success": sum(1 for q, r in rewrites.items() if r.strip() == q.strip())}
    return out


def rewrite_queries(versions: Dict[str, Dict]) -> Dict:
    out = asyncio.run(_rewrite(unique_queries(versions)))
    write_json("rewrites.json", out)
    return out["meta"]


def _embedder(spec, loop):
    """(ham embed 1 van ban, thong tin nap, don dep). ST: batch 1, tien to truy van; OpenAI: cung duong voi app."""
    if spec.kind == "st":
        model, load_s, cold = load_st(spec, resolve_revision(spec))
        return (lambda t: st_encode(model, [spec.query_prefix + t], 1)[0]), {"load_s": load_s, "cold": cold}
    llm = load_llm_settings()
    if spec.id == "oa-small":  # dung gateway.embed nhu embed_query cua app (build_retriever)
        gw = get_gateway()
        return (lambda t: loop.run_until_complete(gw.embed([t]))[0]), {}
    client, name = build_client(llm), openai_model_name(llm.base_url, spec.name)
    return (lambda t: loop.run_until_complete(client.embeddings.create(model=name, input=[t], dimensions=spec.dims))
            .data[0].embedding), {}


def embed_queries(model_id: str, versions: Dict[str, Dict]) -> None:
    """Tang dan: chi embed van ban chua co trong cache vector truy van. Do thoi gian khi co truy van raw moi (lan dau);
    ban viet lai (rewrites.json) chua co thi bo qua raw+rewrite, chay lai sau khi co se bo sung."""
    spec, rev = SPECS[model_id], resolve_revision(SPECS[model_id])
    name = f"qvec-{model_id}-{rev[:12]}.json"
    vecs: Dict[str, List[float]] = read_json(name, {})
    rewrites = (read_json("rewrites.json") or {}).get("rewrites", {})
    raws = unique_queries(versions)
    combined = [texts_for(q, rewrites[q])["raw+rewrite"] for q in raws if q in rewrites]
    raws_todo = [t for t in raws if text_key(t) not in vecs]
    combined_todo = [t for t in combined if text_key(t) not in vecs]
    if not raws_todo and not combined_todo:
        print(f"{model_id}: cache vector truy van da day du", file=sys.stderr)
        return
    loop = asyncio.new_event_loop()
    embed, info = _embedder(spec, loop)
    psutil.cpu_percent(None)  # moc dau cho CPU he thong trung binh
    for w in WARMUP:
        embed(w)
    times: List[float] = []
    for t in raws_todo:  # chi truy van raw duoc tinh thoi gian (batch 1)
        t0 = time.perf_counter()
        v = embed(t)
        times.append((time.perf_counter() - t0) * 1000)
        vecs[text_key(t)] = [float(x) for x in v]
    for t in combined_todo:
        vecs[text_key(t)] = [float(x) for x in embed(t)]
    write_json(name, vecs)
    if not times:
        print(f"{model_id}: bo sung {len(combined_todo)} van ban raw+rewrite, giu so do thoi gian cu", file=sys.stderr)
        return
    ops = {"model": model_id, "revision": rev, "n_timed_queries": len(times), "warmup_excluded": len(WARMUP),
           "threads": THREADS if spec.kind == "st" else None, "date": datetime.datetime.now().isoformat(timespec="seconds"),
           "p50_ms": round(percentile_ms(times, 50), 1), "p95_ms": round(percentile_ms(times, 95), 1),
           "mean_ms": round(sum(times) / len(times), 1), "peak_rss_mb_serve": round(peak_rss_mb()),
           "sys_cpu_pct_avg": psutil.cpu_percent(None), "kind_note": "round trip API" if spec.kind == "openai" else "local CPU"}
    if info:
        ops.update({"load_seconds": round(info["load_s"], 2), "load_cold_cache": info["cold"]})
        import sentence_transformers, torch, transformers
        ops["libs"] = {"torch": torch.__version__, "transformers": transformers.__version__,
                       "sentence_transformers": sentence_transformers.__version__}
    write_json(f"ops-query-{model_id}.json", ops)
    print(f"{model_id}: p50={ops['p50_ms']}ms p95={ops['p95_ms']}ms rss={ops['peak_rss_mb_serve']}MB", file=sys.stderr)
