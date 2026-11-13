"""Tach dap an thanh cac y (point) cho ra soat pham vi cau hoi (spec 005 FR-030, T067); hop dong chung cua
scope-check-prepare / scope-check-score. Tat dinh, khong goi LLM.

Quy tac tach (moi dong khong phai tieu de nam trong dung mot y):
- Moi bullet (`- `, `* `, `1. `) la mot y; dong thut vao ngay sau bullet (ke ca bullet long) thuoc ve bullet do.
- Doan van (cac dong thuong lien tiep, khong bullet) la mot y.
- Tieu de KHONG phai y: dong chi in dam (`**Schema**`, co the them `:`), dong `# ...`, hoac dong thuong ket thuc
  bang ':' va ngan (<= MAX_COLON_HEADING ky tu; dong dai hon co noi dung that nen la y). Tieu de duoc them vao dau
  cac y theo sau dang `[tieu de] `; hai tieu de lien nhau khong co y o giua xep chong (`[a > b]`). Pham vi tieu de
  het khi gap tieu de moi, hoac mot dong trong roi den mot doan van thuong (bullet sau dong trong van thuoc tieu de cu).
- Khoi code ``` ... ``` dinh vao y ngay truoc no (ke ca qua dong trong); khong co y truoc thi tu thanh mot y.
  Trong khoi code khong phan loai gi, giu nguyen ca dong trong.
- Bo tach chi nhan ``` o dau dong; dap an co ``` giua dong hoac so khoi le bi check_fences tu choi (prepare thoat 1).
- Tieu de khong co y nao theo sau (het dap an) thanh mot y de khong mat chu.
- Bullet `- ` / `* ` bi bo dau (giu so `1.` vi thu tu co nghia); y ghi them tien to tieu de khi co.
"""
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Trang thai tung y do judge gan: asked = cau hoi hoi y nay; sibling = y thuoc cau hoi nua anh em; unasked = khong ai hoi
STATUSES = ("asked", "sibling", "unasked")
FLAGGING_STATUSES = ("sibling", "unasked")
BATCH_GLOB = "batch-*.json"
MANIFEST_NAME = "manifest.json"
MAX_COLON_HEADING = 60  # dong ket thuc ':' dai hon muc nay la y chu khong phai tieu de

BOLD_ONLY = re.compile(r"^\*\*([^*]+)\*\*\s*:?$")
MD_HEADING = re.compile(r"^#{1,6}\s+(.+)$")
BULLET = re.compile(r"^[-*]\s+(.*)$")
NUMBERED = re.compile(r"^\d+[.)]\s+")
FENCE = "```"


class ScopeCheckError(RuntimeError):
    """Loi dau vao cua scope-check-prepare / scope-check-score (lenh in thong diep va thoat ma khac 0)."""


@dataclass
class _Point:
    heading: str
    lines: List[str]
    kind: str  # bullet | para | fence


@dataclass
class _State:
    points: List[_Point] = field(default_factory=list)
    last: Optional[_Point] = None  # y dang mo de noi tiep dong; None sau tieu de
    heading: List[str] = field(default_factory=list)  # tieu de dang co hieu luc (xep chong)
    heading_raw: List[str] = field(default_factory=list)  # dong goc cua tieu de chua gan y nao
    blank: bool = False  # vua gap dong trong

    def start(self, kind: str, line: str) -> _Point:
        # doan van sau dong trong ket thuc pham vi tieu de da gan it nhat mot y
        if kind != "bullet" and self.blank and self.heading and not self.heading_raw:
            self.heading = []
        point = _Point(" > ".join(self.heading), [line], kind)
        self.points.append(point)
        self.last, self.heading_raw = point, []
        return point


def check_fences(answer: str) -> Optional[str]:
    """Ly do dap an co khoi code ``` ma bo tach y khong xu ly dung, hoac None. Chi nhan ``` o dau dong (sau thut le);
    ``` giua dong hay so khoi le (khong dong) se lam cac y sau bi gop sai, nen prepare tu choi."""
    toggles = 0
    for number, line in enumerate(answer.split("\n"), start=1):
        count = line.count(FENCE)
        if count and not line.lstrip().startswith(FENCE):
            return f"dong {number}: ``` khong nam o dau dong"
        toggles += count % 2
    return "so ``` le (khoi code khong dong)" if toggles % 2 else None


def heading_text(stripped: str) -> Optional[str]:
    """Noi dung tieu de neu dong (da strip, khong phai bullet) la tieu de, nguoc lai None."""
    match = BOLD_ONLY.match(stripped) or MD_HEADING.match(stripped)
    if match:
        return match.group(1).strip().rstrip(":").strip()
    if stripped.endswith(":") and len(stripped) <= MAX_COLON_HEADING:
        return stripped[:-1].strip()
    return None


def split_points(answer: str) -> List[Tuple[str, List[str]]]:
    """[(tieu de da xep chong hoac '', cac dong cua y)] theo thu tu; dung truc tiep de kiem tra bao phu."""
    state, in_fence = _State(), False
    for raw in answer.split("\n"):
        line, stripped = raw.rstrip(), raw.strip()
        if in_fence:  # trong khoi code giu nguyen moi dong, ke ca dong trong
            state.last.lines.append(line)
            in_fence = not stripped.startswith(FENCE)
            continue
        if not stripped:
            state.blank = True
            continue
        last, is_bullet = state.last, BULLET.match(stripped)
        is_list = bool(is_bullet or NUMBERED.match(stripped))
        title = None if is_list else heading_text(stripped)
        if stripped.startswith(FENCE):
            if last is not None:
                last.lines.append(line)
            else:
                state.start("fence", line)
            in_fence = stripped.count(FENCE) % 2 == 1
        elif raw[:1].isspace() and last is not None and last.kind == "bullet":
            last.lines.append(line)  # dong thut vao (ke ca bullet long) thuoc bullet truoc
        elif title is not None:
            if not state.heading_raw:
                state.heading = []
            state.heading.append(title)
            state.heading_raw.append(stripped)
            state.last = None
        elif is_list:
            state.start("bullet", is_bullet.group(1) if is_bullet else stripped)
        elif last is not None and last.kind == "para" and not state.blank:
            last.lines.append(stripped)
        else:
            state.start("para", stripped)
        state.blank = False
    if state.heading_raw:  # tieu de cuoi khong co y theo sau: giu chu bang cach cho no thanh mot y
        state.points.append(_Point("", list(state.heading_raw), "para"))
    return [(point.heading, point.lines) for point in state.points]


def segment_answer(answer: str) -> List[Dict[str, str]]:
    """[{"id": "p1", "text": "[tieu de] noi dung"}, ...] theo thu tu trong dap an."""
    points = []
    for number, (heading, lines) in enumerate(split_points(answer), start=1):
        body = "\n".join(lines)
        points.append({"id": f"p{number}", "text": f"[{heading}] {body}" if heading else body})
    return points
