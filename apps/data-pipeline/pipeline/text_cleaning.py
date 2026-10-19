"""Lam sach van ban Q&A truoc khi hash va embed (FR-006, research R3).

Thu tu: NFC -> bo ky tu dieu khien -> (chi phan van xuoi) bo the HTML sot + unescape entity
-> gop khoang trang -> toi da 1 dong trong. Code block (```...```) va inline code (`...`) giu
nguyen de khong pha JSX / generic Java (List<String>) / indentation Python.
"""
import html
import re
import unicodedata

_FENCED_CODE_RE = re.compile(r"(```.*?```)", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"(`[^`\n]+`)")
# Chi the HTML pho bien, chu thuong (case-sensitive): khong an nham generic viet hoa nhu <T>, <K, V>
_HTML_TAG_NAMES = (
    "a|abbr|b|blockquote|br|code|dd|details|div|dl|dt|em|h[1-6]|hr|i|img|kbd|li|ol|p|pre|"
    "small|span|strong|sub|summary|sup|table|tbody|td|th|thead|tr|u|ul"
)
_HTML_TAG_RE = re.compile(rf"</?(?:{_HTML_TAG_NAMES})(?:\s[^<>]*)?/?>")
_LINE_BREAK_TAG_RE = re.compile(r"<br\s*/?>|</(?:p|div|li|h[1-6]|tr|summary|details|blockquote|pre)>")
# Ky tu dieu khien C0/C1 tru \t, \n; zero-width space; BOM
_CONTROL_RANGES = ((0x00, 0x08), (0x0B, 0x1F), (0x7F, 0x9F), (0x200B, 0x200B), (0xFEFF, 0xFEFF))
_CONTROL_RE = re.compile("[" + "".join(f"{chr(lo)}-{chr(hi)}" for lo, hi in _CONTROL_RANGES) + "]")
_INLINE_SPACE_RE = re.compile("[ " + chr(0x09) + chr(0xA0) + "]+")  # space, tab, NBSP
_MANY_BLANK_LINES_RE = re.compile(r"\n{3,}")


def _clean_prose(text: str) -> str:
    """Bo the HTML sot va unescape entity, bo qua inline code."""
    parts = _INLINE_CODE_RE.split(text)
    for i in range(0, len(parts), 2):  # chi so chan = van xuoi, le = inline code
        prose = _LINE_BREAK_TAG_RE.sub("\n", parts[i])
        parts[i] = html.unescape(_HTML_TAG_RE.sub("", prose))
    return "".join(parts)


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL_RE.sub("", text)
    segments = _FENCED_CODE_RE.split(text)
    for i, segment in enumerate(segments):
        if i % 2:  # code block: chi bo khoang trang cuoi dong
            segments[i] = "\n".join(line.rstrip() for line in segment.split("\n"))
        else:
            prose = _clean_prose(segment)
            segments[i] = "\n".join(_INLINE_SPACE_RE.sub(" ", line).strip() for line in prose.split("\n"))
    return _MANY_BLANK_LINES_RE.sub("\n\n", "".join(segments)).strip()


def normalize_for_compare(text: str) -> str:
    """Dang so sanh: lower, bo dau tieng Viet, bo dau cau. Dung cho trung gan dung va golden set."""
    text = clean_text(text).lower().replace("đ", "d")
    text = "".join(ch for ch in unicodedata.normalize("NFD", text) if not unicodedata.combining(ch))
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())
