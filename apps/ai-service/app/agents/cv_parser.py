"""CV Parser LLM (FR-AI-013): text CV da redact -> CvProfile qua structured output, roi code hau kiem.

Phan code giu nguyen tu mock: trich text, redact PII, cat do dai, bo dong nghi injection truoc khi gui LLM
(cv_text). Code dien total_years_experience va flags (design 02 muc 3.3.1). LLM loi thi dung parser quy tac.
"""
import json
import logging
import re
from typing import List, Literal, Optional

import openai
from pydantic import BaseModel

from .. import cv_text, mock_cv_parser
from ..llm.errors import ConfigError, LlmError
from ..llm.gateway import LlmGateway
from ..models_cv import (CvEducation, CvExperience, CvFlags, CvParseMetadata, CvParseResponse, CvProfile,
                         CvProject, CvSkill)
from ..prompts.store import UNTRUSTED_NOTICE, PromptStore, wrap_untrusted
from .registry import agent_mode, cached_llm_agent

log = logging.getLogger("ai_service.cv_parser")
_YM = re.compile(r"^(19|20)\d{2}-(0[1-9]|1[0-2])$")


# Schema gui cho LLM: khong co id, nam kinh nghiem, flags (code dien); khong rang buoc do dai (code cat)
class LlmExperience(BaseModel):
    role: str
    company_type: Literal["product", "outsource", "startup", "other", "unknown"]
    start: Optional[str]
    end: Optional[str]
    tech: List[str]
    summary: str


class LlmProject(BaseModel):
    name: str
    role: str
    tech: List[str]
    summary: str
    highlights: List[str]


class CvParserOutput(BaseModel):
    headline: str
    skills: List[CvSkill]
    experiences: List[LlmExperience]
    projects: List[LlmProject]
    education: List[CvEducation]
    track_relevance: Literal["high", "medium", "low"]


def _clean(value: str, limit: int) -> str:
    """Bo chuoi co dau hieu injection (FR-AI-012) va cat do dai."""
    return "" if cv_text.has_injection(value) else value.strip()[:limit]


def _clean_list(values: List[str], limit: int, size: int) -> List[str]:
    return [v for v in (_clean(x, limit) for x in values) if v][:size]


def _ym(value: Optional[str]) -> Optional[str]:
    return value if value and _YM.match(value) else None


def to_profile(out: CvParserOutput, *, injection: bool, truncated: bool) -> CvProfile:
    """Hau kiem: cat do dai theo schema, bo chuoi injection, ngay sai dinh dang -> null, code tinh nam KN."""
    experiences = [CvExperience(role=_clean(e.role, 80) or "Developer", company_type=e.company_type,
                                start=_ym(e.start), end=_ym(e.end) if e.end else None,
                                tech=_clean_list(e.tech, 40, 8), summary=_clean(e.summary, 300))
                   for e in out.experiences[:8]]
    projects = [CvProject(id=f"p{i + 1}", name=_clean(p.name, 80) or f"Dự án {i + 1}", role=_clean(p.role, 80),
                          tech=_clean_list(p.tech, 40, 8), summary=_clean(p.summary, 300),
                          highlights=_clean_list(p.highlights, 150, 3))
                for i, p in enumerate(out.projects[:6])]
    skills = [s for s in out.skills if not cv_text.has_injection(s.name)][:25]
    dropped = (len(out.skills) > len(skills) or any(cv_text.has_injection(x) for x in
               [out.headline] + [e.summary for e in out.experiences] + [p.summary for p in out.projects]))
    return CvProfile(
        headline=_clean(out.headline, 120) or "Ứng viên", skills=[s.model_copy(update={"name": s.name[:40]})
                                                                   for s in skills],
        experiences=experiences, projects=projects,
        education=[CvEducation(degree=_clean(e.degree, 100) or "Không rõ", year=e.year) for e in out.education[:3]],
        total_years_experience=mock_cv_parser.years_from_experiences(experiences),
        track_relevance=out.track_relevance,
        flags=CvFlags(injection_suspected=injection or dropped, truncated=truncated))


class LlmCvParser:
    agent = "cv_parser"

    def __init__(self, gateway: LlmGateway, prompts: Optional[PromptStore] = None, prompt_version: str = None):
        self._gateway = gateway
        self._prompt = (prompts or PromptStore()).get(self.agent, prompt_version)

    async def parse(self, data: bytes, track: str) -> CvParseResponse:
        text, truncated = cv_text.prepare_cv_text(data)  # loi dinh dang -> ApiError nhu mock
        lines = text.splitlines()
        clean = [ln for ln in lines if not cv_text.has_injection(ln)]
        injection = len(clean) != len(lines)
        messages = [{"role": "system", "content": f"{self._prompt.text}\n\n{UNTRUSTED_NOTICE}"},
                    {"role": "user", "content": json.dumps({"track": track}) + "\n\n" +
                     wrap_untrusted("cv_text", "\n".join(clean))}]
        try:
            result = await self._gateway.complete(self.agent, messages, CvParserOutput,
                                                  prompt_version=self._prompt.version)
        except (LlmError, ConfigError, openai.APIError) as err:
            log.warning("cv_parser_fallback error=%s", type(err).__name__)
            return mock_cv_parser.parse_cv_bytes(data, track)  # parser quy tac: van ra CvProfile hop le
        rec = result.record
        return CvParseResponse(
            cv_profile=to_profile(result.data, injection=injection, truncated=truncated),
            metadata=CvParseMetadata(model=rec.model, prompt_version=f"{self.agent}.{rec.prompt_version}",
                                     input_tokens=rec.input_tokens, output_tokens=rec.output_tokens,
                                     latency_ms=rec.latency_ms))


class MockCvParser:
    async def parse(self, data: bytes, track: str) -> CvParseResponse:
        return mock_cv_parser.parse_cv_bytes(data, track)


def get_cv_parser():
    """AGENT_CV_PARSER_MODE=llm thi dung LLM; thieu cau hinh LLM thi ve parser quy tac (khong loi 500)."""
    if agent_mode("cv_parser") == "mock":
        return MockCvParser()
    return cached_llm_agent("cv_parser", LlmCvParser) or MockCvParser()
