"""Tham chieu ben vung cho chunk RAG (Phase 03b): id S1.. / R chi co nghia trong mot luot, con ref + title + url theo
chunk de bao cao cuoi buoi biet Evaluator da doi chieu voi tai lieu nao va dua vao study_plan.resources."""
import re
from .models_interview import SourceRef
from .rag.models import Chunk

TITLE_CHARS = 150
_MARKDOWN = re.compile(r"[*#`>_]+")


def title_of(content: str) -> str:
    """Dong dau cua chunk: voi cap Q&A cua DE la cau hoi; bo ky hieu markdown."""
    line = next((x for x in content.splitlines() if x.strip()), "")
    return " ".join(_MARKDOWN.sub("", line).split())[:TITLE_CHARS]


def source_ref(chunk: Chunk) -> SourceRef:
    return SourceRef(ref=chunk.dedup_key, title=title_of(chunk.content), url=chunk.source_url)  # url: kiem o model
