"""Dung bao cao Markdown tu ket qua JSON cua thi nghiem embedding (khong tinh lai gi, chi trinh bay + ap luat quyet dinh)."""
from typing import Dict, List

ORDER = ["oa-small", "oa-large", "st-minilm", "st-e5", "st-bge"]
GROUPS = ["vi", "mixed", "en", "no_diacritics", "all"]
STRAT_NAME = {"raw": "raw, chi vector (CHI SO CHINH)", "raw+rewrite": "raw+rewrite (LLM viet lai, mot lan, chung cho moi model)"}
VERDICT_TEXT = {"better": "TOT HON (CI > 0)", "worse": "KEM HON (CI < 0)", "tie": "ngang (CI chua 0)"}
REPRO = """cd apps/ai-service
PY=.venv/Scripts/python.exe; M="-m evals.embedding_model_experiment"
$PY -m pip install --use-feature=truststore -r evals/requirements-embedding-experiment.txt
export HF_HUB_DISABLE_XET=1   # may co TLS interception: hf-xet treo khong tai duoc, dung HTTP thuong (truststore inject o entry)
$PY $M load-corpus            # doc ai_db (aie_reader) -> evals/.cache (gitignore)
$PY $M rewrites               # viet lai LLM MOT lan -> .cache/rewrites.json
$PY $M queries --model oa-small
$PY $M embed --model oa-large --max-usd 1 && $PY $M queries --model oa-large
for m in st-minilm st-e5 st-bge; do
  $PY $M embed --model $m                      # lan dau tai model tu HF: thoi gian nap lan nay KHONG dung de bao cao
  HF_HUB_OFFLINE=1 $PY $M queries --model $m  # nap tu cache nong: do nap, p50/p95, RSS
done
$PY $M parity
$PY $M evaluate --out-json <reports>/rag-embedding-results.json --out-md <reports>/rag-embedding-results.md
$PY -m pytest tests/test_embedding_experiment_core.py"""


def _ci(d: Dict) -> str:
    return f"{d['diff']:+.3f} [{d['lo']:+.3f}, {d['hi']:+.3f}]"


def _table(head: List[str], rows: List[List[str]]) -> str:
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] +
                     ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]) + "\n"


def _headline(r: Dict, ver: str, name: str, strategy: str) -> str:
    res, ci = r["results"][ver][name][strategy], r["ci"][ver][name].get(strategy, {})
    rows = []
    for m in ORDER:
        if m not in res:
            status = r["models"][m]["status"]
            rows.append([m, "KHONG CHAY: " + (status if status != "ok" else "thieu vector truy van cho chien luoc nay"),
                         "", "", "", "", ""])
            continue
        a = res[m]["by_group"]["all"]
        c = ci.get(m, {}).get("all")
        rows.append([m, f"{a['recall']:.3f} ({a['hits']}/{a['n']})", f"{a['mrr']:.3f}",
                     "co so" if c is None else _ci(c["recall"]), "" if c is None else VERDICT_TEXT[c["recall"]["verdict"]],
                     "" if c is None else _ci(c["mrr"]), "" if c is None else VERDICT_TEXT[c["mrr"]["verdict"]]])
    return _table(["Model", "recall@5", "MRR", "d recall vs oa-small [95% CI]", "ket luan recall", "d MRR [95% CI]",
                   "ket luan MRR"], rows)


def _groups(r: Dict, ver: str, name: str, strategy: str) -> str:
    res = r["results"][ver][name][strategy]
    ns = res[next(iter(res))]["by_group"] if res else {}
    head = ["Model"] + [f"{g} (n={ns[g]['n']})" for g in GROUPS if g in ns]
    return _table(head, [[m] + [f"{res[m]['by_group'][g]['recall']:.3f}" for g in GROUPS if g in ns]
                         for m in ORDER if m in res])


def _version_section(r: Dict, ver: str, sets: List[str], depth: str) -> str:
    out = []
    for name in sets:
        first = next(iter(r["results"][ver][name].get("raw", {}).values()), {"rows": []})
        n = len(first["rows"])
        out.append(f"{depth} {ver} / {name} (n={n} truy van)\n")
        for strategy in ("raw", "raw+rewrite"):
            if strategy not in r["results"][ver][name]:
                continue
            out.append(f"**{STRAT_NAME[strategy]}**: recall@5 tong + hieu so\n\n{_headline(r, ver, name, strategy)}")
            out.append(f"recall@5 theo nhom:\n\n{_groups(r, ver, name, strategy)}")
    return "\n".join(out)


def _missing(r: Dict) -> str:
    rows = [[v, s, d["n_queries"], d["n_relevant_ids"], d["n_missing_ids"], ",".join(d["missing_ids"]) or "-",
             len(d["queries_all_relevant_missing"]), d["recall_ceiling"]]
            for v, sets in r["precheck_missing"].items() for s, d in sets.items()]
    return _table(["golden", "tap", "truy van", "id relevant", "id thieu trong kho", "id thieu", "truy van het dap an",
                   "tran recall"], rows)


def _cost_line(r: Dict) -> str:
    big, rw = r["ops"]["oa-large"]["embed"] or {}, r["rewrites_meta"] or {}
    return (f"Chi phi OpenAI: oa-large embed kho {big.get('billed_tokens', 'n/a')} token = ${big.get('cost_actual_usd', 'n/a')}; "
            f"viet lai {rw.get('n', 'n/a')} truy van ({rw.get('model')}, prompt {rw.get('prompt_version')}) "
            f"{rw.get('billed_tokens', 'n/a')} token, {rw.get('unchanged_after_success', 'n/a')} ban viet lai giong truy van goc; "
            f"embed truy van khong dang ke.\n")


def _note(m: str, e: Dict, q: Dict) -> str:
    if m.startswith("st"):
        return (f"CPU cuc bo; cpu he thong tb {e.get('sys_cpu_pct_avg_this_run', 'n/a')}% (embed kho), "
                f"{q.get('sys_cpu_pct_avg', 'n/a')}% (truy van)")
    cost = f"; chi phi embed kho ${e['cost_actual_usd']}" if "cost_actual_usd" in e else ""
    return "vong API (mang)" + cost


def _ops(r: Dict) -> str:
    rows = []
    for m in ORDER:
        e, q = (r["ops"][m]["embed"] or {}), (r["ops"][m]["query"] or {})
        if not q and not e:
            rows.append([m, "khong chay", "", "", "", "", ""])
            continue
        t = e.get("truncation", {})
        over = (r["ops"]["oa-large"]["embed"] or {}).get("chunks_over_limit")  # cung van ban kho cho ca hai model OpenAI
        trunc = (f"{over} chunk > 8191 token (tiktoken)" if m.startswith("oa") else
                 " / ".join(f"{t[k]['pct']}%" for k in ("all", "qa_pair", "question") if k in t) + f" @{e.get('max_seq_length')}")
        embed_s = e.get("embed_seconds_total", e.get("api_wall_seconds", "n/a (vector luu san)" if m == "oa-small" else ""))
        rows.append([m, embed_s, q.get("load_seconds", "-"), f"{q.get('p50_ms', '')} / {q.get('p95_ms', '')}",
                     f"{q.get('peak_rss_mb_serve', '-')} / {e.get('peak_rss_mb_corpus_embed', '-')}", trunc,
                     _note(m, e, q)])
    return _table(["Model", "embed kho (s)", "nap model (s)", "1 truy van p50 / p95 (ms)", "RSS dinh phuc vu / embed kho (MB)",
                   "chunk bi cat: tat ca / qa_pair / question", "ghi chu"], rows)


def _ceiling(r: Dict, ver: str, name: str, strategy: str, m: str) -> str:
    """Ca oa-small lan model deu 100% o chien luoc nay: tap het kha nang phan biet (khong phai bang chung 'ngang')."""
    res = r["results"][ver][name].get(strategy, {})
    both = all(k in res and res[k]["by_group"]["all"]["recall"] == 1.0 for k in ("oa-small", m))
    return " (ca hai 100%: tap het kha nang phan biet)" if both else ""


def _summary(r: Dict, ver: str) -> str:
    """Moi model: o nao CI recall@5 loai 0 (tot hon / kem hon) va o nao ngang. Chi liet ke, khong dien giai them."""
    lines = []
    for m in ORDER[1:]:
        by: Dict[str, List[str]] = {"better": [], "worse": [], "tie": []}
        for n in (x for x in r["ci"][ver] if x != "pooled"):
            for strat, models in r["ci"][ver][n].items():
                if m in models:
                    by[models[m]["all"]["recall"]["verdict"]].append(f"{n}/{strat}")
        lines.append(f"- {m}: " + ("khong chay" if not any(by.values()) else
                                   "; ".join(f"{VERDICT_TEXT[k]}: {', '.join(v) or '-'}" for k, v in by.items())))
    return "\n".join(lines) + "\n"


def _verdict_matrix(r: Dict, ver: str) -> str:
    cols = [(n, s) for s in ("raw", "raw+rewrite") for n in ("main", "holdout") if n in r["ci"][ver]]
    rows = []
    for m in ORDER[1:]:
        cells = []
        for n, s in cols:
            c = r["ci"][ver][n].get(s, {}).get(m, {}).get("all")
            cells.append("khong chay" if c is None else
                         f"{_ci(c['recall'])} {c['recall']['verdict']}{_ceiling(r, ver, n, s, m)}")
        rows.append([m] + cells)
    return _table(["Model"] + [f"{n}/{s}" for n, s in cols], rows)


def render_markdown(r: Dict) -> str:
    ver = "repo"
    sets = [n for n in r["results"][ver] if n != "pooled"]
    parity = r["parity"] or {}
    idx = parity.get("indexes_on_knowledge_chunks") or []
    index_names = [i["name"] for i in idx]
    ann = any("hnsw" in i["def"].lower() or "ivfflat" in i["def"].lower() for i in idx)
    db_parity = {k: v for k, v in parity.get("memory_vs_pgvector_search", {}).items() if k != "mismatches"}
    golden_rows = [[v, f, s, "giong repo" if g["same_files_as_repo"] else "KHAC repo"]
                   for v, g in r["golden"].items() for f, s in g["sha256"].items()]
    model_rows = [[m, i["hf_or_api_name"], i["revision"], i["dims"], i["status"]] for m, i in r["models"].items()]
    out = [f"# RAG: so sanh model embedding ({r['generated']})\n",
           f"git HEAD {r['git_head'][:10]}; corpus {r['corpus']['n_chunks']} chunk interview_qa ({r['corpus']['n_qa_ids']} qa_id; "
           f"{r['corpus']['n_by_chunk_type']}), vector 3-small doc tu ai_db. Mot duong tim cho moi model: cosine toan kho -> "
           f"k*OVERFETCH(4) -> dedup qa_id -> top-5; khong bo loc category/difficulty. Bootstrap ghep cap theo truy van, "
           f"{r['bootstrap']['resamples']} lan, seed {r['bootstrap']['seed']}.\n",
           _cost_line(r),
           "## Model va ban ghim\n", _table(["id", "model / repo", "revision HF (hoac API)", "dim", "trang thai"], model_rows),
           "## Golden (SHA-256 file)\n", _table(["ban", "file", "sha256", "so voi repo"], golden_rows),
           "## Kiem tra truoc: id relevant khong con trong kho\n", _missing(r),
           "## Cong kiem tra tuong duong\n",
           f"- vector luu vs embed lai 20 chunk bang 3-small: {parity.get('stored_vs_reembedded_3small')}\n"
           f"- trong bo nho vs PgKnowledgeRepository.search (oa-small, raw): {db_parity}\n"
           f"- index tren knowledge_chunks: {index_names} -> "
           f"{'co index ANN: top-5 co the lech nhe' if ann else 'KHONG co index ANN (hnsw/ivfflat): ai_db tim chinh xac (quet toan bang), nen trung het la dung ky vong'}\n",
           f"## Ket qua chinh ({ver}, bo golden trong repo)\n", _version_section(r, ver, sets, "###"),
           "## Ma tran ket luan (recall@5, hieu so so voi oa-small [95% CI] + ket luan)\n", _verdict_matrix(r, ver),
           "Tom tat theo luat (chi liet ke o nao CI loai 0, khong ngoai suy):\n\n" + _summary(r, ver)]
    if "pooled" in r["results"][ver]:
        out += ["## Phu: gop main + holdout (KHONG dung de ket luan thang/thua)\n", _version_section(r, ver, ["pooled"], "###")]
    for other in (v for v in r["golden"] if v != ver):
        if r["golden"][other]["same_files_as_repo"]:
            out.append(f"## Golden {other}\n\nFile giong het ban repo (cung SHA-256), ket qua trung, khong lap lai.\n")
        elif other in r["results"]:
            out += [f"## Golden {other} (file KHAC repo)\n", _version_section(r, other, [n for n in r["results"][other] if n != "pooled"], "###"),
                    _verdict_matrix(r, other)]
    out += ["## Van hanh (4 thread CPU, nhu VM e2-standard-4)\n",
            "LUU Y: do tren may dev 6 nhan / 12 luong, KHONG phai VM e2-standard-4. May co nen ~40% CPU (antivirus, tien trinh "
            "khac) va Phase 2 chay song song, nen thoi gian chi mang tinh tham khao (cot cpu he thong tb cho thay muc tai). "
            "Truy van do batch 1, bo 3 lan khoi dong; thoi gian OpenAI la vong API (mang), khong so truc tiep voi CPU cuc bo.\n",
            _ops(r),
            "## Luat quyet dinh (ghi truoc khi chay)\n",
            "Mot model chi thang ve chat luong neu khoang tin cay 95% bootstrap cua hieu so (model - oa-small, theo truy van) "
            "KHONG chua 0 (ket luan 'TOT HON'/'KEM HON' o tren). Con lai coi la ngang va quyet theo van hanh. Golden chi 24 + 32 "
            "truy van nen chi phat hien chenh lech lon; nhieu so sanh (4 model x 2 tap x 2 chien luoc) chua hieu chinh da so sanh. "
            "Can duoi CI dung bang 0 tinh la ngang. Chi so chinh theo plan la raw chi vector; duong production la hybrid "
            "(BM25 + vector + topic_id, RRF) + viet lai, KHONG do o day nen khong ngoai suy sang production.\n",
            "## Lenh tai lap\n", "```\n" + REPRO + "\n```\n"]
    return "\n".join(out)
