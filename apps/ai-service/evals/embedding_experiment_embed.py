"""Giai doan `embed` (vector kho) cua thi nghiem embedding, moi model chay trong MOT tien trinh rieng de do thoi gian nap
va RSS dinh khong lan nhau. ST: chia lat theo do dai token (it padding), ghi cache sau moi vai lat, chay lai thi tiep tuc.
OpenAI (oa-large): in uoc tinh chi phi truoc, bo neu vuot --max-usd.
"""
import asyncio
import json
import sys
import time
from typing import Dict, List

import psutil

from app.llm.gateway import build_client
from app.llm.settings import load_llm_settings
from evals.embedding_experiment_cache import VectorStore, load_corpus, write_json
from evals.embedding_experiment_core import truncation_by_type
from evals.embedding_experiment_models import (OPENAI_MAX_TOKENS, OPENAI_PRICE_PER_M, SPECS, ModelSpec, load_st,
                                               openai_embed, openai_model_name, openai_token_lengths, peak_rss_mb,
                                               resolve_revision, st_encode, st_token_lengths, THREADS)

SLICE = 64  # so chunk moi lat
TOKEN_BUDGET = 8192  # batch_size = ngan sach token / chunk dai nhat trong lat (tran 32): bge-m3 max_seq 8192 khong tran RAM
FLUSH_EVERY = 8  # lat


def store_config(spec: ModelSpec, revision: str) -> Dict:
    return {"model": spec.name, "revision": revision, "doc_prefix": spec.doc_prefix, "dims": spec.dims}


def store_for(spec: ModelSpec) -> VectorStore:
    if spec.id == "oa-small":  # vector da luu trong ai_db (load-corpus), khong embed lai
        return VectorStore("oa-small-stored", store_config(spec, "stored"))
    rev = resolve_revision(spec)
    return VectorStore(f"{spec.id}-{rev[:12]}", store_config(spec, rev))


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def embed_st(spec: ModelSpec) -> None:
    rows = load_corpus()
    rev = resolve_revision(spec)
    model, load_s, cold = load_st(spec, rev)
    max_len = model.max_seq_length
    texts = [spec.doc_prefix + r["content"] for r in rows]
    lengths = st_token_lengths(model, texts)
    trunc = truncation_by_type(lengths, [r["chunk_type"] for r in rows], max_len)
    store = VectorStore(f"{spec.id}-{rev[:12]}", store_config(spec, rev))
    todo = set(store.missing([r["content_hash"] for r in rows]))
    order = sorted((i for i, r in enumerate(rows) if r["content_hash"] in todo), key=lambda i: lengths[i])
    _log(f"{spec.id} rev={rev[:12]} max_seq={max_len} da co={len(rows) - len(order)} can embed={len(order)} "
         f"cat={trunc['all']['pct']}% load={load_s:.1f}s cold_cache={cold}")
    psutil.cpu_percent(None)  # moc dau; lan goi cuoi tra CPU he thong trung binh ca lan chay (ban phat hien chay chong)
    elapsed, done = 0.0, 0
    sessions: List[Dict] = store.meta.get("sessions", [])
    for n, start in enumerate(range(0, len(order), SLICE), 1):
        idx = order[start:start + SLICE]
        batch = max(1, min(32, TOKEN_BUDGET // max(min(lengths[i], max_len) for i in idx)))
        t0 = time.perf_counter()
        vecs = st_encode(model, [texts[i] for i in idx], batch)
        elapsed += time.perf_counter() - t0
        store.add([rows[i]["content_hash"] for i in idx], vecs)
        done += len(idx)
        if n % FLUSH_EVERY == 0 or done == len(order):
            _log(f"{spec.id} {done}/{len(order)} embed={elapsed:.0f}s rss={peak_rss_mb():.0f}MB")
            sessions_now = sessions + [{"load_s": round(load_s, 2), "cold_cache": cold, "embedded": done,
                                        "embed_s": round(elapsed, 1)}]
            store.meta["sessions"] = sessions_now
            store.save()
    total = sum(s["embed_s"] for s in store.meta.get("sessions", []))
    write_json(f"ops-embed-{spec.id}.json", {
        "model": spec.id, "revision": rev, "max_seq_length": max_len, "threads": THREADS, "n_chunks": len(rows),
        "embed_seconds_total": round(total, 1), "embedded_this_run": done, "load_seconds_this_process": round(load_s, 2),
        "load_cold_cache": cold, "peak_rss_mb_corpus_embed": round(peak_rss_mb()),
        "sys_cpu_pct_avg_this_run": psutil.cpu_percent(None) if done else None,
        "tokens_total": int(sum(lengths)), "truncation": trunc, "sessions": store.meta.get("sessions", [])})
    _log(f"{spec.id} xong: {total:.0f}s tong, cat {trunc['all']['pct']}%")


def embed_openai(spec: ModelSpec, max_usd: float) -> None:
    rows = load_corpus()
    texts = [r["content"] for r in rows]
    lengths = openai_token_lengths(texts)
    cost = sum(lengths) / 1e6 * OPENAI_PRICE_PER_M[spec.id]
    over = sum(1 for x in lengths if x > OPENAI_MAX_TOKENS)
    print(f"{spec.id}: {len(texts)} chunk, {sum(lengths)} token (tiktoken cl100k), uoc ${cost:.3f}, "
          f"{over} chunk > {OPENAI_MAX_TOKENS} token", flush=True)
    ops = {"model": spec.id, "tokens_estimated": sum(lengths), "cost_estimated_usd": round(cost, 4),
           "chunks_over_limit": over}
    if cost > max_usd or over:
        write_json(f"ops-embed-{spec.id}.json", {**ops, "skipped": f"cost>{max_usd} hoac chunk vuot gioi han"})
        raise SystemExit("bo qua: vuot ngan sach hoac co chunk vuot gioi han token")
    store = store_for(spec)
    missing = set(store.missing([r["content_hash"] for r in rows]))
    todo = [i for i, r in enumerate(rows) if r["content_hash"] in missing]
    llm = load_llm_settings()
    t0 = time.perf_counter()
    vecs, billed = asyncio.run(openai_embed(build_client(llm), openai_model_name(llm.base_url, spec.name),
                                            [texts[i] for i in todo], spec.dims,
                                            on_progress=lambda a, b: _log(f"{spec.id} {a}/{b}")))
    wall = time.perf_counter() - t0
    store.add([rows[i]["content_hash"] for i in todo], vecs)
    store.meta.update({"billed_tokens": billed, "api_wall_seconds": round(wall, 1)})
    store.save()
    write_json(f"ops-embed-{spec.id}.json", {**ops, "billed_tokens": billed,
                                             "cost_actual_usd": round(billed / 1e6 * OPENAI_PRICE_PER_M[spec.id], 4),
                                             "api_wall_seconds": round(wall, 1), "embedded_this_run": len(todo)})
    print(json.dumps({"billed_tokens": billed, "wall_s": round(wall, 1)}))
