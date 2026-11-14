"""Dau vao Evaluator va viec dung prompt: EvaluationInput, build_messages, id tai lieu S1..Sn / R, nguon da trich."""
import json
from dataclasses import dataclass, field
from typing import List, Optional

from ..evaluator_source_checks import SourcedPoint, label, source_blocks
from ..models_interview import CitedSource, PlanTopic, SourceRef, TopicTurn
from ..prompts.store import UNTRUSTED_NOTICE, wrap_untrusted


@dataclass
class EvaluationInput:
    level: str
    phase: str
    topic: PlanTopic
    difficulty: int
    turn_kind: str
    turn_number: int
    question: str
    answer: str
    topic_turns: List[TopicTurn] = field(default_factory=list)
    reference_answer: str = ""  # cap Q&A chuan trong kho khi cau vua hoi lay tu kho (question_bank)
    turn_snippets: List[str] = field(default_factory=list)  # Phase 02: chunk theo cau vua hoi + cau tra loi
    turn_sources: List[SourceRef] = field(default_factory=list)  # 03b: cung thu tu turn_snippets
    reference_source: Optional[SourceRef] = None  # 03b: cau tu kho cua reference_answer
    spoken: bool = False  # answer la ban ghi STT (answer_source = voice): doi thuat ngu phien am truoc khi cham


def build_messages(system_prompt: str, inp: EvaluationInput, with_ids: bool = False) -> List[dict]:
    """Phan tinh (rubric, anchor) o system de huong prompt caching; du lieu nguoi dung boc <untrusted>.
    with_ids (v4): moi tai lieu doi chieu co id [S1].. / [R] de Evaluator trich nguon."""
    data = {"level": inp.level, "phase": inp.phase, "difficulty": inp.difficulty, "turn_kind": inp.turn_kind,
            "topic": {"title": inp.topic.title, "objective": inp.topic.objective,
                      "key_points": inp.topic.key_points},
            "question": inp.question}
    turns = "\n".join(f"Q: {t.q}\nA: {t.a}" for t in inp.topic_turns[-5:]) or "(không có)"
    # snippet cua topic (luc start) truoc, chunk theo luot sau; prompt coi ca hai la tai lieu doi chieu (luat 8)
    blocks = source_blocks(all_snippets(inp), inp.reference_answer)
    texts = [label(i, t) if with_ids else t for i, t in blocks]
    reference = texts.pop() if inp.reference_answer else "(không có)"
    snippets = "\n---\n".join(texts) or "(không có)"
    user = "\n\n".join([json.dumps(data, ensure_ascii=False), wrap_untrusted("topic_turns", turns),
                        wrap_untrusted("reference_snippets", snippets),
                        wrap_untrusted("reference_answer", reference),
                        wrap_untrusted("answer", inp.answer)])
    return [{"role": "system", "content": f"{system_prompt}\n\n{UNTRUSTED_NOTICE}"},
            {"role": "user", "content": user}]


def all_snippets(inp: EvaluationInput) -> List[str]:
    # snippet cua topic (luc start) truoc, chunk theo luot sau: thu tu nay quyet dinh id S1..Sn
    return [*inp.topic.reference_snippets, *inp.turn_snippets]


def source_refs(inp: EvaluationInput) -> List[Optional[SourceRef]]:
    """Tham chieu ben vung cung thu tu id S1.. / R; thieu (plan cu, interview-service bo truong) thi None."""
    topic = list(inp.topic.reference_sources)[:len(inp.topic.reference_snippets)]
    topic += [None] * (len(inp.topic.reference_snippets) - len(topic))
    turn = list(inp.turn_sources)[:len(inp.turn_snippets)]
    turn += [None] * (len(inp.turn_snippets) - len(turn))
    return topic + turn + ([inp.reference_source] if inp.reference_answer else [])


def cited_sources(points: List[SourcedPoint], inp: EvaluationInput) -> List[CitedSource]:
    """Tai lieu cac y (giu lai + bi bac bo) da trich, bo trung theo id; y contradicted dung truoc (can on nhat)."""
    ids = [i for i, _ in source_blocks(all_snippets(inp), inp.reference_answer)]
    refs = dict(zip(ids, source_refs(inp)))
    out: dict = {}
    for p in sorted(points, key=lambda p: p.support != "contradicted"):
        for i in p.source_ids:
            if refs.get(i) is not None and i not in out:
                out[i] = CitedSource(**refs[i].model_dump(), id=i, support=p.support)
    return list(out.values())
