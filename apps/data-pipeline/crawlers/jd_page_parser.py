"""Parse trang chi tiet JD -> Raw JD (spec 009 R2, contracts/jd-record-formats.md).

Doc moi <script type="application/ld+json">: JobPosting nam trong mang hoac @graph; khoi JSON loi bi bo qua
thay vi dung ca trang. Khong co JobPosting -> None. Khong xoa PII o day (crawl_source xoa truoc khi tra).
"""
import json
import re
from typing import Any, Dict, Iterator, List, Optional

from bs4 import BeautifulSoup

from pipeline.text_cleaning import clean_text

from .jd_sources import JdSource

REQUIRED_FIELDS = ("source", "source_job_id", "url", "crawled_at", "title", "company", "description_text")
# Xuong dong o the khoi; the inline (strong, a, code) giu lien mach de tieu de section nam tren dong rieng
_BLOCK_TAGS = ("p", "div", "li", "ul", "ol", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "blockquote")
_PLAIN_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
_ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _walk(value: Any) -> Iterator[Dict]:
    if isinstance(value, list):
        for item in value:
            yield from _walk(item)
    elif isinstance(value, dict):
        yield value
        yield from _walk(value.get("@graph", []))


def _find_job_posting(soup: BeautifulSoup) -> Optional[Dict]:
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.get_text(), strict=False)  # strict=False: JSON-LD hay co xuong dong tho
        except ValueError:
            continue
        for node in _walk(data):
            kind = node.get("@type")
            if kind == "JobPosting" or (isinstance(kind, list) and "JobPosting" in kind):
                return node
    return None


def _text(value: Any) -> str:
    """Chuoi sach tu gia tri JSON-LD: chuoi, hoac doi tuong co 'name' (hiringOrganization...)."""
    if isinstance(value, dict):
        return _text(value.get("name"))
    return clean_text(value) if isinstance(value, str) else ""


def _html_to_text(markup: str) -> str:
    soup = BeautifulSoup(markup, "html.parser")
    for noise in soup.find_all(("script", "style")):
        noise.decompose()
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for block in soup.find_all(_BLOCK_TAGS):
        block.insert_before("\n")
        block.insert_after("\n")
    return re.sub(r"\n\s*\n+", "\n", clean_text(soup.get_text()))


def _description(posting: Dict, soup: BeautifulSoup, source: JdSource) -> str:
    text = _html_to_text(str(posting.get("description") or ""))
    if source.description_selector:  # topdev: JSON-LD chi co doan rut gon, than mo ta nam trong HTML
        node = soup.select_one(source.description_selector)
        body = _html_to_text(node.decode_contents()) if node is not None else ""
        if len(body) > len(text):
            text = body
    return text


def _skills(posting: Dict) -> List[str]:
    raw = posting.get("skills")
    items = re.split(r"[,;|\n]", raw) if isinstance(raw, str) else (raw if isinstance(raw, list) else [])
    return [s for s in dict.fromkeys(_text(item) for item in items) if s]


def _locations(posting: Dict) -> List[str]:
    places = posting.get("jobLocation")
    found: List[str] = []
    for place in places if isinstance(places, list) else [places]:
        address = place.get("address") if isinstance(place, dict) else place
        if isinstance(address, dict):  # thanh pho nam o addressRegion, quan / huyen o addressLocality
            address = address.get("addressRegion") or address.get("addressLocality") or address.get("streetAddress")
        text = _text(address)
        if text and text not in found:
            found.append(text)
    return found


def _experience(posting: Dict) -> Optional[str]:
    value = posting.get("experienceRequirements")
    if isinstance(value, dict):
        months = value.get("monthsOfExperience")
        return f"{months} months" if months not in (None, "") else (_text(value.get("description")) or None)
    return _text(value) or None


def _employment_types(posting: Dict) -> List[str]:
    values: List[Any] = []
    for key in ("employmentType", "jobLocationType"):  # jobLocationType: TELECOMMUTE -> remote (R6)
        raw = posting.get(key)
        values += raw if isinstance(raw, list) else [raw]
    return [t for t in dict.fromkeys(_text(v) for v in values) if t]


def _number(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        value = float(value) if _PLAIN_NUMBER_RE.fullmatch(value.strip()) else None
    if not isinstance(value, (int, float)) or value <= 0:
        return None
    return int(value) if float(value).is_integer() else value


def _salary(posting: Dict) -> Optional[Dict]:
    """So that -> {currency, min, max, text: None}; chu ("Sign in to view salary", "Thoa thuan") -> {text, min/max: None}."""
    base = posting.get("baseSalary")
    currency = _text(base.get("currency")) or None if isinstance(base, dict) else None
    node = base.get("value", base) if isinstance(base, dict) else base
    node = node if isinstance(node, dict) else {"value": node}
    low, high, single = (_number(node.get(key)) for key in ("minValue", "maxValue", "value"))
    if low is None and high is None:
        low = high = single
    if low is not None or high is not None:
        return {"currency": currency, "min": low, "max": high, "text": None}
    text = _text(node.get("value"))
    return {"text": text, "min": None, "max": None} if text else None


def _date(value: Any) -> Optional[str]:
    text = _text(value)
    return (text[:10] if _ISO_DATE_RE.match(text) else text) or None


def parse_job_page(html: str, source: JdSource, url: str, crawled_at: str) -> Optional[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    posting = _find_job_posting(soup)
    if posting is None:
        return None
    org = posting.get("hiringOrganization")
    return {
        "source": source.name,
        "source_job_id": source.job_id(url) or "",
        "url": url,
        "crawled_at": crawled_at,
        "title": _text(posting.get("title") or posting.get("name")),
        "company": _text(org[0] if isinstance(org, list) and org else org),
        "skills_raw": _skills(posting),
        "description_text": _description(posting, soup, source),
        "location_raw": _locations(posting),
        "experience_raw": _experience(posting),
        "employment_type_raw": _employment_types(posting),
        "salary_raw": _salary(posting),
        "date_posted": _date(posting.get("datePosted")),
        "valid_through": _date(posting.get("validThrough")),
        "synthetic": False,
    }


def missing_required(record: Dict) -> List[str]:
    """Ten cac truong bat buoc (contract Raw JD) con trong; rong = record dung duoc."""
    return [field for field in REQUIRED_FIELDS if not record.get(field)]
