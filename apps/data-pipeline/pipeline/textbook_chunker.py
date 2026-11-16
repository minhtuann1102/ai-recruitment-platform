"""Cat trang giao trinh thanh doan (spec 012, research R6).

Moi section -> mot hoac nhieu doan. Section vua co (<= HARD_MAX_CHARS) giu nguyen mot doan; section dai hon thi
goi tham lam theo doan van (tach o dong trong), khoi ``` luon di cung doan van ngay truoc no. Doan van don le vuot
HARD_MAX_CHARS bi cat o ranh gioi cau. Khong doi chu hoa/thuong, khong chuan hoa khoang trang trong khoi.
Khong bo doan ngan o day: loc nhieu (`too_short`...) la viec cua textbook_noise_filter.
"""
import re
from typing import Dict, List, Tuple

TARGET_MIN_CHARS = 320
TARGET_MAX_CHARS = 1000
HARD_MAX_CHARS = 1600
MIN_WORDS = 30

SEP = "\n\n"
_SENTENCE_END = re.compile(r"(?<=[.!?])(\s+)")
_FENCE = "```"

Block = Tuple[str, bool]  # (text, is_code)


def split_fenced_blocks(text: str) -> List[Block]:
    """Tach van ban thanh khoi van xuoi / khoi code, theo thu tu. Dong trong KHONG tach khoi code.

    Mo khoi: dong bat dau bang ``` (ke ca ```python). Khoi khong dong -> phan con lai la code.
    Khoi van xuoi tach o dong trong; khoi code giu nguyen van ban (gom ca dong rao).
    """
    blocks: List[Block] = []
    buf: List[str] = []
    in_fence = False

    def flush(is_code: bool) -> None:
        chunk = "\n".join(buf).rstrip() if is_code else "\n".join(buf).strip()
        if chunk.strip():
            blocks.append((chunk, is_code))
        buf.clear()

    for line in text.replace("\r\n", "\n").split("\n"):
        fenced = line.lstrip().startswith(_FENCE)
        if in_fence:
            buf.append(line)
            if fenced:  # dong rao dong
                flush(True)
                in_fence = False
        elif fenced:
            flush(False)
            buf.append(line)
            in_fence = True
        elif not line.strip():
            flush(False)
        else:
            buf.append(line)
    flush(in_fence)
    return blocks


def chunk_page(page: Dict) -> List[Dict]:
    """Trang tho (data-model §2) -> [{heading_path, body}], giu thu tu section."""
    chunks: List[Dict] = []
    for section in page.get("sections", []):
        heading_path = list(section.get("heading_path") or [])
        for body in _chunk_section(section.get("text") or ""):
            chunks.append({"heading_path": heading_path, "body": body})
    return chunks


def render_content(title: str, heading_path: List[str], body: str) -> str:
    """'<title> > <h2> > <h3>\\n\\n<body>' — dong dau la duong dan tieu de."""
    return " > ".join([title, *heading_path]) + SEP + body


def _chunk_section(text: str) -> List[str]:
    text = text.replace("\r\n", "\n").strip()
    if not text:
        return []
    if len(text) <= HARD_MAX_CHARS:
        return [text]
    return _merge_tail(_pack(_group_atoms(_explode(split_fenced_blocks(text)))))


def _explode(blocks: List[Block]) -> List[Block]:
    """Khoi vuot HARD_MAX_CHARS -> cac manh <= HARD_MAX_CHARS cung loai."""
    out: List[Block] = []
    for text, is_code in blocks:
        if len(text) <= HARD_MAX_CHARS:
            out.append((text, is_code))
        elif is_code:
            out.extend((piece, True) for piece in _split_code(text))
        else:
            out.extend((piece, False) for piece in _split_prose(text))
    return out


def _group_atoms(blocks: List[Block]) -> List[str]:
    """Gan khoi code vao doan van ngay truoc (code dau section: vao doan van ke sau) neu van <= HARD_MAX_CHARS."""
    atoms: List[str] = []
    lead_code = False  # atom cuoi chi gom code dung dau section, dang cho doan van ke sau
    for text, is_code in blocks:
        fits = bool(atoms) and len(atoms[-1]) + len(SEP) + len(text) <= HARD_MAX_CHARS
        if is_code and fits:
            atoms[-1] += SEP + text
        elif is_code:
            lead_code = not atoms
            atoms.append(text)
        elif fits and lead_code:
            atoms[-1] += SEP + text
            lead_code = False
        else:
            atoms.append(text)
            lead_code = False
    return atoms


def _pack(atoms: List[str]) -> List[str]:
    """Goi tham lam toi TARGET_MAX_CHARS; atom don le lon hon van giu nguyen mot doan (<= HARD_MAX_CHARS)."""
    chunks: List[str] = []
    cur = ""
    for atom in atoms:
        if cur and len(cur) + len(SEP) + len(atom) > TARGET_MAX_CHARS:
            chunks.append(cur)
            cur = atom
        else:
            cur = cur + SEP + atom if cur else atom
    if cur:
        chunks.append(cur)
    return chunks


def _merge_tail(chunks: List[str]) -> List[str]:
    """Doan cuoi < TARGET_MIN_CHARS ma gop vao doan truoc van <= HARD_MAX_CHARS thi gop (tranh mat noi dung)."""
    if len(chunks) >= 2 and len(chunks[-1]) < TARGET_MIN_CHARS and len(chunks[-2]) + len(SEP) + len(chunks[-1]) <= HARD_MAX_CHARS:
        chunks[-2:] = [chunks[-2] + SEP + chunks[-1]]
    return chunks


def _split_prose(text: str) -> List[str]:
    """Doan van qua dai -> goi cau toi TARGET_MAX_CHARS; cau don le > HARD_MAX_CHARS thi cat o khoang trang."""
    parts = _SENTENCE_END.split(text)  # [cau, khoang trang, cau, ...]
    sentences, seps = parts[0::2], parts[1::2]
    pieces: List[str] = []
    cur = ""
    for i, sentence in enumerate(sentences):
        sep = seps[i - 1] if i else ""
        if len(sentence) > HARD_MAX_CHARS:
            if cur.strip():
                pieces.append(cur.strip())
            cur = ""
            pieces.extend(_split_on_whitespace(sentence))
        elif cur and len(cur) + len(sep) + len(sentence) > TARGET_MAX_CHARS:
            pieces.append(cur.strip())
            cur = sentence
        else:
            cur = cur + sep + sentence if cur else sentence
    if cur.strip():
        pieces.append(cur.strip())
    return pieces


def _split_on_whitespace(text: str) -> List[str]:
    """Cau khong dau cau qua dai: cat o khoang trang cuoi truoc TARGET_MAX_CHARS (khong co thi cat cung)."""
    pieces: List[str] = []
    while len(text) > HARD_MAX_CHARS:
        cut = max(text.rfind(" ", 0, TARGET_MAX_CHARS), text.rfind("\n", 0, TARGET_MAX_CHARS))
        cut = cut if cut > 0 else TARGET_MAX_CHARS
        pieces.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    if text:
        pieces.append(text)
    return pieces


def _split_code(text: str) -> List[str]:
    """Khoi code > HARD_MAX_CHARS: cat o ranh gioi dong, moi manh boc lai bang dong rao mo/dong."""
    lines = text.split("\n")
    opener = lines[0] if lines[0].lstrip().startswith(_FENCE) else _FENCE
    inner = lines[1:] if lines[0].lstrip().startswith(_FENCE) else lines
    if inner and inner[-1].strip() == _FENCE:
        inner = inner[:-1]
    budget = max(TARGET_MAX_CHARS - len(opener) - len(_FENCE) - 2, 80)
    pieces: List[str] = []
    cur: List[str] = []
    size = 0
    for line in inner:
        for part in ([line[i:i + budget] for i in range(0, len(line), budget)] or [""]):
            if cur and size + len(part) + 1 > budget:
                pieces.append("\n".join([opener, *cur, _FENCE]))
                cur, size = [], 0
            cur.append(part)
            size += len(part) + 1
    if cur:
        pieces.append("\n".join([opener, *cur, _FENCE]))
    return pieces
