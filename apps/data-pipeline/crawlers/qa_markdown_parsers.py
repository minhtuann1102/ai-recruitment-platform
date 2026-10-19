"""Tach cap hoi/dap tu file markdown cua cac repo Q&A phong van.

Hai kieu: (1) cau hoi la mot dong khop regex (heading, so thu tu, chu dam), dap an la cac dong
den cau hoi ke tiep hoac ranh gioi section; (2) <details><summary>cau hoi</summary>dap an</details>.
"""
import re
import textwrap
from dataclasses import dataclass
from typing import List, Optional, Pattern, Tuple

QAPair = Tuple[str, str]

# Dong "back to top" va dong chi con the HTML rong sau khi bo footer
_FOOTER_LINE_RE = re.compile("back to top|" + chr(0x2B06) + "|" + chr(0x21A5), re.IGNORECASE)  # mui ten len
_HTML_ONLY_LINE_RE = re.compile(r"^\s*(?:</?(?:div|b|a|p|br|details)[^>]*>\s*)+$")
_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
# Emoji muc do (👶 ⭐️ 🚀...) va so thu tu dau cau hoi
_EMOJI_RANGES = ((0x1F300, 0x1FAFF), (0x2600, 0x27BF), (0x2B00, 0x2BFF), (0xFE0F, 0xFE0F), (0x200D, 0x200D))
_QUESTION_NOISE_RE = re.compile("[" + "".join(f"{chr(lo)}-{chr(hi)}" for lo, hi in _EMOJI_RANGES) + "]")
_LEADING_NUMBER_RE = re.compile(r"^\s*\d+[.)]\s+")
# _nhan manh_ va **dam** trong cau hoi; khong dung vao __dunder__ hay snake_case
_UNDERSCORE_EMPHASIS_RE = re.compile(r"(?<![\w`])_([^_\n]+?)_(?![\w`])")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_DETAILS_RE = re.compile(r"<summary>(.*?)</summary>(.*?)</details>", re.DOTALL | re.IGNORECASE)
# Dong nhan "- Answer:" va dong "Image Source: ..."
_LABEL_LINE_RE = re.compile(r"^\s*(?:[-*]\s*)?(?:\*\*)?Answer:?(?:\*\*)?\s*$|^\s*Image Source:", re.IGNORECASE)
_ARTICLE_TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


@dataclass(frozen=True)
class HeadingFormat:
    question: Pattern[str]  # group(1) = cau hoi
    boundary: Optional[Pattern[str]] = None  # dong ket thuc dap an ma khong phai cau hoi
    dedent: bool = False  # dap an thut le (danh sach so thu tu markdown)


def _strip_markdown_noise(text: str) -> str:
    text = _IMAGE_RE.sub("", text)
    return _LINK_RE.sub(r"\1", text)


def clean_question(text: str) -> str:
    text = _strip_markdown_noise(_QUESTION_NOISE_RE.sub("", text))
    text = _LEADING_NUMBER_RE.sub("", text.strip())
    text = _BOLD_RE.sub(r"\1", _UNDERSCORE_EMPHASIS_RE.sub(r"\1", text))
    return text.strip(" *#")


def clean_answer(lines: List[str], dedent: bool = False) -> str:
    kept = [
        ln
        for ln in lines
        if not _FOOTER_LINE_RE.search(ln) and not _HTML_ONLY_LINE_RE.match(ln) and not _LABEL_LINE_RE.match(ln)
    ]
    text = "\n".join(kept)
    if dedent:
        text = textwrap.dedent(text)
    return _strip_markdown_noise(text).strip()


def parse_headings(markdown: str, fmt: HeadingFormat) -> List[QAPair]:
    pairs: List[QAPair] = []
    question: Optional[str] = None
    body: List[str] = []

    def flush() -> None:
        if question is not None:
            pairs.append((clean_question(question), clean_answer(body, fmt.dedent)))

    for line in markdown.splitlines():
        match = fmt.question.match(line)
        if match:
            flush()
            question, body = match.group(1), []
        elif fmt.boundary is not None and fmt.boundary.match(line):
            flush()
            question, body = None, []
        elif question is not None:
            body.append(line)
    flush()
    return pairs


def parse_article(markdown: str, answer_heading: Optional[Pattern[str]] = None) -> List[QAPair]:
    """Moi file la mot cau: cau hoi = tieu de h1; dap an = phan sau `answer_heading` (neu co) hoac sau h1."""
    title = _ARTICLE_TITLE_RE.search(markdown)
    if not title:
        return []
    start = title.end()
    if answer_heading is not None:
        section = answer_heading.search(markdown, start)
        start = section.end() if section else start
    return [(clean_question(title.group(1)), clean_answer(markdown[start:].splitlines()))]


def parse_details(markdown: str) -> List[QAPair]:
    return [
        (clean_question(re.sub(r"<[^>]+>", "", summary)), clean_answer(answer.splitlines()))
        for summary, answer in _DETAILS_RE.findall(markdown)
    ]
