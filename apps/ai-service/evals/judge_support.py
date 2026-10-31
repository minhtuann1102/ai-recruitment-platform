"""LLM-as-judge cho do bam nguon (Phase 05 hybrid RAG): y Evaluator ghi `supported` co that su duoc tai lieu ung ho
khong, va y `no_source` la do Evaluator khong trich, truy hoi khong lay ra hay kho thieu.

Chua hieu chinh voi nhan nguoi thi KHONG dung lam so do (evals/support_set.py). Judge phai chep doan tai lieu lam can cu;
code kiem tu cua doan do co trong tai lieu, khong thi `entailed` / `contradicted` bi tinh la `unrelated` (giu
`raw_verdict`). Khong doi khop lien tuc: model hay bo markdown hoac danh so du y dung (`QUOTE_COVERAGE`).
Doi chung (--control) ghep y voi tai lieu topic khac: chi do judge de dai khi tai lieu lech han, khong noi gi ve tai lieu
cung topic. Ba vong mo phong lap lai y: bao cao ca so tren y khac nhau (`unique`).
  python -m evals.judge_support ../../plans/reports/eval-sim-a.json [...] --control --triage --out <file>
"""
import argparse
import asyncio
import json
import random
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Awaitable, Callable, Dict, List, Literal, Optional

from pydantic import BaseModel

from app.evaluation_checks import _words
from app.llm.gateway import get_gateway
from app.llm.usage import UsageCollector
from app.plan_snippets import memory_retriever
from app.prompts.store import PromptStore, wrap_untrusted
from app.rag.models import SearchFilters

PROMPTS = PromptStore(Path(__file__).with_name("prompts"))
REPORTS = Path(__file__).resolve().parents[3] / "plans" / "reports"
MAX_DOC_CHARS = 6000  # Evaluator doc ca chunk; cat ngan se thien ve `unrelated`
VERDICTS = ("entailed", "contradicted", "unrelated")
COVERED = ("entailed", "contradicted")
QUOTE_WORDS, QUOTE_COVERAGE = 3, 0.8  # 0.8 -> 1.0 doi ket qua < 0.01; 0.6 de lot doi chung (quote che tu y dang xet)
Search = Callable[[str], Awaitable[List[str]]]


class SupportVerdict(BaseModel):
    verdict: Literal["entailed", "contradicted", "unrelated"]
    doc_id: Optional[str] = None
    doc_quote: str = ""
    reason: str


def items_from_sessions(sessions: Dict[str, Dict], run: str = "") -> List[dict]:
    """`supported`: tai lieu da trich. `no_source`: moi tai lieu cua luot; luot khong co tai lieu van giu de tim toan kho
    (y o intro la chuyen du an cua ung vien, kho khong the co nen `triage` bo qua)."""
    items = []
    for pid, s in sessions.items():
        topics = {t["id"]: t["title"] for ph in s["plan"]["phases"] for t in ph["topics"]}
        for t in s["turns"]:
            docs = t.get("documents") or []
            for n, e in enumerate((t.get("evaluation") or {}).get("evidence", [])):
                if e.get("support") not in ("supported", "no_source"):
                    continue
                chosen = docs if e["support"] == "no_source" else [d for d in docs if d["id"] in e["source_ids"]]
                if chosen or e["support"] == "no_source":
                    items.append({"id": f"{run}:{pid}#{t['turn_number']}#{n}", "support": e["support"],
                                  "claim": e["claim"], "quote": e["quote"], "question": t["question"],
                                  "phase": t["phase"], "topic": topics.get(t["topic_id"], ""),
                                  "question_source": str(t.get("question_source")),
                                  "docs": [{"id": d["id"], "text": d["text"][:MAX_DOC_CHARS]} for d in chosen]})
    return items


def unique(items: List[dict]) -> List[dict]:
    """Moi cap (cau hoi, y) mot lan: phien lap lai giua cac vong khong doc lap. Uu tien ban co tai lieu."""
    return list({(i["question"], i["claim"]): i for i in sorted(items, key=lambda i: bool(i["docs"]))}.values())


def control_items(items: List[dict], seed: int = 7) -> List[dict]:
    """Moi y `supported` khac nhau ghep ngau nhien voi mot bo tai lieu cua topic khac."""
    base, rng, out = unique([i for i in items if i["support"] == "supported"]), random.Random(seed), []
    pool = list({i["docs"][0]["text"]: i for i in base}.values())
    for item in base:
        others = [o for o in pool if o["topic"] != item["topic"]]
        if others:
            out.append({**item, "id": f"control:{item['id']}", "docs": rng.choice(others)["docs"]})
    return out


def build_messages(item: dict, system: str) -> List[dict]:
    docs = "\n\n".join(f"[{d['id']}] {d['text']}" for d in item["docs"])
    body = "\n".join([f"question: {item['question']}", wrap_untrusted("claim", item["claim"]),
                      wrap_untrusted("quote", item["quote"]), wrap_untrusted("documents", docs)])
    return [{"role": "system", "content": system}, {"role": "user", "content": body}]


def coverage(quote: str, text: str) -> float:
    words = _words(quote)
    found = set(_words(text))
    return sum(w in found for w in words) / len(words) if len(words) >= QUOTE_WORDS else 0.0


def checked(item: dict, out: SupportVerdict) -> dict:
    """Can cu phai nam trong tai lieu cua muc; judge hay bo sot `doc_id` nen lay tai lieu khop nhat lam `doc_id`."""
    best = max(item["docs"], key=lambda d: coverage(out.doc_quote, d["text"]), default=None)
    valid = bool(best) and coverage(out.doc_quote, best["text"]) >= QUOTE_COVERAGE
    verdict = out.verdict if valid else "unrelated"
    return {**out.model_dump(), "raw_verdict": out.verdict, "verdict": verdict, "doc_id": best["id"] if valid else None}


async def judge_items(items: List[dict], gateway=None, concurrency: int = 6) -> Dict[str, dict]:
    """Loi mot muc (het retry) -> verdict None, khong bo ca lan chay da tra phi."""
    gateway, prompt, sem = gateway or get_gateway(), PROMPTS.get("judge_support"), asyncio.Semaphore(concurrency)

    async def one(item):
        try:
            async with sem:
                result = await gateway.complete("judge", build_messages(item, prompt.text), SupportVerdict,
                                                prompt_version=prompt.version)
            return item["id"], checked(item, result.data)
        except Exception as err:
            return item["id"], {"verdict": None, "raw_verdict": None, "doc_id": None, "reason": type(err).__name__}

    return dict(await asyncio.gather(*(one(i) for i in items)))


def rates(items: List[dict], results: Dict[str, dict]) -> Dict:
    """Ti le nhan da kiem can cu; `raw_entailed` truoc khi kiem; `failed` dem rieng de khong lam lech mau so."""
    judged = [results[i["id"]] for i in items if i["id"] in results]
    done = [r for r in judged if r["verdict"]]
    counts = Counter(r["verdict"] for r in done)
    return {"n": len(done), "failed": len(judged) - len(done),
            **{v: round(counts[v] / len(done), 3) if done else None for v in VERDICTS},
            "raw_entailed": round(sum(r["raw_verdict"] == "entailed" for r in done) / len(done), 3) if done else None}


async def triage(items: List[dict], results: Dict[str, dict], search: Search, gateway=None) -> Dict:
    """Y `no_source` khac nhau ngoai intro -> not_cited (tai lieu cua luot co noi toi), retrieval_miss (chi tim toan kho
    moi thay), corpus_gap (toan kho khong thay; la can tren vi tim toan kho cung co the truot), unknown (judge / tim loi).
    `contradicted` cung tinh la co noi toi: kho phu y do, chi la judge thay nguoc chieu."""
    missing = [i for i in unique(items) if i["support"] == "no_source" and i["phase"] != "intro"]
    outcome = {i["id"]: "not_cited" for i in missing if (results.get(i["id"]) or {}).get("verdict") in COVERED}
    outcome.update({i["id"]: "unknown" for i in missing if i["docs"] and not results.get(i["id"], {}).get("verdict")})

    sem = asyncio.Semaphore(4)

    async def lookup(item):
        try:
            async with sem:
                return item, await search(item["claim"])
        except Exception:
            outcome[item["id"]] = "unknown"
            return item, None

    found = await asyncio.gather(*(lookup(i) for i in missing if i["id"] not in outcome))
    outcome.update({i["id"]: "corpus_gap" for i, chunks in found if chunks == []})
    searched = [{**i, "docs": [{"id": f"K{n}", "text": c[:MAX_DOC_CHARS]} for n, c in enumerate(chunks, 1)]}
                for i, chunks in found if chunks]
    corpus = await judge_items(searched, gateway)
    for key, r in corpus.items():
        outcome[key] = ("unknown" if not r["verdict"] else "retrieval_miss" if r["verdict"] in COVERED else "corpus_gap")
    by_item = {i["id"]: i for i in missing}
    groups = Counter((by_item[k]["phase"], v) for k, v in outcome.items())
    return {"n": len(missing), **Counter(outcome.values()), "by_phase": {f"{p}:{v}": n for (p, v), n in groups.items()},
            "outcomes": outcome, "corpus_results": corpus}


def corpus_search(retriever) -> Search:
    """Toan kho (qa_pair + textbook), khong loc topic. Mot duong BM25 / vector loi thi bao loi: ket qua mot phan se bien
    thanh corpus_gap gia."""
    async def search(claim: str) -> List[str]:
        collector = UsageCollector()
        chunks = await retriever.hybrid.search(claim, SearchFilters(chunk_type="qa_pair"), 5, collector)
        if collector.rag_errors:
            raise RuntimeError(collector.rag_errors[0])
        return [c.content for c in chunks]
    return search


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("runs", nargs="+", type=Path, help="file phien gia lap co `documents`")
    parser.add_argument("--control", action="store_true", help="doi chung: y ghep tai lieu cua topic khac")
    parser.add_argument("--triage", action="store_true", help="phan loai no_source, can ai_db")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    items = [i for run in args.runs
             for i in items_from_sessions(json.loads(run.read_text("utf-8"))["sessions"], run.stem)]
    out = args.out or REPORTS / f"judge-support-{datetime.now():%y%m%d-%H%M}.json"
    out.parent.mkdir(parents=True, exist_ok=True)

    def save(report: dict) -> None:
        out.write_text(json.dumps(report, ensure_ascii=False, indent=1), "utf-8")

    async def run() -> dict:
        judged = [i for i in items if i["docs"]]
        results = await judge_items(judged)
        by = lambda key, group: {v: rates([i for i in group if i[key] == v], results)  # noqa: E731
                                 for v in sorted({i[key] for i in group})}
        supported = [i for i in judged if i["support"] == "supported"]
        report = {"runs": [r.stem for r in args.runs], "prompt": PROMPTS.get("judge_support").version,
                  "uncalibrated": True, "by_support": by("support", judged),
                  "by_support_unique": by("support", unique(judged)),
                  "supported_by_question_source": by("question_source", supported),
                  "supported_by_question_source_unique": by("question_source", unique(supported)),
                  "results": results, "items": items}
        save(report)  # moi buoc ghi ngay: buoc sau loi khong mat ket qua da tra phi
        if args.control:
            controls = control_items(items)
            report["control"] = {**rates(controls, c := await judge_items(controls)), "results": c}
            save(report)
        if args.triage:
            try:
                retriever = memory_retriever()
                await retriever.hybrid.bm25.index()  # nap corpus truoc: tim co gioi han RESOLVE_BUDGET_S se tinh la loi
                report["triage"] = await triage(items, results, corpus_search(retriever))
            except Exception as err:  # RAG tat (retriever None) hay khong nap duoc corpus
                report["triage"] = {"error": repr(err)}
        return report

    report = asyncio.run(run())
    save(report)
    print(json.dumps({k: v for k, v in report.items() if k not in ("results", "items", "control")},
                     ensure_ascii=False)[:1500])
    print(f"Da ghi {out}")


if __name__ == "__main__":
    main()
