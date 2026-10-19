"""Planner MOCK: dung ke hoach phong van tu topic catalog bang quy tac (khong LLM).

Ket qua cung hinh dang InterviewPlan that (docs/ai-service/02 3.3.2) de interview-service tich hop som.
"""
from typing import List, Optional

from .api_error import ApiError
from .catalog.loader import CatalogError, load_catalog
from .catalog.models import Scenario, Topic
from .models_common import LEVEL_CONFIG
from .models_cv import CvProfile
from .models_interview import InterviewPlan, PlanPhase, PlanTopic


def load_track(track: str):
    try:
        return load_catalog(track)
    except CatalogError:
        raise ApiError(422, "invalid_request", f"track khong ton tai: {track}", {"track": track})


def _overlap(text: str, skills: List[str]) -> int:
    low = text.lower()
    return sum(1 for s in skills if s.lower() in low)


def _rank(items, key_text, skills):
    # sort on dinh: nhieu ky nang trung CV len truoc, hoa thi giu thu tu catalog
    return sorted(items, key=lambda it: -_overlap(key_text(it), skills))


def _clamp(value: int, level: str) -> int:
    lo, hi = LEVEL_CONFIG[level]["bounds"]
    return max(lo, min(hi, value))


def _catalog_topic(tid: str, t: Topic, level: str) -> PlanTopic:
    return PlanTopic(
        id=tid, title=t.title, source="catalog", catalog_ref=t.id,
        objective=f"Đánh giá hiểu biết về {t.title} ở mức {level}",
        key_points=[f"Nêu được {c}" for c in t.key_concepts[:4]],
        start_difficulty=_clamp(LEVEL_CONFIG[level]["start"], level),
        opening_hint=f"Bắt đầu bằng câu hỏi tổng quan về {t.title}",
        backup_question=f"{t.title}: bạn hiểu như thế nào và đã áp dụng ra sao?")


def _scenario_topic(tid: str, s: Scenario, level: str) -> PlanTopic:
    return PlanTopic(
        id=tid, title=s.title, source="scenario", catalog_ref=s.id,
        objective="Đánh giá cách tiếp cận một tình huống thực tế",
        key_points=["Làm rõ yêu cầu và giả định", "Đề xuất thiết kế hoặc hướng giải quyết cụ thể",
                    "Nêu trade-off và rủi ro"],
        start_difficulty=_clamp(LEVEL_CONFIG[level]["start"], level),
        opening_hint=f"Đưa tình huống: {s.title}",
        backup_question=f"Tình huống: {s.title}. Bạn sẽ tiếp cận thế nào?")


def _intro_topic(tid: str, level: str, cv: Optional[CvProfile]) -> PlanTopic:
    start = _clamp(LEVEL_CONFIG[level]["start"], level)
    if cv and cv.track_relevance != "low" and cv.projects:
        p = cv.projects[0]
        tech = ", ".join(p.tech[:3]) or "công nghệ đã dùng"
        return PlanTopic(
            id=tid, title=f"Dự án {p.name} ({tech})", source="cv", cv_ref=p.id,
            objective="Đánh giá vai trò thật và quyết định kỹ thuật trong dự án",
            key_points=["Mô tả rõ phần việc của mình", f"Giải thích lý do chọn {tech}",
                        "Nêu khó khăn gặp phải và cách xử lý"],
            start_difficulty=start, opening_hint=f"Hỏi ứng viên kể về dự án {p.name}",
            backup_question="Bạn hãy kể về dự án gần nhất và phần việc chính của bạn?")
    return PlanTopic(
        id=tid, title="Giới thiệu bản thân và dự án gần nhất", source="generic",
        objective="Làm quen và nắm bối cảnh kinh nghiệm của ứng viên",
        key_points=["Giới thiệu ngắn gọn về nền tảng", "Mô tả một dự án và vai trò của mình",
                    "Nêu công nghệ đã dùng"],
        start_difficulty=start, opening_hint="Mời ứng viên giới thiệu bản thân và dự án gần nhất",
        backup_question="Bạn hãy giới thiệu về bản thân và dự án gần nhất bạn tham gia?")


def build_plan(track: str, level: str, duration_minutes: int, cv: Optional[CvProfile]) -> InterviewPlan:
    catalog = load_track(track)
    cfg = LEVEL_CONFIG[level]
    skills = [s.name for s in cv.skills] if cv else []
    scale = duration_minutes / 30
    m_intro, m_tech, m_scn = (max(1, round(m * scale)) for m in cfg["minutes"])
    n_tech = cfg["technical"] - (1 if duration_minutes <= 15 else 0)

    topics = _rank(catalog.topics_for(level), lambda t: t.title + " " + " ".join(t.key_concepts), skills)[:n_tech]
    scenarios = _rank(catalog.scenarios_for(level), lambda s: s.title, skills)
    if len(topics) < n_tech or not scenarios:
        raise ApiError(422, "invalid_request", f"catalog {track} khong du topic cho level {level}")

    tid = iter(range(1, 100))
    intro = _intro_topic(f"t{next(tid)}", level, cv)
    tech = [_catalog_topic(f"t{next(tid)}", t, level) for t in topics]
    scn = _scenario_topic(f"t{next(tid)}", scenarios[0], level)
    note = None
    if cv and cv.total_years_experience >= 5 and level in ("fresher", "junior"):
        note = "CV gợi ý kinh nghiệm cao hơn level đã chọn"
    return InterviewPlan(level_note=note, phases=[
        PlanPhase(phase="intro", time_budget_min=m_intro, topics=[intro]),
        PlanPhase(phase="technical", time_budget_min=m_tech, topics=tech),
        PlanPhase(phase="scenario", time_budget_min=m_scn, topics=[scn]),
    ])
