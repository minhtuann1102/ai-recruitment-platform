"""Danh sach nguon Q&A phong van tren GitHub va cach tach cap cua tung nguon.

DE quyet dinh 2026-10-19: lay ca nguon khong ro giay phep (spec 005 Clarifications). Repo du an
dang public nen noi dung thu thap KHONG commit: chi nam o data/raw/ va ai_db; tai lai bang `collect`.
`license` ghi giay phep da biet cua nguon (kiem qua GitHub API), con lai la 'unknown'.
"""
import re
from dataclasses import dataclass
from typing import Callable, List, Tuple

from .qa_markdown_parsers import HeadingFormat, QAPair, parse_article, parse_details, parse_headings


@dataclass(frozen=True)
class QASource:
    name: str  # dung trong cid: cr-<name>-<hash>
    repo: str
    paths: Tuple[str, ...]  # file, hoac "thu-muc/*.md" (moi file .md trong thu muc, tru README.md)
    parse: Callable[[str], List[QAPair]]
    lang: str  # en | uk | ru
    license: str
    attribution: str


def _headings(question: str, boundary: str = None, dedent: bool = False) -> Callable[[str], List[QAPair]]:
    fmt = HeadingFormat(re.compile(question), re.compile(boundary) if boundary else None, dedent)
    return lambda markdown: parse_headings(markdown, fmt)


_DEVINTERVIEW = _headings(r"^## \d+\.\s+(.+)$", r"^#{1,2} |^#### Explore all")
_LEARNING_ZONE = _headings(r"^## Q\.\s+(.+)$", r"^#{1,2} ")
# Cau hoi dang "12.  ### ..."; muc "### Coding Exercise" o cot 0 la ranh gioi
_SUDHEERJ = _headings(r"^\d+\.\s+### (.+)$", r"^#{1,3} ", dedent=True)

_DEVINTERVIEW_TOPICS = (
    "java spring microservices sql redis mongodb nosql docker kubernetes devops git aws load-balancing "
    "node typescript javascript python django react next llms llmops nlp deep-learning data-scientist python-ml"
).split()
_LEARNING_ZONE_REPOS = (
    "java-basics spring-boot-basics hibernate-basics sql-basics mongodb-basics python-basics "
    "nodejs-basics typescript-basics react-basics javascript-basics docker-and-kubernetes-basics"
).split()
_DEVOPS_EXERCISES_TOPICS = "containers kubernetes cicd terraform linux git databases security aws observability kafka".split()

SOURCES: Tuple[QASource, ...] = (
    *(
        QASource(f"devi-{t}", f"Devinterview-io/{t}-interview-questions", ("README.md",), _DEVINTERVIEW, "en", "unknown", "Devinterview.io")
        for t in _DEVINTERVIEW_TOPICS
    ),
    *(
        QASource(f"lz-{r}", f"learning-zone/{r}", ("README.md",), _LEARNING_ZONE, "en", "unknown", "learning-zone (Pradeep Kumar)")
        for r in _LEARNING_ZONE_REPOS
    ),
    QASource(
        "devops-exercises",
        "bregman-arie/devops-exercises",
        tuple(f"topics/{t}/README.md" for t in _DEVOPS_EXERCISES_TOPICS),
        parse_details,
        "en",
        "CC-BY-NC-ND-3.0",
        "bregman-arie/devops-exercises contributors",
    ),
    QASource("sudheerj-react", "sudheerj/reactjs-interview-questions", ("README.md",), _SUDHEERJ, "en", "MIT", "Sudheer Jonna and contributors"),
    QASource("sudheerj-js", "sudheerj/javascript-interview-questions", ("README.md",), _SUDHEERJ, "en", "unknown", "Sudheer Jonna and contributors"),
    QASource("devlovers-node", "DevLoversTeam/nodejs-interview-questions", ("README.md",), parse_details, "uk", "MIT", "DevLoversTeam contributors"),
    QASource("devlovers-python", "DevLoversTeam/python-interview-questions", ("README.md",), parse_details, "uk", "MIT", "DevLoversTeam contributors"),
    QASource("yakimka-python", "yakimka/python_interview_questions", ("questions.md",), _headings(r"^### (.+)$", r"^## "), "ru", "MIT", "yakimka and contributors"),
    QASource("grigorev-ml", "alexeygrigorev/data-science-interviews", ("theory.md",), _headings(r"^\*\*(.+?)\*\*\s*$", r"^## "), "en", "CC-BY-4.0", "Alexey Grigorev and contributors"),
    # Nguon nang cao (cau hard; quyet dinh DE 2026-10-19): moi file la mot cau phong van he phan tan / tai cao
    QASource(
        "doocs-advanced-java",
        "doocs/advanced-java",
        tuple(f"docs/{d}/*.md" for d in ("high-concurrency", "distributed-system", "high-availability", "micro-services")),
        lambda markdown: parse_article(markdown, re.compile(r"^##\s*面试题剖析\s*$", re.MULTILINE)),
        "zh",
        "CC-BY-SA-4.0",
        "doocs/advanced-java contributors",
    ),
    QASource("genai-60", "aishwaryanr/awesome-generative-ai-guide", ("interview_prep/60_gen_ai_questions.md",), _headings(r"^\d+\.\s+(.+)$", r"^## |^---\s*$", dedent=True), "en", "MIT", "Aishwarya Naresh Reganti and contributors"),
)
