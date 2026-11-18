"""Tach trang tai lieu (HTML hoac markdown) thanh section, dung chung cho react_docs_crawler (005 US5) va
crawler textbook (spec 012, research R5).

Cau truc ra: sections[{heading_path, text}]; code block giu dang ``` de chunker khong cat roi khoi doan van.
Text da clean_text + scrub_pii (FR-023). Voi trang textbook (parse_html_page / parse_markdown_page) heading_path
KHONG gom ten trang (h1): ten trang di rieng trong "title" (data-model §2); section nam truc tiep duoi h1 co
heading_path rong. parse_sections giu nguyen hanh vi cu (h1 nam trong path) cho react_docs_crawler.
"""
import re
from typing import Dict, List, Optional, Tuple

from bs4 import BeautifulSoup, Tag

from pipeline.pii_patterns import scrub_pii
from pipeline.text_cleaning import clean_text

from .docs_html_cleanup import preserve_code_line_breaks, remove_hidden

HEADING_LEVELS = {"h1": 1, "h2": 2, "h3": 3}
BLOCK_TAGS = ("h1", "h2", "h3", "p", "li", "pre", "blockquote", "td", "th", "dt", "dd")  # dt/dd: danh sach dinh nghia MDN
# Block cha de bo block long: dd KHONG tinh (dd chua p/ul/pre thi cac block con tu duoc nhat, giu dong code + ranh gioi)
_NESTING_PARENT_TAGS = tuple(t for t in BLOCK_TAGS if t != "dd")
# Phan giao dien, khong phai noi dung (nut copy code, icon, script)
NOISE_TAGS = ("script", "style", "noscript", "svg", "button", "nav", "iframe")

_FENCE_RE = re.compile(r"^ {0,3}(```|~~~)")
# Tieu day '#' dong (ATX) toi cap 3; "# C#" giu nguyen "C#" vi '#' dong phai dung sau khoang trang
_MD_HEADING_RE = re.compile(r"^ {0,3}(#{1,3})[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$")


def _block_text(element: Tag) -> str:
    if element.name == "pre":
        code = element.get_text().strip("\n")
        return f"```\n{code}\n```" if code.strip() else ""
    return element.get_text(" ", strip=True)


def content_root(soup: BeautifulSoup, selector: Optional[str]) -> Optional[Tag]:
    """Vung noi dung: selector CSS cua nguon; khong co selector thi <article>, roi <main>.

    Selector da khai ma khong khop gi thi tra None (khong lui ve article / main) de selector sai lo ra thanh
    "0 section" thay vi am tham lay ca sidebar.
    """
    if selector and selector.strip():
        return soup.select_one(selector.strip())
    return soup.find("article") or soup.find("main")


def parse_sections(root: Tag, level_stack: bool = False) -> List[Dict]:
    """Gom block theo heading gan nhat; heading_path = [h1, h2, h3] hien hanh. Bo section rong.

    level_stack=False (react_docs_crawler, 005): path = path[: cap-1] + [heading] - khi thieu h1 cac h2 long vao nhau.
    level_stack=True (textbook): ngan xep cap, pop khi cap dinh >= cap moi nen h2 lien tiep la anh em (nhu markdown).
    """
    sections: List[Dict] = []
    path: List[str] = []
    levels: List[int] = []  # cap cua tung phan tu trong path, chi dung khi level_stack
    buffer: List[str] = []

    def flush() -> None:
        text = scrub_pii(clean_text("\n\n".join(b for b in buffer if b)))
        if text and path:
            sections.append({"heading_path": list(path), "text": text})
        buffer.clear()

    for element in root.find_all(BLOCK_TAGS):
        # Block long trong block khac (p trong li, li trong li...) da nam trong text cua block ngoai
        if element.find_parent(_NESTING_PARENT_TAGS) is not None:
            continue
        if element.name == "dd" and element.find(BLOCK_TAGS) is not None:
            continue  # dd chua block: p / ul / pre / dl long ben trong duoc nhat rieng
        level = HEADING_LEVELS.get(element.name)
        if level is None:
            buffer.append(_block_text(element))
            continue
        flush()
        heading = scrub_pii(clean_text(element.get_text(" ", strip=True)))
        if level_stack:
            while levels and levels[-1] >= level:
                levels.pop()
                path.pop()
            levels.append(level)
            path.append(heading)
        else:
            path[:] = path[: level - 1] + [heading]
    flush()
    return sections


def _drop_title_from_paths(sections: List[Dict], title: str) -> List[Dict]:
    """Bo h1 (= ten trang) khoi dau heading_path; section duoi h1 truc tiep co heading_path rong."""
    for section in sections:
        if section["heading_path"] and section["heading_path"][0] == title:
            section["heading_path"] = section["heading_path"][1:]
    return sections


def parse_html_page(html: str, selector: Optional[str] = None) -> Optional[Dict]:
    """{title, sections} cua mot trang HTML; None neu khong co vung noi dung hoac khong co section nao."""
    soup = BeautifulSoup(html, "html.parser")
    for noise in soup.find_all(NOISE_TAGS):
        noise.decompose()
    root = content_root(soup, selector)
    if root is None:
        return None
    remove_hidden(root)  # truoc khi doc h1 / heading: text an khong lot vao title va heading_path
    preserve_code_line_breaks(root)
    sections = parse_sections(root, level_stack=True)
    if not sections:
        return None
    h1 = root.find("h1")
    if h1 is None:
        h1 = soup.find("h1")
        if h1 is not None:
            remove_hidden(h1)  # h1 ngoai vung noi dung chua duoc don
    raw_title = h1.get_text(" ", strip=True) if h1 is not None else (soup.title.get_text(strip=True) if soup.title else "")
    title = scrub_pii(clean_text(raw_title))
    return {"title": title, "sections": _drop_title_from_paths(sections, title)}


def parse_markdown_page(text: str) -> Dict:
    """{title, sections} cua mot file markdown: tach theo dong '#', '##', '###' ngoai khoi ```.

    title = tieu de '#' dau tien; khong co thi lay `title:` trong front-matter YAML (docs Hugo nhu Redis, Docker);
    ca hai deu khong co thi "". Tieu de cap 4+ khong tach, nam trong than section.
    heading_path theo ngan xep cap tieu de: hai '##' lien tiep la anh em, ke ca khi file khong co '#'.
    """
    sections: List[Dict] = []
    stack: List[Tuple[int, str]] = []  # (cap, tieu de) tu goc toi tieu de hien tai
    buffer: List[str] = []
    fence: Optional[str] = None  # dau mo khoi code dang mo (``` hoac ~~~), None = ngoai khoi code
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    lines, title = _strip_front_matter(lines)

    def flush() -> None:
        body = scrub_pii(clean_text("\n".join(buffer)))
        if body and stack:
            sections.append({"heading_path": [h for _, h in stack], "text": body})
        buffer.clear()

    has_h1 = False
    for line in lines:
        fence_match = _FENCE_RE.match(line)
        if fence_match and (fence is None or fence_match.group(1) == fence):
            fence = None if fence else fence_match.group(1)
            buffer.append(line)
            continue
        heading = None if fence else _MD_HEADING_RE.match(line)
        if heading is None or not heading.group(2).strip():
            buffer.append(line)
            continue
        flush()
        level, heading_text = len(heading.group(1)), scrub_pii(clean_text(heading.group(2)))
        if level == 1 and not has_h1:
            has_h1, title = True, heading_text
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, heading_text))
    flush()
    return {"title": title, "sections": _drop_title_from_paths(sections, title) if title else sections}


def _strip_front_matter(lines: List[str]) -> Tuple[List[str], str]:
    """Bo khoi front-matter YAML (`---` ... `---`) o dau file; tra (dong con lai, gia tri `title:` hoac "")."""
    if not lines or lines[0].strip() != "---":
        return lines, ""
    for end in range(1, len(lines)):
        if lines[end].strip() == "---":
            title = ""
            for line in lines[1:end]:
                key, _, value = line.partition(":")
                if key.strip() == "title" and value.strip():
                    title = scrub_pii(clean_text(value.strip().strip("'\"")))
            return lines[end + 1:], title
    return lines, ""
