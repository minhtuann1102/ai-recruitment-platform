"""JD Parser MOCK + phan code dung chung (lam sach JD, map topic, hau kiem) cho JD Parser LLM.

JD la du lieu khong tin cay nhu CV (BRU-18): chuan hoa, redact lien he, bo dong nghi injection truoc moi buoc.
Mock: moi dong gach dau dong la mot yeu cau; map ve topic khi ten topic hoac key concept xuat hien trong dong.
"""
import re
from typing import Dict, List, Tuple

from . import cv_text
from .catalog.models import TrackCatalog
from .mock_evaluator import fold
from .models_cv import CvParseMetadata
from .models_jd import JdFlags, JdParseResponse, JdProfile, JdRequirement

_NICE = re.compile(r"(uu tien|loi the|nice to have|\bplus\b|bonus|preferred|diem cong)")
_BULLET = re.compile(r"^\s*([-•*+]|\d+[.)])\s+")


def prepare_jd_text(raw: str) -> Tuple[List[str], bool, bool]:
    """-> (dong da lam sach, injection_suspected, truncated). Khong toi thieu 200 ky tu nhu CV (JD co the ngan)."""
    text, truncated = cv_text.truncate(cv_text.redact_pii(cv_text.normalize(raw)))
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    clean = [ln for ln in lines if not cv_text.has_injection(ln)]
    return clean, len(clean) != len(lines), truncated


def _keywords(catalog: TrackCatalog) -> Dict[str, List[str]]:
    return {t.id: [fold(t.title)] + [fold(c) for c in t.key_concepts] for t in catalog.topics}


def map_topics(text: str, catalog: TrackCatalog, limit: int = 3) -> List[str]:
    """Topic co ten hoac key concept (da bo dau) nam trong text; giu thu tu catalog."""
    f = fold(text)
    words = set(re.findall(r"[a-z0-9#+.]+", f))
    hits = []
    for tid, keys in _keywords(catalog).items():
        for k in keys:
            k_words = re.findall(r"[a-z0-9#+.]+", k)
            if k in f or (len(k_words) == 1 and k_words[0] in words and len(k_words[0]) >= 3):
                hits.append(tid)
                break
    return hits[:limit]


def finalize_requirements(items: List[Tuple[str, str, List[str]]], catalog: TrackCatalog) -> List[JdRequirement]:
    """(text, kind, topic_ids) -> JdRequirement: bo chuoi injection, topic_id phai co trong catalog cua track."""
    valid = {t.id for t in catalog.topics}
    out = []
    for text, kind, topic_ids in items:
        text = text.strip()
        if not text or cv_text.has_injection(text):
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
    for ln in lines:
        if not _BULLET.match(ln):
            nice_section = bool(_NICE.search(fold(ln)))  # tieu de muc "Uu tien" doi loai cho cac dong sau
            continue
        text = _BULLET.sub("", ln)
        kind = "nice" if nice_section or _NICE.search(fold(text)) else "must"
        items.append((text, kind, map_topics(text, catalog)))
    title = next((ln for ln in lines if not _BULLET.match(ln)), "")[:120]
    profile = JdProfile(title=title, requirements=finalize_requirements(items, catalog),
                        flags=JdFlags(injection_suspected=injection, truncated=truncated))
    return JdParseResponse(jd_profile=profile, metadata=CvParseMetadata(
        model="mock-rule-based", prompt_version="jd_parser.mock", input_tokens=len(raw) // 4, output_tokens=0,
        latency_ms=0))
