"""JD Parser MOCK + phan code dung chung (lam sach JD, map topic, hau kiem) cho JD Parser LLM.

JD la du lieu khong tin cay nhu CV (BRU-18): chuan hoa, redact lien he, bo dong nghi injection truoc moi buoc.
Mock: moi dong gach dau dong la mot yeu cau; map ve topic khi ten topic hoac key concept xuat hien trong dong.
"""
import re
from typing import List, Tuple

from . import cv_text
from .catalog.models import TrackCatalog
from .mock_evaluator import fold
from .models_cv import CvParseMetadata
from .models_jd import JdFlags, JdParseResponse, JdProfile, JdRequirement

_NICE = re.compile(r"(uu tien|loi the|nice to have|\bplus\b|bonus|preferred|diem cong)")
_BULLET = re.compile(r"^\s*([-•*+]|\d+[.)])\s*")
# Mau injection cho JD hep hon cho CV: JD tieng Anh hay co "Who you are", "instructions" mot cach binh thuong
_JD_INJECTION = re.compile(r"ignore (all|previous|above)|system prompt|you are now|\[inst\]|<\||```|"
                           r"bỏ qua (mọi|các) (hướng dẫn|chỉ dẫn)|chấm .{0,20}điểm", re.I)


def has_jd_injection(value: str) -> bool:
    return bool(_JD_INJECTION.search(value))


def _is_heading(line: str) -> bool:
    """Tieu de muc: ket thuc bang ':' hoac ngan (<= 4 tu) khong co dau cau."""
    return line.endswith(":") or (len(line.split()) <= 4 and not re.search(r"[,.;]", line))


def prepare_jd_text(raw: str) -> Tuple[List[str], bool, bool]:
    """-> (dong da lam sach, injection_suspected, truncated). Khong toi thieu 200 ky tu nhu CV (JD co the ngan)."""
    text, truncated = cv_text.truncate(cv_text.redact_pii(cv_text.normalize(raw)))
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    clean = [ln for ln in lines if not has_jd_injection(ln)]
    return clean, len(clean) != len(lines), truncated


def _tokens(text: str) -> List[str]:
    return re.findall(r"[a-z0-9#+]+(?:[.-][a-z0-9]+)*", fold(text))


def _key_matches(key: str, words: List[str]) -> bool:
    """Khop tron tu (khong khop chuoi con: "agile" khong chua "gil"). Key mot tu chi tinh khi la ten cong nghe
    (co chu hoa, so hoac ky hieu: Kafka, JPA, G1) de tu thuong nhu "module", "index" khong map nham."""
    k_words = _tokens(key)
    if not k_words:
        return False
    if len(k_words) == 1 and (key.islower() or len(k_words[0]) < 3):
        return False
    n = len(k_words)
    return any(words[i:i + n] == k_words for i in range(len(words) - n + 1))


def _title_terms(title: str) -> List[str]:
    """Ten cong nghe trong tieu de topic ("Task queue voi Celery" -> "Celery"): tu viet hoa khong dung dau,
    hoac co so / ky hieu; de JD chi nhac "Celery" van map duoc."""
    words = title.split()
    return [w for i, w in enumerate(words) if (i > 0 and w[:1].isupper()) or re.search(r"[0-9#+./]", w)]


def map_topics(text: str, catalog: TrackCatalog, limit: int = 3) -> List[str]:
    """Topic co ten hoac key concept nam tron tu trong text; giu thu tu catalog."""
    words = _tokens(text)
    hits = [t.id for t in catalog.topics
            if any(_key_matches(k, words) for k in [t.title, *_title_terms(t.title), *t.key_concepts])]
    return hits[:limit]


def finalize_requirements(items: List[Tuple[str, str, List[str]]], catalog: TrackCatalog) -> List[JdRequirement]:
    """(text, kind, topic_ids) -> JdRequirement: bo chuoi injection, topic_id phai co trong catalog cua track."""
    valid = {t.id for t in catalog.topics}
    out = []
    for text, kind, topic_ids in items:
        text = text.strip()
        if not text or has_jd_injection(text):
            continue
        ids = [t for t in dict.fromkeys(topic_ids) if t in valid][:3]
        out.append(JdRequirement(id=f"r{len(out) + 1}", text=text[:150], kind=kind, topic_ids=ids,
                                 out_of_catalog=not ids))
        if len(out) == 15:
            break
    return out


def parse_jd_text(raw: str, catalog: TrackCatalog) -> JdParseResponse:
    lines, injection, truncated = prepare_jd_text(raw)
    items, nice_section = [], False
    has_bullets = any(_BULLET.match(ln) and _BULLET.sub("", ln) for ln in lines[1:])
    for ln in lines[1:]:  # dong dau la chuc danh
        if not _BULLET.match(ln) and (has_bullets or _is_heading(ln)):
            nice_section = bool(_NICE.search(fold(ln)))  # tieu de muc "Uu tien" doi loai cho cac dong sau
            continue
        text = _BULLET.sub("", ln)
        kind = "nice" if nice_section or _NICE.search(fold(text)) else "must"
        items.append((text, kind, map_topics(text, catalog)))
    title = lines[0][:120] if lines else ""
    profile = JdProfile(title=title, requirements=finalize_requirements(items, catalog),
                        flags=JdFlags(injection_suspected=injection, truncated=truncated))
    return JdParseResponse(jd_profile=profile, metadata=CvParseMetadata(
        model="mock-rule-based", prompt_version="jd_parser.mock", input_tokens=len(raw) // 4, output_tokens=0,
        latency_ms=0))
