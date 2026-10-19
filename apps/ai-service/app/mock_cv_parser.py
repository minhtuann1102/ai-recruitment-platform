"""CV Parser MOCK: thay buoc LLM bang quy tac regex + tu vung de dung duoc khi chua co LLM.

Phan "code" that su (trich text, redact, cat do dai, nam kinh nghiem, quet injection) nam o cv_text.py
va file nay; chi buoc trich xuat co cau truc la gia lap. Se thay bang CV Parser LLM (docs/ai-service/02 3.3.1).
"""
import re
import time
from typing import List, Optional, Tuple

from . import cv_text
from .models_cv import (CvEducation, CvExperience, CvFlags, CvParseMetadata, CvParseResponse,
                        CvProfile, CvProject, CvSkill)

_VOCAB = {
    "language": ["Java", "Python", "JavaScript", "TypeScript", "Go", "C#", "Kotlin", "PHP", "SQL", "Dart"],
    "framework": ["Spring Boot", "Spring", "Hibernate", "Django", "FastAPI", "Flask", "NestJS", "Express",
                  "React", "Next.js", "Vue", "Node.js", "PyTorch", "TensorFlow", "scikit-learn", "LangChain"],
    "database": ["PostgreSQL", "MySQL", "MongoDB", "Redis", "Oracle", "Elasticsearch", "pgvector"],
    "devops": ["Docker", "Kubernetes", "Jenkins", "Terraform", "AWS", "GCP", "Azure", "CI/CD", "GitHub Actions"],
    "tool": ["Kafka", "RabbitMQ", "Git", "Postman", "Celery", "BullMQ", "Airflow", "Spark"],
    "concept": ["REST", "GraphQL", "Microservices", "RAG", "LLM", "Machine Learning", "OOP", "Agile"],
}
_TRACK_HINTS = {
    "java_backend": {"java", "spring boot", "spring", "hibernate", "kafka"},
    "python_backend": {"python", "django", "fastapi", "flask", "celery"},
    "nodejs_backend": {"node.js", "nestjs", "express", "typescript", "javascript", "bullmq"},
    "ai_engineer": {"pytorch", "tensorflow", "scikit-learn", "langchain", "rag", "llm", "machine learning"},
}
_RANGE = re.compile(r"(\d{1,2})/(\d{4})\s*[-–—]\s*(?:(\d{1,2})/(\d{4})|(nay|hiện tại|present))", re.I)
_PROJECT = re.compile(r"^(dự án|project)\s*[:\-]?\s*(.+)$", re.I)
_EDU = re.compile(r"(kỹ sư|cử nhân|thạc sĩ|bachelor|master|engineer)[^\n]*?((?:19|20)\d{2})", re.I)


def _find_skills(text: str) -> List[Tuple[str, str]]:
    found = []
    for category, names in _VOCAB.items():
        for name in names:
            if re.search(r"(?<![\w.])" + re.escape(name) + r"(?![\w])", text, re.I):
                found.append((name, category))
    return found


def _tech_in(lines: List[str]) -> List[str]:
    return [n for n, _ in _find_skills("\n".join(lines))]


def _month_index(year: int, month: int) -> int:
    return year * 12 + month


def _experiences(lines: List[str]) -> Tuple[List[CvExperience], float]:
    items, spans = [], []
    for i, line in enumerate(lines):
        m = _RANGE.search(line)
        if not m:
            continue
        start = _month_index(int(m.group(2)), int(m.group(1)))
        if m.group(5):
            end, end_iso = None, None
        else:
            end = _month_index(int(m.group(4)), int(m.group(3)))
            end_iso = f"{m.group(4)}-{int(m.group(3)):02d}"
        role = re.split(r"\btại\b|\bat\b|\(", line[: m.start()], flags=re.I)[0].strip(" -–—,:|")
        nxt = next((x for x in lines[i + 1:i + 3] if x and not _RANGE.search(x)), "")
        items.append(CvExperience(role=role or "Developer", start=f"{m.group(2)}-{int(m.group(1)):02d}",
                                  end=end_iso, tech=_tech_in(lines[i:i + 4])[:8], summary=nxt[:300]))
        spans.append((start, end))
    return items[:8], _years(spans)


def _years(spans: List[Tuple[int, Optional[int]]]) -> float:
    """Gop khoang thoi gian chong nhau roi lam tron 0.5 nam (code tinh, khong de LLM cong tru)."""
    now = _month_index(*_today())
    merged: List[List[int]] = []
    for s, e in sorted((s, now if e is None else e) for s, e in spans):
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    months = sum(max(e - s, 0) for s, e in merged)
    return round(months / 12 * 2) / 2


def _today() -> Tuple[int, int]:
    t = time.localtime()
    return t.tm_year, t.tm_mon


def _projects(lines: List[str]) -> List[CvProject]:
    out = []
    for i, line in enumerate(lines):
        m = _PROJECT.match(line)
        if not m:
            continue
        block = lines[i + 1:i + 5]
        highlights = [b.lstrip("-•* ").strip()[:150] for b in block if b.startswith(("-", "•", "*")) and re.search(r"\d", b)]
        summary = next((b for b in block if b and not b.startswith(("-", "•", "*"))), "")
        out.append(CvProject(id=f"p{len(out) + 1}", name=m.group(2).strip()[:80], tech=_tech_in(block)[:8],
                             summary=summary[:300], highlights=highlights[:3]))
    return out[:6]


def _relevance(track: str, skills: List[str]) -> str:
    hits = len({s.lower() for s in skills} & _TRACK_HINTS.get(track, set()))
    return "high" if hits >= 3 else "medium" if hits >= 1 else "low"


def parse_cv_bytes(data: bytes, track: str) -> CvParseResponse:
    started = time.perf_counter()
    text, truncated = cv_text.prepare_cv_text(data)
    lines = [ln for ln in text.splitlines()]
    clean = [ln for ln in lines if not cv_text.has_injection(ln)]
    injection = len(clean) != len(lines)  # dong nghi injection bi loai truoc khi trich xuat

    skills_found = _find_skills("\n".join(clean))
    experiences, years = _experiences(clean)
    projects = _projects(clean)
    skills = [CvSkill(name=n, category=c, evidence="project" if any(n in p.tech for p in projects) else "listed")
              for n, c in skills_found][:25]
    edu = [CvEducation(degree=m.group(0)[:100].strip(), year=int(m.group(2))) for m in _EDU.finditer("\n".join(clean))][:3]
    top = ", ".join(s.name for s in skills[:3])
    role = experiences[0].role if experiences else "Developer"
    profile = CvProfile(
        headline=f"{role} ~{years:g} năm, {top}"[:120] if top else f"{role} ~{years:g} năm",
        skills=skills, experiences=experiences, projects=projects, education=edu,
        total_years_experience=years, track_relevance=_relevance(track, [s.name for s in skills]),
        flags=CvFlags(injection_suspected=injection, truncated=truncated),
    )
    elapsed = int((time.perf_counter() - started) * 1000)
    return CvParseResponse(cv_profile=profile, metadata=CvParseMetadata(
        model="mock-rule-based", prompt_version="cv_parser.mock", input_tokens=len(text) // 4,
        output_tokens=0, latency_ms=elapsed))
