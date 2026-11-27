"""Chay MOT model sentence-transformers trong tien trinh rieng (experiment 017 Phase 2): embed + do van hanh.

Tach tien trinh de peak RSS / thoi gian nap cua tung model khong lan nhau. Doc van ban tu file work (cache dir, gitignore),
ghi vector vao VectorCache va chi so van hanh vao ops-*.json. torch 4 thread nhu VM e2-standard-4 (4 vCPU, khong GPU).
Chay: python -m pipeline.match_embedding_st_worker --model-id st-e5 --revision <sha> --work <file>
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List

from .match_embedding_models import MODELS, PASSAGE, QUERY, VectorCache, ops_path
from .match_eval_metrics import latency_summary

THREADS, WARMUP, ROUNDS = 4, 3, 3
DOWNLOAD_IGNORE = ["onnx/*", "openvino/*", "*.onnx*", "*.h5", "*.msgpack", "*.ot", "imgs/*", "colbert*", "sparse*"]


def _peak_rss_mb() -> float:
    import psutil
    info = psutil.Process().memory_info()
    peak = getattr(info, "peak_wset", None)  # Windows: dinh working set; noi khac dung rss hien tai (cuoi chay)
    return round((peak or info.rss) / 2**20, 1)


def _token_stats(model, texts: List[str]) -> Dict:
    """So token (gom ky hieu dac biet + tien to) so voi max_seq_length: van ban dai hon bi model cat am tham."""
    lengths = [len(model.tokenizer(t, add_special_tokens=True)["input_ids"]) for t in texts]
    over = sum(1 for n in lengths if n > model.max_seq_length)
    return {"n": len(lengths), "truncated": over, "rate": over / len(lengths) if lengths else 0.0,
            "max_tokens": max(lengths, default=0), "mean_tokens": round(sum(lengths) / len(lengths), 1) if lengths else 0.0}


def run(args: argparse.Namespace) -> int:
    import truststore
    truststore.inject_into_ssl()  # TLS interception tren may nay: truoc moi cuoc goi mang cua HF
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    import psutil
    import torch
    from huggingface_hub import snapshot_download
    from sentence_transformers import SentenceTransformer

    spec = MODELS[args.model_id]
    torch.set_num_threads(THREADS)
    items = json.loads(Path(args.work).read_text(encoding="utf-8"))["items"]  # [{role, text}]
    finals = [(it["role"], spec.final_text(it["role"], it["text"])) for it in items]
    cache = VectorCache(spec.model_id, args.revision, spec.dims)

    started = time.perf_counter()
    local = snapshot_download(spec.name, revision=args.revision, ignore_patterns=DOWNLOAD_IGNORE)
    download_s = time.perf_counter() - started
    started = time.perf_counter()
    model = SentenceTransformer(local, device="cpu")
    load_s = time.perf_counter() - started
    dims = (getattr(model, "get_embedding_dimension", None) or model.get_sentence_embedding_dimension)()  # ten cu bi deprecate
    if dims != spec.dims:
        raise RuntimeError(f"{spec.model_id}: dims {dims} != {spec.dims}")

    for _, text in finals[:WARMUP]:
        model.encode([text], convert_to_numpy=True)
    psutil.cpu_percent(None)  # moc de do CPU he thong trong cua so do (phat hien tien trinh khac tranh CPU)
    proc = psutil.Process()
    proc.cpu_percent(None)
    window = time.perf_counter()
    samples: Dict[str, List[float]] = {QUERY: [], PASSAGE: []}
    for round_no in range(ROUNDS):
        for role, text in finals:
            began = time.perf_counter()
            vector = model.encode([text], convert_to_numpy=True)[0]
            samples[role].append((time.perf_counter() - began) * 1000)
            if round_no == 0:
                cache.put(text, vector)
    window_s = time.perf_counter() - window
    system_cpu = psutil.cpu_percent(None)
    own_cpu = proc.cpu_percent(None) / psutil.cpu_count()  # phan tram tong CPU may do tien trinh nay dung
    cache.save()

    ops = {
        "model_id": spec.model_id, "repo": spec.name, "revision": args.revision, "torch": torch.__version__,
        "threads": THREADS, "warmup": WARMUP, "rounds": ROUNDS, "max_seq_length": model.max_seq_length,
        "download_s": round(download_s, 1), "load_s": round(load_s, 2), "peak_rss_mb": _peak_rss_mb(),
        "latency_ms": {role: latency_summary(v) for role, v in samples.items()},
        "truncation": {role: _token_stats(model, [t for r, t in finals if r == role]) for role in (QUERY, PASSAGE)},
        "cpu": {"window_s": round(window_s, 1), "system_pct": system_cpu, "own_pct": round(own_cpu, 1),
                "other_pct": round(max(0.0, system_cpu - own_cpu), 1), "logical_cores": psutil.cpu_count()},
    }
    ops_path(spec.model_id, args.revision).write_text(json.dumps(ops, indent=2), encoding="utf-8")
    print(f"{spec.model_id}: load {load_s:.1f}s, peak RSS {ops['peak_rss_mb']} MB, "
          f"p50 query {ops['latency_ms'][QUERY]['p50']:.0f} ms, other-process CPU {ops['cpu']['other_pct']}%")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", required=True, choices=[m for m, s in MODELS.items() if s.kind == "st"])
    parser.add_argument("--revision", required=True)
    parser.add_argument("--work", required=True, help="JSON {items: [{role, text}]} do experiment ghi")
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
