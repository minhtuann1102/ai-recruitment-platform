"""Tong hop diem va bao cao cuoi buoi (docs/ai-service/05 muc 6.3-6.4). DIEM do code tinh.

Phan nhan xet la MOCK (template); se thay bang Reporter LLM. Reporter that khong duoc sua diem.
"""
import time
from typing import Dict, List

from .mock_evaluator import is_scored
from .models_interview import FinalizeRequest, FinalizeTurn

PHASE_WEIGHTS = {
    "fresher": {"intro": 0.15, "technical": 0.60, "scenario": 0.25},
    "junior": {"intro": 0.15, "technical": 0.55, "scenario": 0.30},
    "middle": {"intro": 0.20, "technical": 0.45, "scenario": 0.35},
    "senior": {"intro": 0.20, "technical": 0.35, "scenario": 0.45},
}
CRITERIA = ["technical_accuracy", "completeness", "extensibility", "relevance"]


def verdict(overall: float) -> str:
    return "exceeds" if overall >= 8.5 else "meets" if overall >= 7.0 else "near" if overall >= 5.0 else "below"


def _avg(values: List[float]) -> float:
    return round(sum(values) / len(values), 1) if values else 0.0


def _scored(turns: List[FinalizeTurn]) -> List[FinalizeTurn]:
    return [t for t in turns if t.phase != "wrap_up" and t.evaluation and is_scored(t.evaluation)]


def _confidence(req: FinalizeRequest, scored: List[FinalizeTurn], phases_scored: int) -> str:
    degraded = sum(1 for t in req.turns if t.evaluation and t.evaluation.degraded)
    evaluated = sum(1 for t in req.turns if t.evaluation)
    if len(scored) < 6 or (evaluated and degraded / evaluated > 0.2) or phases_scored < 3:
        return "low"
    return "medium" if len(scored) <= 9 else "high"


def _turn_comment(t: FinalizeTurn) -> str:
    ev = t.evaluation
    if ev.answer_type == "dont_know":
        return "Ứng viên chưa trả lời được câu này."
    if ev.answer_type == "manipulation":
        return "Câu trả lời cố tác động tới việc chấm điểm nên không được tính."
    got = f"Nêu được: {ev.covered_points[0]}. " if ev.covered_points else ""
    miss = f"Còn thiếu: {ev.missing_points[0]}." if ev.missing_points else "Đáp ứng đủ các ý chính."
    return (got + miss).replace("Nêu được: Nêu được ", "Nêu được ")


def build_report(req: FinalizeRequest) -> Dict:
    started = time.perf_counter()
    scored = _scored(req.turns)
    topics = []
    for phase_topic in [(ph.phase, t) for ph in req.plan.phases for t in ph.topics]:
        phase, topic = phase_topic
        ts = [t for t in scored if t.topic_id == topic.id]
        if not ts:
            continue
        hinted = next((x.hint_used for x in req.state.topics if x.id == topic.id), False)
        topics.append({"topic_id": topic.id, "title": topic.title, "phase": phase,
                       "score": _avg([t.evaluation.turn_score_10 for t in ts]), "hint_used": hinted,
                       "difficulty_path": [t.difficulty for t in ts],
                       "comment": _turn_comment(ts[-1]), "_turns": [t.turn_number for t in ts]})
    weights = PHASE_WEIGHTS[req.level]
    sections = [{"phase": ph, "score": _avg([t["score"] for t in topics if t["phase"] == ph]),
                 "weight": weights[ph]} for ph in weights if any(t["phase"] == ph for t in topics)]
    total_w = sum(s["weight"] for s in sections) or 1
    overall = round(sum(s["score"] * s["weight"] for s in sections) / total_w, 1)
    criteria = {c: _avg([getattr(t.evaluation.scores_10, c) for t in scored]) for c in CRITERIA}
    good = [t for t in topics if t["score"] >= 7.0]
    weak = sorted([t for t in topics if t["score"] < 5.0], key=lambda t: t["score"])
    kp = {t.id: t.key_points for ph in req.plan.phases for t in ph.topics}
    v = verdict(overall)
    return {
        "schema_version": 1, "status": "complete",
        "session": {"track": req.track, "level": req.level, "duration_s": req.duration_s,
                    "end_reason": req.end_reason, "evaluated_turns": len(scored),
                    "confidence": _confidence(req, scored, len(sections))},
        "overall": {"score": overall, "verdict": v,
                    "summary": f"[Mock] Kết quả tổng thể: {v}. Nhận xét chi tiết sẽ do Reporter LLM viết."},
        "sections": sections, "criteria": criteria,
        "topics": [{k: v for k, v in t.items() if k != "_turns"} for t in topics],
        "strengths": [{"point": f"Nắm tốt {t['title']}", "evidence_turns": t["_turns"]} for t in good[:3]],
        "improvements": [{"point": t["title"], "why": t["comment"], "evidence_turns": t["_turns"]}
                         for t in weak[:3]],
        "study_plan": [{"topic": t["title"], "priority": "high" if t["score"] < 3.5 else "medium",
                        "actions": [f"Ôn lại: {p}" for p in kp.get(t["topic_id"], [])[:3]], "resources": []}
                       for t in weak[:3]],
        "turns": [{"turn_number": t.turn_number, "topic_id": t.topic_id, "turn_kind": t.turn_kind,
                   "question": t.question, "scores": t.evaluation.scores_10.model_dump(),
                   "comment": _turn_comment(t)} for t in scored],
        "meta": {"difficulty_trajectory": [t.difficulty for t in scored], "degraded_turns":
                 [t.turn_number for t in req.turns if t.evaluation and t.evaluation.degraded],
                 "prompt_versions": {"evaluator": "mock", "reporter": "mock"},
                 "disclaimer": "Điểm do AI chấm, mang tính tham khảo cho việc luyện tập."},
        "metadata": {"model": "mock-rule-based", "latency_ms": int((time.perf_counter() - started) * 1000)},
    }
