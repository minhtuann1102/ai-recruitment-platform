"""Planner uu tien topic co cau trong kho o level dang hoi (next-phase-plan Phase C muc 3).

Topic khong co cau hoi trong kho thi Interviewer tu dat cau, khong co dap an chuan: do 30/10 `supported` cua cau
AI tu dat 0.63 so voi 0.88 cua cau kho. Luc start dem so cau hoi doc duoc (spoken_ok) theo topic va do kho, chay
song song voi Planner nen khong them do tre; sau khi co plan, topic ky thuat lay tu catalog ma kho khong co cau nao
gan do kho bat dau thi doi sang topic chua dung co cau, uu tien cung nhom (category). Ap dung cho ca Planner LLM va
plan du phong, khong doi prompt. Topic JD giu nguyen. So dem la can tren: chua ap dieu kien trung tu cua
question_bank.rank, nen topic dem > 0 van co the khong co cau nao duoc chon.
"""
import asyncio
import logging
import time
from typing import Callable, Dict, Iterable, Optional, Tuple

from .catalog.models import TrackCatalog
from .mock_planner import catalog_topic
from .models_interview import InterviewPlan
from .plan_snippets import swallow_task_result
from .rag.difficulty import difficulty_bucket
from .rag.question_bank import gap

log = logging.getLogger("ai_service.rag")
Coverage = Dict[str, Dict[Optional[str], int]]  # topic_id -> do kho (easy/medium/hard/None) -> so cau hoi
COVERAGE_TTL_S = 600  # kho chi doi khi DE nap lai; dem lai moi 10 phut la du
COVERAGE_WAIT_S = 1.0  # cho them toi da sau khi Planner xong; qua han thi giu plan nhu cu
_cache: Dict[Tuple[str, ...], Tuple[float, Coverage]] = {}


async def load_coverage(retriever, topic_ids: Iterable[str], clock: Callable[[], float] = time.monotonic) -> Coverage:
    """So cau hoi trong kho theo topic; RAG tat, tat ngan hang cau hoi, repo khong ho tro hoac loi thi rong
    (rong = khong biet, plan giu nguyen)."""
    count = getattr(getattr(retriever, "repo", None), "count_bank", None)
    if retriever is None or not getattr(retriever, "question_bank", True) or count is None:
        return {}
    key = tuple(sorted(set(topic_ids)))
    hit = _cache.get(key)
    if hit and clock() - hit[0] < COVERAGE_TTL_S:
        return hit[1]
    try:
        coverage = await count(list(key))
    except Exception as err:  # chi la uu tien chon topic: loi thi chay nhu truoc, khong bao loi RAG cua phien
        log.warning("bank_coverage_failed error=%s", type(err).__name__)
        return {}
    _cache[key] = (clock(), coverage)
    return coverage


def start_coverage(retriever, catalog: TrackCatalog, level: str) -> "asyncio.Task[Coverage]":
    """Bat dau dem truoc khi goi Planner: chay song song, khong cong them vao thoi gian start. Task khong bao gio bi
    huy (huy psycopg co the mat toi 5 s); Planner loi, request bi huy hay qua han cho thi task van chay xong va nap
    cache cho lan start sau (statement_timeout 15 s chan truy van treo)."""
    task = asyncio.ensure_future(load_coverage(retriever, [t.id for t in catalog.topics_for(level)]))
    task.add_done_callback(swallow_task_result)
    return task


async def settle(task: "asyncio.Task[Coverage]") -> Coverage:
    """Ket qua dem neu xong trong COVERAGE_WAIT_S; khong thi bo qua lan nay, plan giu nguyen."""
    done, _ = await asyncio.wait({task}, timeout=COVERAGE_WAIT_S)
    if task in done:
        return task.result()
    log.warning("bank_coverage_timeout wait_s=%s", COVERAGE_WAIT_S)
    return {}


def bank_count(coverage: Coverage, topic_id: str, difficulty: int) -> int:
    """So cau ma question_bank.pick dung duoc o do kho bat dau (lech toi da 1 bac; khong ro do kho tinh lech 1)."""
    bucket = difficulty_bucket(difficulty)
    return sum(n for d, n in coverage.get(topic_id, {}).items() if gap(d, bucket) < 2)


def prefer_covered(plan: InterviewPlan, catalog: TrackCatalog, level: str, coverage: Coverage,
                   keep: Iterable[str] = ()) -> InterviewPlan:
    """Doi topic catalog khong co cau trong kho sang topic chua dung co cau (cung nhom truoc, roi nhieu cau hon,
    roi thu tu catalog). Giu id, do kho bat dau va vi tri cua topic; khong co ung vien thi giu topic cu."""
    if not coverage:
        return plan
    level_topics = catalog.topics_for(level)
    by_id = {t.id: t for t in level_topics}  # chi dem topic cua level: topic ngoai danh sach khong biet so cau
    kept = set(keep)
    out = plan.model_copy(deep=True)
    used = {t.catalog_ref for ph in out.phases for t in ph.topics if t.catalog_ref}
    changed = False
    for ph in out.phases:
        if ph.phase != "technical":
            continue
        for i, topic in enumerate(ph.topics):
            ref = topic.catalog_ref
            if topic.source != "catalog" or ref not in by_id or ref in kept:
                continue
            if bank_count(coverage, ref, topic.start_difficulty) > 0:
                continue
            counts = {t.id: bank_count(coverage, t.id, topic.start_difficulty) for t in level_topics}
            candidates = [t for t in level_topics if t.id not in used and counts[t.id] > 0]
            if not candidates:
                continue
            best = min(candidates, key=lambda t: (t.category != by_id[ref].category, -counts[t.id]))
            ph.topics[i] = catalog_topic(topic.id, best, level).model_copy(
                update={"start_difficulty": topic.start_difficulty})
            used.add(best.id)
            changed = True
            log.info("planner_bank_swap topic=%s from=%s to=%s questions=%d", topic.id, ref, best.id, counts[best.id])
    return out if changed else plan
