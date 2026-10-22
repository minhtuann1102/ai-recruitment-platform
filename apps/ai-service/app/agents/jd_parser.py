"""JD Parser LLM (FR-AI-016): JD da lam sach -> JdProfile; topic_id ngoai catalog bi loai (out_of_catalog).

JD tho chi JD Parser thay; agent sau chi nhan jd_profile da qua schema (BRU-18). LLM loi thi dung parser quy tac.
"""
import json
import logging
from typing import List, Literal, Optional

import openai
from pydantic import BaseModel

from .. import mock_jd_parser
from ..catalog.models import TrackCatalog
from ..llm.errors import ConfigError, LlmError
from ..llm.gateway import LlmGateway
from ..models_cv import CvParseMetadata
from ..models_jd import JdFlags, JdParseResponse, JdProfile
from ..prompts.store import UNTRUSTED_NOTICE, PromptStore, wrap_untrusted
from .registry import agent_mode, cached_llm_agent

log = logging.getLogger("ai_service.jd_parser")


class LlmRequirement(BaseModel):
    text: str
    kind: Literal["must", "nice"]
    topic_ids: List[str]


class JdParserOutput(BaseModel):
    title: str
    requirements: List[LlmRequirement]


def catalog_listing(catalog: TrackCatalog) -> List[dict]:
    """Danh sach topic cho LLM chon id (moi level, vi JD khong gan voi level ung vien chon)."""
    return [{"id": t.id, "title": t.title, "key_concepts": t.key_concepts[:5]} for t in catalog.topics]


class LlmJdParser:
    agent = "jd_parser"

    def __init__(self, gateway: LlmGateway, prompts: Optional[PromptStore] = None, prompt_version: str = None):
        self._gateway = gateway
        self._prompt = (prompts or PromptStore()).get(self.agent, prompt_version)

    async def parse(self, jd_text: str, catalog: TrackCatalog) -> JdParseResponse:
        lines, injection, truncated = mock_jd_parser.prepare_jd_text(jd_text)
        data = {"track": catalog.track, "catalog": catalog_listing(catalog)}
        messages = [{"role": "system", "content": f"{self._prompt.text}\n\n{UNTRUSTED_NOTICE}"},
                    {"role": "user", "content": json.dumps(data, ensure_ascii=False) + "\n\n" +
                     wrap_untrusted("jd_text", "\n".join(lines))}]
        try:
            result = await self._gateway.complete(self.agent, messages, JdParserOutput,
                                                  prompt_version=self._prompt.version)
        except (LlmError, ConfigError, openai.APIError) as err:
            log.warning("jd_parser_fallback error=%s", type(err).__name__)
            return mock_jd_parser.parse_jd_text(jd_text, catalog)
        out, rec = result.data, result.record
        reqs = mock_jd_parser.finalize_requirements([(r.text, r.kind, r.topic_ids) for r in out.requirements],
                                                    catalog)
        dropped = len(reqs) < min(len(out.requirements), 15)  # co yeu cau bi loai vi chua chi dan
        title = "" if mock_jd_parser.has_jd_injection(out.title) else out.title.strip()[:120]
        profile = JdProfile(title=title, requirements=reqs,
                            flags=JdFlags(injection_suspected=injection or dropped, truncated=truncated))
        return JdParseResponse(jd_profile=profile, metadata=CvParseMetadata(
            model=rec.model, prompt_version=f"{self.agent}.{rec.prompt_version}", input_tokens=rec.input_tokens,
            output_tokens=rec.output_tokens, latency_ms=rec.latency_ms))


class MockJdParser:
    async def parse(self, jd_text: str, catalog: TrackCatalog) -> JdParseResponse:
        return mock_jd_parser.parse_jd_text(jd_text, catalog)


def get_jd_parser():
    if agent_mode("jd_parser") == "mock":
        return MockJdParser()
    return cached_llm_agent("jd_parser", LlmJdParser) or MockJdParser()
