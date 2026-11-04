"""Tham chieu ben vung cho chunk RAG (Phase 03b): id S1.. / R chi co nghia trong mot luot, con ref + title + url theo
chunk de bao cao cuoi buoi biet Evaluator da doi chieu voi tai lieu nao va dua vao study_plan.resources."""
import re
from .models_interview import SourceRef
from .rag.models import Chunk

TITLE_CHARS = 150
# Giay phep cho phep dua noi dung (ke ca ban dich) cho ung vien; khop LICENSE_ALLOWLIST cua data-pipeline
# (pipeline/qa_seed_rules.py). CC-BY-NC-ND (cam ban dich) va "unknown" bi loai cho toi khi owner / DE chot (Q1).
SHAREABLE_LICENSES = frozenset({"CC0-1.0", "MIT", "Apache-2.0", "CC-BY-4.0", "CC-BY-SA-4.0", "CC-BY-SA-2.5"})
_MARKDOWN = re.compile(r"[*#`>_]+")


def title_of(content: str) -> str:
    """Dong dau cua chunk: voi cap Q&A cua DE la cau hoi; bo ky hieu markdown."""
    line = next((x for x in content.splitlines() if x.strip()), "")
    return " ".join(_MARKDOWN.sub("", line).split())[:TITLE_CHARS]


def source_ref(chunk: Chunk) -> SourceRef:
    return SourceRef(ref=chunk.dedup_key, title=title_of(chunk.content), url=chunk.source_url,  # url: kiem o model
                     license=chunk.license)


def shareable(source: SourceRef) -> bool:
    """Dua vao study_plan duoc khong: chi giay phep da biet va cho phep (bao thu khi chua ro)."""
    return source.license in SHAREABLE_LICENSES
