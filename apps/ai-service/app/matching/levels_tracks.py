"""Bang bac level va anh xa track phong van -> nhom JD cua 009 (spec 017 Assumptions, data-model muc 3, research R7)."""
from typing import Dict, Optional

# Nhan level cua JD 009 (Intern|Junior|Mid|Senior|Lead|Manager) va cua request (fresher|junior|middle|senior)
# dung chung mot thang bac. 009 gop fresher vao Junior.
_LEVEL_RANK: Dict[str, int] = {
    "intern": 0, "fresher": 1, "junior": 1, "mid": 2, "middle": 2, "senior": 3, "lead": 4, "manager": 5,
}

# 6 track phong van (app/catalog/*.yaml; co test doi chieu) -> nhom JD. Nhom mobile_fullstack chua co track nen
# chua duoc goi y.
TRACK_GROUPS: Dict[str, str] = {
    "java_backend": "backend",
    "nodejs_backend": "backend",
    "python_backend": "backend",
    "frontend_react": "frontend",
    "devops_engineer": "devops",
    "ai_engineer": "ai_data",
}


def level_rank(label: Optional[str]) -> Optional[int]:
    """Nhan level -> bac; khong co hoac nhan la -> None (khong loc, level_fit 0.5)."""
    return _LEVEL_RANK.get((label or "").strip().lower())


def rank_from_years(years: Optional[float]) -> Optional[int]:
    """Suy bac tu so nam kinh nghiem, cung nguong level_from_years cua 009: < 3 Junior, < 5 Mid, con lai Senior."""
    if years is None:
        return None
    if years < 3:
        return 1
    return 2 if years < 5 else 3


def candidate_level_rank(level: Optional[str], years: Optional[float]) -> Optional[int]:
    """Bac cua ung vien: level muc tieu trong request neu co, khong thi suy tu so nam, khong co ca hai thi None."""
    explicit = level_rank(level)
    return explicit if explicit is not None else rank_from_years(years)


def group_for_track(track: str) -> Optional[str]:
    return TRACK_GROUPS.get(track)
