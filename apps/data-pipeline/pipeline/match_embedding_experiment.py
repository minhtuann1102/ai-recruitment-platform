"""Experiment embedding 017 (Phase 2 cua plans/261126-2235-embedding-model-comparison): cham bo dev 264 cap CV x JD bang
bo cham 017 (0.6 cosine + 0.3 skill + 0.1 level, loc cung nhu endpoint, as_of 2026-11-01), CHI doi model embedding.

Cong tai lap truoc (oa-small phai ra lai so da cong bo +-0.005) roi moi doi model. Chi so chinh = xep hang cosine thuan theo CV
(khong phu thuoc thang diem); phu = diem day du voi trong so cu (chinh cho thang cosine cua 3-small). Luat quyet dinh: mot model
chi thang neu CI 95% bootstrap (theo CV) cua nDCG@5 (model - oa-small) khong chua 0. Day la bang chung dev tren 264 cap
(24 CV); cap nhat chot ve matching nam o bo test khoa cua 018.

Chay (tu apps/data-pipeline):  .venv/Scripts/python.exe -m pipeline.match_embedding_experiment [--models oa-small,st-e5 ...]
  --gate-only: chi cong tai lap; --remeasure: do lai van hanh cac model ST; --out-dir: thu muc bao cao;
  --accept-gate-miss "ly do": chi NGUOI QUYET DINH dung, chay tiep khi cong lech (khong cho phep lech tap cap); ly do vao bao cao.
Ma thoat: 0 xong; 1 tham so sai; 3 cong tai lap khong dat; 4 co model loi; 5 bi chan (khoa OpenAI bi tu choi, cong chua chay du).
Khong ghi vao ai_db / ai-service; vector cache trong data/processed (gitignore).
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np

from .match_embedding_evaluate import BASE_ID, Context, add_comparisons, evaluate_model, run_gate, run_gate_without_embeddings
from .match_embedding_models import (CACHE_DIR, MODELS, ModelSpec, VectorCache, embed_openai_missing, ops_path,
                                     resolve_hf_revision)
from .match_embedding_report import write_reports
from .match_eval_metrics import latency_summary
from .settings import APP_DIR

REPORTS_DIR = APP_DIR.parents[1] / "plans" / "261126-2235-embedding-model-comparison" / "reports"
REVISIONS_PATH = CACHE_DIR / "revisions.json"
EXIT_OK, EXIT_INPUT, EXIT_GATE_FAIL, EXIT_MODEL, EXIT_BLOCKED = 0, 1, 3, 4, 5


class OpenAIKeyRejected(RuntimeError):
    """Moi khoa OpenAI da cau hinh deu bi tu choi (het han / sai): khong co vector CV nen khong chay duoc phan can embedding."""


def _openai_keys() -> List[str]:
    """Khoa OpenAI duoc cau hinh cho api.openai.com: EMBEDDING_API_KEY (data-pipeline, index JD) roi LLM_API_KEY cua ai-service
    (endpoint 017 dung khoa nay). Chi lay khoa co base URL la api.openai.com; khong thu khoa cua nha cung cap khac."""
    from urllib.parse import urlparse

    from dotenv import dotenv_values

    keys: List[str] = []
    for env_file, key_var, url_var in ((APP_DIR / ".env", "EMBEDDING_API_KEY", "EMBEDDING_BASE_URL"),
                                       (APP_DIR.parent / "ai-service" / ".env", "LLM_API_KEY", "LLM_BASE_URL")):
        values = dotenv_values(env_file)
        key, host = (values.get(key_var) or "").strip(), (urlparse(values.get(url_var) or "").hostname or "").lower()
        if key and host == "api.openai.com" and key not in keys:
            keys.append(key)
    if not keys:
        raise RuntimeError("khong co khoa OpenAI (api.openai.com) trong data-pipeline/.env hoac ai-service/.env")
    return keys


def _pinned_revision(spec: ModelSpec) -> str:
    """OpenAI: 'api' (khong co revision). HF: sha commit, ghi vao revisions.json lan dau de cac lan chay sau dung lai dung sha."""
    if spec.kind == "openai":
        return "api"
    pins = json.loads(REVISIONS_PATH.read_text(encoding="utf-8")) if REVISIONS_PATH.is_file() else {}
    if spec.name not in pins:
        pins[spec.name] = resolve_hf_revision(spec.name)
        REVISIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
        REVISIONS_PATH.write_text(json.dumps(pins, indent=2), encoding="utf-8")
    return pins[spec.name]


def _embed_openai_with_fallback(spec: ModelSpec, items: List[tuple], cache: VectorCache) -> Dict:
    """Thu tung khoa da cau hinh; chi chuyen khoa khi bi tu choi xac thuc (het han / sai)."""
    from openai import AuthenticationError

    for number, key in enumerate(_openai_keys(), 1):
        try:
            return embed_openai_missing(spec, items, cache, key)
        except AuthenticationError as exc:
            print(f"khoa OpenAI #{number} bi tu choi (HTTP {exc.status_code})", file=sys.stderr)
    raise OpenAIKeyRejected("khoa OpenAI cau hinh trong data-pipeline/.env va ai-service/.env bi tu choi (401, het han)")


def _embed_texts(spec: ModelSpec, items: List[tuple], remeasure: bool) -> Dict:
    """Vector (theo thu tu items) + revision + chi so van hanh. OpenAI trong tien trinh nay; ST trong tien trinh rieng."""
    revision = _pinned_revision(spec)
    cache, finals = VectorCache(spec.model_id, revision, spec.dims), [spec.final_text(r, t) for r, t in items]
    ops_file, ops = ops_path(spec.model_id, revision), {}
    if spec.kind == "openai":
        stats = _embed_openai_with_fallback(spec, items, cache)
        if ops_file.is_file():
            ops = json.loads(ops_file.read_text(encoding="utf-8"))
        if stats["calls"]:  # do tre chi do khi that su goi mang; lan chay cache thi giu so cu
            ops = {"model_id": spec.model_id, "network_latency_ms_query": latency_summary(stats["latency_ms_query"]),
                   "prompt_tokens_embedded_now": stats["prompt_tokens"]}
            ops_file.write_text(json.dumps(ops, indent=2), encoding="utf-8")
    else:
        if remeasure or not cache.covers(finals) or not ops_file.is_file():
            work = CACHE_DIR / f"work-{spec.model_id}.json"
            work.write_text(json.dumps({"items": [{"role": r, "text": t} for r, t in items]}), encoding="utf-8")
            cmd = [sys.executable, "-m", "pipeline.match_embedding_st_worker", "--model-id", spec.model_id,
                   "--revision", revision, "--work", str(work)]
            if subprocess.run(cmd, cwd=APP_DIR).returncode != 0:
                raise RuntimeError(f"worker {spec.model_id} loi")
            cache = VectorCache(spec.model_id, revision, spec.dims)
        ops = json.loads(ops_file.read_text(encoding="utf-8"))
    vectors = [cache.get(f) for f in finals]
    if any(v is None for v in vectors):
        raise RuntimeError(f"{spec.model_id}: cache thieu vector")
    return {"vectors": np.vstack(vectors), "revision": revision, "ops": ops}


def _parse_models(raw: str) -> List[str]:
    wanted = list(MODELS) if raw == "all" else [m.strip() for m in raw.split(",") if m.strip()]
    unknown = [m for m in wanted if m not in MODELS]
    if unknown:
        raise ValueError(f"model la {', '.join(unknown)} (chon {', '.join(MODELS)})")
    return [BASE_ID] + [m for m in wanted if m != BASE_ID]  # oa-small luon co: la co so cua moi so sanh


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", default="all", help=f"danh sach cach nhau dau phay trong {', '.join(MODELS)} hoac all")
    parser.add_argument("--gate-only", action="store_true")
    parser.add_argument("--remeasure", action="store_true")
    parser.add_argument("--accept-gate-miss", default="", metavar="REASON",
                        help="chi nguoi quyet dinh dung: chay tiep du cong tai lap lech (khong lech tap cap); ly do duoc ghi vao bao cao")
    parser.add_argument("--out-dir", default=str(REPORTS_DIR))
    args = parser.parse_args(argv)
    try:
        wanted = _parse_models(args.models)
    except ValueError as exc:
        print(f"loi: {exc}", file=sys.stderr)
        return EXIT_INPUT
    import truststore
    truststore.inject_into_ssl()  # TLS interception: truoc moi cuoc goi OpenAI / HF
    ctx, out_dir = Context(), Path(args.out_dir)
    try:
        small = _embed_texts(MODELS[BASE_ID], ctx.items, args.remeasure)
    except OpenAIKeyRejected as exc:
        partial = run_gate_without_embeddings(ctx)
        print(f"BI CHAN: {exc}. Cong tai lap day du chua chay; phan khong can embedding: "
              f"{'dat' if partial['published']['overall_pass'] else 'KHONG DAT'}", file=sys.stderr)
        write_reports({"gate": partial, "models": {}, "blocked": str(exc)}, out_dir, gate_failed=True)
        return EXIT_BLOCKED
    gate = run_gate(ctx, small)
    print(f"cong tai lap: tong {'DAT' if gate['published']['overall_pass'] else 'KHONG DAT'}, "
          f"theo ngon ngu {'dat' if gate['published']['language_pass'] else 'khong dat'}")
    waiver = args.accept_gate_miss.strip()
    if not gate["pair_check"]["equal"] or (not gate["published"]["overall_pass"] and not waiver):  # tap cap lech khong the bo qua
        write_reports({"gate": gate, "models": {}}, out_dir, gate_failed=True)
        return EXIT_GATE_FAIL
    if args.gate_only:
        write_reports({"gate": gate, "models": {}}, out_dir)
        return EXIT_OK
    results, failures = {BASE_ID: evaluate_model(ctx, MODELS[BASE_ID], small)}, {}
    for model_id in wanted[1:]:
        try:
            results[model_id] = evaluate_model(ctx, MODELS[model_id], _embed_texts(MODELS[model_id], ctx.items, args.remeasure))
        except Exception as exc:  # that bai duoc bao nhu that bai (model sau van chay)
            failures[model_id] = f"{type(exc).__name__}: {exc}"
            print(f"loi {model_id}: {failures[model_id]}", file=sys.stderr)
    add_comparisons(results)
    write_reports({"gate": gate, "models": results, "failures": failures, "n_cv": len(ctx.cvs),
                   "gate_waiver": waiver if not gate["published"]["overall_pass"] else "",
                   "n_pairs": sum(len(v) for v in ctx.data.labels.values())}, out_dir)
    return EXIT_MODEL if failures else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
