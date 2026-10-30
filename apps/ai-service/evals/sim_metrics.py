"""Chi so tang 3 tu cac phien gia lap (design 09 muc 10.2, NFR-AI-QUAL09..12, 15). Ham thuan, khong goi mang."""
from collections import Counter
from statistics import mean
from typing import Dict, List, Optional

from app.models_common import LEVEL_CONFIG
from app.models_interview import InterviewPlan
from app.text_similarity import jaccard
from app.time_budget import turn_cap
from evals.personas import Persona


def _rate(hits: List[bool]) -> Optional[float]:
    return round(sum(hits) / len(hits), 3) if hits else None


def slope(values: List[int]) -> float:
    """He so goc hoi quy tuyen tinh cua quy dao do kho theo thu tu luot."""
    n = len(values)
    if n < 2:
        return 0.0
    xs = range(n)
    mx, my = (n - 1) / 2, mean(values)
    den = sum((x - mx) ** 2 for x in xs)
    return sum((x - mx) * (y - my) for x, y in zip(xs, values)) / den


def _overall(s: Dict) -> float:
    return s["report"]["overall"]["score"]


def discrimination(sessions: Dict[str, Dict], personas: Dict[str, Persona]) -> Dict:
    groups: Dict[tuple, Dict[str, float]] = {}
    for pid, s in sessions.items():
        p = personas[pid]
        if not p.behaviors:
            groups.setdefault((p.level, p.track), {})[p.quality] = _overall(s)
    full = [g for g in groups.values() if len(g) == 3]
    verdict_ok = [sessions[pid]["report"]["overall"]["verdict"] in
                  (("meets", "exceeds") if personas[pid].quality == "strong" else ("below",))
                  for pid in sessions if not personas[pid].behaviors and personas[pid].quality != "average"]
    return {"ordered": sum(g["strong"] > g["average"] > g["weak"] for g in full), "groups": len(full),
            "gap_strong_weak": round(mean(g["strong"] - g["weak"] for g in full), 2) if full else None,
            "verdict_ok": _rate(verdict_ok)}


def adaptation(sessions: Dict[str, Dict], personas: Dict[str, Persona]) -> Dict:
    ok, hints = [], {"strong": [], "weak": []}
    for pid, s in sessions.items():
        p = personas[pid]
        if p.behaviors or p.quality == "average":
            continue
        diffs = [t["difficulty"] for t in s["turns"] if t["phase"] != "wrap_up"]
        ok.append(slope(diffs) > 0 if p.quality == "strong" else slope(diffs) < 0)
        hints[p.quality].append(sum(t["turn_kind"] == "hint" for t in s["turns"]) / max(1, len(s["turns"])))
    return {"slope_direction_ok": _rate(ok),
            "hint_rate": {q: round(mean(v), 3) if v else None for q, v in hints.items()}}


def constraints(sessions: Dict[str, Dict], personas: Dict[str, Persona]) -> Dict:
    over_cap, phases_ok, repeats, total = 0, [], 0, 0
    for pid, s in sessions.items():
        plan = InterviewPlan.model_validate(s["plan"])
        over_cap += len(s["turns"]) > turn_cap(plan)
        if "end_early" not in personas[pid].behaviors and s["report"]["session"]["end_reason"] != "time_hard_limit":
            seen = {t["phase"] for t in s["turns"]}
            phases_ok.append({"intro", "technical", "scenario", "wrap_up"} <= seen)  # 4 phase (design 09)
        qs = [t["question"] for t in s["turns"]]
        repeats += sum(any(jaccard(q, prev) >= 0.8 for prev in qs[:i]) for i, q in enumerate(qs))
        total += len(qs)
    return {"sessions_over_turn_cap": over_cap, "all_phases_reached": _rate(phases_ok),
            "repeat_rate": round(repeats / total, 3) if total else None,
            "follow_up_limit_violations": _follow_up_violations(sessions, personas)}


def _follow_up_violations(sessions: Dict[str, Dict], personas: Dict[str, Persona]) -> int:
    """So topic co so luot follow-up/hint/clarify vuot gioi han cua level (FR-AI-035)."""
    bad = 0
    for pid, s in sessions.items():
        cfg = LEVEL_CONFIG[personas[pid].level]
        for ph in s["plan"]["phases"]:
            limit = cfg["max_fu_scn"] if ph["phase"] == "scenario" else cfg["max_fu"]
            for t in ph["topics"]:
                extra = sum(1 for x in s["turns"] if x["topic_id"] == t["id"] and x["turn_kind"] != "main")
                bad += extra > limit
    return bad


def report_quality(sessions: Dict[str, Dict], personas: Dict[str, Persona]) -> Dict:
    """Recall lo hong: topic does_not_know da hoi co trong improvements (qua evidence_turns hoac ten topic).
    Diem manh sai: strengths dan chung luot thuoc topic does_not_know."""
    recall, false_strengths, closed_fast = [], 0, []
    for pid, s in sessions.items():
        p, rep = personas[pid], s["report"]
        topic_of = {t["turn_number"]: t["topic_id"] for t in s["turns"]}
        titles = {t["id"]: (t["title"], t.get("catalog_ref")) for ph in s["plan"]["phases"] for t in ph["topics"]}
        gaps = {tid for tid, (_, ref) in titles.items() if ref in p.does_not_know and tid in topic_of.values()}
        flagged = {topic_of.get(n) for i in rep.get("improvements", []) for n in i["evidence_turns"]}
        flagged |= {tid for tid in gaps for i in rep.get("improvements", []) if titles[tid][0] in i["point"]}
        recall += [g in flagged for g in gaps]
        # cung cach doi chieu nhu recall: evidence_turns hoac ten topic trong point
        false_strengths += sum(1 for st in rep.get("strengths", []) for g in gaps
                               if g in {topic_of.get(n) for n in st["evidence_turns"]} or titles[g][0] in st["point"])
        # topic khong biet phai dong trong <= 2 luot sau luot dau lo ra (design 09 muc 10.2)
        closed_fast += [sum(1 for t in s["turns"] if t["topic_id"] == g) - 1 <= 2 for g in gaps]
    return {"gap_recall": _rate(recall), "gaps_asked": len(recall), "false_strengths": false_strengths,
            "unknown_topic_closed_within_2": _rate(closed_fast)}


def injection(sessions: Dict[str, Dict], personas: Dict[str, Persona]) -> Dict:
    pairs = [(_overall(s), _overall(sessions[personas[pid].base_id])) for pid, s in sessions.items()
             if "injection_attempt" in personas[pid].behaviors and personas[pid].base_id in sessions]
    return {"pairs": len(pairs), "no_score_gain": _rate([inj <= base for inj, base in pairs])}


def question_bank(sessions: Dict[str, Dict]) -> Dict:
    """Cau chinh phan technical lay tu kho interview_qa (question_source = bank) va so topic ky thuat co cau trong kho."""
    main = [t for s in sessions.values() for t in s["turns"] if t["phase"] == "technical" and t["turn_kind"] == "main"]
    topics = [t for s in sessions.values() for ph in s["plan"]["phases"] if ph["phase"] == "technical"
              for t in ph["topics"]]
    return {"technical_main_turns": len(main), "from_bank": _rate([t.get("question_source") == "bank" for t in main]),
            "fallback": _rate([t.get("question_source") == "fallback" for t in main]),
            "topics_with_bank": _rate([bool(t.get("bank_questions")) for t in topics])}


def _support_rates(support: List[str]) -> Dict:
    return {"points": len(support), **{k: _rate([x == k for x in support]) for k in ("supported", "no_source")}}


def grounding(sessions: Dict[str, Dict]) -> Dict:
    """Evaluator v4 (Phase 03a): ti le y da giu duoc tai lieu ung ho / khong co nguon, va luot diem khong bam nguon
    (confidence = low). v3 / mock khong co support nen bi bo qua. Y bi tai lieu bac bo KHONG nam trong `evidence`
    (postcheck bo khoi covered) nen `points` khong gom chung; dem qua `sources`, la can duoi: bo trung theo id, bo id
    khong co ref. So dung: log `evaluator_sources contradicted=N`."""
    evals = [t["evaluation"] for s in sessions.values() for t in s["turns"] if t.get("evaluation")]
    rated = [ev["confidence"] for ev in evals if ev.get("confidence")]
    refuted = [x for ev in evals for x in ev.get("sources", []) if x.get("support") == "contradicted"]
    return {**_support_rates([e["support"] for ev in evals for e in ev.get("evidence", []) if e.get("support")]),
            "contradicted_sources": len(refuted), "refuted_by_reference": sum(x["id"] == "R" for x in refuted),
            "turns_rated": len(rated), "low_confidence": _rate([c == "low" for c in rated])}


def grounding_breakdown(sessions: Dict[str, Dict]) -> Dict:
    """Tach y covered theo phase / loai luot / nguon cau hoi. Khi co `documents` (turn_source_recorder), tach them y
    no_source theo luot co tai lieu hay khong: khong co thi LLM khong the trich, co ma khong trich moi can xem tiep."""
    points = [(t, e["support"]) for s in sessions.values() for t in s["turns"]
              for e in (t.get("evaluation") or {}).get("evidence", []) if e.get("support")]

    def by(key: str) -> Dict:
        groups: Dict[str, List[str]] = {}
        for t, support in points:
            groups.setdefault(str(t.get(key)), []).append(support)
        return {k: _support_rates(v) for k, v in sorted(groups.items())}

    missing = [t for t, support in points if support == "no_source"]
    known = [t for t in missing if "documents" in t]
    return {"phase": by("phase"), "turn_kind": by("turn_kind"), "question_source": by("question_source"),
            "no_source": {"no_documents": sum(not t["documents"] for t in known),
                          "with_documents": sum(bool(t["documents"]) for t in known),
                          "unrecorded": len(missing) - len(known)}}


def rag_health(sessions: Dict[str, Dict]) -> Dict[str, int]:
    """So request theo metadata.rag.status. Co `error` thi grounding cua lan chay khong dung lam moc: RAG tat giua
    chung lam luot khong co tai lieu, no_source tang gia."""
    return dict(Counter(c["metadata"]["rag"]["status"] for s in sessions.values() for c in s["calls"]
                        if (c.get("metadata") or {}).get("rag")))
