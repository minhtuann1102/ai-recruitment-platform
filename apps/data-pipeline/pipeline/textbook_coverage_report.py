"""Tinh bao cao do phu textbook (spec 012 T032, data-model §5, research R10). Ham thuan: khong doc file, khong goi mang / DB.

`build_report` nhan manifest + catalog + doan da xu ly (+ ket qua vector tuy chon) va tra dict de ghi `coverage-report.json`.
Kiem tra tu khoa: BM25 (textbook_keyword_rank) tren MOI doan, truy van = `query_en` cua tinh huong, chi xet doan co category
thuoc (category chinh cua track, "System Design"); trung khi mot trong 3 doan dau mang ma tinh huong.
"""
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from .textbook_catalog_tracks import Track
from .textbook_keyword_rank import Bm25
from .textbook_source_manifest import Source, active_pages

GENERAL_CATEGORY = "System Design"
TOP_K = 3
SC_RATIO = 0.8  # SC-001 (>= 3 doan) va SC-004 (truy hoi): it nhat 80% tinh huong

ScenarioQuery = Tuple[str, str, List[str]]  # (ma tinh huong, query_en, cac category duoc xet)


def allowed_categories(track: Track) -> List[str]:
    return sorted({track.main_category, GENERAL_CATEGORY})


def scenario_queries(tracks: Dict[str, Track], queries: Dict[str, Dict]) -> List[ScenarioQuery]:
    """Cac tinh huong co `query_en`, theo thu tu catalog; tinh huong khong co dong truy van bi bo qua."""
    result = []
    for track in tracks.values():
        for scn in track.scenario_ids:
            query = ((queries.get(scn) or {}).get("query_en") or "").strip()
            if query:
                result.append((scn, query, allowed_categories(track)))
    return result


def drop_reasons(decisions: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
    """So quyet dinh `drop` theo ly do (tu file decisions cua nguon)."""
    return dict(sorted(Counter(d.get("reason") or "other" for d in decisions.values() if d.get("verdict") == "drop").items()))


def _scenario_ids(record: Dict) -> List[str]:
    return (record.get("metadata") or {}).get("scenario_ids") or []


def _ratio(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def _source_rows(sources: List[Source], records_by_source: Dict[str, List[Dict]],
                 drops: Dict[str, Dict[str, int]]) -> List[Dict]:
    return [{
        "source_id": s.source_id, "status": s.status, "kind": s.kind, "license": s.license,
        "license_class": s.license_class,
        "pages_used": sum(1 for p in s.pages if p.status == "use"),
        "pages_excluded": sum(1 for p in s.pages if p.status != "use"),
        "chunks": len(records_by_source.get(s.source_id, [])),
        "drops": drops.get(s.source_id, {}),
    } for s in sources]


def _track_rows(sources: List[Source], tracks: Dict[str, Track], records: List[Dict]) -> Dict[str, Dict]:
    official = {t: set() for t in tracks}
    for source, page in active_pages(sources):
        if source.kind == "official":
            for track_id in page.tracks:
                official.get(track_id, set()).add(source.source_id)
    chunk_counts = Counter(t for r in records for t in (r.get("metadata") or {}).get("tracks") or [])
    return {t: {"official_sources": len(official[t]), "chunks": chunk_counts[t]} for t in tracks}


def build_report(sources: List[Source], tracks: Dict[str, Track], queries: Dict[str, Dict],
                 records_by_source: Dict[str, List[Dict]], drops: Optional[Dict[str, Dict[str, int]]] = None,
                 vector_hits: Optional[Dict[str, bool]] = None) -> Dict[str, Any]:
    """`vector_hits` None = khong chay --db (khong co khoa vector_hit); co thi {ma tinh huong: bool}."""
    records = [r for recs in records_by_source.values() for r in recs]
    bm25 = Bm25(records)
    chunk_counts = Counter(scn for r in records for scn in _scenario_ids(r))
    scenarios: Dict[str, Dict[str, Any]] = {}
    for track in tracks.values():
        allowed = set(allowed_categories(track))
        for scn in track.scenario_ids:
            query = ((queries.get(scn) or {}).get("query_en") or "").strip()
            top = bm25.top(query, TOP_K, lambda d: d.get("category") in allowed) if query else []
            rank = next((i for i, doc in enumerate(top, start=1) if scn in _scenario_ids(doc)), None)
            row: Dict[str, Any] = {"track": track.track_id, "chunks": chunk_counts[scn],
                                   "keyword_hit": rank is not None, "first_hit_rank": rank}
            if vector_hits is not None:
                row["vector_hit"] = bool(vector_hits.get(scn, False))
            scenarios[scn] = row
    n = len(scenarios)
    has_chunks = [s for s, r in scenarios.items() if r["chunks"] >= 1]
    gaps: Dict[str, List[str]] = {
        "zero_chunks": [s for s, r in scenarios.items() if r["chunks"] == 0],
        "under_3_chunks": [s for s, r in scenarios.items() if 1 <= r["chunks"] < 3],
        "retrieval_miss": [s for s in has_chunks if not scenarios[s]["keyword_hit"]],
    }
    totals: Dict[str, Any] = {
        "chunks": len(records), "scenarios": n,
        "ratio_ge1": _ratio(sum(1 for r in scenarios.values() if r["chunks"] >= 1), n),
        "ratio_ge3": _ratio(sum(1 for r in scenarios.values() if r["chunks"] >= 3), n),
        "keyword_hit_ratio": _ratio(sum(1 for r in scenarios.values() if r["keyword_hit"]), n),
        "vector_hit_ratio": None,
    }
    sc004 = totals["keyword_hit_ratio"] >= SC_RATIO
    if vector_hits is not None:
        gaps["vector_miss"] = [s for s in has_chunks if not scenarios[s]["vector_hit"]]
        totals["vector_hit_ratio"] = _ratio(sum(1 for r in scenarios.values() if r["vector_hit"]), n)
        sc004 = sc004 and totals["vector_hit_ratio"] >= SC_RATIO
    totals["sc001"] = bool(n) and totals["ratio_ge1"] == 1.0 and totals["ratio_ge3"] >= SC_RATIO
    totals["sc004"] = bool(n) and sc004
    return {"sources": _source_rows(sources, records_by_source, drops or {}),
            "tracks": _track_rows(sources, tracks, records), "scenarios": scenarios, "gaps": gaps, "totals": totals}
