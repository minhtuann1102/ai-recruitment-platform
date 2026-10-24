"""Viet lai truy van tieng Viet thanh truy van tim kiem tieng Anh bang LLM (thu nghiem rag-design muc 7.4).

Chi dung cho duong tim vector (topic < 2 cap Q&A); loi LLM thi dung truy van goc (RAG khong duoc lam hong phien).
"""
import logging
from typing import Optional

from ..llm.gateway import LlmGateway
from ..llm.usage import UsageCollector
from ..prompts.store import UNTRUSTED_NOTICE, PromptStore, wrap_untrusted

log = logging.getLogger("ai_service.rag")
AGENT = "query_rewriter"


class QueryRewriter:
    def __init__(self, gateway: LlmGateway, prompts: Optional[PromptStore] = None):
        self._gateway = gateway
        self._prompt = (prompts or PromptStore()).get(AGENT)

    async def to_english(self, query: str, collector: Optional[UsageCollector] = None) -> str:
        messages = [{"role": "system", "content": f"{self._prompt.text}\n\n{UNTRUSTED_NOTICE}"},
                    {"role": "user", "content": wrap_untrusted("query", query[:500])}]
        try:
            result = await self._gateway.complete(AGENT, messages, prompt_version=self._prompt.version,
                                                  collector=collector)
        except Exception as err:  # truy hoi la tuy chon: loi thi giu truy van goc
            log.warning("query_rewrite_failed error=%s", type(err).__name__)
            return query
        text = " ".join(str(result.data).split())[:300]
        return text or query
